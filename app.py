
# app.py（自研版 v7）
# 四分頁：人物 / 關係 / 法定繼承試算 / 家族樹
# 參考系譜學慣例，但使用我們自定 JSON Schema（仍相容舊版 members/children 與 persons/links）
# 家族樹：預設使用 Graphviz（夫妻水平線；已婚=實線、離婚/喪偶=虛線；孩子從夫妻中點垂直往下）。保留 PyVis 做為備援。

import json
from datetime import date, datetime
from collections import defaultdict, deque
from typing import Dict, List, Tuple
import tempfile

import streamlit as st
import pandas as pd
from graphviz import Digraph
from pyvis.network import Network

# ----------------- 自家資料模型（簡潔但完整） -----------------
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None, note=""):
        self.pid, self.name, self.gender, self.birth, self.death, self.note = pid, name, gender, birth, death, note
    def alive_on(self, d: date) -> bool:
        if not self.death: return True
        try:
            return datetime.strptime(self.death, "%Y-%m-%d").date() > d
        except:
            return True

class Marriage:
    def __init__(self, mid, a, b, status="married", start=None, end=None):
        self.mid, self.a, self.b, self.status, self.start, self.end = mid, a, b, status, start, end

class ParentChild:
    def __init__(self, cid, parent, child):
        self.cid, self.parent, self.child = cid, parent, child

class DB:
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.marriages: Dict[str, Marriage] = {}
        self.links: Dict[str, ParentChild] = {}

    @staticmethod
    def from_obj(o)->"DB":
        db = DB()
        # 支援兩種外來結構：members/marriages/children 或 persons/marriages/links
        if "members" in o:
            for m in o.get("members", []):
                db.persons[m["id"]] = Person(m["id"], m["name"], m.get("gender","unknown"), m.get("birth"), m.get("death"), m.get("note",""))
            for m in o.get("marriages", []):
                mid = m.get("id") or f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(mid, m["husband"], m["wife"], m.get("status","married"), m.get("start"), m.get("end"))
            for c in o.get("children", []):
                # 容錯：允許只有父或只有母（單親）
                if c.get("father"):
                    cid1 = f"c_{c['father']}_{c['child']}"
                    db.links[cid1] = ParentChild(cid1, c["father"], c["child"])
                if c.get("mother"):
                    cid2 = f"c_{c['mother']}_{c['child']}"
                    db.links[cid2] = ParentChild(cid2, c["mother"], c["child"])
        else:
            for pid, p in o.get("persons", {}).items():
                db.persons[pid] = Person(p.get("pid", pid), p.get("name",""), p.get("gender","unknown"),
                                         p.get("birth"), p.get("death"), p.get("note",""))
            for mid, m in o.get("marriages", {}).items():
                db.marriages[mid] = Marriage(m.get("mid", mid), m["a"], m["b"], m.get("status","married"), m.get("start"), m.get("end"))
            for cid, c in o.get("links", {}).items():
                db.links[cid] = ParentChild(c.get("cid", cid), c["parent"], c["child"])
        return db

    def to_json(self)->dict:
        return {
            "persons": {k: vars(v) for k,v in self.persons.items()},
            "marriages": {k: vars(v) for k,v in self.marriages.items()},
            "links": {k: vars(v) for k,v in self.links.items()},
        }

    def ensure_person(self, name: str, gender="unknown") -> str:
        # 以姓名查找現有人物；如無則建立
        for pid, p in self.persons.items():
            if p.name == name:
                return pid
        base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in name)
        pid = base; i = 1
        while pid in self.persons:
            i += 1; pid = f"{base}_{i}"
        self.persons[pid] = Person(pid, name, gender)
        return pid

def get_name_index(db: DB) -> Dict[str, str]:
    return {p.name: pid for pid, p in db.persons.items()}

# ----------------- 工具：層級與父母 -----------------
def compute_levels_and_parents(db: DB) -> Tuple[Dict[str,int], Dict[str,List[str]], Dict[str,List[str]]]:
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for l in db.links.values():
        parents_of[l.child].append(l.parent)
        children_of[l.parent].append(l.child)

    # 找 root（沒有父母的人）
    roots = [pid for pid in db.persons if not parents_of[pid]]
    if not roots and db.persons:
        roots = [next(iter(db.persons))]

    level = {pid:0 for pid in roots}
    q = deque(roots)
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            nv = level[u] + 1
            if v not in level or nv < level[v]:
                level[v] = nv
                q.append(v)
    for pid in db.persons:
        level.setdefault(pid, 0)
    return level, parents_of, children_of

def union_id(a: str, b: str) -> str:
    return f"u_{a}_{b}" if a < b else f"u_{b}_{a}"

# ----------------- 法定繼承（配偶置頂；僅直系卑親屬代位） -----------------
class InheritanceTW:
    def __init__(self, db: DB):
        self.db = db

    def heirs(self, decedent: str, dod: str):
        ddate = datetime.strptime(dod, "%Y-%m-%d").date()
        if decedent not in self.db.persons: 
            return pd.DataFrame(), "找不到被繼承人"

        spouses = self._spouses_alive(decedent, ddate)
        group, order_label = self._first_order_group(decedent, ddate)

        rows, other_rows = [], []
        spouse_share = 0.0

        if order_label == "第一順位":
            branches = self._desc_branches(decedent, ddate)
            unit = len(branches) + (1 if spouses else 0)
            spouse_share = (1 / unit) if spouses else 0
            for br in branches:
                for pid, frac in br.items():
                    p = self.db.persons[pid]
                    other_rows.append({"heir_id":pid, "name":p.name, "relation":"直系卑親屬",
                                       "share": round(frac * (1/unit), 6),
                                       "note": "" if pid in self._children_of(decedent) else "代位支分"})
        elif order_label in ("第二順位", "第三順位"):
            spouse_share = 0.5 if spouses else 0
            others = len(group); each = (1 - spouse_share)/others if others else 0
            for pid in group:
                p = self.db.persons[pid]
                other_rows.append({"heir_id":pid,"name":p.name,"relation":order_label,"share":round(each,6),"note":""})
        elif order_label == "第四順位":
            spouse_share = (2/3) if spouses else 0
            others = len(group); each = (1 - spouse_share)/others if others else 0
            for pid in group:
                p = self.db.persons[pid]
                other_rows.append({"heir_id":pid,"name":p.name,"relation":order_label,"share":round(each,6),"note":""})
        else:
            spouse_share = 1.0 if spouses else 0

        for sid in spouses:
            sp = self.db.persons[sid]
            rows.append({"heir_id":sid,"name":sp.name,"relation":"配偶","share":round(spouse_share,6),"note":""})
        rows.extend(other_rows)

        df = pd.DataFrame(rows)
        if not df.empty:
            df["__o__"] = df["relation"].apply(lambda r: 0 if r=="配偶" else 1)
            df = df.sort_values(by=["__o__","relation","name"]).drop(columns="__o__").reset_index(drop=True)

        memo = "；".join(filter(None, [f"血親順位：{order_label}" if order_label else "", "配偶為當然繼承人" if spouses else ""]))
        return df, memo

    # helpers
    def _spouses_alive(self, pid: str, d: date) -> List[str]:
        res = []
        for m in self.db.marriages.values():
            if pid in (m.a, m.b):
                other = m.b if pid==m.a else m.a
                if (m.end is None) or (datetime.strptime(m.end,"%Y-%m-%d").date() > d):
                    if self.db.persons.get(other) and self.db.persons[other].alive_on(d):
                        res.append(other)
        return list(dict.fromkeys(res))

    def _children_of(self, pid: str) -> List[str]:
        return [l.child for l in self.db.links.values() if l.parent==pid]

    def _parents_of(self, pid: str) -> List[str]:
        return [l.parent for l in self.db.links.values() if l.child==pid]

    def _siblings_alive(self, pid: str, d: date) -> List[str]:
        sibs=set()
        for p in self._parents_of(pid):
            for c in self._children_of(p):
                if c!=pid and self.db.persons[c].alive_on(d): sibs.add(c)
        return list(sibs)

    def _grandparents_alive(self, pid: str, d: date) -> List[str]:
        g=set()
        for p in self._parents_of(pid):
            for gp in self._parents_of(p):
                if self.db.persons[gp].alive_on(d): g.add(gp)
        return list(g)

    def _desc_branches(self, pid: str, d: date) -> List[Dict[str,float]]:
        branches=[]
        for c in self._children_of(pid):
            if self.db.persons[c].alive_on(d):
                branches.append({c:1.0})
            else:
                w=self._alive_desc_weights(c,d)
                if w: branches.append(w)
        return branches

    def _alive_desc_weights(self, pid: str, d: date) -> Dict[str,float]:
        kids=self._children_of(pid)
        alive=[k for k in kids if self.db.persons[k].alive_on(d)]
        if alive:
            w=1/len(alive)
            return {k:w for k in alive}
        res={}
        for k in kids:
            sub=self._alive_desc_weights(k,d)
            for p,w in sub.items():
                res[p]=res.get(p,0)+w/max(1,len(kids))
        return res

    def _first_order_group(self, pid: str, d: date) -> Tuple[List[str], str]:
        br = self._desc_branches(pid,d)
        if sum(len(x) for x in br) > 0:
            return list({p for b in br for p in b.keys()}), "第一順位"
        parents=self._parents_of(pid)
        parents_alive=[p for p in parents if self.db.persons[p].alive_on(d)]
        if parents_alive: return parents_alive, "第二順位"
        sibs=self._siblings_alive(pid,d)
        if sibs: return sibs, "第三順位"
        grands=self._grandparents_alive(pid,d)
        if grands: return grands, "第四順位"
        return [], ""

# ----------------- Graphviz 版家族樹（自家演算法） -----------------
def build_graphviz(db: DB) -> Digraph:
    levels, parents_of, children_of = compute_levels_and_parents(db)
    dot = Digraph(engine="dot")
    dot.attr(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="1.2")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#E8F0FE", color="#1D4ED8", fontname="Taipei Sans TC, Noto Sans CJK, Arial")

    # 依層級分 rank（同代同層）
    by_level = defaultdict(list)
    for pid in db.persons:
        by_level[levels.get(pid,0)].append(pid)
    for lvl in sorted(by_level.keys()):
        same = " ".join(by_level[lvl])
        if same:
            dot.body.append("{rank=same; " + same + "}")
    # 人物節點
    for pid, p in db.persons.items():
        dot.node(pid, label=p.name)

    # 夫妻水平線（實線/虛線）+ union node → 子女
    for m in db.marriages.values():
        a, b = m.a, m.b
        if a not in db.persons or b not in db.persons:
            continue
        style = "solid" if m.status == "married" else "dashed"
        # 夫妻連線（純視覺，無箭頭，不影響層級）
        dot.edge(a, b, dir="none", style=style, color="#2F5E73", constraint="false")
        # union node 置於兩人之間
        uid = union_id(a, b)
        dot.node(uid, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        dot.edge(a, uid, style="invis")  # 幫助定位
        dot.edge(b, uid, style="invis")
        # 從 union node 到孩子
        kids = sorted(set(children_of.get(a, [])) & set(children_of.get(b, [])))
        for c in kids:
            dot.edge(uid, c, dir="none", color="#2F5E73")

    # 單親→子女
    for child, parents in parents_of.items():
        if len(parents) == 1:
            dot.edge(parents[0], child, dir="none", color="#2F5E73")

    return dot

# ----------------- PyVis 備援（保留舊法） -----------------
def build_pyvis(db: DB) -> Network:
    levels, parents_of, children_of = compute_levels_and_parents(db)
    net = Network(height="720px", width="100%", directed=False, notebook=False)
    for pid, p in db.persons.items():
        net.add_node(pid, label=p.name, shape="box", level=levels.get(pid,0))
    for m in db.marriages.values():
        dashed = (m.status != "married")
        net.add_edge(m.a, m.b, dashes=dashed, physics=False, arrows="", color={"color":"#2f5e73","inherit":False}, smooth={"type":"horizontal"}, width=2)
    unions_done = set()
    for child, parents in parents_of.items():
        if len(parents) == 0:
            continue
        elif len(parents) == 1:
            par = parents[0]
            net.add_edge(par, child, arrows="to", color={"color":"#2f5e73","inherit":False}, width=2, smooth={"type":"cubicBezier","forceDirection":"vertical","roundness":0.0})
        else:
            a, b = sorted(parents)[:2]
            uid = union_id(a,b)
            if uid not in unions_done:
                net.add_node(uid, label="", shape="dot", size=1, physics=False)
                net.add_edge(a, uid, arrows="", color={"color":"#cfd8e3","inherit":False}, width=1, smooth={"type":"horizontal"}, physics=False)
                net.add_edge(b, uid, arrows="", color={"color":"#cfd8e3","inherit":False}, width=1, smooth={"type":"horizontal"}, physics=False)
                unions_done.add(uid)
            net.add_edge(uid, child, arrows="to", color={"color":"#2f5e73","inherit":False}, width=2, smooth={"type":"cubicBezier","forceDirection":"vertical","roundness":0.0})
    return net

# ----------------- UI -----------------
st.set_page_config(layout="wide", page_title="家族平台", page_icon="🌳")
st.title("🌳 家族平台（人物｜關係｜法定繼承｜家族樹）")

if "db" not in st.session_state:
    st.session_state.db = DB()

# ---- 側邊欄：資料維護 / 匯入匯出 ----
with st.sidebar:
    st.header("資料維護 / 匯入匯出")
    if st.button("🧪 一鍵載入示範：陳一郎家族"):
        demo = {
            "members": [
                {"id":"f1","name":"陳一郎","gender":"M"},
                {"id":"f2","name":"陳前妻","gender":"F"},
                {"id":"f3","name":"王子","gender":"M"},
                {"id":"f4","name":"王子妻","gender":"F"},
                {"id":"f5","name":"王孫","gender":"M"},
                {"id":"f6","name":"陳妻","gender":"F"},
                {"id":"f7","name":"陳大","gender":"M"},
                {"id":"f8","name":"陳二","gender":"M"},
                {"id":"f9","name":"陳三","gender":"M"}
            ],
            "marriages":[
                {"husband":"f1","wife":"f2","status":"divorced"},
                {"husband":"f3","wife":"f4","status":"married"},
                {"husband":"f1","wife":"f6","status":"married"}
            ],
            "children":[
                {"father":"f1","mother":"f2","child":"f3"},
                {"father":"f3","mother":"f4","child":"f5"},
                {"father":"f1","mother":"f6","child":"f7"},
                {"father":"f1","mother":"f6","child":"f8"},
                {"father":"f1","mother":"f6","child":"f9"}
            ]
        }
        st.session_state.db = DB.from_obj(demo)
        st.success("已載入示範資料"); st.rerun()

    up = st.file_uploader("匯入 JSON（members/children 或 persons/links）", type=["json"])
    if up:
        try:
            st.session_state.db = DB.from_obj(json.load(up))
            st.success("匯入成功"); st.rerun()
        except Exception as e:
            st.exception(e)

    # 匯出
    st.download_button("📥 下載 JSON 備份",
                       data=json.dumps(st.session_state.db.to_json(), ensure_ascii=False, indent=2),
                       file_name="family.json", mime="application/json")

# 重新綁定最新 DB
db: DB = st.session_state.db

# ---- 分頁 ----
tab1, tab2, tab3, tab4 = st.tabs(["👤 人物", "🔗 關係", "🧮 法定繼承試算", "🗺️ 家族樹"])

# --- Tab1 人物 ---
with tab1:
    st.subheader("人物維護（免 ID）")
    nm = st.text_input("姓名 *")
    gd = st.selectbox("性別", ["unknown","female","male"], index=0)
    if st.button("新增 / 覆蓋人物"):
        if not nm.strip():
            st.error("請輸入姓名")
        else:
            pid = db.ensure_person(nm.strip(), gd)
            st.success(f"已儲存人物：{nm}（ID: {pid}）")
    if db.persons:
        df = pd.DataFrame([{**vars(p)} for p in db.persons.values()])
        st.dataframe(df, use_container_width=True)

# --- Tab2 關係 ---
with tab2:
    st.subheader("婚姻 / 親子關係（用姓名選擇）")
    names = sorted([p.name for p in db.persons.values()])
    if not names:
        st.info("請先建立人物或一鍵載入示範資料。")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**婚姻**")
            a = st.selectbox("配偶 A", names, key="m_a")
            b = st.selectbox("配偶 B", names, key="m_b")
            stt = st.selectbox("狀態", ["married","divorced","widowed"])
            if st.button("建立/更新 婚姻"):
                if a == b:
                    st.error("同一個人不能和自己結婚")
                else:
                    a_id = db.ensure_person(a)
                    b_id = db.ensure_person(b)
                    mid = f"m_{a_id}_{b_id}"
                    db.marriages[mid] = Marriage(mid, a_id, b_id, stt)
                    st.success(f"婚姻已儲存：{a} - {b}（{stt}）")
        with c2:
            st.markdown("**親子**")
            par = st.selectbox("父/母", names, key="pc_p")
            chd = st.selectbox("子女", names, key="pc_c")
            if st.button("建立/更新 親子"):
                if par == chd:
                    st.error("同一個人不能同時是自己的父母與子女")
                else:
                    par_id = db.ensure_person(par)
                    chd_id = db.ensure_person(chd)
                    cid = f"c_{par_id}_{chd_id}"
                    db.links[cid] = ParentChild(cid, par_id, chd_id)
                    st.success(f"親子已儲存：{par} → {chd}")
        st.markdown("—")
        if db.marriages:
            st.dataframe(pd.DataFrame([{**vars(m)} for m in db.marriages.values()]))
        if db.links:
            st.dataframe(pd.DataFrame([{**vars(l)} for l in db.links.values()]))

# --- Tab3 法定繼承 ---
with tab3:
    st.subheader("法定繼承人試算（配偶優先；僅直系卑親屬代位）")
    if not db.persons:
        st.info("請先建立人物/關係或載入示範資料。")
    else:
        pick = st.selectbox("被繼承人", sorted([p.name for p in db.persons.values()]))
        dod = st.text_input("死亡日 YYYY-MM-DD", value=str(date.today()))
        if st.button("計算繼承人"):
            dec_id = get_name_index(db)[pick]
            rule = InheritanceTW(db)
            df, memo = rule.heirs(dec_id, dod)
            if df.empty:
                st.warning("無結果，請檢查資料")
            else:
                st.success(memo or "計算完成")
                st.dataframe(df, use_container_width=True)

# --- Tab4 家族樹 ---
with tab4:
    st.subheader("家族樹（夫妻水平線；離婚虛線；孩子由中點垂直）")
    if not db.persons:
        st.info("請先建立人物/關係或載入示範資料。")
    else:
        style = st.radio("呈現引擎", ["Graphviz（建議）","PyVis（備援）"], horizontal=True)
        if style.startswith("Graphviz"):
            dot = build_graphviz(db)
            st.graphviz_chart(dot)
            st.download_button("⬇️ 下載 DOT", data="\n".join(dot.body), file_name="family_tree.dot", mime="text/plain")
        else:
            net = build_pyvis(db)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                net.write_html(tmp.name, notebook=False)
                html = open(tmp.name, "r", encoding="utf-8").read()
            st.components.v1.html(html, height=780, scrolling=True)

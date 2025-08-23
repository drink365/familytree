# app.py — FamilyTree v7.4.0
# 重點：
# 1) 前任在左、本人在中、現任在右：以「左右錨點 + 高權重不可見邊」鎖死順序（即使 DOT 想重排也不會）
# 2) 子女一律從雙親連線中點垂直往下（離婚/喪偶=虛線；婚姻=實線）
# 3) 兄弟姊妹共用水平匯流線，減少重疊
# 4) 頁籤：人物｜關係｜法定繼承試算（簡化示範）｜家族樹（Graphviz / PyVis）

import json
from datetime import date, datetime
from collections import defaultdict
from typing import Dict, List, Tuple
import tempfile

import streamlit as st
import pandas as pd
from graphviz import Digraph
from pyvis.network import Network

VERSION = "v7.4.0"

# ----------------- Data Models -----------------
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None, note=""):
        self.pid, self.name, self.gender, self.birth, self.death, self.note = pid, name, gender, birth, death, note
    def alive_on(self, d: date) -> bool:
        if not self.death:
            return True
        try:
            return datetime.strptime(self.death, "%Y-%m-%d").date() > d
        except Exception:
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
    def from_obj(o) -> "DB":
        db = DB()
        # 支援兩種結構：members/children；或 persons/marriages/links
        if "members" in o:
            for m in o.get("members", []):
                db.persons[m["id"]] = Person(
                    m["id"], m["name"], m.get("gender", "unknown"),
                    m.get("birth"), m.get("death"), m.get("note", "")
                )
            for m in o.get("marriages", []):
                mid = m.get("id") or f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(
                    mid, m["husband"], m["wife"],
                    m.get("status", "married"), m.get("start"), m.get("end")
                )
            for c in o.get("children", []):
                if c.get("father"):
                    cid1 = f"c_{c['father']}_{c['child']}"
                    db.links[cid1] = ParentChild(cid1, c["father"], c["child"])
                if c.get("mother"):
                    cid2 = f"c_{c['mother']}_{c['child']}"
                    db.links[cid2] = ParentChild(cid2, c["mother"], c["child"])
        else:
            for pid, p in o.get("persons", {}).items():
                db.persons[pid] = Person(
                    p.get("pid", pid), p.get("name", ""), p.get("gender", "unknown"),
                    p.get("birth"), p.get("death"), p.get("note", "")
                )
            for mid, m in o.get("marriages", {}).items():
                db.marriages[mid] = Marriage(
                    m.get("mid", mid), m["a"], m["b"],
                    m.get("status", "married"), m.get("start"), m.get("end")
                )
            for cid, c in o.get("links", {}).items():
                db.links[cid] = ParentChild(c.get("cid", cid), c["parent"], c["child"])
        return db

    def to_json(self) -> dict:
        return {
            "persons": {k: vars(v) for k, v in self.persons.items()},
            "marriages": {k: vars(v) for k, v in self.marriages.items()},
            "links": {k: vars(v) for k, v in self.links.items()},
        }

    def ensure_person(self, name: str, gender="unknown") -> str:
        for pid, p in self.persons.items():
            if p.name == name:
                return pid
        base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in name)
        pid = base
        i = 1
        while pid in self.persons:
            i += 1
            pid = f"{base}_{i}"
        self.persons[pid] = Person(pid, name, gender)
        return pid

    def name_index(self) -> Dict[str, str]:
        return {p.name: pid for pid, p in self.persons.items()}

def union_id(a: str, b: str) -> str:
    return f"u_{a}_{b}" if a < b else f"u_{b}_{a}"

# ----------------- Leveling -----------------
def compute_levels_and_parents(db: DB) -> Tuple[Dict[str, int], Dict[str, List[str]], Dict[str, List[str]]]:
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for l in db.links.values():
        parents_of[l.child].append(l.parent)
        children_of[l.parent].append(l.child)

    memo: Dict[str, int] = {}
    def depth(pid: str) -> int:
        if pid in memo:
            return memo[pid]
        ps = parents_of.get(pid, [])
        if not ps:
            memo[pid] = 0
            return 0
        d = 1 + max(depth(p) for p in ps)
        memo[pid] = d
        return d

    level = {pid: depth(pid) for pid in db.persons}

    # 夫妻同層（拉齊至較高）
    changed = True
    while changed:
        changed = False
        for m in db.marriages.values():
            a, b = m.a, m.b
            if a not in level or b not in level:
                continue
            t = max(level[a], level[b])
            if level[a] != t or level[b] != t:
                level[a] = level[b] = t
                changed = True

    return level, parents_of, children_of

# ----------------- Graphviz tree -----------------
def build_graphviz(db: DB) -> Digraph:
    levels, parents_of, children_of = compute_levels_and_parents(db)

    dot = Digraph(engine="dot")
    # ordering="out" + 高權重不可見鏈 強制左右順序
    dot.attr(rankdir="TB", splines="ortho", nodesep="1.2", ranksep="1.6",
             compound="true", ordering="out")
    dot.attr(
        "node", shape="box", style="rounded,filled", fillcolor="#0f5b75",
        color="#0b3e52", fontcolor="white", penwidth="2",
        fontname="Taipei Sans TC, Noto Sans CJK, Arial", fontsize="14"
    )
    dot.attr("edge", color="#1a4b5f", penwidth="2")

    # 節點
    for pid, p in db.persons.items():
        dot.node(pid, label=p.name)

    # 同層（rank=same）
    by_level = defaultdict(list)
    for pid in db.persons:
        by_level[levels.get(pid, 0)].append(pid)
    for lvl in sorted(by_level.keys()):
        dot.body.append("{rank=same; " + " ".join(by_level[lvl]) + "}")

    # -------- 以「左右錨點 + 不可見高權重邊」鎖死：前任在左、本人中、現任在右 --------
    marriages_by_person = defaultdict(list)
    for mid, m in db.marriages.items():
        marriages_by_person[m.a].append((mid, m))
        marriages_by_person[m.b].append((mid, m))

    for pid, marrs in marriages_by_person.items():
        ex_list, cur_list = [], []
        for mid, m in marrs:
            spouse = m.b if pid == m.a else m.a
            (cur_list if m.status == "married" else ex_list).append(spouse)

        if ex_list and cur_list:
            # 依配偶 id 排序，避免非決定性順序
            ex_list  = sorted(set(ex_list))
            cur_list = sorted(set(cur_list))

            # 建立左右不可見錨點（同層）
            L = f"ancL_{pid}"
            R = f"ancR_{pid}"
            dot.node(L, label="", shape="point", width="0.01", height="0.01", style="invis")
            dot.node(R, label="", shape="point", width="0.01", height="0.01", style="invis")
            dot.body.append(f"{{rank=same; {L} {' '.join(ex_list)} {pid} {' '.join(cur_list)} {R}}}")

            # 以不可見高權重邊串成一條序列：L → ex... → 本人 → cur... → R
            chain = [L] + ex_list + [pid] + cur_list + [R]
            for a, b in zip(chain, chain[1:]):
                dot.edge(a, b, style="invis", weight="1000", minlen="1", constraint="true")
    # -------------------------------------------------------------------------

    # 兄弟姊妹匯流線（水平 rail）
    def add_sibling_rail(parent_a: str, parent_b: str, kids: List[str]):
        if not kids:
            return None
        rail_id = f"rail_{parent_a}_{parent_b}"
        dot.node(rail_id, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        for c in kids:
            dot.edge(rail_id, c, dir="none", tailport="s", headport="n", minlen="1")
        return rail_id

    # 婚姻與子女（孩子從雙親 union 中點往下；離婚=虛線）
    for m in db.marriages.values():
        a, b = m.a, m.b
        if a not in db.persons or b not in db.persons:
            continue
        style = "solid" if m.status == "married" else "dashed"
        uid = union_id(a, b)
        dot.node(uid, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        dot.body.append(f"{{rank=same; {a} {uid} {b}}}")
        dot.edge(a, uid, dir="none", style=style, weight="100", minlen="1")
        dot.edge(uid, b, dir="none", style=style, weight="100", minlen="1")

        kids = [c for c in children_of.get(a, []) if c in set(children_of.get(b, []))]
        kids = sorted(kids)
        if kids:
            rail = add_sibling_rail(a, b, kids)
            dot.edge(uid, rail, dir="none", tailport="s", headport="n", minlen="1")

    # 單親（只有一個父/母）
    for child, parents in parents_of.items():
        if len(parents) == 1:
            dot.edge(parents[0], child, dir="none", tailport="s", headport="n", minlen="1")

    return dot

# ----------------- PyVis (fallback) -----------------
def build_pyvis(db: DB) -> Network:
    import json as js
    levels, parents_of, children_of = compute_levels_and_parents(db)
    net = Network(height="720px", width="100%", directed=False, notebook=False)
    for pid, p in db.persons.items():
        net.add_node(pid, label=p.name, shape="box", level=levels.get(pid, 0))
    for m in db.marriages.values():
        dashed = (m.status != "married")
        net.add_edge(
            m.a, m.b, dashes=dashed, physics=False, arrows="",
            color={"color": "#2f5e73", "inherit": False},
            smooth={"type": "horizontal"}, width=2
        )
    unions = set()
    for child, parents in parents_of.items():
        if len(parents) == 1:
            par = parents[0]
            net.add_edge(
                par, child, arrows="to",
                color={"color": "#2f5e73", "inherit": False}, width=2,
                smooth={"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.0}
            )
        elif len(parents) >= 2:
            a, b = sorted(parents)[:2]
            uid = union_id(a, b)
            if uid not in unions:
                net.add_node(uid, label="", shape="dot", size=1, physics=False)
                net.add_edge(a, uid, arrows="", color={"color": "#cfd8e3", "inherit": False},
                             width=1, smooth={"type": "horizontal"}, physics=False)
                net.add_edge(b, uid, arrows="", color={"color": "#cfd8e3", "inherit": False},
                             width=1, smooth={"type": "horizontal"}, physics=False)
                unions.add(uid)
            net.add_edge(
                uid, child, arrows="to",
                color={"color": "#2f5e73", "inherit": False}, width=2,
                smooth={"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.0}
            )
    options = {
        "layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed"}},
        "physics": {"enabled": False},
        "edges": {"smooth": {"enabled": True, "type": "cubicBezier"}, "color": {"inherit": False}},
        "nodes": {"shape": "box"}
    }
    net.set_options(js.dumps(options))
    return net

# ----------------- UI -----------------
st.set_page_config(layout="wide", page_title=f"家族平台 {VERSION}", page_icon="🌳")
st.title(f"🌳 家族平台（人物｜關係｜法定繼承｜家族樹） — {VERSION}")

if "db" not in st.session_state:
    st.session_state.db = DB()

with st.sidebar:
    st.header("資料維護 / 匯入匯出")
    if st.button("🧪 一鍵載入示範：陳一郎家族"):
        demo = {
            "members": [
                {"id": "f1", "name": "陳一郎", "gender": "M"},
                {"id": "f2", "name": "陳前妻", "gender": "F"},
                {"id": "f3", "name": "王子", "gender": "M"},
                {"id": "f4", "name": "王子妻", "gender": "F"},
                {"id": "f5", "name": "王孫", "gender": "M"},
                {"id": "f6", "name": "陳妻", "gender": "F"},
                {"id": "f7", "name": "陳大", "gender": "M"},
                {"id": "f8", "name": "陳二", "gender": "M"},
                {"id": "f9", "name": "陳三", "gender": "M"}
            ],
            "marriages": [
                {"husband": "f1", "wife": "f2", "status": "divorced"},
                {"husband": "f3", "wife": "f4", "status": "married"},
                {"husband": "f1", "wife": "f6", "status": "married"}
            ],
            "children": [
                {"father": "f1", "mother": "f2", "child": "f3"},
                {"father": "f3", "mother": "f4", "child": "f5"},
                {"father": "f1", "mother": "f6", "child": "f7"},
                {"father": "f1", "mother": "f6", "child": "f8"},
                {"father": "f1", "mother": "f6", "child": "f9"}
            ]
        }
        st.session_state.db = DB.from_obj(demo)
        st.success("已載入示範資料")
        st.rerun()

    up = st.file_uploader("匯入 JSON（members/children 或 persons/links）", type=["json"])
    if up:
        try:
            st.session_state.db = DB.from_obj(json.load(up))
            st.success("匯入成功")
            st.rerun()
        except Exception as e:
            st.exception(e)

    st.download_button(
        "📥 下載 JSON 備份",
        data=json.dumps(st.session_state.db.to_json(), ensure_ascii=False, indent=2),
        file_name="family.json",
        mime="application/json"
    )

db: DB = st.session_state.db

tab1, tab2, tab3, tab4 = st.tabs(["👤 人物", "🔗 關係", "🧮 法定繼承試算", "🗺️ 家族樹"])

with tab1:
    st.subheader("人物維護（免 ID）")
    nm = st.text_input("姓名 *")
    gd = st.selectbox("性別", ["unknown", "female", "male"], index=0)
    if st.button("新增 / 覆蓋人物"):
        if not nm.strip():
            st.error("請輸入姓名")
        else:
            pid = db.ensure_person(nm.strip(), gd)
            st.success(f"已儲存人物：{nm}（ID: {pid}）")
    if db.persons:
        df = pd.DataFrame([{**vars(p)} for p in db.persons.values()])
        st.dataframe(df, use_container_width=True)

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
            stt = st.selectbox("狀態", ["married", "divorced", "widowed"])
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

with tab3:
    st.subheader("法定繼承人試算（配偶優先；僅直系卑親屬代位，簡化示範）")
    if not db.persons:
        st.info("請先建立人物/關係或載入示範資料。")
    else:
        pick = st.selectbox("被繼承人", sorted([p.name for p in db.persons.values()]))
        dod = st.text_input("死亡日 YYYY-MM-DD", value=str(date.today()))
        from datetime import datetime as _dt

        class InheritanceTW:
            def __init__(self, db: DB):
                self.db = db
            def heirs(self, decedent: str, dod: str):
                ddate = _dt.strptime(dod, "%Y-%m-%d").date()
                if decedent not in self.db.persons:
                    return pd.DataFrame(), "找不到被繼承人"
                def alive(pid): return self.db.persons[pid].alive_on(ddate)
                def children(pid): return [l.child for l in self.db.links.values() if l.parent == pid]
                def spouses(pid):
                    s = []
                    for m in self.db.marriages.values():
                        if pid in (m.a, m.b):
                            o = m.b if pid == m.a else m.a
                            if (m.end is None) or (_dt.strptime(m.end, "%Y-%m-%d").date() > ddate):
                                if alive(o):
                                    s.append(o)
                    return list(dict.fromkeys(s))
                sp = spouses(decedent)
                rows = []
                kids = children(decedent)
                if kids or sp:
                    unit = (1 if sp else 0) + (1 if kids else 0)
                    spouse_share = (1 / unit) if sp else 0
                    for sid in sp:
                        rows.append({"name": self.db.persons[sid].name, "relation": "配偶", "share": round(spouse_share, 6)})
                    if kids:
                        each = (1 - spouse_share) / len(kids) if len(kids) > 0 else 0
                        for k in kids:
                            rows.append({"name": self.db.persons[k].name, "relation": "直系卑親屬", "share": round(each, 6)})
                return pd.DataFrame(rows), ""
        rule = InheritanceTW(db)
        dec_id = db.name_index()[pick]
        df, memo = rule.heirs(dec_id, dod)
        if df.empty:
            st.warning("無結果，請檢查資料")
        else:
            st.success(memo or "計算完成")
            st.dataframe(df, use_container_width=True)

with tab4:
    st.subheader("家族樹（夫妻水平線；離婚虛線；孩子由中點垂直；前任左、現任右）")
    if not db.persons:
        st.info("請先建立人物/關係或載入示範資料。")
    else:
        style = st.radio("呈現引擎", ["Graphviz（建議）", "PyVis（備援）"], horizontal=True)
        if style.startswith("Graphviz"):
            st.graphviz_chart(build_graphviz(db))
        else:
            net = build_pyvis(db)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                net.write_html(tmp.name, notebook=False)
                html = open(tmp.name, "r", encoding="utf-8").read()
            st.components.v1.html(html, height=780, scrolling=True)

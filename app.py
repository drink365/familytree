# app.py（A版：心智圖風圓弧線 + 同代同層 + 匯入即時呈現 + 配偶置頂）
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import re
import tempfile
from collections import deque, defaultdict

import streamlit as st
import pandas as pd

# 依賴檢查
try:
    import networkx as nx
    from pyvis.network import Network
except ModuleNotFoundError as e:
    st.set_page_config(page_title="家族樹＋法定繼承人（TW）", page_icon="🌳", layout="wide")
    st.title("🌳 家族樹 + 法定繼承人（台灣民法・MVP）")
    st.error(
        f"❗ 缺少套件：{e.name}\n請確認 requirements.txt 並於 Manage app → App actions → Restart（建議 Python 3.11）。"
    )
    st.stop()

# ------------------ 工具 ------------------
def slugify(text: str) -> str:
    s = re.sub(r"\s+", "-", text.strip())
    s = re.sub(r"[^\w\-]", "", s)
    return s.lower() or "x"

def new_id(prefix: str, name: str, existed: set) -> str:
    base = f"{prefix}_{slugify(name)}"
    pid = base
    i = 1
    while pid in existed:
        i += 1
        pid = f"{base}-{i}"
    return pid

# ------------------ 資料模型 ------------------
class Person:
    def __init__(self, pid: str, name: str, gender: str = "unknown",
                 birth: Optional[str] = None, death: Optional[str] = None, note: str = ""):
        self.pid = pid
        self.name = name
        self.gender = gender
        self.birth = birth
        self.death = death
        self.note = note
    def alive_on(self, d: date) -> bool:
        if self.death:
            try:
                return datetime.strptime(self.death, "%Y-%m-%d").date() > d
            except Exception:
                return True
        return True

class Marriage:
    def __init__(self, mid: str, a: str, b: str, start: Optional[str] = None,
                 end: Optional[str] = None, status: str = "married"):
        self.mid = mid
        self.a = a
        self.b = b
        self.start = start
        self.end = end
        self.status = status

class ParentChild:
    def __init__(self, cid: str, parent: str, child: str):
        self.cid = cid
        self.parent = parent
        self.child = child

class FamilyDB:
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.marriages: Dict[str, Marriage] = {}
        self.links: Dict[str, ParentChild] = {}

    # 讓 UI 以「名字」為主（免 ID）
    def name_index(self) -> Dict[str, str]:
        return {p.name: pid for pid, p in self.persons.items()}

    def ensure_person_by_name(self, name: str, gender: str = "unknown") -> str:
        idx = self.name_index()
        if name in idx:
            return idx[name]
        pid = new_id("p", name, set(self.persons.keys()))
        self.persons[pid] = Person(pid, name, gender)
        return pid

    # CRUD
    def upsert_person(self, p: Person):
        self.persons[p.pid] = p
    def upsert_marriage(self, m: Marriage):
        self.marriages[m.mid] = m
    def upsert_link(self, pc: ParentChild):
        self.links[pc.cid] = pc

    # 關係
    def children_of(self, pid: str) -> List[str]:
        return [pc.child for pc in self.links.values() if pc.parent == pid]
    def parents_of(self, pid: str) -> List[str]:
        return [pc.parent for pc in self.links.values() if pc.child == pid]
    def spouses_of(self, pid: str, at: Optional[date] = None) -> List[str]:
        res = []
        for m in self.marriages.values():
            if pid in (m.a, m.b):
                other = m.b if pid == m.a else m.a
                if not at:
                    res.append(other)
                else:
                    if (not m.end) or (datetime.strptime(m.end, "%Y-%m-%d").date() > at):
                        res.append(other)
        return list(dict.fromkeys(res))

    # 匯入匯出
    def to_json(self) -> dict:
        return {
            "persons": {pid: p.__dict__ for pid, p in self.persons.items()},
            "marriages": {mid: m.__dict__ for mid, m in self.marriages.items()},
            "links": {cid: l.__dict__ for cid, l in self.links.items()},
        }
    @staticmethod
    def from_obj(obj) -> "FamilyDB":
        db = FamilyDB()
        if isinstance(obj, list):
            for item in obj:
                if not isinstance(item, dict): continue
                t = item.get("type") or item.get("_type")
                if t == "person":
                    p = Person(**{k: item.get(k) for k in ["pid","name","gender","birth","death","note"] if k in item})
                    if not p.pid: p.pid = new_id("p", p.name or "未知", set(db.persons.keys()))
                    db.upsert_person(p)
                elif t in ("marriage","spouse"):
                    a = item.get("a") or item.get("p1"); b = item.get("b") or item.get("p2")
                    if not a or not b: continue
                    mid = item.get("mid") or new_id("m", f"{a}-{b}", set(db.marriages.keys()))
                    m = Marriage(mid, a, b, item.get("start"), item.get("end"), item.get("status","married"))
                    db.upsert_marriage(m)
                elif t in ("parent_child","parent-child","pc","link"):
                    par = item.get("parent"); ch = item.get("child")
                    if not par or not ch: continue
                    cid = item.get("cid") or new_id("c", f"{par}-{ch}", set(db.links.keys()))
                    db.upsert_link(ParentChild(cid, par, ch))
            return db

        persons = obj.get("persons", {})
        if isinstance(persons, list):
            persons = { (p.get("pid") or new_id("p", p.get("name","未知"), set())).strip(): p for p in persons }  # type: ignore
        for pid, pobj in persons.items():
            p = Person(**pobj);  p.pid = p.pid or pid
            db.upsert_person(p)

        marriages = obj.get("marriages", {})
        if isinstance(marriages, list):
            marriages = { (m.get("mid") or new_id("m", f"{m.get('a')}-{m.get('b')}", set())).strip(): m for m in marriages }  # type: ignore
        for mid, mobj in marriages.items():
            m = Marriage(**mobj); m.mid = m.mid or mid
            db.upsert_marriage(m)

        links = obj.get("links", {})
        if isinstance(links, list):
            links = { (l.get("cid") or new_id("c", f"{l.get('parent')}-{l.get('child')}", set())).strip(): l for l in links }  # type: ignore
        for cid, cobj in links.items():
            l = ParentChild(**cobj); l.cid = l.cid or cid
            db.upsert_link(l)
        return db

# ------------------ 台灣民法（僅直系卑親屬代位；配偶優先顯示） ------------------
class InheritanceRuleTW:
    def __init__(self, db: FamilyDB):
        self.db = db

    def get_heirs(self, decedent_id: str, dod: str):
        ddate = datetime.strptime(dod, "%Y-%m-%d").date()
        if decedent_id not in self.db.persons:
            return pd.DataFrame(), "找不到被繼承人"

        spouses = self.db.spouses_of(decedent_id, at=ddate)
        spouses_alive = [sid for sid in spouses if self.db.persons.get(sid) and self.db.persons[sid].alive_on(ddate)]

        group, relation_label = self._find_first_order_group(decedent_id, ddate)

        rows, note = [], []
        if not group and not spouses_alive:
            return pd.DataFrame(columns=["heir_id", "name", "relation", "share", "note"]), "查無繼承人"

        spouse_share = 0.0
        other_rows = []

        if relation_label == "第一順位":
            branches = self._descendant_branches(decedent_id, ddate)
            unit = len(branches) + (1 if spouses_alive else 0)
            spouse_share = (1 / unit) if spouses_alive else 0
            for branch in branches:
                for pid, frac in branch.items():
                    p = self.db.persons[pid]
                    other_rows.append({"heir_id": pid, "name": p.name, "relation": "直系卑親屬",
                                       "share": round(frac * (1 / unit), 6),
                                       "note": "代位支分" if pid not in self.db.children_of(decedent_id) else ""})
        elif relation_label in ("第二順位", "第三順位"):
            spouse_share = 0.5 if spouses_alive else 0
            others = len(group)
            each = (1 - spouse_share) / others if others > 0 else 0
            for pid in group:
                p = self.db.persons[pid]
                other_rows.append({"heir_id": pid, "name": p.name, "relation": relation_label,
                                   "share": round(each, 6), "note": ""})
        elif relation_label == "第四順位":
            spouse_share = (2 / 3) if spouses_alive else 0
            others = len(group)
            each = (1 - spouse_share) / others if others > 0 else 0
            for pid in group:
                p = self.db.persons[pid]
                other_rows.append({"heir_id": pid, "name": p.name, "relation": relation_label,
                                   "share": round(each, 6), "note": ""})
        else:
            spouse_share = 1.0 if spouses_alive else 0

        # 先放配偶（置頂），再放其他繼承人
        for sid in spouses_alive:
            sp = self.db.persons[sid]
            rows.append({"heir_id": sid, "name": sp.name, "relation": "配偶",
                         "share": round(spouse_share, 6), "note": ""})
        rows.extend(other_rows)

        df = pd.DataFrame(rows)
        if not df.empty:
            df["__ord__"] = df["relation"].apply(lambda r: 0 if r == "配偶" else 1)
            df = df.sort_values(by=["__ord__", "relation", "name"]).drop(columns="__ord__").reset_index(drop=True)

        if relation_label:
            note.append(f"血親順位：{relation_label}")
        if spouses_alive:
            note.append("配偶為當然繼承人（依民法）")
        return df, "；".join(note)

    def _find_first_order_group(self, decedent_id: str, ddate: date):
        branches = self._descendant_branches(decedent_id, ddate)
        if sum(len(b) for b in branches) > 0:
            return list({pid for b in branches for pid in b.keys()}), "第一順位"
        parents = [pid for pid in self.db.parents_of(decedent_id) if self.db.persons[pid].alive_on(ddate)]
        if parents:
            return parents, "第二順位"
        sibs = self._siblings_alive(decedent_id, ddate)
        if sibs:
            return sibs, "第三順位"
        grands = self._grandparents_alive(decedent_id, ddate)
        if grands:
            return grands, "第四順位"
        return [], ""

    def _descendant_branches(self, decedent_id: str, ddate: date):
        children = self.db.children_of(decedent_id)
        branches = []
        for c in children:
            if self.db.persons[c].alive_on(ddate):
                branches.append({c: 1.0})
            else:
                sub = self._alive_descendants_weights(c, ddate)
                if sub:
                    branches.append(sub)
        return branches

    def _alive_descendants_weights(self, pid: str, ddate: date):
        kids = self.db.children_of(pid)
        alive = [k for k in kids if self.db.persons[k].alive_on(ddate)]
        if alive:
            w = 1 / len(alive)
            return {k: w for k in alive}
        result = {}
        for k in kids:
            sub = self._alive_descendants_weights(k, ddate)
            for p, w in sub.items():
                result[p] = result.get(p, 0) + w / max(1, len(kids))
        return result

    def _siblings_alive(self, decedent_id: str, ddate: date):
        parents = self.db.parents_of(decedent_id)
        sibs = set()
        for par in parents:
            for c in self.db.children_of(par):
                if c != decedent_id and self.db.persons[c].alive_on(ddate):
                    sibs.add(c)
        return list(sibs)

    def _grandparents_alive(self, decedent_id: str, ddate: date):
        grands = set()
        for p in self.db.parents_of(decedent_id):
            for gp in self.db.parents_of(p):
                if self.db.persons[gp].alive_on(ddate):
                    grands.add(gp)
        return list(grands)

# ------------------ 世代分層：計算每個人的 level（同代同層） ------------------
def compute_generations(db: 'FamilyDB'):
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for pc in db.links.values():
        parents_of[pc.child].append(pc.parent)
        children_of[pc.parent].append(pc.child)

    roots = [pid for pid in db.persons.keys() if len(parents_of[pid]) == 0]
    level = {pid: 0 for pid in roots}

    q = deque(roots)
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            lv = level.get(v, None)
            nv = level[u] + 1
            if lv is None or nv < lv:
                level[v] = nv
                q.append(v)

    for pid in db.persons.keys():
        if pid not in level:
            level[pid] = 0
    return level

# ------------------ UI（含 session_state 持久） ------------------
st.set_page_config(page_title="家族樹＋法定繼承人（TW）", page_icon="🌳", layout="wide")

if "db" not in st.session_state:
    st.session_state.db = FamilyDB()
db: FamilyDB = st.session_state.db

st.title("🌳 家族樹 + 法定繼承人（台灣民法・簡化輸入版）")

with st.sidebar:
    st.header("資料維護 / 匯入匯出 / 診斷")

    p_cnt = len(db.persons); m_cnt = len(db.marriages); l_cnt = len(db.links)
    st.info(f"目前資料：人物 {p_cnt}｜婚姻 {m_cnt}｜親子 {l_cnt}")

    if st.button("🧪 一鍵載入示範資料"):
        demo = {
            "persons": {
                "p1": {"pid":"p1","name":"爸爸","gender":"male"},
                "p2": {"pid":"p2","name":"媽媽","gender":"female"},
                "p3": {"pid":"p3","name":"大兒子","gender":"male"},
                "p4": {"pid":"p4","name":"小兒子","gender":"male"},
                "p5": {"pid":"p5","name":"女兒","gender":"female"}
            },
            "marriages": {
                "m1": {"mid":"m1","a":"p1","b":"p2","start":None,"end":None,"status":"married"}
            },
            "links": {
                "c1":{"cid":"c1","parent":"p1","child":"p3"},
                "c2":{"cid":"c2","parent":"p2","child":"p3"},
                "c3":{"cid":"c3","parent":"p1","child":"p4"},
                "c4":{"cid":"c4","parent":"p2","child":"p4"},
                "c5":{"cid":"c5","parent":"p1","child":"p5"},
                "c6":{"cid":"c6","parent":"p2","child":"p5"}
            }
        }
        st.session_state.db = FamilyDB.from_obj(demo)
        st.success("✅ 已載入示範資料")

    up = st.file_uploader("匯入 JSON（family.json 或 list 版）", type=["json"], accept_multiple_files=False)
    if up is not None:
        try:
            obj = json.load(up)
            st.session_state.db = FamilyDB.from_obj(obj)
            st.success(f"✅ 已匯入：{up.name}（不需重啟，頁面已更新）")
        except Exception as e:
            st.exception(e)

    exp = json.dumps(db.to_json(), ensure_ascii=False, indent=2)
    st.download_button("📥 下載 JSON 備份", data=exp, file_name="family.json", mime="application/json")
    st.caption("提示：重新部署/Restart 會清空記憶體，請常用『下載 JSON 備份』保存。")

tab1, tab2, tab3, tab4 = st.tabs(["👤 人物（免ID）", "🔗 關係（選名字）", "🧮 法定繼承試算（配偶置頂）", "🗺️ 家族樹（心智圖風圓弧線）"])

# --- Tab1：人物 ---
with tab1:
    st.subheader("新增人物（免ID）")
    name = st.text_input("姓名 *")
    gender = st.selectbox("性別", ["unknown", "female", "male"], index=0)
    birth = st.text_input("出生日 YYYY-MM-DD（可空）", value="")
    death = st.text_input("死亡日 YYYY-MM-DD（可空）", value="")
    note = st.text_area("備註（可空）", value="")
    if st.button("➕ 新增 / 覆蓋人物", type="primary"):
        if not name.strip():
            st.error("請輸入姓名")
        else:
            idx = db.name_index()
            if name in idx:
                pid = idx[name]
            else:
                pid = new_id("p", name, set(db.persons.keys()))
            db.upsert_person(Person(pid, name.strip(), gender, birth or None, death or None, note))
            st.success(f"已儲存人物：{name}（ID: {pid}）")

    st.markdown("—")
    if db.persons:
        st.markdown("**人物清單（只讀）**")
        st.dataframe(pd.DataFrame([{**vars(p)} for p in db.persons.values()]))

# --- Tab2：關係（婚姻/親子）---
with tab2:
    st.subheader("婚姻/伴侶關係（選名字，不用ID）")
    all_names = sorted(list(db.name_index().keys()))
    colA, colB = st.columns(2)
    with colA:
        a_name = st.selectbox("配偶 A（既有人物）", options=all_names + ["（輸入新名字）"])
        b_name = st.selectbox("配偶 B（既有人物）", options=all_names + ["（輸入新名字）"])
        new_a = new_b = ""
        if a_name == "（輸入新名字）":
            new_a = st.text_input("輸入新名字（A）")
        if b_name == "（輸入新名字）":
            new_b = st.text_input("輸入新名字（B）")
        mstart = st.text_input("結婚日 YYYY-MM-DD（可空）")
        mend = st.text_input("婚姻結束日 YYYY-MM-DD（可空）")
        status = st.selectbox("狀態", ["married", "divorced", "widowed"])
        if st.button("➕ 建立/更新 婚姻"):
            if a_name == "（輸入新名字）":
                if not new_a.strip():
                    st.error("請輸入 A 的新名字"); st.stop()
                a_pid = db.ensure_person_by_name(new_a.strip())
            else:
                a_pid = db.ensure_person_by_name(a_name)
            if b_name == "（輸入新名字）":
                if not new_b.strip():
                    st.error("請輸入 B 的新名字"); st.stop()
                b_pid = db.ensure_person_by_name(new_b.strip())
            else:
                b_pid = db.ensure_person_by_name(b_name)
            if a_pid == b_pid:
                st.error("同一個人不能和自己結婚")
            else:
                mid = new_id("m", f"{db.persons[a_pid].name}-{db.persons[b_pid].name}", set(db.marriages.keys()))
                db.upsert_marriage(Marriage(mid, a_pid, b_pid, mstart or None, mend or None, status))
                st.success(f"已儲存婚姻：{db.persons[a_pid].name} － {db.persons[b_pid].name}（ID: {mid}）")

    with colB:
        st.subheader("親子關係（選名字，不用ID）")
        parent_name = st.selectbox("父/母（既有人物）", options=all_names + ["（輸入新名字）"], key="parent_sel")
        child_name = st.selectbox("子女（既有人物）", options=all_names + ["（輸入新名字）"], key="child_sel")
        new_parent = new_child = ""
        if parent_name == "（輸入新名字）":
            new_parent = st.text_input("輸入新名字（父/母）")
        if child_name == "（輸入新名字）":
            new_child = st.text_input("輸入新名字（子女）")
        if st.button("➕ 建立/更新 親子"):
            if parent_name == "（輸入新名字）":
                if not new_parent.strip():
                    st.error("請輸入父/母的新名字"); st.stop()
                parent_pid = db.ensure_person_by_name(new_parent.strip())
            else:
                parent_pid = db.ensure_person_by_name(parent_name)
            if child_name == "（輸入新名字）":
                if not new_child.strip():
                    st.error("請輸入子女的新名字"); st.stop()
                child_pid = db.ensure_person_by_name(new_child.strip())
            else:
                child_pid = db.ensure_person_by_name(child_name)
            if parent_pid == child_pid:
                st.error("同一個人不能同時是自己的父母與子女")
            else:
                cid = new_id("c", f"{db.persons[parent_pid].name}-{db.persons[child_pid].name}", set(db.links.keys()))
                db.upsert_link(ParentChild(cid, parent_pid, child_pid))
                st.success(f"已儲存親子：{db.persons[parent_pid].name} → {db.persons[child_pid].name}（ID: {cid}）")

    st.markdown("—")
    if db.marriages:
        st.markdown("**婚姻/伴侶清單（只讀）**")
        st.dataframe(pd.DataFrame([{**vars(m)} for m in db.marriages.values()]))
    if db.links:
        st.markdown("**親子清單（只讀）**")
        st.dataframe(pd.DataFrame([{**vars(l)} for l in db.links.values()]))

# --- Tab3：法定繼承（配偶置頂）---
with tab3:
    st.subheader("法定繼承人試算（僅直系卑親屬代位；配偶排第一）")
    names = list(db.name_index().keys())
    if not names:
        st.info("請先在前兩個分頁新增人物與關係，或在側邊欄按『一鍵載入示範資料』。")
    else:
        pick_name = st.selectbox("被繼承人（選名字）", options=sorted(names))
        dod = st.text_input("死亡日 YYYY-MM-DD", value=str(date.today()))
        if st.button("計算繼承人"):
            decedent_id = db.name_index()[pick_name]
            rule = InheritanceRuleTW(db)
            df, memo = rule.get_heirs(decedent_id, dod)
            if df.empty:
                st.warning("無結果，請檢查資料。")
            else:
                st.success(memo or "計算完成（配偶置頂顯示）")
                st.dataframe(df)

# --- Tab4：家族樹（心智圖圓弧 + 同代同層；婚姻不影響佈局）---
with tab4:
    st.subheader("家族樹（心智圖風圓弧線，同代同層，自上而下）")
    if not db.persons:
        st.info("尚無資料。請先建立人物/關係或在側邊欄按『一鍵載入示範資料』。")
    else:
        levels = compute_generations(db)
        G_layout = nx.DiGraph()
        for p in db.persons.values():
            label = p.name
            if p.birth: label += f"\\n*{p.birth}"
            if p.death: label += f"\\n✝ {p.death}"
            G_layout.add_node(p.pid, label=label, shape="box", level=levels.get(p.pid, 0))
        for pc in db.links.values():
            G_layout.add_edge(pc.parent, pc.child, relation="parent")

        net = Network(height="650px", width="100%", directed=True, notebook=False)
        net.from_nx(G_layout)

        import json as js
        options = {
            "layout": {
                "hierarchical": {
                    "enabled": True,
                    "direction": "UD",
                    "levelSeparation": 160,
                    "nodeSpacing": 220,
                    "treeSpacing": 260,
                    "sortMethod": "hubsize",
                    "blockShifting": False,
                    "edgeMinimization": False,
                    "parentCentralization": True
                }
            },
            "physics": {"enabled": False},
            "edges": {
                "smooth": {
                    "enabled": True,
                    "type": "cubicBezier",
                    "forceDirection": "vertical",
                    "roundness": 0.6
                },
                "color": {"inherit": False, "color": "#5b7bb3"},
                "width": 2,
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}
            },
            "nodes": {
                "shape": "box",
                "borderWidth": 1,
                "color": {"background": "#dce9ff", "border": "#8aa8d6"},
                "font": {"size": 14}
            }
        }
        net.set_options(js.dumps(options))

        # 婚姻：虛線，不影響層級
        for m in db.marriages.values():
            a, b = m.a, m.b
            if a in db.persons and b in db.persons:
                net.add_edge(a, b, dashes=True, physics=False, arrows='', color={"color": "#999", "inherit": False})

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.write_html(tmp.name, notebook=False)
            html = open(tmp.name, "r", encoding="utf-8").read()

        left, right = st.columns([3, 2], gap="large")
        with left:
            st.components.v1.html(html, height=720, scrolling=True)

        with right:
            st.markdown("### ⚡ 快速新增 / 修改")
            all_names = sorted(list(db.name_index().keys()))

            with st.expander("➕ 新增人物"):
                nm = st.text_input("姓名", key="q_add_name_v2")
                gd = st.selectbox("性別", ["unknown", "female", "male"], index=0, key="q_add_gender_v2")
                if st.button("新增人物", key="q_add_person_btn_v2"):
                    if not nm.strip():
                        st.error("請輸入姓名")
                    else:
                        pid = db.ensure_person_by_name(nm.strip(), gd)
                        st.success(f"已新增：{nm}（ID: {pid}）")

            with st.expander("❤️ 新增配偶關係"):
                a = st.selectbox("配偶 A（選名字）", options=all_names, key="q_m_a_v2")
                b = st.selectbox("配偶 B（選名字）", options=all_names, key="q_m_b_v2")
                st_dt = st.text_input("結婚日 YYYY-MM-DD（可空）", key="q_m_start_v2")
                en_dt = st.text_input("婚姻結束日 YYYY-MM-DD（可空）", key="q_m_end_v2")
                stt = st.selectbox("狀態", ["married", "divorced", "widowed"], key="q_m_status_v2")
                if st.button("建立/更新 婚姻", key="q_m_btn_v2"):
                    if a == b:
                        st.error("同一個人不能和自己結婚")
                    else:
                        a_id = db.ensure_person_by_name(a)
                        b_id = db.ensure_person_by_name(b)
                        mid = new_id("m", f"{a}-{b}", set(db.marriages.keys()))
                        db.upsert_marriage(Marriage(mid, a_id, b_id, st_dt or None, en_dt or None, stt))
                        st.success(f"已儲存婚姻：{a} - {b}（ID: {mid}）")

            with st.expander("👶 新增親子關係"):
                par = st.selectbox("父/母（選名字）", options=all_names, key="q_c_parent_v2")
                chd = st.selectbox("子女（選名字）", options=all_names, key="q_c_child_v2")
                if st.button("建立/更新 親子", key="q_c_btn_v2"):
                    if par == chd:
                        st.error("同一個人不能同時是自己的父母與子女")
                    else:
                        par_id = db.ensure_person_by_name(par)
                        chd_id = db.ensure_person_by_name(chd)
                        cid = new_id("c", f"{par}-{chd}", set(db.links.keys()))
                        db.upsert_link(ParentChild(cid, par_id, chd_id))
                        st.success(f"已儲存親子：{par} → {chd}（ID: {cid}）")

# app.py — FamilyTree v7.6.4 (strict ordering)
# 重點：
# - 同層嚴格排序：前任(全部) → 本人 → 現任 → 其他同層人員
# - 夫妻同層水平線；離婚/喪偶虛線；孩子由「夫妻中點」垂直往下
# - 分頁：人物｜關係｜法定繼承試算｜家族樹
# - 一鍵載入「陳一郎家族」示範
# - 免系統 graphviz：自帶 DOT builder；以 st.graphviz_chart 顯示

import json
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List

import streamlit as st
import pandas as pd

VERSION = "7.6.4"

# ---------------- DOT builder ----------------
def _fmt_attrs(d: dict) -> str:
    if not d:
        return ""
    parts = []
    for k, v in d.items():
        if isinstance(v, bool):
            parts.append(f'{k}={"true" if v else "false"}')
        elif isinstance(v, (int, float)):
            parts.append(f"{k}={v}")
        else:
            sv = str(v).replace('"', r"\\\"")
            parts.append(f'{k}="{sv}"')
    return " [" + ", ".join(parts) + "]"

class DotBuilder:
    def __init__(self, directed: bool = True):
        self.directed = directed
        self.graph_attrs, self.node_defaults, self.edge_defaults = {}, {}, {}
        self.nodes = {}
        self.edges = []
        self.extra = []

    def attr(self, kind=None, **kwargs):
        if kind == "node":
            self.node_defaults.update(kwargs)
        elif kind == "edge":
            self.edge_defaults.update(kwargs)
        else:
            self.graph_attrs.update(kwargs)

    def node(self, nid: str, label: str = "", **attrs):
        if nid not in self.nodes:
            self.nodes[nid] = {}
        if label:
            self.nodes[nid]["label"] = label
        self.nodes[nid].update(attrs)

    def edge(self, a: str, b: str, **attrs):
        self.edges.append((a, b, dict(attrs)))

    @property
    def source(self) -> str:
        gtype = "digraph" if self.directed else "graph"
        edgeop = "->" if self.directed else "--"
        out = [f"{gtype} G {{"]

        if self.graph_attrs: out.append("  graph" + _fmt_attrs(self.graph_attrs) + ";")
        if self.node_defaults: out.append("  node" + _fmt_attrs(self.node_defaults) + ";")
        if self.edge_defaults: out.append("  edge" + _fmt_attrs(self.edge_defaults) + ";")

        for nid, attrs in self.nodes.items():
            out.append(f'  "{nid}"' + _fmt_attrs(attrs) + ";")
        for raw in self.extra:
            out.append("  " + raw)
        for a, b, attrs in self.edges:
            out.append(f'  "{a}" {edgeop} "{b}"' + _fmt_attrs(attrs) + ";")

        out.append("}")
        return "\n".join(out)

# ---------------- Data model ----------------
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None, note=""):
        self.pid, self.name, self.gender = pid, name, gender
        self.birth, self.death, self.note = birth, death, note

    def alive_on(self, d: date) -> bool:
        if not self.death:
            return True
        try:
            return datetime.strptime(self.death, "%Y-%m-%d").date() > d
        except Exception:
            return True

class Marriage:
    def __init__(self, mid, a, b, status="married", start=None, end=None):
        self.mid, self.a, self.b = mid, a, b
        self.status, self.start, self.end = status, start, end

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
        if "members" in o:  # A 格式
            for m in o.get("members", []):
                db.persons[m["id"]] = Person(
                    m["id"], m["name"], m.get("gender", "unknown"),
                    m.get("birth"), m.get("death"), m.get("note", "")
                )
            for m in o.get("marriages", []):
                mid = m.get("id") or f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(
                    mid, m["husband"], m["wife"], m.get("status", "married"),
                    m.get("start"), m.get("end")
                )
            for c in o.get("children", []):
                if c.get("father"):
                    cid = f"c_{c['father']}_{c['child']}"
                    db.links[cid] = ParentChild(cid, c["father"], c["child"])
                if c.get("mother"):
                    cid = f"c_{c['mother']}_{c['child']}"
                    db.links[cid] = ParentChild(cid, c["mother"], c["child"])
        else:  # B 格式
            for pid, p in o.get("persons", {}).items():
                db.persons[pid] = Person(
                    pid, p.get("name",""), p.get("gender","unknown"),
                    p.get("birth"), p.get("death"), p.get("note","")
                )
            for mid, m in o.get("marriages", {}).items():
                db.marriages[mid] = Marriage(
                    mid, m["a"], m["b"], m.get("status","married"),
                    m.get("start"), m.get("end")
                )
            for cid, c in o.get("links", {}).items():
                db.links[cid] = ParentChild(cid, c["parent"], c["child"])
        return db

    def ensure_person(self, name: str, gender="unknown") -> str:
        for pid, p in self.persons.items():
            if p.name == name:
                return pid
        base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in name)
        pid = base; i = 1
        while pid in self.persons:
            i += 1; pid = f"{base}_{i}"
        self.persons[pid] = Person(pid, name, gender)
        return pid

    def name_index(self) -> Dict[str,str]:
        return {p.name: pid for pid, p in self.persons.items()}

    def to_json(self) -> dict:
        return {
            "persons": {k: vars(v) for k, v in self.persons.items()},
            "marriages": {k: vars(v) for k, v in self.marriages.items()},
            "links": {k: vars(v) for k, v in self.links.items()},
        }

def union_id(a:str,b:str)->str:
    return f"u_{a}_{b}" if a<b else f"u_{b}_{a}"

# ---------------- 層級計算 ----------------
def compute_levels_and_maps(db: DB):
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for l in db.links.values():
        parents_of[l.child].append(l.parent)
        children_of[l.parent].append(l.child)

    memo = {}
    def depth(pid: str) -> int:
        if pid in memo: return memo[pid]
        ps = parents_of.get(pid, [])
        memo[pid] = 0 if not ps else 1 + max(depth(p) for p in ps)
        return memo[pid]

    level = {pid: depth(pid) for pid in db.persons}

    # 夫妻同層
    changed = True
    while changed:
        changed = False
        for m in db.marriages.values():
            a, b = m.a, m.b
            if a in level and b in level:
                t = max(level[a], level[b])
                if level[a]!=t or level[b]!=t:
                    level[a]=level[b]=t; changed = True
    return level, parents_of, children_of

# ---------------- 嚴格同層排序 ----------------
def strict_order_by_level(level_nodes: List[str], lvl: int, level: Dict[str,int],
                          current_of: Dict[str,str], ex_of: Dict[str,List[str]]) -> List[str]:
    """
    先放「有現任的人」的區塊（前任 → 本人 → 現任），再放其他同層。
    這會保證「前任在最左、本人在中、現任在右」，且整個區塊在同層最前方。
    """
    placed = set()
    ordered: List[str] = []

    # 先取 pivots（有現任且現任同層），避免被前任搶先
    pivots = []
    seen_couple = set()
    for pid in sorted(level_nodes):
        cur = current_of.get(pid)
        if not cur or level.get(cur, -1) != lvl:
            continue
        couple_key = tuple(sorted([pid, cur]))
        if couple_key in seen_couple:
            continue
        seen_couple.add(couple_key)
        pivots.append(pid)

    # 所有 pivot 區塊先排（確保在最左側）
    for pid in sorted(pivots):
        # 前任（同層）→ 本人 → 現任
        ex_same = [x for x in ex_of.get(pid, []) if level.get(x, -1) == lvl]
        ex_same = sorted(set(ex_same))
        block = ex_same + [pid]
        cur = current_of.get(pid)
        if cur and level.get(cur, -1) == lvl:
            block += [cur]
        for x in block:
            if x not in placed:
                ordered.append(x); placed.add(x)

    # 其餘同層（沒有現任者、只有前任者、單身等）
    for pid in sorted(level_nodes):
        if pid in placed:
            continue
        ex_same = [x for x in ex_of.get(pid, []) if level.get(x, -1) == lvl]
        ex_same = sorted(set(ex_same))
        block = ex_same + [pid]
        cur = current_of.get(pid)
        if cur and level.get(cur, -1) == lvl and cur not in placed:
            block += [cur]
        for x in block:
            if x not in placed:
                ordered.append(x); placed.add(x)

    return ordered

# ---------------- 繪製家族樹 ----------------
def build_graphviz_source(db: DB) -> str:
    level, parents_of, children_of = compute_levels_and_maps(db)

    dot = DotBuilder(directed=True)
    dot.attr(rankdir="TB", splines="ortho", nodesep="1.2", ranksep="1.6",
             compound=True, ordering="out")
    dot.attr("node", shape="box", style="rounded,filled",
             fillcolor="#0f5b75", color="#0b3e52",
             fontcolor="white", fontname="Taipei Sans TC, Noto Sans CJK, Arial",
             penwidth="2", fontsize="14")
    dot.attr("edge", color="#1a4b5f", penwidth="2")

    for pid, p in db.persons.items():
        dot.node(pid, p.name)

    # 夫妻映射（現任/前任）
    ex_map = defaultdict(list)
    cur_map = {}
    for m in db.marriages.values():
        a, b = m.a, m.b
        if m.status == "married":
            cur_map[a] = b; cur_map[b] = a
        else:
            ex_map[a].append(b); ex_map[b].append(a)

    # 按層同 rank + 嚴格順序
    nodes_by_level = defaultdict(list)
    for pid in db.persons:
        nodes_by_level[level.get(pid,0)].append(pid)

    for lvl in sorted(nodes_by_level):
        lv_nodes = nodes_by_level[lvl]
        ordered = strict_order_by_level(lv_nodes, lvl, level, cur_map, ex_map)
        if ordered:
            dot.extra.append("{rank=same; " + " ".join(f'"{x}"' for x in ordered) + "}")
            for a, b in zip(ordered, ordered[1:]):
                dot.edge(a, b, style="invis", constraint=True, weight=2200, minlen=1)

    # 兄弟姊妹 rail（與孩子同層）
    def add_sibling_rail(kids: List[str]):
        if not kids: return None
        rail = f"rail_{'_'.join(kids)}"
        dot.node(rail, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        dot.extra.append("{rank=same; \"" + rail + "\" " + " ".join(f'"{k}"' for k in kids) + "}")
        for c in kids:
            dot.edge(rail, c, dir="none", tailport="s", headport="n", minlen=2)
        return rail

    # 婚姻線＋孩子（從夫妻中點垂直）
    for m in db.marriages.values():
        a, b = m.a, m.b
        if a not in db.persons or b not in db.persons: 
            continue
        style = "solid" if m.status=="married" else "dashed"
        uid = union_id(a,b)
        dot.node(uid, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        dot.extra.append(f'{{rank=same; "{a}" "{uid}" "{b}"}}')
        dot.edge(a, uid, dir="none", style=style, weight=5, minlen=1)
        dot.edge(uid, b, dir="none", style=style, weight=5, minlen=1)

        kids = [c for c in set(children_of.get(a,[])).intersection(children_of.get(b,[]))]
        kids.sort()
        if kids:
            rail = add_sibling_rail(kids)
            dot.edge(uid, rail, dir="none", tailport="s", headport="n", minlen=2)

    # 單親（若某 child 只有一位 parent）
    child_parent_count = defaultdict(int)
    for l in db.links.values():
        child_parent_count[l.child] += 1
    for l in db.links.values():
        if child_parent_count[l.child] == 1:
            dot.edge(l.parent, l.child, dir="none", tailport="s", headport="n", minlen=2)

    return dot.source

# ---------------- 法定繼承（簡化示範） ----------------
class InheritanceTW:
    def __init__(self, db: DB):
        self.db = db

    def heirs(self, decedent: str, dod: str):
        try:
            ddate = datetime.strptime(dod, "%Y-%m-%d").date()
        except Exception:
            ddate = date.today()
        if decedent not in self.db.persons:
            return pd.DataFrame(), "找不到被繼承人"

        def alive(pid): return self.db.persons[pid].alive_on(ddate)

        def children_of(pid):
            return [l.child for l in self.db.links.values() if l.parent==pid]

        def spouses_alive(pid):
            s = []
            for m in self.db.marriages.values():
                if pid in (m.a,m.b):
                    o = m.b if pid==m.a else m.a
                    if alive(o): s.append(o)
            return list(dict.fromkeys(s))

        sp = spouses_alive(decedent)
        kids = children_of(decedent)

        rows = []
        if kids or sp:
            unit = (1 if sp else 0) + (1 if kids else 0)
            spouse_share = (1/unit) if sp else 0
            for sid in sp:
                rows.append({"name": self.db.persons[sid].name, "relation": "配偶", "share": round(spouse_share,6)})
            if kids:
                each = (1 - spouse_share) / len(kids) if len(kids)>0 else 0
                for k in kids:
                    rows.append({"name": self.db.persons[k].name, "relation": "直系卑親屬", "share": round(each,6)})

        return pd.DataFrame(rows), "計算完成"

# ---------------- Streamlit UI ----------------
st.set_page_config(layout="wide", page_title=f"家族平台 {VERSION}", page_icon="🌳")
st.title(f"🌳 家族平台（人物｜關係｜法定繼承｜家族樹）— v{VERSION}")

if "db" not in st.session_state:
    st.session_state.db = DB()

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
                {"id":"f9","name":"陳三","gender":"M"},
            ],
            "marriages": [
                {"husband":"f1","wife":"f2","status":"divorced"},
                {"husband":"f1","wife":"f6","status":"married"},
                {"husband":"f3","wife":"f4","status":"married"},
            ],
            "children": [
                {"father":"f1","mother":"f2","child":"f3"},
                {"father":"f1","mother":"f6","child":"f7"},
                {"father":"f1","mother":"f6","child":"f8"},
                {"father":"f1","mother":"f6","child":"f9"},
                {"father":"f3","mother":"f4","child":"f5"},
            ],
        }
        st.session_state.db = DB.from_obj(demo)
        st.success("已載入示範資料")
        st.rerun()

    up = st.file_uploader("匯入 JSON（members/children 或 persons/marriages/links）", type=["json"])
    if up:
        try:
            st.session_state.db = DB.from_obj(json.load(up))
            st.success("匯入成功"); st.rerun()
        except Exception as e:
            st.error(f"匯入失敗：{e}")

    st.download_button(
        "📥 下載 JSON 備份",
        data=json.dumps(st.session_state.db.to_json(), ensure_ascii=False, indent=2),
        file_name="family.json",
        mime="application/json",
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
        st.markdown("---")
        if db.marriages:
            st.caption("婚姻記錄")
            st.dataframe(pd.DataFrame([{**vars(m)} for m in db.marriages.values()]), use_container_width=True)
        if db.links:
            st.caption("親子連結")
            st.dataframe(pd.DataFrame([{**vars(l)} for l in db.links.values()]), use_container_width=True)

with tab3:
    st.subheader("法定繼承人試算（配偶優先；僅直系卑親屬代位，簡化示範）")
    if not db.persons:
        st.info("請先建立人物/關係或載入示範資料。")
    else:
        pick = st.selectbox("被繼承人", sorted([p.name for p in db.persons.values()]))
        dod = st.text_input("死亡日 YYYY-MM-DD", value=str(date.today()))
        dec_id = db.name_index()[pick]
        rule = InheritanceTW(db)
        df, memo = rule.heirs(dec_id, dod)
        if df.empty:
            st.warning("無結果，請檢查資料是否完整。")
        else:
            if memo: st.success(memo)
            st.dataframe(df, use_container_width=True)

with tab4:
    st.subheader("家族樹（夫妻水平線；離婚虛線；孩子中點垂直；前任左、現任右，且優先於同層其他人）")
    st.caption(f"👥 人物 {len(db.persons)}｜💍 婚姻 {len(db.marriages)}｜👶 親子 {len(db.links)}")
    if not db.persons:
        st.info("請先建立人物/關係，或在左側按「一鍵載入示範」。")
    else:
        try:
            dot_src = build_graphviz_source(db)
            st.graphviz_chart(dot_src, use_container_width=True)
            with st.expander("顯示 DOT 原始碼（除錯用）", expanded=False):
                st.code(dot_src, language="dot")
        except Exception as e:
            st.error(f"繪圖發生錯誤：{e}")

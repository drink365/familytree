# app.py — FamilyTree v7.9.1
# - 強制左右順序：前任 → 本人 → 現任（rank=same + invisible edges，高權重 9999）
# - 三代分層；夫妻中點；在婚實線、離婚虛線
# - Streamlit + Graphviz（st.graphviz_chart，不需系統安裝 graphviz 執行檔）

import json
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional

import streamlit as st
import pandas as pd

VERSION = "7.9.1"

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
            sv = str(v).replace('"', r"\\" + r"\"")
            parts.append(f'{k}="{sv}"')
    return " [" + ", ".join(parts) + "]"

class DotBuilder:
    def __init__(self, directed: bool = True):
        self.directed = directed
        self.graph_attrs, self.node_defaults, self.edge_defaults = {}, {}, {}
        self.nodes: Dict[str, dict] = {}
        self.edges: List[Tuple[str, str, dict]] = []
        self.extra: List[str] = []

    def attr(self, kind: Optional[str] = None, **kwargs):
        if kind == "node":
            self.node_defaults.update(kwargs)
        elif kind == "edge":
            self.edge_defaults.update(kwargs)
        else:
            self.graph_attrs.update(kwargs)

    def node(self, nid: str, label: str = "", **attrs):
        if nid not in self.nodes:
            self.nodes[nid] = {}
        if label != "":
            self.nodes[nid]["label"] = label
        self.nodes[nid].update(attrs)

    def edge(self, a: str, b: str, **attrs):
        self.edges.append((a, b, dict(attrs)))

    @property
    def source(self) -> str:
        gtype = "digraph" if self.directed else "graph"
        edgeop = "->" if self.directed else "--"
        out = [f"{gtype} G {{"]

        if self.graph_attrs:
            out.append("  graph" + _fmt_attrs(self.graph_attrs) + ";")
        if self.node_defaults:
            out.append("  node" + _fmt_attrs(self.node_defaults) + ";")
        if self.edge_defaults:
            out.append("  edge" + _fmt_attrs(self.edge_defaults) + ";")

        for nid, attrs in self.nodes.items():
            out.append(f'  "{nid}"' + _fmt_attrs(attrs) + ";")
        for raw in self.extra:
            out.append("  " + raw)
        for a, b, attrs in self.edges:
            out.append(f'  "{a}" {edgeop} "{b}"' + _fmt_attrs(attrs) + ";")

        out.append("}")
        return "\n".join(out)

# ---------------- Data models ----------------
def normalize_status(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip().lower()
    married  = {"married", "在婚", "結婚", "已婚", "現任", "marry", "true", "是"}
    divorced = {"divorced", "離婚"}
    widowed  = {"widowed", "喪偶", "喪夫", "喪妻"}
    if s in married:  return "married"
    if s in divorced: return "divorced"
    if s in widowed:  return "widowed"
    return "divorced"

def clean_name(x: str) -> str:
    return str(x).strip() if x else x

def union_id(a: str, b: str) -> str:
    return f"u_{a}_{b}" if a < b else f"u_{b}_{a}"

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
        if "members" in o:  # A 格式（members / marriages / children）
            for m in o.get("members", []):
                m["name"] = clean_name(m.get("name", ""))
                db.persons[m["id"]] = Person(
                    m["id"], m["name"], m.get("gender", "unknown"),
                    m.get("birth"), m.get("death"), m.get("note", "")
                )
            for m in o.get("marriages", []):
                a = clean_name(m["husband"]); b = clean_name(m["wife"])
                mid = m.get("id") or f"m_{a}_{b}"
                status = normalize_status(m.get("status", "married"))
                db.marriages[mid] = Marriage(mid, a, b, status, m.get("start"), m.get("end"))
            for c in o.get("children", []):
                if c.get("father"):
                    cid = f'c_{c["father"]}_{c["child"]}'
                    db.links[cid] = ParentChild(cid, c["father"], c["child"])
                if c.get("mother"):
                    cid = f'c_{c["mother"]}_{c["child"]}'
                    db.links[cid] = ParentChild(cid, c["mother"], c["child"])
        else:  # B 格式（persons / marriages / links）
            for pid, p in o.get("persons", {}).items():
                nm = clean_name(p.get("name", ""))
                db.persons[pid] = Person(
                    pid, nm, p.get("gender", "unknown"),
                    p.get("birth"), p.get("death"), p.get("note", "")
                )
            for mid, m in o.get("marriages", {}).items():
                a = clean_name(m["a"]); b = clean_name(m["b"])
                status = normalize_status(m.get("status", "married"))
                db.marriages[mid] = Marriage(mid, a, b, status, m.get("start"), m.get("end"))
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

    def name_index(self) -> Dict[str, str]:
        return {p.name: pid for pid, p in self.persons.items()}

    def to_json(self) -> dict:
        return {
            "persons": {k: vars(v) for k, v in self.persons.items()},
            "marriages": {k: vars(v) for k, v in self.marriages.items()},
            "links": {k: vars(v) for k, v in self.links.items()},
        }

# ---------------- Levels ----------------
def compute_levels_and_maps(db: DB):
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
                if level[a] != t or level[b] != t:
                    level[a] = level[b] = t
                    changed = True
    return level, parents_of, children_of

# ---------------- Ordering helpers ----------------
def order_level_base(level_nodes: List[str], name_of: Dict[str, str]) -> List[str]:
    # 低權重的基礎穩定排序（避免 DOT 依 id 或 hash 隨機）
    return sorted(level_nodes, key=lambda x: name_of.get(x, x))

# ---------------- Graphviz builder ----------------
def build_graphviz_source(db: DB) -> str:
    level, parents_of, children_of = compute_levels_and_maps(db)

    # 前任 / 現任索引
    ex_map = defaultdict(list)
    cur_map: Dict[str, str] = {}
    for m in db.marriages.values():
        a, b = m.a, m.b
        if m.status == "married":
            cur_map[a] = b; cur_map[b] = a
        else:
            ex_map[a].append(b); ex_map[b].append(a)

    dot = DotBuilder(directed=True)
    dot.attr(rankdir="TB", splines="ortho", nodesep="1.2", ranksep="1.6", compound=True, ordering="out")
    dot.attr("node", shape="box", style="rounded,filled",
             fillcolor="#0f5b75", color="#0b3e52",
             fontcolor="white", fontname="Taipei Sans TC, Noto Sans CJK, Arial",
             penwidth="2", fontsize="14")
    dot.attr("edge", color="#1a4b5f", penwidth="2")

    # 節點
    for pid, p in db.persons.items():
        dot.node(pid, p.name)

    name_of = {pid: db.persons[pid].name for pid in db.persons}
    nodes_by_level = defaultdict(list)
    for pid in db.persons:
        nodes_by_level[level.get(pid, 0)].append(pid)

    # ---- 同層約束（核心）：前任 → 本人 → 現任 ----
    for lvl in sorted(nodes_by_level):
        lv_nodes = nodes_by_level[lvl]
        if not lv_nodes:
            continue

        # 先把整層放 rank=same；並用低權重 invisible 邊按姓名穩定一下
        base_order = order_level_base(lv_nodes, name_of)
        dot.extra.append("{rank=same; " + " ".join(f'"{x}"' for x in base_order) + "}")
        for a, b in zip(base_order, base_order[1:]):
            dot.edge(a, b, style="invis", constraint=True, weight=5, minlen=1)

        # 對每個人在「同層」的前任/現任，強制高權重順序
        for pid in lv_nodes:
            seq = []
            # 同層前任（多個，以姓名排序）
            exs = [x for x in ex_map.get(pid, []) if level.get(x, -1) == lvl]
            exs.sort(key=lambda x: name_of.get(x, x))
            # 同層現任（最多一個）
            cur = cur_map.get(pid)
            cur_ok = cur and level.get(cur, -1) == lvl

            if exs or cur_ok:
                seq = exs + [pid]
                if cur_ok:
                    seq.append(cur)
                # 再加一次 rank=same（不重複也沒關係）
                dot.extra.append("{rank=same; " + " ".join(f'"{x}"' for x in seq) + "}")
                # 超高權重不可見邊，強制左右順序
                for a, b in zip(seq, seq[1:]):
                    dot.edge(a, b, style="invis", constraint=True, weight=9999, minlen=1)

    # ---- 夫妻中點 + 子女 junction（Gemini） ----
    def add_children_from_pair(a: str, b: str, kids: List[str], style: str):
        if not kids: return
        mid = union_id(a, b)
        dot.node(mid, label="", shape="point", width="0.02", height="0.02", color="#94A3B8")
        dot.extra.append(f'{{rank=same; "{a}" "{mid}" "{b}"}}')
        dot.edge(a, mid, dir="none", style=style, weight=5, minlen=1)
        dot.edge(mid, b, dir="none", style=style, weight=5, minlen=1)

        jn = f"jn_{a}_{b}"
        dot.node(jn, label="", style="invis", width="0", height="0")
        dot.edge(mid, jn, dir="none", style="invis", weight=10, minlen=1)
        dot.extra.append("{rank=same; " + " ".join(['"{}"'.format(jn)] + [f'"{k}"' for k in kids]) + "}")
        for c in kids:
            dot.edge(jn, c, dir="none", tailport="s", headport="n", minlen=2)

    children_of_parent = defaultdict(set)
    for l in db.links.values():
        children_of_parent[l.parent].add(l.child)

    def common_children(a: str, b: str) -> List[str]:
        sa = set(children_of.get(a, []))
        sb = set(children_of.get(b, []))
        return sorted(list(sa.intersection(sb)))

    for m in db.marriages.values():
        a, b = m.a, m.b
        if a not in db.persons or b not in db.persons:
            continue
        kids = common_children(a, b)
        style = "solid" if m.status == "married" else "dashed"
        add_children_from_pair(a, b, kids, style)

    # 單親
    child_parent_count = defaultdict(int)
    for l in db.links.values():
        child_parent_count[l.child] += 1
    for l in db.links.values():
        if child_parent_count[l.child] == 1:
            dot.edge(l.parent, l.child, dir="none", tailport="s", headport="n", minlen=2)

    return dot.source

# ---------------- Inheritance (簡化示範) ----------------
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
        def children_of(pid): return [l.child for l in self.db.links.values() if l.parent == pid]
        def spouses_alive(pid):
            s = []
            for m in self.db.marriages.values():
                if pid in (m.a, m.b):
                    o = m.b if pid == m.a else m.a
                    if alive(o): s.append(o)
            return list(dict.fromkeys(s))

        sp = spouses_alive(decedent)
        kids = children_of(decedent)

        rows = []
        if kids or sp:
            unit = (1 if sp else 0) + (1 if kids else 0)
            spouse_share = (1 / unit) if sp else 0
            for sid in sp:
                rows.append({"name": self.db.persons[sid].name, "relation": "配偶", "share": round(spouse_share, 6)})
            if kids:
                each = (1 - spouse_share) / len(kids) if len(kids) > 0 else 0
                for k in kids:
                    rows.append({"name": self.db.persons[k].name, "relation": "直系卑親屬", "share": round(each, 6)})
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
                {"husband": "f1", "wife": "f6", "status": "married"},
                {"husband": "f3", "wife": "f4", "status": "married"}
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
            if memo:
                st.success(memo)
            st.dataframe(df, use_container_width=True)

with tab4:
    st.subheader("家族樹（前任在左、本人置中、現任在右；三代分層）")
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

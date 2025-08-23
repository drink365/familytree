# app.py — FamilyTree v7.6.0 (no external graphviz dependency)
# - 不需安裝 graphviz 系統套件；用自製 DOT 產生器 + st.graphviz_chart
# - 規則：同層【前任們 → 本人 → 現任】；婚姻實線、離婚/喪偶虛線；孩子自父母中點垂直
# - 內建「陳一郎家族」一鍵示範；法定繼承（簡化示範）

import json
from datetime import date, datetime
from collections import defaultdict
from typing import Dict, List
import streamlit as st
import pandas as pd

VERSION = "7.6.0"

# ----------------- Minimal DOT builder -----------------
def _fmt_attrs(d: dict) -> str:
    if not d:
        return ""
    parts = []
    for k, v in d.items():
        if isinstance(v, bool):
            parts.append(f'{k}={"true" if v else "false"}')
        elif isinstance(v, (int, float)):
            parts.append(f'{k}={v}')
        else:
            s = str(v).replace('"', r"\"")
            parts.append(f'{k}="{s}"')
    return " [" + ", ".join(parts) + "]"

class DotBuilder:
    def __init__(self, directed: bool = True):
        self.directed = directed
        self.graph_attrs = {}
        self.node_defaults = {}
        self.edge_defaults = {}
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
            self.nodes[nid] = {"label": label} if label else {}
        if label:
            self.nodes[nid]["label"] = label
        self.nodes[nid].update(attrs)

    def edge(self, a: str, b: str, **attrs):
        self.edges.append((a, b, dict(attrs)))

    @property
    def source(self) -> str:
        gtype = "digraph" if self.directed else "graph"
        edgeop = "->" if self.directed else "--"
        lines = [f"{gtype} G {{"]

        if self.graph_attrs:
            lines.append("  graph" + _fmt_attrs(self.graph_attrs) + ";")
        if self.node_defaults:
            lines.append("  node" + _fmt_attrs(self.node_defaults) + ";")
        if self.edge_defaults:
            lines.append("  edge" + _fmt_attrs(self.edge_defaults) + ";")

        for nid, attrs in self.nodes.items():
            lines.append(f'  "{nid}"' + _fmt_attrs(attrs) + ";")
        for raw in self.extra:
            lines.append("  " + raw)
        for a, b, attrs in self.edges:
            lines.append(f'  "{a}" {edgeop} "{b}"' + _fmt_attrs(attrs) + ";")

        lines.append("}")
        return "\n".join(lines)

# ----------------- Data Models -----------------
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None):
        self.pid, self.name, self.gender, self.birth, self.death = pid, name, gender, birth, death

    def alive_on(self, d: date) -> bool:
        if not self.death:
            return True
        try:
            return datetime.strptime(self.death, "%Y-%m-%d").date() > d
        except Exception:
            return True

class Marriage:
    def __init__(self, mid, a, b, status="married"):
        self.mid, self.a, self.b, self.status = mid, a, b, status

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
        if "members" in o:
            for m in o.get("members", []):
                db.persons[m["id"]] = Person(m["id"], m["name"], m.get("gender", "unknown"))
            for m in o.get("marriages", []):
                mid = m.get("id") or f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(mid, m["husband"], m["wife"], m.get("status", "married"))
            for c in o.get("children", []):
                if c.get("father"):
                    db.links[f"c_{c['father']}_{c['child']}"] = ParentChild(f"c_{c['father']}_{c['child']}", c["father"], c["child"])
                if c.get("mother"):
                    db.links[f"c_{c['mother']}_{c['child']}"] = ParentChild(f"c_{c['mother']}_{c['child']}", c["mother"], c["child"])
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
        pid = f"p_{len(self.persons)+1}"
        self.persons[pid] = Person(pid, name, gender)
        return pid

    def name_index(self) -> Dict[str, str]:
        return {p.name: pid for pid, p in self.persons.items()}

def union_id(a: str, b: str) -> str:
    return f"u_{a}_{b}" if a < b else f"u_{b}_{a}"

# ----------------- Level + Graph -----------------
def compute_levels(db: DB):
    parents = defaultdict(list)
    children = defaultdict(list)
    for l in db.links.values():
        parents[l.child].append(l.parent)
        children[l.parent].append(l.child)

    memo = {}
    def depth(pid):
        if pid in memo:
            return memo[pid]
        ps = parents.get(pid, [])
        if not ps:
            memo[pid] = 0
        else:
            memo[pid] = 1 + max(depth(p) for p in ps)
        return memo[pid]

    level = {pid: depth(pid) for pid in db.persons}
    return level, parents, children

def build_graphviz(db: DB) -> str:
    level, parents, children = compute_levels(db)
    dot = DotBuilder(True)
    dot.attr(rankdir="TB", splines="ortho", nodesep="1.2", ranksep="1.4")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#0f5b75", fontcolor="white")
    dot.attr("edge", color="#1a4b5f", penwidth="2")

    for pid, p in db.persons.items():
        dot.node(pid, p.name)

    ex_map = defaultdict(list)
    cur_map = {}
    for m in db.marriages.values():
        if m.status == "married":
            cur_map[m.a] = m.b
            cur_map[m.b] = m.a
        else:
            ex_map[m.a].append(m.b)
            ex_map[m.b].append(m.a)

    nodes_by_lvl = defaultdict(list)
    for pid in db.persons:
        nodes_by_lvl[level[pid]].append(pid)

    for lvl in sorted(nodes_by_lvl):
        nodes = sorted(nodes_by_lvl[lvl])
        dot.extra.append("{rank=same; " + " ".join(f'"{n}"' for n in nodes) + "}")
        for pid in nodes:
            exs = sorted(ex_map.get(pid, []))
            cur = cur_map.get(pid)
            block = exs + [pid] + ([cur] if cur else [])
            if len(block) > 1:
                dot.extra.append("{rank=same; " + " ".join(f'"{n}"' for n in block) + "}")
                for a,b in zip(block, block[1:]):
                    dot.edge(a,b,style="invis",constraint=False)

    for m in db.marriages.values():
        uid = union_id(m.a,m.b)
        dot.node(uid,"",shape="point",width="0.01")
        dot.edge(m.a,uid,dir="none",style="solid" if m.status=="married" else "dashed")
        dot.edge(uid,m.b,dir="none",style="solid" if m.status=="married" else "dashed")

        kids = [c for c in children.get(m.a,[]) if c in children.get(m.b,[])]
        if kids:
            rail=f"rail_{uid}"
            dot.node(rail,"",shape="point",width="0.01")
            dot.edge(uid,rail,dir="none")
            for c in kids:
                dot.edge(rail,c,dir="none")

    for c,ps in parents.items():
        if len(ps)==1:
            dot.edge(ps[0],c,dir="none")
    return dot.source

# ----------------- UI -----------------
st.set_page_config(layout="wide",page_title=f"家族平台 {VERSION}",page_icon="🌳")
st.title(f"🌳 家族平台 — v{VERSION}")

if "db" not in st.session_state:
    st.session_state.db=DB()

with st.sidebar:
    if st.button("🧪 一鍵載入示範：陳一郎家族"):
        demo=json.load(open("demo_family.json",encoding="utf-8"))
        st.session_state.db=DB.from_obj(demo)
        st.rerun()
    up=st.file_uploader("匯入 JSON",type=["json"])
    if up:
        st.session_state.db=DB.from_obj(json.load(up))
        st.rerun()
    st.download_button("下載 JSON",data=json.dumps(st.session_state.db.to_json(),ensure_ascii=False,indent=2),file_name="family.json")

db=st.session_state.db
tab1,tab2,tab3=st.tabs(["👤 人物","🔗 關係","🗺️ 家族樹"])

with tab1:
    name=st.text_input("姓名")
    if st.button("新增人物"):
        if name: db.ensure_person(name)
    if db.persons:
        st.dataframe(pd.DataFrame([{**vars(p)} for p in db.persons.values()]))

with tab2:
    names=sorted([p.name for p in db.persons.values()])
    if names:
        a=st.selectbox("配偶A",names)
        b=st.selectbox("配偶B",names)
        stt=st.selectbox("狀態",["married","divorced","widowed"])
        if st.button("新增婚姻"): 
            db.marriages[f"m_{a}_{b}"]=Marriage(f"m_{a}_{b}",db.name_index()[a],db.name_index()[b],stt)
        par=st.selectbox("父母",names)
        chd=st.selectbox("子女",names)
        if st.button("新增親子"):
            db.links[f"c_{par}_{chd}"]=ParentChild(f"c_{par}_{chd}",db.name_index()[par],db.name_index()[chd])

with tab3:
    if db.persons:
        dot=build_graphviz(db)
        st.graphviz_chart(dot,use_container_width=True)

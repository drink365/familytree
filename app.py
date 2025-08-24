# app.py
import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

st.set_page_config(page_title="家族樹生成器（修正版）", page_icon="🌳", layout="wide")

BORDER = "#114b5f"
NODE_BG = "#0b3d4f"
NODE_FG = "#ffffff"

def _pid(): return "P_" + uuid.uuid4().hex[:6]
def _mid(): return "M_" + uuid.uuid4().hex[:6]

# 初始化狀態
if "data" not in st.session_state:
    st.session_state.data = {"persons": {}, "marriages": {}, "children": []}

def clear_all():
    st.session_state.data = {"persons": {}, "marriages": {}, "children": []}

def load_demo():
    clear_all()
    P = st.session_state.data["persons"]
    M = st.session_state.data["marriages"]
    C = st.session_state.data["children"]

    p1 = _pid(); P[p1] = {"name": "陳一郎"}
    p2 = _pid(); P[p2] = {"name": "陳前妻"}
    p3 = _pid(); P[p3] = {"name": "陳妻"}
    c1 = _pid(); P[c1] = {"name": "王子"}
    c2 = _pid(); P[c2] = {"name": "陳大"}
    c3 = _pid(); P[c3] = {"name": "陳二"}
    c4 = _pid(); P[c4] = {"name": "陳三"}
    c5 = _pid(); P[c5] = {"name": "王子妻"}
    c6 = _pid(); P[c6] = {"name": "王孫"}

    m1 = _mid(); M[m1] = {"a": p1, "b": p2, "divorced": True}
    m2 = _mid(); M[m2] = {"a": p1, "b": p3, "divorced": False}
    m3 = _mid(); M[m3] = {"a": c1, "b": c5, "divorced": False}

    C += [
        {"mid": m1, "child": c1},
        {"mid": m2, "child": c2},
        {"mid": m2, "child": c3},
        {"mid": m2, "child": c4},
        {"mid": m3, "child": c6},
    ]

# 繪製節點
def person_node(dot, pid, name):
    dot.node(pid, name, shape="box", style="rounded,filled",
             fillcolor=NODE_BG, fontcolor=NODE_FG, color=BORDER, penwidth="1.2")

def draw_tree():
    data = st.session_state.data
    if not data["persons"]:
        st.info("請先載入示範或自行新增資料")
        return

    dot = Digraph("family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="0.9")

    for pid, p in data["persons"].items():
        person_node(dot, pid, p["name"])

    # 每段婚姻單獨 joint node
    m2kids = defaultdict(list)
    for rec in data["children"]:
        m2kids[rec["mid"]].append(rec["child"])

    for mid, m in data["marriages"].items():
        a, b, div = m["a"], m["b"], m["divorced"]
        j = f"J_{mid}"  # 該婚姻專屬 joint node
        dot.node(j, "", shape="point", width="0.02", height="0.02", color=BORDER)

        # 父母同列
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        # 父母橫線（不影響層級）
        dot.edge(a, b, dir="none", style="dashed" if div else "solid",
                 color=BORDER, constraint="false")

        # 鎖 joint node 在父母下方
        dot.edge(a, j, style="invis", weight="50")
        dot.edge(b, j, style="invis", weight="50")

        # 子女直落
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids: s.node(c)
            for c in kids:
                dot.edge(j, c, dir="none", color=BORDER, weight="2")

    st.graphviz_chart(dot, use_container_width=True)

# 側欄操作
with st.sidebar:
    if st.button("載入示範"):
        load_demo()
    if st.button("清空"):
        clear_all()

st.title("家族樹生成器（修正版）")
draw_tree()

with st.expander("目前資料"):
    st.json(st.session_state.data)

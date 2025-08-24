# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="家族樹生成器（穩定版）", page_icon="🌳", layout="wide")

COLOR_BORDER = "#114b5f"
COLOR_NODE_BG = "#0b3d4f"
COLOR_NODE_FG = "#ffffff"

def _pid(): return "P_" + uuid.uuid4().hex[:8]
def _mid(): return "M_" + uuid.uuid4().hex[:8]

# ---------------- 狀態 ----------------
def _empty_state():
    return {"persons": {}, "marriages": {}, "children": [], "sibling_hints": []}

if "data" not in st.session_state:
    st.session_state.data = _empty_state()

def clear_all():
    st.session_state.data = _empty_state()

def load_demo():
    # 與你需求一致的示範；先清空避免殘留造成錯線
    clear_all()
    d = st.session_state.data
    P, M = d["persons"], d["marriages"]

    # 人物
    a = _pid(); P[a] = {"name": "陳一郎"}
    ex = _pid(); P[ex] = {"name": "陳前妻"}
    w  = _pid(); P[w]  = {"name": "陳妻"}
    c1 = _pid(); P[c1] = {"name": "陳大"}
    c2 = _pid(); P[c2] = {"name": "陳二"}
    c3 = _pid(); P[c3] = {"name": "陳三"}
    s  = _pid(); P[s]  = {"name": "王子"}
    sw = _pid(); P[sw] = {"name": "王子妻"}
    g  = _pid(); P[g]  = {"name": "王孫"}

    # 婚姻
    m1 = _mid(); M[m1] = {"a": a, "b": ex, "divorced": True}
    m2 = _mid(); M[m2] = {"a": a, "b": w,  "divorced": False}
    m3 = _mid(); M[m3] = {"a": s, "b": sw, "divorced": False}

    # 子女必須掛在對應婚姻的 joint node 之下
    d["children"].extend([
        {"mid": m1, "child": s},
        {"mid": m2, "child": c1},
        {"mid": m2, "child": c2},
        {"mid": m2, "child": c3},
        {"mid": m3, "child": g},
    ])

# ---------------- 工具 ----------------
def node_person(dot, pid, name):
    dot.node(
        pid, name,
        shape="box",
        style="rounded,filled",
        fillcolor=COLOR_NODE_BG,
        fontcolor=COLOR_NODE_FG,
        color=COLOR_BORDER,
        penwidth="1.2",
        fontsize="14",
    )

def build_maps(data):
    m2kids = defaultdict(list)
    child2parents = defaultdict(set)
    for rec in data["children"]:
        mid, child = rec.get("mid"), rec.get("child")
        if mid in data["marriages"] and child in data["persons"]:
            a = data["marriages"][mid]["a"]
            b = data["marriages"][mid]["b"]
            m2kids[mid].append(child)
            child2parents[child] |= {a, b}
    return m2kids, child2parents

# ---------------- 繪圖 ----------------
def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先點左側『載入示範』，或自行新增人物/婚姻/子女。")
        return

    dot = Digraph("family", format="svg", engine="dot")
    # 重要：使用 polyline（而非 ortho）可避免繞遠路的直角折返
    dot.graph_attr.update(
        rankdir="TB",
        splines="polyline",
        nodesep="0.6",
        ranksep="0.9",
        concentrate="false",
        ordering="out",
        newrank="true",
    )

    # 畫所有人
    for pid, p in d["persons"].items():
        node_person(dot, pid, p["name"])

    m2kids, child2parents = build_maps(d)

    # 每段婚姻：夫妻同列 + joint node 鎖在正下方 + 子女直落
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m.get("divorced", False)
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", height="0.02", color=COLOR_BORDER)

        # 夫妻同列；joint node 不與其他婚姻同列（避免合併層級）
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        # 夫妻橫線只為視覺呈現，不影響層級
        dot.edge(a, b, dir="none",
                 style=("dashed" if divorced else "solid"),
                 color=COLOR_BORDER,
                 constraint="false",
                 weight="1")

        # 關鍵：用高權重的隱形邊把 joint node 鎖在兩人**正下方**
        # 這兩條邊會參與層級計算（constraint=True by default）
        dot.edge(a, jn, style="invis", weight="80", minlen="1")
        dot.edge(b, jn, style="invis", weight="80", minlen="1")

        # 子女：同列；從 joint node 直落（沒有箭頭）
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            # 讓兄弟姊妹彼此以隱形高權重相連，固定橫向順序
            for i in range(len(kids) - 1):
                dot.edge(kids[i], kids[i+1], style="invis", weight="30")
            for c in kids:
                dot.edge(jn, c, dir="none", color=COLOR_BORDER, weight="6", minlen="2")

    # 若需要半同胞提示（本例無），用虛線且不影響層級
    for a, b in d.get("sibling_hints", []):
        with dot.subgraph() as s:
            s.attr(rank="same"); s.node(a); s.node(b)
        dot.edge(a, b, dir="none", style="dashed", color=COLOR_BORDER, constraint="false")

    st.graphviz_chart(dot, use_container_width=True)

# ---------------- 介面 ----------------
with st.sidebar:
    st.markdown("## 操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with c2:
        if st.button("清空", use_container_width=True):
            clear_all()

st.title("家族樹生成器（穩定版）")
draw_tree()

with st.expander("（除錯）目前資料"):
    st.json(st.session_state.data, expanded=False)

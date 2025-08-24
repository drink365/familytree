# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

st.set_page_config(page_title="家族樹生成器（修正走線版）", page_icon="🌳", layout="wide")

# 顏色
BORDER = "#114b5f"
NODE_BG = "#0b3d4f"
NODE_FG = "#ffffff"

def _pid(): return "P_" + uuid.uuid4().hex[:8]
def _mid(): return "M_" + uuid.uuid4().hex[:8]

def _empty():
    return {"persons": {}, "marriages": {}, "children": []}

if "data" not in st.session_state:
    st.session_state.data = _empty()

def clear_all():
    st.session_state.data = _empty()

def load_demo():
    clear_all()
    d = st.session_state.data
    P, M = d["persons"], d["marriages"]

    # 人物
    chen = _pid();   P[chen] = {"name": "陳一郎"}
    ex   = _pid();   P[ex]   = {"name": "陳前妻"}
    wife = _pid();   P[wife] = {"name": "陳妻"}
    a    = _pid();   P[a]    = {"name": "陳大"}
    b    = _pid();   P[b]    = {"name": "陳二"}
    c    = _pid();   P[c]    = {"name": "陳三"}
    wz   = _pid();   P[wz]   = {"name": "王子"}
    wzw  = _pid();   P[wzw]  = {"name": "王子妻"}
    ws   = _pid();   P[ws]   = {"name": "王孫"}

    # 婚姻
    mex  = _mid();   M[mex]  = {"a": chen, "b": ex,   "divorced": True}
    mnow = _mid();   M[mnow] = {"a": chen, "b": wife, "divorced": False}
    mw   = _mid();   M[mw]   = {"a": wz,   "b": wzw,  "divorced": False}

    # 子女掛在各自婚姻
    d["children"] += [
        {"mid": mex,  "child": wz},
        {"mid": mnow, "child": a},
        {"mid": mnow, "child": b},
        {"mid": mnow, "child": c},
        {"mid": mw,   "child": ws},
    ]

# 工具
def person_node(dot, pid, name):
    dot.node(pid, name, shape="box", style="rounded,filled",
             fillcolor=NODE_BG, fontcolor=NODE_FG, color=BORDER, penwidth="1.2", fontsize="14")

def build_m2kids(data):
    m2kids = defaultdict(list)
    for rec in data["children"]:
        mid, child = rec.get("mid"), rec.get("child")
        if mid in data["marriages"] and child in data["persons"]:
            m2kids[mid].append(child)
    return m2kids

# 繪圖
def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先點左側『載入示範』或自行新增資料。")
        return

    dot = Digraph("family", format="svg", engine="dot")
    # 關鍵：使用 ortho，但我們指定連接埠，避免 Graphviz 自動拉「共用橫桿」
    dot.graph_attr.update(
        rankdir="TB",
        splines="ortho",
        nodesep="0.6",
        ranksep="0.9",
        concentrate="false"
    )

    # 人物
    for pid, p in d["persons"].items():
        person_node(dot, pid, p["name"])

    m2kids = build_m2kids(d)

    # 每段婚姻一個 joint node
    for mid, m in d["marriages"].items():
        a, b, div = m["a"], m["b"], m.get("divorced", False)
        j = f"J_{mid}"
        # 用小方點（比 point 更容易控制方位）
        dot.node(j, "", shape="box", width="0.02", height="0.02", style="filled", fillcolor=NODE_BG, color=BORDER)

        # 父母同列
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        # 顯示夫妻線（不影響層級）
        dot.edge(a, b, dir="none", style=("dashed" if div else "solid"),
                 color=BORDER, constraint="false")

        # 用高權重隱形邊把 joint 鎖在兩人正下方
        dot.edge(a, j, style="invis", weight="100", minlen="1")
        dot.edge(b, j, style="invis", weight="100", minlen="1")

        # 子女：同列，從 joint 的「南側」直落到孩子的「北側」
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)

            # 直接畫 j:s -> child:n，避免 Graphviz 先走橫向再下來
            for c in kids:
                dot.edge(j, c,
                         dir="none",
                         color=BORDER,
                         tailport="s",
                         headport="n",
                         weight="80",
                         minlen="2")

    st.graphviz_chart(dot, use_container_width=True)

# 介面
st.title("家族樹生成器（修正走線版）")

with st.sidebar:
    st.markdown("### 操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with c2:
        if st.button("清空資料", use_container_width=True):
            clear_all()

draw_tree()

with st.expander("（除錯）目前資料"):
    st.json(st.session_state.data, expanded=False)

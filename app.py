# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
import uuid
from collections import defaultdict

st.set_page_config(page_title="家族樹（穩定連線版）", page_icon="🌳", layout="wide")

# ---- 配色 ----
BORDER = "#0B3646"
NODE_BG = "#08394A"
NODE_FG = "#FFFFFF"

def _pid(): return "P_" + uuid.uuid4().hex[:7]
def _mid(): return "M_" + uuid.uuid4().hex[:7]

def _empty():
    return {"persons": {}, "marriages": {}, "children": []}

if "data" not in st.session_state:
    st.session_state.data = _empty()

# ---- 範例 ----
def load_demo():
    d = _empty()
    P = d["persons"]; M = d["marriages"]; C = d["children"]
    chen = _pid();   P[chen] = {"name": "陳一郎"}
    ex   = _pid();   P[ex]   = {"name": "陳前妻"}
    wife = _pid();   P[wife] = {"name": "陳妻"}
    c1   = _pid();   P[c1]   = {"name": "陳大"}
    c2   = _pid();   P[c2]   = {"name": "陳二"}
    c3   = _pid();   P[c3]   = {"name": "陳三"}
    wz   = _pid();   P[wz]   = {"name": "王子"}
    wzw  = _pid();   P[wzw]  = {"name": "王子妻"}
    ws   = _pid();   P[ws]   = {"name": "王孫"}

    mex  = _mid();   M[mex]  = {"a": chen, "b": ex,   "divorced": True}
    mnow = _mid();   M[mnow] = {"a": chen, "b": wife, "divorced": False}
    mw   = _mid();   M[mw]   = {"a": wz,   "b": wzw,  "divorced": False}

    C += [{"mid": mex, "child": wz},
          {"mid": mnow, "child": c1},
          {"mid": mnow, "child": c2},
          {"mid": mnow, "child": c3},
          {"mid": mw, "child": ws}]
    st.session_state.data = d

# ---- UI：左側 ----
with st.sidebar:
    st.markdown("## 操作")
    if st.button("載入示範", use_container_width=True):
        load_demo()
    if st.button("清空", use_container_width=True):
        st.session_state.data = _empty()

# ---- 繪圖 ----
def node_person(dot, pid, name):
    dot.node(pid, name, shape="box", style="rounded,filled",
             fillcolor=NODE_BG, color=BORDER, fontcolor=NODE_FG, penwidth="1.2")

def build_maps(d):
    m2kids = defaultdict(list)
    for r in d["children"]:
        if r["mid"] in d["marriages"] and r["child"] in d["persons"]:
            m2kids[r["mid"]].append(r["child"])
    return m2kids

def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("點左側『載入示範』或自行加入資料。")
        return

    dot = Digraph("family", format="svg", engine="dot")
    # ordering=out 可讓邊的順序更可預期；splines=ortho 產生直角線
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="1.0",
                          concentrate="false", compound="true", ordering="out")

    # 1) 人物
    for pid, p in d["persons"].items():
        node_person(dot, pid, p["name"])

    m2kids = build_maps(d)

    # 2) 婚姻（每段婚姻一個 joint node）
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m.get("divorced", False)
        j = f"J_{mid}"
        dot.node(j, "", shape="point", width="0.02", height="0.02", color=BORDER)

        # 夫妻＋joint 同列，避免 joint 漂移
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(j); s.node(b)

        # 兩條「高權重」隱形邊把 joint 鎖在 a、b 中間
        dot.edge(a, j, style="invis", weight="100")
        dot.edge(b, j, style="invis", weight="100")

        # 顯示夫妻橫線（不影響層級），並指定左右連接埠避免短小垂勾
        dot.edge(a, b, dir="none",
                 tailport="e", headport="w",
                 style=("dashed" if divorced else "solid"),
                 color=BORDER, constraint="false", weight="1")

        # 子女橫列，從 joint 垂直往下；接到子女「北面」避免折返
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(j, c, dir="none", color=BORDER, minlen="2", weight="2",
                         headport="n")

    return dot

st.title("家族樹（穩定連線版）")

dot = draw_tree()
if dot:
    st.graphviz_chart(dot, use_container_width=True)

with st.expander("目前資料（除錯）"):
    st.json(st.session_state.data, expanded=False)

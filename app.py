# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="家族樹生成器（最終穩定版）", page_icon="🌳", layout="wide")

COLOR_BORDER = "#114b5f"
COLOR_NODE_BG = "#0b3d4f"
COLOR_NODE_FG = "#ffffff"

def _pid(): return "P_" + uuid.uuid4().hex[:8]
def _mid(): return "M_" + uuid.uuid4().hex[:8]

# ---------------- 狀態 ----------------
def _empty_state():
    return {"persons": {}, "marriages": {}, "children": []}

if "data" not in st.session_state:
    st.session_state.data = _empty_state()

def clear_all():
    st.session_state.data = _empty_state()

def load_demo():
    """與題圖一致的示範；先清空避免殘留造成錯線"""
    clear_all()
    d = st.session_state.data
    P, M = d["persons"], d["marriages"]

    # 人物
    p_f = _pid(); P[p_f] = {"name": "陳一郎"}
    p_ex = _pid(); P[p_ex] = {"name": "陳前妻"}
    p_w  = _pid(); P[p_w]  = {"name": "陳妻"}
    c_a  = _pid(); P[c_a]  = {"name": "陳大"}
    c_b  = _pid(); P[c_b]  = {"name": "陳二"}
    c_c  = _pid(); P[c_c]  = {"name": "陳三"}
    s    = _pid(); P[s]    = {"name": "王子"}
    sw   = _pid(); P[sw]   = {"name": "王子妻"}
    g    = _pid(); P[g]    = {"name": "王孫"}

    # 婚姻（每段婚姻一個 joint/marriage node）
    m_ex  = _mid(); M[m_ex]  = {"a": p_f, "b": p_ex, "divorced": True}
    m_now = _mid(); M[m_now] = {"a": p_f, "b": p_w,  "divorced": False}
    m_w   = _mid(); M[m_w]   = {"a": s,   "b": sw,   "divorced": False}

    # 子女掛在對應婚姻
    d["children"].extend([
        {"mid": m_ex,  "child": s},
        {"mid": m_now, "child": c_a},
        {"mid": m_now, "child": c_b},
        {"mid": m_now, "child": c_c},
        {"mid": m_w,   "child": g},
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
    """m2kids: 每段婚姻的孩子清單"""
    m2kids = defaultdict(list)
    for rec in data["children"]:
        mid, child = rec.get("mid"), rec.get("child")
        if mid in data["marriages"] and child in data["persons"]:
            m2kids[mid].append(child)
    return m2kids

# ---------------- 繪圖 ----------------
def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先點『載入示範』或使用左側表單新增資料。")
        return

    # 重要：使用 polyline 避免過度“繞路”的直角折返
    dot = Digraph("family", format="svg", engine="dot")
    dot.graph_attr.update(
        rankdir="TB",
        splines="polyline",
        nodesep="0.7",
        ranksep="1.0",
        newrank="true",
        concentrate="false",
        ordering="out",
    )

    # 1) 畫人
    for pid, p in d["persons"].items():
        node_person(dot, pid, p["name"])

    # 2) 以「婚姻點」作為父母與子女的樞紐（標準 DAG 做法）
    m2kids = build_maps(d)

    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m.get("divorced", False)
        jn = f"J_{mid}"   # marriage node
        dot.node(jn, "", shape="point", width="0.02", height="0.02", color=COLOR_BORDER)

        # 讓夫妻同一列；但婚姻點與其他婚姻不合併層級
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        # 視覺水平線（不參與分層）
        dot.edge(a, b, dir="none",
                 style=("dashed" if divorced else "solid"),
                 color=COLOR_BORDER, constraint="false")

        # 關鍵：兩條高權重「隱形邊」鎖住婚姻點在兩人正下方
        # 這兩條邊參與層級計算（預設 constraint=True）
        dot.edge(a, jn, style="invis", weight="80", minlen="1")
        dot.edge(b, jn, style="invis", weight="80", minlen="1")

        # 子女同列，由婚姻點直落；加上 minlen 讓層距更穩
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids: s.node(c)
            # 以隱形高權重相連，固定橫向順序，避免 Graphviz 自動重排
            for i in range(len(kids) - 1):
                dot.edge(kids[i], kids[i+1], style="invis", weight="30")
            for c in kids:
                dot.edge(jn, c, dir="none", color=COLOR_BORDER, weight="6", minlen="2")

    st.graphviz_chart(dot, use_container_width=True)

# ---------------- 介面 ----------------
st.title("家族樹生成器（最終穩定版）")

with st.sidebar:
    st.markdown("### 操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with c2:
        if st.button("清空資料", use_container_width=True):
            clear_all()

    st.markdown("---")
    st.markdown("### 新增人物")
    with st.form("f_add_person", clear_on_submit=True):
        name = st.text_input("姓名*", value="")
        note = st.text_input("備註（可留白）", value="")
        if st.form_submit_button("新增人物"):
            if name.strip():
                pid = _pid()
                st.session_state.data["persons"][pid] = {"name": name.strip(), "note": note.strip()}
                st.success(f"已新增：{name}")
            else:
                st.warning("請輸入姓名")

    P = st.session_state.data["persons"]
    if P:
        st.markdown("### 新增婚姻/伴侶")
        with st.form("f_add_marriage"):
            a = st.selectbox("配偶 A", options=list(P.keys()), format_func=lambda x: P[x]["name"])
            b = st.selectbox("配偶 B", options=[k for k in P.keys() if k != a], format_func=lambda x: P[x]["name"])
            divorced = st.checkbox("已離婚（虛線）", value=False)
            if st.form_submit_button("建立婚姻/伴侶"):
                # 避免重覆建立
                exists = any((m["a"]==a and m["b"]==b) or (m["a"]==b and m["b"]==a)
                             for m in st.session_state.data["marriages"].values())
                if exists:
                    st.warning("這對配偶關係已存在。")
                else:
                    mid = _mid()
                    st.session_state.data["marriages"][mid] = {"a": a, "b": b, "divorced": divorced}
                    st.success(f"已建立：{P[a]['name']} ↔ {P[b]['name']}")

    if st.session_state.data["marriages"] and P:
        st.markdown("### 為婚姻新增子女")
        with st.form("f_add_child"):
            mid = st.selectbox(
                "選擇婚姻/伴侶",
                options=list(st.session_state.data["marriages"].keys()),
                format_func=lambda m: f"{P[st.session_state.data['marriages'][m]['a']]['name']} ↔ {P[st.session_state.data['marriages'][m]['b']]['name']}"
            )
            child = st.selectbox("子女", options=list(P.keys()), format_func=lambda x: P[x]["name"])
            if st.form_submit_button("加入子女"):
                already = any((row["mid"]==mid and row["child"]==child) for row in st.session_state.data["children"])
                if already:
                    st.warning("該子女已在這段婚姻下。")
                else:
                    st.session_state.data["children"].append({"mid": mid, "child": child})
                    st.success(f"已加入子女：{P[child]['name']}")

# 右側畫圖
draw_tree()

with st.expander("（除錯）目前資料"):
    st.json(st.session_state.data, expanded=False)

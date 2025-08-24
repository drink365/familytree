# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="家族樹生成器", page_icon="🌳", layout="wide")

# 色系（可自行調整）
BORDER_COLOR = "#114b5f"
NODE_BG = "#0b3d4f"
NODE_FG = "#ffffff"

# ---------------- 資料模型 ----------------
# persons: {pid: {"name": str, "note": str}}
# marriages: {mid: {"a": pid, "b": pid, "divorced": bool}}
# children: [{"mid": mid, "child": pid}]   # 子女一定掛在 marriage 的 joint node 下
# sibling_links: [(pid1, pid2)]             # 非同父母的「橫向虛線」提示（可選）

def _pid(): return "P_" + uuid.uuid4().hex[:8]
def _mid(): return "M_" + uuid.uuid4().hex[:8]

def ensure_state():
    if "data" not in st.session_state:
        st.session_state.data = {
            "persons": {},
            "marriages": {},
            "children": [],
            "sibling_links": [],
        }

def clear_all():
    st.session_state.data = {
        "persons": {},
        "marriages": {},
        "children": [],
        "sibling_links": [],
    }

def load_demo():
    """載入與你附圖一致的示範資料；會先清空，避免殘留造成錯線。"""
    clear_all()
    persons, marriages, children = {}, {}, []

    # 人物
    p_chen = _pid();     persons[p_chen] = {"name": "陳一郎", "note": ""}
    p_ex   = _pid();     persons[p_ex]   = {"name": "陳前妻", "note": ""}
    p_wife = _pid();     persons[p_wife] = {"name": "陳妻", "note": ""}

    p_da   = _pid();     persons[p_da]   = {"name": "陳大", "note": ""}
    p_er   = _pid();     persons[p_er]   = {"name": "陳二", "note": ""}
    p_san  = _pid();     persons[p_san]  = {"name": "陳三", "note": ""}

    p_wz   = _pid();     persons[p_wz]   = {"name": "王子", "note": ""}
    p_wzw  = _pid();     persons[p_wzw]  = {"name": "王子妻", "note": ""}
    p_ws   = _pid();     persons[p_ws]   = {"name": "王孫", "note": ""}

    # 婚姻（每段婚姻一個 joint node）
    m_ex   = _mid(); marriages[m_ex]   = {"a": p_chen, "b": p_ex,   "divorced": True}
    m_now  = _mid(); marriages[m_now]  = {"a": p_chen, "b": p_wife, "divorced": False}
    m_wang = _mid(); marriages[m_wang] = {"a": p_wz,   "b": p_wzw,  "divorced": False}

    # 小孩掛到對應的婚姻
    children.append({"mid": m_ex,   "child": p_wz})
    children.append({"mid": m_now,  "child": p_da})
    children.append({"mid": m_now,  "child": p_er})
    children.append({"mid": m_now,  "child": p_san})
    children.append({"mid": m_wang, "child": p_ws})

    st.session_state.data = {
        "persons": persons,
        "marriages": marriages,
        "children": children,
        "sibling_links": [],   # 這個案例不需要
    }

# ---------------- 小工具 ----------------
def build_maps():
    """回傳:
       - m2kids: {mid: [child_pid, ...]}
       - child2parents: {child_pid: set([a_pid, b_pid])}
    """
    d = st.session_state.data
    m2kids = defaultdict(list)
    child2parents = defaultdict(set)
    for row in d["children"]:
        mid = row.get("mid")
        c   = row.get("child")
        if mid in d["marriages"] and c in d["persons"]:
            a = d["marriages"][mid]["a"]
            b = d["marriages"][mid]["b"]
            m2kids[mid].append(c)
            child2parents[c] |= {a, b}
    return m2kids, child2parents

def node_person(dot, pid, name):
    dot.node(
        pid, name,
        shape="box",
        style="rounded,filled",
        color=BORDER_COLOR,
        fillcolor=NODE_BG,
        fontcolor=NODE_FG,
        penwidth="1.2",
        fontsize="14",
    )

# ---------------- 繪圖 ----------------
def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先『載入示範』或自行新增人物與關係。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="0.9")

    # 1) 畫所有人物
    for pid, p in d["persons"].items():
        node_person(dot, pid, p["name"])

    # 2) 每段婚姻建立 joint node 與連線
    m2kids, child2parents = build_maps()

    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", color=BORDER_COLOR)

        # 夫妻與 joint node 放在同一列，避免 joint node 漂移
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(jn); s.node(b)

        # 鎖 joint node：兩條高權重隱形邊（影響佈局但不顯示）
        dot.edge(a, jn, style="invis", weight="60")
        dot.edge(b, jn, style="invis", weight="60")

        # 顯示夫妻連線（現任實線／前任虛線），不影響層級
        dot.edge(a, b, dir="none",
                 style=("dashed" if divorced else "solid"),
                 color=BORDER_COLOR, constraint="false")

        # 子女：同一橫列；由 joint node 垂直往下
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)

            # 讓兄弟姊妹互相「隱形串接」，縮小 joint node 橫向延伸
            for i in range(len(kids) - 1):
                dot.edge(kids[i], kids[i + 1], style="invis", weight="30")

            # joint node → 每位子女（無箭頭，直落）
            for c in kids:
                dot.edge(jn, c, dir="none", color=BORDER_COLOR, weight="5", minlen="1")

    # 3) 半同胞提示（如果有）：虛線、同列
    def same_parents(x, y):
        return bool(child2parents.get(x)) and child2parents.get(x) == child2parents.get(y)

    for a, b in d["sibling_links"]:
        if same_parents(a, b):
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)
        dot.edge(a, b, dir="none", style="dashed", color=BORDER_COLOR, constraint="false")

    st.graphviz_chart(dot, use_container_width=True)

# ---------------- UI ----------------
ensure_state()

left, right = st.columns([1, 3])

with left:
    st.markdown("### 操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with c2:
        if st.button("清空資料", use_container_width=True):
            clear_all()

    st.markdown("### 新增人物")
    with st.form("f_add_person", clear_on_submit=True):
        name = st.text_input("姓名*", value="")
        note = st.text_input("備註", value="")
        if st.form_submit_button("新增人物"):
            if name.strip():
                pid = _pid()
                st.session_state.data["persons"][pid] = {"name": name.strip(), "note": note.strip()}
                st.success(f"已新增：{name}")
            else:
                st.warning("請輸入姓名")

    ps = st.session_state.data["persons"]
    if ps:
        st.markdown("### 新增婚姻/伴侶")
        with st.form("f_add_marriage"):
            a = st.selectbox("配偶 A", options=list(ps.keys()), format_func=lambda x: ps[x]["name"])
            b = st.selectbox("配偶 B", options=[k for k in ps.keys() if k != a],
                             format_func=lambda x: ps[x]["name"])
            divorced = st.checkbox("已離婚（以虛線表示）", value=False)
            if st.form_submit_button("建立婚姻/伴侶關係"):
                exists = any((mm["a"]==a and mm["b"]==b) or (mm["a"]==b and mm["b"]==a)
                             for mm in st.session_state.data["marriages"].values())
                if exists:
                    st.warning("這對配偶關係已存在。")
                else:
                    mid = _mid()
                    st.session_state.data["marriages"][mid] = {"a": a, "b": b, "divorced": divorced}
                    st.success(f"已建立：{ps[a]['name']} ↔ {ps[b]['name']}")

    if st.session_state.data["marriages"] and ps:
        st.markdown("### 為婚姻新增子女")
        with st.form("f_add_child"):
            mid = st.selectbox(
                "選擇婚姻/伴侶",
                options=list(st.session_state.data["marriages"].keys()),
                format_func=lambda m: f"{ps[st.session_state.data['marriages'][m]['a']]['name']} ↔ {ps[st.session_state.data['marriages'][m]['b']]['name']}"
            )
            child = st.selectbox("子女", options=list(ps.keys()), format_func=lambda x: ps[x]["name"])
            if st.form_submit_button("加入子女"):
                if any((row["mid"] == mid and row["child"] == child) for row in st.session_state.data["children"]):
                    st.warning("該子女已在這段婚姻下。")
                else:
                    st.session_state.data["children"].append({"mid": mid, "child": child})
                    st.success(f"已加入子女：{ps[child]['name']}")

    if ps:
        st.markdown("###（可選）半同胞虛線")
        with st.form("f_add_sibling_hint"):
            a = st.selectbox("人物 A", options=list(ps.keys()), format_func=lambda x: ps[x]["name"], key="sibA")
            b = st.selectbox("人物 B", options=[k for k in ps.keys() if k != a],
                             format_func=lambda x: ps[x]["name"], key="sibB")
            if st.form_submit_button("加入虛線提示"):
                pair = (a, b) if a < b else (b, a)
                if pair in st.session_state.data["sibling_links"]:
                    st.warning("這條虛線已存在。")
                else:
                    st.session_state.data["sibling_links"].append(pair)
                    st.success(f"已加入：{ps[a]['name']} - - - {ps[b]['name']}")

with right:
    st.markdown("## 家族樹")
    draw_tree()

    with st.expander("（除錯）目前資料"):
        st.json(st.session_state.data, expanded=False)

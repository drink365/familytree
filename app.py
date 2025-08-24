# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from graphviz import Digraph
from collections import defaultdict
import uuid

# ---------- 外觀設定 ----------
st.set_page_config(page_title="家族樹生成器", page_icon="🌳", layout="wide")
BORDER_COLOR = "#114b5f"
NODE_BG = "#0b3d4f"
NODE_FG = "#ffffff"

# ---------- 資料結構 ----------
# persons: {pid: {"name": str, "note": str}}
# marriages: {mid: {"a": pid, "b": pid, "divorced": bool}}
# children: [{"mid": mid, "child": pid}]
# sibling_links: [(pid1, pid2)]       # 非同父母的「橫向虛線提示」(可選)

def new_pid():
    return "P_" + uuid.uuid4().hex[:8]

def new_mid():
    return "M_" + uuid.uuid4().hex[:8]

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = {
            "persons": {},
            "marriages": {},
            "children": [],
            "sibling_links": [],
        }

def load_demo():
    """載入與你給的圖片一致的示範資料"""
    persons = {}
    marriages = {}
    children = []
    sibling_links = []

    # 人物
    p_chen = new_pid();      persons[p_chen] = {"name": "陳一郎", "note": ""}
    p_ex = new_pid();        persons[p_ex]   = {"name": "陳前妻", "note": ""}
    p_wife = new_pid();      persons[p_wife] = {"name": "陳妻", "note": ""}

    p_da = new_pid();        persons[p_da]   = {"name": "陳大", "note": ""}
    p_er = new_pid();        persons[p_er]   = {"name": "陳二", "note": ""}
    p_san = new_pid();       persons[p_san]  = {"name": "陳三", "note": ""}

    p_wangzi = new_pid();    persons[p_wangzi]   = {"name": "王子", "note": ""}
    p_wangwife = new_pid();  persons[p_wangwife] = {"name": "王子妻", "note": ""}
    p_wangsun = new_pid();   persons[p_wangsun]  = {"name": "王孫", "note": ""}

    # 婚姻
    m_ex = new_mid();  marriages[m_ex]  = {"a": p_chen, "b": p_ex, "divorced": True}
    m_now = new_mid(); marriages[m_now] = {"a": p_chen, "b": p_wife, "divorced": False}
    m_wang = new_mid();marriages[m_wang]= {"a": p_wangzi, "b": p_wangwife, "divorced": False}

    # 子女（一定要接到 marriage 的 joint node）
    children.append({"mid": m_ex,  "child": p_wangzi})
    children.append({"mid": m_now, "child": p_da})
    children.append({"mid": m_now, "child": p_er})
    children.append({"mid": m_now, "child": p_san})
    children.append({"mid": m_wang, "child": p_wangsun})

    st.session_state.data = {
        "persons": persons,
        "marriages": marriages,
        "children": children,
        "sibling_links": sibling_links,
    }

def clear_all():
    st.session_state.data = {
        "persons": {},
        "marriages": {},
        "children": [],
        "sibling_links": [],
    }

# ---------- 小工具 ----------
def build_child_map():
    """回傳:
       - m2kids: {mid: [child_pid, ...]}
       - child2parents: {child_pid: set([a_pid, b_pid])}
    """
    d = st.session_state.data
    m2kids = defaultdict(list)
    child2parents = defaultdict(set)
    for row in d["children"]:
        mid = row["mid"]; c = row["child"]
        if mid in d["marriages"]:
            a = d["marriages"][mid]["a"]
            b = d["marriages"][mid]["b"]
            m2kids[mid].append(c)
            child2parents[c] |= {a, b}
    return m2kids, child2parents

def person_node(dot, pid, person):
    dot.node(
        pid,
        person["name"],
        shape="box",
        style="rounded,filled",
        color=BORDER_COLOR,
        fillcolor=NODE_BG,
        fontcolor=NODE_FG,
        penwidth="1.2",
        fontsize="14",
    )

# ---------- 繪圖主程式 ----------
def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("尚無資料。請點選左上角『載入示範』或到下方自行新增人物與關係。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="0.8")

    # 1) 畫所有人物
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # 2) 夫妻及 joint node
    m2kids, child2parents = build_child_map()
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", color=BORDER_COLOR)

        # 夫妻水平線：現任實線、離婚虛線；不影響層級
        dot.edge(a, b, dir="none", style=("dashed" if divorced else "solid"),
                 color=BORDER_COLOR, constraint="false")

        # 高權重隱形邊鎖 joint node 在兩人中間
        dot.edge(a, jn, dir="none", style="invis", weight="50")
        dot.edge(b, jn, dir="none", style="invis", weight="50")

        # 讓夫妻同一列
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        # joint node → 子女
        kids = m2kids.get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(jn, c, color=BORDER_COLOR)

    # 3) 半同胞的橫向提示（虛線）
    def same_parents(x, y):
        return bool(child2parents.get(x)) and child2parents.get(x) == child2parents.get(y)

    for a, b in d["sibling_links"]:
        if same_parents(a, b):
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)
        dot.edge(a, b, style="dashed", color=BORDER_COLOR, dir="none")

    st.graphviz_chart(dot, use_container_width=True)

# ---------- 介面：操作列 ----------
ensure_session()
left, right = st.columns([1, 3])

with left:
    st.markdown("### 操作")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with col2:
        if st.button("清空資料", use_container_width=True):
            clear_all()

    st.markdown("### 新增人物")
    with st.form("add_person", clear_on_submit=True):
        name = st.text_input("姓名*", value="")
        note = st.text_input("備註", value="")
        ok = st.form_submit_button("新增人物")
        if ok:
            if name.strip():
                pid = new_pid()
                st.session_state.data["persons"][pid] = {"name": name.strip(), "note": note.strip()}
                st.success(f"已新增人物：{name}")
            else:
                st.warning("請輸入姓名")

    st.markdown("### 新增婚姻/伴侶")
    ps = st.session_state.data["persons"]
    if ps:
        id_name = {pid: f'{ps[pid]["name"]} ({pid})' for pid in ps}
        with st.form("add_marriage"):
            a = st.selectbox("配偶 A", options=list(ps.keys()), format_func=lambda x: ps[x]["name"])
            b = st.selectbox("配偶 B", options=[k for k in ps.keys() if k != a], format_func=lambda x: ps[x]["name"])
            divorced = st.checkbox("已離婚（以虛線表示）", value=False)
            ok2 = st.form_submit_button("建立婚姻/伴侶關係")
            if ok2:
                # 避免重覆婚姻
                exists = any((m["a"]==a and m["b"]==b) or (m["a"]==b and m["b"]==a)
                             for m in st.session_state.data["marriages"].values())
                if exists:
                    st.warning("這對配偶關係已存在。")
                else:
                    mid = new_mid()
                    st.session_state.data["marriages"][mid] = {"a": a, "b": b, "divorced": divorced}
                    st.success(f"已建立：{ps[a]['name']} ↔ {ps[b]['name']}")

    st.markdown("### 為某段婚姻新增子女")
    if st.session_state.data["marriages"] and st.session_state.data["persons"]:
        with st.form("add_child"):
            mid = st.selectbox(
                "選擇婚姻/伴侶",
                options=list(st.session_state.data["marriages"].keys()),
                format_func=lambda m: f"{ps[st.session_state.data['marriages'][m]['a']]['name']} ↔ {ps[st.session_state.data['marriages'][m]['b']]['name']}"
            )
            child = st.selectbox("子女", options=list(ps.keys()), format_func=lambda x: ps[x]["name"])
            ok3 = st.form_submit_button("加入子女")
            if ok3:
                # 避免重覆加入
                already = any((row["mid"] == mid and row["child"] == child) for row in st.session_state.data["children"])
                if already:
                    st.warning("該子女已在這段婚姻下。")
                else:
                    st.session_state.data["children"].append({"mid": mid, "child": child})
                    st.success(f"已加入子女：{ps[child]['name']}")

    st.markdown("###（可選）半同胞橫向虛線")
    if st.session_state.data["persons"]:
        with st.form("add_sibling_link"):
            a = st.selectbox("人物 A", options=list(ps.keys()), format_func=lambda x: ps[x]["name"], key="sibA")
            b = st.selectbox("人物 B", options=[k for k in ps.keys() if k != a],
                             format_func=lambda x: ps[x]["name"], key="sibB")
            ok4 = st.form_submit_button("加入虛線提示")
            if ok4:
                pair = (a, b) if a < b else (b, a)
                if pair in st.session_state.data["sibling_links"]:
                    st.warning("這條虛線已存在。")
                else:
                    st.session_state.data["sibling_links"].append(pair)
                    st.success(f"已加入：{ps[a]['name']} - - - {ps[b]['name']}")

with right:
    st.markdown("## 家族樹")
    draw_tree()

    # 可視化目前資料（除錯用）
    with st.expander("查看目前資料（除錯用）", expanded=False):
        st.json(st.session_state.data, expanded=False)

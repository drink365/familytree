import io
import json
from typing import Dict, List, Set, Tuple
import streamlit as st
from graphviz import Digraph

# =============== 外觀設定 ===============
st.set_page_config(page_title="家族平台｜家族樹＋法定繼承", layout="wide")
PRIMARY = "#184a5a"
ACCENT = "#0e2d3b"

st.markdown("""
    <style>
    .stApp {background-color: #f7fbfd;}
    .big-title {font-size: 32px; font-weight: 800; color:#0e2d3b; letter-spacing:1px;}
    .subtle {color:#55707a}
    .pill {
        display:inline-block; padding:6px 10px; border-radius:999px;
        background:#e7f3f6; color:#184a5a; font-size:12px; margin-right:8px;
    }
    .card {
        border:1px solid #e8eef0; border-radius:12px; padding:14px 16px; background:#fff;
        margin-bottom:12px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🌳 家族平台（家族樹＋法定繼承）</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">前任在左、本人置中、現任在右；三代分層；台灣民法法定繼承（嚴格順位制）</div>', unsafe_allow_html=True)
st.write("")

# =============== 節點樣式顏色 ===============
COLOR_MALE = "#D2E9FF"
COLOR_FEMALE = "#FFD2D2"
COLOR_DECEASED = "#D9D9D9"

# =============== 一鍵示範資料 ===============
DEMO = {
    "persons": {
        "c_yilang": {"name": "陳一郎", "gender": "男", "deceased": False},
        "c_wife": {"name": "陳妻", "gender": "女", "deceased": False},
        "c_exwife": {"name": "陳前妻", "gender": "女", "deceased": False},
        "wang_zi": {"name": "王子", "gender": "男", "deceased": False},
        "wang_zi_wife": {"name": "王子妻", "gender": "女", "deceased": False},
        "wang_sun": {"name": "王孫", "gender": "男", "deceased": False},
        "chen_da": {"name": "陳大", "gender": "男", "deceased": False},
        "chen_er": {"name": "陳二", "gender": "男", "deceased": False},
        "chen_san": {"name": "陳三", "gender": "男", "deceased": False},
    },
    "marriages": [
        {"id": "m_current", "a": "c_yilang", "b": "c_wife", "status": "current"},
        {"id": "m_ex", "a": "c_yilang", "b": "c_exwife", "status": "ex"},
        {"id": "m_wang", "a": "wang_zi", "b": "wang_zi_wife", "status": "current"},
    ],
    "children": [
        {"marriage_id": "m_current", "children": ["chen_da","chen_er","chen_san"]},
        {"marriage_id": "m_ex", "children": ["wang_zi"]},
        {"marriage_id": "m_wang", "children": ["wang_sun"]},
    ]
}

if "data" not in st.session_state:
    st.session_state["data"] = DEMO

# =============== 工具函式 ===============
def normalize_name(s: str) -> str:
    return (s or "").strip()

def ensure_person_id(data: dict, name: str, gender: str, deceased: bool) -> str:
    name = normalize_name(name)
    if not name:
        raise ValueError("姓名不可空白")
    persons = data.setdefault("persons", {})
    for pid, info in persons.items():
        if info.get("name") == name:
            # 更新性別與生死狀態
            info["gender"] = gender
            info["deceased"] = deceased
            return pid
    # 建新 ID
    base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in name)
    pid = base
    i = 1
    while pid in persons:
        i += 1; pid = f"{base}_{i}"
    persons[pid] = {"name": name, "gender": gender, "deceased": deceased}
    return pid

def node_color(info: dict) -> str:
    if info.get("deceased"):
        return COLOR_DECEASED
    return COLOR_MALE if info.get("gender") == "男" else COLOR_FEMALE

def node_label(info: dict) -> str:
    return f"{info.get('name','')}（殁）" if info.get("deceased") else info.get("name","")

# =============== 建圖 ===============
def build_graph(data: dict, root_id: str) -> Digraph:
    dot = Digraph(comment="Family Tree", engine="dot", format="svg")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.7")

    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = {c["marriage_id"]: c["children"] for c in children}

    # 人物節點
    for pid, info in persons.items():
        dot.node(pid, node_label(info), style="filled", fillcolor=node_color(info), color="#0e2d3b")

    # 婚姻連結
    for m in marriages:
        mid = m["id"]; a, b = m["a"], m["b"]
        dotted = (m.get("status") == "ex")
        dot.node(mid, "", shape="point", width="0.02", color="#184a5a")
        style = "dashed" if dotted else "solid"
        dot.edge(a, mid, dir="none", style=style)
        dot.edge(b, mid, dir="none", style=style)
        with dot.subgraph() as s:
            s.attr(rank="same"); s.node(a); s.node(b)

    # 子女
    for mid, kids in ch_map.items():
        if not kids: continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for cid in kids: s.node(cid)
        for cid in kids:
            dot.edge(mid, cid)

    return dot

# =============== 分頁 ===============
tab_tree, tab_data = st.tabs(["🧭 家族樹", "🗂️ 資料"])

with tab_tree:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    if persons:
        root_id = st.selectbox("選擇家族樹根人物", list(persons.keys()), format_func=lambda x: persons[x]["name"])
        dot = build_graph(data, root_id)
        st.graphviz_chart(dot.source, use_container_width=True)
    else:
        st.info("請先在『資料』分頁新增人物")

with tab_data:
    st.markdown("### 新增人物")
    with st.form("add_person", clear_on_submit=True):
        name = st.text_input("姓名 *")
        gender = st.selectbox("性別", ["男","女"])
        deceased = st.checkbox("已過世")
        submitted = st.form_submit_button("新增/更新")
        if submitted:
            try:
                pid = ensure_person_id(st.session_state["data"], name, gender, deceased)
                st.success(f"已新增/更新：{name}")
            except Exception as e:
                st.error(f"失敗：{e}")

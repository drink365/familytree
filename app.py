# app.py
# -*- coding: utf-8 -*-

import json
from collections import defaultdict
from typing import Dict, List, Tuple

import streamlit as st
from graphviz import Digraph

st.set_page_config(page_title="Family Tree", page_icon="🌳", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# 資料模型（存在 session）
# ──────────────────────────────────────────────────────────────────────────────
def _empty_data():
    return {
        "persons": {},      # pid -> {id,name,sex("男"/"女"),alive(bool)}
        "marriages": {},    # mid -> {id,a(pid),b(pid),divorced(bool)}
        "children": [],     # list of {mid, child(pid)}
        "_seq": 0,
    }

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def next_id():
    st.session_state.data["_seq"] += 1
    return str(st.session_state.data["_seq"])

# ──────────────────────────────────────────────────────────────────────────────
# 快速建立 / 範例
# ──────────────────────────────────────────────────────────────────────────────
def add_person(name: str, sex: str = "男", alive: bool = True) -> str:
    pid = next_id()
    st.session_state.data["persons"][pid] = {
        "id": pid, "name": name, "sex": sex, "alive": alive
    }
    return pid

def add_marriage(a: str, b: str, divorced: bool = False) -> str:
    # 若已存在同一對，直接更新離婚狀態
    for mid, m in st.session_state.data["marriages"].items():
        if {m["a"], m["b"]} == {a, b}:
            m["divorced"] = bool(divorced)
            return mid
    mid = f"M{next_id()}"
    st.session_state.data["marriages"][mid] = {
        "id": mid, "a": a, "b": b, "divorced": bool(divorced)
    }
    return mid

def add_child(mid: str, child_pid: str) -> None:
    if mid not in st.session_state.data["marriages"]:
        return
    d = st.session_state.data
    if not any(x["mid"] == mid and x["child"] == child_pid for x in d["children"]):
        d["children"].append({"mid": mid, "child": child_pid})

def load_demo():
    st.session_state.data = _empty_data()
    P = {}
    def P_(name, sex="男", alive=True):
        pid = add_person(name, sex, alive); P[name] = pid; return pid

    # 人物
    P_("陳一郎","男"); P_("陳前妻","女"); P_("陳妻","女")
    P_("陳大","男");   P_("陳大嫂","女")
    P_("陳二","男");   P_("陳二嫂","女")
    P_("陳三","男");   P_("陳三嫂","女")
    P_("王子","男");   P_("王子妻","女"); P_("王孫","男")
    P_("二孩A","女");  P_("二孩B","男");  P_("二孩C","女")
    P_("三孩A","男");  P_("三孩B","女")

    # 婚姻
    m1 = add_marriage(P["陳一郎"], P["陳前妻"], divorced=True)
    m2 = add_marriage(P["陳一郎"], P["陳妻"])
    m3 = add_marriage(P["王子"],   P["王子妻"])
    m4 = add_marriage(P["陳大"],   P["陳大嫂"])
    m5 = add_marriage(P["陳二"],   P["陳二嫂"])
    m6 = add_marriage(P["陳三"],   P["陳三嫂"])

    # 子女
    add_child(m1, P["王子"])
    add_child(m2, P["陳大"]); add_child(m2, P["陳二"]); add_child(m2, P["陳三"])
    add_child(m3, P["王孫"])
    add_child(m5, P["二孩A"]); add_child(m5, P["二孩B"]); add_child(m5, P["二孩C"])
    add_child(m6, P["三孩A"]); add_child(m6, P["三孩B"])

# ──────────────────────────────────────────────────────────────────────────────
# Graphviz 繪圖（重點：婚姻點 + 子女群組 + 多婚姻左右排開）
# ──────────────────────────────────────────────────────────────────────────────
COLOR_MALE   = "#d8eaff"
COLOR_FEMALE = "#ffdbe1"
COLOR_DEAD   = "#e6e6e6"
BORDER       = "#164b5f"
FONT         = "#0b2430"

def _node_person(dot: Digraph, pid: str, person: Dict):
    label = person["name"] + ("" if person["alive"] else "（殁）")
    shape = "box" if person["sex"] == "男" else "ellipse"
    fill  = COLOR_DEAD if not person["alive"] else (COLOR_MALE if person["sex"]=="男" else COLOR_FEMALE)
    dot.node(pid, label=label, shape=shape, style="filled", fillcolor=fill,
             color=BORDER, fontcolor=FONT, penwidth="1.4")

def build_dot(data: Dict) -> str:
    persons   = data["persons"]
    marriages = data["marriages"]
    children  = data["children"]

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.72", bgcolor="white")
    dot.edge_attr.update(arrowhead="none", color=BORDER, penwidth="1.3")

    # 1) 人物節點
    for pid, p in persons.items():
        _node_person(dot, pid, p)

    # 2) 先統計「某人參與的所有婚姻」→ 之後讓他的所有 hub 與他同層，並用隱形邊串起來
    hubs_by_person: Dict[str, List[str]] = defaultdict(list)
    for mid, m in marriages.items():
        a, b = m["a"], m["b"]
        hubs_by_person[a].append(f"hub_{mid}")
        hubs_by_person[b].append(f"hub_{mid}")

    # 3) 每段婚姻：A→hub←B（離婚就虛線），hub→down→子女；子女同排
    kids_by_mid: Dict[str, List[str]] = defaultdict(list)
    for r in children:
        kids_by_mid[r["mid"]].append(r["child"])

    for mid, m in marriages.items():
        a, b, divorced = m["a"], m["b"], m["divorced"]

        hub  = f"hub_{mid}"    # 配偶之間的中繼點（同層）
        down = f"down_{mid}"   # 婚姻點正下方的錨點（子女從這裡往下）
        dot.node(hub,  label="", shape="point", width="0.01", height="0.01", color=BORDER)
        dot.node(down, label="", shape="point", width="0.01", height="0.01", color=BORDER)

        # 讓 A、hub、B 在同一層，婚線絕對水平
        dot.body.append('{ rank=same; "' + a + '" "' + hub + '" "' + b + '" }')

        # A→hub、B→hub（離婚為虛線）
        style = "dashed" if divorced else "solid"
        dot.edge(a, hub,  style=style, weight="6", constraint="true")
        dot.edge(b, hub,  style=style, weight="6", constraint="true")

        # hub→down 垂直中線
        dot.edge(hub, down, weight="10", constraint="true", minlen="1")

        # 同段婚姻的孩子們：同層 + 由 down 垂直連下去
        kids = kids_by_mid.get(mid, [])
        if kids:
            dot.body.append("{ rank=same; " + " ".join(f'"{c}"' for c in kids) + " }")
            for c in kids:
                dot.edge(down, c, weight="8", constraint="true", minlen="1")
            # 用隱形邊讓兄弟姊妹更水平緊湊
            for i in range(len(kids) - 1):
                dot.edge(kids[i], kids[i+1], style="invis", weight="2", constraint="true")

    # 4) 多段婚姻的人：把他的 hub 全放同層，並用隱形水平邊串起 → 左右排開、不交錯
    for pid, hubs in hubs_by_person.items():
        if len(hubs) <= 1:
            continue
        # 與本人同層
        dot.body.append("{ rank=same; " + " ".join(f'"{x}"' for x in ([pid] + hubs)) + " }")
        # 隱形水平鏈（hub1 — hub2 — hub3 …）
        for i in range(len(hubs) - 1):
            dot.edge(hubs[i], hubs[i+1], style="invis", weight="5", constraint="true")

    return dot.source

# ──────────────────────────────────────────────────────────────────────────────
# 介面
# ──────────────────────────────────────────────────────────────────────────────
def list_person_options() -> List[Tuple[str,str]]:
    d = st.session_state.data
    return [(pid, f'{p["name"]}（{"男" if p["sex"]=="男" else "女"}{"・在世" if p["alive"] else "・殁"}）')
            for pid, p in d["persons"].items()]

def main():
    ensure_session()
    d = st.session_state.data

    # 頂部工具
    left, right = st.columns([1,1])
    with left:
        st.markdown("### 🌳 家族樹（穩定版）")
        st.caption("A→婚姻點←B、子女自婚姻點往下；多段婚姻左右排開，線條不再交錯。")
    with right:
        c1, c2 = st.columns(2)
        if c1.button("載入示範", use_container_width=True):
            load_demo(); st.rerun()
        if c2.button("清空資料", use_container_width=True):
            st.session_state.data = _empty_data(); st.rerun()

    st.divider()

    tab1, tab2, tab3 = st.tabs(["人物", "關係", "家族樹"])
    with tab1:
        st.subheader("新增人物")
        with st.form("add_person", clear_on_submit=True):
            col1, col2, col3 = st.columns([2,1,1])
            name = col1.text_input("姓名")
            sex  = col2.selectbox("性別", ["男","女"])
            alive= col3.selectbox("狀態", ["在世","已故"])
            if st.form_submit_button("新增"):
                if name.strip():
                    add_person(name.strip(), sex, alive=="在世")
                    st.success("已新增")
                else:
                    st.warning("請輸入姓名")

        st.divider()
        st.subheader("現有人物")
        if not d["persons"]:
            st.info("尚無人物。請先新增或載入示範。")
        else:
            for pid, p in list(d["persons"].items()):
                cols = st.columns([3,1,1,1])
                tag = "" if p["alive"] else "（殁）"
                cols[0].markdown(f'**{p["name"]}{tag}**　/ {p["sex"]}')
                if cols[1].button("切換在世/殁", key=f"alive_{pid}"):
                    p["alive"] = not p["alive"]
                new = cols[2].text_input("改名", value=p["name"], key=f"rename_{pid}")
                if new != p["name"]:
                    p["name"] = new or p["name"]
                if cols[3].button("刪除此人", key=f"del_{pid}"):
                    mids = [mid for mid,m in d["marriages"].items() if pid in (m["a"], m["b"])]
                    for mid in mids:
                        d["marriages"].pop(mid, None)
                        d["children"] = [r for r in d["children"] if r["mid"] != mid]
                    d["children"] = [r for r in d["children"] if r["child"] != pid]
                    d["persons"].pop(pid, None)
                    st.rerun()

    with tab2:
        st.subheader("建立婚姻")
        persons_opts = list_person_options()
        if not persons_opts:
            st.info("請先新增人物。")
        else:
            colA, colB, colC = st.columns([2,2,1])
            A = colA.selectbox("配偶 A", persons_opts, format_func=lambda x:x[1], index=0)
            B = colB.selectbox("配偶 B", persons_opts, format_func=lambda x:x[1], index=min(1,len(persons_opts)-1))
            divorced = colC.checkbox("離婚（前配偶）", value=False)
            if st.button("建立/更新婚姻", use_container_width=True, type="primary"):
                if A[0]==B[0]:
                    st.warning("兩個欄位不可為同一人。")
                else:
                    add_marriage(A[0], B[0], divorced)
                    st.success("已建立/更新")
        st.divider()

        st.subheader("加入子女")
        if not d["marriages"]:
            st.info("請先建立一段婚姻。")
        else:
            mids = list(d["marriages"].keys())
            def fmt_m(mid):
                a,b,div = d["marriages"][mid]["a"], d["marriages"][mid]["b"], d["marriages"][mid]["divorced"]
                na, nb = d["persons"][a]["name"], d["persons"][b]["name"]
                return f"{na} ↔ {nb}{'（離）' if div else ''}"
            mid = st.selectbox("選擇婚姻", mids, format_func=fmt_m)
            kid_opts = list_person_options()
            kid = st.selectbox("選擇子女（先至人物頁建立）", kid_opts, format_func=lambda x:x[1])
            if st.button("加入子女", use_container_width=True):
                add_child(mid, kid[0])
                st.success("已加入")

    with tab3:
        st.subheader("家族樹")
        if not d["persons"]:
            st.info("請先新增人物與關係，或點上方「載入示範」。")
        else:
            dot_src = build_dot(d)
            st.graphviz_chart(dot_src, use_container_width=True)

if __name__ == "__main__":
    main()

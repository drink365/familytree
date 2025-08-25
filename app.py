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
# Graphviz 繪圖（強化：婚姻點 + 子女分組 + 同層對齊）
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
    # orthogonal 直角線 + 間距設定
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.70", bgcolor="white")
    dot.edge_attr.update(arrowhead="none", color=BORDER, penwidth="1.3")

    # 1) 畫出所有人物節點
    for pid, p in persons.items():
        _node_person(dot, pid, p)

    # 預先把每段婚姻的子女收集起來
    kids_by_mid: Dict[str, List[str]] = defaultdict(list)
    for r in children:
        kids_by_mid[r["mid"]].append(r["child"])

    # 2) 每段婚姻：配偶同層 + 中間婚姻點 + 子女群組
    for mid, m in marriages.items():
        a, b, divorced = m["a"], m["b"], m["divorced"]

        # 2-1 配偶同層（rank=same），並畫配偶之間的水平線（離婚用虛線）
        dot.body.append("{ rank=same; " + f'"{a}" "{b}"' + " }")
        dot.edge(a, b, style="dashed" if divorced else "solid", weight="5")  # weight 拉近距離

        # 2-2 中線「婚姻點」與「下方錨點」
        hub   = f"hub_{mid}"     # 配偶之間的中繼點
        down  = f"down_{mid}"    # 婚姻點正下方的錨點（用來垂直對齊子女）
        dot.node(hub,  label="", shape="point", width="0.01", height="0.01", color=BORDER)
        dot.node(down, label="", shape="point", width="0.01", height="0.01", color=BORDER)

        # 讓 hub 與配偶在同一層，確保婚線水平且 hub 位於兩者之間
        dot.body.append("{ rank=same; " + f'"{a}" "{hub}" "{b}"' + " }")

        # 配偶 → 婚姻點（不改層級，只是水平相連）
        dot.edge(a, hub,  weight="3", constraint="true")
        dot.edge(b, hub,  weight="3", constraint="true")

        # 婚姻點 → 下方錨點（強制下一層，形成垂直中線）
        dot.edge(hub, down, weight="10", constraint="true")

        # 2-3 子女群組（這段婚姻的所有子女排成一排）
        kids = kids_by_mid.get(mid, [])
        if kids:
            # 把這組孩子放同一層
            dot.body.append("{ rank=same; " + " ".join(f'"{c}"' for c in kids) + " }")
            # 用「下方錨點」接到每個孩子，形成乾淨的「T 型」垂直線
            for c in kids:
                dot.edge(down, c, weight="8", constraint="true", minlen="1")
            # 用隱形邊把兄弟姊妹串起來，讓他們水平排列更緊湊
            for i in range(len(kids)-1):
                dot.edge(kids[i], kids[i+1], style="invis", weight="2", constraint="true")

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
        st.markdown("### 🌳 家族樹（Graphviz 強化版）")
        st.caption("配偶同層＋婚姻點＋子女群組：線條垂直、兄弟姊妹同排、不同婚姻分組清楚。")
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
                # 切換生死
                if cols[1].button("切換在世/殁", key=f"alive_{pid}"):
                    p["alive"] = not p["alive"]
                # 改名
                new = cols[2].text_input("改名", value=p["name"], key=f"rename_{pid}")
                if new != p["name"]:
                    p["name"] = new or p["name"]
                # 刪除
                if cols[3].button("刪除此人", key=f"del_{pid}"):
                    # 刪掉相關婚姻與子女關係
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

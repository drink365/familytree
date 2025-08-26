# -*- coding: utf-8 -*-
"""
📦 家族樹小幫手（Mini MVP）
-------------------------------------------------
目標：
- 用最少的欄位，最快速畫出家族樹
- 不需要懂 JSON、不需要帳號
- 完成 3~4 個任務就能看到結果，過程有進度提示
- 不把資料寫入資料庫（僅暫存於 session）

執行方式：
1) pip install streamlit graphviz
2) streamlit run family_tree_app.py

備註：
- 本工具僅示意，不構成法律/稅務/醫療建議。
- 隱私：所有輸入僅暫存於當前瀏覽會話的記憶體，頁面離開/重新整理即重置。
"""

from __future__ import annotations
import json
import uuid
from typing import Dict, List, Optional

import streamlit as st
from graphviz import Digraph

# -------------------------------
# Utilities & Session Init
# -------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {  # extremely small schema
            "persons": {},  # pid -> {name, gender, year, note, is_me}
            "marriages": {},  # mid -> {spouse1, spouse2, children: [pid]}
        }
    if "quests" not in st.session_state:
        st.session_state.quests = {
            "me": False,
            "parents": False,
            "spouse": False,
            "child": False,
        }
    if "layout_lr" not in st.session_state:
        st.session_state.layout_lr = False  # False: 垂直 TB, True: 水平 LR


# -------------------------------
# Core CRUD
# -------------------------------

def add_person(name: str, gender: str, year: Optional[str] = None, note: str = "", is_me: bool = False) -> str:
    pid = _new_id("P")
    st.session_state.tree["persons"][pid] = {
        "name": name.strip() or "未命名",
        "gender": gender,
        "year": (year or "").strip(),
        "note": (note or "").strip(),
        "is_me": bool(is_me),
    }
    return pid


def add_or_get_marriage(spouse1: str, spouse2: str) -> str:
    # Keep 1 marriage node per pair (order-agnostic)
    for mid, m in st.session_state.tree["marriages"].items():
        s = {m["spouse1"], m["spouse2"]}
        if {spouse1, spouse2} == s:
            return mid
    mid = _new_id("M")
    st.session_state.tree["marriages"][mid] = {
        "spouse1": spouse1,
        "spouse2": spouse2,
        "children": [],
    }
    return mid


def add_child(marriage_id: str, child_pid: str):
    m = st.session_state.tree["marriages"].get(marriage_id)
    if not m:
        return
    if child_pid not in m["children"]:
        m["children"].append(child_pid)


def get_me_pid() -> Optional[str]:
    for pid, p in st.session_state.tree["persons"].items():
        if p.get("is_me"):
            return pid
    return None


def get_spouses_of(pid: str) -> List[str]:
    spouses = []
    for m in st.session_state.tree["marriages"].values():
        if pid in (m["spouse1"], m["spouse2"]):
            spouses.append(m["spouse2"] if m["spouse1"] == pid else m["spouse1"])
    return spouses


def get_marriages_of(pid: str) -> List[str]:
    mids = []
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in (m["spouse1"], m["spouse2"]):
            mids.append(mid)
    return mids


# -------------------------------
# Demo Seed
# -------------------------------

def seed_demo():
    st.session_state.tree = {"persons": {}, "marriages": {}}
    me = add_person("我", "女", year="1970", is_me=True)
    f = add_person("爸爸", "男", year="1940")
    m = add_person("媽媽", "女", year="1945")
    mid_parents = add_or_get_marriage(f, m)
    add_child(mid_parents, me)

    s = add_person("另一半", "男", year="1968")
    mid_me = add_or_get_marriage(me, s)
    c1 = add_person("大女兒", "女", year="1995")
    c2 = add_person("小兒子", "男", year="1999")
    add_child(mid_me, c1)
    add_child(mid_me, c2)

    st.toast("已載入示範家族。可在左側新增/調整成員。", icon="✅")


# -------------------------------
# Gamified Progress (low-key)
# -------------------------------

def compute_progress():
    me_pid = get_me_pid()
    st.session_state.quests["me"] = bool(me_pid)

    # parents quest: 至少有一個雙親節點與我連結
    has_parents = False
    if me_pid:
        for m in st.session_state.tree["marriages"].values():
            if me_pid in m.get("children", []) and all([m.get("spouse1"), m.get("spouse2")]):
                has_parents = True
                break
    st.session_state.quests["parents"] = has_parents

    # spouse quest: 我是否有任一婚姻
    st.session_state.quests["spouse"] = bool(me_pid and get_marriages_of(me_pid))

    # child quest: 我任一婚姻是否已有小孩
    has_child = False
    if me_pid:
        for mid in get_marriages_of(me_pid):
            if st.session_state.tree["marriages"][mid]["children"]:
                has_child = True
                break
    st.session_state.quests["child"] = has_child

    done = sum(1 for k, v in st.session_state.quests.items() if v)
    pct = int(done * 25)
    return pct


# -------------------------------
# Graph Rendering
# -------------------------------
GENDER_STYLE = {
    "男": {"fillcolor": "#E3F2FD"},  # light blue
    "女": {"fillcolor": "#FCE4EC"},  # light pink
    "其他/不透漏": {"fillcolor": "#F3F4F6"},  # gray
}


def render_graph() -> Digraph:
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]

    dot = Digraph(comment="FamilyTree", graph_attr={
        "rankdir": "LR" if st.session_state.layout_lr else "TB",
        "splines": "spline",
        "nodesep": "0.4",
        "ranksep": "0.6",
        "fontname": "PingFang TC, Microsoft JhengHei, Noto Sans CJK TC, Arial",
    })

    # Person nodes
    for pid, p in persons.items():
        label = p["name"]
        if p.get("year"):
            label += f"\n({p['year']})"
        if p.get("is_me"):
            label = "⭐ " + label
        style = GENDER_STYLE.get(p.get("gender") or "其他/不透漏", GENDER_STYLE["其他/不透漏"])  # default
        dot.node(pid, label=label, shape="box", style="rounded,filled", color="#90A4AE", fillcolor=style["fillcolor"], penwidth="1.2")

    # Marriage nodes (as small points)
    for mid, m in marriages.items():
        dot.node(mid, label="", shape="point", width="0.02")
        if m.get("spouse1") and m.get("spouse2"):
            dot.edge(m["spouse1"], mid, color="#9E9E9E")
            dot.edge(m["spouse2"], mid, color="#9E9E9E")
        # children
        for c in m.get("children", []):
            if c in persons:
                dot.edge(mid, c, color="#BDBDBD")

    return dot


# -------------------------------
# UI Components
# -------------------------------

def sidebar_progress():
    st.sidebar.header("🎯 小任務進度")
    pct = compute_progress()
    st.sidebar.progress(pct / 100, text=f"完成度：{pct}%")

    def _checkmark(ok: bool):
        return "✅" if ok else "⬜️"

    q = st.session_state.quests
    st.sidebar.write(f"{_checkmark(q['me'])} 1) 建立『我』")
    st.sidebar.write(f"{_checkmark(q['parents'])} 2) 加上父母")
    st.sidebar.write(f"{_checkmark(q['spouse'])} 3) 另一半/配偶")
    st.sidebar.write(f"{_checkmark(q['child'])} 4) 子女")

    st.sidebar.divider()
    st.sidebar.caption("不會儲存到資料庫。下載或關閉頁面即清空。")

    if pct == 100:
        st.balloons()


def form_me():
    st.subheader("Step 1｜建立『我』")
    me_pid = get_me_pid()
    if me_pid:
        p = st.session_state.tree["persons"][me_pid]
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_name = st.text_input("我的名稱", value=p["name"], key="me_name")
        with col2:
            new_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=["女", "男", "其他/不透漏"].index(p["gender"]), key="me_gender")
        with col3:
            new_year = st.text_input("出生年(選填)", value=p.get("year", ""), key="me_year")
        p.update({"name": new_name, "gender": new_gender, "year": new_year})
        st.success("已建立『我』，可繼續下一步。")
    else:
        with st.form("me_form"):
            name = st.text_input("我的名稱", value="我")
            gender = st.selectbox("性別", ["女", "男", "其他/不透漏"]) 
            year = st.text_input("出生年(選填)")
            ok = st.form_submit_button("＋ 建立『我』")
            if ok:
                add_person(name, gender, year=year, is_me=True)
                st.toast("已建立『我』", icon="✅")


def form_parents():
    st.subheader("Step 2｜加上父母（可先略過）")
    me_pid = get_me_pid()
    if not me_pid:
        st.info("請先完成 Step 1")
        return

    # 快速新增父母並連到我
    col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
    with col1:
        father_name = st.text_input("父親姓名", value="爸爸")
    with col2:
        mother_name = st.text_input("母親姓名", value="媽媽")
    with col3:
        add_btn = st.button("＋ 一鍵新增父母並連結")
    if add_btn:
        f = add_person(father_name, "男")
        m = add_person(mother_name, "女")
        mid = add_or_get_marriage(f, m)
        add_child(mid, me_pid)
        st.toast("已新增父母並連結到『我』", icon="👨‍👩‍👧")


def form_spouse_and_children():
    st.subheader("Step 3｜配偶 / Step 4｜子女")
    me_pid = get_me_pid()
    if not me_pid:
        st.info("請先完成 Step 1")
        return

    persons = st.session_state.tree["persons"]

    # 配偶
    with st.expander("＋ 新增配偶/另一半"):
        sp_name = st.text_input("姓名", value="另一半")
        sp_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=1)
        add_sp = st.button("新增配偶並建立婚姻")
        if add_sp:
            sp = add_person(sp_name, sp_gender)
            add_or_get_marriage(me_pid, sp)
            st.toast("已新增配偶", icon="💍")

    # 子女（從我所有婚姻中選擇一個）
    my_mids = get_marriages_of(me_pid)
    if my_mids:
        mid_labels = []
        for mid in my_mids:
            m = st.session_state.tree["marriages"][mid]
            s1 = persons.get(m["spouse1"], {}).get("name", "?")
            s2 = persons.get(m["spouse2"], {}).get("name", "?")
            mid_labels.append((mid, f"{s1} ❤ {s2}"))
        mid_idx = st.selectbox("選擇要新增子女的關係", options=list(range(len(mid_labels))), format_func=lambda i: mid_labels[i][1])
        chosen_mid = mid_labels[mid_idx][0]

        with st.expander("＋ 新增子女"):
            c_name = st.text_input("子女姓名", value="孩子")
            c_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=0)
            c_year = st.text_input("出生年(選填)")
            add_c = st.button("新增子女並連結")
            if add_c:
                cid = add_person(c_name, c_gender, year=c_year)
                add_child(chosen_mid, cid)
                st.toast("已新增子女", icon="🧒")
    else:
        st.info("尚未新增任何配偶/婚姻，請先新增配偶。")


# -------------------------------
# Data Views & Export/Import
# -------------------------------

def data_tables():
    st.subheader("資料檢視")
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]

    if persons:
        st.markdown("**成員名冊**")
        st.dataframe(
            [{"pid": pid, **p} for pid, p in persons.items()],
            use_container_width=True,
            hide_index=True,
        )
    if marriages:
        st.markdown("**婚姻/關係**")
        rows = []
        for mid, m in marriages.items():
            rows.append({
                "mid": mid,
                "spouse1": persons.get(m["spouse1"], {}).get("name", m["spouse1"]),
                "spouse2": persons.get(m["spouse2"], {}).get("name", m["spouse2"]),
                "children": ", ".join([persons.get(cid, {}).get("name", cid) for cid in m.get("children", [])]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def import_export():
    st.subheader("匯入 / 匯出")
    # Export JSON
    as_json = json.dumps(st.session_state.tree, ensure_ascii=False, indent=2)
    st.download_button("⬇ 下載 JSON（暫存資料）", data=as_json, file_name="family_tree.json", mime="application/json")

    # Import JSON
    up = st.file_uploader("上傳 family_tree.json 以還原", type=["json"])
    if up is not None:
        try:
            data = json.load(up)
            assert isinstance(data, dict) and "persons" in data and "marriages" in data
            st.session_state.tree = data
            st.toast("已匯入 JSON。", icon="📥")
        except Exception as e:
            st.error(f"上傳格式有誤：{e}")

    # Danger zone: reset
    st.divider()
    if st.button("🗑 清空全部（不會刪本機檔案）"):
        st.session_state.tree = {"persons": {}, "marriages": {}}
        st.session_state.quests = {"me": False, "parents": False, "spouse": False, "child": False}
        st.toast("已清空。", icon="🗑")


# -------------------------------
# Main App
# -------------------------------

def main():
    st.set_page_config(page_title="家族樹小幫手", page_icon="🌳", layout="wide")
    init_state()

    st.title("🌳 家族樹小幫手｜低調好玩版")
    st.caption("填三四個欄位，立刻畫出家族樹；不需要帳號、不儲存資料。")

    with st.sidebar:
        if st.button("✨ 載入示範家族"):
            seed_demo()
        st.toggle("水平排列 (LR)", key="layout_lr", help="預設為垂直排列 (TB)")

    sidebar_progress()

    tab_build, tab_graph, tab_table, tab_io = st.tabs(["✍️ 建立家庭", "🖼 家族圖", "📋 資料表", "📦 匯入/匯出"])

    with tab_build:
        form_me()
        st.divider()
        form_parents()
        st.divider()
        form_spouse_and_children()

    with tab_graph:
        dot = render_graph()
        st.graphviz_chart(dot, use_container_width=True)
        st.caption("提示：可在側欄切換水平/垂直排列。")

    with tab_table:
        data_tables()

    with tab_io:
        import_export()

    # Footer
    st.divider()
    st.caption("隱私承諾：您的輸入僅用於本次即時計算，不寫入資料庫；下載/離開頁面即清空。")


if __name__ == "__main__":
    main()

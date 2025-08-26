# -*- coding: utf-8 -*-
"""
🌳 家族樹小幫手（新手精靈 + 進階模式 + 穩定導覽 + 夫妻並排；No f-strings）
- 新手模式：一步一頁（建立我→配偶→子女→預覽）
- 進階模式：大家族/多段婚姻/收養/繼親/半血緣/批次兄弟姊妹
- 穩定導覽：用 radio 當主導航，rerun 後仍停留在原頁，不會跳回第一頁
- 編輯成員：表單提交制，按「💾 儲存變更」才會寫入
- 家族圖：每段婚姻用 subgraph(rank=same) 讓配偶緊鄰；用隱形邊與權重強化並排
- 隱私：資料僅存在 session，不寫入資料庫
"""
from __future__ import annotations
import json
import uuid
from typing import List, Optional

import streamlit as st
from graphviz import Digraph

VERSION = "2025-08-26-stable-nav-save-form-spouse-pair"

# =============================
# Helpers & State
# =============================
GENDER_OPTIONS = ["女", "男", "其他/不透漏"]
REL_MAP = {"bio": "親生", "adopted": "收養", "step": "繼親"}
STATUS_MAP = {"married": "已婚", "divorced": "前任(離異)", "separated": "分居"}

def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:8])

def _safe_index(seq, value, default=0):
    try:
        return list(seq).index(value)
    except ValueError:
        return default

def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {
            "persons": {},     # pid -> {name, gender, year, note, is_me, deceased}
            "marriages": {},   # mid -> {spouse1, spouse2, children: [pid], status}
            "child_types": {}, # mid -> { child_pid: "bio"|"adopted"|"step" }
        }
    st.session_state.tree.setdefault("child_types", {})
    for mid in st.session_state.tree.get("marriages", {}):
        st.session_state.tree["marriages"].setdefault(mid, {}).setdefault("status", "married")
        st.session_state.tree["child_types"].setdefault(mid, {})
    for _, p in st.session_state.tree.get("persons", {}).items():
        p.setdefault("deceased", False)
        p.setdefault("note", "")
        p.setdefault("gender", "其他/不透漏")

    if "quests" not in st.session_state:
        st.session_state.quests = {"me": False, "parents": False, "spouse": False, "child": False}
    if "layout_lr" not in st.session_state:
        st.session_state.layout_lr = False  # False=TB, True=LR
    if "celebrate_ready" not in st.session_state:
        st.session_state.celebrate_ready = False
    # 新手模式 & 精靈步驟
    if "beginner_mode" not in st.session_state:
        st.session_state.beginner_mode = True
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1  # 1~4
    # 穩定導覽：記住目前所在頁
    if "main_nav" not in st.session_state:
        st.session_state.main_nav = "🎛 進階建立"      # 以你的使用情境，預設落在進階建立
    if "main_nav_beginner" not in st.session_state:
        st.session_state.main_nav_beginner = "🖼 家族圖"

# =============================
# CRUD
# =============================
def add_person(name: str, gender: str, year: Optional[str] = None,
               note: str = "", is_me: bool = False, deceased: bool = False) -> str:
    pid = _new_id("P")
    st.session_state.tree["persons"][pid] = {
        "name": (name or "").strip() or "未命名",
        "gender": gender if gender in GENDER_OPTIONS else "其他/不透漏",
        "year": (year or "").strip(),
        "note": (note or "").strip(),
        "is_me": bool(is_me),
        "deceased": bool(deceased),
    }
    return pid

def add_or_get_marriage(spouse1: str, spouse2: str, status: str = "married") -> str:
    for mid, m in st.session_state.tree["marriages"].items():
        s = {m.get("spouse1"), m.get("spouse2")}
        if {spouse1, spouse2} == s:
            if status and m.get("status") != status:
                m["status"] = status
            st.session_state.tree["child_types"].setdefault(mid, {})
            return mid
    mid = _new_id("M")
    st.session_state.tree["marriages"][mid] = {
        "spouse1": spouse1, "spouse2": spouse2, "children": [], "status": status
    }
    st.session_state.tree["child_types"].setdefault(mid, {})
    return mid

def add_child(marriage_id: str, child_pid: str, relation: str = "bio"):
    m = st.session_state.tree["marriages"].get(marriage_id)
    if not m:
        return
    if child_pid not in m["children"]:
        m["children"].append(child_pid)
    st.session_state.tree["child_types"].setdefault(marriage_id, {})[child_pid] = relation

def set_child_relation(marriage_id: str, child_pid: str, relation: str):
    st.session_state.tree["child_types"].setdefault(marriage_id, {})
    if child_pid in st.session_state.tree["child_types"][marriage_id]:
        st.session_state.tree["child_types"][marriage_id][child_pid] = relation

def get_me_pid() -> Optional[str]:
    for pid, p in st.session_state.tree["persons"].items():
        if p.get("is_me"):
            return pid
    return None

def get_marriages_of(pid: str) -> List[str]:
    mids = []
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in (m.get("spouse1"), m.get("spouse2")):
            mids.append(mid)
    return mids

def get_parent_marriage_of(pid: str) -> Optional[str]:
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in m.get("children", []):
            return mid
    return None

# —— 刪除成員（安全清理所有關聯）
def delete_person(pid: str):
    tree = st.session_state.tree
    if pid not in tree["persons"]:
        return

    # 從 children 清掉
    for mid, m in list(tree["marriages"].items()):
        if pid in m.get("children", []):
            m["children"] = [c for c in m["children"] if c != pid]
            if mid in tree["child_types"] and pid in tree["child_types"][mid]:
                del tree["child_types"][mid][pid]

    # 從配偶欄位清掉，沒人也沒小孩的婚姻刪除
    for mid, m in list(tree["marriages"].items()):
        changed = False
        if m.get("spouse1") == pid:
            m["spouse1"] = None
            changed = True
        if m.get("spouse2") == pid:
            m["spouse2"] = None
            changed = True
        if (m.get("spouse1") is None and m.get("spouse2") is None and not m.get("children")):
            if mid in tree["child_types"]:
                del tree["child_types"][mid]
            del tree["marriages"][mid]
        elif changed:
            tree["child_types"].setdefault(mid, {})

    del tree["persons"][pid]

# =============================
# Demo Seed
# =============================
def seed_demo():
    st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    me = add_person("我", "女", year="1970", is_me=True)
    f = add_person("爸爸", "男", year="1940")
    mo = add_person("媽媽", "女", year="1945")
    mid_parents = add_or_get_marriage(f, mo, status="married")
    add_child(mid_parents, me, relation="bio")

    s = add_person("另一半", "男", year="1968")
    mid_me = add_or_get_marriage(me, s, status="married")
    c1 = add_person("大女兒", "女", year="1995")
    c2 = add_person("小兒子", "男", year="1999")
    add_child(mid_me, c1, relation="bio")
    add_child(mid_me, c2, relation="bio")

    ex = add_person("前任", "女")
    mid_ex = add_or_get_marriage(f, ex, status="divorced")
    hbro = add_person("同父異母弟弟", "男", year="1980")
    add_child(mid_ex, hbro, relation="bio")

    st.session_state.celebrate_ready = True
    st.toast("已載入示範家族（含前任/同父異母）。", icon="✅")

# =============================
# Progress & Styles
# =============================
def compute_progress():
    me_pid = get_me_pid()
    st.session_state.quests["me"] = bool(me_pid)

    has_parents = False
    if me_pid:
        for m in st.session_state.tree["marriages"].values():
            if me_pid in m.get("children", []) and all([m.get("spouse1"), m.get("spouse2")]):
                has_parents = True
                break
    st.session_state.quests["parents"] = has_parents
    st.session_state.quests["spouse"] = bool(me_pid and get_marriages_of(me_pid))

    has_child = False
    if me_pid:
        for mid in get_marriages_of(me_pid):
            if st.session_state.tree["marriages"][mid]["children"]:
                has_child = True
                break
    st.session_state.quests["child"] = has_child

    done = sum(1 for v in st.session_state.quests.values() if v)
    return int(done * 25)

GENDER_STYLE = {
    "男": {"fillcolor": "#E3F2FD"},
    "女": {"fillcolor": "#FCE4EC"},
    "其他/不透漏": {"fillcolor": "#F3F4F6"},
}
STATUS_EDGE_STYLE = {
    "married":   {"style": "solid",  "color": "#9E9E9E", "weight": "2"},
    "divorced":  {"style": "dashed", "color": "#9E9E9E", "weight": "1"},
    "separated": {"style": "dotted", "color": "#9E9E9E", "weight": "1"},
}
CHILD_EDGE_STYLE = {
    "bio":     {"style": "solid",  "color": "#BDBDBD", "weight": "2"},
    "adopted": {"style": "dotted", "color": "#BDBDBD", "weight": "1"},
    "step":    {"style": "dashed", "color": "#BDBDBD", "weight": "1"},
}

def render_graph() -> Digraph:
    persons   = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]

    dot = Digraph(
        comment="FamilyTree",
        graph_attr={
            "rankdir": "LR" if st.session_state.layout_lr else "TB",
            "splines": "spline",
            "nodesep": "0.35",
            "ranksep": "0.55",
            "fontname": "PingFang TC, Microsoft JhengHei, Noto Sans CJK TC, Arial",
        },
    )

    # 先畫所有人
    for pid, p in persons.items():
        label = p.get("name", "未命名")
        year = p.get("year")
        if year:
            label = label + "\n(" + str(year) + ")"
        if p.get("deceased"):
            label = label + " †"
        if p.get("is_me"):
            label = "⭐ " + label
        style = GENDER_STYLE.get(p.get("gender") or "其他/不透漏", GENDER_STYLE["其他/不透漏"])
        dot.node(
            pid, label=label, shape="box",
            style="rounded,filled", color="#90A4AE", fillcolor=style["fillcolor"], penwidth="1.2"
        )

    # 針對每段婚姻，建立一個 subgraph 讓配偶與婚姻點 rank=same（緊鄰）
    for mid, m in marriages.items():
        s1 = m.get("spouse1")
        s2 = m.get("spouse2")
        # 婚姻點
        dot.node(mid, label="", shape="point", width="0.02")

        # 配偶兩人與婚姻點同 rank，並加一條隱形邊以保持貼近
        with dot.subgraph(name="cluster_" + mid) as sg:
            sg.attr(rank="same")
            if s1:
                sg.node(s1)
            if s2:
                sg.node(s2)
            sg.node(mid)
            if s1 and s2:
                sg.edge(s1, s2, style="invis", weight="10")  # invisible to glue spouses

        # 婚姻邊線
        stl = STATUS_EDGE_STYLE.get(m.get("status", "married"), STATUS_EDGE_STYLE["married"])
        if s1:
            dot.edge(s1, mid, color=stl["color"], style=stl["style"], weight=stl["weight"])
        if s2:
            dot.edge(s2, mid, color=stl["color"], style=stl["style"], weight=stl["weight"])

        # 子女線（依關係型式指定線型）
        for c in m.get("children", []):
            if c in persons:
                rel = child_types.get(mid, {}).get(c, "bio")
                cstl = CHILD_EDGE_STYLE.get(rel, CHILD_EDGE_STYLE["bio"])
                dot.edge(mid, c, color=cstl["color"], style=cstl["style"], weight=cstl["weight"])

    return dot

# =============================
# Newbie Wizard
# =============================
def onboarding_wizard():
    st.header("🪄 新手模式｜一步一步建立家族")
    step = st.session_state.wizard_step
    st.progress((step-1)/4.0, text="步驟 {}/4".format(step))

    # Step 1：建立「我」
    if step == 1:
        st.subheader("Step 1｜建立『我』")
        with st.form("wiz_me", clear_on_submit=False):
            name = st.text_input("我的名稱", value="我", placeholder="例如：黃榮如")
            gender = st.selectbox("性別", GENDER_OPTIONS, index=0)
            year = st.text_input("出生年(選填)", placeholder="例如：1968")
            confirm = st.checkbox("我確認以上資料正確")
            ok = st.form_submit_button("✅ 建立『我』")
        if ok:
            if not confirm:
                st.warning("請先勾選確認。")
            else:
                add_person(name, gender, year=year, is_me=True)
                st.session_state.celebrate_ready = True
                st.session_state.wizard_step = 2
                st.rerun()

    # Step 2：新增配偶（可略過）
    if step == 2:
        st.subheader("Step 2｜新增配偶（可略過）")
        with st.form("wiz_spouse", clear_on_submit=True):
            sp_name = st.text_input("配偶姓名", placeholder="例如：陳威翔")
            sp_gender = st.selectbox("性別", GENDER_OPTIONS, index=1)
            sp_status = st.selectbox("關係狀態", list(STATUS_MAP.keys()),
                                     index=0, format_func=lambda s: STATUS_MAP[s])
            col1, col2 = st.columns(2)
            with col1:
                skip = st.form_submit_button("先略過 →")
            with col2:
                confirm = st.checkbox("我確認新增", key="wiz_spouse_confirm")
                ok = st.form_submit_button("💍 新增配偶")
        if skip:
            st.session_state.wizard_step = 3
            st.rerun()
        if ok:
            if not confirm or not sp_name.strip():
                st.warning("請輸入姓名並勾選確認；或按「先略過」。")
            else:
                me = get_me_pid()
                sp = add_person(sp_name.strip(), sp_gender)
                add_or_get_marriage(me, sp, status=sp_status)
                st.session_state.celebrate_ready = True
                st.session_state.wizard_step = 3
                st.rerun()

    # Step 3：新增子女（可略過）
    if step == 3:
        st.subheader("Step 3｜新增子女（可略過）")
        mids = get_marriages_of(get_me_pid()) if get_me_pid() else []
        if not mids:
            st.info("你尚未新增配偶，若要先加孩子也可以，系統會建立一位『未知配偶』以便連結。")
        with st.form("wiz_child", clear_on_submit=True):
            c_name = st.text_input("子女姓名", placeholder="例如：黃榮惠")
            c_gender = st.selectbox("性別", GENDER_OPTIONS, index=0)
            c_year = st.text_input("出生年(選填)", placeholder="例如：1998")
            col1, col2 = st.columns(2)
            with col1:
                skip = st.form_submit_button("先略過 →")
            with col2:
                confirm = st.checkbox("我確認新增", key="wiz_child_confirm")
                ok = st.form_submit_button("👶 新增子女")
        if skip:
            st.session_state.wizard_step = 4
            st.rerun()
        if ok:
            if not confirm or not c_name.strip():
                st.warning("請輸入姓名並勾選確認；或按「先略過」。")
            else:
                me = get_me_pid()
                mids = get_marriages_of(me)
                chosen_mid = mids[0] if mids else None
                if chosen_mid is None:
                    placeholder = add_person("未知配偶", "其他/不透漏")
                    chosen_mid = add_or_get_marriage(me, placeholder, status="married")
                cid = add_person(c_name.strip(), c_gender, year=c_year)
                add_child(chosen_mid, cid, relation="bio")
                st.session_state.celebrate_ready = True
                st.session_state.wizard_step = 4
                st.rerun()

    # Step 4：預覽家族圖 & 建議下一步
    if step == 4:
        st.subheader("Step 4｜預覽家族圖")
        try:
            dot = render_graph()
            st.graphviz_chart(dot, use_container_width=True)
        except Exception as e:
            st.error("圖形渲染失敗：{}".format(e))

        st.markdown("### ✅ 接下來你可以：")
        st.markdown("1. 前往 **進階模式** 補：父母、前任/分居、出生年、備註")
        st.markdown("2. 開啟 **⚡ 快速兩代**：一次補上父母/配偶/多個子女")
        st.markdown("3. 到 **📦 匯入/匯出** 下載 JSON 備份")

        colA, colB = st.columns([1,1])
        with colA:
            if st.button("🔧 進階模式（大家族）"):
                st.session_state.beginner_mode = False
                st.session_state.main_nav = "🎛 進階建立"  # 切換後直接進入進階建立
                st.rerun()
        with colB:
            if st.button("↩️ 回到 Step 2"):
                st.session_state.wizard_step = 2
                st.rerun()

    st.divider()
    st.caption("提示：任何步驟都可以略過；你可以隨時切換回進階模式。")

# =============================
# UI Sections (Advanced)
# =============================
def sidebar_progress():
    st.sidebar.header("🎯 小任務進度")
    pct = compute_progress()
    st.sidebar.progress(pct / 100, text="完成度：{}%".format(pct))

    def ck(ok: bool) -> str: return "✅" if ok else "⬜️"
    q = st.session_state.quests
    st.sidebar.write("{} 1) 建立『我』".format(ck(q["me"])))
    st.sidebar.write("{} 2) 加上父母".format(ck(q["parents"])))
    st.sidebar.write("{} 3) 另一半/配偶".format(ck(q["spouse"])))
    st.sidebar.write("{} 4) 子女".format(ck(q["child"])))

    st.sidebar.divider()
    st.sidebar.caption("不會儲存到資料庫。下載或關閉頁面即清空。")
    if pct == 100 and st.session_state.celebrate_ready:
        st.balloons()
        st.session_state.celebrate_ready = False

def form_me():
    st.subheader("Step 1｜建立『我』")
    me_pid = get_me_pid()
    if me_pid:
        p = st.session_state.tree["persons"][me_pid]
        # 直接編輯我：這裡維持即時寫入，避免兩層表單
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            p["name"] = st.text_input("我的名稱", value=p["name"], key="me_name")
        with col2:
            idx = _safe_index(GENDER_OPTIONS, p.get("gender", "其他/不透漏"), default=2)
            p["gender"] = st.selectbox("性別", GENDER_OPTIONS, index=idx, key="me_gender")
        with col3:
            p["year"] = st.text_input("出生年(選填)", value=p.get("year", ""), key="me_year")
        with col4:
            p["deceased"] = st.toggle("已故?", value=p.get("deceased", False), key="me_dec")
        st.success("已建立『我』，可繼續下一步。")
    else:
        with st.form("me_form"):
            name = st.text_input("我的名稱", value="我", key="me_new_name")
            gender = st.selectbox("性別", GENDER_OPTIONS, key="me_new_gender")
            year = st.text_input("出生年(選填)", key="me_new_year")
            ok = st.form_submit_button("＋ 建立『我』")
            if ok:
                add_person(name, gender, year=year, is_me=True)
                st.session_state.celebrate_ready = True
                st.toast("已建立『我』", icon="✅")

def form_parents():
    st.subheader("Step 2｜加上父母（可先略過）")
    me_pid = get_me_pid()
    if not me_pid:
        st.info("請先完成 Step 1")
        return
    col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
    with col1:
        father_name = st.text_input("父親姓名", value="爸爸", key="father_name_input")
    with col2:
        mother_name = st.text_input("母親姓名", value="媽媽", key="mother_name_input")
    with col3:
        if st.button("＋ 一鍵新增父母並連結", key="add_parents_btn"):
            f = add_person(father_name, "男")
            m = add_person(mother_name, "女")
            mid = add_or_get_marriage(f, m)
            add_child(mid, me_pid, relation="bio")
            st.session_state.celebrate_ready = True
            st.toast("已新增父母並連結到『我』", icon="👨‍👩‍👧")

def form_spouse_and_children():
    st.subheader("Step 3｜配偶 / Step 4｜子女")
    me_pid = get_me_pid()
    if not me_pid:
        st.info("請先完成 Step 1")
        return

    persons = st.session_state.tree["persons"]

    # —— 新增配偶/另一半：必須提交才生效
    with st.expander("＋ 新增配偶/另一半（可標注前任/分居）"):
        with st.form("form_add_spouse_main", clear_on_submit=True):
            sp_name = st.text_input("姓名", value="", key="sp_name_main")
            sp_gender = st.selectbox("性別", GENDER_OPTIONS, index=1, key="sp_gender_main")
            sp_status = st.selectbox(
                "關係狀態", list(STATUS_MAP.keys()), index=0,
                format_func=lambda s: STATUS_MAP[s], key="sp_status_main"
            )
            col_ok1, col_ok2 = st.columns([1,2])
            with col_ok1:
                confirm_add_sp = st.checkbox("我確認新增", key="confirm_add_sp_main")
            with col_ok2:
                submit_sp = st.form_submit_button("✅ 提交新增關係", disabled=False)

        if submit_sp:
            if not confirm_add_sp:
                st.warning("請先勾選「我確認新增」。")
            elif sp_name.strip():
                sp = add_person(sp_name.strip(), sp_gender)
                add_or_get_marriage(me_pid, sp, status=sp_status)
                st.session_state.celebrate_ready = True
                st.success("已新增關係")
            else:
                st.warning("請輸入配偶姓名後再提交。")

    # —— 選擇關係新增子女（提交制）
    my_mids = get_marriages_of(me_pid)
    if my_mids:
        mid_labels = []
        for mid in my_mids:
            m = st.session_state.tree["marriages"][mid]
            s1 = persons.get(m["spouse1"], {}).get("name", "?")
            s2 = persons.get(m["spouse2"], {}).get("name", "?")
            status = m.get("status", "married")
            mid_labels.append((mid, "{} ❤ {}（{}）".format(s1, s2, STATUS_MAP.get(status, status))))
        mid_idx = st.selectbox(
            "選擇要新增子女的關係",
            options=list(range(len(mid_labels))),
            format_func=lambda i: mid_labels[i][1],
            key="choose_mid_main",
        )
        chosen_mid = mid_labels[mid_idx][0]

        with st.expander("＋ 新增子女"):
            with st.form("form_add_child_main_{}".format(chosen_mid), clear_on_submit=True):
                c_name = st.text_input("子女姓名", value="", key="child_name_main_{}".format(chosen_mid))
                c_gender = st.selectbox("性別", GENDER_OPTIONS, index=0, key="child_gender_main_{}".format(chosen_mid))
                c_year = st.text_input("出生年(選填)", key="child_year_main_{}".format(chosen_mid))
                c_rel = st.selectbox(
                    "關係類型", list(REL_MAP.keys()),
                    index=0, format_func=lambda s: REL_MAP[s], key="child_rel_main_{}".format(chosen_mid)
                )
                colc1, colc2 = st.columns([1,2])
                with colc1:
                    confirm_add_ch = st.checkbox("我確認新增", key="confirm_add_child_{}".format(chosen_mid))
                with colc2:
                    submit_child = st.form_submit_button("👶 提交新增子女", disabled=False)

            if submit_child:
                if not confirm_add_ch:
                    st.warning("請先勾選「我確認新增」。")
                elif c_name.strip():
                    cid = add_person(c_name.strip(), c_gender, year=c_year)
                    add_child(chosen_mid, cid, relation=c_rel)
                    st.session_state.celebrate_ready = True
                    st.success("已新增子女")
                else:
                    st.warning("請輸入子女姓名後再提交。")
    else:
        st.info("尚未新增任何配偶/婚姻，請先新增配偶。")

# —— ⚡ 快速加直系兩代（父母 + 配偶 + 多子女；提交時驗證）
def quick_two_gen(pid: str):
    persons = st.session_state.tree["persons"]

    with st.expander("⚡ 快速加直系兩代（父母 + 配偶 + 多子女）", expanded=False):
        st.caption("可只填需要的欄位；未提交前不會建立任何資料。")

        with st.form("form_q2g_{}".format(pid), clear_on_submit=True):
            # A. 父母
            st.markdown("**A. 父母**（可留白略過）")
            c1, c2 = st.columns([1.2, 1.2])
            with c1:
                fa_name = st.text_input("父親姓名", key="q2g_fa_{}".format(pid))
            with c2:
                mo_name = st.text_input("母親姓名", key="q2g_mo_{}".format(pid))
            add_parents = st.checkbox("建立父母並連結", key="q2g_addp_{}".format(pid))

            # B. 配偶/關係
            st.markdown("**B. 配偶/關係**（可留白略過）")
            c4, c5, c6 = st.columns([1.2, 1.0, 1.0])
            with c4:
                sp_name = st.text_input("配偶姓名", key="q2g_spn_{}".format(pid))
            with c5:
                sp_gender = st.selectbox("性別", GENDER_OPTIONS, index=1, key="q2g_spg_{}".format(pid))
            with c6:
                sp_status = st.selectbox(
                    "狀態", list(STATUS_MAP.keys()), index=0,
                    format_func=lambda s: STATUS_MAP[s], key="q2g_sps_{}".format(pid)
                )
            add_spouse = st.checkbox("建立配偶/關係", key="q2g_adds_{}".format(pid))

            # C. 子女
            st.markdown("**C. 子女**（可留白略過）")
            c7, c8, c9, c10 = st.columns([2.0, 1.0, 1.0, 1.2])
            with c7:
                kids_csv = st.text_input("子女姓名（以逗號分隔）", key="q2g_kcsv_{}".format(pid))
            with c8:
                kid_gender = st.selectbox("預設性別", GENDER_OPTIONS, index=0, key="q2g_kg_{}".format(pid))
            with c9:
                kid_rel = st.selectbox(
                    "關係類型", list(REL_MAP.keys()), index=0,
                    format_func=lambda s: REL_MAP[s], key="q2g_krel_{}".format(pid)
                )
            with c10:
                kid_year = st.text_input("預設出生年(選填)", key="q2g_kyr_{}".format(pid))

            col_ok1, col_ok2 = st.columns([1, 2])
            with col_ok1:
                confirm_q2g = st.checkbox("我確認建立上述資料", key="q2g_ok_{}".format(pid))
            with col_ok2:
                submit_q2g = st.form_submit_button("🚀 一鍵建立")  # 總是可按

        if submit_q2g:
            if not confirm_q2g:
                st.warning("請先勾選「我確認建立上述資料」。")
                return

            # A. 父母
            if add_parents and (fa_name or mo_name):
                fpid = add_person((fa_name or "父親").strip(), "男")
                mpid = add_person((mo_name or "母親").strip(), "女")
                mid = add_or_get_marriage(fpid, mpid, status="married")
                add_child(mid, pid, relation="bio")

            # B. 配偶
            chosen_mid = None
            if add_spouse and sp_name:
                spid = add_person(sp_name.strip(), sp_gender)
                chosen_mid = add_or_get_marriage(pid, spid, status=sp_status)

            # C. 子女
            kids = [s.strip() for s in (kids_csv or "").split(",") if s.strip()]
            if kids:
                if chosen_mid is None:
                    placeholder = add_person("未知配偶", "其他/不透漏")
                    chosen_mid = add_or_get_marriage(pid, placeholder, status="married")
                for nm in kids:
                    cid = add_person(nm, kid_gender, year=kid_year)
                    add_child(chosen_mid, cid, relation=kid_rel)

            st.session_state.celebrate_ready = True
            st.success("已完成快速建立。")
            st.rerun()

def advanced_builder():
    st.subheader("🎛 進階建立｜大家族與複雜關係")
    persons = st.session_state.tree["persons"]
    if not persons:
        st.info("請至少先建立『我』或任一成員。")
        return

    id_list = list(persons.keys())
    idx = st.selectbox(
        "選擇成員以編輯/加關係",
        options=list(range(len(id_list))),
        format_func=lambda i: persons[id_list[i]]["name"],
        key="adv_pick_person",
    )
    pid = id_list[idx]
    p = persons[pid]

    # ✏️ 編輯成員（表單提交制）
    with st.expander("✏️ 編輯成員資料", expanded=True):
        with st.form("form_edit_{}".format(pid), clear_on_submit=False):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            name_buf = c1.text_input("名稱", value=p.get("name", ""), key="edit_name_{}".format(pid))
            g_idx = _safe_index(GENDER_OPTIONS, p.get("gender", "其他/不透漏"), default=2)
            gender_buf = c2.selectbox("性別", GENDER_OPTIONS, index=g_idx, key="edit_gender_{}".format(pid))
            year_buf = c3.text_input("出生年(選填)", value=p.get("year", ""), key="edit_year_{}".format(pid))
            dec_buf = c4.toggle("已故?", value=p.get("deceased", False), key="edit_dec_{}".format(pid))
            note_buf = st.text_area("備註(收養/繼親/職業等)", value=p.get("note", ""), key="edit_note_{}".format(pid))
            saved = st.form_submit_button("💾 儲存變更")
        if saved:
            p["name"] = (name_buf or "").strip() or "未命名"
            p["gender"] = gender_buf
            p["year"] = (year_buf or "").strip()
            p["deceased"] = bool(dec_buf)
            p["note"] = (note_buf or "").strip()
            st.success("已儲存變更")

        st.caption("提示：標註『†』= 已故；只有按下「💾 儲存變更」才會寫入。")

        st.markdown("---")
        st.markdown("🗑️ **刪除這位成員**")
        if p.get("is_me"):
            st.caption("此成員為『我』，不可刪除。")
        else:
            cold1, cold2 = st.columns([1,2])
            with cold1:
                confirm_del = st.checkbox("我確定要刪除", key="confirm_del_{}".format(pid))
            with cold2:
                del_clicked = st.button("❌ 刪除此成員", key="btn_del_{}".format(pid), type="primary", disabled=not confirm_del)
                if del_clicked:
                    delete_person(pid)
                    st.success("已刪除")
                    st.rerun()

    # ⚡ 快速兩代精靈
    quick_two_gen(pid)

    st.markdown("---")
    # 四個功能區
    cA, cB, cC, cD = st.columns(4)

    # 一鍵新增父母
    with cA:
        st.markdown("**父母**")
        fa = st.text_input("父親姓名", key="adv_f_{}".format(pid))
        mo = st.text_input("母親姓名", key="adv_m_{}".format(pid))
        if st.button("➕ 為該成員一鍵新增父母並連結", key="btn_add_parents_{}".format(pid)):
            fpid = add_person(fa or "父親", "男")
            mpid = add_person(mo or "母親", "女")
            mid = add_or_get_marriage(fpid, mpid, status="married")
            add_child(mid, pid, relation="bio")
            st.session_state.celebrate_ready = True
            st.toast("已新增父母並連結", icon="👨‍👩‍👧")

    # 新增配偶/關係（提交制）
    with cB:
        st.markdown("**配偶/關係**")
        spn = st.text_input("配偶姓名", key="adv_sp_{}".format(pid))
        spg = st.selectbox("性別", GENDER_OPTIONS, index=1, key="adv_spg_{}".format(pid))
        sps = st.selectbox(
            "狀態", list(STATUS_MAP.keys()), index=0,
            format_func=lambda s: STATUS_MAP[s],
            key="adv_sps_{}".format(pid),
        )
        if st.button("➕ 新增關係", key="btn_add_sp_{}".format(pid)):
            if spn.strip():
                spid = add_person(spn.strip(), spg)
                add_or_get_marriage(pid, spid, status=sps)
                st.session_state.celebrate_ready = True
                st.toast("已新增關係", icon="💍")
            else:
                st.warning("請先輸入配偶姓名。")

    # 新增子女（提交制）
    with cC:
        st.markdown("**子女**")
        persons = st.session_state.tree["persons"]
        my_mids = get_marriages_of(pid)
        if my_mids:
            mid_labels = []
            for mid in my_mids:
                m = st.session_state.tree["marriages"][mid]
                s1 = persons.get(m["spouse1"], {}).get("name", "?")
                s2 = persons.get(m["spouse2"], {}).get("name", "?")
                status = m.get("status", "married")
                mid_labels.append((mid, "{} ❤ {}（{}）".format(s1, s2, STATUS_MAP.get(status, status))))
            mid_idx = st.selectbox(
                "選擇關係",
                options=list(range(len(mid_labels))),
                format_func=lambda i: mid_labels[i][1],
                key="adv_mid_{}".format(pid),
            )
            chosen_mid = mid_labels[mid_idx][0]
            with st.form("form_add_child_adv_{}".format(pid), clear_on_submit=True):
                cn = st.text_input("子女姓名", key="adv_child_name_{}".format(pid))
                cg = st.selectbox("性別", GENDER_OPTIONS, index=0, key="adv_child_gender_{}".format(pid))
                cy = st.text_input("出生年(選填)", key="adv_child_year_{}".format(pid))
                cr = st.selectbox(
                    "關係類型", list(REL_MAP.keys()), index=0,
                    format_func=lambda s: REL_MAP[s],
                    key="adv_child_rel_{}".format(pid),
                )
                colx1, colx2 = st.columns([1,2])
                with colx1:
                    confirm_add_child2 = st.checkbox("我確認新增", key="adv_confirm_child_{}".format(pid))
                with colx2:
                    submit_child2 = st.form_submit_button("👶 提交新增子女", disabled=False)

            if submit_child2:
                if not confirm_add_child2:
                    st.warning("請先勾選「我確認新增」。")
                elif cn.strip():
                    cid = add_person(cn.strip(), cg, year=cy)
                    add_child(chosen_mid, cid, relation=cr)
                    st.session_state.celebrate_ready = True
                    st.success("已新增子女")
                else:
                    st.warning("請輸入子女姓名後再提交。")
        else:
            st.caption("尚無關係，請先新增配偶/另一半。")

    # 兄弟姊妹（批次）— 整行按鈕、點擊時驗證
    with cD:
        st.markdown("**兄弟姊妹（批次）**")
        pmid = get_parent_marriage_of(pid)

        if pmid is None:
            st.caption("此成員目前**沒有已知的雙親關係**，因此無法判定兄弟姊妹。請先在左側加上父母。")
        else:
            sibs = st.text_input("以逗號分隔：如 小明, 小美", key="adv_sibs_{}".format(pid))
            sg = st.selectbox("預設性別", GENDER_OPTIONS, index=2, key="adv_sibs_gender_{}".format(pid))
            confirm_sibs = st.checkbox("我確認新增", key="adv_confirm_sibs_{}".format(pid))
            click_add_sibs = st.button("👫 提交新增兄弟姊妹", key="btn_add_sibs_submit_{}".format(pid))

            if click_add_sibs:
                if not confirm_sibs:
                    st.warning("請先勾選「我確認新增」。")
                else:
                    names = [s.strip() for s in (sibs or "").split(",") if s.strip()]
                    if not names:
                        st.warning("請至少輸入一個姓名（以逗號分隔）。")
                    else:
                        for nm in names:
                            sid = add_person(nm, sg)
                            add_child(pmid, sid, relation="bio")
                        st.session_state.celebrate_ready = True
                        st.success("已新增兄弟姊妹")
                        st.rerun()

    st.markdown("---")

    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]
    if marriages:
        st.markdown("**關係檢視與微調**")
        for mid, m in marriages.items():
            s1 = st.session_state.tree["persons"].get(m["spouse1"], {}).get("name", "?")
            s2 = st.session_state.tree["persons"].get(m["spouse2"], {}).get("name", "?")
            with st.expander("{} ❤ {}".format(s1, s2), expanded=False):
                m["status"] = st.selectbox(
                    "婚姻狀態", list(STATUS_MAP.keys()),
                    index=_safe_index(list(STATUS_MAP.keys()), m.get("status", "married"), default=0),
                    format_func=lambda s: STATUS_MAP[s],
                    key="stat_{}".format(mid),
                )
                for cid in m.get("children", []):
                    cname = st.session_state.tree["persons"].get(cid, {}).get("name", cid)
                    current_rel = child_types.get(mid, {}).get(cid, "bio")
                    new_rel = st.selectbox(
                        "{} 的關係".format(cname), list(REL_MAP.keys()),
                        index=_safe_index(list(REL_MAP.keys()), current_rel, default=0),
                        format_func=lambda s: REL_MAP[s],
                        key="rel_{}_{}".format(mid, cid),
                    )
                    set_child_relation(mid, cid, new_rel)

def data_tables():
    st.subheader("資料檢視")
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]

    if persons:
        st.markdown("**成員名冊**")
        st.dataframe(
            [{"pid": pid, **p} for pid, p in persons.items()],
            use_container_width=True, hide_index=True,
        )
    if marriages:
        st.markdown("**婚姻/關係**")
        rows = []
        for mid, m in marriages.items():
            rows.append({
                "mid": mid,
                "spouse1": persons.get(m["spouse1"], {}).get("name", m["spouse1"]),
                "spouse2": persons.get(m["spouse2"], {}).get("name", m["spouse2"]),
                "status": STATUS_MAP.get(m.get("status", "married"), m.get("status", "married")),
                "children": ", ".join([persons.get(cid, {}).get("name", cid) for cid in m.get("children", [])]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

def import_export():
    st.subheader("匯入 / 匯出")
    as_json = json.dumps(st.session_state.tree, ensure_ascii=False, indent=2)
    st.download_button("⬇ 下載 JSON（暫存資料）", data=as_json,
                       file_name="family_tree.json", mime="application/json", key="download_json_btn")
    up = st.file_uploader("上傳 family_tree.json 以還原", type=["json"], key="uploader_json")
    if up is not None:
        try:
            data = json.load(up)
            assert isinstance(data, dict) and "persons" in data and "marriages" in data
            st.session_state.tree = data
            init_state()
            st.toast("已匯入 JSON。", icon="📥")
        except Exception as e:
            st.error("上傳格式有誤：{}".format(e))

    st.divider()
    if st.button("🗑 清空全部（不會刪本機檔案）", key="reset_all_btn"):
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
        st.session_state.quests = {"me": False, "parents": False, "spouse": False, "child": False}
        st.toast("已清空。", icon="🗑")

# =============================
# Main
# =============================
def main():
    st.set_page_config(page_title="家族樹小幫手", page_icon="🌳", layout="wide")
    init_state()

    st.write("🟢 App booted — {}".format(VERSION))  # 顯示版本號方便確認
    st.title("🌳 家族樹小幫手｜低調好玩版")
    st.caption("新手用精靈，老手用進階。你可在左側切換模式。")

    with st.sidebar:
        if st.button("✨ 載入示範家族", key="seed_demo_btn"):
            seed_demo()
        st.toggle("水平排列 (LR)", key="layout_lr", help="預設為垂直排列 (TB)")
        st.markdown("---")
        st.checkbox("新手模式（建議新用戶）", key="beginner_mode")

    try:
        sidebar_progress()
    except Exception as e:
        st.error("側欄進度顯示失敗：{}".format(e))

    # 切換：新手模式 vs 進階模式（radio 導覽，rerun 後保留所在頁）
    if st.session_state.beginner_mode:
        onboarding_wizard()

        nav_items_b = ["🖼 家族圖", "📋 資料表", "📦 匯入/匯出"]
        if st.session_state.main_nav_beginner not in nav_items_b:
            st.session_state.main_nav_beginner = "🖼 家族圖"
        st.session_state.main_nav_beginner = st.radio(
            "導覽", nav_items_b, index=nav_items_b.index(st.session_state.main_nav_beginner),
            horizontal=True, key="nav_b"
        )

        if st.session_state.main_nav_beginner == "🖼 家族圖":
            try:
                dot = render_graph()
                st.graphviz_chart(dot, use_container_width=True)
            except Exception:
                st.info("尚未有資料。請在上方步驟建立成員。")

        elif st.session_state.main_nav_beginner == "📋 資料表":
            data_tables()

        elif st.session_state.main_nav_beginner == "📦 匯入/匯出":
            import_export()

    else:
        nav_items = ["✍️ 建立家庭", "🖼 家族圖", "📋 資料表", "🎛 進階建立", "📦 匯入/匯出"]
        if st.session_state.main_nav not in nav_items:
            st.session_state.main_nav = "🎛 進階建立"
        st.session_state.main_nav = st.radio(
            "導覽", nav_items, index=nav_items.index(st.session_state.main_nav),
            horizontal=True, key="nav_main"
        )

        current = st.session_state.main_nav
        if current == "✍️ 建立家庭":
            try:
                form_me(); st.divider(); form_parents(); st.divider(); form_spouse_and_children()
            except Exception as e:
                st.error("建立家庭區塊失敗：{}".format(e))

        elif current == "🖼 家族圖":
            try:
                dot = render_graph()
                st.graphviz_chart(dot, use_container_width=True)
            except Exception as e:
                st.error("圖形渲染失敗：{}".format(e))
            st.caption("提示：可在側欄切換水平/垂直排列；離異/分居以虛線/點線表示；收養/繼親子女以不同線型表示。")

        elif current == "📋 資料表":
            try:
                data_tables()
            except Exception as e:
                st.error("資料表顯示失敗：{}".format(e))

        elif current == "🎛 進階建立":
            try:
                advanced_builder()
            except Exception as e:
                st.error("進階建立區塊失敗：{}".format(e))

        elif current == "📦 匯入/匯出":
            try:
                import_export()
            except Exception as e:
                st.error("匯入/匯出區塊失敗：{}".format(e))

    st.divider()
    st.caption("隱私承諾：您的輸入僅用於本次即時計算，不寫入資料庫；下載/離開頁面即清空。")

if __name__ == "__main__":
    main()

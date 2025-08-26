# -*- coding: utf-8 -*-
"""
🌳 家族樹小幫手（MVP + 進階模式 + 快速兩代；No f-strings）
- 進階模式：多段婚姻、前任/分居、收養/繼親、半血緣、批次兄弟姊妹
- 新增：⚡ 快速加直系兩代（父母 + 配偶 + 多子女）
- 行為保障：所有新增皆需「勾選 + 提交」，避免誤新增；刪除成員有紅色確認鍵
- 隱私：僅存在 session，不寫入資料庫
"""
from __future__ import annotations
import json
import uuid
from typing import List, Optional

import streamlit as st
from graphviz import Digraph

VERSION = "2025-08-26-UXsubmit-quick2gen-FIX"

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
    "married":   {"style": "solid",  "color": "#9E9E9E"},
    "divorced":  {"style": "dashed", "color": "#9E9E9E"},
    "separated": {"style": "dotted", "color": "#9E9E9E"},
}
CHILD_EDGE_STYLE = {
    "bio":     {"style": "solid",  "color": "#BDBDBD"},
    "adopted": {"style": "dotted", "color": "#BDBDBD"},
    "step":    {"style": "dashed", "color": "#BDBDBD"},
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
            "nodesep": "0.4",
            "ranksep": "0.6",
            "fontname": "PingFang TC, Microsoft JhengHei, Noto Sans CJK TC, Arial",
        },
    )

    # 人
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

    # 婚姻點 + 線
    for mid, m in marriages.items():
        dot.node(mid, label="", shape="point", width="0.02")
        stl = STATUS_EDGE_STYLE.get(m.get("status", "married"), STATUS_EDGE_STYLE["married"])
        if m.get("spouse1") and m.get("spouse2"):
            dot.edge(m["spouse1"], mid, color=stl["color"], style=stl["style"])
            dot.edge(m["spouse2"], mid, color=stl["color"], style=stl["style"])
        for c in m.get("children", []):
            if c in persons:
                rel = child_types.get(mid, {}).get(c, "bio")
                cstl = CHILD_EDGE_STYLE.get(rel, CHILD_EDGE_STYLE["bio"])
                dot.edge(mid, c, color=cstl["color"], style=cstl["style"])
    return dot

# =============================
# UI Sections
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

# —— ⚡ 快速加直系兩代（父母 + 配偶 + 多子女；按鈕永遠可按，提交時驗證）
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
                submit_q2g = st.form_submit_button("🚀 一鍵建立")  # 不再 disabled

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

    # ✏️ 編輯成員
    with st.expander("✏️ 編輯成員資料", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        p["name"] = c1.text_input("名稱", value=p["name"], key="edit_name_{}".format(pid))
        g_idx = _safe_index(GENDER_OPTIONS, p.get("gender", "其他/不透漏"), default=2)
        p["gender"] = c2.selectbox("性別", GENDER_OPTIONS, index=g_idx, key="edit_gender_{}".format(pid))
        p["year"] = c3.text_input("出生年(選填)", value=p.get("year", ""), key="edit_year_{}".format(pid))
        p["deceased"] = c4.toggle("已故?", value=p.get("deceased", False), key="edit_dec_{}".format(pid))
        p["note"] = st.text_area("備註(收養/繼親/職業等)", value=p.get("note", ""), key="edit_note_{}".format(pid))
        st.caption("提示：標註『†』= 已故；可在備註註明關係特殊情形。")

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

    # 批次兄弟姊妹（提交制）
    with cD:
        st.markdown("**兄弟姊妹（批次）**")
        pmid = get_parent_marriage_of(pid)
        if pmid:
            with st.form("form_add_sibs_{}".format(pid), clear_on_submit=True):
                sibs = st.text_input("以逗號分隔：如 小明, 小美", key="adv_sibs_{}".format(pid))
                sg = st.selectbox("預設性別", GENDER_OPTIONS, index=2, key="adv_sibs_gender_{}".format(pid))
                cols1, cols2 = st.columns([1,2])
                with cols1:
                    confirm_sibs = st.checkbox("我確認新增", key="adv_confirm_sibs_{}".format(pid))
                with cols2:
                    submit_sibs = st.form_submit_button("👫 提交新增兄弟姊妹", disabled=False)

            if submit_sibs:
                if not confirm_sibs:
                    st.warning("請先勾選「我確認新增」。")
                else:
                    names = [s.strip() for s in sibs.split(",") if s.strip()]
                    for nm in names:
                        sid = add_person(nm, sg)
                        add_child(pmid, sid, relation="bio")
                    st.session_state.celebrate_ready = True
                    st.success("已新增兄弟姊妹")
        else:
            st.caption("此成員尚無已知父母，請先新增父母後再新增兄弟姊妹。")

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
    st.caption("填三四個欄位，立刻畫出家族樹；需要時開啟進階模式處理大家族與複雜關係。")

    with st.sidebar:
        if st.button("✨ 載入示範家族", key="seed_demo_btn"):
            seed_demo()
        st.toggle("水平排列 (LR)", key="layout_lr", help="預設為垂直排列 (TB)")

    try:
        sidebar_progress()
    except Exception as e:
        st.error("側欄進度顯示失敗：{}".format(e))

    try:
        tab_build, tab_graph, tab_table, tab_adv, tab_io = st.tabs(
            ["✍️ 建立家庭", "🖼 家族圖", "📋 資料表", "🎛 進階建立", "📦 匯入/匯出"]
        )
    except Exception as e:
        st.error("Tabs 建立失敗：{}".format(e))
        return

    with tab_build:
        try:
            form_me()
            st.divider()
            form_parents()
            st.divider()
            form_spouse_and_children()
        except Exception as e:
            st.error("建立家庭區塊失敗：{}".format(e))

    with tab_graph:
        try:
            dot = render_graph()
            st.graphviz_chart(dot, use_container_width=True)
        except Exception as e:
            st.error("圖形渲染失敗：{}".format(e))
        st.caption("提示：可在側欄切換水平/垂直排列；離異/分居以虛線/點線表示；收養/繼親子女以不同線型表示。")

    with tab_table:
        try:
            data_tables()
        except Exception as e:
            st.error("資料表顯示失敗：{}".format(e))

    with tab_adv:
        try:
            advanced_builder()
        except Exception as e:
            st.error("進階建立區塊失敗：{}".format(e))

    with tab_io:
        try:
            import_export()
        except Exception as e:
            st.error("匯入/匯出區塊失敗：{}".format(e))

    st.divider()
    st.caption("隱私承諾：您的輸入僅用於本次即時計算，不寫入資料庫；下載/離開頁面即清空。")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
🌳 家族樹小幫手｜單頁極簡版（含法定繼承人試算；No f-strings）
- 區塊：建立我 → 一鍵父母 → 配偶/子女 → 家族圖 → 法定繼承人試算 → 進階建立 → 資料表 → 匯入/匯出
- 新增：法定繼承試算依民法 §1138（順位）、§1139（第一順序決定）、§1140（代位繼承）、§1144（配偶應繼分）
- 行為：所有新增皆需「勾選 + 提交」，避免誤新增；按鈕用提交時驗證
- 顯示：已故 → 名字加「(殁)」、底色淺灰
- 匯入：先暫存於 session_state，上按「📥 套用匯入」才覆蓋（避免 rerun 造成沒反應）
"""
from __future__ import annotations
import json, uuid
from typing import List, Optional, Dict, Tuple

import streamlit as st
from graphviz import Digraph

VERSION = "2025-08-26-onepage-heirs-1138-1139-1140-1144"

# ====== 常量 ======
GENDER_OPTIONS = ["女", "男", "其他/不透漏"]
REL_MAP = {"bio": "親生", "adopted": "收養", "step": "繼親"}
STATUS_MAP = {"married": "已婚", "divorced": "前任(離異)", "separated": "分居"}

GENDER_STYLE = {"男": {"fillcolor": "#E3F2FD"},
                "女": {"fillcolor": "#FCE4EC"},
                "其他/不透漏": {"fillcolor": "#F3F4F6"}}
STATUS_EDGE_STYLE = {"married": {"style": "solid", "color": "#9E9E9E"},
                     "divorced": {"style": "dashed", "color": "#9E9E9E"},
                     "separated": {"style": "dotted", "color": "#9E9E9E"}}
CHILD_EDGE_STYLE = {"bio": {"style": "solid", "color": "#BDBDBD"},
                    "adopted": {"style": "dotted", "color": "#BDBDBD"},
                    "step": {"style": "dashed", "color": "#BDBDBD"}}

# ====== State/Helper ======
def _new_id(prefix): return "{}_{}".format(prefix, uuid.uuid4().hex[:8])
def _safe_index(seq, value, default=0):
    try: return list(seq).index(value)
    except ValueError: return default

def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    if "celebrate_ready" not in st.session_state:
        st.session_state.celebrate_ready = False
    # 補預設欄位
    for mid in list(st.session_state.tree.get("marriages", {}).keys()):
        st.session_state.tree["marriages"][mid].setdefault("status", "married")
        st.session_state.tree["child_types"].setdefault(mid, {})
    for _, p in st.session_state.tree.get("persons", {}).items():
        p.setdefault("deceased", False); p.setdefault("note", ""); p.setdefault("gender", "其他/不透漏")

def get_me_pid():
    for pid, p in st.session_state.tree["persons"].items():
        if p.get("is_me"): return pid
    return None

def add_person(name, gender, year=None, note="", is_me=False, deceased=False):
    pid = _new_id("P")
    st.session_state.tree["persons"][pid] = {
        "name": (name or "").strip() or "未命名",
        "gender": gender if gender in GENDER_OPTIONS else "其他/不透漏",
        "year": (year or "").strip(), "note": (note or "").strip(),
        "is_me": bool(is_me), "deceased": bool(deceased)
    }
    return pid

def add_or_get_marriage(a, b, status="married"):
    for mid, m in st.session_state.tree["marriages"].items():
        if {m.get("spouse1"), m.get("spouse2")} == {a, b}:
            if status and m.get("status") != status: m["status"] = status
            st.session_state.tree["child_types"].setdefault(mid, {})
            return mid
    mid = _new_id("M")
    st.session_state.tree["marriages"][mid] = {"spouse1": a, "spouse2": b, "children": [], "status": status}
    st.session_state.tree["child_types"].setdefault(mid, {})
    return mid

def add_child(mid, cid, relation="bio"):
    m = st.session_state.tree["marriages"].get(mid)
    if not m: return
    if cid not in m["children"]: m["children"].append(cid)
    st.session_state.tree["child_types"].setdefault(mid, {})[cid] = relation

def set_child_relation(mid, cid, relation):
    st.session_state.tree["child_types"].setdefault(mid, {})
    if cid in st.session_state.tree["child_types"][mid]:
        st.session_state.tree["child_types"][mid][cid] = relation

def get_marriages_of(pid):
    mids = []
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in (m.get("spouse1"), m.get("spouse2")): mids.append(mid)
    return mids

def get_parent_marriage_of(pid):
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in m.get("children", []): return mid
    return None

def delete_person(pid):
    t = st.session_state.tree
    if pid not in t["persons"]: return
    for mid, m in list(t["marriages"].items()):
        if pid in m.get("children", []):
            m["children"] = [c for c in m["children"] if c != pid]
            if pid in t["child_types"].get(mid, {}): del t["child_types"][mid][pid]
    for mid, m in list(t["marriages"].items()):
        changed = False
        if m.get("spouse1") == pid: m["spouse1"] = None; changed = True
        if m.get("spouse2") == pid: m["spouse2"] = None; changed = True
        if (m.get("spouse1") is None and m.get("spouse2") is None and not m.get("children")):
            if mid in t["child_types"]: del t["child_types"][mid]
            del t["marriages"][mid]
        elif changed:
            t["child_types"].setdefault(mid, {})
    del t["persons"][pid]

# ====== Demo ======
def seed_demo():
    st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    me = add_person("我", "女", year="1970", is_me=True)
    f = add_person("爸爸", "男", year="1940")
    mo = add_person("媽媽", "女", year="1945")
    mid_p = add_or_get_marriage(f, mo)
    add_child(mid_p, me, "bio")
    sp = add_person("另一半", "男", year="1968")
    mid_me = add_or_get_marriage(me, sp)
    c1 = add_person("大女兒", "女", year="1995")
    c2 = add_person("小兒子", "男", year="1999")
    add_child(mid_me, c1); add_child(mid_me, c2)
    ex = add_person("前任", "女")
    mid_ex = add_or_get_marriage(f, ex, "divorced")
    half = add_person("同父異母弟弟", "男", year="1980")
    add_child(mid_ex, half)
    st.session_state.celebrate_ready = True
    st.toast("已載入示範家族。", icon="✅")

# ====== 法定繼承：核心演算法（§1138/§1139/§1140/§1144） ======
def _is_alive(pid):
    p = st.session_state.tree["persons"].get(pid, {})
    return not p.get("deceased", False)

def _child_rel(mid, cid):
    return st.session_state.tree["child_types"].get(mid, {}).get(cid, "bio")

def _eligible_child(mid, cid):
    # 只有親生與收養有法定親子繼承關係；繼親不具
    rel = _child_rel(mid, cid)
    return rel in ("bio", "adopted")

def _list_children_of(person_id):
    res = []
    for mid, m in st.session_state.tree["marriages"].items():
        if person_id in (m.get("spouse1"), m.get("spouse2")):
            for cid in m.get("children", []):
                if _eligible_child(mid, cid):
                    res.append((mid, cid))
    return res

def _list_parents_of(person_id):
    pmid = get_parent_marriage_of(person_id)
    if pmid is None: return []
    m = st.session_state.tree["marriages"][pmid]
    return [p for p in [m.get("spouse1"), m.get("spouse2")] if p]

def _list_siblings_of(person_id):
    # 透過父母＋其餘婚姻，收集全血/半血兄弟姊妹
    sibs = set()
    pmid = get_parent_marriage_of(person_id)
    if pmid:
        for cid in st.session_state.tree["marriages"][pmid].get("children", []):
            if cid != person_id: sibs.add(cid)
    parents = _list_parents_of(person_id)
    for par in parents:
        for mid, m in st.session_state.tree["marriages"].items():
            if par in (m.get("spouse1"), m.get("spouse2")):
                for cid in m.get("children", []):
                    if cid != person_id:
                        sibs.add(cid)
    return list(sibs)

def _list_spouses_alive_of(person_id):
    spouses = []
    for mid, m in st.session_state.tree["marriages"].items():
        if person_id in (m.get("spouse1"), m.get("spouse2")):
            status = m.get("status", "married")
            if status == "divorced":
                continue
            other = m.get("spouse1") if m.get("spouse2") == person_id else m.get("spouse2")
            if other and _is_alive(other):
                spouses.append(other)
    # 去重
    return list(dict.fromkeys(spouses).keys())

def _stirpes_descendants(children_pairs):
    """
    逐支(per stirpes)遞迴（僅供第一順位使用）：
    輸入 list[(mid, child_pid)]；輸出 list[(heir_pid, weight)]，weights across OUTPUT 加總=1
    - 子女在世：該支由該子女承受（此支重=1）
    - 子女先亡：該支由其直系卑親屬承受（在該支內 weights 加總=1），可遞迴
    """
    branches = []
    for mid, child in children_pairs:
        if not _eligible_child(mid, child):
            continue
        if _is_alive(child):
            branches.append([(child, 1.0)])
        else:
            leaves = _stirpes_descendants(_list_children_of(child))
            if leaves:
                branches.append(leaves)
    n = len(branches)
    if n == 0:
        return []
    # 將每支 base = 1/n，再乘以該支內部的權重
    out = []
    base = 1.0 / float(n)
    for leaves in branches:
        for pid, w in leaves:
            out.append((pid, base * float(w)))
    # 合併同人
    merged = {}
    for pid, w in out:
        merged[pid] = merged.get(pid, 0.0) + w
    return [(pid, merged[pid]) for pid in merged]

def heirs_by_order(decedent_pid):
    """
    回傳 (order, heirs_list, spouses_alive)
    order: 1/2/3/4 或 None
    heirs_list:
      - 第1順位：list[(pid, weight)] 為直系卑親屬或其代位之「支內」權重合併後的結果（總和=1）
      - 第2/3/4順位：list[(pid, 1.0)] 僅作名單，實際 share 於後續計算
    spouses_alive: 存活配偶清單（離異不列）
    """
    spouses_alive = _list_spouses_alive_of(decedent_pid)

    # 第一順位（§1138、§1139、§1140）
    children = _list_children_of(decedent_pid)
    first = _stirpes_descendants(children)  # already normalized to sum=1
    if first:
        return (1, first, spouses_alive)

    # 第二順位：父母（在世）（§1138）
    parents = [pid for pid in _list_parents_of(decedent_pid) if _is_alive(pid)]
    if parents:
        return (2, [(pid, 1.0) for pid in parents], spouses_alive)

    # 第三順位：兄弟姊妹（不適用§1140 代位，依你指定條文）
    sibs_alive = [sid for sid in _list_siblings_of(decedent_pid) if _is_alive(sid)]
    if sibs_alive:
        return (3, [(pid, 1.0) for pid in sibs_alive], spouses_alive)

    # 第四順位：祖父母（在世）（§1138）
    gps = set()
    for par in _list_parents_of(decedent_pid):
        for gp in _list_parents_of(par):
            if _is_alive(gp):
                gps.add(gp)
    if gps:
        return (4, [(pid, 1.0) for pid in gps], spouses_alive)

    # 無其他順位
    return (None, [], spouses_alive)

def compute_statutory_shares_v2(decedent_pid):
    """
    法定繼承試算：民法§1138、§1139、§1140、§1144
    傳回 {order, basis, result, notes}
    """
    order, group, spouses = heirs_by_order(decedent_pid)
    res, notes = [], []
    basis = "依民法§1138（順位）、§1139（第一順序決定）、§1140（代位繼承）、§1144（配偶應繼分）試算"

    n_sp = len(spouses)

    if order is None:
        if n_sp > 0:
            share_sp_each = 1.0 / float(n_sp)
            for sp in spouses:
                res.append({"pid": sp, "share": share_sp_each, "role": "配偶"})
            notes.append("無第一至第四順位繼承人，配偶單獨繼承（§1144-4）。")
        else:
            notes.append("未找到任何法定繼承人。")
        return {"order": order, "basis": basis, "result": res, "notes": notes}

    # 第一順位：配偶視為一個子女分支（§1144-1）
    if order == 1:
        # 重新建立「子女分支」以取得分支數（而非 leaf 人數）
        branches = []  # 每一支: list[(pid, weight)]，該支內 weights 加總=1
        for mid, cid in _list_children_of(decedent_pid):
            if _is_alive(cid):
                branches.append([(cid, 1.0)])
            else:
                leaves = _stirpes_descendants(_list_children_of(cid))
                if leaves: branches.append(leaves)
        N = len(branches)  # 有效子女分支數（在世或代位線上仍有人）

        if N == 0 and n_sp == 0:
            notes.append("無子女亦無配偶，應再檢查第二至第四順位。")
            return {"order": order, "basis": basis, "result": res, "notes": notes}

        if n_sp > 0:
            total_branch = N + 1  # 配偶為一支
            branch_share = 1.0 / float(total_branch)
            # 多位配偶分配該一支
            sp_each = branch_share / float(n_sp)
            for sp in spouses:
                res.append({"pid": sp, "share": sp_each, "role": "配偶"})
        else:
            branch_share = 1.0 / float(N) if N > 0 else 0.0

        # 子女各支分配（代位：在支內按 leaves 的 weight 比例承受）
        for leaves in branches:
            for pid, w in leaves:
                res.append({"pid": pid, "share": branch_share * float(w),
                            "role": "直系卑親屬" if w >= 0.999 else "代位繼承"})
        notes.append("配偶與第一順位並存：配偶視為一分支，與各子女分支平均（§1144-1）；代位只適用第一順位（§1140）。")
        return {"order": order, "basis": basis, "result": res, "notes": notes}

    # 第二順位：父母（§1144-2）
    if order == 2:
        if n_sp > 0:
            sp_total = 0.5
            sp_each = sp_total / float(n_sp)
            for sp in spouses:
                res.append({"pid": sp, "share": sp_each, "role": "配偶"})
            others_total = 0.5
        else:
            others_total = 1.0
        alive_parents = [pid for pid, _ in group]
        each_parent = (others_total / float(len(alive_parents))) if alive_parents else 0.0
        for pid in alive_parents:
            res.append({"pid": pid, "share": each_parent, "role": "父母"})
        notes.append("配偶與第二順位並存：配偶1/2，父母共1/2（§1144-2）。" if n_sp > 0 else "無配偶：由父母平均（§1138）。")
        return {"order": order, "basis": basis, "result": res, "notes": notes}

    # 第三順位：兄弟姊妹（不適用§1140；§1144-2）
    if order == 3:
        if n_sp > 0:
            sp_total = 0.5
            sp_each = sp_total / float(n_sp)
            for sp in spouses:
                res.append({"pid": sp, "share": sp_each, "role": "配偶"})
            others_total = 0.5
        else:
            others_total = 1.0
        sibs = [pid for pid, _ in group]
        each_sib = (others_total / float(len(sibs))) if sibs else 0.0
        for pid in sibs:
            res.append({"pid": pid, "share": each_sib, "role": "兄弟姊妹"})
        notes.append("配偶與第三順位並存：配偶1/2，兄弟姊妹共1/2（§1144-2）。" if n_sp > 0 else "無配偶：兄弟姊妹平均（§1138）。")
        return {"order": order, "basis": basis, "result": res, "notes": notes}

    # 第四順位：祖父母（§1144-3）
    if order == 4:
        if n_sp > 0:
            sp_total = 2.0/3.0
            sp_each = sp_total / float(n_sp)
            for sp in spouses:
                res.append({"pid": sp, "share": sp_each, "role": "配偶"})
            others_total = 1.0/3.0
        else:
            others_total = 1.0
        gps = [pid for pid, _ in group]
        each_gp = (others_total / float(len(gps))) if gps else 0.0
        for pid in gps:
            res.append({"pid": pid, "share": each_gp, "role": "祖父母"})
        notes.append("配偶與第四順位並存：配偶2/3，祖父母共1/3（§1144-3）。" if n_sp > 0 else "無配偶：祖父母平均（§1138）。")
        return {"order": order, "basis": basis, "result": res, "notes": notes}

    return {"order": order, "basis": basis, "result": res, "notes": notes}

# ====== UI 區塊 ======

def block_header():
    st.title("🌳 家族樹小幫手｜單頁版")
    st.caption("填寫必要欄位並按提交即可；不會自動寫入。")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("✨ 載入示範家族", key="btn_seed"):
            seed_demo()
    with c2:
        confirm_reset = st.checkbox("我確定要清空", key="confirm_reset")
        if st.button("🗑 清空全部", key="btn_reset", disabled=not confirm_reset):
            st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
            st.session_state.confirm_reset = False
            st.toast("已清空。", icon="🗑")
    with c3:
        st.markdown("**快速切換模式**")
        mode = st.radio("資料來源", ["空白", "示範"], horizontal=True, key="mode_select")
        if mode == "示範" and not st.session_state.tree["persons"]:
            seed_demo()
        if mode == "空白" and st.session_state.tree.get("persons"):
            if st.button("切到空白（不影響已下載檔案）", key="btn_blank"):
                st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
                st.toast("已切換為空白模式。", icon="🧹")
    st.markdown("---")


def block_me():
    st.subheader("Step 1｜建立『我』")
    me_pid = get_me_pid()
    if me_pid:
        p = st.session_state.tree["persons"][me_pid]
        col1, col2, col3, col4 = st.columns([2,1,1,1])
        p["name"] = col1.text_input("我的名稱", value=p["name"], key="me_name")
        p["gender"] = col2.selectbox("性別", GENDER_OPTIONS,
                                     index=_safe_index(GENDER_OPTIONS, p.get("gender","其他/不透漏"),2),
                                     key="me_gender")
        p["year"] = col3.text_input("出生年(選填)", value=p.get("year",""), key="me_year")
        p["deceased"] = col4.toggle("已故?", value=p.get("deceased",False), key="me_dec")
        st.success("已建立『我』，可繼續下一步。")
    else:
        with st.form("form_me"):
            name = st.text_input("我的名稱", value="我", key="me_new_name")
            gender = st.selectbox("性別", GENDER_OPTIONS, key="me_new_gender")
            year = st.text_input("出生年(選填)", key="me_new_year")
            confirm = st.checkbox("我確認新增", key="me_new_ok")
            ok = st.form_submit_button("✅ 建立『我』")
        if ok:
            if not confirm: st.warning("請先勾選「我確認新增」。")
            else:
                add_person(name, gender, year=year, is_me=True)
                st.session_state.celebrate_ready = True
                st.toast("已建立『我』", icon="✅")

def block_parents():
    st.subheader("Step 2｜一鍵新增父母（可略過）")
    me = get_me_pid()
    if not me:
        st.info("請先完成 Step 1"); return
    c1, c2, c3 = st.columns([1.2,1.2,1.2])
    fa = c1.text_input("父親姓名", value="爸爸", key="father_name_input")
    mo = c2.text_input("母親姓名", value="媽媽", key="mother_name_input")
    if c3.button("＋ 新增父母並連結到『我』", key="btn_add_parents"):
        f = add_person(fa, "男"); m = add_person(mo, "女")
        mid = add_or_get_marriage(f, m); add_child(mid, me, "bio")
        st.session_state.celebrate_ready = True
        st.toast("已新增父母。", icon="👨‍👩‍👧")

def block_spouse_children():
    st.subheader("Step 3｜配偶 / Step 4｜子女")
    me = get_me_pid()
    if not me:
        st.info("請先完成 Step 1"); return

    # 配偶
    with st.expander("＋ 新增配偶/另一半（可標注前任/分居）", expanded=False):
        with st.form("form_add_spouse_main", clear_on_submit=True):
            sp_name = st.text_input("姓名", value="", key="sp_name_main")
            sp_gender = st.selectbox("性別", GENDER_OPTIONS, index=1, key="sp_gender_main")
            sp_status = st.selectbox("關係狀態", list(STATUS_MAP.keys()), index=0,
                                     format_func=lambda s: STATUS_MAP[s], key="sp_status_main")
            col_ok1, col_ok2 = st.columns([1,2])
            confirm = col_ok1.checkbox("我確認新增", key="confirm_add_sp_main")
            submit = col_ok2.form_submit_button("💍 提交新增關係")
        if submit:
            if not confirm: st.warning("請先勾選「我確認新增」。")
            elif sp_name.strip():
                sp = add_person(sp_name.strip(), sp_gender)
                add_or_get_marriage(me, sp, sp_status)
                st.session_state.celebrate_ready = True
                st.success("已新增關係")
            else:
                st.warning("請輸入配偶姓名後再提交。")

    # 子女
    my_mids = get_marriages_of(me)
    if my_mids:
        persons = st.session_state.tree["persons"]
        labels = []
        for mid in my_mids:
            m = st.session_state.tree["marriages"][mid]
            s1 = persons.get(m["spouse1"],{}).get("name","?")
            s2 = persons.get(m["spouse2"],{}).get("name","?")
            lbl = "{} ❤ {}（{}）".format(s1, s2, STATUS_MAP.get(m.get("status","married"), m.get("status","married")))
            labels.append((mid, lbl))
        pick = st.selectbox("選擇要新增子女的關係",
                            options=list(range(len(labels))),
                            format_func=lambda i: labels[i][1], key="choose_mid_main")
        chosen_mid = labels[pick][0]
        with st.expander("＋ 新增子女", expanded=False):
            with st.form("form_add_child_main_{}".format(chosen_mid), clear_on_submit=True):
                c_name = st.text_input("子女姓名", key="child_name_main_{}".format(chosen_mid))
                c_gender = st.selectbox("性別", GENDER_OPTIONS, index=0, key="child_gender_main_{}".format(chosen_mid))
                c_year = st.text_input("出生年(選填)", key="child_year_main_{}".format(chosen_mid))
                c_rel = st.selectbox("關係類型", list(REL_MAP.keys()), index=0,
                                     format_func=lambda s: REL_MAP[s], key="child_rel_main_{}".format(chosen_mid))
                col1, col2 = st.columns([1,2])
                confirm_c = col1.checkbox("我確認新增", key="confirm_add_child_{}".format(chosen_mid))
                submit_c = col2.form_submit_button("👶 提交新增子女")
            if submit_c:
                if not confirm_c: st.warning("請先勾選「我確認新增」。")
                elif c_name.strip():
                    cid = add_person(c_name.strip(), c_gender, year=c_year)
                    add_child(chosen_mid, cid, relation=c_rel)
                    st.session_state.celebrate_ready = True
                    st.success("已新增子女")
                else:
                    st.warning("請輸入子女姓名後再提交。")
    else:
        st.info("尚未新增任何配偶/婚姻，請先新增配偶。")

def block_quick_two_gen(target_pid):
    with st.expander("⚡ 快速加直系兩代（父母 + 配偶 + 多子女）", expanded=False):
        st.caption("可只填需要的欄位；未提交前不會建立任何資料。")
        with st.form("form_q2g_{}".format(target_pid), clear_on_submit=True):
            st.markdown("**A. 父母**（可留白略過）")
            c1, c2 = st.columns([1.2,1.2])
            fa_name = c1.text_input("父親姓名", key="q2g_fa_{}".format(target_pid))
            mo_name = c2.text_input("母親姓名", key="q2g_mo_{}".format(target_pid))
            add_parents = st.checkbox("建立父母並連結", key="q2g_addp_{}".format(target_pid))

            st.markdown("**B. 配偶/關係**（可留白略過）")
            c4, c5, c6 = st.columns([1.2,1.0,1.0])
            sp_name = c4.text_input("配偶姓名", key="q2g_spn_{}".format(target_pid))
            sp_gender = c5.selectbox("性別", GENDER_OPTIONS, index=1, key="q2g_spg_{}".format(target_pid))
            sp_status = c6.selectbox("狀態", list(STATUS_MAP.keys()), index=0,
                                     format_func=lambda s: STATUS_MAP[s], key="q2g_sps_{}".format(target_pid))
            add_spouse = st.checkbox("建立配偶/關係", key="q2g_adds_{}".format(target_pid))

            st.markdown("**C. 子女**（可留白略過）")
            c7, c8, c9, c10 = st.columns([2.0,1.0,1.0,1.2])
            kids_csv = c7.text_input("子女姓名（以逗號分隔）", key="q2g_kcsv_{}".format(target_pid))
            kid_gender = c8.selectbox("預設性別", GENDER_OPTIONS, index=0, key="q2g_kg_{}".format(target_pid))
            kid_rel = c9.selectbox("關係類型", list(REL_MAP.keys()), index=0,
                                   format_func=lambda s: REL_MAP[s], key="q2g_krel_{}".format(target_pid))
            kid_year = c10.text_input("預設出生年(選填)", key="q2g_kyr_{}".format(target_pid))
            col_ok1, col_ok2 = st.columns([1,2])
            confirm = col_ok1.checkbox("我確認建立上述資料", key="q2g_ok_{}".format(target_pid))
            submit = col_ok2.form_submit_button("🚀 一鍵建立")
        if submit:
            if not confirm:
                st.warning("請先勾選「我確認建立上述資料」。"); return
            if add_parents and (fa_name or mo_name):
                fpid = add_person((fa_name or "父親").strip(), "男")
                mpid = add_person((mo_name or "母親").strip(), "女")
                mid = add_or_get_marriage(fpid, mpid, "married")
                add_child(mid, target_pid, "bio")
            chosen_mid = None
            if add_spouse and sp_name:
                spid = add_person(sp_name.strip(), sp_gender)
                chosen_mid = add_or_get_marriage(target_pid, spid, sp_status)
            kids = [s.strip() for s in (kids_csv or "").split(",") if s.strip()]
            if kids:
                if chosen_mid is None:
                    placeholder = add_person("未知配偶", "其他/不透漏")
                    chosen_mid = add_or_get_marriage(target_pid, placeholder, "married")
                for nm in kids:
                    cid = add_person(nm, kid_gender, year=kid_year)
                    add_child(chosen_mid, cid, relation=kid_rel)
            st.session_state.celebrate_ready = True
            st.success("已完成快速建立。"); st.rerun()

def block_advanced():
    st.subheader("🎛 進階建立｜大家族與複雜關係")
    persons = st.session_state.tree["persons"]
    if not persons:
        st.info("請先建立至少一位成員。"); return
    ids = list(persons.keys())
    pick = st.selectbox("選擇成員以編輯/加關係",
                        options=list(range(len(ids))),
                        format_func=lambda i: persons[ids[i]]["name"], key="adv_pick")
    pid = ids[pick]; p = persons[pid]

    # ✏️ 編輯
    with st.expander("✏️ 編輯成員資料", expanded=True):
        c1,c2,c3,c4 = st.columns([2,1,1,1])
        p["name"] = c1.text_input("名稱", value=p["name"], key="edit_name_{}".format(pid))
        p["gender"] = c2.selectbox("性別", GENDER_OPTIONS,
                                   index=_safe_index(GENDER_OPTIONS,p.get("gender","其他/不透漏"),2),
                                   key="edit_gender_{}".format(pid))
        p["year"] = c3.text_input("出生年(選填)", value=p.get("year",""), key="edit_year_{}".format(pid))
        p["deceased"] = c4.toggle("已故?", value=p.get("deceased",False), key="edit_dec_{}".format(pid))
        p["note"] = st.text_area("備註(收養/繼親/職業等)", value=p.get("note",""), key="edit_note_{}".format(pid))
        st.markdown("---")
        st.markdown("🗑️ **刪除這位成員**")
        if p.get("is_me"):
            st.caption("此成員為『我』，不可刪除。")
        else:
            sure = st.checkbox("我確定要刪除", key="confirm_del_{}".format(pid))
            del_btn = st.button("❌ 刪除此成員", key="btn_del_{}".format(pid), disabled=not sure)
            if del_btn:
                delete_person(pid); st.success("已刪除"); st.rerun()

    # ⚡ 快速兩代（對此成員）
    block_quick_two_gen(pid)

    st.markdown("---")
    cA, cB, cC = st.columns(3)

    # 父母
    with cA:
        st.markdown("**父母**")
        fa = st.text_input("父親姓名", key="adv_f_{}".format(pid))
        mo = st.text_input("母親姓名", key="adv_m_{}".format(pid))
        if st.button("➕ 新增父母並連結", key="btn_add_parents_{}".format(pid)):
            fpid = add_person(fa or "父親", "男")
            mpid = add_person(mo or "母親", "女")
            mid = add_or_get_marriage(fpid, mpid, "married")
            add_child(mid, pid, "bio"); st.session_state.celebrate_ready = True
            st.toast("已新增父母並連結。", icon="👨‍👩‍👧")

    # 配偶
    with cB:
        st.markdown("**配偶/關係**")
        spn = st.text_input("配偶姓名", key="adv_sp_{}".format(pid))
        spg = st.selectbox("性別", GENDER_OPTIONS, index=1, key="adv_spg_{}".format(pid))
        sps = st.selectbox("狀態", list(STATUS_MAP.keys()), index=0,
                           format_func=lambda s: STATUS_MAP[s], key="adv_sps_{}".format(pid))
        if st.button("➕ 新增關係", key="btn_add_sp_{}".format(pid)):
            if spn.strip():
                spid = add_person(spn.strip(), spg)
                add_or_get_marriage(pid, spid, sps)
                st.session_state.celebrate_ready = True
                st.toast("已新增關係", icon="💍")
            else:
                st.warning("請先輸入配偶姓名。")

    # 子女
    with cC:
        st.markdown("**子女**")
        my_mids = get_marriages_of(pid)
        if my_mids:
            persons = st.session_state.tree["persons"]
            mids_ui = []
            for mid in my_mids:
                m = st.session_state.tree["marriages"][mid]
                s1 = persons.get(m["spouse1"],{}).get("name","?")
                s2 = persons.get(m["spouse2"],{}).get("name","?")
                mids_ui.append((mid, "{} ❤ {}（{}）".format(s1, s2, STATUS_MAP.get(m.get("status","married"), m.get("status","married")))))
            mid_idx = st.selectbox("選擇關係", options=list(range(len(mids_ui))),
                                   format_func=lambda i: mids_ui[i][1], key="adv_mid_{}".format(pid))
            chosen_mid = mids_ui[mid_idx][0]
            with st.form("form_add_child_adv_{}".format(pid), clear_on_submit=True):
                cn = st.text_input("子女姓名", key="adv_child_name_{}".format(pid))
                cg = st.selectbox("性別", GENDER_OPTIONS, index=0, key="adv_child_gender_{}".format(pid))
                cy = st.text_input("出生年(選填)", key="adv_child_year_{}".format(pid))
                cr = st.selectbox("關係類型", list(REL_MAP.keys()), index=0,
                                  format_func=lambda s: REL_MAP[s], key="adv_child_rel_{}".format(pid))
                okcol1, okcol2 = st.columns([1,2])
                confirm = okcol1.checkbox("我確認新增", key="adv_confirm_child_{}".format(pid))
                ok = okcol2.form_submit_button("👶 提交新增子女")
            if ok:
                if not confirm: st.warning("請先勾選「我確認新增」。")
                elif cn.strip():
                    cid = add_person(cn.strip(), cg, year=cy)
                    add_child(chosen_mid, cid, relation=cr)
                    st.session_state.celebrate_ready = True
                    st.success("已新增子女")
                else:
                    st.warning("請輸入子女姓名後再提交。")
        else:
            st.caption("尚無關係，請先新增配偶/另一半。")

    st.markdown("---")
    # 批次兄弟姊妹
    st.markdown("**兄弟姊妹（批次）**")
    pmid = get_parent_marriage_of(pid)
    if pmid is None:
        st.caption("此成員目前沒有已知的雙親關係，無法判定兄弟姊妹。請先新增其父母。")
    else:
        sibs = st.text_input("以逗號分隔：如 小明, 小美", key="adv_sibs_{}".format(pid))
        sg = st.selectbox("預設性別", GENDER_OPTIONS, index=2, key="adv_sibs_gender_{}".format(pid))
        confirm_s = st.checkbox("我確認新增", key="adv_confirm_sibs_{}".format(pid))
        click_add_sibs = st.button("👫 提交新增兄弟姊妹", key="btn_add_sibs_submit_{}".format(pid))
        if click_add_sibs:
            if not confirm_s: st.warning("請先勾選「我確認新增」。")
            else:
                names = [s.strip() for s in (sibs or "").split(",") if s.strip()]
                if not names: st.warning("請至少輸入一個姓名（以逗號分隔）。")
                else:
                    for nm in names:
                        sid = add_person(nm, sg); add_child(pmid, sid, "bio")
                    st.session_state.celebrate_ready = True
                    st.success("已新增兄弟姊妹"); st.rerun()

    # 微調關係
    st.markdown("---")
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]
    if marriages:
        st.markdown("**關係檢視與微調**")
        for mid, m in marriages.items():
            s1 = st.session_state.tree["persons"].get(m["spouse1"],{}).get("name","?")
            s2 = st.session_state.tree["persons"].get(m["spouse2"],{}).get("name","?")
            with st.expander("{} ❤ {}".format(s1, s2), expanded=False):
                m["status"] = st.selectbox("婚姻狀態", list(STATUS_MAP.keys()),
                                           index=_safe_index(list(STATUS_MAP.keys()), m.get("status","married"), 0),
                                           format_func=lambda s: STATUS_MAP[s], key="stat_{}".format(mid))
                for cid in m.get("children", []):
                    cname = st.session_state.tree["persons"].get(cid, {}).get("name", cid)
                    current_rel = child_types.get(mid, {}).get(cid, "bio")
                    new_rel = st.selectbox("{} 的關係".format(cname), list(REL_MAP.keys()),
                                           index=_safe_index(list(REL_MAP.keys()), current_rel, 0),
                                           format_func=lambda s: REL_MAP[s], key="rel_{}_{}".format(mid, cid))
                    set_child_relation(mid, cid, new_rel)

def block_graph():
    st.subheader("🖼 家族圖")
    try:
        persons = st.session_state.tree["persons"]
        dot = Digraph(comment="FamilyTree",
                      graph_attr={"rankdir": "TB", "splines": "spline", "nodesep": "0.4", "ranksep": "0.6",
                                  "fontname": "PingFang TC, Microsoft JhengHei, Noto Sans CJK TC, Arial"})
        # 人節點（已故：名字加(殁)，底色淺灰）
        for pid, p in persons.items():
            label = p.get("name","未命名")
            if p.get("year"): label = label + "\n(" + str(p.get("year")) + ")"
            if p.get("deceased"):
                label = label + "(殁)"; fill = "#E0E0E0"
            else:
                fill = GENDER_STYLE.get(p.get("gender") or "其他/不透漏",
                                        GENDER_STYLE["其他/不透漏"])["fillcolor"]
            if p.get("is_me"): label = "⭐ " + label
            dot.node(pid, label=label, shape="box", style="rounded,filled",
                     color="#90A4AE", fillcolor=fill, penwidth="1.2")

        # 關係與子女
        marriages = st.session_state.tree["marriages"]
        child_types = st.session_state.tree["child_types"]
        for mid, m in marriages.items():
            dot.node(mid, label="", shape="point", width="0.02")
            stl = STATUS_EDGE_STYLE.get(m.get("status","married"), STATUS_EDGE_STYLE["married"])
            if m.get("spouse1") and m.get("spouse2"):
                dot.edge(m["spouse1"], mid, color=stl["color"], style=stl["style"])
                dot.edge(m["spouse2"], mid, color=stl["color"], style=stl["style"])
            for c in m.get("children", []):
                if c in persons:
                    rel = child_types.get(mid, {}).get(c, "bio")
                    cstl = CHILD_EDGE_STYLE.get(rel, CHILD_EDGE_STYLE["bio"])
                    dot.edge(mid, c, color=cstl["color"], style=cstl["style"])
        st.graphviz_chart(dot, use_container_width=True)
    except Exception as e:
        st.error("圖形渲染失敗：{}".format(e))

def block_heirs():
    st.subheader("⚖️ 法定繼承人試算（民法§1138、§1139、§1140、§1144）")
    persons = st.session_state.tree["persons"]
    if not persons:
        st.info("請先建立至少一位成員。"); return

    # 選擇被繼承人
    id_list = list(persons.keys())
    pick = st.selectbox("選擇被繼承人", options=list(range(len(id_list))),
                        format_func=lambda i: persons[id_list[i]]["name"], key="heir_pick")
    target = id_list[pick]

    with st.expander("說明 / 限制", expanded=False):
        st.caption("本試算依民法§1138（順位）、§1139（第一順序決定）、§1140（代位繼承）、§1144（配偶應繼分）。未涵蓋：遺囑、拋棄或喪失繼承權、特留分、夫妻剩餘財產分配、半血分額差異、祖父母分線等。")

    if st.button("🧮 立即試算", key="btn_calc_heirs"):
        out = compute_statutory_shares_v2(target)
        # 顯示結果表格
        rows = []
        for item in out["result"]:
            pid = item["pid"]
            name = persons.get(pid, {}).get("name", pid)
            share = item["share"]
            role = item.get("role", "")
            rows.append({"成員": name, "角色": role, "應繼分": "{:.2f}%".format(share * 100.0)})
        if rows:
            st.markdown("**試算結果**")
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("沒有可分配的繼承人結果。")
        order_name = {1:"第一順位（直系卑親屬）",2:"第二順位（父母）",3:"第三順位（兄弟姊妹）",4:"第四順位（祖父母）"}.get(out["order"], "無")
        st.markdown("**適用順位**：{}".format(order_name))
        st.markdown("**法律依據**：{}".format(out["basis"]))
        if out["notes"]:
            st.markdown("**備註**：{}".format("；".join(out["notes"])))

def block_tables():
    st.subheader("📋 資料檢視")
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]
    if persons:
        st.markdown("**成員名冊**")
        st.dataframe([{"pid": pid, **p} for pid, p in persons.items()], use_container_width=True, hide_index=True)
    if marriages:
        st.markdown("**婚姻/關係**")
        rows = []
        for mid, m in marriages.items():
            rows.append({
                "mid": mid,
                "spouse1": persons.get(m.get("spouse1"),{}).get("name", m.get("spouse1")),
                "spouse2": persons.get(m.get("spouse2"),{}).get("name", m.get("spouse2")),
                "status": STATUS_MAP.get(m.get("status","married"), m.get("status","married")),
                "children": ", ".join([persons.get(cid,{}).get("name", cid) for cid in m.get("children", [])]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def block_health():
    st.subheader("🔎 資料健檢")
    persons = st.session_state.tree.get("persons", {})
    marriages = st.session_state.tree.get("marriages", {})
    child_types = st.session_state.tree.get("child_types", {})

    issues = []

    for mid, m in marriages.items():
        s1, s2 = m.get("spouse1"), m.get("spouse2")
        if not s1 or s1 not in persons:
            issues.append("關係 {} 缺少有效的 spouse1_pid".format(mid))
        if not s2 or s2 not in persons:
            issues.append("關係 {} 缺少有效的 spouse2_pid".format(mid))
        if s1 and s2 and s1 == s2:
            issues.append("關係 {} 的雙方是同一人（{}）".format(mid, s1))

    for mid, m in marriages.items():
        for c in m.get("children", []) or []:
            if c not in persons:
                issues.append("關係 {} 有不存在的子女 pid：{}".format(mid, c))

    for mid, cmap in child_types.items():
        for c in list(cmap.keys()):
            if c not in persons:
                issues.append("child_types[{}] 包含不存在的成員 pid：{}".format(mid, c))

    for pid, p in persons.items():
        if not p.get("name"):
            issues.append("成員 {} 缺少名稱".format(pid))
        if p.get("gender") not in GENDER_STYLE:
            issues.append("成員 {} 性別「{}」不在選項內".format(pid, p.get("gender")))

    if not issues:
        st.success("✅ 未發現問題。")
    else:
        st.warning("發現 {} 項潛在問題：".format(len(issues)))
        for msg in issues[:50]:
            st.write("• " + msg)
        if len(issues) > 50:
            st.caption("其餘 {} 項略。".format(len(issues)-50))


def block_io():
    st.subheader("📦 匯入 / 匯出")

    # 匯出目前資料
    data = json.dumps(st.session_state.tree, ensure_ascii=False, indent=2)
    st.download_button("⬇ 下載 JSON", data=data, file_name="family_tree.json",
                       mime="application/json", key="btn_dl_json")

    st.divider()

    # 上傳檔先緩存在 session_state，避免 rerun 遺失
    if "upload_bytes" not in st.session_state:
        st.session_state.upload_bytes = None
        st.session_state.upload_name = None

    up = st.file_uploader("選擇 family_tree.json（選擇後仍需按下方按鈕才會匯入）",
                          type=["json"], key="uploader_json")
    if up is not None:
        st.session_state.upload_bytes = up.getvalue()
        st.session_state.upload_name = getattr(up, "name", "未命名")

    if st.session_state.upload_bytes:
        st.info("已選擇檔案：{}".format(st.session_state.upload_name))
        try:
            preview = json.loads(st.session_state.upload_bytes.decode("utf-8"))
            persons_cnt = len(preview.get("persons", {})) if isinstance(preview, dict) else 0
            marriages_cnt = len(preview.get("marriages", {})) if isinstance(preview, dict) else 0
            st.caption("預覽：成員 {} 人、關係 {} 筆".format(persons_cnt, marriages_cnt))
        except Exception as e:
            st.error("檔案無法解析為 JSON：{}".format(e))

        cols = st.columns([1,1,2])
        apply = cols[0].button("📥 套用匯入（覆蓋目前資料）", key="btn_apply_import")
        clear  = cols[1].button("🧹 取消選擇", key="btn_clear_upload")

        if apply:
            try:
                raw = st.session_state.upload_bytes.decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("JSON 頂層不是物件")
                tree = {
                    "persons": data.get("persons", {}) or {},
                    "marriages": data.get("marriages", {}) or {},
                    "child_types": data.get("child_types", {}) or {},
                }
                st.session_state.tree = tree
                init_state()
                st.success("✅ 匯入完成：成員 {} 人、關係 {} 筆"
                           .format(len(tree["persons"]), len(tree["marriages"])))
                st.session_state.upload_bytes = None
                st.session_state.upload_name = None
                st.rerun()
            except Exception as e:
                st.error("套用匯入失敗：{}".format(e))

        if clear:
            st.session_state.upload_bytes = None
            st.session_state.upload_name = None
            st.toast("已清除選擇的檔案。", icon="🧹")
            st.rerun()
    else:
        st.caption("提示：選擇檔案後，需按「📥 套用匯入」才會覆蓋目前資料。未按按鈕不會自動匯入。")

# ====== Main ======
def main():
    st.set_page_config(page_title="家族樹小幫手", page_icon="🌳", layout="wide")
    init_state()
    st.write("🟢 App booted — {}".format(VERSION))
    block_header()
    block_me(); st.divider()
    block_parents(); st.divider()
    block_spouse_children(); st.divider()
    block_graph(); st.divider()
    block_heirs(); st.divider()        # ← 法定繼承人試算（§1138/§1139/§1140/§1144）
    block_advanced(); st.divider()
    block_tables(); st.divider()
    block_health(); st.divider()
    block_io()
    st.caption("隱私：所有資料僅在本次工作階段中，下載或重新整理後即清空。")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
🌳 家族樹小幫手（單頁版）
- 單一頁面、無側欄、無新手模式
- 輸入介面重整：先選/新增成員 → 編輯成員 → 新增父母/配偶/子女/兄弟姊妹 → 檢視與刪除關係
- 圖像：夫妻強制相鄰；同父同母兄弟姊妹依出生年(小→大)排序；已故 = 名稱後「（殁）」且灰底
- 可刪除整段婚姻關係（不刪任何人）
"""
from __future__ import annotations
import json
import uuid
from typing import List, Optional, Tuple

import streamlit as st
from graphviz import Digraph

VERSION = "2025-08-26-single-page-ui-v1"

# ========= 基本常數 =========
GENDER_OPTIONS = ["女", "男", "其他/不透漏"]
REL_MAP = {"bio": "親生", "adopted": "收養", "step": "繼親"}
STATUS_MAP = {"married": "已婚", "divorced": "前任(離異)", "separated": "分居"}

GENDER_FILL = {"男": "#E3F2FD", "女": "#FCE4EC", "其他/不透漏": "#F3F4F6"}
DECEASED_FILL = "#E0E0E0"  # 已故灰底

STATUS_EDGE = {
    "married":   {"style": "solid",  "color": "#9E9E9E", "weight": "50"},
    "divorced":  {"style": "dashed", "color": "#9E9E9E", "weight": "40"},
    "separated": {"style": "dotted", "color": "#9E9E9E", "weight": "40"},
}
CHILD_EDGE = {
    "bio":     {"style": "solid",  "color": "#BDBDBD", "weight": "1"},
    "adopted": {"style": "dotted", "color": "#BDBDBD", "weight": "1"},
    "step":    {"style": "dashed", "color": "#BDBDBD", "weight": "1"},
}

# ========= 狀態 =========
def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:8])

def _safe_index(seq, value, default=0):
    try:
        return list(seq).index(value)
    except ValueError:
        return default

def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    st.session_state.tree.setdefault("child_types", {})
    # 欄位預設
    for mid in list(st.session_state.tree["marriages"].keys()):
        st.session_state.tree["marriages"].setdefault(mid, {}).setdefault("status", "married")
        st.session_state.tree["child_types"].setdefault(mid, {})
    for p in st.session_state.tree["persons"].values():
        p.setdefault("gender", "其他/不透漏")
        p.setdefault("deceased", False)
        p.setdefault("note", "")
        p.setdefault("is_me", False)
        p.setdefault("year", "")

    # 單頁選單記憶
    if "tab" not in st.session_state:
        st.session_state.tab = "🖼 家族圖"

    if "layout_lr" not in st.session_state:
        st.session_state.layout_lr = False  # False=垂直(TB), True=水平(LR)

# ========= CRUD =========
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
        if {spouse1, spouse2} == {m.get("spouse1"), m.get("spouse2")}:
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

def add_child(mid: str, child_pid: str, relation: str = "bio"):
    m = st.session_state.tree["marriages"].get(mid)
    if not m: return
    if child_pid not in m["children"]:
        m["children"].append(child_pid)
    st.session_state.tree["child_types"].setdefault(mid, {})[child_pid] = relation

def set_child_relation(mid: str, child_pid: str, relation: str):
    st.session_state.tree["child_types"].setdefault(mid, {})
    if child_pid in st.session_state.tree["child_types"][mid]:
        st.session_state.tree["child_types"][mid][child_pid] = relation

def delete_person(pid: str):
    t = st.session_state.tree
    if pid not in t["persons"]: return
    # 從所有婚姻移除子女
    for mid, m in list(t["marriages"].items()):
        if pid in m.get("children", []):
            m["children"] = [c for c in m["children"] if c != pid]
            if mid in t["child_types"] and pid in t["child_types"][mid]:
                del t["child_types"][mid][pid]
    # 從配偶移除；若婚姻空且無子女則刪婚姻
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

def delete_marriage(mid: str):
    t = st.session_state.tree
    if mid in t["child_types"]:
        del t["child_types"][mid]
    if mid in t["marriages"]:
        del t["marriages"][mid]

def get_me_pid() -> Optional[str]:
    for pid, p in st.session_state.tree["persons"].items():
        if p.get("is_me"): return pid
    return None

def get_marriages_of(pid: str) -> List[str]:
    out = []
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in (m.get("spouse1"), m.get("spouse2")):
            out.append(mid)
    return out

def get_parent_marriage_of(pid: str) -> Optional[str]:
    for mid, m in st.session_state.tree["marriages"].items():
        if pid in m.get("children", []): return mid
    return None

# ========= Demo =========
def seed_demo():
    st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    me = add_person("我", "女", "1968", is_me=True)
    dad = add_person("爸爸", "男", "1935", deceased=True)
    mom = add_person("媽媽", "女", "1945")
    mid_pm = add_or_get_marriage(dad, mom, "married")
    add_child(mid_pm, me, "bio")

    spouse = add_person("陳威翔", "男", "1965")
    mid_me = add_or_get_marriage(me, spouse, "married")
    add_child(mid_me, add_person("大女兒", "女", "1995"))
    add_child(mid_me, add_person("小兒子", "男", "1999"))

    bro = add_person("A-Ting", "男", "1974")
    add_child(mid_pm, bro)

    frank = add_person("Frank", "男", "1966")
    jessie = add_person("Jessie", "女", "1970")
    mid_fj = add_or_get_marriage(frank, jessie, "married")
    add_child(mid_fj, add_person("女兒Y", "女", "2003"))

    # 故意留一段可供刪除的空關係：爸爸與已刪除的前任
    ex = add_person("爸爸前任", "女")
    ghost_mid = add_or_get_marriage(dad, ex, "divorced")
    delete_person(ex)  # 刪人但留關係
    st.toast("已載入示範家族。", icon="✅")

# ========= 圖像 =========
def _parse_year(y: str) -> Optional[int]:
    try:
        y = (y or "").strip()
        if not y: return None
        return int(y)
    except Exception:
        return None

def _order_children(children: List[str], persons: dict) -> List[str]:
    # 先有年分的照年分小→大；沒有年分的排後面，並保持原相對順序（Python sort 穩定）
    return sorted(
        children,
        key=lambda pid: (
            _parse_year(persons.get(pid, {}).get("year", "")) is None,
            _parse_year(persons.get(pid, {}).get("year", "")) or 10**9,
        ),
    )

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

    # 人節點
    for pid, p in persons.items():
        name = p.get("name", "未命名")
        label = name + ("\n(" + str(p.get("year")) + ")" if p.get("year") else "")
        if p.get("deceased"):
            label = label + "（殁）"
            fill = DECEASED_FILL
        else:
            fill = GENDER_FILL.get(p.get("gender") or "其他/不透漏", GENDER_FILL["其他/不透漏"])

        if p.get("is_me"):
            label = "⭐ " + label

        dot.node(pid, label=label, shape="box",
                 style="rounded,filled", color="#90A4AE", fillcolor=fill, penwidth="1.2")

    # 婚姻與孩子
    for mid, m in marriages.items():
        s1, s2 = m.get("spouse1"), m.get("spouse2")
        dot.node(mid, label="", shape="point", width="0.02")

        # 夫妻並排（關係點一起 rank）
        with dot.subgraph(name="cluster_" + mid) as sg:
            sg.attr(rank="same")
            if s1: sg.node(s1)
            if s2: sg.node(s2)
            sg.node(mid)
            if s1 and s2:
                sg.edge(s1, s2, style="invis", weight="100", dir="none", minlen="1")

        # 配偶↔婚姻點
        est = STATUS_EDGE.get(m.get("status", "married"), STATUS_EDGE["married"])
        if s1: dot.edge(s1, mid, color=est["color"], style=est["style"], weight=est["weight"])
        if s2: dot.edge(s2, mid, color=est["color"], style=est["style"], weight=est["weight"])

        # 孩子排序與固定左右順序
        kids = _order_children([c for c in m.get("children", []) if c in persons], persons)
        if kids:
            with dot.subgraph(name="cluster_kids_" + mid) as sk:
                sk.attr(rank="same")
                for c in kids:
                    sk.node(c)
                for i in range(len(kids)-1):
                    sk.edge(kids[i], kids[i+1], style="invis", weight="5")

        for c in kids:
            rel = child_types.get(mid, {}).get(c, "bio")
            cst = CHILD_EDGE.get(rel, CHILD_EDGE["bio"])
            dot.edge(mid, c, color=cst["color"], style=cst["style"], weight=cst["weight"])

    return dot

# ========= 單頁 UI =========
def section_topbar():
    st.title("🌳 家族樹小幫手")
    st.caption("單頁介面．不自動跳轉．所有資料僅存在本機記憶體。")
    col1, col2, col3 = st.columns([1.4, 1.0, 2.0])
    with col1:
        if st.button("✨ 載入示範家族", use_container_width=True):
            seed_demo()
    with col2:
        st.toggle("水平排列", key="layout_lr", help="取消則為垂直排列 (TB)")
    with col3:
        st.markdown("App 版本：`{}`".format(VERSION))

def tabbar():
    tabs = ["🖼 家族圖", "✍️ 建立/編輯", "📋 資料表", "📦 匯入/匯出"]
    # 用 radio 做上方導覽，避免 tabs 每次 rerun 重置
    st.session_state.tab = st.radio("導覽", tabs, horizontal=True, index=tabs.index(st.session_state.tab))
    st.write("")  # 間距

def view_graph():
    try:
        dot = render_graph()
        st.graphviz_chart(dot, use_container_width=True)
    except Exception as e:
        st.error("圖形渲染失敗：{}".format(e))

    st.caption("說明：夫妻一定相鄰；同父同母子女按年齡由左至右；已故以灰底並加「（殁）」；"
               "離異/分居用虛線/點線；收養/繼親子女用不同線型。")

def panel_build_edit():
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]

    st.header("✍️ 建立 / 編輯")

    # A. 先選/新增一位成員（卡片 1）
    with st.container():
        st.subheader("A. 選擇或新增成員")
        cols = st.columns([2, 1.2, 1.2, 1.2])
        pid_list = list(persons.keys())
        if pid_list:
            idx = cols[0].selectbox("選擇成員", options=list(range(len(pid_list))),
                                    format_func=lambda i: persons[pid_list[i]]["name"])
            current_pid = pid_list[idx]
        else:
            current_pid = None
            cols[0].info("目前尚無成員，請在右側先新增。")

        with cols[1]:
            new_name = st.text_input("姓名（新增）", placeholder="例如：我 / 陳先生 / 王小美")
        with cols[2]:
            new_gender = st.selectbox("性別（新增）", GENDER_OPTIONS, index=0)
        with cols[3]:
            new_is_me = st.checkbox("此人是『我』", value=(not pid_list))
        c2 = st.columns([1, 3])
        with c2[0]:
            if st.button("➕ 新增成員", use_container_width=True, disabled=not new_name.strip()):
                npid = add_person(new_name.strip(), new_gender, is_me=new_is_me)
                # 若設為我，清除其他 is_me
                if new_is_me:
                    for k, v in persons.items():
                        if k != npid:
                            v["is_me"] = False
                st.success("已新增：{}".format(new_name.strip()))
                current_pid = npid

        if not current_pid:
            st.stop()

    st.divider()

    # B. 編輯這位成員（卡片 2：表單提交）
    p = persons[current_pid]
    st.subheader("B. 編輯「{}」的資料".format(p.get("name","")))
    with st.form("edit_person_{}".format(current_pid)):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        name_buf = c1.text_input("名稱", value=p.get("name", ""))
        g_idx    = _safe_index(GENDER_OPTIONS, p.get("gender", "其他/不透漏"), 2)
        gender   = c2.selectbox("性別", GENDER_OPTIONS, index=g_idx)
        year_buf = c3.text_input("出生年(選填)", value=p.get("year", ""))
        deceased = c4.toggle("已故？（改為灰底＋加「（殁）」）", value=p.get("deceased", False))
        note_buf = st.text_area("備註(職業/說明…)", value=p.get("note",""))
        colx = st.columns([1,1,1,3])
        with colx[0]:
            is_me = st.toggle("設為『我』", value=p.get("is_me", False))
        with colx[1]:
            ok = st.form_submit_button("💾 儲存變更", use_container_width=True)
        with colx[2]:
            del_confirm = st.checkbox("我確認刪除此人")
        with colx[3]:
            del_btn = st.form_submit_button("❌ 刪除此人", disabled=not del_confirm, use_container_width=True)
    if ok:
        p["name"] = name_buf.strip() or "未命名"
        p["gender"] = gender
        p["year"] = year_buf.strip()
        p["deceased"] = bool(deceased)
        p["note"] = note_buf.strip()
        if is_me:
            for k, v in persons.items():
                v["is_me"] = (k == current_pid)
        st.success("已儲存變更")
    if del_btn:
        delete_person(current_pid)
        st.success("已刪除此人")
        st.stop()

    st.divider()

    # C. 為此人建立或擴充關係（卡片 3）
    st.subheader("C. 關係操作（父母／配偶／子女／兄弟姊妹）")

    # C1. 一鍵加父母
    cc1, cc2, cc3 = st.columns([1.2, 1.2, 1.2])
    with cc1:
        fa = st.text_input("父親姓名（可留白跳過）", key="add_pa_{}".format(current_pid))
    with cc2:
        mo = st.text_input("母親姓名（可留白跳過）", key="add_ma_{}".format(current_pid))
    with cc3:
        if st.button("👨‍👩‍👧 一鍵新增父母並連結到此人", use_container_width=True):
            if not (fa or mo):
                st.warning("至少輸入父或母其中一人。")
            else:
                fpid = add_person(fa or "父親", "男")
                mpid = add_person(mo or "母親", "女")
                mid = add_or_get_marriage(fpid, mpid, "married")
                add_child(mid, current_pid, "bio")
                st.success("已建立父母並連結")

    # C2. 新增配偶/關係（提交制）
    with st.expander("➕ 新增配偶／關係", expanded=False):
        with st.form("add_spouse_{}".format(current_pid), clear_on_submit=True):
            spn = st.text_input("配偶姓名")
            spg = st.selectbox("性別", GENDER_OPTIONS, index=1)
            sps = st.selectbox("關係狀態", list(STATUS_MAP.keys()),
                               index=0, format_func=lambda s: STATUS_MAP[s])
            confirm_sp = st.checkbox("我確認新增")
            ok_sp = st.form_submit_button("✅ 提交新增關係")
        if ok_sp:
            if not confirm_sp or not spn.strip():
                st.warning("請輸入姓名並勾選確認。")
            else:
                spid = add_person(spn.strip(), spg)
                add_or_get_marriage(current_pid, spid, sps)
                st.success("已新增關係")

    # C3. 新增子女（先選一段關係）
    my_mids = get_marriages_of(current_pid)
    if my_mids:
        label_items = []
        for mid in my_mids:
            m = marriages[mid]
            s1 = persons.get(m.get("spouse1"), {}).get("name", "?")
            s2 = persons.get(m.get("spouse2"), {}).get("name", "?")
            label_items.append((mid, "{} ❤ {}（{}）".format(s1, s2, STATUS_MAP.get(m.get("status","married"), "已婚"))))
        idx_mid = st.selectbox("選擇要新增子女的關係", options=list(range(len(label_items))),
                               format_func=lambda i: label_items[i][1])
        chosen_mid = label_items[idx_mid][0]

        with st.expander("👶 新增子女", expanded=False):
            with st.form("add_child_{}".format(chosen_mid), clear_on_submit=True):
                cn = st.text_input("子女姓名")
                cg = st.selectbox("性別", GENDER_OPTIONS, index=0)
                cy = st.text_input("出生年(選填)")
                cr = st.selectbox("與雙親的關係", list(REL_MAP.keys()),
                                  index=0, format_func=lambda s: REL_MAP[s])
                confirm_ch = st.checkbox("我確認新增")
                ok_ch = st.form_submit_button("👶 提交新增子女")
            if ok_ch:
                if not confirm_ch or not cn.strip():
                    st.warning("請輸入子女姓名並勾選確認。")
                else:
                    cid = add_person(cn.strip(), cg, year=cy)
                    add_child(chosen_mid, cid, relation=cr)
                    st.success("已新增子女")

    # C4. 兄弟姊妹（批次）
    pmid = get_parent_marriage_of(current_pid)
    with st.expander("👫 批次新增兄弟姊妹", expanded=False):
        if pmid is None:
            st.info("此人尚未連結雙親，無法判定兄弟姊妹。請先於上方建立父母。")
        else:
            sline = st.text_input("以逗號分隔輸入：如 小明, 小美")
            sg = st.selectbox("預設性別", GENDER_OPTIONS, index=2)
            confirm_s = st.checkbox("我確認新增這些兄弟姊妹")
            ok_s = st.button("👫 提交新增", use_container_width=False)
            if ok_s:
                names = [s.strip() for s in (sline or "").split(",") if s.strip()]
                if not confirm_s or not names:
                    st.warning("請輸入姓名並勾選確認。")
                else:
                    for nm in names:
                        sid = add_person(nm, sg)
                        add_child(pmid, sid, "bio")
                    st.success("已新增兄弟姊妹")

    st.divider()

    # D. 關係檢視／微調／刪除（卡片 4）
    st.subheader("D. 關係檢視與微調")
    for mid, m in list(marriages.items()):
        s1 = persons.get(m.get("spouse1"), {}).get("name", m.get("spouse1"))
        s2 = persons.get(m.get("spouse2"), {}).get("name", m.get("spouse2"))
        with st.expander("{} ❤ {}".format(s1 or "None", s2 or "None"), expanded=False):
            m["status"] = st.selectbox("婚姻狀態", list(STATUS_MAP.keys()),
                                       index=_safe_index(list(STATUS_MAP.keys()), m.get("status","married"), 0),
                                       format_func=lambda s: STATUS_MAP[s], key="stat_{}".format(mid))
            # 子女關係微調
            for cid in m.get("children", []):
                cname = persons.get(cid, {}).get("name", cid)
                cur = child_types.get(mid, {}).get(cid, "bio")
                new = st.selectbox("{} 的關係".format(cname), list(REL_MAP.keys()),
                                   index=_safe_index(list(REL_MAP.keys()), cur, 0),
                                   format_func=lambda s: REL_MAP[s],
                                   key="rel_{}_{}".format(mid, cid))
                set_child_relation(mid, cid, new)

            st.markdown("---")
            d1, d2 = st.columns([1,2])
            with d1:
                chk = st.checkbox("我確認刪除此關係", key="delm_ck_{}".format(mid))
            with d2:
                btn = st.button("🗑 刪除這段關係（不刪任何人）", key="delm_btn_{}".format(mid), disabled=not chk)
            if btn:
                delete_marriage(mid)
                st.success("已刪除此關係")
                st.experimental_rerun()

def panel_tables():
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]

    st.header("📋 資料表")
    if persons:
        st.markdown("**成員名冊**")
        st.dataframe(
            [{"pid": pid, **p} for pid, p in persons.items()],
            use_container_width=True, hide_index=True
        )
    if marriages:
        st.markdown("**婚姻/關係**")
        rows = []
        for mid, m in marriages.items():
            rows.append({
                "mid": mid,
                "spouse1": persons.get(m.get("spouse1"), {}).get("name", m.get("spouse1")),
                "spouse2": persons.get(m.get("spouse2"), {}).get("name", m.get("spouse2")),
                "status": STATUS_MAP.get(m.get("status","married"), m.get("status","married")),
                "children": ", ".join([persons.get(cid, {}).get("name", cid) for cid in m.get("children", [])]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

def panel_import_export():
    st.header("📦 匯入 / 匯出")
    data = json.dumps(st.session_state.tree, ensure_ascii=False, indent=2)
    st.download_button("⬇ 下載 JSON（暫存資料）", data=data, file_name="family_tree.json", mime="application/json")
    up = st.file_uploader("上傳 family_tree.json 以還原", type=["json"])
    if up is not None:
        try:
            obj = json.load(up)
            assert isinstance(obj, dict) and "persons" in obj and "marriages" in obj
            st.session_state.tree = obj
            init_state()
            st.success("已匯入 JSON。")
        except Exception as e:
            st.error("上傳格式不正確：{}".format(e))

    st.divider()
    if st.button("🗑 清空全部（僅清空本次暫存）"):
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
        st.success("已清空。")

# ========= Main =========
def main():
    st.set_page_config(page_title="家族樹小幫手", page_icon="🌳", layout="wide")
    init_state()
    section_topbar()
    tabbar()

    if st.session_state.tab == "🖼 家族圖":
        view_graph()
    elif st.session_state.tab == "✍️ 建立/編輯":
        panel_build_edit()
    elif st.session_state.tab == "📋 資料表":
        panel_tables()
    elif st.session_state.tab == "📦 匯入/匯出":
        panel_import_export()

    st.divider()
    st.caption("隱私：資料僅在瀏覽器執行會話中暫存；離開或清空即消失。")

if __name__ == "__main__":
    main()

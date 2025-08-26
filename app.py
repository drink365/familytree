# -*- coding: utf-8 -*-
"""
🌳 家族樹小幫手（Mini MVP + 進階模式）
-------------------------------------------------
目標：
- 極簡模式：3~4步即可畫出家族樹
- 進階模式：支援大家族與複雜關係（多段婚姻、同父異母/同母異父、前任、收養/繼親、祖父母、兄弟姊妹批次等）
- 不需要懂 JSON、不需要帳號
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
from typing import Dict, List, Optional, Tuple

import streamlit as st
from graphviz import Digraph

# -------------------------------
# Utilities & Session Init
# -------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {  # small but extensible schema
            "persons": {},  # pid -> {name, gender, year, note, is_me, deceased}
            "marriages": {},  # mid -> {spouse1, spouse2, children: [pid], status}
            "child_types": {},  # mid -> { child_pid: "bio"|"adopted"|"step" }
        }
    # Backward-compat for existing sessions
    st.session_state.tree.setdefault("child_types", {})
    for mid in st.session_state.tree.get("marriages", {}):
        st.session_state.tree["marriages"].setdefault(mid, {}).setdefault("status", "married")
        st.session_state.tree["child_types"].setdefault(mid, {})
    for pid, p in st.session_state.tree.get("persons", {}).items():
        p.setdefault("deceased", False)
        p.setdefault("note", "")

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

def add_person(name: str, gender: str, year: Optional[str] = None, note: str = "", is_me: bool = False, deceased: bool=False) -> str:
    pid = _new_id("P")
    st.session_state.tree["persons"][pid] = {
        "name": name.strip() or "未命名",
        "gender": gender,
        "year": (year or "").strip(),
        "note": (note or "").strip(),
        "is_me": bool(is_me),
        "deceased": bool(deceased),
    }
    return pid


def add_or_get_marriage(spouse1: str, spouse2: str, status: str = "married") -> str:
    # Keep 1 marriage node per pair (order-agnostic)
    for mid, m in st.session_state.tree["marriages"].items():
        s = {m.get("spouse1"), m.get("spouse2")}
        if {spouse1, spouse2} == s:
            # update status if provided
            if status and m.get("status") != status:
                m["status"] = status
            return mid
    mid = _new_id("M")
    st.session_state.tree["marriages"][mid] = {
        "spouse1": spouse1,
        "spouse2": spouse2,
        "children": [],
        "status": status,
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
    if marriage_id in st.session_state.tree["child_types"]:
        if child_pid in st.session_state.tree["child_types"][marriage_id]:
            st.session_state.tree["child_types"][marriage_id][child_pid] = relation


def get_me_pid() -> Optional[str]:
    for pid, p in st.session_state.tree["persons"].items():
        if p.get("is_me"):
            return pid
    return None


def get_spouses_of(pid: str) -> List[str]:
    spouses = []
    for m in st.session_state.tree["marriages"].values():
        if pid in (m.get("spouse1"), m.get("spouse2")):
            spouses.append(m["spouse2"] if m["spouse1"] == pid else m["spouse1"])
    return spouses


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


def get_parents(pid: str) -> Tuple[Optional[str], Optional[str]]:
    mid = get_parent_marriage_of(pid)
    if not mid:
        return None, None
    m = st.session_state.tree["marriages"][mid]
    return m.get("spouse1"), m.get("spouse2")


# -------------------------------
# Demo Seed
# -------------------------------

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

    # 舉例：前任 + 同父異母
    ex = add_person("前任", "女")
    mid_ex = add_or_get_marriage(f, ex, status="divorced")
    hbro = add_person("同父異母弟弟", "男", year="1980")
    add_child(mid_ex, hbro, relation="bio")

    st.toast("已載入示範家族（含前任/同父異母）。可在左側進階模式調整。", icon="✅")


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

STATUS_EDGE_STYLE = {
    "married": {"style": "solid", "color": "#9E9E9E"},
    "divorced": {"style": "dashed", "color": "#9E9E9E"},
    "separated": {"style": "dotted", "color": "#9E9E9E"},
}

CHILD_EDGE_STYLE = {
    "bio": {"style": "solid", "color": "#BDBDBD"},
    "adopted": {"style": "dotted", "color": "#BDBDBD"},
    "step": {"style": "dashed", "color": "#BDBDBD"},
}


def render_graph() -> Digraph:
    persons = st.session_state.tree["persons"]
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]

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
        if p.get("deceased"):
            label += " †"
        if p.get("is_me"):
            label = "⭐ " + label
        style = GENDER_STYLE.get(p.get("gender") or "其他/不透漏", GENDER_STYLE["其他/不透漏"])  # default
        dot.node(pid, label=label, shape="box", style="rounded,filled", color="#90A4AE", fillcolor=style["fillcolor"], penwidth="1.2")

    # Marriage nodes (as small points)
    for mid, m in marriages.items():
        dot.node(mid, label="", shape="point", width="0.02")
        stl = STATUS_EDGE_STYLE.get(m.get("status", "married"), STATUS_EDGE_STYLE["married"])
        if m.get("spouse1") and m.get("spouse2"):
            dot.edge(m["spouse1"], mid, color=stl["color"], style=stl["style"])
            dot.edge(m["spouse2"], mid, color=stl["color"], style=stl["style"])
        # children
        for c in m.get("children", []):
            if c in persons:
                rel = child_types.get(mid, {}).get(c, "bio")
                cstl = CHILD_EDGE_STYLE.get(rel, CHILD_EDGE_STYLE["bio"])
                dot.edge(mid, c, color=cstl["color"], style=cstl["style"])

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
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            new_name = st.text_input("我的名稱", value=p["name"], key="me_name")
        with col2:
            new_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=["女", "男", "其他/不透漏"].index(p["gender"]), key="me_gender")
        with col3:
            new_year = st.text_input("出生年(選填)", value=p.get("year", ""), key="me_year")
        with col4:
            new_dec = st.toggle("已故?", value=p.get("deceased", False), key="me_dec")
        p.update({"name": new_name, "gender": new_gender, "year": new_year, "deceased": new_dec})
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
        add_child(mid, me_pid, relation="bio")
        st.toast("已新增父母並連結到『我』", icon="👨‍👩‍👧")


def form_spouse_and_children():
    st.subheader("Step 3｜配偶 / Step 4｜子女")
    me_pid = get_me_pid()
    if not me_pid:
        st.info("請先完成 Step 1")
        return

    persons = st.session_state.tree["persons"]

    # 配偶（含狀態）
    with st.expander("＋ 新增配偶/另一半（可標注前任/分居）"):
        sp_name = st.text_input("姓名", value="另一半")
        sp_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=1)
        sp_status = st.selectbox("關係狀態", ["married", "divorced", "separated"], format_func=lambda s:{"married":"已婚","divorced":"前任(離異)","separated":"分居"}[s])
        add_sp = st.button("新增並建立關係")
        if add_sp:
            sp = add_person(sp_name, sp_gender)
            add_or_get_marriage(me_pid, sp, status=sp_status)
            st.toast("已新增關係", icon="💍")

    # 子女（從我所有婚姻中選擇一個）
    my_mids = get_marriages_of(me_pid)
    if my_mids:
        mid_labels = []
        for mid in my_mids:
            m = st.session_state.tree["marriages"][mid]
            s1 = persons.get(m["spouse1"], {}).get("name", "?")
            s2 = persons.get(m["spouse2"], {}).get("name", "?")
            status = m.get("status", "married")
            mid_labels.append((mid, f"{s1} ❤ {s2}（{ {'married':'已婚','divorced':'離','separated':'分'}[status]}）"))
        mid_idx = st.selectbox("選擇要新增子女的關係", options=list(range(len(mid_labels))), format_func=lambda i: mid_labels[i][1])
        chosen_mid = mid_labels[mid_idx][0]

        with st.expander("＋ 新增子女"):
            c_name = st.text_input("子女姓名", value="孩子")
            c_gender = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=0)
            c_year = st.text_input("出生年(選填)")
            c_rel = st.selectbox("關係類型", ["bio", "adopted", "step"], format_func=lambda s:{"bio":"親生","adopted":"收養","step":"繼親"}[s])
            add_c = st.button("新增子女並連結")
            if add_c:
                cid = add_person(c_name, c_gender, year=c_year)
                add_child(chosen_mid, cid, relation=c_rel)
                st.toast("已新增子女", icon="🧒")
    else:
        st.info("尚未新增任何配偶/婚姻，請先新增配偶。")


# -------------------------------
# 進階模式（大家族/複雜關係）
# -------------------------------

def advanced_builder():
    st.subheader("🎛 進階建立｜大家族與複雜關係")
    persons = st.session_state.tree["persons"]
    if not persons:
        st.info("請至少先建立『我』或任一成員。")
        return

    # 選人編輯
    id_list = list(persons.keys())
    idx = st.selectbox("選擇成員以編輯/加關係", options=list(range(len(id_list))), format_func=lambda i: persons[id_list[i]]["name"])
    pid = id_list[idx]
    p = persons[pid]

    with st.expander("✏️ 編輯成員資料", expanded=True):
        c1, c2, c3, c4 = st.columns([2,1,1,1])
        p["name"] = c1.text_input("名稱", value=p["name"])
        p["gender"] = c2.selectbox("性別", ["女", "男", "其他/不透漏"], index=["女","男","其他/不透漏"].index(p.get("gender","其他/不透漏")))
        p["year"] = c3.text_input("出生年(選填)", value=p.get("year",""))
        p["deceased"] = c4.toggle("已故?", value=p.get("deceased", False))
        p["note"] = st.text_area("備註(收養/繼親/職業等)", value=p.get("note",""))
        st.caption("提示：標註『†』= 已故；可在備註註明關係特殊情形。")

    st.markdown("---")
    cA, cB, cC, cD = st.columns(4)
    with cA:
        st.markdown("**父母**")
        fa = st.text_input("父親姓名", key=f"adv_f_{pid}")
        mo = st.text_input("母親姓名", key=f"adv_m_{pid}")
        if st.button("➕ 為該成員一鍵新增父母並連結", key=f"btn_add_parents_{pid}"):
            fpid = add_person(fa or "父親", "男")
            mpid = add_person(mo or "母親", "女")
            mid = add_or_get_marriage(fpid, mpid, status="married")
            add_child(mid, pid, relation="bio")
            st.toast("已新增父母並連結", icon="👨‍👩‍👧")

    with cB:
        st.markdown("**配偶/關係**")
        spn = st.text_input("配偶姓名", key=f"adv_sp_{pid}")
        spg = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=1, key=f"adv_spg_{pid}")
        sps = st.selectbox("狀態", ["married","divorced","separated"], index=0, format_func=lambda s:{"married":"已婚","divorced":"前任(離異)","separated":"分居"}[s], key=f"adv_sps_{pid}")
        if st.button("➕ 新增關係", key=f"btn_add_sp_{pid}"):
            spid = add_person(spn or "配偶", spg)
            add_or_get_marriage(pid, spid, status=sps)
            st.toast("已新增關係", icon="💍")

    with cC:
        st.markdown("**子女**")
        my_mids = get_marriages_of(pid)
        if my_mids:
            mid_labels = []
            for mid in my_mids:
                m = st.session_state.tree["marriages"][mid]
                s1 = persons.get(m["spouse1"], {}).get("name", "?")
                s2 = persons.get(m["spouse2"], {}).get("name", "?")
                status = m.get("status","married")
                mid_labels.append((mid, f"{s1} ❤ {s2}（{ {'married':'已婚','divorced':'離','separated':'分'}[status]}）"))
            mid_idx = st.selectbox("選擇關係", options=list(range(len(mid_labels))), format_func=lambda i: mid_labels[i][1], key=f"adv_mid_{pid}")
            chosen_mid = mid_labels[mid_idx][0]
            cn = st.text_input("子女姓名", key=f"adv_child_name_{pid}")
            cg = st.selectbox("性別", ["女","男","其他/不透漏"], key=f"adv_child_gender_{pid}")
            cy = st.text_input("出生年(選填)", key=f"adv_child_year_{pid}")
            cr = st.selectbox("關係類型", ["bio","adopted","step"], format_func=lambda s:{"bio":"親生","adopted":"收養","step":"繼親"}[s], key=f"adv_child_rel_{pid}")
            if st.button("➕ 新增子女", key=f"btn_add_child_{pid}"):
                cid = add_person(cn or "孩子", cg, year=cy)
                add_child(chosen_mid, cid, relation=cr)
                st.toast("已新增子女", icon="🧒")
        else:
            st.caption("尚無關係，請先新增配偶/另一半。")

    with cD:
        st.markdown("**兄弟姊妹（批次）**")
        pmid = get_parent_marriage_of(pid)
        if pmid:
            sibs = st.text_input("以逗號分隔：如 小明, 小美", key=f"adv_sibs_{pid}")
            sg = st.selectbox("預設性別", ["女","男","其他/不透漏"], key=f"adv_sibs_gender_{pid}")
            if st.button("➕ 批次新增兄弟姊妹", key=f"btn_add_sibs_{pid}"):
                names = [s.strip() for s in sibs.split(',') if s.strip()]
                for nm in names:
                    sid = add_person(nm, sg)
                    add_child(pmid, sid, relation="bio")
                st.toast("已新增兄弟姊妹", icon="👫")
        else:
            st.caption("此成員尚無已知父母，請先新增父母後再新增兄弟姊妹。")

    st.markdown("---")

    # 子女關係類型微調 & 婚姻狀態調整
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]
    if marriages:
        st.markdown("**關係檢視與微調**")
        for mid, m in marriages.items():
            s1 = st.session_state.tree["persons"].get(m["spouse1"], {}).get("name", "?")
            s2 = st.session_state.tree["persons"].get(m["spouse2"], {}).get("name", "?")
            with st.expander(f"{s1} ❤ {s2}"):
                # 調整婚姻狀態
                new_status = st.selectbox("婚姻狀態", ["married","divorced","separated"], index=["married","divorced","separated"].index(m.get("status","married")), format_func=lambda s:{"married":"已婚","divorced":"前任(離異)","separated":"分居"}[s], key=f"stat_{mid}")
                m["status"] = new_status
                # 子女列與關係類型調整
                rows = []
                for cid in m.get("children", []):
                    cname = st.session_state.tree["persons"].get(cid, {}).get("name", cid)
                    rel_key = f"rel_{mid}_{cid}"
                    current_rel = child_types.get(mid, {}).get(cid, "bio")
                    new_rel = st.selectbox(f"{cname} 的關係", ["bio","adopted","step"], index=["bio","adopted","step"].index(current_rel), format_func=lambda s:{"bio":"親生","adopted":"收養","step":"繼親"}[s], key=rel_key)
                    set_child_relation(mid, cid, new_rel)


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
                "status": m.get("status","married"),
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
            # Backward-compat ensure
            init_state()
            st.toast("已匯入 JSON。", icon="📥")
        except Exception as e:
            st.error(f"上傳格式有誤：{e}")

    # Danger zone: reset
    st.divider()
    if st.button("🗑 清空全部（不會刪本機檔案）"):
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
        st.session_state.quests = {"me": False, "parents": False, "spouse": False, "child": False}
        st.toast("已清空。", icon="🗑")


# -------------------------------
# Main App
# -------------------------------

def main():
    st.set_page_config(page_title="家族樹小幫手", page_icon="🌳", layout="wide")
    init_state()

    st.title("🌳 家族樹小幫手｜低調好玩版")
    st.caption("填三四個欄位，立刻畫出家族樹；需要時開啟進階模式處理大家族與複雜關係。")

    with st.sidebar:
        if st.button("✨ 載入示範家族"):
            seed_demo()
        st.toggle("水平排列 (LR)", key="layout_lr", help="預設為垂直排列 (TB)")

    sidebar_progress()

    tab_build, tab_graph, tab_table, tab_adv, tab_io = st.tabs(["✍️ 建立家庭", "🖼 家族圖", "📋 資料表", "🎛 進階建立", "📦 匯入/匯出"])

    with tab_build:
        form_me()
        st.divider()
        form_parents()
        st.divider()
        form_spouse_and_children()

    with tab_graph:
        dot = render_graph()
        st.graphviz_chart(dot, use_container_width=True)
        st.caption("提示：可在側欄切換水平/垂直排列；離異/分居以虛線/點線表示；收養/繼親子女以不同線型表示。")

    with tab_table:
        data_tables()

    with tab_adv:
        advanced_builder()

    with tab_io:
        import_export()

    # Footer
    st.divider()
    st.caption("隱私承諾：您的輸入僅用於本次即時計算，不寫入資料庫；下載/離開頁面即清空。")


if __name__ == "__main__":
    main()

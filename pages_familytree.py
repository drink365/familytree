# pages_familytree.py — Family tree with straight spouse line,
# deceased flag + inline editing & delete, female styling fixed (rounded when deceased)
# v1.1 (2025-09-01) — order可控/交換左右、防呆、婚姻刪除、匯入清理、渲染快取、JSON meta

import json
import uuid
from typing import List, Dict, Any, Tuple
import streamlit as st
import graphviz
import pandas as pd
from datetime import datetime

# ----------------------------- State & Helpers -----------------------------

APP_VERSION = "1.1"

def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def _init_state():
    if "family_tree" not in st.session_state:
        st.session_state.family_tree = {"persons": {}, "marriages": {}}
    if "selected_mid" not in st.session_state:
        st.session_state.selected_mid = None

def _reset_tree():
    st.session_state.family_tree = {"persons": {}, "marriages": {}}
    st.session_state.selected_mid = None

def _export_json() -> str:
    payload = {
        "_meta": {
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        },
        "persons": st.session_state.family_tree.get("persons", {}),
        "marriages": st.session_state.family_tree.get("marriages", {}),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def _import_json(text: str):
    obj = json.loads(text)
    persons = {str(k): v for k, v in obj.get("persons", {}).items()}
    marriages = {str(k): v for k, v in obj.get("marriages", {}).items()}

    # backfill & cleanup
    valid_pids = set(persons.keys())
    for mid, m in list(marriages.items()):
        sp = [x for x in (m.get("spouses") or []) if x in valid_pids]
        ch = [x for x in (m.get("children") or []) if x in valid_pids]
        ord2 = [x for x in (m.get("order") or sp) if x in sp]
        if not ord2:
            ord2 = sp[:]
        marriages[mid]["spouses"] = sp
        marriages[mid]["children"] = ch
        marriages[mid]["order"] = ord2
        if not sp and not ch:
            marriages.pop(mid, None)

    st.session_state.family_tree = {"persons": persons, "marriages": marriages}
    mids = list(marriages.keys())
    st.session_state.selected_mid = (
        st.session_state.selected_mid if st.session_state.selected_mid in mids
        else (mids[-1] if mids else None)
    )

# ----------------------------- Mutators -----------------------------

def add_person(name: str, gender: str = "", note: str = "", deceased: bool = False) -> str:
    pid = _uid("p")
    st.session_state.family_tree["persons"][pid] = {
        "name": (name or "").strip() or pid,
        "gender": (gender or "").strip(),
        "note": (note or "").strip(),
        "deceased": bool(deceased),
    }
    return pid

def add_or_get_marriage(p1: str, p2: str) -> str:
    """spouses 以排序後集合保存；order 以『輸入順序』保存（決定左右）。"""
    a, b = sorted([p1, p2])
    marriages = st.session_state.family_tree["marriages"]
    for mid, m in marriages.items():
        if sorted(m.get("spouses", [])) == [a, b]:
            if "order" not in m or not m["order"]:
                m["order"] = [p1, p2]
            return mid
    mid = _uid("m")
    marriages[mid] = {
        "spouses": [a, b],
        "order": [p1, p2],
        "children": [],
        "divorced": False
    }
    return mid

def toggle_divorce(mid: str, value: bool):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m:
        m["divorced"] = bool(value)

def _can_add_child(mid: str, child_pid: str) -> Tuple[bool, str]:
    marriages = st.session_state.family_tree["marriages"]
    persons = st.session_state.family_tree["persons"]
    m = marriages.get(mid)
    if not m or child_pid not in persons:
        return False, "資料錯誤：找不到婚姻或成員。"
    if child_pid in (m.get("spouses") or []):
        return False, "不可將配偶加入為子女。"
    if child_pid in m.get("children", []):
        return False, "此子女已存在於該婚姻。"
    return True, ""

def add_child(mid: str, child_pid: str):
    ok, msg = _can_add_child(mid, child_pid)
    if not ok:
        st.error(msg); return
    m = st.session_state.family_tree["marriages"].get(mid)
    if m and child_pid not in m["children"]:
        m["children"].append(child_pid)

def remove_children(mid: str, child_ids: List[str]):
    m = st.session_state.family_tree["marriages"].get(mid)
    if not m:
        return
    m["children"] = [c for c in m.get("children", []) if c not in set(child_ids)]

def _delete_person(pid: str):
    """Remove a person and clean up marriages that reference them."""
    persons = st.session_state.family_tree["persons"]
    marriages = st.session_state.family_tree["marriages"]
    if pid not in persons:
        return
    to_delete_mids = []
    for mid, m in list(marriages.items()):
        if pid in m.get("spouses", []):
            m["spouses"] = [x for x in m["spouses"] if x != pid]
            m["order"] = [x for x in (m.get("order") or []) if x != pid]
        if pid in m.get("children", []):
            m["children"] = [x for x in m["children"] if x != pid]
        if not m.get("spouses") and not m.get("children"):
            to_delete_mids.append(mid)
        if m.get("spouses") and not m.get("order"):
            m["order"] = m["spouses"][:]
    for mid in to_delete_mids:
        marriages.pop(mid, None)
    persons.pop(pid, None)

# ----------------------------- Rendering -----------------------------

def render_graph(tree: dict) -> graphviz.Digraph:
    g = graphviz.Digraph("G", engine="dot")
    g.attr(rankdir="TB", splines="line", nodesep="0.5", ranksep="0.9")
    g.attr("edge", dir="none", penwidth="2")

    persons: Dict[str, Dict[str, Any]] = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # Person nodes with color/shape logic (deceased overrides only the fillcolor)
    for pid, p in persons.items():
        name = p.get("name", pid)
        note = p.get("note")
        deceased = p.get("deceased", False)
        gender = p.get("gender", "")
        label = name + (f"\n{note}" if note else "")

        # base style by gender
        if gender == "男":
            shape = "box";         style = "filled";          fillcolor = "#E6F2FF"
        elif gender == "女":
            shape = "box";         style = "rounded,filled";  fillcolor = "#FFE6E6"
        else:
            shape = "box";         style = "rounded,filled";  fillcolor = "white"

        # deceased: keep shape/style (so females stay rounded), just change fill
        if deceased:
            fillcolor = "#E0E0E0"

        g.node(pid, label=label, shape=shape, style=style,
               fillcolor=fillcolor, fontsize="11")

    # Marriage mid points — tiny visible dot
    for mid in marriages.keys():
        g.node(mid, label="", shape="point", width="0.03", color="black")

    # Spouse line (one straight segment), with mid centered by invisible constraints
    for mid, m in marriages.items():
        order = m.get("order") or m.get("spouses", [])
        if len(order) != 2:
            order = m.get("spouses", [])[:2]
        divorced = m.get("divorced", False)

        if len(order) == 2:
            s1, s2 = order
            with g.subgraph(name=f"cluster_{mid}") as sg:
                sg.attr(rank="same", color="invis", style="invis", newrank="true")
                sg.node(s1); sg.node(mid); sg.node(s2)
                sg.edge(s1, mid, style="invis", constraint="true", weight="50000", minlen="0")
                sg.edge(mid, s2, style="invis", constraint="true", weight="50000", minlen="0")
            ls = "dashed" if divorced else "solid"
            g.edge(s1, s2, style=ls, constraint="true", weight="1800", minlen="0")

        elif len(order) == 1:
            s1 = order[0]
            with g.subgraph(name=f"cluster_{mid}") as sg:
                sg.attr(rank="same", color="invis", style="invis", newrank="true")
                sg.node(s1); sg.node(mid)
                sg.edge(s1, mid, style="invis", constraint="true", weight="40000", minlen="0")
            g.edge(s1, mid, style="solid", constraint="true", weight="1800", minlen="0")

    # Children downward
    for mid, m in marriages.items():
        children = [c for c in m.get("children", []) if c in persons]
        if not children:
            continue
        jn = f"{mid}_d"
        g.node(jn, label="", shape="point", width="0.04", color="black")
        g.edge(mid, jn, style="solid", weight="1200", minlen="1", constraint="true")
        for c in children:
            g.edge(jn, c, style="solid", weight="900", minlen="1", constraint="true")

    return g

# 渲染快取：以序列化字串作為 key
@st.cache_data(show_spinner=False)
def _graph_cached(tree_json: str) -> graphviz.Digraph:
    return render_graph(json.loads(tree_json))

# ----------------------------- UI -----------------------------

def _fmt_pid(persons: dict, pid: str) -> str:
    return f"{persons.get(pid, {}).get('name', pid)}｜{pid}"

def _sidebar_controls():
    # Per request: sidebar removed.
    return

def _bottom_io_controls():
    st.markdown("---")
    st.subheader("📦 資料匯入 / 匯出")
    c1, c2 = st.columns([2, 2], gap="large")

    with c1:
        st.markdown("**匯出目前資料**")
        st.download_button(
            label="⬇️ 匯出 JSON",
            data=_export_json().encode("utf-8"),
            file_name="family_tree.json",
            mime="application/json",
            use_container_width=True,
            key="bottom_export",
        )
        if st.button("🧹 全部清空", type="secondary", use_container_width=True, key="bottom_clear_inline"):
            _reset_tree()
            st.warning("已清空家族樹")
            _safe_rerun()

    with c2:
        st.markdown("**匯入 JSON 檔**")
        up2 = st.file_uploader("選擇檔案", type=["json"], key="bottom_uploader")
        if up2 is not None:
            if st.button("▶️ 執行匯入", type="primary", use_container_width=True):
                try:
                    _import_json(up2.read().decode("utf-8"))
                    st.success("已匯入，家族樹已更新")
                    _safe_rerun()
                except Exception as e:
                    st.error(f"匯入失敗：{e}")

def _person_manager():
    st.subheader("👤 人員管理")

    # Create form inputs for adding new person
    c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
    with c1:
        name = st.text_input("姓名*", key="person_name")
    with c2:
        gender = st.selectbox("性別", ["", "男", "女"], index=0)
    with c3:
        note = st.text_input("備註", key="person_note")
    with c4:
        deceased = st.checkbox("已故", key="person_deceased")

    if st.button("新增成員", type="primary"):
        if not name.strip():
            st.error("請輸入姓名")
        else:
            pid = add_person(name, gender, note, deceased)
            st.success(f"已新增：{name}（{pid}）")

    # Editable table
    persons = st.session_state.family_tree["persons"]
    if persons:
        base_rows = []
        for pid, v in persons.items():
            base_rows.append({
                "選取": False,
                "pid": pid,
                "姓名": v.get("name", ""),
                "性別": v.get("gender", ""),
                "備註": v.get("note", ""),
                "已故": bool(v.get("deceased", False)),
            })
        df = pd.DataFrame(base_rows)

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "選取": st.column_config.CheckboxColumn("選取", default=False),
                "pid": st.column_config.Column("pid", disabled=True),
                "姓名": st.column_config.TextColumn("姓名"),
                "性別": st.column_config.SelectboxColumn("性別", options=["", "男", "女"]),
                "備註": st.column_config.TextColumn("備註"),
                "已故": st.column_config.CheckboxColumn("已故", default=False),
            },
            key="people_editor",
        )

        csave, cdel = st.columns([1,1])
        with csave:
            if st.button("💾 儲存變更", type="primary", use_container_width=True):
                # write back
                for _, row in edited.iterrows():
                    pid = row["pid"]
                    if pid in persons:
                        persons[pid]["name"] = (row["姓名"] or "").strip() or pid
                        persons[pid]["gender"] = row["性別"]
                        persons[pid]["note"] = row["備註"]
                        persons[pid]["deceased"] = bool(row["已故"])
                st.success("已套用變更。")
                _safe_rerun()
        with cdel:
            if st.button("🗑️ 刪除所選", type="secondary", use_container_width=True):
                selected_pids = [row["pid"] for _, row in edited.iterrows() if row["選取"]]
                if not selected_pids:
                    st.warning("尚未選取要刪除的成員。")
                else:
                    for pid in selected_pids:
                        _delete_person(pid)
                    st.success(f"已刪除 {len(selected_pids)} 位成員，並清理關聯。")
                    _safe_rerun()

def _marriage_manager():
    st.subheader("💍 婚姻與子女")
    persons = st.session_state.family_tree.get("persons", {})
    # 依顯示姓名排序，方便選取
    p_values = sorted(list(persons.keys()), key=lambda x: persons.get(x, {}).get("name", x))

    c1, c2, c3 = st.columns(3)
    with c1:
        s1 = st.selectbox("配偶 A（左側）", ["-"] + p_values,
                          format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                          key="spouse_a_select")
    with c2:
        s2 = st.selectbox("配偶 B（右側）", ["-"] + p_values,
                          format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                          key="spouse_b_select")
    with c3:
        st.markdown("\n")
        make = st.button("建立婚姻")

    if make:
        if s1 == "-" or s2 == "-" or s1 == s2:
            st.error("請選擇兩位不同成員作為配偶")
        else:
            st.session_state.selected_mid = add_or_get_marriage(s1, s2)
            st.success(f"已建立/載入婚姻：{st.session_state.selected_mid}")

    marriages = st.session_state.family_tree.get("marriages", {})
    if marriages:
        mids = list(marriages.keys())
        if not st.session_state.selected_mid or st.session_state.selected_mid not in mids:
            st.session_state.selected_mid = mids[-1]
        default_index = mids.index(st.session_state.selected_mid)

        def _m_label(mid: str) -> str:
            m = marriages[mid]
            order = m.get("order") or m.get("spouses", [])
            names = [persons.get(x, {}).get('name', x) for x in order]
            return f"{mid}｜{' ↔ '.join(names)}"

        selected_mid = st.selectbox(
            "選擇婚姻（新增/刪除子女、設定離婚、交換左右）",
            options=mids, index=default_index, format_func=_m_label,
        )
        st.session_state.selected_mid = selected_mid

        # 交換左右
        m = marriages[selected_mid]
        order = m.get("order") or m.get("spouses", [])
        c_swap1, c_swap2 = st.columns([1,3])
        with c_swap1:
            if st.button("⇄ 交換左右", use_container_width=True):
                if len(order) == 2:
                    m["order"] = [order[1], order[0]]
                    st.success("已交換左右順序")
                    _safe_rerun()

        c4, c5 = st.columns([3, 2])
        with c4:
            child = st.selectbox(
                "選擇子女（現有成員）",
                ["-"] + p_values,
                format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                key="child_select",
            )
        with c5:
            st.markdown("\n")
            addc = st.button("加入子女")

        if addc:
            if child == "-":
                st.error("請選擇一位成員作為子女")
            else:
                add_child(selected_mid, child)
                # add_child 內含防呆與提示
                _safe_rerun()

        m = marriages[selected_mid]
        current_children = m.get("children", [])
        if current_children:
            st.markdown("**刪除子女（只移出此婚姻，不刪除成員）**")
            del_sel = st.multiselect(
                "選擇要刪除的子女",
                options=current_children,
                format_func=lambda x: _fmt_pid(persons, x),
                key="del_children_select"
            )
            if st.button("🗑️ 刪除子女"):
                if not del_sel:
                    st.warning("未選擇任何子女。")
                else:
                    remove_children(selected_mid, del_sel)
                    st.success("已從此婚姻移除選定子女")
                    _safe_rerun()
        else:
            st.info("此婚姻目前沒有子女。")

        divorced_now = marriages[selected_mid].get("divorced", False)
        new_divorced = st.checkbox("此婚姻為離婚狀態（配偶線改為虛線）", value=divorced_now)
        if new_divorced != divorced_now:
            toggle_divorce(selected_mid, new_divorced)
            st.info("已更新離婚狀態")
            _safe_rerun()

        # 刪除整段婚姻（不刪任何人）
        st.markdown("---")
        c_del_m1, _ = st.columns([1,3])
        with c_del_m1:
            if st.button("🗑️ 刪除此婚姻", use_container_width=True):
                marriages.pop(selected_mid, None)
                st.success("已刪除該婚姻（不影響成員資料）")
                st.session_state.selected_mid = list(marriages.keys())[-1] if marriages else None
                _safe_rerun()

        # 概覽表
        rows = []
        for mid, mm in marriages.items():
            ord2 = mm.get("order") or mm.get("spouses", [])
            sp_names = [persons.get(x, {}).get("name", x) for x in ord2]
            ch = [persons.get(x, {}).get("name", x) for x in mm.get("children", [])]
            rows.append({"mid": mid, "配偶": "、".join(sp_names),
                         "子女": "、".join(ch), "離婚": "是" if mm.get("divorced", False) else "否"})
        st.dataframe(rows, use_container_width=True, hide_index=True)

def _viewer():
    st.subheader("🌳 家族樹")
    tree = st.session_state.family_tree
    if not tree["persons"]:
        st.info("尚未建立任何成員。請先於上方區塊新增人員，並建立婚姻與子女。")
        return
    tree_json = json.dumps(tree, ensure_ascii=False, sort_keys=True)
    g = _graph_cached(tree_json)
    st.graphviz_chart(g, use_container_width=True)

# ----------------------------- Entry -----------------------------

def main():
    st.set_page_config(page_title="家族樹", page_icon="🌳", layout="wide")
    _init_state()
    st.title("🌳 家族樹")
    _sidebar_controls()
    with st.expander("➕ 建立 / 管理成員與關係", expanded=True):
        _person_manager(); _marriage_manager()
    _viewer()
    _bottom_io_controls()

def render():
    main()

if __name__ == "__main__":
    main()

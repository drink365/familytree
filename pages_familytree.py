# pages_familytree.py — Spouse-first stable layout with side anchors
# 修正：
# 1) 用 child->parent_mid 對應，對每對夫妻建立左右錨定鏈，避免新增兄弟姐妹後左右對調。
# 2) 夫妻線使用 ports：A:e->mid:w 與 mid:e->B:w，確保短而水平。
# 其餘：配偶相鄰(強力不可見鎖)、刪子女、左右交換、離婚虛線、清空即時刷新、線條一致等。

import json
import uuid
from typing import List
import streamlit as st
import graphviz

# ----------------------------- State & Helpers -----------------------------

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
    return json.dumps(st.session_state.family_tree, ensure_ascii=False, indent=2)

def _import_json(text: str):
    obj = json.loads(text)
    persons = {str(k): v for k, v in obj.get("persons", {}).items()}
    marriages = {str(k): v for k, v in obj.get("marriages", {}).items()}
    for mid, m in marriages.items():
        if m.get("spouses") and "order" not in m:
            marriages[mid]["order"] = list(m.get("spouses"))
    st.session_state.family_tree = {"persons": persons, "marriages": marriages}
    mids = list(marriages.keys())
    st.session_state.selected_mid = (
        st.session_state.selected_mid if st.session_state.selected_mid in mids
        else (mids[-1] if mids else None)
    )

# ----------------------------- Mutators -----------------------------

def add_person(name: str, gender: str = "", note: str = "") -> str:
    pid = _uid("p")
    st.session_state.family_tree["persons"][pid] = {
        "name": (name or "").strip() or pid,
        "gender": (gender or "").strip(),
        "note": (note or "").strip(),
    }
    return pid

def add_or_get_marriage(p1: str, p2: str) -> str:
    a, b = sorted([p1, p2])
    for mid, m in st.session_state.family_tree["marriages"].items():
        if sorted(m.get("spouses", [])) == [a, b]:
            if "order" not in m:
                m["order"] = [a, b]
            return mid
    mid = _uid("m")
    st.session_state.family_tree["marriages"][mid] = {
        "spouses": [a, b],
        "order": [a, b],
        "children": [],
        "divorced": False
    }
    return mid

def toggle_divorce(mid: str, value: bool):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m:
        m["divorced"] = bool(value)

def add_child(mid: str, child_pid: str):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m and child_pid not in m["children"]:
        m["children"].append(child_pid)

def remove_children(mid: str, child_ids: List[str]):
    m = st.session_state.family_tree["marriages"].get(mid)
    if not m:
        return
    m["children"] = [c for c in m.get("children", []) if c not in set(child_ids)]

def swap_spouse_order(mid: str):
    m = st.session_state.family_tree["marriages"].get(mid)
    if not m:
        return
    order = m.get("order") or m.get("spouses", [])[:]
    if len(order) == 2:
        m["order"] = [order[1], order[0]]

# ----------------------------- Rendering -----------------------------

def render_graph(tree: dict) -> graphviz.Digraph:
    g = graphviz.Digraph("G", engine="dot")
    g.attr(rankdir="TB", splines="line", nodesep="0.5", ranksep="0.9")
    g.attr("edge", dir="none", penwidth="2")  # 線條一致

    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # Person nodes
    for pid, p in persons.items():
        name = p.get("name", pid)
        note = p.get("note")
        label = name + (f"\n{note}" if note else "")
        gender = p.get("gender", "")
        if gender == "男":
            g.node(pid, label=label, shape="box", style="filled",
                   fillcolor="#E6F2FF", fontsize="11")
        elif gender == "女":
            g.node(pid, label=label, shape="box", style="rounded,filled",
                   fillcolor="#FFE6E6", fontsize="11")
        else:
            g.node(pid, label=label, shape="box", style="rounded,filled",
                   fillcolor="white", fontsize="11")

    # Marriage mid points（可見極小點）
    for mid in marriages.keys():
        g.node(mid, label="", shape="point", width="0.03", color="black")

    # 先建 child -> parent_mid 對應（每個人通常只有一組父母）
    parents_of = {}
    for pmid, m in marriages.items():
        for c in m.get("children", []):
            parents_of.setdefault(c, []).append(pmid)

    # 夫妻相鄰(不可見鎖)、夫妻可見線(ports)、左右錨定鏈
    for mid, m in marriages.items():
        order = m.get("order") or m.get("spouses", [])
        if len(order) != 2:
            order = m.get("spouses", [])[:2]
        divorced = m.get("divorced", False)

        if len(order) == 2:
            s1, s2 = order  # s1=左、s2=右
            # 相鄰鎖
            with g.subgraph(name=f"cluster_{mid}") as sg:
                sg.attr(rank="same", color="invis", style="invis", newrank="true")
                sg.node(s1); sg.node(mid); sg.node(s2)
                guard = f"{mid}_guard"
                sg.node(guard, label="", shape="point", width="0.01", style="invis")
                sg.edge(s1, mid, style="invis", constraint="true", weight="50000", minlen="0")
                sg.edge(mid, s2, style="invis", constraint="true", weight="50000", minlen="0")
                sg.edge(s2, guard, style="invis", constraint="true", weight="50000", minlen="0")

            # 可見夫妻線（水平短線）
            ls = "dashed" if divorced else "solid"
            g.edge(f"{s1}:e", f"{mid}:w", style=ls, constraint="false", weight="0", minlen="0")
            g.edge(f"{mid}:e", f"{s2}:w", style=ls, constraint="false", weight="0", minlen="0")

            # **左右錨定**：把 A 的父母 mid 固定在左邊、B 的父母 mid 固定在右邊
            left_parent  = (parents_of.get(s1) or [None])[0]
            right_parent = (parents_of.get(s2) or [None])[0]
            chain = []
            if left_parent:
                chain.append(left_parent)
            chain.extend([s1, mid, s2])
            if right_parent:
                chain.append(right_parent)

            if len(chain) >= 2:
                with g.subgraph(name=f"order_{mid}") as og:
                    og.attr(rank="same", color="invis", style="invis", newrank="true")
                    for i in range(len(chain)-1):
                        og.edge(chain[i], chain[i+1],
                                style="invis", constraint="true", weight="22000", minlen="0")

        elif len(order) == 1:
            s1 = order[0]
            with g.subgraph(name=f"cluster_{mid}") as sg:
                sg.attr(rank="same", color="invis", style="invis", newrank="true")
                sg.node(s1); sg.node(mid)
                sg.edge(s1, mid, style="invis", constraint="true", weight="40000", minlen="0")
            g.edge(f"{s1}:e", f"{mid}:w", style="solid", constraint="false", weight="0", minlen="0")

    # 子女：只由 mid 向下
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

# ----------------------------- UI -----------------------------

def _fmt_pid(persons: dict, pid: str) -> str:
    return f"{persons.get(pid, {}).get('name', pid)}｜{pid}"

def _sidebar_controls():
    st.sidebar.header("📦 匯入 / 匯出")
    st.sidebar.download_button(
        label="⬇️ 匯出 JSON",
        data=_export_json().encode("utf-8"),
        file_name="family_tree.json",
        mime="application/json",
        use_container_width=True,
    )
    if st.sidebar.button("🧹 全部清空", type="secondary", use_container_width=True, key="side_clear"):
        _reset_tree()
        st.sidebar.warning("已清空家族樹")
        _safe_rerun()

    uploaded = st.sidebar.file_uploader("⬆️ 匯入 JSON 檔", type=["json"], key="side_uploader")
    if uploaded is not None:
        if st.sidebar.button("▶️ 執行匯入", type="primary", use_container_width=True):
            try:
                _import_json(uploaded.read().decode("utf-8"))
                st.sidebar.success("已匯入，家族樹已更新")
                _safe_rerun()
            except Exception as e:
                st.sidebar.error(f"匯入失敗：{e}")

    st.sidebar.markdown("---")
    st.sidebar.caption("夫妻水平相鄰；有子女時自 mid 向下生成匯流點。")

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
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        name = st.text_input("姓名*", key="person_name")
    with c2:
        gender = st.selectbox("性別", ["", "男", "女"], index=0)
    with c3:
        note = st.text_input("備註", key="person_note")

    if st.button("新增成員", type="primary"):
        if not name.strip():
            st.error("請輸入姓名")
        else:
            pid = add_person(name, gender, note)
            st.success(f"已新增：{name}（{pid}）")

    if st.session_state.family_tree["persons"]:
        st.dataframe(
            {
                "pid": list(st.session_state.family_tree["persons"].keys()),
                "姓名": [v.get("name", "") for v in st.session_state.family_tree["persons"].values()],
                "性別": [v.get("gender", "") for v in st.session_state.family_tree["persons"].values()],
                "備註": [v.get("note", "") for v in st.session_state.family_tree["persons"].values()],
            },
            use_container_width=True,
            hide_index=True,
        )

def _marriage_manager():
    st.subheader("💍 婚姻與子女")
    persons = st.session_state.family_tree.get("persons", {})
    p_values = list(persons.keys())

    c1, c2, c3 = st.columns(3)
    with c1:
        s1 = st.selectbox("配偶 A", ["-"] + p_values,
                          format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                          key="spouse_a_select")
    with c2:
        s2 = st.selectbox("配偶 B", ["-"] + p_values,
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
            st.success(f"已建立婚姻：{st.session_state.selected_mid}")

    marriages = st.session_state.family_tree.get("marriages", {})
    if marriages:
        mids = list(marriages.keys())
        if not st.session_state.selected_mid or st.session_state.selected_mid not in mids:
            st.session_state.selected_mid = mids[-1]
        default_index = mids.index(st.session_state.selected_mid)

        def _m_label(mid: str) -> str:
            m = marriages[mid]
            order = m.get("order") or m.get("spouses", [])
            names = [persons.get(x, {}).get("name", x) for x in order]
            return f"{mid}｜{' ↔ '.join(names)}"

        selected_mid = st.selectbox(
            "選擇婚姻（新增/刪除子女、設定離婚、左右交換）",
            options=mids, index=default_index, format_func=_m_label,
        )
        st.session_state.selected_mid = selected_mid

        c4, c5, c6 = st.columns([3, 2, 2])
        with c4:
            child = st.selectbox(
                "選擇子女（現有成員）",
                ["-"] + list(persons.keys()),
                format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                key="child_select",
            )
        with c5:
            st.markdown("\n")
            addc = st.button("加入子女")
        with c6:
            st.markdown("\n")
            if st.button("⇄ 配偶左右交換"):
                swap_spouse_order(selected_mid)
                st.success("已交換左右（配偶仍相鄰）")
                _safe_rerun()

        if addc:
            if child == "-":
                st.error("請選擇一位成員作為子女")
            else:
                add_child(selected_mid, child)
                st.success("已加入子女")
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

        st.markdown("---")
        rows = []
        for mid, mm in marriages.items():
            order = mm.get("order") or mm.get("spouses", [])
            sp_names = [persons.get(x, {}).get("name", x) for x in order]
            ch = [persons.get(x, {}).get("name", x) for x in mm.get("children", [])]
            rows.append({"mid": mid, "配偶(左→右)": "、".join(sp_names),
                         "子女": "、".join(ch), "離婚": "是" if mm.get("divorced", False) else "否"})
        st.dataframe(rows, use_container_width=True, hide_index=True)

def _viewer():
    st.subheader("🌳 家族樹")
    tree = st.session_state.family_tree
    if not tree["persons"]:
        st.info("尚未建立任何成員。請先於上方區塊新增人員，並建立婚姻與子女。")
        return
    g = render_graph(tree)
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

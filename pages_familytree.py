# pages_familytree.py — anti-crossing edition with vertical drop node (mid_d)
# Spouses adjacent (s1–mid–s2), children from a lower drop point to avoid crossings,
# siblings same-rank, execute-import buttons, stable selection, width="stretch".

import json
import uuid
from typing import Dict, List, Tuple

import streamlit as st
import graphviz

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _uid(prefix: str = "id") -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:8])

def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def _init_state():
    if "family_tree" not in st.session_state:
        st.session_state.family_tree = {
            "persons": {},   # pid -> {"name": str, "gender": "男"|"女"|"" , "note": str}
            "marriages": {}, # mid -> {"spouses": [pid,pid], "children": [pid,...], "divorced": bool}
        }
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
    st.session_state.family_tree = {"persons": persons, "marriages": marriages}
    mids = list(marriages.keys())
    st.session_state.selected_mid = st.session_state.selected_mid if st.session_state.selected_mid in mids else (mids[-1] if mids else None)

# ------------------------------------------------------------
# Mutators
# ------------------------------------------------------------

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
            return mid
    mid = _uid("m")
    st.session_state.family_tree["marriages"][mid] = {"spouses": [a, b], "children": [], "divorced": False}
    return mid

def toggle_divorce(mid: str, value: bool):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m:
        m["divorced"] = bool(value)

def add_child(mid: str, child_pid: str):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m and child_pid not in m["children"]:
        m["children"].append(child_pid)

# ------------------------------------------------------------
# Graph utils
# ------------------------------------------------------------

def _parents_map(tree: dict) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for mid, m in tree.get("marriages", {}).items():
        for c in m.get("children", []):
            out[c] = mid
    return out

def _spouse_map(tree: dict) -> Dict[str, List[Tuple[str, List[str]]]]:
    out: Dict[str, List[Tuple[str, List[str]]]] = {}
    for mid, m in tree.get("marriages", {}).items():
        for s in m.get("spouses", []):
            out.setdefault(s, []).append((mid, m.get("spouses", [])))
    return out

# ------------------------------------------------------------
# Rendering (Graphviz)
# ------------------------------------------------------------

def render_graph(tree: dict) -> graphviz.Graph:
    g = graphviz.Graph("G", engine="dot")
    g.attr(rankdir="TB", splines="ortho", nodesep="0.46", ranksep="0.8")
    g.attr("edge", dir="none")

    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # People (style by gender)
    for pid, p in persons.items():
        name = p.get("name", pid)
        note = p.get("note")
        label = name + ("\n{}".format(note) if note else "")
        gender = p.get("gender", "")
        if gender == "男":
            g.node(pid, label=label, shape="box", style="filled", fillcolor="#E6F2FF", fontsize="11")
        elif gender == "女":
            g.node(pid, label=label, shape="box", style="rounded,filled", fillcolor="#FFE6E6", fontsize="11")
        else:
            g.node(pid, label=label, shape="box", style="rounded,filled", fillcolor="white", fontsize="11")

    # Marriage points (invisible)
    for mid in marriages.keys():
        g.node(mid, label="", shape="point", width="0.01", style="invis")
        g.node(f"{mid}_d", label="", shape="point", width="0.01", style="invis")  # drop node

    # Spouses: enforce adjacency s1–mid–s2 (order with invisible constraints; visible line doesn't constrain)
    for mid, m in marriages.items():
        sp = list(m.get("spouses", []))
        divorced = m.get("divorced", False)
        if len(sp) == 2:
            s1, s2 = sp
            with g.subgraph(name=f"rank_{mid}") as sg:
                sg.attr(rank="same")
                sg.node(s1); sg.node(mid); sg.node(s2)

            # lock order & closeness
            g.edge(s1, mid, style="invis", weight="500", constraint="true", minlen="0")
            g.edge(mid, s2, style="invis", weight="500", constraint="true", minlen="0")

            # visible spouse lines (do NOT influence layout => avoid crossings)
            line_style = "dashed" if divorced else "solid"
            g.edge(s1, mid, style=line_style, penwidth="2", constraint="false", tailport="e", headport="w")
            g.edge(mid, s2, style=line_style, penwidth="2", constraint="false", tailport="e", headport="w")

        elif len(sp) == 1:
            s1 = sp[0]
            with g.subgraph(name=f"rank_single_{mid}") as sg:
                sg.attr(rank="same")
                sg.node(s1); sg.node(mid)
            g.edge(s1, mid, style="solid", penwidth="2", constraint="false", tailport="e", headport="w")
            g.edge(s1, mid, style="invis", weight="400", constraint="true", minlen="0")  # keep together
            g.edge(mid, f"{mid}_d", style="invis", weight="300", constraint="true", minlen="1")  # prepare drop

    # Siblings: same level & ordering; children come from a lower drop node to avoid spouse-line crossings
    parent_of = _parents_map(tree)
    spouse_map = _spouse_map(tree)

    for mid, m in marriages.items():
        children = [c for c in m.get("children", []) if c in persons]

        # siblings same rank
        if children:
            with g.subgraph(name=f"rank_children_{mid}") as sgc:
                sgc.attr(rank="same")
                for c in children:
                    sgc.node(c)

        # vertical drop: mid -> mid_d (invisible, constraining), then mid_d -> child (visible, constraining)
        g.edge(mid, f"{mid}_d", style="invis", weight="500", minlen="1", constraint="true", tailport="s", headport="n")
        for c in children:
            g.edge(f"{mid}_d", c, weight="300", minlen="1", constraint="true", tailport="s", headport="n")

        # order siblings to encourage cross-family adjacency
        if len(children) >= 2:
            right_pref, neutral = [], []
            for c in children:
                pref = "neutral"
                for _mid2, spouses2 in spouse_map.get(c, []):
                    partners = [x for x in spouses2 if x != c]
                    if partners:
                        partner = partners[0]
                        if parent_of.get(partner) and parent_of.get(partner) != mid:
                            pref = "right"; break
                (right_pref if pref == "right" else neutral).append(c)
            ordered = neutral + right_pref
            for i in range(len(ordered) - 1):
                g.edge(ordered[i], ordered[i+1], style="invis", weight="180", constraint="true")

    return g

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

def _fmt_pid(persons: dict, pid: str) -> str:
    return "{}｜{}".format(persons.get(pid, {}).get("name", pid), pid)

def _sidebar_controls():
    st.sidebar.header("📦 匯入 / 匯出")

    st.sidebar.download_button(
        label="⬇️ 匯出 JSON",
        data=_export_json().encode("utf-8"),
        file_name="family_tree.json",
        mime="application/json",
        width="stretch",
    )

    uploaded = st.sidebar.file_uploader("⬆️ 匯入 JSON 檔", type=["json"], key="side_uploader")
    if uploaded is not None:
        if st.sidebar.button("▶️ 執行匯入", type="primary"):
            try:
                _import_json(uploaded.read().decode("utf-8"))
                st.sidebar.success("已匯入，家族樹已更新")
                _rerun()
            except Exception as e:
                st.sidebar.error("匯入失敗：{}".format(e))

    if st.sidebar.button("🧹 全部清空", type="secondary", key="side_clear"):
        _reset_tree()
        st.sidebar.warning("已清空家族樹")

    st.sidebar.markdown("---")
    st.sidebar.caption("提示：配偶以水平線連結（離婚為虛線），子女由較低的落點垂直連接，避免交錯。")

def _bottom_io_controls():
    st.markdown("---")
    st.subheader("📦 資料匯入 / 匯出")
    c1, c2, c3 = st.columns([2, 2, 1])

    with c1:
        st.markdown("**匯出目前資料**")
        st.download_button(
            label="⬇️ 匯出 JSON",
            data=_export_json().encode("utf-8"),
            file_name="family_tree.json",
            mime="application/json",
            width="stretch",
            key="bottom_export",
        )

    with c2:
        st.markdown("**匯入 JSON 檔**")
        up2 = st.file_uploader("選擇檔案", type=["json"], key="bottom_uploader")
        if up2 is not None:
            if st.button("▶️ 執行匯入", type="primary"):
                try:
                    _import_json(up2.read().decode("utf-8"))
                    st.success("已匯入，家族樹已更新")
                    _rerun()
                except Exception as e:
                    st.error("匯入失敗：{}".format(e))

    with c3:
        st.markdown("**動作**")
        if st.button("🧹 全部清空", type="secondary", key="bottom_clear"):
            _reset_tree()
            st.warning("已清空家族樹")

def _person_manager():
    st.subheader("👤 人員管理")
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        name = st.text_input("姓名*", key="person_name")
    with c2:
        gender = st.selectbox("性別", ["", "男", "女"], index=0, help="只提供男/女選項")
    with c3:
        note = st.text_input("備註", key="person_note")

    if st.button("新增成員", type="primary"):
        if not name.strip():
            st.error("請輸入姓名")
        else:
            pid = add_person(name, gender, note)
            st.success("已新增：{}（{}）".format(name, pid))

    if st.session_state.family_tree["persons"]:
        st.dataframe(
            {
                "pid": list(st.session_state.family_tree["persons"].keys()),
                "姓名": [v.get("name", "") for v in st.session_state.family_tree["persons"].values()],
                "性別": [v.get("gender", "") for v in st.session_state.family_tree["persons"].values()],
                "備註": [v.get("note", "") for v in st.session_state.family_tree["persons"].values()],
            },
            width="stretch",
            hide_index=True,
        )

def _marriage_manager():
    st.subheader("💍 婚姻與子女")
    persons = st.session_state.family_tree.get("persons", {})
    p_values = list(persons.keys())

    c1, c2, c3 = st.columns(3)
    with c1:
        s1 = st.selectbox("配偶 A", ["-"] + p_values, format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x), key="spouse_a_select")
    with c2:
        s2 = st.selectbox("配偶 B", ["-"] + p_values, format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x), key="spouse_b_select")
    with c3:
        st.markdown("\n")
        make = st.button("建立婚姻")

    if make:
        if s1 == "-" or s2 == "-" or s1 == s2:
            st.error("請選擇兩位不同成員作為配偶")
        else:
            st.session_state.selected_mid = add_or_get_marriage(s1, s2)
            st.success("已建立婚姻：{}".format(st.session_state.selected_mid))

    marriages = st.session_state.family_tree.get("marriages", {})
    if marriages:
        mids = list(marriages.keys())
        if not st.session_state.selected_mid or st.session_state.selected_mid not in mids:
            st.session_state.selected_mid = mids[-1]
        default_index = mids.index(st.session_state.selected_mid)

        def _m_label(mid: str) -> str:
            sp = marriages[mid].get("spouses", [])
            names = [persons.get(x, {}).get("name", x) for x in sp]
            return "{}｜{}".format(mid, " ↔ ".join(names))

        selected_mid = st.selectbox("選擇婚姻（用於新增子女/設定離婚）",
                                    options=mids, index=default_index, format_func=_m_label)
        st.session_state.selected_mid = selected_mid

        c4, c5 = st.columns([3, 2])
        with c4:
            child = st.selectbox("選擇子女（現有成員）",
                                 ["-"] + list(persons.keys()),
                                 format_func=lambda x: "-" if x=="-" else _fmt_pid(persons, x),
                                 key="child_select")
        with c5:
            st.markdown("\n")
            addc = st.button("加入子女")

        if addc:
            if child == "-":
                st.error("請選擇一位成員作為子女")
            else:
                add_child(selected_mid, child)
                st.success("已加入子女")

        divorced_now = marriages[selected_mid].get("divorced", False)
        new_divorced = st.checkbox("此婚姻為離婚狀態（配偶線改為虛線）", value=divorced_now)
        if new_divorced != divorced_now:
            toggle_divorce(selected_mid, new_divorced)
            st.info("已更新離婚狀態")

        st.markdown("---")
        rows = []
        for mid, m in marriages.items():
            sp = [persons.get(x, {}).get("name", x) for x in m.get("spouses", [])]
            ch = [persons.get(x, {}).get("name", x) for x in m.get("children", [])]
            rows.append({"mid": mid, "配偶": "、".join(sp), "子女": "、".join(ch), "離婚": "是" if m.get("divorced", False) else "否"})
        st.dataframe(rows, width="stretch", hide_index=True)

def _viewer():
    st.subheader("🌳 家族樹")
    tree = st.session_state.family_tree
    if not tree["persons"]:
        st.info("尚未建立任何成員。請先於上方區塊新增人員，並建立婚姻與子女。")
        return
    g = render_graph(tree)
    st.graphviz_chart(g, width="stretch")

# ------------------------------------------------------------
# Entry
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="家族樹", page_icon="🌳", layout="wide")
    _init_state()

    st.title("🌳 家族樹")

    _sidebar_controls()
    with st.expander("➕ 建立 / 管理成員與關係", expanded=True):
        _person_manager()
        _marriage_manager()

    _viewer()
    _bottom_io_controls()

def render():
    main()

if __name__ == "__main__":
    main()

import json
import uuid
from typing import Dict, List, Tuple

import streamlit as st
import graphviz

# ------------------------------------------------------------
# Helpers: IDs, Session, Storage
# ------------------------------------------------------------

def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _init_state():
    if "family_tree" not in st.session_state:
        st.session_state.family_tree = {
            "persons": {},
            "marriages": {},
        }
    if "last_download" not in st.session_state:
        st.session_state.last_download = ""


def _reset_tree():
    st.session_state.family_tree = {
        "persons": {},
        "marriages": {},
    }


def _export_json() -> str:
    return json.dumps(st.session_state.family_tree, ensure_ascii=False, indent=2)


def _import_json(text: str):
    obj = json.loads(text)
    assert isinstance(obj, dict) and "persons" in obj and "marriages" in obj
    persons = {str(k): v for k, v in obj.get("persons", {}).items()}
    marriages = {str(k): v for k, v in obj.get("marriages", {}).items()}
    st.session_state.family_tree = {"persons": persons, "marriages": marriages}

# ------------------------------------------------------------
# Core model mutators
# ------------------------------------------------------------

def add_person(name: str, gender: str = "", note: str = "") -> str:
    pid = _uid("p")
    st.session_state.family_tree["persons"][pid] = {
        "name": name.strip() or pid,
        "gender": gender.strip(),
        "note": note.strip(),
    }
    return pid

def add_or_get_marriage(p1: str, p2: str) -> str:
    a, b = sorted([p1, p2])
    for mid, m in st.session_state.family_tree["marriages"].items():
        sp = sorted(m.get("spouses", []))
        if sp == [a, b]:
            return mid
    mid = _uid("m")
    st.session_state.family_tree["marriages"][mid] = {
        "spouses": [a, b],
        "children": [],
        "divorced": False,
    }
    return mid

def toggle_divorce(mid: str, value: bool):
    m = st.session_state.family_tree["marriages"].get(mid)
    if m:
        m["divorced"] = bool(value)

def add_child(mid: str, child_pid: str):
    m = st.session_state.family_tree["marriages"].get(mid)
    if not m:
        return
    if child_pid not in m["children"]:
        m["children"].append(child_pid)

# ------------------------------------------------------------
# Graph construction utilities
# ------------------------------------------------------------

def _parents_map(tree: dict) -> Dict[str, str]:
    out = {}
    for mid, m in tree.get("marriages", {}).items():
        for c in m.get("children", []):
            out[c] = mid
    return out

def _spouse_map(tree: dict) -> Dict[str, List[Tuple[str, List[str]]]]:
    out = {}
    for mid, m in tree.get("marriages", {}).items():
        spouses = list(m.get("spouses", []))
        for s in spouses:
            out.setdefault(s, []).append((mid, spouses))
    return out

# ------------------------------------------------------------
# Rendering (Graphviz)
# ------------------------------------------------------------

def render_graph(tree: dict) -> graphviz.Graph:
    g = graphviz.Graph("G", engine="dot")
    g.attr(rankdir="TB", splines="ortho", nodesep="0.35", ranksep="0.6")

    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # Create person nodes with color and shape by gender
    for pid, p in persons.items():
        label = p.get("name", pid)
        gender = p.get("gender", "")
        if gender == "男":
            g.node(pid, label=label, shape="box", style="filled", fillcolor="lightblue")
        else:
            g.node(pid, label=label, shape="box", style="rounded,filled", fillcolor="mistyrose")

    # Invisible point nodes for marriages
    for mid, m in marriages.items():
        g.node(mid, label="", shape="point", width="0.01")

    # Horizontal spouse layout on same rank
    for mid, m in marriages.items():
        spouses = list(m.get("spouses", []))
        divorced = m.get("divorced", False)
        if len(spouses) == 2:
            s1, s2 = spouses
            with g.subgraph() as sg:
                sg.attr(rank="same")
                sg.edge(s1, s2, style="dashed" if divorced else "solid", penwidth="2", constraint="false")
                sg.edge(s1, mid, style="invis", weight="200")
                sg.edge(s2, mid, style="invis", weight="200")
        elif len(spouses) == 1:
            s1 = spouses[0]
            g.edge(s1, mid, style="invis", weight="120")

    # Children edges & sibling ordering
    parent_of = _parents_map(tree)
    spouse_map = _spouse_map(tree)
    for mid, m in marriages.items():
        children = list(m.get("children", []))
        for c in children:
            if c in persons:
                g.edge(mid, c, weight="8")

        if len(children) >= 2:
            right_pref = []
            neutral = []
            for c in children:
                pref = "neutral"
                for m2_id, spouses2 in spouse_map.get(c, []):
                    partners = [x for x in spouses2 if x != c]
                    if not partners:
                        continue
                    partner = partners[0]
                    partner_parents = parent_of.get(partner)
                    if partner_parents and partner_parents != mid:
                        pref = "right"
                        break
                if pref == "right":
                    right_pref.append(c)
                else:
                    neutral.append(c)
            ordered_children = neutral + right_pref
            if len(ordered_children) >= 2:
                for i in range(len(ordered_children)-1):
                    a = ordered_children[i]
                    b = ordered_children[i+1]
                    if a in persons and b in persons:
                        g.edge(a, b, style="invis", weight="150", constraint="true")

    return g

# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------

def _sidebar_controls():
    st.sidebar.header("📦 匯入 / 匯出")
    data_str = _export_json()
    st.sidebar.download_button(
        label="⬇️ 匯出 JSON",
        data=data_str.encode("utf-8"),
        file_name="family_tree.json",
        mime="application/json",
        use_container_width=True,
    )
    uploaded = st.sidebar.file_uploader("⬆️ 匯入 JSON 檔", type=["json"])
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8")
            _import_json(text)
            st.sidebar.success("已匯入，家族樹已更新")
        except Exception as e:
            st.sidebar.error(f"匯入失敗：{e}")
    if st.sidebar.button("🧹 全部清空", type="secondary", use_container_width=True):
        _reset_tree()
        st.sidebar.warning("已清空家族樹")
    st.sidebar.markdown("---")
    st.sidebar.caption("提示：配偶使用水平線（離婚為虛線），子女由婚姻點往下連。")


def _person_manager():
    st.subheader("👤 人員管理")
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        name = st.text_input("姓名*", key="person_name")
    with c2:
        gender = st.selectbox("性別", ["", "男", "女"], index=0, help="只提供男/女選項")
    with c3:
        note = st.text_input("備註", key="person_note")
    add = st.button("新增成員", type="primary")
    if add:
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
    p_opts = [(v.get("name", k), k) for k, v in persons.items()]
    p_values = [pid for _, pid in p_opts]

    c1, c2, c3 = st.columns(3)
    with c1:
        s1 = st.selectbox(
            "配偶 A",
            options=["-"] + p_values,
            format_func=lambda x: "-" if x == "-" else f"{persons[x]['name']}｜{x}",
            key="spouse_a_select"
        )
    with c2:
        s2 = st.selectbox(
            "配偶 B",
            options=["-"] + p_values,
            format_func=lambda x: "-" if x == "-" else f"{persons[x]['name']}｜{x}",
            key="spouse_b_select"
        )
    with c3:
        st.markdown("
")
        make = st.button("建立婚姻")
    if make:
        if s1 == "-" or s2 == "-" or s1 == s2:
            st.error("請選擇兩位不同成員作為配偶")
        else:
            mid = add_or_get_marriage(s1, s2)
            # 記住剛建立的婚姻，避免畫面更新後選擇消失
            st.session_state["marriage_select"] = mid
            st.success(f"已建立婚姻：{mid}")
    marriages = st.session_state.family_tree.get("marriages", {})
    if marriages:
        mids = list(marriages.keys())
        def _m_label(mid: str) -> str:
            sp = marriages[mid].get("spouses", [])
            names = [persons.get(x, {}).get("name", x) for x in sp]
            return f"{mid}｜{' ↔ '.join(names)}"
        selected_mid = st.selectbox(
            "選擇婚姻（用於新增子女/設定離婚）",
            options=mids,
            format_func=_m_label,
            key="marriage_select"
        )
        c4, c5 = st.columns([3, 2])
        with c4:
            child = st.selectbox(
            "選擇子女（現有成員）",
            options=["-"] + list(persons.keys()),
            format_func=lambda x: "-" if x == "-" else f"{persons[x]['name']}｜{x}",
            key="child_select"
        )
        with c5:
            st.markdown("\n")
            addc = st.button("加入子女")
        if addc:
            if child == "-":
                st.error("請選擇一位成員作為子女")
            else:
                add_child(selected_mid, child)
                # 保留目前選取的婚姻，不跳畫面
                st.session_state["marriage_select"] = selected_mid
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
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _viewer():
    st.subheader("🌳 家族樹")
    tree = st.session_state.family_tree
    if not tree["persons"]:
        st.info("尚未建立任何成員。請先於上方區塊新增人員，並建立婚姻與子女。")
        return
    g = render_graph(tree)
    st.graphviz_chart(g, use_container_width=True)

# ------------------------------------------------------------
# Page entry
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

# hosting frameworks entry

def render():
    main()

if __name__ == "__main__":
    main()

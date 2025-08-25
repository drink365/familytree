
import streamlit as st
from graphviz import Digraph
from collections import defaultdict

# ---------------------------------
# Data model
# ---------------------------------

def _empty_data():
    return {
        "persons": {},          # pid -> {name, sex('男'/'女'), alive(True/False), note}
        "marriages": {},        # mid -> {a, b, divorced(bool)}
        "children": [],         # list of {mid, child}
        "_seq": 0,
    }

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def next_id():
    st.session_state.data["_seq"] += 1
    return str(st.session_state.data["_seq"])

def ensure_person(name, sex="男", alive=True, note=""):
    d = st.session_state.data
    # unique by name for demo
    for pid, p in d["persons"].items():
        if p["name"] == name:
            return pid
    pid = next_id()
    d["persons"][pid] = {"name": name, "sex": sex, "alive": alive, "note": note}
    return pid

def add_marriage(a, b, divorced=False):
    d = st.session_state.data
    for mid, m in d["marriages"].items():
        if {m["a"], m["b"]} == {a, b}:
            m["divorced"] = bool(divorced)
            return mid
    mid = f"M{next_id()}"
    d["marriages"][mid] = {"a": a, "b": b, "divorced": bool(divorced)}
    return mid

def add_child(mid, child):
    d = st.session_state.data
    if mid not in d["marriages"]:
        return
    if not any((x["mid"] == mid and x["child"] == child) for x in d["children"]):
        d["children"].append({"mid": mid, "child": child})

def load_demo(clear=True):
    if clear:
        st.session_state.data = _empty_data()
    yilang = ensure_person("陳一郎", "男", True)
    exwife = ensure_person("陳前妻", "女", True)
    wife   = ensure_person("陳妻",   "女", True)
    wangzi = ensure_person("王子",   "男", True)
    wz_wife= ensure_person("王子妻", "女", True)
    chenda = ensure_person("陳大",   "男", True)
    chener = ensure_person("陳二",   "男", True)
    chensan= ensure_person("陳三",   "男", True)
    w_sun  = ensure_person("王孫",   "男", True)

    mid_now = add_marriage(yilang, wife,   divorced=False)
    mid_ex  = add_marriage(yilang, exwife, divorced=True)

    add_child(mid_now, chenda)
    add_child(mid_now, chener)
    add_child(mid_now, chensan)
    add_child(mid_ex,  wangzi)

    mid_wang = add_marriage(wangzi, wz_wife, divorced=False)
    add_child(mid_wang, w_sun)

# ---------------------------------
# Helpers
# ---------------------------------

COLOR_MALE   = "#dff2ff"
COLOR_FEMALE = "#ffe9f2"
COLOR_DEAD   = "#eeeeee"
BORDER_COLOR = "#6b7a8d"

def list_person_options(include_empty=False, empty_label="— 未選擇 —"):
    d = st.session_state.data
    opts = []
    if include_empty:
        opts.append((None, empty_label))
    for pid, p in d["persons"].items():
        label = f'{p["name"]}（{p["sex"]}）' + ("" if p["alive"] else "（殁）")
        opts.append((pid, label))
    return opts

def list_marriage_options(include_empty=False, empty_label="— 未選擇 —"):
    d = st.session_state.data
    opts = []
    if include_empty:
        opts.append((None, empty_label))
    for mid, m in d["marriages"].items():
        a = d["persons"].get(m["a"], {"name":"?"})["name"]
        b = d["persons"].get(m["b"], {"name":"?"})["name"]
        status = "離婚" if m["divorced"] else "在婚"
        label = f"{a} – {b}（{status}）"
        opts.append((mid, label))
    return opts

def pick_from(label, options, key):
    labels = [lab for _, lab in options]
    vals   = [val for val, _ in options]
    idx = st.selectbox(label, labels, index=0, key=key)
    sel_index = labels.index(idx)
    return vals[sel_index]

# ---------------------------------
# Build maps & generations
# ---------------------------------

def build_maps():
    d = st.session_state.data
    parents_of_child = defaultdict(set)
    marriage_children = defaultdict(list)

    for row in d["children"]:
        mid, c = row["mid"], row["child"]
        if mid not in d["marriages"]:
            continue
        a, b = d["marriages"][mid]["a"], d["marriages"][mid]["b"]
        parents_of_child[c].update([a, b])
        marriage_children[mid].append(c)
    return parents_of_child, marriage_children

def compute_generations():
    """Assign generation index. Roots (no parents) -> 0; child = max(parents)+1."""
    d = st.session_state.data
    parents_of_child, _ = build_maps()
    gens = {pid: None for pid in d["persons"]}

    # roots
    roots = [pid for pid in d["persons"] if len(parents_of_child.get(pid, set())) == 0]
    for r in roots:
        gens[r] = 0

    changed = True
    while changed:
        changed = False
        for pid in d["persons"]:
            ps = list(parents_of_child.get(pid, []))
            if not ps:
                continue
            if all(gens.get(p) is not None for p in ps):
                new_g = max(gens[p] for p in ps) + 1
                if gens[pid] is None or new_g > gens[pid]:
                    gens[pid] = new_g
                    changed = True

    # fallback
    for pid, g in gens.items():
        if g is None:
            gens[pid] = 0
    return gens

# ---------------------------------
# Drawing
# ---------------------------------

def person_node(dot, pid, p):
    label = p["name"] + ("" if p["alive"] else "（殁）")
    shape = "box" if p["sex"] == "男" else "ellipse"
    fill = COLOR_DEAD if not p["alive"] else (COLOR_MALE if p["sex"] == "男" else COLOR_FEMALE)
    dot.node(pid, label, shape=shape, style="filled", fillcolor=fill,
             color=BORDER_COLOR, fontcolor="#0b2430", penwidth="1.4")

def draw_tree_vertical():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    gens = compute_generations()
    parents_of_child, marriage_children = build_maps()

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.6", ranksep="1.0")

    # 1) Add persons
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # 2) Marriages and children
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", color=BORDER_COLOR)

        # parents horizontal connection (purely visual)
        dot.edge(a, b, dir="none", style=("dashed" if divorced else "solid"),
                 color=BORDER_COLOR, constraint="false")
        # parent -> joint: invisible but constraint=true to enforce vertical order
        dot.edge(a, jn, dir="none", style="invis", weight="30", constraint="true")
        dot.edge(b, jn, dir="none", style="invis", weight="30", constraint="true")

        # children must be below -> constraint=true
        for c in marriage_children.get(mid, []):
            dot.edge(jn, c, color=BORDER_COLOR, constraint="true")

        # keep the two parents on the same horizontal layer
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a)
            s.node(b)

    # 3) Force generation layers
    max_gen = max(gens.values()) if gens else 0
    for g in range(max_gen + 1):
        with dot.subgraph() as s:
            s.attr(rank="same")
            for pid, gg in gens.items():
                if gg == g:
                    s.node(pid)

    st.graphviz_chart(dot, use_container_width=True)

# ---------------------------------
# UI
# ---------------------------------

def start_fresh():
    st.session_state.data = _empty_data()

def page_people():
    d = st.session_state.data
    st.subheader("👤 人物")
    with st.form("add_person"):
        c1, c2 = st.columns([2,1])
        name = c1.text_input("姓名*")
        sex  = c2.radio("性別", ["男", "女"], horizontal=True, index=0)
        c3, c4 = st.columns(2)
        alive = c3.checkbox("尚在人世", value=True)
        note  = c4.text_input("備註")
        ok = st.form_submit_button("新增人物", type="primary")
        if ok:
            if name.strip():
                ensure_person(name.strip(), sex, alive, note)
                st.success(f"已新增：{name}")
                st.rerun()
            else:
                st.warning("請輸入姓名。")

    st.divider()
    p_opts = list_person_options(include_empty=True)
    p_pick = pick_from("選擇要編修的人物", p_opts, key="edit_person_pick")
    if p_pick:
        p = d["persons"][p_pick]
        with st.form("edit_person"):
            name = st.text_input("姓名", p["name"])
            sex  = st.radio("性別", ["男", "女"], index=(0 if p["sex"]=="男" else 1), horizontal=True)
            alive = st.checkbox("尚在人世", value=p["alive"])
            note = st.text_input("備註", p.get("note",""))
            c1, c2 = st.columns(2)
            ok = c1.form_submit_button("儲存")
            del_ = c2.form_submit_button("刪除此人")
            if ok:
                p.update({"name": name.strip() or p["name"], "sex": sex, "alive": alive, "note": note})
                st.success("已更新")
                st.rerun()
            if del_:
                mids_to_del = [mid for mid, m in d["marriages"].items() if p_pick in (m["a"], m["b"])]
                for mid in mids_to_del:
                    d["children"] = [row for row in d["children"] if row["mid"] != mid]
                    del d["marriages"][mid]
                d["children"] = [row for row in d["children"] if row["child"] != p_pick]
                del d["persons"][p_pick]
                st.success("已刪除")
                st.rerun()

def page_relations():
    d = st.session_state.data
    st.subheader("🔗 關係")
    st.markdown("### 建立或更新婚姻")
    with st.form("form_marriage"):
        c1, c2 = st.columns(2)
        a = pick_from("配偶 A", list_person_options(include_empty=True), key="m_a")
        b = pick_from("配偶 B", list_person_options(include_empty=True), key="m_b")
        divorced = st.checkbox("此段婚姻已離婚（線條改為虛線）", value=False)
        ok = st.form_submit_button("建立／更新婚姻", type="primary")
        if ok:
            if not a or not b:
                st.warning("請選擇雙方。")
            elif a == b:
                st.warning("兩個欄位不可為同一人。")
            else:
                add_marriage(a, b, divorced)
                st.success("婚姻已建立/更新")
                st.rerun()

    st.divider()
    st.markdown("### 把子女掛到父母（選擇婚姻）")
    m = pick_from("選擇父母（某段婚姻）", list_marriage_options(include_empty=True), key="kid_mid")
    with st.form("form_child"):
        kid = pick_from("子女", list_person_options(include_empty=True), key="kid_pid")
        ok = st.form_submit_button("掛上子女")
        if ok:
            if not m:
                st.warning("請先選擇婚姻。")
            elif not kid:
                st.warning("請選擇子女。")
            else:
                add_child(m, kid)
                st.success("子女已掛上")
                st.rerun()

def page_tree():
    st.subheader("🧬 家族樹（上下排列）")
    draw_tree_vertical()

# ---------------------------------
# Main
# ---------------------------------

st.set_page_config(page_title="家族平台（上下排列）", layout="wide")
ensure_session()

st.title("🌳 家族平台（人物｜關係｜家族樹）")

c1, c2 = st.columns([1,1])
with c1:
    if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
        load_demo(clear=True)
        st.success("已載入示範資料。")
        st.rerun()
with c2:
    with st.popover("🧹 開始輸入我的資料（清空）", use_container_width=True):
        st.warning("此動作會刪除目前所有資料，且無法復原。")
        agree = st.checkbox("我了解並同意清空")
        if st.button("確認清空", type="primary", disabled=not agree):
            st.session_state.data = _empty_data()
            st.success("資料已清空。")
            st.rerun()

st.markdown(
    """
    <style>
    .st-emotion-cache-1r6slb0 {max-width: 1400px;}
    </style>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["人物", "關係", "家族樹"])
with tab1:
    page_people()
with tab2:
    page_relations()
with tab3:
    page_tree()

import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

# -------------------------------
# Session & Data
# -------------------------------

def _empty_data():
    return {
        "persons": {},          # pid -> {name, sex('男'/'女'), alive(True/False), note}
        "marriages": {},        # mid -> {a, b, divorced(bool)}
        "children": [],         # list of {mid, child}
        "sibling_links": [],    # list of (pid1, pid2)  (無序對；用排序後的tuple去重)
        "_seq": 0,              # for id generation
    }

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def next_id():
    st.session_state.data["_seq"] += 1
    return str(st.session_state.data["_seq"])

# -------------------------------
# Demo Data
# -------------------------------

def ensure_person(name, sex="男", alive=True, note=""):
    """Find or create person by name; return pid."""
    d = st.session_state.data
    for pid, p in d["persons"].items():
        if p["name"] == name:
            return pid
    pid = next_id()
    d["persons"][pid] = {"name": name, "sex": sex, "alive": alive, "note": note}
    return pid

def add_marriage(a, b, divorced=False):
    """Return mid if created; if same pair exists, return that mid."""
    d = st.session_state.data
    # check exists
    for mid, m in d["marriages"].items():
        if {m["a"], m["b"]} == {a, b}:
            # update divorced flag if different
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

def add_sibling_link(a, b):
    if not a or not b:
        return
    a, b = sorted([a, b])
    d = st.session_state.data
    if (a, b) not in d["sibling_links"]:
        d["sibling_links"].append((a, b))

def load_demo(clear=True):
    if clear:
        st.session_state.data = _empty_data()
    # 人物
    yilang = ensure_person("陳一郎", "男", True)
    exwife = ensure_person("陳前妻", "女", True)
    wife   = ensure_person("陳妻",   "女", True)
    wangzi = ensure_person("王子",   "男", True)
    wz_wife= ensure_person("王子妻", "女", True)
    chenda = ensure_person("陳大",   "男", True)
    chener = ensure_person("陳二",   "男", True)
    chensan= ensure_person("陳三",   "男", True)
    w_sun  = ensure_person("王孫",   "男", True)

    # 婚姻：現任（陳一郎×陳妻）、前任（陳一郎×陳前妻）
    mid_now = add_marriage(yilang, wife,   divorced=False)
    mid_ex  = add_marriage(yilang, exwife, divorced=True)

    # 子女
    add_child(mid_now, chenda)
    add_child(mid_now, chener)
    add_child(mid_now, chensan)
    add_child(mid_ex,  wangzi)

    # 王子成家
    mid_wang = add_marriage(wangzi, wz_wife, divorced=False)
    add_child(mid_wang, w_sun)

# -------------------------------
# UI Helpers
# -------------------------------

COLOR_MALE   = "#dff2ff"
COLOR_FEMALE = "#ffe9f2"
COLOR_DEAD   = "#eeeeee"
BORDER_COLOR = "#6b7a8d"

def list_person_options(include_empty=False, empty_label="— 未選擇 —"):
    d = st.session_state.data
    opts = []
    if include_empty:
        opts.append((None, empty_label))
    # 保持插入順序（較直覺）
    for pid, p in d["persons"].items():
        label = f'{p["name"]}（{p["sex"]}）'
        if not p["alive"]:
            label += "（殁）"
        opts.append((pid, label))
    # sort by label Chinese-friendly (keep as-insert order usually ok)
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
    """ options: list[(value, label)] ; returns value """
    labels = [lab for _, lab in options]
    vals   = [val for val, _ in options]
    idx = st.selectbox(label, labels, index=0, key=key)
    # find index
    sel_index = labels.index(idx)
    return vals[sel_index]

# -------------------------------
# Inheritance (Civil Code 1138)
# -------------------------------

def build_child_map():
    """mid -> (father, mother), parent_map[child] = {parents} ; and direct children per parent"""
    d = st.session_state.data
    mid_parents = {}
    children_by_parent = defaultdict(list)
    parent_set = defaultdict(set)

    for mid, m in d["marriages"].items():
        a, b = m["a"], m["b"]
        mid_parents[mid] = (a, b)
    for row in d["children"]:
        mid, c = row["mid"], row["child"]
        if mid in mid_parents:
            a, b = mid_parents[mid]
            children_by_parent[a].append(c)
            children_by_parent[b].append(c)
            parent_set[c].update([a, b])
    return children_by_parent, parent_set

def descendants_of(pid):
    """Return all living descendants list (with representation for lineal only)."""
    d = st.session_state.data
    children_by_parent, _ = build_child_map()

    out = []
    dq = deque(children_by_parent.get(pid, []))
    while dq:
        x = dq.popleft()
        out.append(x)
        for y in children_by_parent.get(x, []):
            dq.append(y)
    return out

def parents_of(pid):
    _, parent_map = build_child_map()
    return list(parent_map.get(pid, set()))

def siblings_of(pid):
    # 同父母
    _, parent_map = build_child_map()
    pset = parent_map.get(pid, set())
    sibs = set()
    if pset:
        for x, p in parent_map.items():
            if x != pid and p == pset:
                sibs.add(x)
    # 額外手動連的兄弟姊妹（不一定同父母）
    d = st.session_state.data
    for a, b in d["sibling_links"]:
        if a == pid:
            sibs.add(b)
        elif b == pid:
            sibs.add(a)
    return list(sibs)

def grandparents_of(pid):
    gps = set()
    for p in parents_of(pid):
        gps.update(parents_of(p))
    return list(gps)

def find_spouses(pid):
    d = st.session_state.data
    res = []
    for mid, m in d["marriages"].items():
        if m["a"] == pid:
            res.append((mid, m["b"], m["divorced"]))
        elif m["b"] == pid:
            res.append((mid, m["a"], m["divorced"]))
    return res

def heirs_1138(decedent):
    """Return dict with groups and textual explanation."""
    d = st.session_state.data
    out = {"spouse": [], "rank": 0, "heirs": []}

    # 配偶永遠參與分配
    spouses = [sp for _, sp, _ in find_spouses(decedent)]
    out["spouse"] = spouses

    # 第一順位：直系卑親屬（含代位）
    rank1 = [x for x in lineal_heirs_with_representation(decedent) if d["persons"][x]["alive"]]
    if rank1:
        out["rank"] = 1
        out["heirs"] = rank1
        return out

    # 第二順位：父母
    rank2 = [x for x in parents_of(decedent) if d["persons"][x]["alive"]]
    if rank2:
        out["rank"] = 2
        out["heirs"] = rank2
        return out

    # 第三順位：兄弟姊妹
    rank3 = [x for x in siblings_of(decedent) if d["persons"][x]["alive"]]
    if rank3:
        out["rank"] = 3
        out["heirs"] = rank3
        return out

    # 第四順位：祖父母
    rank4 = [x for x in grandparents_of(decedent) if d["persons"][x]["alive"]]
    if rank4:
        out["rank"] = 4
        out["heirs"] = rank4
        return out

    # 否則：國庫（不在此示範）
    return out

def lineal_heirs_with_representation(decedent):
    """一代代往下，若子女死亡，以其直系卑親屬代位"""
    d = st.session_state.data
    children_by_parent, _ = build_child_map()

    def alive(pid):
        return d["persons"][pid]["alive"]

    # 先看直系第一層子女中，活著的
    first_gen = children_by_parent.get(decedent, [])
    alive_children = [x for x in first_gen if alive(x)]
    if alive_children:
        return alive_children

    # 若子女全亡或不存在，找代位
    heirs = []
    for c in first_gen:
        # c 亡 -> 由 c 的子女代位
        if not alive(c):
            heirs.extend([x for x in children_by_parent.get(c, []) if alive(x)])
    return heirs

# -------------------------------
# Drawing (Graphviz)
# -------------------------------

def person_node(dot, pid, p):
    label = p["name"]
    if not p["alive"]:
        label += "（殁）"

    shape = "box" if p["sex"] == "男" else "ellipse"
    fill = COLOR_DEAD if not p["alive"] else (COLOR_MALE if p["sex"] == "男" else COLOR_FEMALE)

    dot.node(pid, label, shape=shape, style="filled", fillcolor=fill,
             color=BORDER_COLOR, fontcolor="#0b2430", penwidth="1.4")

def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")

    # 節點
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # 夫妻（婚姻節點）+ 子女
    # —— 唯一改動：夫妻之間畫「水平橫線」（現任實線、前任虛線），其餘位置不變 ——
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", color=BORDER_COLOR)

        style = "dashed" if divorced else "solid"

        # 夫妻水平線（不改變原本佈局）；孩子仍從中點 jn 往下
        dot.edge(a, b, dir="none", style=style, color=BORDER_COLOR, constraint="false")

        # 用隱形邊讓 jn 停在兩人之間，維持既有版面
        dot.edge(a, jn, dir="none", style="invis", weight="50")
        dot.edge(b, jn, dir="none", style="invis", weight="50")

        # 讓夫妻併排
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a)
            s.node(b)

        # 小孩垂直往下
        kids = [row["child"] for row in d["children"] if row["mid"] == mid]
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(jn, c, color=BORDER_COLOR)

    # 兄弟姊妹(無共同父母時)用虛線相連，並強制 rank=same
    # 收集已有共同父母的兄弟姊妹，避免重複畫
    _, parent_map = build_child_map()
    def has_same_parents(x, y):
        return parent_map.get(x, set()) and parent_map.get(x, set()) == parent_map.get(y, set())

    for a, b in d["sibling_links"]:
        if has_same_parents(a, b):
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a)
            s.node(b)
        dot.edge(a, b, style="dashed", color=BORDER_COLOR, dir="none")

    st.graphviz_chart(dot, use_container_width=True)

# -------------------------------
# UI
# -------------------------------

def start_fresh():
    st.session_state.data = _empty_data()

def page_people():
    d = st.session_state.data
    st.subheader("👤 人物")
    st.caption("先建立人物，再到「關係」掛上婚姻與子女。")

    # 新增人物
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

    # 編修人物
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
                # 同步刪除關係
                # 刪婚姻
                mids_to_del = [mid for mid, m in d["marriages"].items() if p_pick in (m["a"], m["b"])]
                for mid in mids_to_del:
                    # 刪除底下子女關係
                    d["children"] = [row for row in d["children"] if row["mid"] != mid]
                    del d["marriages"][mid]
                # 刪小孩掛載
                d["children"] = [row for row in d["children"] if row["child"] != p_pick]
                # 刪手動兄弟姊妹
                d["sibling_links"] = [(a,b) for (a,b) in d["sibling_links"] if a != p_pick and b != p_pick]
                # 刪本人
                del d["persons"][p_pick]
                st.success("已刪除")
                st.rerun()

def page_relations():
    d = st.session_state.data
    st.subheader("🔗 關係")
    st.caption("先建立婚姻，再把子女掛到某段婚姻（父母）下。若無血緣但想並列視覺，可用兄弟姊妹虛線連結。")

    # -- 建立婚姻
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

    # -- 把子女掛到父母（某段婚姻）
    st.markdown("### 把子女掛到父母（某段婚姻）")
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

    st.divider()

    # -- 兄弟姊妹
    st.markdown("### 掛上兄弟姊妹（沒有血緣連線也可）")
    with st.form("form_siblings"):
        a = pick_from("成員 A", list_person_options(include_empty=True), key="sib_a")
        b = pick_from("成員 B", list_person_options(include_empty=True), key="sib_b")
        ok = st.form_submit_button("以虛線連結（同列顯示）")
        if ok:
            if not a or not b:
                st.warning("請選擇兩位。")
            elif a == b:
                st.warning("同一人不可相連。")
            else:
                add_sibling_link(a, b)
                st.success("已以虛線相連並同列顯示")
                st.rerun()

def page_inheritance():
    d = st.session_state.data
    st.subheader("⚖️ 法定繼承試算（民法 1138）")

    if not d["persons"]:
        st.info("請先新增人物。")
        return

    target = pick_from("選擇被繼承人", list_person_options(include_empty=False), key="decedent")
    info = heirs_1138(target)

    person_name = lambda pid: d["persons"][pid]["name"]
    spouse_names = "、".join([person_name(x) for x in info["spouse"]]) if info["spouse"] else "（無）"
    heirs_names  = "、".join([person_name(x) for x in info["heirs"]]) if info["heirs"] else "（無）"

    st.write(f"**配偶參與分配**：{spouse_names}")
    st.write(f"**順位**：{info['rank'] if info['rank'] else '（無）'}")
    st.write(f"**同順位繼承人**：{heirs_names}")

# UI: Tree
# -------------------------------

def page_tree():
    st.subheader("🧬 家族樹")
    draw_tree()

# -------------------------------
# Main Layout
# -------------------------------

st.set_page_config(page_title="家族平台", layout="wide")
ensure_session()

st.title("🌳 家族平台（人物｜關係｜法定繼承｜家族樹）")

c1, c2 = st.columns([1,1])
with c1:
    if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
        load_demo(clear=True)
        st.success("已載入示範資料。")
        st.rerun()
with c2:
    # 有二次確認的清空
    with st.popover("🧹 開始輸入我的資料（清空）", use_container_width=True):
        st.warning("此動作會刪除目前所有資料（人物、婚姻、子女、兄弟姊妹），且無法復原。")
        agree = st.checkbox("我了解並同意清空")
        if st.button("確認清空", type="primary", disabled=not agree):
            start_fresh()
            st.success("資料已清空，請到「人物」分頁新增第一位成員。")
            st.rerun()

st.markdown(
    """
    <style>
    .st-emotion-cache-1r6slb0 {max-width: 1400px;}
    </style>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(["人物", "關係", "法定繼承試算", "家族樹"])

with tab1:
    page_people()
with tab2:
    page_relations()
with tab3:
    page_inheritance()
with tab4:
    page_tree()

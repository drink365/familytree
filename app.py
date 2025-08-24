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
    if a == b:
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

    # 王子家庭
    mid_wz = add_marriage(wangzi, wz_wife, divorced=False)
    add_child(mid_wz, w_sun)

# -------------------------------
# Helpers (UI & common)
# -------------------------------

def start_fresh():
    st.session_state.data = _empty_data()

def list_person_options(include_empty=False, empty_label="— 未選擇 —"):
    d = st.session_state.data
    opts = []
    if include_empty:
        opts.append((None, empty_label))
    for pid, p in d["persons"].items():
        label = f'{p["name"]}（{p["sex"]}）'
        if not p["alive"]:
            label += "（殁）"
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

# -------------------------------
# Inheritance (Civil Code 1138)
# -------------------------------

def build_child_map():
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
    d = st.session_state.data
    children_by_parent, _ = build_child_map()
    res = []
    q = deque(children_by_parent.get(pid, []))
    while q:
        c = q.popleft()
        res.append(c)
        q.extend(children_by_parent.get(c, []))
    return res

def lineal_heirs_with_representation(decedent):
    d = st.session_state.data
    children_by_parent, _ = build_child_map()

    def collect_lineal(children_list):
        line = []
        for c in children_list:
            person = d["persons"].get(c)
            if not person:
                continue
            if person["alive"]:
                line.append(c)
            else:
                line.extend(collect_lineal(children_by_parent.get(c, [])))
        return line

    children = children_by_parent.get(decedent, [])
    heirs = collect_lineal(children)
    return list(dict.fromkeys(heirs))

def parents_of(pid):
    d = st.session_state.data
    _, parent_set = build_child_map()
    return list(parent_set.get(pid, []))

def siblings_of(pid):
    d = st.session_state.data
    _, parent_map = build_child_map()
    sibs = set()
    my_parents = set(parent_map.get(pid, []))
    for cid, parents in parent_map.items():
        if cid == pid:
            continue
        if set(parents) == my_parents and parents:
            sibs.add(cid)
    for a, b in d["sibling_links"]:
        if a == pid:
            sibs.add(b)
        if b == pid:
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
    d = st.session_state.data
    out = {"spouse": [], "rank": 0, "heirs": []}
    spouses = [sp for _, sp, _ in find_spouses(decedent)]
    out["spouse"] = spouses

    rank1 = [x for x in lineal_heirs_with_representation(decedent) if d["persons"][x]["alive"]]
    if rank1:
        out["rank"] = 1
        out["heirs"] = rank1
        return out

    rank2 = [p for p in parents_of(decedent) if d["persons"][p]["alive"]]
    if rank2:
        out["rank"] = 2
        out["heirs"] = rank2
        return out

    rank3 = [s for s in siblings_of(decedent) if d["persons"][s]["alive"]]
    if rank3:
        out["rank"] = 3
        out["heirs"] = rank3
        return out

    rank4 = [g for g in grandparents_of(decedent) if d["persons"][g]["alive"]]
    if rank4:
        out["rank"] = 4
        out["heirs"] = rank4
        return out

    out["rank"] = 0
    out["heirs"] = []
    return out

# -------------------------------
# Graphviz Family Tree
# -------------------------------

COLOR_MALE   = "#d8eaff"
COLOR_FEMALE = "#ffdbe1"
COLOR_DEAD   = "#e6e6e6"
BORDER_COLOR = "#164b5f"

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
    # 可見的夫妻水平線使用 constraint=false，不影響佈局；
    # 佈局仍由 A->jn、B->jn 兩條「隱形」邊決定；有子女時從 jn 垂直往下。
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        jn = f"J_{mid}"
        dot.node(jn, "", shape="point", width="0.02", style="invis")
        style = "dashed" if divorced else "solid"

        # 1) 可見的夫妻水平線（純視覺，不影響佈局）
        dot.edge(a, b, dir="none", style=style, color=BORDER_COLOR, constraint="false")

        # 2) 隱形邊固定中點位置並維持原本佈局
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)
        dot.edge(a, jn, dir="none", style="invis")
        dot.edge(b, jn, dir="none", style="invis")

        # 3) 子女：從中點 jn 垂直往下連
        kids = [row["child"] for row in d["children"] if row["mid"] == mid]
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(jn, c, color=BORDER_COLOR)

    # 兄弟姊妹（無共同父母時）用虛線相連
    _, parent_map = build_child_map()
    def has_same_parents(x, y):
        return parent_map.get(x, set()) and parent_map.get(x, set()) == parent_map.get(y, set())

    for a, b in d["sibling_links"]:
        if has_same_parents(a, b):
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)
        dot.edge(a, b, style="dashed", color=BORDER_COLOR, dir="none")

    st.graphviz_chart(dot, use_container_width=True)

# -------------------------------
# UI: People
# -------------------------------

def page_people():
    d = st.session_state.data

    st.subheader("👤 人物")
    st.caption("先新增人物，再到「關係」分頁建立婚姻與子女。")

    with st.form("add_person"):
        st.markdown("**新增人物**")
        name = st.text_input("姓名", "")
        sex  = st.radio("性別", ["男", "女"], horizontal=True, index=0)
        alive = st.checkbox("尚在人世", value=True)
        note = st.text_input("備註", "")
        ok = st.form_submit_button("新增")
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
                    d["marriages"].pop(mid, None)
                d["children"] = [row for row in d["children"] if row["child"] != p_pick]
                d["sibling_links"] = [t for t in d["sibling_links"] if p_pick not in t]
                d["persons"].pop(p_pick, None)
                st.success("已刪除")
                st.rerun()

# -------------------------------
# UI: Relations
# -------------------------------

def page_relations():
    d = st.session_state.data

    st.subheader("🔗 關係")

    st.markdown("### 建立婚姻（現任 / 離婚）")
    with st.form("form_marriage"):
        colA, colB, colC = st.columns([2,2,1])
        with colA:
            a = pick_from("配偶 A", list_person_options(include_empty=True), key="marry_a")
        with colB:
            b = pick_from("配偶 B", list_person_options(include_empty=True), key="marry_b")
        with colC:
            divorced = st.checkbox("此婚姻為離婚/前配偶", value=False)
        ok = st.form_submit_button("建立婚姻")
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

    st.markdown("### 掛上兄弟姊妹（沒有血緣連線也可）")
    with st.form("form_sibling"):
        base = pick_from("基準成員", list_person_options(include_empty=True), key="sib_base")
        sib  = pick_from("要掛為其兄弟姊妹者", list_person_options(include_empty=True), key="sib_other")
        ok = st.form_submit_button("建立兄弟姊妹關係")
        if ok:
            if not base or not sib:
                st.warning("請選擇兩個人。")
            elif base == sib:
                st.warning("同一個人無法建立兄弟姊妹關係。")
            else:
                add_sibling_link(base, sib)
                st.success("已建立兄弟姊妹關係")
                st.rerun()

# -------------------------------
# UI: Inheritance
# -------------------------------

def page_inheritance():
    d = st.session_state.data

    st.subheader("⚖️ 法定繼承試算")
    if not d["persons"]:
        st.info("尚無資料，請先新增人物或載入示範。")
        return

    target = pick_from("選擇被繼承人", list_person_options(include_empty=True), key="succ_target")
    if not target:
        st.info("請選擇被繼承人。")
        return

    result = heirs_1138(target)
    if result["rank"] == 0 and not result["spouse"]:
        st.info("查無可繼承人（四順位皆無、且無配偶）。")
        return

    def show_names(ids):
        return "、".join([d["persons"][i]["name"] for i in ids]) if ids else "（無）"

    st.markdown("---")
    st.markdown(f"**被繼承人**：{d['persons'][target]['name']}")
    st.markdown(f"**配偶**（當然繼承人）：{show_names(result['spouse'])}")
    rank_txt = {1:"第一順位（直系卑親屬，含代位）", 2:"第二順位（父母）", 3:"第三順位（兄弟姊妹）", 4:"第四順位（祖父母）", 0:"（無）"}
    st.markdown(f"**適用順位**：{rank_txt[result['rank']]}")
    st.markdown(f"**本順位繼承人**：{show_names(result['heirs'])}")
    st.caption("說明：依民法第1138條，配偶為當然繼承人；先檢視第一順位（直系卑親屬），無者再依序檢視第二至第四順位。代位繼承僅適用於直系卑親屬。")

# -------------------------------
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
    with st.popover("🧹 開始輸入我的資料（清空）", use_container_width=True):
        st.warning("此動作會刪除目前所有資料（人物、婚姻、子女、兄弟姊妹），且無法復原。")
        agree = st.checkbox("我了解並同意清空")
        if st.button("確認清空", type="primary", disabled=not agree):
            start_fresh()
            st.success("資料已清空，請到「人物」分頁新增第一位成員。")
            st.rerun()

st.markdown("本圖以 **陳一郎家族譜** 為示範。")
st.markdown(
    """
    <div style="margin:.4rem 0 1.2rem 0;">
      <a href="#人物" style="margin-right:12px;">➡️ 先到「人物」新增家人</a>
      <a href="#關係">➡️ 再到「關係」建立婚姻、子女與兄弟姊妹</a>
    </div>
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

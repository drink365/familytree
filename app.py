# -*- coding: utf-8 -*-
import streamlit as st
from graphviz import Digraph
from collections import defaultdict

st.set_page_config(page_title="Family Tree", page_icon="🌳", layout="wide")

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
    erA    = ensure_person("二孩A",  "女", True)
    erB    = ensure_person("二孩B",  "男", True)
    erC    = ensure_person("二孩C",  "女", True)
    sanA   = ensure_person("三孩A",  "男", True)
    sanB   = ensure_person("三孩B",  "女", True)

    # 婚姻
    m1 = add_marriage(yilang, exwife, divorced=True)
    m2 = add_marriage(yilang, wife, divorced=False)
    m3 = add_marriage(wangzi, wz_wife, divorced=False)
    m4 = add_marriage(chenda, ensure_person("陳大嫂", "女", True), False)
    m5 = add_marriage(chener, ensure_person("陳二嫂", "女", True), False)
    m6 = add_marriage(chensan, ensure_person("陳三嫂", "女", True), False)

    # 子女
    add_child(m1, wangzi)
    add_child(m2, chenda)
    add_child(m2, chener)
    add_child(m2, chensan)
    add_child(m3, w_sun)
    add_child(m5, erA)
    add_child(m5, erB)
    add_child(m5, erC)
    add_child(m6, sanA)
    add_child(m6, sanB)

# -------------------------------
# Helpers for kinship
# -------------------------------
def build_child_map():
    """Return (children_by_parent, parents_of_child)."""
    d = st.session_state.data
    children_by_parent = defaultdict(list)
    parents_of_child = defaultdict(list)
    # marriage mid -> (a,b)
    pairs = {mid: (m["a"], m["b"]) for mid, m in d["marriages"].items()}
    for row in d["children"]:
        mid, c = row["mid"], row["child"]
        if mid not in pairs:
            continue
        a, b = pairs[mid]
        if a:
            children_by_parent[a].append(c)
            parents_of_child[c].append(a)
        if b:
            children_by_parent[b].append(c)
            parents_of_child[c].append(b)
    return children_by_parent, parents_of_child

def lineal_heirs_with_representation(decedent):
    """直系卑親屬（含代位）"""
    d = st.session_state.data
    children_by_parent, _ = build_child_map()

    heirs = []

    # 子女活的直接入列；死亡者由其直系卑親屬代位（遞迴）
    def collect_lineal(children_list):
        line = []
        for c in children_list:
            person = d["persons"].get(c)
            if not person:
                continue
            if person["alive"]:
                line.append(c)
            else:
                cc = children_by_parent.get(c, [])
                line.extend(collect_lineal(cc))
        return line

    children = children_by_parent.get(decedent, [])
    heirs = collect_lineal(children)
    return list(dict.fromkeys(heirs))  # unique & keep order

def parents_of(pid):
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
    # 手動兄弟姊妹連結
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
    """民法1138順位（簡化）：配偶 + 直系卑親屬 / 父母 / 兄弟姊妹 / 祖父母"""
    d = st.session_state.data
    out = {"spouse": [], "rank": 0, "heirs": []}

    # 配偶
    spouses = [sp for _, sp, _ in find_spouses(decedent)]
    out["spouse"] = spouses

    # 第一順位：直系卑親屬（含代位）
    rank1 = [x for x in lineal_heirs_with_representation(decedent) if d["persons"][x]["alive"]]
    if rank1:
        out["rank"] = 1
        out["heirs"] = rank1
        return out

    # 第二順位：父母
    rank2 = [p for p in parents_of(decedent) if d["persons"][p]["alive"]]
    if rank2:
        out["rank"] = 2
        out["heirs"] = rank2
        return out

    # 第三順位：兄弟姊妹（無代位）
    rank3 = [s for s in siblings_of(decedent) if d["persons"][s]["alive"]]
    if rank3:
        out["rank"] = 3
        out["heirs"] = rank3
        return out

    # 第四順位：祖父母
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
        st.info("請先新增人物與關係，或點右上角「載入示範」。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")

    # 節點
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # 婚線(夫妻水平) + 離婚虛線
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        style = "dashed" if divorced else "solid"
        dot.edge(a, b, dir="none", color=BORDER_COLOR, penwidth="1.2", style=style)

    # 親子（婚點作為隱形中繼，避免錯連）
    # 對每段婚姻建一個隱擬node，把父母→婚點、婚點→子女，讓線條乾淨
    for mid, m in d["marriages"].items():
        hub = f"hub_{mid}"
        dot.node(hub, label="", shape="point", width="0.01", height="0.01")
        dot.edge(m["a"], hub, dir="none", color=BORDER_COLOR, penwidth="1.0")
        dot.edge(m["b"], hub, dir="none", color=BORDER_COLOR, penwidth="1.0")
        for row in d["children"]:
            if row["mid"] == mid:
                dot.edge(hub, row["child"], dir="none", color=BORDER_COLOR, penwidth="1.0")

    st.graphviz_chart(dot)

# -------------------------------
# UI Components
# -------------------------------
def list_person_options(include_empty=False):
    d = st.session_state.data
    opts = []
    if include_empty:
        opts.append(("", "（未選擇）"))
    for pid, p in d["persons"].items():
        tag = "" if p["alive"] else "（殁）"
        opts.append((pid, f'{p["name"]}{tag} / {p["sex"]}'))
    return opts

def pick_from(label, options, key=None):
    show = [o[1] for o in options]
    idx = st.selectbox(label, range(len(show)), format_func=lambda i: show[i], key=key)
    return options[idx][0]

def page_data():
    d = st.session_state.data
    st.subheader("🧑 人物")
    with st.form("form_add_person"):
        c1, c2, c3 = st.columns([2,1,1])
        with c1:
            name = st.text_input("姓名")
        with c2:
            sex = st.selectbox("性別", ["男", "女"])
        with c3:
            alive = st.selectbox("狀態", ["在世", "已故"])
        ok = st.form_submit_button("新增人物")
        if ok:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = next_id()
                d["persons"][pid] = {"name": name.strip(), "sex": sex, "alive": (alive=="在世"), "note": ""}
                st.success("已新增")
                st.rerun()

    st.divider()
    st.subheader("✏️ 編輯人物")
    if not d["persons"]:
        st.info("目前尚無人物。")
        return
    p_pick = pick_from("選擇人物", list_person_options(), key="edit_person_pick")
    if p_pick:
        p = d["persons"][p_pick]
        with st.form("form_edit_person"):
            c1, c2, c3 = st.columns([2,1,1])
            with c1:
                name = st.text_input("姓名", p["name"])
            with c2:
                sex = st.selectbox("性別", ["男", "女"], index=0 if p["sex"]=="男" else 1)
            with c3:
                alive = st.checkbox("在世", value=p["alive"])
            note = st.text_input("備註", p.get("note",""))
            c1b, c2b = st.columns(2)
            ok = c1b.form_submit_button("儲存")
            del_ = c2b.form_submit_button("刪除此人")
            if ok:
                p.update({"name": name.strip() or p["name"], "sex": sex, "alive": alive, "note": note})
                st.success("已更新")
                st.rerun()
            if del_:
                # 同步刪除關係
                mids_to_del = [mid for mid, m in d["marriages"].items() if p_pick in (m["a"], m["b"])]
                for mid in mids_to_del:
                    d["children"] = [row for row in d["children"] if row["mid"] != mid]
                    d["marriages"].pop(mid, None)
                d["children"] = [row for row in d["children"] if row["child"] != p_pick]
                d["sibling_links"] = [t for t in d["sibling_links"] if p_pick not in t]
                d["persons"].pop(p_pick, None)
                st.success("已刪除")
                st.rerun()

def page_relations():
    d = st.session_state.data
    st.subheader("🔗 關係")

    # 建立婚姻
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
    st.markdown("### 新增子女")
    if not d["marriages"]:
        st.info("請先建立至少一段婚姻。")
    else:
        with st.form("form_child"):
            mids = list(d["marriages"].keys())
            mid = st.selectbox("選擇婚姻", mids, format_func=lambda m: f'{d["persons"][d["marriages"][m]["a"]]["name"]} ↔ {d["persons"][d["marriages"][m]["b"]]["name"]} {"(離)" if d["marriages"][m]["divorced"] else ""}')
            child = pick_from("選擇/新增子女", [("", "（請到「人物」頁面新增子女人物）」")] + list_person_options(), key="pick_child_for_mid")
            ok = st.form_submit_button("加入子女")
            if ok:
                if not mid or not child:
                    st.warning("請選擇婚姻與子女。")
                else:
                    add_child(mid, child)
                    st.success("已加入子女")
                    st.rerun()

def page_tree():
    st.subheader("🌳 家族樹")
    draw_tree()

def page_tools():
    d = st.session_state.data
    st.subheader("⚖️ 法規小工具（示意）")
    if not d["persons"]:
        st.info("請先新增人物或載入示範。")
        return
    decedent = pick_from("選擇被繼承人", list_person_options(), key="heir_dec")
    if st.button("計算法定繼承順位"):
        res = heirs_1138(decedent)
        rank_map = {0:"無",1:"直系卑親屬",2:"父母",3:"兄弟姊妹",4:"祖父母"}
        st.write("配偶：", "、".join(d["persons"][x]["name"] for x in res["spouse"]) or "（無）")
        st.write("順位：", rank_map.get(res["rank"], ""))
        st.write("同順位繼承人：", "、".join(d["persons"][x]["name"] for x in res["heirs"]) or "（無）")

# -------------------------------
# Main
# -------------------------------
def main():
    ensure_session()

    # 頂部工具列
    top_left, top_right = st.columns([1,1])
    with top_left:
        st.markdown("### 🌳 Family Tree")
    with top_right:
        c1, c2 = st.columns(2)
        if c1.button("載入示範", use_container_width=True):
            load_demo(clear=True)
            st.success("已載入示範")
            st.rerun()
        if c2.button("清空資料", use_container_width=True):
            st.session_state.data = _empty_data()
            st.success("已清空")
            st.rerun()

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["人物", "關係", "家族樹", "工具"])
    with tab1:
        page_data()
    with tab2:
        page_relations()
    with tab3:
        page_tree()
    with tab4:
        page_tools()

if __name__ == "__main__":
    main()

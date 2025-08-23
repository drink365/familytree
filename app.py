
import json
from collections import defaultdict, deque
import streamlit as st

st.set_page_config(page_title="家庭樹（三代分層）", page_icon="🌳", layout="wide")

# =========================
# 初始化資料（可用「載入示範」填入）
# =========================
if "db" not in st.session_state:
    st.session_state.db = {"persons": {}, "marriages": [], "children": []}
if "anchor" not in st.session_state:
    st.session_state.anchor = ""

def load_demo():
    st.session_state.db = {
        "persons": {
            "p_self":   {"name": "陳一郎", "birth": 1968},
            "p_ex":     {"name": "陳前妻", "birth": 1969},
            "p_cur":    {"name": "陳妻",   "birth": 1972},
            "p_wangzi":     {"name": "王子",   "birth": 1989},
            "p_wangzi_sp":  {"name": "王子妻", "birth": 1990},
            "p_wangsun":    {"name": "王孫",   "birth": 2018},
            "p_d1": {"name": "陳大", "birth": 1994},
            "p_d2": {"name": "陳二", "birth": 1996},
            "p_d3": {"name": "陳三", "birth": 1999},
        },
        "marriages": [
            {"a": "p_self", "b": "p_ex", "status": "divorced"},
            {"a": "p_self", "b": "p_cur", "status": "married"},
            {"a": "p_wangzi", "b": "p_wangzi_sp", "status": "married"},
        ],
        "children": [
            {"parents": ["p_self", "p_cur"], "child": "p_d1"},
            {"parents": ["p_self", "p_cur"], "child": "p_d2"},
            {"parents": ["p_self", "p_cur"], "child": "p_d3"},
            {"parents": ["p_wangzi", "p_wangzi_sp"], "child": "p_wangsun"},
            {"parents": ["p_ex"], "child": "p_wangzi"},
        ],
    }
    st.session_state.anchor = "p_self"

def clear_all():
    st.session_state.db = {"persons": {}, "marriages": [], "children": []}
    st.session_state.anchor = ""

db = st.session_state.db

# =========================
# 輔助：正規化與世代推導（確保三層）
# =========================
def normalize_marriages(m_list):
    out = []
    for m in m_list:
        a, b = m["a"], m["b"]
        if a > b:
            a, b = b, a
        out.append((a, b, m.get("status", "married")))
    return out

def normalize_children(c_list):
    out = []
    for c in c_list:
        ps = list(c.get("parents", []))
        if len(ps) == 2 and ps[0] > ps[1]:
            ps[0], ps[1] = ps[1], ps[0]
        out.append((tuple(ps), c["child"]))
    return out

def compute_generations(db, anchor_id=""):
    persons = db.get("persons", {})
    marriages = normalize_marriages(db.get("marriages", []))
    children = normalize_children(db.get("children", []))

    spouse_edges = set()
    for a,b,stt in marriages:
        spouse_edges.add((a,b))
        spouse_edges.add((b,a))

    parent_of = defaultdict(list)
    child_of = defaultdict(list)
    for parents, child in children:
        for p in parents:
            parent_of[p].append(child)
        child_of[child] = list(parents)

    gens = {}
    # 以 anchor 為第 0 代（若未選擇，嘗試用「有小孩的父母」做為 0 代）
    if anchor_id and anchor_id in persons:
        gens[anchor_id] = 0
    else:
        # 找出任何有子女的父母作為 0 代
        found = False
        for parents, child in children:
            for p in parents:
                gens[p] = 0
                found = True
            if found:
                break

    # 迭代推導：
    changed = True
    while changed:
        changed = False
        # 配偶同代
        for a,b,_ in marriages:
            if a in gens and b not in gens:
                gens[b] = gens[a]; changed = True
            if b in gens and a not in gens:
                gens[a] = gens[b]; changed = True

        # 父母 -> 子女（子女為父母代 +1）
        for parents, child in children:
            known = [gens[p] for p in parents if p in gens]
            if known:
                g = max(known) + 1
                if child not in gens or gens[child] < g:
                    gens[child] = g; changed = True

        # 子女 -> 父母（若子女已知代，父母＝子女代-1，不小於0）
        for parents, child in children:
            if child in gens:
                for p in parents:
                    if p not in gens:
                        g = max(0, gens[child] - 1)
                        gens[p] = g; changed = True

    # 若仍有未指定世代的人，放入與 anchor 同代
    if gens and len(gens) < len(persons):
        default_gen = gens.get(anchor_id, 0) if anchor_id in gens else 0
        for pid in persons:
            if pid not in gens:
                gens[pid] = default_gen

    return gens

def build_graphviz_source(db, anchor_id=""):
    persons = db.get("persons", {})
    marriages = normalize_marriages(db.get("marriages", []))
    children = normalize_children(db.get("children", []))

    # 計算世代（保證配偶同層、子女下一層）
    gens = compute_generations(db, anchor_id)

    # 建 spouse map 與 kids map
    spouse_map = defaultdict(list)
    for a,b,stt in marriages:
        spouse_map[a].append((b,stt))
        spouse_map[b].append((a,stt))

    kids_by_parents = defaultdict(list)
    for parents, child in children:
        kids_by_parents[parents].append(child)

    THEME = "#0F4C5C"
    NODE_STYLE = (
        'shape=box, style="rounded,filled", color="{0}", fillcolor="{0}22", '
        'fontname="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei, Arial", '
        'fontsize=16'
    ).format(THEME)

    dot = []
    dot.append("digraph G {")
    dot.append('graph [splines=ortho, nodesep=0.6, ranksep=0.9];')
    dot.append(f"node [{NODE_STYLE}];")
    dot.append(f'edge [color="{THEME}", penwidth=2];')

    # 人物節點
    for pid, info in persons.items():
        label = info.get("name", pid)
        dot.append(f'"{pid}" [label="{label}"];')

    # 夫妻中點與連線
    mid_nodes = set()
    for a,b,status in marriages:
        # 夫妻同層
        dot.append('{rank=same; "' + a + '" "' + b + '"}')
        # 相鄰（不可見高權重）
        dot.append(f'"{a}" -> "{b}" [style=invis, weight=1000, constraint=true];')

        mid = f"mid_{a}_{b}"
        mid_nodes.add(mid)
        dot.append(f'"{mid}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')
        style = "solid" if status == "married" else "dashed"
        dot.append(f'"{a}" -> "{mid}" [dir=none, style={style}];')
        dot.append(f'"{mid}" -> "{b}" [dir=none, style={style}];')

    # 兄弟姊妹排序（年長在左）
    def kid_sort_key(kid_id):
        p = persons.get(kid_id, {})
        return (p.get("birth", 10**9), p.get("order", 10**9), p.get("name", kid_id))

    # 子女 rail
    for key, kids in kids_by_parents.items():
        kids_sorted = sorted(kids, key=kid_sort_key)
        rail = "rail_" + "_".join(key) if key else "rail_root"
        dot.append("{rank=same; " + " ".join(['"{}"'.format(rail)] + [f'"{k}"' for k in kids_sorted]) + "}")
        dot.append(f'"{rail}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')

        if len(key) == 2:
            a,b = key
            mid = f"mid_{a}_{b}"
            if mid not in mid_nodes:
                dot.append(f'"{mid}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')
                dot.append(f'"{a}" -> "{mid}" [dir=none, style=solid];')
                dot.append(f'"{mid}" -> "{b}" [dir=none, style=solid];')
                mid_nodes.add(mid)
            dot.append(f'"{mid}" -> "{rail}" [dir=none];')
        elif len(key) == 1:
            p = key[0]
            dot.append(f'"{p}" -> "{rail}" [dir=none];')
        for kid in kids_sorted:
            dot.append(f'"{rail}" -> "{kid}" [dir=none];')

    # 固定 anchor 的水平順序：前任 → anchor → 現任
    if anchor_id in persons:
        exs = [s for s,stt in spouse_map.get(anchor_id, []) if stt != "married"]
        curs = [s for s,stt in spouse_map.get(anchor_id, []) if stt == "married"]
        ordered = exs + [anchor_id] + curs
        if len(ordered) > 1:
            dot.append('{rank=same; ' + " ".join(f'"{x}"' for x in ordered) + "}")
            for a,b in zip(ordered, ordered[1:]):
                dot.append(f'"{a}" -> "{b}" [style=invis, weight=2000, constraint=true];')

    # 每一代同層（0,1,2…）
    gen_to_nodes = defaultdict(list)
    for pid,g in gens.items():
        gen_to_nodes[g].append(pid)
    for g in sorted(gen_to_nodes.keys()):
        nodes = gen_to_nodes[g]
        dot.append("{rank=same; " + " ".join(f'"{n}"' for n in nodes) + "}")

    dot.append("}")
    return "\n".join(dot)

# =========================
# UI：左側輸入、右側預覽
# =========================
left, right = st.columns([1,2])

with left:
    st.subheader("資料輸入")
    b1, b2 = st.columns(2)
    if b1.button("載入示範"):
        load_demo()
    if b2.button("全部清空", type="secondary"):
        clear_all()
    st.divider()

    with st.form("add_person"):
        st.markdown("**新增人物**")
        pid = st.text_input("ID（英文/數字，不可重複）")
        name = st.text_input("姓名 *")
        birth = st.number_input("出生年（可空）", min_value=0, step=1, value=0)
        order = st.number_input("同輩排序（可空）", min_value=0, step=1, value=0)
        submitted = st.form_submit_button("加入人物")
        if submitted:
            if not pid or not name:
                st.error("ID 與 姓名 為必填")
            elif pid in db["persons"]:
                st.error("此 ID 已存在")
            else:
                db["persons"][pid] = {"name": name}
                if birth: db["persons"][pid]["birth"] = int(birth)
                if order: db["persons"][pid]["order"] = int(order)
                st.success(f"已新增人物 {name}（{pid}）")

    with st.form("add_marriage"):
        st.markdown("**新增婚姻/伴侶**")
        a = st.text_input("A 的 ID")
        b = st.text_input("B 的 ID")
        status = st.selectbox("關係狀態", ["married", "divorced", "widowed"])
        submitted = st.form_submit_button("加入關係")
        if submitted:
            if not a or not b or a not in db["persons"] or b not in db["persons"]:
                st.error("A/B ID 必須存在於人物清單")
            else:
                db["marriages"].append({"a": a, "b": b, "status": status})
                st.success(f"已新增關係：{a} - {b}（{status}）")

    with st.form("add_child"):
        st.markdown("**新增子女**")
        p1 = st.text_input("家長 1 ID（必填）")
        p2 = st.text_input("家長 2 ID（可空白，單親留空）")
        c  = st.text_input("子女 ID（需已存在於人物清單）")
        submitted = st.form_submit_button("加入子女")
        if submitted:
            ps = [x for x in [p1.strip(), p2.strip()] if x]
            if len(ps)==0 or not c:
                st.error("請至少提供 1 位家長與 1 位子女")
            elif any(p not in db["persons"] for p in ps) or c not in db["persons"]:
                st.error("家長/子女必須存在於人物清單")
            else:
                db["children"].append({"parents": ps, "child": c})
                st.success(f"已新增子女關係：{ps} -> {c}")

    # 選擇主角（第 0 代）
    st.markdown("**選擇主角（第 0 代）**")
    options = [""] + list(db["persons"].keys())
    labels = {k: (db["persons"][k]["name"] if k else "（未指定）") for k in options}
    selected = st.selectbox("主角", options=options, format_func=lambda k: labels[k], index=options.index(st.session_state.anchor) if st.session_state.anchor in options else 0)
    st.session_state.anchor = selected

with right:
    st.subheader("家族樹預覽")
    dot = build_graphviz_source(db, anchor_id=st.session_state.anchor)
    st.graphviz_chart(dot, use_container_width=True)

    st.download_button(
        "下載 Graphviz DOT",
        data=dot.encode("utf-8"),
        file_name="family_tree.dot",
        mime="text/vnd.graphviz",
    )

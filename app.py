
import json
from collections import defaultdict, deque
import streamlit as st

st.set_page_config(page_title="家庭樹", page_icon="🌳", layout="wide")

# -------- State --------
if "db" not in st.session_state:
    # 預設 demo；使用者可自行覆寫
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

db = st.session_state.db

# -------- Helpers --------
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

def build_graphviz_source(db):
    persons = db.get("persons", {})
    marriages = normalize_marriages(db.get("marriages", []))
    children = normalize_children(db.get("children", []))

    spouse_map = defaultdict(list)
    for a, b, stt in marriages:
        spouse_map[a].append((b, stt))
        spouse_map[b].append((a, stt))

    kids_by_parents = defaultdict(list)
    parent_of = defaultdict(list)
    child_of = {}
    for parents, child in children:
        kids_by_parents[parents].append(child)
        for p in parents:
            parent_of[p].append(child)
        child_of[child] = list(parents)

    # ---- generations (確保第三代會出現) ----
    gens = {pid: 0 for pid in persons if pid not in child_of}
    q = deque(gens.keys())
    while q:
        p = q.popleft()
        for c in parent_of.get(p, []):
            if c not in gens or gens[c] < gens[p] + 1:
                gens[c] = gens[p] + 1
                q.append(c)

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

    # nodes
    for pid, info in persons.items():
        label = info.get("name", pid)
        dot.append(f'"{pid}" [label="{label}"];')

    # marriages + midpoint
    mid_nodes = set()
    for a, b, status in marriages:
        dot.append('{rank=same; "' + a + '" "' + b + '"}')
        dot.append(f'"{a}" -> "{b}" [style=invis, weight=1000, constraint=true];')
        mid = f"mid_{a}_{b}"
        mid_nodes.add(mid)
        dot.append(f'"{mid}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')
        style = "solid" if status == "married" else "dashed"
        dot.append(f'"{a}" -> "{mid}" [dir=none, style={style}];')
        dot.append(f'"{mid}" -> "{b}" [dir=none, style={style}];')

    def kid_sort_key(kid_id):
        p = persons.get(kid_id, {})
        return (p.get("birth", 10**9), p.get("order", 10**9), p.get("name", kid_id))

    # rails & kids
    for key, kids in kids_by_parents.items():
        kids_sorted = sorted(kids, key=kid_sort_key)
        rail = "rail_" + "_".join(key) if key else "rail_root"
        dot.append("{rank=same; " + " ".join(['"{}"'.format(rail)] + [f'"{k}"' for k in kids_sorted]) + "}")
        dot.append(f'"{rail}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')

        if len(key) == 2:
            a, b = key
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

    # order: ex -> self -> current (applicable if current exists)
    for p, lst in spouse_map.items():
        current = [s for s, stt in lst if stt == "married"]
        exs = [s for s, stt in lst if stt != "married"]
        if current:
            ordered = exs + [p] + current
            dot.append('{rank=same; ' + " ".join(f'"{x}"' for x in ordered) + "}")
            for a, b in zip(ordered, ordered[1:]):
                dot.append(f'"{a}" -> "{b}" [style=invis, weight=2000, constraint=true];')

    # rank by generation (will naturally show 第0/1/2代 = 三層)
    gen_to_nodes = defaultdict(list)
    for pid, g in gens.items():
        gen_to_nodes[g].append(pid)
    for g, nodes in sorted(gen_to_nodes.items(), key=lambda x: x[0]):
        if nodes:
            dot.append("{rank=same; " + " ".join(f'"{n}"' for n in nodes) + "}")

    dot.append("}")
    return "\n".join(dot)

# -------- UI: 左側輸入 / 右側預覽 --------
left, right = st.columns([1, 2])

with left:
    st.header("輸入資料")
    with st.expander("快速新增"):
        with st.form("add_person"):
            st.subheader("新增人物")
            pid = st.text_input("ID（必填，英文/數字）")
            pname = st.text_input("姓名*", value="")
            pbirth = st.number_input("出生年(可選)", value=0, min_value=0, step=1)
            porder = st.number_input("排序號(可選)", value=0, min_value=0, step=1)
            if st.form_submit_button("加入人物"):
                if pid and pname:
                    st.session_state.db["persons"][pid] = {"name": pname}
                    if pbirth: st.session_state.db["persons"][pid]["birth"] = int(pbirth)
                    if porder: st.session_state.db["persons"][pid]["order"] = int(porder)
                    st.success(f"已新增人物：{pname} ({pid})")
                else:
                    st.error("ID 與 姓名 必填")

        with st.form("add_marriage"):
            st.subheader("新增婚姻/伴侶")
            a = st.text_input("A 的 ID")
            b = st.text_input("B 的 ID")
            status = st.selectbox("關係狀態", ["married", "divorced", "widowed"])
            if st.form_submit_button("加入關係"):
                if a and b and a in db["persons"] and b in db["persons"]:
                    st.session_state.db["marriages"].append({"a": a, "b": b, "status": status})
                    st.success(f"已新增關係：{a} - {b} ({status})")
                else:
                    st.error("A/B 必須存在於人物清單中")

        with st.form("add_child"):
            st.subheader("新增子女")
            parent1 = st.text_input("家長1 ID（必填）")
            parent2 = st.text_input("家長2 ID（可空白，單親就留空）")
            child = st.text_input("子女 ID（必須已存在人物）")
            if st.form_submit_button("加入子女"):
                ps = [p for p in [parent1.strip(), parent2.strip()] if p]
                if not ps or not child:
                    st.error("請提供至少一位家長與一位子女 ID")
                elif any(p not in db["persons"] for p in ps) or child not in db["persons"]:
                    st.error("家長/子女 ID 必須存在於人物清單中")
                else:
                    st.session_state.db["children"].append({"parents": ps, "child": child})
                    st.success(f"已新增子女關係：{ps} -> {child}")

    # 原始 JSON 編輯
    st.subheader("JSON 編輯（可直接貼上）")
    edited = st.text_area(
        "資料格式：persons / marriages / children",
        value=json.dumps(db, ensure_ascii=False, indent=2),
        height=420,
    )
    if st.button("套用 JSON"):
        try:
            st.session_state.db = json.loads(edited)
            db = st.session_state.db
            st.success("已套用")
        except Exception as e:
            st.error(f"JSON 解析失敗：{e}")

    st.download_button(
        "下載 JSON",
        data=json.dumps(db, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="family_data.json",
        mime="application/json",
    )

with right:
    st.header("預覽家族樹")
    dot = build_graphviz_source(db)
    st.graphviz_chart(dot, use_container_width=True)

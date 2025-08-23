
import json
from collections import defaultdict, deque
import streamlit as st

# -----------------------
# 基本設定
# -----------------------
st.set_page_config(page_title="家庭樹（正確三代佈局）", page_icon="🌳", layout="wide")

# -----------------------
# Demo 資料：與附圖一致
# -----------------------
DEMO_DB = {
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
    # status: married(實線) / divorced(虛線) / widowed(虛線)
    "marriages": [
        {"a": "p_self", "b": "p_ex", "status": "divorced"},
        {"a": "p_self", "b": "p_cur", "status": "married"},
        {"a": "p_wangzi", "b": "p_wangzi_sp", "status": "married"},
    ],
    # parents 可為兩位或單親（只有一位）
    "children": [
        {"parents": ["p_self", "p_cur"], "child": "p_d1"},
        {"parents": ["p_self", "p_cur"], "child": "p_d2"},
        {"parents": ["p_self", "p_cur"], "child": "p_d3"},
        {"parents": ["p_wangzi", "p_wangzi_sp"], "child": "p_wangsun"},
        # 依附圖：王子視為前妻的單親子女（不是陳一郎之子）
        {"parents": ["p_ex"], "child": "p_wangzi"},
    ],
}


# -----------------------
# Graphviz DOT 產生器
# -----------------------
def build_graphviz_source(db):
    persons = db.get("persons", {})
    marriages = []
    for m in db.get("marriages", []):
        a, b = m["a"], m["b"]
        if a > b:
            a, b = b, a
        marriages.append((a, b, m.get("status", "married")))

    children = []
    for c in db.get("children", []):
        ps = list(c.get("parents", []))
        if len(ps) == 2 and ps[0] > ps[1]:
            ps[0], ps[1] = ps[1], ps[0]
        children.append((tuple(ps), c["child"]))

    spouse_map = defaultdict(list)
    for a, b, st in marriages:
        spouse_map[a].append((b, st))
        spouse_map[b].append((a, st))

    kids_by_parents = defaultdict(list)
    parent_of = defaultdict(list)
    child_of = {}
    for parents, child in children:
        kids_by_parents[parents].append(child)
        for p in parents:
            parent_of[p].append(child)
        child_of[child] = list(parents)

    # 推算世代
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

    # 人物節點
    for pid, info in persons.items():
        label = info.get("name", pid)
        dot.append(f'"{pid}" [label="{label}"];')

    # 夫妻與中點
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
        return (
            p.get("birth", 10**9),
            p.get("order", 10**9),
            p.get("name", kid_id),
        )

    for key, kids in kids_by_parents.items():
        kids_sorted = sorted(kids, key=kid_sort_key)
        rail = "rail_" + "_".join(key) if key else "rail_root"

        same_rank_elems = " ".join(['"{}"'.format(rail)] + [f'"{k}"' for k in kids_sorted])
        dot.append("{rank=same; " + same_rank_elems + "}")
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

    for p, lst in spouse_map.items():
        current = [s for s, st in lst if st == "married"]
        exs = [s for s, st in lst if st != "married"]
        if current:
            ordered = exs + [p] + current
            dot.append('{rank=same; ' + " ".join(f'"{x}"' for x in ordered) + "}")
            for a, b in zip(ordered, ordered[1:]):
                dot.append(f'"{a}" -> "{b}" [style=invis, weight=2000, constraint=true];')

    gen_to_nodes = defaultdict(list)
    for pid, g in gens.items():
        gen_to_nodes[g].append(pid)
    for g, nodes in gen_to_nodes.items():
        dot.append("{rank=same; " + " ".join(f'"{n}"' for n in nodes) + "}")

    dot.append("}")
    return "\n".join(dot)


# -----------------------
# UI
# -----------------------
st.title("🌳 家庭樹（正確三代佈局版）")

st.markdown('''
- 若不上傳檔案，會直接顯示內建 demo（與你附圖一致）。
- 也可上傳自訂 JSON，結構如下：

```
{
  "persons": {
    "idA": {"name": "張三", "birth": 1970, "order": 1},
    "idB": {"name": "李四"}
  },
  "marriages": [
    {"a": "idA", "b": "idB", "status": "married"}   // 或 "divorced"/"widowed"
  ],
  "children": [
    {"parents": ["idA", "idB"], "child": "child1"},
    {"parents": ["idB"], "child": "child2"}         // 單親
  ]
}
```
''')

uploaded = st.file_uploader("上傳自訂家庭 JSON（可略過）", type=["json"])
if uploaded:
    try:
        db = json.load(uploaded)
    except Exception as e:
        st.error(f"JSON 解析失敗：{e}")
        st.stop()
else:
    db = DEMO_DB

dot = build_graphviz_source(db)
st.subheader("家族樹")
st.graphviz_chart(dot, use_container_width=True)

with st.expander("查看 DOT 原始碼（除錯用）"):
    st.code(dot, language="dot")

st.download_button(
    "下載 Graphviz DOT",
    data=dot.encode("utf-8"),
    file_name="family_tree.dot",
    mime="text/vnd.graphviz",
)

st.caption("© 永傳家族辦公室｜重點邏輯：夫妻中點＋水平順序固定＋世代分層")

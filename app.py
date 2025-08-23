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
    """
    根據資料輸出 Graphviz DOT：
    1) 夫妻中點（point）承接子女，避免子女線接錯父或母
    2) 三代以 rank=same 固定層級
    3) 不可見邊固定「前任 → 本人 → 現任」水平順序
    4) 兄弟姊妹以 birth/order 排序，經由 rail（point）排列
    """
    persons = db.get("persons", {})
    # marriages 正規化成 (a,b,status) 並確保 a<b 方便建 key
    marriages = []
    for m in db.get("marriages", []):
        a, b = m["a"], m["b"]
        if a > b:
            a, b = b, a
        marriages.append((a, b, m.get("status", "married")))

    # children: [(parents_tuple, child)]
    children = []
    for c in db.get("children", []):
        ps = list(c.get("parents", []))
        if len(ps) == 2 and ps[0] > ps[1]:
            ps[0], ps[1] = ps[1], ps[0]
        children.append((tuple(ps), c["child"]))

    # 關聯表
    spouse_map = defaultdict(list)      # p -> [(spouse, status)]
    for a, b, st in marriages:
        spouse_map[a].append((b, st))
        spouse_map[b].append((a, st))

    kids_by_parents = defaultdict(list) # key=(a,b) 或 (a,) -> [child...]
    parent_of = defaultdict(list)
    child_of = {}
    for parents, child in children:
        kids_by_parents[parents].append(child)
        for p in parents:
            parent_of[p].append(child)
        child_of[child] = list(parents)

    # 推算世代：沒有父母紀錄者為第 0 代
    gens = {pid: 0 for pid in persons if pid not in child_of}
    q = deque(gens.keys())
    while q:
        p = q.popleft()
        for c in parent_of.get(p, []):
            if c not in gens or gens[c] < gens[p] + 1:
                gens[c] = gens[p] + 1
                q.append(c)

    # 風格
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
        # 夫妻同層
        dot.append('{rank=same; "' + a + '" "' + b + '"}')
        # 讓二人相鄰：高權重不可見邊
        dot.append(f'"{a}" -> "{b}" [style=invis, weight=1000, constraint=true];')

        mid = f"mid_{a}_{b}"
        mid_nodes.add(mid)
        dot.append(f'"{mid}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')
        style = "solid" if status == "married" else "dashed"
        dot.append(f'"{a}" -> "{mid}" [dir=none, style={style}];')
        dot.append(f'"{mid}" -> "{b}" [dir=none, style={style}];')

    # 兄弟姊妹排序 key
    def kid_sort_key(kid_id):
        p = persons.get(kid_id, {})
        return (
            p.get("birth", 10**9),
            p.get("order", 10**9),
            p.get("name", kid_id),
        )

    # rail：夫妻中點/單親 → rail → kids
    for key, kids in kids_by_parents.items():
        kids_sorted = sorted(kids, key=kid_sort_key)
        rail = "rail_" + "_".join(key) if key else "rail_root"

        # rail 與孩子同層
        same_rank_elems = " ".join(['"{}"'.format(rail)] + [f'"{k}"' for k in kids_sorted])
        dot.append("{rank=same; " + same_rank_elems + "}")
        dot.append(f'"{rail}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')

        if len(key) == 2:
            a, b = key
            mid = f"mid_{a}_{b}"
            if mid not in mid_nodes:
                # 若沒有婚姻記錄但有共同子女，也建立中點（預設實線）
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

    # 水平順序：前任 → 本人 → 現任（有現任才固定）
    for p, lst in spouse_map.items():
        current = [s for s, st in lst if st == "married"]
        exs = [s for s, st in lst if st != "married"]
        if current:
            ordered = exs + [p] + current
            dot.append('{rank=same; ' + " ".join(f'"{x}"' for x in ordered) + "}")
            for a, b in zip(ordered, ordered[1:]):
                dot.append(f'"{a}" -> "{b}" [style=invis, weight=2000, constraint=true];')

    # 同代同層
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

st.markdown("""
- 若不上傳檔案，會直接顯示內建 demo（與你附圖一致）。
- 也可上傳自訂 JSON，結構如下：


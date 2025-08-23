import json
import os
from collections import defaultdict, deque
import streamlit as st

st.set_page_config(page_title="家庭樹範例（正確三代佈局）", page_icon="🌳", layout="wide")

# =========================
# Demo 資料（與你附圖一致）
# =========================
DEMO_DB = {
    # 人物：id -> {name, birth(可選, 用於同輩排序), order(可選, 沒 birth 時用), note(可選)}
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

    # 婚姻/伴侶關係（會建立夫妻中點；非 married 以虛線顯示）
    # a 與 b 的 id，小到大不重要，程式會處理
    "marriages": [
        {"a": "p_self", "b": "p_ex", "status": "divorced"},  # 離婚：虛線
        {"a": "p_self", "b": "p_cur", "status": "married"},  # 現任：實線
        {"a": "p_wangzi", "b": "p_wangzi_sp", "status": "married"},  # 王子夫妻
    ],

    # 子女關係
    # parents: 兩位父母或單親（只有 1 個 id），child: 子女 id
    # ⚠️ 若想畫成「單親」，就只放一個家長；若是雙親，放兩個家長
    "children": [
        # 陳一郎＋陳妻 的孩子三人
        {"parents": ["p_self", "p_cur"], "child": "p_d1"},
        {"parents": ["p_self", "p_cur"], "child": "p_d2"},
        {"parents": ["p_self", "p_cur"], "child": "p_d3"},

        # 王孫：王子＋王子妻
        {"parents": ["p_wangzi", "p_wangzi_sp"], "child": "p_wangsun"},

        # 王子：這裡依照你的附圖 → 畫成「陳前妻的單親子女」（不是陳一郎的孩子）
        # 如果你想要王子是前妻＋一郎的孩子，就改成 ["p_ex","p_self"]
        {"parents": ["p_ex"], "child": "p_wangzi"},
    ]
}


# =========================
# Graphviz DOT 產生器
# =========================
def build_graphviz_source(db):
    """把結構化資料轉成 Graphviz DOT，保證：
       1) 夫妻同層、前任→本人→現任 水平排序固定
       2) 孩子永遠從【夫妻中點】或【單親】往下
       3) 同一代 rank=same，確保三代分層
       4) 兄弟姊妹由 birth/order 排序，rail 與孩子同層避免交錯
    """
    persons = db["persons"]
    # 正規化 marriages：[(a,b,status)] 確保 a<b，方便生成 key
    marriages = []
    for m in db.get("marriages", []):
        a, b, status = m["a"], m["b"], m.get("status", "married")
        if a > b:
            a, b = b, a
        marriages.append((a, b, status))

    # children：[(parents_tuple, child)]
    children = []
    for c in db.get("children", []):
        ps = list(c["parents"])
        child = c["child"]
        if len(ps) == 2 and ps[0] > ps[1]:
            ps[0], ps[1] = ps[1], ps[0]
        children.append((tuple(ps), child))

    spouse_map = defaultdict(list)   # p -> [(spouse, status)]
    for a, b, st in marriages:
        spouse_map[a].append((b, st))
        spouse_map[b].append((a, st))

    kids_by_parents = defaultdict(list)  # key=(a,b) 或 (a,) -> [child...]
    parent_of = defaultdict(list)
    child_of = defaultdict(list)
    for parents, child in children:
        kids_by_parents[parents].append(child)
        for p in parents:
            parent_of[p].append(child)
        child_of[child] = list(parents)

    # ---- 推世代（沒有父母紀錄者為第 0 代）
    gens = {pid: 0 for pid in persons if pid not in child_of}
    q = deque(gens.keys())
    while q:
        p = q.popleft()
        for c in parent_of.get(p, []):
            if c not in gens or gens[c] < gens[p] + 1:
                gens[c] = gens[p] + 1
                q.append(c)

    # ---- DOT 風格
    THEME = "#0F4C5C"
    NODE_STYLE = (
        'shape=box, style="rounded,filled", color="{0}", fillcolor="{0}22", '
        'fontname="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei, Arial", '
        'fontsize=16'.format(THEME)
    )

    dot = []
    dot.append("digraph G {")
    dot.append('graph [splines=ortho, nodesep=0.6, ranksep=0.9];')
    dot.append(f"node [{NODE_STYLE}];")
    dot.append(f'edge [color="{THEME}", penwidth=2];')

    # ---- 人物節點
    for pid, info in persons.items():
        label = info.get("name", pid)
        dot.append(f'"{pid}" [label="{label}"];')

    # ---- 夫妻中點與連線（虛線=非 married）
    mid_nodes = set()
    for a, b, status in marriages:
        # 同層
        dot.append('{rank=same; "' + a + '" "' + b + '"}')
        # 讓兩人相鄰（不可見邊，提升 weight）
        dot.append(f'"{a}" -> "{b}" [style=invis, weight=1000, constraint=true];')

        mid = f"mid_{a}_{b}"
        mid_nodes.add(mid)
        dot.append(f'"{mid}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')
        style = "solid" if status == "married" else "dashed"
        dot.append(f'"{a}" -> "{mid}" [dir=none, style={style}];')
        dot.append(f'"{mid}" -> "{b}" [dir=none, style={style}];')

    # ---- 兄弟姊妹排序
    def kid_sort_key(kid_id):
        p = persons.get(kid_id, {})
        # birth 小者在左；若沒有 birth，用 order；都沒有則以名字排序
        return (
            p.get("birth", 10**9),
            p.get("order", 10**9),
            p.get("name", kid_id),
        )

    # ---- rail：夫妻中點/單親 → rail → 孩子（rail 與孩子同層）
    for key, kids in kids_by_parents.items():
        kids_sorted = sorted(kids, key=kid_sort_key)
        rail = "rail_" + "_".join(key) if key else "rail_root"
        dot.append(
            "{rank=same; " + " ".join(['"{}"'.format(rail)] + [f'"{k}"' for k in kids_sorted]) + "}"
        )
        dot.append(f'"{rail}" [shape=point, width=0.01, height=0.01, color="#94A3B8"];')

        if len(key) == 2:
            a, b = key
            mid = f"mid_{a}_{b}"
            if mid not in mid_nodes:
                # 若沒有婚姻記錄，但有共同子女，也建立中點（預設實線）
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

    # ---- 前任 → 本人 → 現任 的水平順序固定（每位當事人只要有現任配偶就套用）
    for p, lst in spouse_map.items():
        cur = [s for s, st in lst if st == "married"]
        exs = [s for s, st in lst if st != "married"]
        if cur:
            ordered = exs + [p] + cur
            dot.append('{rank=same; ' + " ".join(f'"{x}"' for x in ordered) + "}")
            for a, b in zip(ordered, ordered[1:]):
                dot.append(f'"{a}" -> "{b}" [style=invis, weight=2000, constraint=true];')

    # ---- 同代同層
    gen_to_nodes = defaultdict(list)
    for pid, g in gens.items():
        gen_to_nodes[g].append(pid)
    for g, nodes in gen_to_nodes.items():
        dot.append("{rank=same; " + " ".join(f'"{n}"' for n in nodes) + "}")

    dot.append("}")
    return "\n".join(dot)


# =========================
# UI
# =========================
st.title("🌳 家庭樹（正確三代佈局版）")

st.markdown(
    """
- 若不上傳檔案，會直接顯示內建 demo（與你附圖一致）。  
- 也可上傳自訂 JSON，結構如下：
```json
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

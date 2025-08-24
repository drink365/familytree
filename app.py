# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from collections import defaultdict, deque

st.set_page_config(page_title="家族樹（穩定 SVG 版・修正配偶列）", page_icon="🌳", layout="wide")

# ---------------- 視覺參數 ----------------
NODE_W = 120       # 節點寬
NODE_H = 56        # 節點高
H_GAP  = 46        # 橫向間距
V_GAP  = 120       # 縱向間距

BG     = "#0b3d4f"
FG     = "#ffffff"
BORDER = "#114b5f"
LINE   = "#0f3c4d"

# ---------------- 狀態 ----------------
def empty_state():
    return {"persons": {}, "marriages": {}, "children": []}

if "data" not in st.session_state:
    st.session_state.data = empty_state()

def clear_all():
    st.session_state.data = empty_state()

def load_demo():
    """與題圖一致；先清空避免殘留造成錯位"""
    clear_all()
    P = st.session_state.data["persons"]
    M = st.session_state.data["marriages"]
    C = st.session_state.data["children"]

    def np(name):
        pid = f"P{len(P)+1}"
        P[pid] = {"name": name}
        return pid

    def nm(a, b, divorced=False):
        mid = f"M{len(M)+1}"
        M[mid] = {"a": a, "b": b, "divorced": divorced}
        return mid

    # 人物
    chen = np("陳一郎")
    ex   = np("陳前妻")
    wife = np("陳妻")
    c1   = np("陳大")
    c2   = np("陳二")
    c3   = np("陳三")
    wz   = np("王子")
    wzw  = np("王子妻")
    ws   = np("王孫")

    # 婚姻
    mex  = nm(chen, ex, True)
    mnow = nm(chen, wife, False)
    mw   = nm(wz,   wzw,  False)

    # 子女
    C += [
        {"mid": mex,  "child": wz},
        {"mid": mnow, "child": c1},
        {"mid": mnow, "child": c2},
        {"mid": mnow, "child": c3},
        {"mid": mw,   "child": ws},
    ]

# ---------------- 資料映射 ----------------
def build_maps(data):
    kids_of = defaultdict(list)        # mid -> [child...]
    parents_of = {}                    # child -> {a,b}
    marriages_of = defaultdict(list)   # person -> [mid...]

    for mid, m in data["marriages"].items():
        a, b = m["a"], m["b"]
        marriages_of[a].append(mid)
        marriages_of[b].append(mid)

    for row in data["children"]:
        mid, child = row["mid"], row["child"]
        kids_of[mid].append(child)
        a = data["marriages"][mid]["a"]
        b = data["marriages"][mid]["b"]
        parents_of[child] = {a, b}

    # 便於找配偶
    spouses_of = defaultdict(set)
    for mid, m in data["marriages"].items():
        a, b = m["a"], m["b"]
        spouses_of[a].add(b)
        spouses_of[b].add(a)

    return kids_of, parents_of, marriages_of, spouses_of

# ---------------- 分層：配偶跟著有血緣的人走 ----------------
def compute_levels(data):
    kids_of, parents_of, marriages_of, spouses_of = build_maps(data)
    persons = list(data["persons"].keys())

    # 真正的根：沒有父母，且沒有配偶是「有父母的人」
    has_parents = set(parents_of.keys())
    roots = []
    for p in persons:
        if p in has_parents:
            continue
        # 若配偶中有人有父母，p 不能當根（要跟著那位下移）
        if any(sp in has_parents for sp in spouses_of.get(p, [])):
            continue
        roots.append(p)

    level = {}
    q = deque(roots)
    for r in roots:
        level[r] = 0

    seen = set(roots)

    while q:
        p = q.popleft()
        lv = level[p]

        # 讓配偶跟著同層（這一步把像「王子妻」這類無父母者往下拉到配偶那層）
        for sp in spouses_of.get(p, []):
            if sp not in level:
                level[sp] = lv
            if sp not in seen:
                seen.add(sp); q.append(sp)

        # 由 p 的婚姻取得孩子 → 下一層
        for mid in marriages_of.get(p, []):
            for c in kids_of.get(mid, []):
                if c not in level:
                    level[c] = lv + 1
                if c not in seen:
                    seen.add(c); q.append(c)

    # 可能還有孤立節點，補到第 0 層
    for p in persons:
        if p not in level:
            level[p] = 0

    return level

# ---------------- 版面配置：同層配偶緊鄰、孩子群組連續 ----------------
def layout_positions(data):
    level = compute_levels(data)
    kids_of, parents_of, marriages_of, spouses_of = build_maps(data)

    # 每層的節點清單（暫不含排序）
    levels = defaultdict(list)
    for p, lv in level.items():
        levels[lv].append(p)

    # 第 0 層：把「多段婚姻的中心人物」放在他所在群組的中間（近似）
    # 這裡簡化為按名稱排序，已足以固定示範案例順序
    for lv in levels:
        levels[lv].sort(key=lambda pid: data["persons"][pid]["name"])

    # 生成水平位置：逐層從左到右
    pos = {}
    max_lv = max(level.values()) if level else 0

    # 先排第 0 層
    x = 40
    y0 = 40
    for p in levels[0]:
        pos[p] = (x, y0)
        x += NODE_W + H_GAP

    # 從第 1 層開始：依「上一層的婚姻 → 其孩子(+孩子配偶)」為群組排列
    for lv in range(1, max_lv + 1):
        y = 40 + lv * V_GAP
        x = 40

        # 找出上一層的節點與其左右順序
        prev_nodes = [p for p, (px, py) in pos.items() if abs(py - (40 + (lv - 1) * V_GAP)) < 1e-6]
        prev_nodes.sort(key=lambda pid: pos[pid][0])
        index_in_prev = {pid: i for i, pid in enumerate(prev_nodes)}

        # 取出父母皆在上一層的婚姻，依父母在上一層的靠左者排序
        mids = []
        for mid, m in data["marriages"].items():
            a, b = m["a"], m["b"]
            if a in index_in_prev and b in index_in_prev:
                mids.append((min(index_in_prev[a], index_in_prev[b]), mid))
        mids.sort()

        placed = set()

        for _, mid in mids:
            kids = kids_of.get(mid, [])
            # 以孩子的插入順序作為左→右順序；每位孩子的配偶，緊鄰其右
            for c in kids:
                if c not in placed:
                    pos[c] = (x, y); x += NODE_W + H_GAP; placed.add(c)
                # c 的配偶（同層）緊鄰右側
                for mid2 in marriages_of.get(c, []):
                    a, b = data["marriages"][mid2]["a"], data["marriages"][mid2]["b"]
                    sp = a if b == c else b
                    if sp in level and level[sp] == lv and sp not in placed:
                        pos[sp] = (x, y); x += NODE_W + H_GAP; placed.add(sp)

        # 若同層還有未放入的（例如孤立節點），補位
        for p in levels.get(lv, []):
            if p not in placed:
                pos[p] = (x, y); x += NODE_W + H_GAP; placed.add(p)

    return pos

# ---------------- SVG 基元 ----------------
def svg_rect(x, y, w, h, rx=16, text=""):
    return f'''
      <g>
        <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"
              fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
        <text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle"
              font-size="14" font-family="sans-serif" fill="{FG}">{text}</text>
      </g>
    '''

def svg_line(x1, y1, x2, y2, dashed=False):
    dash = ' stroke-dasharray="6,6"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="2"{dash}/>\n'

# ---------------- 繪製 ----------------
def render_svg(data):
    pos = layout_positions(data)
    if not pos:
        return "<svg/>"

    kids_of, parents_of, marriages_of, _ = build_maps(data)

    # 畫布大小
    max_x = max(x for x, _ in pos.values()) + NODE_W + 60
    max_y = max(y for _, y in pos.values()) + NODE_H + 80

    edges = []

    # 夫妻水平線 + 婚姻點 + 子女垂直線
    for mid, m in data["marriages"].items():
        a, b, divorced = m["a"], m["b"], m.get("divorced", False)
        if a not in pos or b not in pos:
            continue
        ax, ay = pos[a]; bx, by = pos[b]
        yline = (ay + by) / 2

        # 夫妻水平線（同層時等高；若不同層，仍以各自中心連）
        edges.append(svg_line(ax + NODE_W, ay + NODE_H / 2, bx, by + NODE_H / 2, dashed=divorced))

        # 婚姻點（放在兩人下方）
        jx = (ax + bx + NODE_W) / 2
        jy = max(ay, by) + NODE_H / 2 + 8

        # 該婚姻的孩子：婚姻點垂直→水平→下探到孩子
        for c in kids_of.get(mid, []):
            if c not in pos:
                continue
            cx, cy = pos[c]
            edges.append(svg_line(jx, jy, jx, cy - 12))                 # 垂直到孩子上方
            edges.append(svg_line(jx, cy - 12, cx + NODE_W/2, cy - 12)) # 水平到孩子上方
            edges.append(svg_line(cx + NODE_W/2, cy - 12, cx + NODE_W/2, cy))  # 直落

    # 節點
    nodes = [svg_rect(x, y, NODE_W, NODE_H, text=data["persons"][pid]["name"])
             for pid, (x, y) in pos.items()]

    svg = f'''
    <svg width="{max_x}" height="{max_y}" xmlns="http://www.w3.org/2000/svg" style="background:#fff">
      {"".join(edges)}
      {"".join(nodes)}
    </svg>
    '''
    return svg

# ---------------- UI ----------------
with st.sidebar:
    st.markdown("## 操作")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範", use_container_width=True):
            load_demo()
    with c2:
        if st.button("清空", use_container_width=True):
            clear_all()

st.markdown("## 家族樹（穩定 SVG 版）")
svg = render_svg(st.session_state.data)
st.components.v1.html(svg, height=720, scrolling=True)

with st.expander("（除錯）目前資料"):
    st.json(st.session_state.data, expanded=False)

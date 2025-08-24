# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import math
from collections import defaultdict, deque

st.set_page_config(page_title="家族樹（穩定 SVG 版）", page_icon="🌳", layout="wide")

# ========== 視覺參數 ==========
NODE_W = 120        # 節點寬
NODE_H = 56         # 節點高
H_GAP  = 40         # 同一列節點的水平間距
V_GAP  = 120        # 列與列的垂直距
FONT   = "14px sans-serif"

BG     = "#0b3d4f"
FG     = "#ffffff"
BORDER = "#114b5f"
LINE   = "#0f3c4d"

# ========== 內部資料結構 ==========
def empty_state():
    return {
        "persons": {},        # pid -> {"name": str}
        "marriages": {},      # mid -> {"a": pid, "b": pid, "divorced": bool}
        "children": []        # {"mid": mid, "child": pid}
    }

if "data" not in st.session_state:
    st.session_state.data = empty_state()

def clear_all():
    st.session_state.data = empty_state()

def load_demo():
    """載入與你的範例圖一致的資料"""
    clear_all()
    P = st.session_state.data["persons"]
    M = st.session_state.data["marriages"]
    C = st.session_state.data["children"]

    def np(name):
        pid = f"P{len(P)+1}"
        P[pid] = {"name": name}
        return pid
    def nm(a,b,div=False):
        mid = f"M{len(M)+1}"
        M[mid] = {"a": a, "b": b, "divorced": div}
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
    mw   = nm(wz,   wzw, False)

    # 子女
    C += [
        {"mid": mex,  "child": wz},
        {"mid": mnow, "child": c1},
        {"mid": mnow, "child": c2},
        {"mid": mnow, "child": c3},
        {"mid": mw,   "child": ws},
    ]

# ========== 版面計算（手工演算法，避免 Graphviz 路由） ==========
def build_maps(data):
    kids_of = defaultdict(list)   # mid -> [child]
    parents_of = {}               # child -> {a,b}
    marriages_of = defaultdict(list)  # person -> [mid]

    for mid, m in data["marriages"].items():
        a, b = m["a"], m["b"]
        marriages_of[a].append(mid); marriages_of[b].append(mid)

    for rec in data["children"]:
        mid, child = rec["mid"], rec["child"]
        kids_of[mid].append(child)
        a = data["marriages"][mid]["a"]
        b = data["marriages"][mid]["b"]
        parents_of[child] = {a,b}

    return kids_of, parents_of, marriages_of

def generations(data):
    """回傳 person -> level（第幾列），以父母列+1為原則；沒有父母者為 0 列"""
    kids_of, parents_of, marriages_of = build_maps(data)

    level = {}
    # 找出沒有父母的人（根）
    roots = [pid for pid in data["persons"].keys() if pid not in parents_of]
    for r in roots: level[r] = 0

    # BFS：父母的孩子在下一列；若 child 有配偶，配偶同列
    q = deque(roots)
    seen = set(roots)
    while q:
        p = q.popleft()
        # p 的所有婚姻
        for mid in marriages_of.get(p, []):
            # 該婚姻的孩子
            for c in kids_of.get(mid, []):
                if c not in level:
                    level[c] = level[p] + 1
                if c not in seen:
                    seen.add(c); q.append(c)
                # c 的配偶（若有）也放同列
                for mid2 in marriages_of.get(c, []):
                    a, b = data["marriages"][mid2]["a"], data["marriages"][mid2]["b"]
                    spouse = a if b == c else b
                    if spouse not in level:
                        level[spouse] = level[c]   # 同列
                    if spouse not in seen:
                        seen.add(spouse); q.append(spouse)
    return level

def layout_positions(data):
    """
    輸出：pos[pid] = (x,y)；x 依每列分組順序手工排；y = level * V_GAP
    規則：
      - 每列由左到右：以「上一列的婚姻 → 其子女(+其配偶)」為一個群組，群組內保持相鄰
      - 同人只顯示一次；多段婚姻時，該人以其最低的 level 站位
    """
    lvl = generations(data)
    by_level = defaultdict(list)
    for pid, lv in lvl.items():
        by_level[lv].append(pid)

    # 依序排列每一列
    pos = {}
    y_of = lambda lv: lv * V_GAP + 40

    kids_of, parents_of, marriages_of = build_maps(data)

    # 第一列：沒有父母者，保持出現順序；同一人多段婚姻也只放一個節點
    x = 40
    for pid in sorted(by_level.get(0, []), key=lambda p: data["persons"][p]["name"]):
        pos[pid] = (x, y_of(0))
        x += NODE_W + H_GAP

    # 從第 1 列起：依上一列的婚姻來決定群組順序
    max_lv = max(lvl.values()) if lvl else 0
    for lv in range(1, max_lv+1):
        x = 40
        y = y_of(lv)
        # 找出「父母在 lv-1」的所有婚姻，依父母的橫向順序來展開孩子群組
        parent_row = [p for p, l in pos.items() if abs(l[1] - y_of(lv-1)) < 1e-6]
        parent_rank = {p:i for i,p in enumerate(sorted(parent_row, key=lambda p: pos[p][0]))}

        mids = []
        for mid, m in data["marriages"].items():
            a, b = m["a"], m["b"]
            if a in parent_rank and b in parent_rank:
                # 父母都在上一列
                mids.append((min(parent_rank[a], parent_rank[b]), mid))
        mids.sort()

        placed = set()
        for _, mid in mids:
            kids = kids_of.get(mid, [])
            for c in kids:
                # 先放孩子本身
                if c not in placed:
                    pos[c] = (x, y)
                    x += NODE_W + H_GAP
                    placed.add(c)
                # 若孩子有配偶，配偶緊鄰其右
                for mid2 in marriages_of.get(c, []):
                    a, b = data["marriages"][mid2]["a"], data["marriages"][mid2]["b"]
                    spouse = a if b == c else b
                    if spouse in lvl and lvl[spouse] == lv and spouse not in placed:
                        pos[spouse] = (x, y)
                        x += NODE_W + H_GAP
                        placed.add(spouse)

        # 可能仍有同列但不在上述群組的（例如外部加入的人），補位
        for pid in by_level.get(lv, []):
            if pid not in placed:
                pos[pid] = (x, y)
                x += NODE_W + H_GAP
                placed.add(pid)

    return pos

# ========== SVG 繪製 ==========
def svg_rect(x, y, w, h, rx=16, text=""):
    return f'''
    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"
            fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
      <text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle"
            font-size="14" font-family="sans-serif" fill="{FG}">{text}</text>
    </g>
    '''

def svg_line(x1,y1,x2,y2, dashed=False):
    dash = ' stroke-dasharray="6,6"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="2"{dash}/>\n'

def render_svg(data):
    pos = layout_positions(data)
    if not pos:
        return "<svg/>"

    # 畫布大小
    max_x = max(x for x,_ in pos.values()) + NODE_W + 40
    max_y = max(y for _,y in pos.values()) + NODE_H + 80

    kids_of, parents_of, marriages_of = build_maps(data)

    # 夫妻線 + 婚姻點 + 子女線
    edges = []
    for mid, m in data["marriages"].items():
        a, b, divorced = m["a"], m["b"], m.get("divorced", False)
        if a not in pos or b not in pos: 
            continue
        ax, ay = pos[a]; bx, by = pos[b]
        # 夫妻線
        y = (ay + by)/2  # 同列；保險點
        edges.append(svg_line(ax+NODE_W, ay+NODE_H/2, bx, by+NODE_H/2, dashed=divorced))
        # 婚姻點（在兩人中間下方）
        jx = (ax + bx + NODE_W)/2
        jy = max(ay, by) + NODE_H/2 + 8
        # 子女
        for c in kids_of.get(mid, []):
            if c not in pos: 
                continue
            cx, cy = pos[c]
            # 垂直落下： 婚姻點 → 子女上緣
            edges.append(svg_line(jx, jy, jx, cy-12))
            # 水平短連到子女中心上方
            edges.append(svg_line(jx, cy-12, cx+NODE_W/2, cy-12))
            # 再短垂直到子女框
            edges.append(svg_line(cx+NODE_W/2, cy-12, cx+NODE_W/2, cy))

    # 節點
    nodes = []
    for pid, p in data["persons"].items():
        if pid not in pos: 
            continue
        x, y = pos[pid]
        nodes.append(svg_rect(x, y, NODE_W, NODE_H, text=p["name"]))

    svg = f'''
    <svg width="{max_x}" height="{max_y}" xmlns="http://www.w3.org/2000/svg" style="background:#fff">
      {"".join(edges)}
      {"".join(nodes)}
    </svg>
    '''
    return svg

# ========== UI ==========
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
st.components.v1.html(svg, height=700, scrolling=True)

with st.expander("（除錯）目前資料"):
    st.json(st.session_state.data, expanded=False)

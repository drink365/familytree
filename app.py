import streamlit as st
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ================== 示範資料（固定） ==================
DEMO_MARRIAGES = {
    "陳一郎|陳妻": {"label": "陳一郎╳陳妻", "children": ["王子", "陳大", "陳二", "陳三"]},
    "王子|王子妻": {"label": "王子╳王子妻", "children": ["王孫"]},
    "陳大|陳大嫂": {"label": "陳大╳陳大嫂", "children": ["二孩A", "二孩B", "二孩C"]},
    "陳二|陳二嫂": {"label": "陳二╳陳二嫂", "children": ["三孩A"]},
}
DEMO_PERSONS = {
    "王子": {"label": "王子", "children_marriages": ["王子|王子妻"]},
    "陳大": {"label": "陳大", "children_marriages": ["陳大|陳大嫂"]},
    "陳二": {"label": "陳二", "children_marriages": ["陳二|陳二嫂"]},
    "陳三": {"label": "陳三", "children_marriages": []},
    "王孫": {"label": "王孫", "children_marriages": []},
    "二孩A": {"label": "二孩A", "children_marriages": []},
    "二孩B": {"label": "二孩B", "children_marriages": []},
    "二孩C": {"label": "二孩C", "children_marriages": []},
    "三孩A": {"label": "三孩A", "children_marriages": []},
}

# ================== 版面視覺（專業預設） ==================
NODE_W, NODE_H = 120, 40
MIN_SEP, LEVEL_GAP = 140, 140
BOX_COLOR = "rgba(12,74,110,1.0)"
TEXT_COLOR = "white"

st.set_page_config(page_title="家族樹（示範）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹（示範）")

# ================== 佈局演算法（Reingold–Tilford 簡化版） ==================
@dataclass
class TNode:
    id: str
    children: List["TNode"] = field(default_factory=list)
    prelim: float = 0.0
    mod: float = 0.0
    x: float = 0.0
    y: float = 0.0
    parent: Optional["TNode"] = None
    thread: Optional["TNode"] = None
    ancestor: Optional["TNode"] = None
    change: float = 0.0
    shift: float = 0.0
    number: int = 0

def _left_brother(v: TNode) -> Optional[TNode]:
    if v.parent is None: return None
    idx = v.number - 1
    return v.parent.children[idx-1] if idx > 0 else None

def _default_left(v: TNode) -> TNode:
    return v.thread or (v.children[0] if v.children else v)

def _default_right(v: TNode) -> TNode:
    return v.thread or (v.children[-1] if v.children else v)

def _ancestor(vil: TNode, v: TNode, default_ancestor: TNode) -> TNode:
    if vil.ancestor and vil.ancestor.parent == v.parent:
        return vil.ancestor
    return default_ancestor

def _move_subtree(wl: TNode, wr: TNode, shift: float):
    subtrees = wr.number - wl.number
    if subtrees <= 0: return
    wr.change += shift / subtrees
    wr.shift += shift
    wl.change -= shift / subtrees
    wr.prelim += shift
    wr.mod += shift

def _execute_shifts(v: TNode):
    shift = change = 0.0
    for w in reversed(v.children):
        w.prelim += shift
        w.mod += shift
        change += w.change
        shift += w.shift + change

def _apportion(v: TNode, min_sep: float):
    w = _left_brother(v)
    if not w: return
    vir = vor = v
    vil = w
    vol = v.parent.children[0]
    sir = vir.mod; sor = vor.mod
    sil = vil.mod; sol = vol.mod
    while _default_right(vil) and _default_left(vir):
        vil = _default_right(vil)
        vir = _default_left(vir)
        vol = _default_left(vol)
        vor = _default_right(vor)
        vor.ancestor = v
        shift = (vil.prelim + sil) - (vir.prelim + sir) + min_sep
        if shift > 0:
            a = _ancestor(vil, v, v.parent.children[0])
            _move_subtree(a, v, shift)
            sir += shift; sor += shift
        sil += vil.mod; sir += vir.mod
        sol += vol.mod; sor += vor.mod
    if _default_right(vil) and not _default_right(vor):
        vor.thread = _default_right(vil); vor.mod += sil - sor
    if _default_left(vir) and not _default_left(vol):
        vol.thread = _default_left(vir); vol.mod += sir - sol

def _first_walk(v: TNode, min_sep: float, depth: int, level_gap: float):
    for i, w in enumerate(v.children):
        w.parent = v; w.number = i + 1
        _first_walk(w, min_sep, depth + 1, level_gap)
    if not v.children:
        lb = _left_brother(v)
        v.prelim = (lb.prelim + min_sep) if lb else 0.0
    else:
        for w in v.children: _apportion(w, min_sep)
        _execute_shifts(v)
        midpoint = (v.children[0].prelim + v.children[-1].prelim) / 2
        lb = _left_brother(v)
        if lb:
            v.prelim = lb.prelim + min_sep
            v.mod = v.prelim - midpoint
        else:
            v.prelim = midpoint
    v.y = depth * level_gap

def _second_walk(v: TNode, m: float, positions: Dict[str, Tuple[float, float]]):
    v.x = v.prelim + m
    positions[v.id] = (v.x, v.y)
    for w in v.children: _second_walk(w, m + v.mod, positions)

def tidy_layout(root: TNode, min_sep: float = 140.0, level_gap: float = 140.0) -> Dict[str, Tuple[float, float]]:
    _first_walk(root, min_sep, depth=0, level_gap=level_gap)
    pos: Dict[str, Tuple[float, float]] = {}
    _second_walk(root, 0.0, pos)
    min_x = min(x for x, _ in pos.values())
    if min_x < 0:
        pos = {k: (x - min_x, y) for k, (x, y) in pos.items()}
    return pos

# ================== 由婚姻資料建樹：孩子先掛在「自己的父母」下面 ==================
def build_tree_from_marriages(
    marriages: Dict[str, Dict],
    persons: Dict[str, Dict],
    root_marriage_id: str
) -> Tuple[TNode, Dict[str, TNode]]:
    node_map: Dict[str, TNode] = {}
    def get_node(nid: str) -> TNode:
        if nid not in node_map: node_map[nid] = TNode(id=nid)
        return node_map[nid]
    def build(mid: str) -> TNode:
        m_node = get_node(mid)
        for child in marriages.get(mid, {}).get("children", []):
            c_node = get_node(child)
            m_node.children.append(c_node)           # 孩子一定掛在自己的父母下方
            for sub_m in persons.get(child, {}).get("children_marriages", []):
                sub_m_node = build(sub_m)            # 再把孩子的婚姻掛在孩子下面
                c_node.children.append(sub_m_node)
        return m_node
    return build(root_marriage_id), node_map

# ================== 畫「示範家族樹」 ==================
def draw_demo_tree():
    marriages, persons, root_id = DEMO_MARRIAGES, DEMO_PERSONS, "陳一郎|陳妻"
    root, _ = build_tree_from_marriages(marriages, persons, root_id)
    pos = tidy_layout(root, min_sep=MIN_SEP, level_gap=LEVEL_GAP)
    if not pos:
        st.error("沒有可顯示的節點。"); return

    def is_m(nid: str) -> bool: return nid in marriages
    xs, ys, labels = [], [], []
    for nid, (x, y) in pos.items():
        xs.append(x); ys.append(y)
        labels.append(marriages.get(nid, {}).get("label") if is_m(nid) else persons.get(nid, {}).get("label", nid))

    # 邊
    ex, ey = [], []
    for m_id, m in marriages.items():
        for child in m.get("children", []):
            if m_id in pos and child in pos:
                x0, y0 = pos[m_id]; x1, y1 = pos[child]
                ex.extend([x0, x1, None]); ey.extend([y0 + NODE_H/2, y1 - NODE_H/2, None])
    for pid, p in persons.items():
        for sub_m in p.get("children_marriages", []):
            if pid in pos and sub_m in pos:
                x0, y0 = pos[pid]; x1, y1 = pos[sub_m]
                ex.extend([x0, x1, None]); ey.extend([y0 + NODE_H/2, y1 - NODE_H/2, None])

    # 軸域（向下為正）
    pad_x, pad_y = NODE_W * 0.75, NODE_H * 2.0
    min_x, max_x = min(xs) - pad_x, max(xs) + pad_x
    min_y, max_y = min(ys) - pad_y, max(ys) + pad_y

    fig = go.Figure()
    if ex:
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines",
                                 line=dict(width=2, color="rgba(80,80,80,1)"),
                                 hoverinfo="none", name=""))
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(symbol="square", size=34, color=BOX_COLOR,
                    line=dict(width=1, color="rgba(0,0,0,0.25)")),
        text=labels, textposition="middle center",
        textfont=dict(color=TEXT_COLOR, size=12),
        hoverinfo="text", name=""
    ))
    fig.update_layout(
        xaxis=dict(visible=False, range=[min_x, max_x]),
        yaxis=dict(visible=False, range=[max_y, min_y]),  # 倒序：向下為正
        margin=dict(l=20, r=20, t=20, b=20),
        height=600, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ===== 直接畫出示範家族樹（不用任何表單或外部檔案） =====
draw_demo_tree()

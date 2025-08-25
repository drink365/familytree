# tree_layout.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TNode:
    id: str
    children: List["TNode"] = field(default_factory=list)
    # layout fields
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
    if v.parent is None:
        return None
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
    if subtrees <= 0:
        return
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
    if not w:
        return
    vir = vor = v
    vil = w
    vol = v.parent.children[0]
    sir = vir.mod
    sor = vor.mod
    sil = vil.mod
    sol = vol.mod
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
            sir += shift
            sor += shift
        sil += vil.mod
        sir += vir.mod
        sol += vol.mod
        sor += vor.mod
    if _default_right(vil) and not _default_right(vor):
        vor.thread = _default_right(vil)
        vor.mod += sil - sor
    if _default_left(vir) and not _default_left(vol):
        vol.thread = _default_left(vir)
        vol.mod += sir - sol

def _first_walk(v: TNode, min_sep: float, depth: int, level_gap: float):
    for i, w in enumerate(v.children):
        w.parent = v
        w.number = i + 1
        _first_walk(w, min_sep, depth + 1, level_gap)
    if not v.children:
        lb = _left_brother(v)
        v.prelim = (lb.prelim + min_sep) if lb else 0.0
    else:
        for w in v.children:
            _apportion(w, min_sep)
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
    for w in v.children:
        _second_walk(w, m + v.mod, positions)

def tidy_layout(root: TNode, min_sep: float = 120.0, level_gap: float = 140.0) -> Dict[str, Tuple[float, float]]:
    """回傳 {node_id: (x, y)}；孩子永遠掛在自己父母(婚姻節點)下方，
    若與左右子樹距離 < min_sep，則整掛平移。"""
    _first_walk(root, min_sep, depth=0, level_gap=level_gap)
    pos: Dict[str, Tuple[float, float]] = {}
    _second_walk(root, 0.0, pos)
    min_x = min(x for x, _ in pos.values())
    if min_x < 0:
        pos = {k: (x - min_x, y) for k, (x, y) in pos.items()}
    return pos

# ===== 資料 → 樹：以「婚姻節點」為錨點 =====
def build_tree_from_marriages(
    marriages: Dict[str, Dict],
    persons: Dict[str, Dict],
    root_marriage_id: str
) -> Tuple[TNode, Dict[str, TNode]]:
    node_map: Dict[str, TNode] = {}

    def get_node(nid: str) -> TNode:
        if nid not in node_map:
            node_map[nid] = TNode(id=nid)
        return node_map[nid]

    def build(m_id: str) -> TNode:
        m_node = get_node(m_id)
        # 孩子一定先掛在「這段婚姻節點」下面
        for child_id in marriages.get(m_id, {}).get("children", []):
            c_node = get_node(child_id)
            m_node.children.append(c_node)
            # 再把孩子自己的婚姻節點掛在孩子下面
            for sub_m in persons.get(child_id, {}).get("children_marriages", []):
                sub_m_node = build(sub_m)
                c_node.children.append(sub_m_node)
        return m_node

    root = build(root_marriage_id)
    return root, node_map

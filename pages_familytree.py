# -*- coding: utf-8 -*-
# pages_familytree.py
#
# 家族樹（Streamlit + Graphviz）
# 重點：
# 1) 配偶一定相鄰（在同層、同群內強制相鄰）
# 2) 同父母子女必定成群，不被外人插隊
# 3) 匯入 JSON 需要按「套用匯入」才會覆寫，避免無限 rerun 閃爍
# 4) Graphviz：婚姻點放入配偶所在層的子圖，並以隱形邊夾在兩配偶中間，避免長弧線

from __future__ import annotations
import json
import uuid
from typing import Dict, List, Tuple, Optional

import streamlit as st
from graphviz import Digraph


# -----------------------------
# 初始化
# -----------------------------
def _init_state():
    if "family" not in st.session_state:
        st.session_state.family = {"persons": {}, "marriages": {}}
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}
    if "group_order" not in st.session_state:
        st.session_state.group_order = {}
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = "upload_1"


def _new_pid():
    return f"P{uuid.uuid4().hex[:4]}"


def _new_mid():
    return f"M{uuid.uuid4().hex[:4]}"


# -----------------------------
# 工具
# -----------------------------
def _base_key(pid: str, persons: Dict[str, dict]) -> Tuple:
    p = persons.get(pid, {})
    y = p.get("birth_year", None)
    nm = p.get("name", "")
    return (9999 if y in (None, "", 0) else int(y), str(nm), pid)


def _parents_mid_of(pid: str, marriages: Dict[str, dict]) -> Optional[str]:
    for mid, m in marriages.items():
        if pid in (m.get("children") or []):
            return mid
    return None


def _cluster_id_of(pid: str, d: int, marriages: Dict[str, dict]) -> str:
    pm = _parents_mid_of(pid, marriages)
    return pm if pm else f"orph:{pid}"


def _ensure_adjacent_inside(lst: List[str], a: str, b: str):
    """把 a 與 b 在 list 中強制相鄰（不調整其它元素的相對順序）"""
    if a not in lst or b not in lst:
        return
    ia, ib = lst.index(a), lst.index(b)
    if abs(ia - ib) == 1:
        return
    lst.pop(ib)
    ia = lst.index(a)
    lst.insert(ia + 1, b)


# -----------------------------
# 計算世代
# -----------------------------
def _compute_generations(tree: Dict) -> Dict[str, int]:
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # 收集父母→子女、配偶對
    children_of = {mid: (m.get("children") or []) for mid, m in marriages.items()}
    spouses_of  = {mid: (m.get("spouses")  or []) for mid, m in marriages.items()}

    # 根：不在任何 children 列表的人，放第 0 層
    all_children = set(c for kids in children_of.values() for c in kids)
    depth: Dict[str, int] = {pid: 0 for pid in persons if pid not in all_children}

    # 由上往下鬆弛直到收斂：配偶同層、子女 = 父母層 + 1
    for _ in range(200):
        changed = False

        # 配偶同層（若其中一人已知層級）
        for sps in spouses_of.values():
            known = [depth[s] for s in sps if s in depth]
            if known:
                d = min(known)
                for s in sps:
                    if depth.get(s) != d:
                        depth[s] = d
                        changed = True

        # 子女 = 父母層 + 1（若父母已有層級）
        for mid, kids in children_of.items():
            sps = spouses_of.get(mid, [])
            pd = [depth[s] for s in sps if s in depth]
            if pd:
                d = min(pd) + 1
                for c in kids:
                    if depth.get(c) != d:
                        depth[c] = d
                        changed = True

        if not changed:
            break

    # 尚未決定的人（孤立或尚未關聯）仍置於第 0 層
    for pid in persons:
        depth.setdefault(pid, 0)

    return depth

# -----------------------------
# 層內群序（穩定）
# -----------------------------
def _stable_cluster_order(
    d: int, clusters: Dict[str, List[str]], marriages: Dict[str, dict], persons: Dict[str, dict]
) -> List[str]:
    prev_order = st.session_state.get("gen_order", {}).get(str(d), [])
    pos = {pid: i for i, pid in enumerate(prev_order)} if prev_order else {}

    anchors = {}
    for cid, lst in clusters.items():
        if cid.startswith("orph:"):
            anchors[cid] = lst[0]
        else:
            m = marriages.get(cid, {})
            sps = m.get("spouses", []) or []
            anchor = None
            for s in sps:
                if s in pos:
                    anchor = s
                    break
            if not anchor:
                anchor = lst[0]
            anchors[cid] = anchor

    def key(cid):
        a = anchors[cid]
        return (0 if a in pos else 1, pos.get(a, 10**9), _base_key(a, persons))

    return sorted(clusters.keys(), key=key)


# -----------------------------
# 佈局核心：以「小孩為單位」織入配偶，保證夫妻相鄰
# -----------------------------
def _apply_rules(tree: Dict, focus_child: Optional[str] = None):
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth = _compute_generations(tree)

    # 分層
    layers: Dict[int, List[str]] = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order: Dict[str, List[str]] = {}
    maxd = max(layers.keys()) if layers else 0

    def _pick_primary_spouse(p: str, d: int) -> Optional[str]:
        """挑同層最合適配偶（有父母者優先、再比基本 key）"""
        cands = []
        for m in marriages.values():
            sps = m.get("spouses", []) or []
            if p in sps:
                for s in sps:
                    if s != p and depth.get(s) == d:
                        cands.append(s)
        if not cands:
            return None

        def kk(s):
            pm = _parents_mid_of(s, marriages)
            return (pm is None, _base_key(s, persons))  # 有父母者優先
        cands.sort(key=kk)
        return cands[0]

    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))

        # 依父母切群
        clusters: Dict[str, List[str]] = {}
        for p in members:
            cid = _cluster_id_of(p, d, marriages)
            clusters.setdefault(cid, []).append(p)

        # 群內穩定排序 + 確保群內同層配偶相鄰
        for cid, lst in clusters.items():
            lst.sort(key=lambda x: _base_key(x, persons))
            for m in marriages.values():
                sps = [s for s in (m.get("spouses", []) or []) if s in lst]
                if len(sps) >= 2:
                    _ensure_adjacent_inside(lst, sps[0], sps[1])

        # 群序
        base_cluster_order = _stable_cluster_order(d, clusters, marriages, persons)

        # 以「單位」（[人] 或 [人,配偶]）輸出，保證夫妻相鄰
        placed = set()
        final: List[str] = []

        for cid in base_cluster_order:
            lst = [p for p in clusters[cid] if p not in placed]
            units: List[List[str]] = []
            for p in lst:
                if p in placed:
                    continue
                sp = _pick_primary_spouse(p, d)
                if sp and sp not in placed:
                    units.append([p, sp])
                    placed.add(p)
                    placed.add(sp)
                else:
                    units.append([p])
                    placed.add(p)
            for u in units:
                final.extend(u)

        for p in members:
            if p not in placed:
                final.append(p)
                placed.add(p)

        gen_order[str(d)] = final

    # group_order（可選）
    group_order: Dict[str, List[str]] = {}
    for d, order in gen_order.items():
        d = int(d)
        pos = {p: i for i, p in enumerate(order)}
        mids = []
        for mid, m in tree.get("marriages", {}).items():
            sps = m.get("spouses", []) or []
            anchor = None
            for s in sps:
                if depth.get(s) == d:
                    anchor = s
                    break
            if anchor is None and sps:
                anchor = sps[0]
            if anchor in pos:
                mids.append((pos[anchor], mid))
        if mids:
            mids.sort()
            group_order[str(d)] = [mid for _, mid in mids]

    st.session_state.gen_order = gen_order
    st.session_state.group_order = group_order
    return gen_order, group_order


# -----------------------------
# Graphviz 視覺化（修正婚姻點長弧線問題）
# -----------------------------
def _graph(tree: Dict):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    gen_order = st.session_state.get("gen_order", {})
    depth     = _compute_generations(tree)

    g = Digraph(
        "G",
        graph_attr={
            "rankdir": "TB",
            "splines": "polyline",  # 讓線較直，避免過度彎曲
            "nodesep": "0.40",
            "ranksep": "0.80",
            "fontname": "Noto Sans CJK TC, Helvetica, Arial",
        },
    )
    g.attr("node", shape="rounded", fontsize="12",
           fontname="Noto Sans CJK TC, Helvetica, Arial")

    # 先建立各層的 rank 子圖，放人物，並用隱形邊固定左右順序
    maxd = max(depth.values()) if depth else 0
    for d in range(0, maxd + 1):
        with g.subgraph(name=f"cluster_rank_{d}") as sg:
            sg.attr(rank="same")
            order = gen_order.get(str(d), [])
            for pid in order:
                label = persons.get(pid, {}).get("name", pid)
                sg.node(pid, label)
            for i in range(len(order) - 1):
                sg.edge(order[i], order[i + 1], style="invis", weight="100")

    # 把婚姻點加入「配偶所在層」的子圖，並以隱形邊夾在兩配偶之間
    for mid, m in marriages.items():
        sps = m.get("spouses", []) or []
        if not sps:
            continue
        d = min(depth.get(s, 0) for s in sps)
        mnode = f"{mid}_pt"
        with g.subgraph(name=f"cluster_rank_{d}") as sg:
            sg.node(mnode, "", shape="point", width="0.02", height="0.02")
            if len(sps) >= 2:
                left, right = sps[0], sps[1]
                sg.edge(left,  mnode, style="invis", weight="200")
                sg.edge(mnode, right, style="invis", weight="200")

    # 真實邊：配偶↔婚姻點（不影響佈局），婚姻點→子女（正常）
    for mid, m in marriages.items():
        sps  = m.get("spouses", []) or []
        kids = m.get("children", []) or []
        if not sps:
            continue
        mnode = f"{mid}_pt"
        for s in sps:
            g.edge(s, mnode, dir="none", weight="2", constraint="false")
        for c in kids:
            g.edge(mnode, c, arrowhead="normal")

    st.graphviz_chart(g)


# -----------------------------
# UI：人物
# -----------------------------
def _ui_persons(tree: Dict):
    st.markdown("### ① 人物管理")
    with st.form("person_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        name   = col1.text_input("姓名 *")
        gender = col2.selectbox("性別", ["男", "女", ""])
        by     = col3.number_input("出生年", min_value=0, max_value=9999, value=0, step=1)
        submitted = col4.form_submit_button("＋ 新增人物")
        if submitted:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _new_pid()
                tree["persons"][pid] = {
                    "name": name.strip(),
                    "gender": gender,
                    "birth_year": None if by in (0, None) else int(by),
                }
                _apply_rules(tree)
                st.rerun()


# -----------------------------
# UI：婚姻 / 子女
# -----------------------------
def _ui_marriages(tree: Dict):
    st.markdown("### ② 婚姻與子女")

    persons   = tree["persons"]
    marriages = tree["marriages"]

    # 建立婚姻
    with st.form("m_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 3, 1])
        ppl = [(p["name"], pid) for pid, p in persons.items()]
        ppl.sort()
        s1 = col1.selectbox(
            "配偶 A", options=[""] + [pid for _, pid in ppl],
            format_func=lambda x: "" if not x else persons[x]["name"]
        )
        s2 = col2.selectbox(
            "配偶 B", options=[""] + [pid for _, pid in ppl],
            format_func=lambda x: "" if not x else persons[x]["name"]
        )
        ok = col3.form_submit_button("＋ 建立婚姻")
        if ok:
            if not s1 or not s2 or s1 == s2:
                st.warning("請選擇兩位不同人物")
            else:
                mid = _new_mid()
                marriages[mid] = {"spouses": [s1, s2], "children": []}
                _apply_rules(tree)
                st.rerun()

    # 管理每一段婚姻
    if marriages:
        for mid, m in marriages.items():
            with st.expander(f"婚姻 {mid}（點開管理）", expanded=False):
                sps = m.get("spouses", [])
                lbl = " × ".join(persons.get(p, {}).get("name", p) for p in sps)
                st.caption(lbl or "（尚未設定配偶）")

                # 加子女
                with st.form(f"kid_{mid}", clear_on_submit=True):
                    col1, col2 = st.columns([5, 1])
                    candidates = [
                        pid for pid in persons.keys()
                        if _parents_mid_of(pid, marriages) in (None, mid)
                    ]  # 不讓一人掛多組父母
                    sel = col1.selectbox(
                        "新增子女", options=[""] + candidates,
                        format_func=lambda x: "" if not x else persons[x]["name"]
                    )
                    ok = col2.form_submit_button("加入子女")
                    if ok:
                        if not sel:
                            st.warning("請選擇子女")
                        else:
                            if sel not in m["children"]:
                                m["children"].append(sel)
                                _apply_rules(tree, focus_child=sel)
                                st.rerun()

                kids = m.get("children", [])
                if kids:
                    st.write("此婚姻子女：", "、".join(persons[k]["name"] for k in kids if k in persons))
                else:
                    st.info("此婚姻目前沒有子女。")

                if st.button("刪除此婚姻", key=f"del_{mid}"):
                    marriages.pop(mid, None)
                    _apply_rules(tree)
                    st.rerun()


# -----------------------------
# UI：家族樹
# -----------------------------
def _ui_graph(tree: Dict):
    st.markdown("### ③ 家族樹視覺化")
    _apply_rules(tree)  # 保持穩定
    _graph(tree)


# -----------------------------
# UI：匯入 / 匯出（防止匯入後「一直閃」）
# -----------------------------
def _ui_io(tree: Dict):
    st.markdown("### ④ 匯入 / 匯出")
    col1, col2, col3 = st.columns([1, 1, 1])

    # 匯出
    col1.download_button(
        "下載 familytree.json",
        data=json.dumps(tree, ensure_ascii=False, indent=2),
        file_name="familytree.json",
        mime="application/json",
    )

    # 只「選檔」，不自動套用
    up = col2.file_uploader("選擇 JSON 檔", type=["json"], key=st.session_state.uploader_key)

    if up is not None:
        st.caption(f"已選擇檔案：{up.name}")
        if col2.button("套用匯入", key=f"apply_{st.session_state.uploader_key}"):
            try:
                data = json.loads(up.read().decode("utf-8"))
                if not isinstance(data, dict):
                    st.error("JSON 結構有誤")
                else:
                    st.session_state.family = data
                    _apply_rules(st.session_state.family)
                    st.success("匯入成功！")
                    # 重新產生 key 清空 uploader，避免 rerun 後又再觸發
                    st.session_state.uploader_key = f"upload_{uuid.uuid4().hex[:6]}"
                    st.rerun()
            except Exception as e:
                st.error(f"匯入失敗：{e}")

    # 清空
    if col3.button("清空所有資料"):
        st.session_state.family = {"persons": {}, "marriages": {}}
        st.session_state.gen_order = {}
        st.session_state.group_order = {}
        st.success("已清空")
        st.rerun()


# -----------------------------
# Page：main / render
# -----------------------------
def main():
    st.set_page_config(page_title="家族樹", layout="wide")
    _init_state()

    st.markdown("## 🌳 家族樹")
    tree = st.session_state.family

    with st.expander("① 人物管理", expanded=True):
        _ui_persons(tree)
    with st.expander("② 婚姻與子女", expanded=True):
        _ui_marriages(tree)
    with st.expander("③ 家族樹視覺化", expanded=True):
        _ui_graph(tree)
    with st.expander("④ 匯入 / 匯出", expanded=True):
        _ui_io(tree)


def render():
    """供外層 multipage 框架呼叫；不設定 page_config。"""
    _init_state()

    st.markdown("## 🌳 家族樹")
    tree = st.session_state.family

    with st.expander("① 人物管理", expanded=True):
        _ui_persons(tree)
    with st.expander("② 婚姻與子女", expanded=True):
        _ui_marriages(tree)
    with st.expander("③ 家族樹視覺化", expanded=True):
        _ui_graph(tree)
    with st.expander("④ 匯入 / 匯出", expanded=True):
        _ui_io(tree)


if __name__ == "__main__":
    main()

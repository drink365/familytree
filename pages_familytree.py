# -*- coding: utf-8 -*-
# pages_familytree.py
#
# Streamlit 家族樹（配偶相鄰、配偶水平線、婚姻點隱藏且僅用 invis 邊定位）

from __future__ import annotations
import json
import uuid
from typing import Dict, List, Optional, Tuple

import streamlit as st
from graphviz import Digraph


# ---------------------------
# Session 初始化
# ---------------------------
def _init_state():
    ss = st.session_state
    ss.setdefault("family", {"persons": {}, "marriages": {}})
    ss.setdefault("gen_order", {})
    ss.setdefault("group_order", {})
    ss.setdefault("uploader_key", f"up_{uuid.uuid4().hex[:6]}")


def _new_pid():
    return f"P{uuid.uuid4().hex[:4]}"


def _new_mid():
    return f"M{uuid.uuid4().hex[:4]}"


# ---------------------------
# 小工具
# ---------------------------
def _parents_mid_of(pid: str, marriages: Dict[str, dict]) -> Optional[str]:
    for mid, m in marriages.items():
        if pid in (m.get("children") or []):
            return mid
    return None


def _base_key(pid: str, persons: Dict[str, dict]) -> Tuple:
    p = persons.get(pid, {})
    nm = p.get("name", "")
    by = p.get("birth_year", None)
    return (9999 if by in (None, "", 0) else int(by), str(nm), pid)


# ---------------------------
# 世代計算
# ---------------------------
def _compute_generations(tree: Dict) -> Dict[str, int]:
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    depth: Dict[str, int] = {pid: 0 for pid in persons}

    spouses_of  = {mid: (m.get("spouses")  or []) for mid, m in marriages.items()}
    children_of = {mid: (m.get("children") or []) for mid, m in marriages.items()}

    for _ in range(200):
        changed = False

        # 配偶同層
        for sps in spouses_of.values():
            if not sps:
                continue
            known = [depth[s] for s in sps if s in depth]
            if known:
                d = min(known)
                for s in sps:
                    if depth.get(s) != d:
                        depth[s] = d
                        changed = True

        # 子女 = 父母層 + 1
        for mid, kids in children_of.items():
            if not kids:
                continue
            pd = [depth[s] for s in spouses_of.get(mid, []) if s in depth]
            if pd:
                d = min(pd) + 1
                for c in kids:
                    if depth.get(c) != d:
                        depth[c] = d
                        changed = True

        if not changed:
            break

    return depth


# ---------------------------
# 層內排序（以本人/配偶為單位，確保相鄰）
# ---------------------------
def _apply_rules(tree: Dict, focus_child: Optional[str] = None):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth     = _compute_generations(tree)

    # 分層
    layers: Dict[int, List[str]] = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order: Dict[str, List[str]] = {}

    def _pick_primary_spouse(p: str, d: int) -> Optional[str]:
        cands = []
        for m in marriages.values():
            sps = m.get("spouses") or []
            if p in sps:
                for s in sps:
                    if s != p and depth.get(s) == d:
                        cands.append(s)
        if not cands:
            return None

        def k(s):
            pm = _parents_mid_of(s, marriages)
            return (pm is None, _base_key(s, persons))  # 有父母者優先
        cands.sort(key=k)
        return cands[0]

    maxd = max(layers) if layers else 0
    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))
        placed = set()
        seq: List[str] = []
        for p in members:
            if p in placed:
                continue
            sp = _pick_primary_spouse(p, d)
            if sp and sp not in placed:
                seq.extend([p, sp])
                placed.update([p, sp])
            else:
                seq.append(p)
                placed.add(p)
        gen_order[str(d)] = seq

    st.session_state.gen_order = gen_order
    st.session_state.group_order = {}
    return gen_order, {}


# ---------------------------
# Graphviz（配偶水平線 + 婚姻點用 invis 邊定位）
# ---------------------------
def _graph(tree: Dict):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    gen_order = st.session_state.get("gen_order", {})
    depth     = _compute_generations(tree)

    g = Digraph(
        "G",
        graph_attr={
            "rankdir": "TB",           # 上→下
            "splines": "polyline",     # 稳定直線/折線
            "nodesep": "0.45",
            "ranksep": "0.85",
            "fontname": "Noto Sans CJK TC, Helvetica, Arial",
        },
    )
    g.attr("node", shape="rounded", fontsize="12",
           fontname="Noto Sans CJK TC, Helvetica, Arial")

    # 同層 subgraph + 隱形串邊固定左右順序
    maxd = max(depth.values()) if depth else 0
    for d in range(0, maxd + 1):
        with g.subgraph(name=f"rank_{d}") as sg:
            sg.attr(rank="same")
            order = gen_order.get(str(d), [])
            for pid in order:
                label = persons.get(pid, {}).get("name", pid)
                sg.node(pid, label)
            for i in range(len(order) - 1):
                sg.edge(order[i], order[i + 1], style="invis", weight="200")

    # 婚姻點（隱藏）+ 配偶水平線
    for mid, m in marriages.items():
        sps = m.get("spouses") or []
        if not sps:
            continue
        d = min(depth.get(s, 0) for s in sps)
        mnode = f"{mid}_pt"

        with g.subgraph(name=f"rank_{d}") as sg:
            # 婚姻點完全隱藏（仍可當作子女錨點）
            sg.node(mnode, "", shape="point", width="0.02", height="0.02", style="invis")

            if len(sps) >= 2:
                left, right = sps[0], sps[1]

                # 用「隱形邊」把婚姻點夾在兩配偶中間（參與佈局，不會被畫出）
                sg.edge(left,  mnode, style="invis", weight="300")
                sg.edge(mnode, right, style="invis", weight="300")

                # 只畫一條真正的配偶水平線（不參與佈局）
                g.edge(left, right,
                       dir="none",
                       constraint="false",
                       weight="0",
                       penwidth="1.6")
            elif len(sps) == 1:
                # 單一配偶時，只用隱形邊維持婚姻點位置
                sg.edge(sps[0], mnode, style="invis", weight="300")

    # 子女：婚姻點 ➜ 子女
    for mid, m in marriages.items():
        sps  = m.get("spouses") or []
        kids = m.get("children") or []
        if not sps:
            continue
        mnode = f"{mid}_pt"
        for c in kids:
            g.edge(mnode, c, arrowhead="normal")

    st.graphviz_chart(g, use_container_width=True)


# ---------------------------
# UI：人物
# ---------------------------
def _ui_persons(tree: Dict):
    st.markdown("### ① 人物管理")
    with st.form("person_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        name   = c1.text_input("姓名 *")
        gender = c2.selectbox("性別", ["男", "女", ""])
        by     = c3.number_input("出生年", min_value=0, max_value=9999, value=0, step=1)
        ok     = c4.form_submit_button("＋ 新增人物")
        if ok:
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


# ---------------------------
# UI：婚姻 / 子女
# ---------------------------
def _ui_marriages(tree: Dict):
    st.markdown("### ② 婚姻與子女")
    persons   = tree["persons"]
    marriages = tree["marriages"]

    # 建立婚姻
    with st.form("m_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 3, 1])
        ppl = [(p["name"], pid) for pid, p in persons.items()]
        ppl.sort()
        s1 = c1.selectbox("配偶 A", [""] + [pid for _, pid in ppl],
                          format_func=lambda x: "" if not x else persons[x]["name"])
        s2 = c2.selectbox("配偶 B", [""] + [pid for _, pid in ppl],
                          format_func=lambda x: "" if not x else persons[x]["name"])
        ok = c3.form_submit_button("＋ 建立婚姻")
        if ok:
            if not s1 or not s2 or s1 == s2:
                st.warning("請選擇兩位不同人物")
            else:
                mid = _new_mid()
                marriages[mid] = {"spouses": [s1, s2], "children": []}
                _apply_rules(tree)
                st.rerun()

    # 管理婚姻
    for mid, m in marriages.items():
        sps = m.get("spouses") or []
        with st.expander(f"{mid} 婚姻（點開管理）", expanded=False):
            st.caption(" × ".join(persons.get(p, {}).get("name", p) for p in sps) or "（尚未設定配偶）")

            # 加子女
            with st.form(f"kid_{mid}", clear_on_submit=True):
                cc1, cc2 = st.columns([5, 1])
                candidates = [
                    pid for pid in persons
                    if _parents_mid_of(pid, marriages) in (None, mid)
                ]
                sel = cc1.selectbox("新增子女", [""] + candidates,
                                    format_func=lambda x: "" if not x else persons[x]["name"])
                ok = cc2.form_submit_button("加入子女")
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
                st.write("子女：", "、".join(persons.get(k, {}).get("name", k) for k in kids))
            else:
                st.info("此婚姻目前沒有子女。")

            if st.button("刪除此婚姻", key=f"del_{mid}"):
                marriages.pop(mid, None)
                _apply_rules(tree)
                st.rerun()


# ---------------------------
# UI：家族樹視覺化
# ---------------------------
def _ui_graph(tree: Dict):
    st.markdown("### ③ 家族樹視覺化")
    _apply_rules(tree)
    _graph(tree)


# ---------------------------
# UI：匯入／匯出
# ---------------------------
def _ui_io(tree: Dict):
    st.markdown("### ④ 匯入 / 匯出")
    c1, c2, c3 = st.columns([1, 1, 1])

    # 匯出
    c1.download_button(
        "下載 familytree.json",
        data=json.dumps(tree, ensure_ascii=False, indent=2),
        file_name="familytree.json",
        mime="application/json",
    )

    # 匯入（選檔不自動套用，避免閃爍）
    up = c2.file_uploader("選擇 JSON", type=["json"], key=st.session_state.uploader_key)
    if up is not None:
        st.caption(f"已選檔：{up.name}")
        if c2.button("套用匯入", key=f"apply_{st.session_state.uploader_key}"):
            try:
                data = json.loads(up.read().decode("utf-8"))
                if isinstance(data, dict) and "persons" in data and "marriages" in data:
                    st.session_state.family = data
                    _apply_rules(st.session_state.family)
                    st.success("匯入成功")
                    st.session_state.uploader_key = f"up_{uuid.uuid4().hex[:6]}"
                    st.rerun()
                else:
                    st.error("JSON 結構不正確")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

    if c3.button("清空所有資料"):
        st.session_state.family = {"persons": {}, "marriages": {}}
        st.session_state.gen_order = {}
        st.session_state.group_order = {}
        st.success("已清空")
        st.rerun()


# ---------------------------
# Page：main / render
# ---------------------------
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

# -*- coding: utf-8 -*-
# pages_familytree.py
#
# 家族樹（Streamlit + Graphviz）
# - 資料結構：
#   tree = {
#     "persons": { pid: {"name":..., "gender":"男|女|", "birth_year": int|None } },
#     "marriages": { mid: {"spouses":[pid1,pid2,...], "children":[pid,...]} }
#   }
# - 佈局重點：以「小孩為單位」把配偶織入，確保配偶永遠相鄰、同父母子女不被外人打斷。

from __future__ import annotations
import json
import re
import uuid
from typing import Dict, List, Tuple, Optional

import streamlit as st
from graphviz import Digraph


# ------------------------------------------------------------
# 初始化
# ------------------------------------------------------------
def _init_state():
    if "family" not in st.session_state:
        st.session_state.family = {"persons": {}, "marriages": {}}
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}
    if "group_order" not in st.session_state:
        st.session_state.group_order = {}

def _new_pid():
    return f"P{uuid.uuid4().hex[:4]}"

def _new_mid():
    return f"M{uuid.uuid4().hex[:4]}"


# ------------------------------------------------------------
# 公用工具
# ------------------------------------------------------------
def _base_key(pid: str, persons: Dict[str, dict]) -> Tuple:
    p = persons.get(pid, {})
    y = p.get("birth_year", None)
    nm = p.get("name", "")
    # 先出生年，再姓名，再 id（穩定排序）
    return (9999 if y in (None, "", 0) else int(y), str(nm), pid)

def _parents_mid_of(pid: str, marriages: Dict[str, dict]) -> Optional[str]:
    for mid, m in marriages.items():
        if pid in (m.get("children") or []):
            return mid
    return None

def _cluster_id_of(pid: str, d: int, marriages: Dict[str, dict]) -> str:
    # 群的概念：同父母（同一 mid）的兄弟姊妹被視作同群；沒有父母者為孤兒群
    pm = _parents_mid_of(pid, marriages)
    return pm if pm else f"orph:{pid}"

def _ensure_adjacent_inside(lst: List[str], a: str, b: str):
    """把 a、b 排成相鄰（僅在 lst 內部挪動，保留穩定性）"""
    if a not in lst or b not in lst:
        return
    ia, ib = lst.index(a), lst.index(b)
    if abs(ia - ib) == 1:
        return
    # 把 b 拉到 a 的旁邊（左邊）
    lst.pop(ib)
    ia = lst.index(a)
    lst.insert(ia + 1, b)


# ------------------------------------------------------------
# 世代計算（同婚姻配偶同層；子女層=父母層+1）
# ------------------------------------------------------------
def _compute_generations(tree: Dict) -> Dict[str, int]:
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth: Dict[str, int] = {}

    child_of = {}
    for mid, m in marriages.items():
        for c in m.get("children", []) or []:
            child_of[c] = mid

    # 初始：不是任何人的小孩 => 先視為第 0 層
    for pid in persons.keys():
        if pid not in child_of:
            depth[pid] = 0

    # 疊代傳播層級
    for _ in range(120):
        changed = False

        # 同婚姻配偶同層
        for m in marriages.values():
            sps = m.get("spouses", []) or []
            known = [depth[s] for s in sps if s in depth]
            if known:
                d = min(known)
                for s in sps:
                    if depth.get(s) != d:
                        depth[s] = d
                        changed = True

        # 子女層 = 父母層 + 1
        for m in marriages.values():
            sps = m.get("spouses", []) or []
            kids = m.get("children", []) or []
            pd = [depth[s] for s in sps if s in depth]
            if not pd:
                continue
            d = min(pd) + 1
            for c in kids:
                if depth.get(c) != d:
                    depth[c] = d
                    changed = True

        # 如果有小孩已知層，回推父母層（最小孩子層 - 1）
        for m in marriages.values():
            sps = m.get("spouses", []) or []
            kids = m.get("children", []) or []
            kd = [depth[c] for c in kids if c in depth]
            if kd:
                want = min(kd) - 1
                for s in sps:
                    if s not in depth or depth[s] > want:
                        depth[s] = want
                        changed = True

        if not changed:
            break

    # 補齊：仍未知者當 0 層
    for pid in persons.keys():
        if pid not in depth:
            depth[pid] = 0

    # 平移最低層到 0
    min_d = min(depth.values()) if depth else 0
    if min_d < 0:
        for k in depth:
            depth[k] -= min_d
    return depth


# ------------------------------------------------------------
# 層內群序：盡量沿用上一輪，再插入新群
# ------------------------------------------------------------
def _stable_cluster_order(d: int, clusters: Dict[str, List[str]],
                          marriages: Dict[str, dict],
                          persons: Dict[str, dict]) -> List[str]:
    prev_order = st.session_state.get("gen_order", {}).get(str(d), [])
    pos = {pid: i for i, pid in enumerate(prev_order)} if prev_order else {}

    # 群的錨點：父母群以配偶做錨；孤兒群以成員做錨
    anchors = {}
    for cid, lst in clusters.items():
        if cid.startswith("orph:"):
            anchors[cid] = lst[0]
        else:
            # 父母群：找其中一位配偶做 anchor，若沒有在此層就取 children 中的第一位
            m = marriages.get(cid, {})
            sps = m.get("spouses", []) or []
            anchor = None
            for s in sps:
                if s in pos:  # 上一輪有出現過
                    anchor = s
                    break
            if not anchor:
                # 若上一輪沒出現，取群內排序最前的人
                anchor = lst[0]
            anchors[cid] = anchor

    def key(cid):
        a = anchors[cid]
        # 是否在上一輪有位置 / 上一輪位置 / 再用 base_key 穩定
        return (0 if a in pos else 1, pos.get(a, 10**9), _base_key(a, persons))

    return sorted(clusters.keys(), key=key)


# ------------------------------------------------------------
# 佈局核心：以「小孩為單位」織入配偶，保證夫妻相鄰
# ------------------------------------------------------------
def _apply_rules(tree: Dict, focus_child: Optional[str] = None):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth     = _compute_generations(tree)

    # 依層聚集
    layers: Dict[int, List[str]] = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order: Dict[str, List[str]] = {}
    maxd = max(layers.keys()) if layers else 0

    # 取得「同層的主要配偶候選」（多配偶挑一位，優先有父母者）
    def _pick_primary_spouse(p: str, d: int) -> Optional[str]:
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
            return (pm is None, _base_key(s, persons))
        cands.sort(key=kk)
        return cands[0]

    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))

        # 依父母切群
        clusters: Dict[str, List[str]] = {}
        for p in members:
            cid = _cluster_id_of(p, d, marriages)
            clusters.setdefault(cid, []).append(p)

        # 群內基本排序，並確保群內同層配偶相鄰（同一孤兒群的情況）
        for cid, lst in clusters.items():
            lst.sort(key=lambda x: _base_key(x, persons))
            for m in marriages.values():
                sps = [s for s in (m.get("spouses", []) or []) if s in lst]
                if len(sps) >= 2:
                    _ensure_adjacent_inside(lst, sps[0], sps[1])

        # 群序（沿用上一輪，插入新群）
        base_cluster_order = _stable_cluster_order(d, clusters, marriages, persons)

        # 以「小孩為單位（child, spouse）」輸出，確保配偶相鄰
        placed = set()
        final: List[str] = []

        for cid in base_cluster_order:
            lst = [p for p in clusters[cid] if p not in placed]

            # 把群內每個人轉為 unit
            units: List[List[str]] = []
            for p in lst:
                if p in placed:
                    continue
                sp = _pick_primary_spouse(p, d)
                if sp and sp not in placed:
                    units.append([p, sp])
                    placed.add(p); placed.add(sp)
                else:
                    units.append([p])
                    placed.add(p)

            # 此父母群輸出為 units 串接 → 群內保持連續
            for u in units:
                final.extend(u)

        # 若還有未被放入（例如被別人視為配偶時跳過），補上
        for p in members:
            if p not in placed:
                final.append(p)
                placed.add(p)

        gen_order[str(d)] = final

    # 產出 group_order（可選，用不到也無妨）
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
                    anchor = s; break
            if anchor is None and sps:
                anchor = sps[0]
            if anchor in pos:
                mids.append((pos[anchor], mid))
        if mids:
            mids.sort()
            group_order[str(d)] = [mid for _, mid in mids]

    st.session_state.gen_order   = gen_order
    st.session_state.group_order = group_order
    return gen_order, group_order


# ------------------------------------------------------------
# Graphviz 視覺化
# ------------------------------------------------------------
def _graph(tree: Dict):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    gen_order = st.session_state.get("gen_order", {})
    depth     = _compute_generations(tree)

    g = Digraph("G", graph_attr={
        "rankdir": "TB",
        "splines": "true",
        "nodesep": "0.40",
        "ranksep": "0.80",
        "fontname": "Noto Sans CJK TC, Helvetica, Arial",
    })
    g.attr("node", shape="rounded", fontsize="12", fontname="Noto Sans CJK TC, Helvetica, Arial")

    # 每層建立 rank=same；並以隱形邊鎖定左右順序
    maxd = max(depth.values()) if depth else 0
    for d in range(0, maxd + 1):
        with g.subgraph(name=f"cluster_rank_{d}") as sg:
            sg.attr(rank="same")
            order = gen_order.get(str(d), [])
            for pid in order:
                label = persons.get(pid, {}).get("name", pid)
                sg.node(pid, label)
            # 隱形邊固定左右順序
            for i in range(len(order) - 1):
                sg.edge(order[i], order[i + 1], style="invis", weight="100")

    # 婚姻點 + 子女
    for mid, m in marriages.items():
        sps = m.get("spouses", []) or []
        kids = m.get("children", []) or []
        if not sps:
            continue

        # 婚姻點放在配偶層
        d_sp = [depth[s] for s in sps if s in depth]
        if d_sp:
            d_here = min(d_sp)
        else:
            d_here = 0

        mnode = f"{mid}_pt"
        g.node(mnode, "", shape="point", width="0.02", height="0.02")

        # 連接配偶 ↔ 婚姻點（無箭頭、較重權重讓水平線穩一點）
        for s in sps:
            g.edge(s, mnode, dir="none", weight="10")

        # 從婚姻點連到子女
        for c in kids:
            g.edge(mnode, c, arrowhead="normal")

    st.graphviz_chart(g)


# ------------------------------------------------------------
# 介面元件
# ------------------------------------------------------------
def _ui_persons(tree: Dict):
    st.markdown("### ① 人物管理")
    with st.form("person_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2,1,1,1])
        name = col1.text_input("姓名 *")
        gender = col2.selectbox("性別", ["男", "女", ""])
        by = col3.number_input("出生年", min_value=0, max_value=9999, value=0, step=1)
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

def _ui_marriages(tree: Dict):
    st.markdown("### ② 婚姻與子女")

    persons = tree["persons"]
    marriages = tree["marriages"]

    # 建立婚姻
    with st.form("m_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3,3,1])
        ppl = [(p["name"], pid) for pid, p in persons.items()]
        ppl.sort()
        s1 = col1.selectbox("配偶 A", options=[""] + [pid for _, pid in ppl],
                            format_func=lambda x: "" if not x else persons[x]["name"])
        s2 = col2.selectbox("配偶 B", options=[""] + [pid for _, pid in ppl],
                            format_func=lambda x: "" if not x else persons[x]["name"])
        ok = col3.form_submit_button("＋ 建立婚姻")
        if ok:
            if not s1 or not s2 or s1 == s2:
                st.warning("請選擇兩位不同人物")
            else:
                mid = _new_mid()
                marriages[mid] = {"spouses": [s1, s2], "children": []}
                _apply_rules(tree)
                st.rerun()

    # 婚姻清單 + 加子女
    if marriages:
        for mid, m in marriages.items():
            with st.expander(f"婚姻 {mid}（點開管理）", expanded=False):
                sps = m.get("spouses", [])
                lbl = " × ".join(persons.get(p, {}).get("name", p) for p in sps)
                st.caption(lbl or "（尚未設定配偶）")

                # 加子女
                with st.form(f"kid_{mid}", clear_on_submit=True):
                    col1, col2 = st.columns([5,1])
                    candidates = [pid for pid in persons.keys()
                                  if _parents_mid_of(pid, marriages) in (None, mid)]  # 不讓一人掛多組父母
                    sel = col1.selectbox("新增子女", options=[""] + candidates,
                                         format_func=lambda x: "" if not x else persons[x]["name"])
                    ok = col2.form_submit_button("加入子女")
                    if ok:
                        if not sel:
                            st.warning("請選擇子女")
                        else:
                            if sel not in m["children"]:
                                m["children"].append(sel)
                                _apply_rules(tree, focus_child=sel)
                                st.rerun()

                # 目前子女列表
                kids = m.get("children", [])
                if kids:
                    st.write("此婚姻子女：", "、".join(persons[k]["name"] for k in kids if k in persons))
                else:
                    st.info("此婚姻目前沒有子女。")

                # 刪除婚姻
                if st.button("刪除此婚姻", key=f"del_{mid}"):
                    # 同步移除 children 的父母關係（資料模型就是從 marriages 讀孩子）
                    marriages.pop(mid, None)
                    _apply_rules(tree)
                    st.rerun()


def _ui_graph(tree: Dict):
    st.markdown("### ③ 家族樹視覺化")
    _apply_rules(tree)  # 每次重新 render 前跑一次，保持穩定
    _graph(tree)


def _ui_io(tree: Dict):
    st.markdown("### ④ 匯入 / 匯出")
    col1, col2 = st.columns([1,1])

    # 匯出
    if col1.download_button("下載 familytree.json",
                            data=json.dumps(tree, ensure_ascii=False, indent=2),
                            file_name="familytree.json",
                            mime="application/json"):
        pass

    # 匯入
    up = col2.file_uploader("選擇 JSON 檔", type=["json"])
    if up is not None:
        try:
            data = json.loads(up.read().decode("utf-8"))
            if not isinstance(data, dict):
                st.error("JSON 結構有誤")
            else:
                st.session_state.family = data
                _apply_rules(st.session_state.family)
                st.success("匯入成功！")
                st.rerun()
        except Exception as e:
            st.error(f"匯入失敗：{e}")


# ------------------------------------------------------------
# 主程式
# ------------------------------------------------------------
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


if __name__ == "__main__":
    main()

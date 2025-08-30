# -*- coding: utf-8 -*-
import json
from collections import deque, defaultdict

import streamlit as st
from graphviz import Digraph


# =========================================================
# 0) 狀態與小工具
# =========================================================
def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    if "pid_counter" not in st.session_state:
        st.session_state.pid_counter = 1
    if "mid_counter" not in st.session_state:
        st.session_state.mid_counter = 1
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}
    if "group_order" not in st.session_state:
        st.session_state.group_order = {}


def _next_pid():
    st.session_state.pid_counter += 1
    return f"P{st.session_state.pid_counter:03d}"


def _next_mid():
    st.session_state.mid_counter += 1
    return f"M{st.session_state.mid_counter:03d}"


def _year(person):
    try:
        v = person.get("birth", "")
        return int(str(v).strip()[:4]) if v else None
    except Exception:
        return None


def _base_key(pid, persons):
    y = _year(persons.get(pid, {}))
    return (y is None, y if y is not None else 9999, persons.get(pid, {}).get("name", ""))


# =========================================================
# 1) 分層（配偶同層；子女下一層；反覆鬆弛）
# =========================================================
def _compute_generations(tree):
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    children_of = {pid: set() for pid in persons}
    indeg = {pid: 0 for pid in persons}
    for m in marriages.values():
        sps = [s for s in (m.get("spouses", []) or []) if s in persons]
        kids = [c for c in (m.get("children", []) or []) if c in persons]
        for s in sps:
            for c in kids:
                if c not in children_of[s]:
                    children_of[s].add(c)
                    indeg[c] += 1

    depth = {pid: 0 for pid in persons}
    q = deque([p for p in persons if indeg.get(p, 0) == 0]) or deque(persons.keys())
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            if depth[v] < depth[u] + 1:
                depth[v] = depth[u] + 1
            indeg[v] -= 1
            if indeg[v] <= 0:
                q.append(v)

    # marriage leveling & parent->child
    changed = True
    guard = 0
    while changed and guard < 200:
        changed = False
        guard += 1
        for m in marriages.values():
            sps = [s for s in (m.get("spouses", []) or []) if s in persons]
            kids = [c for c in (m.get("children", []) or []) if c in persons]
            if sps:
                dmax = max(depth[s] for s in sps)
                for s in sps:
                    if depth[s] < dmax:
                        depth[s] = dmax
                        changed = True
            else:
                dmax = 0
            for c in kids:
                need = dmax + 1
                if depth[c] < need:
                    depth[c] = need
                    changed = True
    return depth


# =========================================================
# 2) 排序：手足群、夫妻區塊（block），穩定插入
# =========================================================
def _parents_mid_of(pid, marriages):
    for mid, m in marriages.items():
        if pid in (m.get("children", []) or []):
            return mid
    return None


def _cluster_id_of(pid, d, marriages):
    """第 d 層的群 ID：有父母→mid；否則→orph:pid。"""
    pmid = _parents_mid_of(pid, marriages)
    return pmid if (pmid is not None and d > 0) else f"orph:{pid}"


def _spouses_of(pid, marriages):
    seen, res = set(), []
    for m in marriages.values():
        sps = m.get("spouses", []) or []
        if pid in sps:
            for s in sps:
                if s != pid and s not in seen:
                    seen.add(s)
                    res.append(s)
    return res


def _move_to_front(lst, x):
    if x in lst:
        lst.remove(x)
        lst.insert(0, x)


def _move_to_back(lst, x):
    if x in lst:
        lst.remove(x)
        lst.append(x)


def _ensure_adjacent_inside(lst, a, b):
    """讓 a、b 在同一 list 內相鄰（盡量不動其它人）。"""
    if a not in lst or b not in lst:
        return
    ia, ib = lst.index(a), lst.index(b)
    if abs(ia - ib) == 1:
        return
    lst.pop(ib)
    ia = lst.index(a)
    lst.insert(ia + 1, b)


def _is_orphan_cluster(cid: str) -> bool:
    # "M..." 是父母婚姻群；其他像 "orph:Pxxx" 都是孤兒群
    return not str(cid).startswith("M")


def _stable_cluster_order(d, clusters, marriages, persons):
    """以上一輪層序為基底，只插入新群（穩定）。"""
    prior = st.session_state.gen_order.get(str(d), [])
    seen, base = set(), []
    for pid in prior:
        cid = _cluster_id_of(pid, d, marriages)
        if cid in clusters and cid not in seen:
            base.append(cid)
            seen.add(cid)

    now_ids = list(clusters.keys())
    existing = set(base)

    parent_pos = {p: i for i, p in enumerate(st.session_state.gen_order.get(str(d - 1), []))}

    def anchor(cid):
        if not str(cid).startswith("M"):
            return float("inf")
        m = marriages.get(cid)
        if not m:
            return float("inf")
        pts = [parent_pos.get(s) for s in (m.get("spouses", []) or [])
               if parent_pos.get(s) is not None]
        return sum(pts) / len(pts) if pts else float("inf")

    new_ids = [cid for cid in now_ids if cid not in existing]
    new_ids.sort(key=lambda cid: anchor(cid))
    for nid in new_ids:
        a = anchor(nid)
        placed = False
        for i, cid in enumerate(base):
            if anchor(cid) >= a:
                base.insert(i, nid)
                placed = True
                break
        if not placed:
            base.append(nid)

    if not prior:
        base = sorted(now_ids, key=lambda cid: (anchor(cid), cid))
    return base


def _build_couple_blocks(d, base_cluster_order, marriages, depth):
    """
    將同一層 d 的『跨群婚姻』連結成不可分割區塊（connected components）。
    回傳 blocks：list[list[cid]]，內部群序沿用 base_cluster_order，避免晃動。
    """
    order_index = {cid: i for i, cid in enumerate(base_cluster_order)}
    adj = {cid: set() for cid in base_cluster_order}

    # 以婚姻把群連起來（只有同層配偶才連）
    for m in marriages.values():
        sps = [s for s in (m.get("spouses", []) or []) if depth.get(s) == d]
        if len(sps) >= 2:
            a, b = sps[0], sps[1]
            ca = _cluster_id_of(a, d, marriages)
            cb = _cluster_id_of(b, d, marriages)
            if ca in adj and cb in adj and ca != cb:
                adj[ca].add(cb)
                adj[cb].add(ca)

    # 依 base_cluster_order 做 DFS，形成穩定區塊順序
    seen, blocks = set(), []
    for cid in base_cluster_order:
        if cid in seen:
            continue
        comp, stack = [], [cid]
        seen.add(cid)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comp.sort(key=lambda x: order_index[x])  # 區塊內群順序沿用 base
        blocks.append(comp)
    return blocks


def _apply_rules(tree, focus_child=None):
    """
    層內策略（符合你的三原則）：
    1) 同父母子女成群；群內配偶相鄰。
    2) 跨群婚姻→把相關群結成『夫妻區塊』（block），排序與位移皆以區塊為單位，避免拆散配偶。
    3) 新增子女若其配偶存在於另一群，兩群自然被連成同一區塊，夫妻相鄰。
    """
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth = _compute_generations(tree)

    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order = {}
    maxd = max(layers.keys()) if layers else 0

    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))

        # 先把每個人分到『群』（同父母群／孤兒群）
        clusters = {}
        for p in members:
            cid = _cluster_id_of(p, d, marriages)
            clusters.setdefault(cid, []).append(p)

        # 群內：配偶相鄰
        for cid, lst in clusters.items():
            lst.sort(key=lambda x: _base_key(x, persons))
            for m in marriages.values():
                sps = [s for s in (m.get("spouses", []) or [])
                       if s in lst and depth.get(s) == d]
                if len(sps) >= 2:
                    _ensure_adjacent_inside(lst, sps[0], sps[1])

        # 群序（穩定插入）
        base_cluster_order = _stable_cluster_order(d, clusters, marriages, persons)

        # 把跨群婚姻合併為『夫妻區塊』
        blocks = _build_couple_blocks(d, base_cluster_order, marriages, depth)

        # 邊界微調：跨群夫妻各自站在區塊交界兩側（左群→右緣；右群→左緣）
        cid_pos = {cid: i for i, cid in enumerate(base_cluster_order)}
        for m in marriages.values():
            sps = [s for s in (m.get("spouses", []) or []) if depth.get(s) == d]
            if len(sps) < 2:
                continue
            a, b = sps[0], sps[1]
            ca = _cluster_id_of(a, d, marriages)
            cb = _cluster_id_of(b, d, marriages)
            if ca == cb or ca not in clusters or cb not in clusters:
                continue
            if cid_pos[ca] < cid_pos[cb]:
                _move_to_back(clusters[ca], a)
                _move_to_front(clusters[cb], b)
            else:
                _move_to_back(clusters[cb], b)
                _move_to_front(clusters[ca], a)

        # 將『夫妻區塊』展開為最終層序（區塊為單位，不會拆散配偶）
        final_list = []
        for comp in blocks:
            for cid in comp:
                final_list.extend(clusters[cid])
        gen_order[str(d)] = final_list

    # group_order（供需要時以層序 anchor 婚姻）
    group_order = {}
    for d, order in gen_order.items():
        d_int = int(d)
        pos = {p: i for i, p in enumerate(order)}
        mids = []
        for mid, m in tree.get("marriages", {}).items():
            sps = m.get("spouses", []) or []
            anchor = None
            for s in sps:
                if depth.get(s) == d_int:
                    anchor = s
                    break
            if anchor is None and sps:
                anchor = sps[0]
            if anchor in pos:
                mids.append((pos[anchor], mid))
        if mids:
            mids.sort()
            group_order[str(d_int)] = [mid for _, mid in mids]

    st.session_state.gen_order = gen_order
    st.session_state.group_order = group_order
    return gen_order, group_order


# =========================================================
# 3) 視覺化（婚姻點居中，子女從婚姻點往下）
# =========================================================
def _graph(tree):
    depth = _compute_generations(tree)
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    if not st.session_state.get("gen_order"):
        _apply_rules(tree)

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", splines="polyline", nodesep="0.25", ranksep="0.9")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="white",
           fontname="Noto Sans CJK TC", fontsize="11")
    g.attr("edge", fontname="Noto Sans CJK TC", fontsize="10")

    # 人物節點
    for pid, p in persons.items():
        nm = p.get("name", pid)
        by = p.get("birth", "")
        label = nm + (f"\n{by}" if by else "")
        g.node(pid, label=label)

    # 層內節點
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    per_layer_order = {}
    for d, nodes in layers.items():
        seq = st.session_state.gen_order.get(str(d))
        if seq:
            per_layer = [p for p in seq if p in nodes] + [p for p in nodes if p not in seq]
        else:
            per_layer = sorted(nodes, key=lambda x: _base_key(x, persons))
        per_layer_order[d] = per_layer

    # 婚姻點 + 夫妻水平線 + 子女
    for mid, m in marriages.items():
        sps = m.get("spouses", []) or []
        kids = m.get("children", []) or []

        s_same = [s for s in sps if s in persons]
        left_sp = right_sp = None
        if len(s_same) >= 2:
            d = depth.get(s_same[0], 0)
            order = per_layer_order.get(d, s_same)
            pos = {p: i for i, p in enumerate(order)}
            s_sorted = sorted(s_same, key=lambda x: pos.get(x, 10**9))
            left_sp, right_sp = s_sorted[0], s_sorted[1]
        elif len(s_same) == 1:
            left_sp = right_sp = s_same[0]

        with g.subgraph() as sg:
            sg.attr(rank="same")
            sg.node(mid, shape="point", width="0.01", height="0.01", label="")
            if left_sp and right_sp:
                sg.edge(left_sp, mid, dir="none", tailport="e",
                        constraint="true", weight="300", minlen="0", penwidth="1.2")
                sg.edge(mid, right_sp, dir="none", headport="w",
                        constraint="true", weight="300", minlen="0", penwidth="1.2")
            elif left_sp:
                sg.edge(left_sp, mid, dir="none", tailport="e",
                        constraint="true", weight="300", minlen="0", penwidth="1.2")

        if kids:
            anchor = f"{mid}_anchor"
            g.node(anchor, shape="point", width="0.01", height="0.01", label="", style="invis")
            g.edge(mid, anchor, style="invis", weight="150", minlen="1", constraint="true")

            if len(kids) >= 2:
                with g.subgraph() as kg:
                    kg.attr(rank="same")
                    for i in range(len(kids) - 1):
                        kg.edge(kids[i], kids[i + 1], style="invis", weight="60", constraint="true")

            for c in kids:
                g.edge(anchor, c, style="invis", weight="120", minlen="1", constraint="true")
                g.edge(mid, c, weight="3", minlen="1")

    # 保持同層
    for d, members in layers.items():
        with g.subgraph() as same:
            same.attr(rank="same")
            for pid in members:
                same.node(pid)

    # 用隱形線保持層內順序（避免跳動）
    for d, order in per_layer_order.items():
        if len(order) >= 2:
            with g.subgraph() as gg:
                gg.attr(rank="same")
                for i in range(len(order) - 1):
                    gg.edge(order[i], order[i + 1], style="invis", weight="220", constraint="true")

    return g


# =========================================================
# 4) UI：人物／婚姻（每筆婚姻一個 form，提交更穩定）
# =========================================================
def _person_form(t):
    st.subheader("① 人物管理")
    with st.form("add_person", clear_on_submit=True):
        c = st.columns(4)
        name = c[0].text_input("姓名 *")
        gender = c[1].selectbox("性別", ["", "男", "女"], index=0)
        birth = c[2].text_input("出生年（可留空）")
        ok = c[3].form_submit_button("新增人物")
        if ok:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _next_pid()
                t["persons"][pid] = {"name": name.strip()}
                if gender:
                    t["persons"][pid]["gender"] = gender
                if birth.strip():
                    t["persons"][pid]["birth"] = birth.strip()
                st.success(f"已新增：{pid}｜{name}")

    if t["persons"]:
        with st.expander("人物清單（點開管理）", expanded=False):
            for pid, p in t["persons"].items():
                cc = st.columns([5, 2, 1, 1])
                cc[0].write(f"{pid}｜{p.get('name','')}")
                cc[1].write(p.get("birth", ""))
                if cc[2].button("刪除", key=f"del_p_{pid}"):
                    for m in t["marriages"].values():
                        m["spouses"] = [x for x in m.get("spouses", []) if x != pid]
                        m["children"] = [x for x in m.get("children", []) if x != pid]
                    del t["persons"][pid]
                    _apply_rules(t)
                    st.rerun()
                if cc[3].button("改名", key=f"ren_{pid}"):
                    st.session_state[f"ren_{pid}"] = True
                if st.session_state.get(f"ren_{pid}"):
                    new = st.text_input("新姓名", value=p.get("name", ""), key=f"in_{pid}")
                    if st.button("確定", key=f"ok_{pid}"):
                        t["persons"][pid]["name"] = new.strip()
                        st.session_state[f"ren_{pid}"] = False
                        st.rerun()


def _marriage_form(t):
    st.subheader("② 婚姻關係")

    # 新增婚姻（單獨一個表單）
    with st.form("add_marriage", clear_on_submit=True):
        c = st.columns(4)
        s1 = c[0].selectbox(
            "配偶 A",
            [""] + list(t["persons"].keys()),
            format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "",
        )
        s2 = c[1].selectbox(
            "配偶 B",
            [""] + list(t["persons"].keys()),
            format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "",
        )
        ok = c[3].form_submit_button("新增婚姻")
        if ok:
            if not s1 or not s2 or s1 == s2:
                st.warning("請選兩位不同人物")
            else:
                mid = _next_mid()
                t["marriages"][mid] = {"spouses": [s1, s2], "children": []}
                _apply_rules(t)
                st.success(f"已新增婚姻：{mid}（已自動把配偶排為相鄰）")
                st.rerun()

    # 管理婚姻（每一筆各自 form → 修正『加入子女沒反應』）
    if t["marriages"]:
        with st.expander("婚姻清單（點開管理）", expanded=False):

            def _who_is_parent_of(child_pid):
                for mmid, mm in t["marriages"].items():
                    if child_pid in (mm.get("children") or []):
                        return mmid
                return None

            for mid, m in t["marriages"].items():
                sps = m.get("spouses", [])
                kids = m.get("children", [])
                title = " × ".join([t["persons"].get(s, {}).get("name", s) for s in sps]) or "（未登記配偶）"
                st.markdown(f"**{mid}**｜{title}｜子女 {len(kids)}")

                with st.form(f"mar_{mid}", clear_on_submit=True):
                    c = st.columns([5, 3, 2, 2])
                    kid = c[0].selectbox(
                        "新增子女",
                        [""] + list(t["persons"].keys()),
                        format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "",
                        key=f"k_{mid}",
                    )
                    add_btn = c[1].form_submit_button("加入子女")
                    clr_btn = c[2].form_submit_button("清空子女")
                    del_btn = c[3].form_submit_button("刪除此婚姻")

                if add_btn:
                    if not kid:
                        st.warning("請先選擇要加入的子女")
                    else:
                        exists_mid = _who_is_parent_of(kid)
                        if exists_mid and exists_mid != mid:
                            nm = t["persons"].get(kid, {}).get("name", kid)
                            st.warning(f"「{nm}」已是 {exists_mid} 的子女，無法同時屬於兩組父母。")
                        else:
                            if kid not in m.setdefault("children", []):
                                m["children"].append(kid)
                                _apply_rules(t, focus_child=kid)
                                st.success("已加入子女")
                                st.rerun()
                            else:
                                st.info("此人已在此婚姻的子女清單中。")

                if clr_btn:
                    m["children"] = []
                    _apply_rules(t)
                    st.success("已清空子女")
                    st.rerun()

                if del_btn:
                    del t["marriages"][mid]
                    _apply_rules(t)
                    st.success("已刪除此婚姻")
                    st.rerun()


# =========================================================
# 5) 視覺化 & 匯入/匯出
# =========================================================
def _ui_visualize(t):
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))


def _ui_import_export(t):
    with st.expander("④ 匯入 / 匯出", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "下載 familytree.json",
                data=json.dumps(t, ensure_ascii=False, indent=2),
                file_name="familytree.json",
                mime="application/json",
            )
        with c2:
            with st.form("import_form", clear_on_submit=True):
                file = st.file_uploader("選擇 JSON 檔", type=["json"])
                submitted = st.form_submit_button("套用匯入")
                if submitted:
                    if not file:
                        st.warning("請先選擇檔案")
                    else:
                        try:
                            data = json.loads(file.getvalue().decode("utf-8"))
                            if isinstance(data, dict) and "persons" in data and "marriages" in data:
                                st.session_state.tree = data
                                _apply_rules(st.session_state.tree)
                                st.success("匯入成功")
                                st.rerun()
                            else:
                                st.warning("JSON 結構需包含 persons / marriages")
                        except Exception as e:
                            st.error(f"匯入失敗：{e}")

        with st.expander("⚠️ 清空所有資料", expanded=False):
            if st.button("我確定要清空（不可復原）"):
                st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
                st.session_state.gen_order = {}
                st.session_state.group_order = {}
                st.success("已清空")
                st.rerun()


# =========================================================
# 6) 入口
# =========================================================
def render():
    _init_state()
    st.set_page_config(page_title="家族樹", layout="wide")
    st.title("家族樹")

    t = st.session_state.tree
    _person_form(t)
    _marriage_form(t)
    _ui_visualize(t)
    _ui_import_export(t)

    st.caption("familytree • couple-block layout v1")


if __name__ == "__main__":
    render()

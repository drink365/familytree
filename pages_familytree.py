# -*- coding: utf-8 -*-
import streamlit as st
import json
from collections import deque
from graphviz import Digraph

# -------------------- 狀態初始化 --------------------
def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}
    if "group_order" not in st.session_state:
        st.session_state.group_order = {}
    for k in ("pid_counter", "mid_counter"):
        if k not in st.session_state:
            st.session_state[k] = 1

def _next_pid():
    st.session_state.pid_counter += 1
    return f"P{st.session_state.pid_counter:03d}"

def _next_mid():
    st.session_state.mid_counter += 1
    return f"M{st.session_state.mid_counter:03d}"

# -------------------- 世代計算（拓撲法，穩定三層） --------------------
def _compute_generations(tree):
    """
    分層規則：
    1) 父/母 → 子：子女層級 >= 父母層級 + 1
    2) 同一段婚姻的配偶：層級相同（取配偶們的最大層級）
    以上兩個約束反覆鬆弛直到收斂，確保「沒有父母資料的配偶」會提升到與其配偶同層。
    """
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # 先用父→子邊做一次拓撲式傳播（給初值）
    children_of = {pid: set() for pid in persons}
    indeg = {pid: 0 for pid in persons}
    for m in marriages.values():
        sps = [s for s in m.get("spouses", []) if s in persons]
        kids = [c for c in m.get("children", []) if c in persons]
        for s in sps:
            for c in kids:
                if c not in children_of[s]:
                    children_of[s].add(c)
                    indeg[c] += 1

    from collections import deque
    depth = {pid: 0 for pid in persons}
    q = deque([p for p in persons if indeg.get(p, 0) == 0])
    if not q and persons:
        q = deque(list(persons.keys()))  # 保底

    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            if depth[v] < depth[u] + 1:
                depth[v] = depth[u] + 1
            indeg[v] -= 1
            if indeg[v] <= 0:
                q.append(v)

    # 加入「配偶同層」與「父母→子」的反覆鬆弛，直到穩定
    changed = True
    guard = 0
    while changed and guard < 200:
        changed = False
        guard += 1
        for m in marriages.values():
            sps = [s for s in m.get("spouses", []) if s in persons]
            kids = [c for c in m.get("children", []) if c in persons]

            # (A) 讓配偶同層：提升較低者到配偶們的最大層級
            if sps:
                d = max(depth[s] for s in sps)
                for s in sps:
                    if depth[s] < d:
                        depth[s] = d
                        changed = True
            else:
                d = None

            # (B) 再推子女：子女層級 >= 父母最大層級 + 1
            if kids:
                parent_depth = d if d is not None else max((depth.get(p, 0) for p in sps), default=0)
                for c in kids:
                    need = parent_depth + 1
                    if depth[c] < need:
                        depth[c] = need
                        changed = True

    return depth

# -------------------- 自動排版啟發式（Sugiyama/Barycenter 風格） --------------------
def _birth_year(p):
    try:
        v = p.get("birth", "")
        return int(str(v).strip()[:4]) if v else None
    except Exception:
        return None

def _barycenter_order(nodes, pos_ref, tie_key=None):
    """依鄰居平均位置（barycenter）排序，沒有鄰居的視為無限大（排後面）。"""
    bc = []
    for i, n in enumerate(nodes):
        neigh_pos = [pos_ref.get(v) for v in pos_ref.get("__adj__", {}).get(n, []) if v in pos_ref]
        score = sum(neigh_pos) / len(neigh_pos) if neigh_pos else float("inf")
        bc.append((score, tie_key(n) if tie_key else None, i, n))
    bc.sort(key=lambda x: (x[0], x[1] if x[1] is not None else 0, x[2]))
    return [n for *_, n in bc]

def _auto_layout(tree, preserve_spouse=True, sort_children_by_birth=True, sweeps=3):
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth = _compute_generations(tree)

    # (0) 子女依出生年排序（可選）
    if sort_children_by_birth:
        for m in marriages.values():
            kids = list(m.get("children", []))
            kids.sort(
                key=lambda k: (
                    _birth_year(persons.get(k, {})) is None,
                    _birth_year(persons.get(k, {})) or 9999,
                    persons.get(k, {}).get("name", ""),
                )
            )
            m["children"] = kids

    # (1) 配偶排序（若不保留，依出生年）
    if not preserve_spouse:
        for m in marriages.values():
            sps = list(m.get("spouses", []))
            sps.sort(
                key=lambda s: (
                    _birth_year(persons.get(s, {})) is None,
                    _birth_year(persons.get(s, {})) or 9999,
                    persons.get(s, {}).get("name", ""),
                )
            )
            m["spouses"] = sps

    # (2) 初始每層排序（出生年、姓名）
    layers = {}
    for pid in persons:
        d = depth.get(pid, 0)
        layers.setdefault(d, []).append(pid)
    gen_order = {}
    for d, nodes in layers.items():
        def tie(n):
            by = _birth_year(persons.get(n, {})) or 9999
            return (by, persons.get(n, {}).get("name", ""))
        gen_order[str(d)] = sorted(nodes, key=tie)

    # (3) 建 adjacency：父母<->子女（跨層）
    adj = {}
    for pid in persons:
        nbrs = set()
        for m in marriages.values():
            if pid in m.get("spouses", []):
                for c in m.get("children", []):
                    nbrs.add(c)
            if pid in m.get("children", []):
                for s in m.get("spouses", []):
                    nbrs.add(s)
        adj[pid] = list(nbrs)

    # (4) 多輪 barycenter
    maxd = max(layers.keys()) if layers else 0
    for _ in range(sweeps):
        # top-down
        for d in range(1, maxd + 1):
            prev = gen_order[str(d - 1)]
            prev_pos = {pid: i for i, pid in enumerate(prev)}
            prev_pos["__adj__"] = adj
            cur = gen_order[str(d)]
            gen_order[str(d)] = _barycenter_order(
                cur,
                prev_pos,
                tie_key=lambda n: (_birth_year(persons.get(n, {})) or 9999, persons.get(n, {}).get("name", "")),
            )
        # bottom-up
        for d in range(maxd - 1, -1, -1):
            nxt = gen_order.get(str(d + 1), [])
            nxt_pos = {pid: i for i, pid in enumerate(nxt)}
            nxt_pos["__adj__"] = adj
            cur = gen_order[str(d)]
            gen_order[str(d)] = _barycenter_order(
                cur,
                nxt_pos,
                tie_key=lambda n: (_birth_year(persons.get(n, {})) or 9999, persons.get(n, {}).get("name", "")),
            )

    # (5) 夫妻群排序（以該層錨點位置從左到右）
    group_order = {}
    for d, nodes in layers.items():
        ord_nodes = gen_order[str(d)]
        posmap = {pid: i for i, pid in enumerate(ord_nodes)}
        anchors = []
        for mid, m in marriages.items():
            sps = m.get("spouses", [])
            anchor = None
            for s in sps:
                if depth.get(s) == d:
                    anchor = s
                    break
            if anchor is not None:
                anchors.append((posmap.get(anchor, 10 ** 9), mid))
        anchors.sort()
        group_order[str(d)] = [mid for _, mid in anchors]

    return gen_order, group_order, tree

# -------------------- Graphviz 繪圖（婚姻點與配偶同層、子女下一層） --------------------
def _graph(tree):
    depth = _compute_generations(tree)
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", splines="polyline", nodesep="0.25", ranksep="0.8")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="white",
           fontname="Noto Sans CJK TC", fontsize="11")
    g.attr("edge", fontname="Noto Sans CJK TC", fontsize="10")

    # 人物節點
    for pid, p in persons.items():
        nm = p.get("name", pid)
        by = p.get("birth", "")
        label = nm + (f"\n{by}" if by else "")
        g.node(pid, label=label)

    # 婚姻節點與連線
    for mid, m in marriages.items():
        spouses = m.get("spouses", []) or []
        children = m.get("children", []) or []

        # 夫妻與婚姻點「同一層」
        with g.subgraph() as sg:
            sg.attr(rank="same")
            sg.node(mid, shape="point", width="0.01", height="0.01", label="")
            if len(spouses) >= 2:
                for i in range(len(spouses) - 1):
                    sg.edge(spouses[i], spouses[i + 1],
                            style="invis", weight="150", constraint="true")
            for s in spouses:
                # 不影響垂直分層
                sg.edge(s, mid, dir="none", weight="5", constraint="false")
            if len(spouses) == 2:
                s1, s2 = spouses[0], spouses[1]
                sg.edge(s1, s2, style="invis", weight="200", constraint="true")

        # 婚姻 → 子女（決定下一層）
        if len(children) >= 2:
            with g.subgraph() as kg:
                kg.attr(rank="same")
                for i in range(len(children) - 1):
                    kg.edge(children[i], children[i + 1],
                            style="invis", weight="60", constraint="true")
        for c in children:
            g.edge(mid, c, weight="3", minlen="1")

    # ---- 強制分層（依演算法算出的世代）----
    levels = sorted(set(depth.values()))
    for d in levels:
        members = [pid for pid, lv in depth.items() if lv == d]
        if members:
            with g.subgraph() as same:
                same.attr(rank="same")
                for pid in members:
                    same.node(pid)

    # ---- 全域同層排序（②-2） ----
    gen_order = st.session_state.get("gen_order", {}) if hasattr(st, "session_state") else {}
    if gen_order:
        gens = {}
        for pid, d in depth.items():
            gens.setdefault(d, []).append(pid)
        for d, people in gens.items():
            seq = [p for p in gen_order.get(str(d), []) if p in people] + \
                  [p for p in people if p not in gen_order.get(str(d), [])]
            if len(seq) >= 2:
                with g.subgraph() as gg:
                    gg.attr(rank="same")
                    for i in range(len(seq) - 1):
                        gg.edge(seq[i], seq[i + 1],
                                style="invis", weight="80", constraint="true")

    # ---- 夫妻群排序（②-3） ----
    group_order = st.session_state.get("group_order", {}) if hasattr(st, "session_state") else {}
    if group_order:
        for d_str, mids in group_order.items():
            try:
                d = int(d_str)
            except Exception:
                continue
            mids_valid = [mid for mid in mids if mid in marriages]
            anchors = []
            for mid in mids_valid:
                sps = marriages.get(mid, {}).get("spouses", [])
                anchor = None
                for s in sps:
                    if depth.get(s) == d:
                        anchor = s
                        break
                if anchor is None and sps:
                    anchor = sps[0]
                if anchor is not None and anchor in persons:
                    anchors.append(anchor)
            if len(anchors) >= 2:
                with g.subgraph() as grp:
                    grp.attr(rank="same")
                    for i in range(len(anchors) - 1):
                        grp.edge(anchors[i], anchors[i + 1],
                                 style="invis", weight="90", constraint="true")

    return g

# -------------------- UI：人物與婚姻 --------------------
def _person_form(t):
    st.subheader("① 人物資料")
    with st.form("add_person", clear_on_submit=True):
        cols = st.columns(4)
        name = cols[0].text_input("姓名")
        birth = cols[1].text_input("出生年（可留空）")
        pid_hint = cols[2].text_input("自訂人物代號（可留空）")
        sub = cols[3].form_submit_button("新增人物")
        if sub:
            if not name:
                st.warning("請輸入姓名")
            else:
                pid = pid_hint.strip() or _next_pid()
                t["persons"][pid] = {"name": name.strip()}
                if birth.strip():
                    t["persons"][pid]["birth"] = birth.strip()
                st.success(f"已新增人物：{pid}｜{name}")

    if t["persons"]:
        with st.expander("人物清單（點開檢視）", expanded=False):
            for pid, p in t["persons"].items():
                cols = st.columns([4, 2, 1, 1])
                cols[0].write(f"{pid}｜{p.get('name','')}")
                cols[1].write(p.get("birth", ""))
                if cols[2].button("刪除", key=f"del_p_{pid}"):
                    for mid in list(t["marriages"].keys()):
                        m = t["marriages"][mid]
                        if pid in m.get("spouses", []):
                            m["spouses"] = [x for x in m.get("spouses", []) if x != pid]
                        if pid in m.get("children", []):
                            m["children"] = [x for x in m.get("children", []) if x != pid]
                    del t["persons"][pid]
                    st.rerun()
                if cols[3].button("改名", key=f"rename_{pid}"):
                    st.session_state[f"edit_name_{pid}"] = True
                if st.session_state.get(f"edit_name_{pid}"):
                    newname = st.text_input(f"{pid} 新姓名", value=p.get("name", ""), key=f"in_name_{pid}")
                    if st.button("確定修改", key=f"ok_name_{pid}"):
                        t["persons"][pid]["name"] = newname.strip()
                        st.session_state[f"edit_name_{pid}"] = False
                        st.rerun()

def _marriage_form(t):
    st.subheader("② 婚姻關係")
    with st.form("add_marriage", clear_on_submit=True):
        cols = st.columns(4)
        s1 = cols[0].selectbox("配偶 A", [""] + list(t["persons"].keys()),
                               format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "")
        s2 = cols[1].selectbox("配偶 B", [""] + list(t["persons"].keys()),
                               format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "")
        mid_hint = cols[2].text_input("自訂婚姻代號（可留空）")
        ok = cols[3].form_submit_button("新增婚姻")
        if ok:
            if not s1 or not s2 or s1 == s2:
                st.warning("請選擇兩位不同的人物作為配偶")
            else:
                mid = mid_hint.strip() or _next_mid()
                t["marriages"][mid] = {"spouses": [s1, s2], "children": []}
                st.success(f"已新增婚姻：{mid}｜{t['persons'][s1]['name']} × {t['persons'][s2]['name']}")

    if t["marriages"]:
        with st.expander("婚姻清單（點開管理）", expanded=False):
            for mid, m in t["marriages"].items():
                sps = m.get("spouses", []) or []
                kids = m.get("children", []) or []

                # 標題：婚姻ID｜配偶姓名 × 配偶姓名｜子女N名
                names = [t["persons"].get(s, {}).get("name", s) for s in sps]
                title = f"**{mid}** ｜ " + (" × ".join(names) if names else "（未登記配偶）")
                if kids:
                    title += f"｜子女{len(kids)}名"
                st.markdown(title)

                # 增加子女
                cols = st.columns([5, 4, 3])
                kid = cols[0].selectbox("選擇子女", [""] + list(t["persons"].keys()),
                                        format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "",
                                        key=f"kid_{mid}")
                addk = cols[1].button("新增子女", key=f"addk_{mid}")
                clear = cols[2].button("清空子女", key=f"clr_{mid}")
                if addk and kid:
                    if kid not in m["children"]:
                        m["children"].append(kid)
                        st.success("已新增子女")
                        st.rerun()
                if clear and st.checkbox(f"我確定要清空 {mid} 的子女", key=f"cf_{mid}"):
                    m["children"] = []
                    st.rerun()

                # 離婚註記 + 配偶排序
                div_ck = st.checkbox("該婚姻已離婚？", value=bool(m.get("divorced")), key=f"div_{mid}")
                t["marriages"][mid]["divorced"] = bool(div_ck)

                st.markdown("**配偶順序（可調整）**")
                if len(sps) <= 1:
                    st.info("此婚姻目前只有一位配偶。")
                else:
                    for i, sid in enumerate(sps):
                        c = st.columns([6, 1, 1, 1, 1])
                        c[0].write(f"{i+1}. {sid}｜" + t["persons"].get(sid, {}).get("name", "?"))
                        if c[1].button("↑", key=f"sp_up_{mid}_{sid}") and i > 0:
                            sps[i - 1], sps[i] = sps[i], sps[i - 1]
                            t["marriages"][mid]["spouses"] = sps
                            st.rerun()
                        if c[2].button("↓", key=f"sp_dn_{mid}_{sid}") and i < len(sps) - 1:
                            sps[i + 1], sps[i] = sps[i], sps[i + 1]
                            t["marriages"][mid]["spouses"] = sps
                            st.rerun()
                        if c[3].button("置頂", key=f"sp_top_{mid}_{sid}") and i > 0:
                            moved = sps.pop(i)
                            sps.insert(0, moved)
                            t["marriages"][mid]["spouses"] = sps
                            st.rerun()
                        if c[4].button("置底", key=f"sp_bot_{mid}_{sid}") and i < len(sps) - 1:
                            moved = sps.pop(i)
                            sps.append(moved)
                            t["marriages"][mid]["spouses"] = sps
                            st.rerun()

                # （可選）當下這段婚姻的子女排序
                if len(kids) >= 2:
                    st.caption("子女順序（此婚姻）")
                    for i, kid in enumerate(kids):
                        nm = t["persons"].get(kid, {}).get("name", kid)
                        r = st.columns([6, 1, 1, 1, 1])
                        r[0].write(f"{i+1}. {kid}｜{nm}")
                        if r[1].button("↑", key=f"mid_up_{mid}_{kid}") and i > 0:
                            kids[i - 1], kids[i] = kids[i], kids[i - 1]
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if r[2].button("↓", key=f"mid_dn_{mid}_{kid}") and i < len(kids) - 1:
                            kids[i + 1], kids[i] = kids[i], kids[i + 1]
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if r[3].button("置頂", key=f"mid_top_{mid}_{kid}") and i > 0:
                            moved = kids.pop(i)
                            kids.insert(0, moved)
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if r[4].button("置底", key=f"mid_bot_{mid}_{kid}") and i < len(kids) - 1:
                            moved = kids.pop(i)
                            kids.append(moved)
                            t["marriages"][mid]["children"] = kids
                            st.rerun()

                st.divider()

# -------------------- UI：排序工具 --------------------
def _ui_children_reorder_global(t):
    with st.expander("②-1 子女排序（每段婚姻的局部排序）", expanded=False):
        marriages = t.get("marriages", {})
        if not marriages:
            st.info("目前沒有婚姻資料。")
            return
        candidates = [mid for mid, m in marriages.items() if len(m.get("children", [])) >= 2]
        if not candidates:
            st.info("目前沒有需要排序的子女（每段婚姻的子女少於 2 位）。")
            return

        def _fmt(mid):
            sps = marriages[mid].get("spouses", [])
            names = [t["persons"].get(s, {}).get("name", s) for s in sps]
            return f"{mid}｜" + (" × ".join(names) if names else "（未登記配偶）")

        mid_sel = st.selectbox("選擇婚姻", candidates, format_func=_fmt, key="kid_sort_mid")
        kids = list(marriages[mid_sel].get("children", []))
        for i, kid in enumerate(kids):
            nm = t["persons"].get(kid, {}).get("name", kid)
            cols = st.columns([6, 1, 1, 1, 1])
            cols[0].write(f"{i+1}. {kid}｜{nm}")
            if cols[1].button("↑", key=f"kid_up_{mid_sel}_{kid}") and i > 0:
                kids[i - 1], kids[i] = kids[i], kids[i - 1]
                marriages[mid_sel]["children"] = kids
                st.rerun()
            if cols[2].button("↓", key=f"kid_dn_{mid_sel}_{kid}") and i < len(kids) - 1:
                kids[i + 1], kids[i] = kids[i], kids[i + 1]
                marriages[mid_sel]["children"] = kids
                st.rerun()
            if cols[3].button("置頂", key=f"kid_top_{mid_sel}_{kid}") and i > 0:
                moved = kids.pop(i)
                kids.insert(0, moved)
                marriages[mid_sel]["children"] = kids
                st.rerun()
            if cols[4].button("置底", key=f"kid_bot_{mid_sel}_{kid}") and i < len(kids) - 1:
                moved = kids.pop(i)
                kids.append(moved)
                marriages[mid_sel]["children"] = kids
                st.rerun()
        st.caption("小提醒：兄弟姊妹維持相鄰、順序一致，有助於減少交錯。")

def _ui_same_layer_reorder(t):
    with st.expander("②-2 同層排序", expanded=False):
        depth_map = _compute_generations(t)
        if not depth_map:
            st.info("請先建立至少一個人物與關係")
            return
        gens = sorted(set(depth_map.values()))
        def _gen_label(d):
            count = sum(1 for _p in depth_map if depth_map[_p] == d)
            return f"第 {d} 層（{count} 人）"
        gen_sel = st.selectbox("選擇世代", gens, format_func=_gen_label, key="sel_gen_same_layer")
        all_in_layer = [p for p, d in depth_map.items() if d == gen_sel]
        current = list(st.session_state.gen_order.get(str(gen_sel), []))
        order = [p for p in current if p in all_in_layer] + [p for p in all_in_layer if p not in current]

        for i, pid in enumerate(order):
            nm = t["persons"].get(pid, {}).get("name", pid)
            cols = st.columns([6, 1, 1, 1, 1])
            cols[0].write(f"{i+1}. {pid}｜{nm}")
            if cols[1].button("↑", key=f"gen_up_{gen_sel}_{pid}") and i > 0:
                order[i - 1], order[i] = order[i], order[i - 1]
                st.session_state.gen_order[str(gen_sel)] = order
                st.rerun()
            if cols[2].button("↓", key=f"gen_dn_{gen_sel}_{pid}") and i < len(order) - 1:
                order[i + 1], order[i] = order[i], order[i + 1]
                st.session_state.gen_order[str(gen_sel)] = order
                st.rerun()
            if cols[3].button("置頂", key=f"gen_top_{gen_sel}_{pid}") and i > 0:
                moved = order.pop(i)
                order.insert(0, moved)
                st.session_state.gen_order[str(gen_sel)] = order
                st.rerun()
            if cols[4].button("置底", key=f"gen_bot_{gen_sel}_{pid}") and i < len(order) - 1:
                moved = order.pop(i)
                order.append(moved)
                st.session_state.gen_order[str(gen_sel)] = order
                st.rerun()

def _ui_couple_group_reorder(t):
    with st.expander("②-3 夫妻群排序（整代群組）", expanded=False):
        depth_map = _compute_generations(t)
        marriages = t.get("marriages", {})
        persons = t.get("persons", {})
        if not depth_map or not marriages:
            st.info("請先建立人物與婚姻關係")
            return
        gens = sorted(set(depth_map.values()))
        def _glabel(d):
            return f"第 {d} 層"
        gsel = st.selectbox("選擇世代（以配偶所在層為準）", gens, format_func=_glabel, key="sel_group_layer")
        mids_in_layer = []
        for mid, m in marriages.items():
            spouses = m.get("spouses", [])
            if any(depth_map.get(s) == gsel for s in spouses):
                mids_in_layer.append(mid)
        if not mids_in_layer:
            st.info("此層沒有可排序的夫妻群")
            return
        saved = list(st.session_state.group_order.get(str(gsel), []))
        order = [mid for mid in saved if mid in mids_in_layer] + [mid for mid in mids_in_layer if mid not in saved]
        def _mfmt(mid):
            sps = marriages.get(mid, {}).get("spouses", [])
            names = [persons.get(s, {}).get("name", s) for s in sps]
            kids = marriages.get(mid, {}).get("children", [])
            return f"{mid}｜" + (" × ".join(names) if names else "（未登記配偶）") + (f"｜子女{len(kids)}名" if kids else "")
        for i, mid in enumerate(order):
            cols = st.columns([7, 1, 1, 1, 1])
            cols[0].write(f"{i+1}. {_mfmt(mid)}")
            if cols[1].button("↑", key=f"grp_up_{gsel}_{mid}") and i > 0:
                order[i - 1], order[i] = order[i], order[i - 1]
                st.session_state.group_order[str(gsel)] = order
                st.rerun()
            if cols[2].button("↓", key=f"grp_dn_{gsel}_{mid}") and i < len(order) - 1:
                order[i + 1], order[i] = order[i], order[i + 1]
                st.session_state.group_order[str(gsel)] = order
                st.rerun()
            if cols[3].button("置頂", key=f"grp_top_{gsel}_{mid}") and i > 0:
                moved = order.pop(i)
                order.insert(0, moved)
                st.session_state.group_order[str(gsel)] = order
                st.rerun()
            if cols[4].button("置底", key=f"grp_bot_{gsel}_{mid}") and i < len(order) - 1:
                moved = order.pop(i)
                order.append(moved)
                st.session_state.group_order[str(gsel)] = order
                st.rerun()
        st.caption("提示：此排序會把同層的『夫妻群（以其中一位配偶為錨點）』依序排列，適合把整個家族群向左/向右移動。")

def _ui_autosuggest(t):
    with st.expander("②-0 一鍵自動建議排序", expanded=False):
        c1, c2 = st.columns(2)
        preserve_sp = c1.checkbox("保留配偶現有順序", value=True, help="取消勾選則會依出生年排序配偶（若有資料）。")
        sort_kids = c2.checkbox("子女依出生年排序", value=True)
        if st.button("⚙️ 生成建議排序並套用", type="primary"):
            gen_order, group_order, new_tree = _auto_layout(
                t, preserve_spouse=preserve_sp, sort_children_by_birth=sort_kids, sweeps=3
            )
            st.session_state.gen_order = gen_order
            st.session_state.group_order = group_order
            st.session_state.tree = new_tree
            st.success("已套用建議排序，您可再用 ②-1/②-2/②-3 做微調。")
            st.rerun()

# -------------------- 視覺化 & 匯入/匯出 --------------------
def _ui_visualize(t):
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))

def _ui_import_export(t):
    with st.expander("④ 匯入 / 匯出", expanded=False):
        c1, c2 = st.columns(2)

        # 匯出：直接下載目前狀態
        with c1:
            st.download_button(
                "下載 familytree.json",
                data=json.dumps(t, ensure_ascii=False, indent=2),
                file_name="familytree.json",
                mime="application/json",
            )

        # 匯入：選檔 → 預覽 → 按「套用匯入」才真正寫入；成功後立刻 rerun
        with c2:
            with st.form("import_form", clear_on_submit=True):
                file = st.file_uploader("選擇 JSON 檔", type=["json"], key="import_file")

                # 預覽統計（不寫入）
                if file is not None:
                    try:
                        preview = json.loads(file.getvalue().decode("utf-8"))
                        if isinstance(preview, dict):
                            pc = len(preview.get("persons", {}) or {})
                            mc = len(preview.get("marriages", {}) or {})
                            st.caption(f"預覽：人物 {pc} 位、婚姻 {mc} 筆")
                            if pc:
                                keys = list((preview.get("persons") or {}).keys())[:3]
                                names = [preview["persons"][k].get("name", k) for k in keys]
                                st.caption("樣本姓名：" + "、".join(names))
                    except Exception as e:
                        st.caption(f"無法預覽：{e}")

                submitted = st.form_submit_button("套用匯入")
                if submitted:
                    if file is None:
                        st.warning("請先選擇檔案")
                    else:
                        try:
                            data = json.loads(file.getvalue().decode("utf-8"))
                            if isinstance(data, dict) and "persons" in data and "marriages" in data:
                                st.session_state.tree = data
                                st.success("匯入成功！")
                                st.rerun()  # 立刻刷新，讓上方區塊用新資料重繪
                            else:
                                st.warning("JSON 結構不正確，需包含 persons 與 marriages。")
                        except Exception as e:
                            st.error(f"匯入失敗：{e}")

            # 只保留「清空所有資料」
            with st.expander("⚠️ 清空所有資料", expanded=False):
                if st.button("我確定要清空（不可復原）"):
                    st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
                    st.session_state.gen_order = {}
                    st.session_state.group_order = {}
                    st.success("資料已清空")
                    st.rerun()

# -------------------- 進入點 --------------------
def render():
    _init_state()
    st.title("家族樹")  # 頁面大標題
    t = st.session_state.tree

    # ① 人物 / ② 婚姻
    _person_form(t)
    _marriage_form(t)

    # ②-0 / ②-1 / ②-2 / ②-3
    _ui_autosuggest(t)
    _ui_children_reorder_global(t)
    _ui_same_layer_reorder(t)
    _ui_couple_group_reorder(t)

    # ③ / ④
    _ui_visualize(t)
    _ui_import_export(t)

    st.caption("familytree autosuggest • r8")  # 版本戳記（確認載入新檔）

if __name__ == "__main__":
    st.set_page_config(page_title="家族樹", layout="wide")
    render()

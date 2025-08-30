# -*- coding: utf-8 -*-
import streamlit as st, json
from graphviz import Digraph

# -------------------- 基礎資料結構 & 狀態 --------------------
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

# -------------------- 世代計算 --------------------
def _compute_generations(tree):
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth = {}
    # 先把有父母者標上父母層 + 1
    # 同時確保所有人都存在於 depth
    for pid in persons:
        depth.setdefault(pid, 0)
    # 多輪鬆弛：由上而下把子女層級拉高
    changed = True
    loop_guard = 0
    while changed and loop_guard < 100:
        changed = False
        loop_guard += 1
        for mid, m in marriages.items():
            sps = m.get("spouses", [])
            kids = m.get("children", [])
            # 該婚姻的父母層次取目前已知的最大層
            parent_depth = 0
            for s in sps:
                parent_depth = max(parent_depth, depth.get(s, 0))
            # 子女至少在父母層 + 1
            for c in kids:
                if depth.get(c, 0) < parent_depth + 1:
                    depth[c] = parent_depth + 1
                    changed = True
    return depth

# -------------------- 自動排版啟發式（Sugiyama / Barycenter 風格） --------------------
def _birth_year(p):
    try:
        v = p.get("birth", "")
        return int(str(v).strip()[:4]) if v else None
    except Exception:
        return None

def _barycenter_order(nodes, pos_ref, tie_key=None):
    """
    依鄰居的平均位置（barycenter）排序，減少交錯；沒有鄰居者放在後面。
    """
    bc = []
    for i, n in enumerate(nodes):
        neigh_pos = [pos_ref.get(v) for v in pos_ref.get("__adj__", {}).get(n, []) if v in pos_ref]
        score = sum(neigh_pos) / len(neigh_pos) if neigh_pos else float("inf")
        bc.append((score, tie_key(n) if tie_key else None, i, n))
    bc.sort(key=lambda x: (x[0], x[1] if x[1] is not None else 0, x[2]))
    return [n for *_, n in bc]

def _auto_layout(tree, preserve_spouse=True, sort_children_by_birth=True, sweeps=3):
    """
    回傳 (gen_order, group_order, tree)：
    - 以出生年/姓名作初始排序
    - 多輪 barycenter（由上而下、由下而上）
    - 夫妻群以錨點（該層配偶）在該層的相對位置排序
    可選：保留配偶現有左右、子女依出生年排序
    """
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth = _compute_generations(tree)

    # (0) 子女依出生年排序（可選）
    if sort_children_by_birth:
        for mid, m in marriages.items():
            kids = list(m.get("children", []))
            kids_sorted = sorted(
                kids,
                key=lambda k: (
                    _birth_year(persons.get(k, {})) is None,
                    _birth_year(persons.get(k, {})) or 9999,
                    persons.get(k, {}).get("name", ""),
                ),
            )
            m["children"] = kids_sorted

    # (1) 配偶排序（可選：若不保留，則依出生年）
    if not preserve_spouse:
        for mid, m in marriages.items():
            sps = list(m.get("spouses", []))
            sps_sorted = sorted(
                sps,
                key=lambda s: (
                    _birth_year(persons.get(s, {})) is None,
                    _birth_year(persons.get(s, {})) or 9999,
                    persons.get(s, {}).get("name", ""),
                ),
            )
            m["spouses"] = sps_sorted

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

    # (3) 建 adjacency：父母<->子女（跨層）、配偶（同層不在此）
    adj = {}
    for pid in persons:
        nbrs = set()
        for mid, m in marriages.items():
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
            nxt = gen_order[str(d + 1)] if str(d + 1) in gen_order else []
            nxt_pos = {pid: i for i, pid in enumerate(nxt)}
            nxt_pos["__adj__"] = adj
            cur = gen_order[str(d)]
            gen_order[str(d)] = _barycenter_order(
                cur,
                nxt_pos,
                tie_key=lambda n: (_birth_year(persons.get(n, {})) or 9999, persons.get(n, {}).get("name", "")),
            )

    # (5) 夫妻群排序（以該層錨點配偶在該層位置由左到右）
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

# -------------------- Graphviz 繪圖 --------------------
def _graph(tree):
    depth = _compute_generations(tree)
    persons = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", splines="polyline", nodesep="0.2", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="white", fontname="Noto Sans CJK TC", fontsize="11")
    g.attr("edge", fontname="Noto Sans CJK TC", fontsize="10")

    # 人物節點
    for pid, p in persons.items():
        nm = p.get("name", pid)
        by = p.get("birth", "")
        label = nm + (f"\\n{by}" if by else "")
        g.node(pid, label=label)

    # 婚姻節點與連線
    for mid, m in marriages.items():
        spouses = m.get("spouses", [])
        children = m.get("children", [])

        # 婚姻為一個小節點（點）當連接器
        g.node(mid, shape="point", width="0.01", height="0.01", label="")

        # 夫妻 → 婚姻
        with g.subgraph() as sg:
            sg.attr(rank="same")
            # 夫妻彼此靠近：隱形連線
            if len(spouses) >= 2:
                for i in range(len(spouses) - 1):
                    sg.edge(spouses[i], spouses[i + 1], style="invis", weight="150", constraint="true")
            for s in spouses:
                sg.edge(s, mid, dir="none", weight="5")
            # 父母節點彼此之間再加一條隱形邊，增加穩定度
            if len(spouses) == 2:
                s1, s2 = spouses[0], spouses[1]
                sg.edge(s1, s2, style="invis", weight="200")

        # 子女 ← 婚姻
        # 兄弟姊妹彼此之間的隱形排序（維持一束，減少交錯）
        if len(children) >= 2:
            with g.subgraph() as kg:
                kg.attr(rank="same")
                for i in range(len(children) - 1):
                    kg.edge(children[i], children[i + 1], style="invis", weight="50", constraint="true")

        for c in children:
            g.edge(mid, c, weight="3")

    # ---- 全域的同層排序（使用者人工 ②-2） ----
    try:
        gen_order = st.session_state.get("gen_order", {}) if hasattr(st, "session_state") else {}
    except Exception:
        gen_order = {}
    if gen_order:
        gens = {}
        for pid, d in depth.items():
            gens.setdefault(d, []).append(pid)
        for d, people in gens.items():
            seq = [p for p in gen_order.get(str(d), []) if p in people] + [p for p in people if p not in gen_order.get(str(d), [])]
            if len(seq) >= 2:
                with g.subgraph() as gg:
                    gg.attr(rank="same")
                    for i in range(len(seq) - 1):
                        gg.edge(seq[i], seq[i + 1], style="invis", weight="80", constraint="true")

    # ---- 夫妻群排序（使用者人工 ②-3） ----
    try:
        group_order = st.session_state.get("group_order", {}) if hasattr(st, "session_state") else {}
    except Exception:
        group_order = {}
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
                        grp.edge(anchors[i], anchors[i + 1], style="invis", weight="90", constraint="true")

    return g

# -------------------- UI：人物與婚姻維護 --------------------
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

    # 簡單清單
    if t["persons"]:
        with st.expander("人物清單（點開檢視）", expanded=False):
            for pid, p in t["persons"].items():
                cols = st.columns([4, 2, 1, 1])
                cols[0].write(f"{pid}｜{p.get('name','')}")
                cols[1].write(p.get("birth", ""))
                if cols[2].button("刪除", key=f"del_p_{pid}"):
                    # 同步從婚姻裡拿掉
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
        s1 = cols[0].selectbox("配偶 A", [""] + list(t["persons"].keys()), format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "")
        s2 = cols[1].selectbox("配偶 B", [""] + list(t["persons"].keys()), format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "")
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
                sps = m.get("spouses", [])
                kids = m.get("children", [])
                st.markdown(f"**{mid}** ｜ " + " × ".join(t['persons'].get(s, {}).get("name", s) for s in sps))
                # 增加子女
                cols = st.columns([5, 4, 3])
                kid = cols[0].selectbox("選擇子女", [""] + list(t["persons"].keys()), format_func=lambda x: t["persons"].get(x, {}).get("name", x) if x else "", key=f"kid_{mid}")
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

                # 顯示該婚姻的子女
                if kids:
                    st.write("子女： " + "、".join(t["persons"].get(k, {}).get("name", k) for k in kids))
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

# -------------------- 視覺化 & 匯入匯出 --------------------
def _ui_visualize(t):
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))

def _ui_import_export(t):
    with st.expander("④ 匯入 / 匯出", expanded=False):
        c1, c2 = st.columns(2)
        if c1.button("匯出 JSON"):
            st.download_button(
                "下載 familytree.json",
                data=json.dumps(t, ensure_ascii=False, indent=2),
                file_name="familytree.json",
                mime="application/json",
            )
        uploaded = c2.file_uploader("匯入 JSON", type=["json"])
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                if isinstance(data, dict) and "persons" in data and "marriages" in data:
                    st.session_state.tree = data
                    st.success("匯入成功")
                    st.rerun()
                else:
                    st.warning("JSON 結構不正確。")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

# -------------------- 進入點 --------------------
def render():
    _init_state()
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

    st.caption("familytree autosuggest • r4")

if __name__ == "__main__":
    st.set_page_config(page_title="家族樹", layout="wide")
    render()

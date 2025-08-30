# -*- coding: utf-8 -*-
import streamlit as st
import json
from collections import deque, Counter, defaultdict
from graphviz import Digraph

# =========================================================
# 0) 狀態
# =========================================================
def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}   # ②-2 同層排序（使用者指定）
    if "group_order" not in st.session_state:
        st.session_state.group_order = {} # ②-3 夫妻群排序（使用者指定）
    if "pid_counter" not in st.session_state:
        st.session_state.pid_counter = 1
    if "mid_counter" not in st.session_state:
        st.session_state.mid_counter = 1

def _next_pid():
    st.session_state.pid_counter += 1
    return f"P{st.session_state.pid_counter:03d}"

def _next_mid():
    st.session_state.mid_counter += 1
    return f"M{st.session_state.mid_counter:03d}"

# =========================================================
# 1) 分層（配偶同層；子女下一層；反覆鬆弛）
# =========================================================
def _compute_generations(tree):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})

    # 初值：父→子建圖，一輪拓撲層級
    children_of = {pid: set() for pid in persons}
    indeg       = {pid: 0   for pid in persons}
    for m in marriages.values():
        sps = [s for s in m.get("spouses", []) if s in persons]
        kids= [c for c in m.get("children", []) if c in persons]
        for s in sps:
            for c in kids:
                if c not in children_of[s]:
                    children_of[s].add(c)
                    indeg[c] += 1

    depth = {pid: 0 for pid in persons}
    q = deque([p for p in persons if indeg.get(p,0) == 0]) or deque(persons.keys())
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            if depth[v] < depth[u] + 1:
                depth[v] = depth[u] + 1
            indeg[v] -= 1
            if indeg[v] <= 0:
                q.append(v)

    # 反覆鬆弛：配偶同層；子女 >= 父母最大層+1
    changed = True
    guard   = 0
    while changed and guard < 200:
        changed = False
        guard  += 1
        for m in marriages.values():
            sps  = [s for s in m.get("spouses", []) if s in persons]
            kids = [c for c in m.get("children", []) if c in persons]
            if sps:
                dmax = max(depth[s] for s in sps)
                for s in sps:
                    if depth[s] < dmax:
                        depth[s] = dmax
                        changed  = True
            else:
                dmax = 0
            for c in kids:
                need = dmax + 1
                if depth[c] < need:
                    depth[c] = need
                    changed  = True
    return depth

# =========================================================
# 2) 排序工具（硬規則使用）
# =========================================================
def _year(person):
    try:
        v = person.get("birth", "")
        return int(str(v).strip()[:4]) if v else None
    except Exception:
        return None

def _spouses_of(pid, marriages):
    """回傳 pid 的配偶清單（可能多段婚姻，去重）。"""
    seen, res = set(), []
    for m in marriages.values():
        sps = m.get("spouses", []) or []
        if pid in sps:
            for s in sps:
                if s != pid and s not in seen:
                    seen.add(s); res.append(s)
    return res

def _parents_mid_of(pid, marriages):
    """回傳 pid 的『父母那段婚姻 mid』；找不到回 None。"""
    for mid, m in marriages.items():
        if pid in (m.get("children", []) or []):
            return mid
    return None

def _couple_units(order, marriages, layer, depth):
    """
    把同層的配偶合併成『單位』（unit）。回傳 units（list of list[pids]）。
    規則：若某人與同層有人結婚，挑第一段婚姻的另一半，兩人結成一個 unit；
         沒有同層配偶則獨立成單人 unit。
    """
    pos = {p:i for i,p in enumerate(order)}
    used = set()
    units = []
    for p in order:
        if p in used:
            continue
        # 找同層配偶
        mate = None
        for mid, m in marriages.items():
            sps = m.get("spouses", []) or []
            if p in sps:
                # 第一個不是自己、且在同一層
                for s in sps:
                    if s != p and depth.get(s) == layer and s in pos:
                        mate = s
                        break
            if mate:
                break
        if mate and mate not in used:
            # 按目前左右位置排序，確保 unit 內呈現相鄰
            a, b = (p, mate) if pos[p] <= pos[mate] else (mate, p)
            units.append([a, b])
            used.add(a); used.add(b)
        else:
            units.append([p])
            used.add(p)
    return units

def _family_blocks(units, marriages):
    """
    把 units（每個 unit 是 [人] 或 [配偶A, 配偶B]）依『父母婚姻』分群。
    - 只要 unit 內有人有父母婚姻（mid），整個 unit 就歸入該 mid 的子女群。
    - 若 unit 內兩人分屬不同 mid，優先採用該 unit 在當前順序中出現時
      第一個帶有 mid 的那位（穩定、可預期）。
    - 找不到 mid 的歸入 None 群。
    回傳：[(group_key, [units...]) ...] 依原出現順序排序。
    """
    groups = defaultdict(list)
    # 保持穩定：照 units 順序掃描，遇到的第一個有 mid 的人當群鍵
    for u in units:
        key = None
        for p in u:
            mid = _parents_mid_of(p, marriages)
            if mid:
                key = mid
                break
        groups[key].append(u)

    # 回傳按原 keys 的出現順序
    ordered = []
    for key in groups:
        ordered.append((key, groups[key]))
    return ordered

def _apply_hard_constraints(order, marriages, layer, depth):
    """
    對單一層的『人物順序 order』套用兩個硬規則：
      1) 夫妻必相鄰（用 unit 表示）
      2) 同父母子女必為連續段（以父母 mid 分群），每位子女若有配偶，配偶跟在旁邊
    輸入：order（list[pids]）
    回傳：新的 order（list[pids]）
    """
    if not order:
        return order[:]

    # 先做「夫妻單位」
    units = _couple_units(order, marriages, layer, depth)

    # 再以「父母婚姻 mid」把 units 分成連續區塊
    blocks = _family_blocks(units, marriages)

    # 最終順序：依 block 的原始順序平舖，每個 unit 內保持相鄰
    new_order = []
    for _, us in blocks:
        for u in us:
            new_order.extend(u)

    # 若長度對不上（極少見：資料異常），保底回原順
    return new_order if len(new_order) == len(order) else order[:]

def _enforce_spouse_adjacency(order, marriages, layer, depth):
    """
    保險起見：再跑一輪把夫妻拉到相鄰（萬一外部又把人塞進去）。
    """
    pos = {p: i for i, p in enumerate(order)}
    changed, guard = True, 0
    while changed and guard < 50:
        changed = False
        guard += 1
        for m in marriages.values():
            sps = [s for s in (m.get("spouses", []) or []) if depth.get(s) == layer]
            if len(sps) < 2:
                continue
            a, b = sps[0], sps[1]
            if a not in pos or b not in pos:
                continue
            ia, ib = pos[a], pos[b]
            if abs(ia - ib) == 1:
                continue
            # 把較右的移到較左者旁（右側）
            if ia < ib:
                mover, target = b, pos[a] + 1
            else:
                mover, target = a, pos[b] + 1
            order.pop(pos[mover])
            if pos[mover] < target:
                target -= 1
            order.insert(target, mover)
            pos = {p: i for i, p in enumerate(order)}
            changed = True
    return order

# =========================================================
# 3) 自動減少交錯（在套用硬規則前，先跑幾輪重心法）
# =========================================================
def _auto_layout(tree, sweeps=4):
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth     = _compute_generations(tree)

    # 依層分組
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    # 初始順序：出生年/姓名
    def base_key(n):
        y = _year(persons.get(n, {}))
        return (y is None, y if y is not None else 9999, persons.get(n, {}).get("name", ""))

    gen_order = {str(d): sorted(nodes, key=base_key) for d, nodes in layers.items()}

    # 父母<->子女鄰接
    adj = {pid: set() for pid in persons}
    for m in marriages.values():
        sps  = m.get("spouses", []) or []
        kids = m.get("children", []) or []
        for s in sps:
            for c in kids:
                adj[s].add(c); adj[c].add(s)

    # 多輪 barycenter 掃描
    maxd = max(layers.keys()) if layers else 0
    def _bary(nodes, refpos):
        scored = []
        for i, n in enumerate(nodes):
            neigh = [refpos.get(v) for v in adj.get(n, []) if v in refpos]
            s = sum(neigh) / len(neigh) if neigh else float("inf")
            scored.append((s, base_key(n), i, n))
        scored.sort(key=lambda x: (x[0], x[1], x[2]))
        return [n for *_, n in scored]

    for _ in range(sweeps):
        # top → down
        for d in range(1, maxd + 1):
            ref = {p: i for i, p in enumerate(gen_order[str(d - 1)])}
            gen_order[str(d)] = _bary(gen_order[str(d)], ref)
        # bottom → up
        for d in range(maxd - 1, -1, -1):
            ref = {p: i for i, p in enumerate(gen_order[str(d + 1)])}
            gen_order[str(d)] = _bary(gen_order[str(d)], ref)

    # ====== 套用硬規則（核心）======
    for d in layers:
        order = gen_order[str(d)]
        order = _apply_hard_constraints(order, marriages, d, depth)
        order = _enforce_spouse_adjacency(order, marriages, d, depth)
        gen_order[str(d)] = order

    # 生成夫妻群排序（供 ②-3 使用）
    group_order = {}
    for d, nodes in layers.items():
        pos = {p: i for i, p in enumerate(gen_order[str(d)])}
        mids = []
        for mid, m in marriages.items():
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

    return gen_order, group_order

# =========================================================
# 4) Graphviz（夫妻同層；婚姻點在中線；子女從中線往下）
# =========================================================
def _graph(tree):
    depth     = _compute_generations(tree)
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})

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

    # 每層列表 + 預設順序（出生年/姓名）
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    def _base_key(pid):
        y = _year(persons.get(pid, {}))
        return (y is None, y if y is not None else 9999, persons.get(pid,{}).get("name",""))

    per_layer_order = {d: sorted(nodes, key=_base_key) for d, nodes in layers.items()}

    # 使用者 ②-2 覆蓋
    if st.session_state.get("gen_order"):
        for d, people in layers.items():
            seq = [p for p in st.session_state.gen_order.get(str(d), []) if p in people] + \
                  [p for p in people if p not in st.session_state.gen_order.get(str(d), [])]
            if seq: per_layer_order[d] = seq

    # ====== 最後一關：硬規則強制套用（不管來源順序如何）======
    for d in list(per_layer_order.keys()):
        order = per_layer_order[d]
        order = _apply_hard_constraints(order, marriages, d, depth)
        order = _enforce_spouse_adjacency(order, marriages, d, depth)
        per_layer_order[d] = order

    # -- 婚姻與子女（夫妻兩段線；孩子從中線往下） --
    for mid, m in marriages.items():
        sps  = m.get("spouses", []) or []
        kids = m.get("children", []) or []

        # 取得此層真正左右配偶（依 per_layer_order 左右位置）
        s_same = [s for s in sps if s in persons]
        left_sp = right_sp = None
        if len(s_same) >= 2:
            d = depth.get(s_same[0], 0)
            order = per_layer_order.get(d, s_same)
            pos = {p:i for i,p in enumerate(order)}
            s_sorted = sorted(s_same, key=lambda x: pos.get(x, 10**9))
            left_sp, right_sp = s_sorted[0], s_sorted[1]
        elif len(s_same) == 1:
            left_sp = right_sp = s_same[0]

        # 同層子圖：婚姻點 + 夫妻線（兩段、同時當錨定）
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

        # 子女：先在婚姻點下放一個隱形錨點，讓孩子聚在中線下方
        if kids:
            anchor = f"{mid}_anchor"
            g.node(anchor, shape="point", width="0.01", height="0.01", label="", style="invis")
            g.edge(mid, anchor, style="invis", weight="150", minlen="1", constraint="true")

            if len(kids) >= 2:
                with g.subgraph() as kg:
                    kg.attr(rank="same")
                    for i in range(len(kids)-1):
                        kg.edge(kids[i], kids[i+1], style="invis", weight="60", constraint="true")

            for c in kids:
                g.edge(anchor, c, style="invis", weight="120", minlen="1", constraint="true")
                g.edge(mid, c, weight="3", minlen="1")   # 可見親子線

    # 強制分層
    for d, members in layers.items():
        with g.subgraph() as same:
            same.attr(rank="same")
            for pid in members:
                same.node(pid)

    # 同層全序鏈（穩定橫向）
    for d, order in per_layer_order.items():
        if len(order) >= 2:
            with g.subgraph() as gg:
                gg.attr(rank="same")
                for i in range(len(order)-1):
                    gg.edge(order[i], order[i+1], style="invis", weight="220", constraint="true")

    # ②-3 夫妻群排序（優先度最高；但因硬規則存在，仍不會破壞相鄰/同父母成段）
    marriages_all = tree.get("marriages", {})
    if st.session_state.get("group_order"):
        for d_str, mids in st.session_state.group_order.items():
            try:
                d = int(d_str)
            except Exception:
                continue
            anchors=[]
            for mid in [m for m in mids if m in marriages_all]:
                sps = marriages_all[mid].get("spouses", [])
                anchor=None
                for s in sps:
                    if depth.get(s)==d:
                        anchor=s; break
                if anchor is None and sps:
                    anchor=sps[0]
                anchors.append(anchor)
            anchors=[a for a in anchors if a in persons]
            if len(anchors)>=2:
                with g.subgraph() as grp:
                    grp.attr(rank="same")
                    for i in range(len(anchors)-1):
                        grp.edge(anchors[i], anchors[i+1],
                                 style="invis", weight="450", constraint="true")
    return g

# =========================================================
# 5) UI：基本資料
# =========================================================
def _person_form(t):
    st.subheader("① 人物管理")
    with st.form("add_person", clear_on_submit=True):
        c = st.columns(4)
        name  = c[0].text_input("姓名 *")
        gender= c[1].selectbox("性別", ["", "男", "女"], index=0)
        birth = c[2].text_input("出生年（可留空）")
        ok = c[3].form_submit_button("新增人物")
        if ok:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _next_pid()
                t["persons"][pid] = {"name": name.strip()}
                if gender: t["persons"][pid]["gender"]=gender
                if birth.strip(): t["persons"][pid]["birth"]=birth.strip()
                st.success(f"已新增：{pid}｜{name}")

    if t["persons"]:
        with st.expander("人物清單（點開管理）", expanded=False):
            for pid, p in t["persons"].items():
                cc = st.columns([5,2,1,1])
                cc[0].write(f"{pid}｜{p.get('name','')}")
                cc[1].write(p.get("birth",""))
                if cc[2].button("刪除", key=f"del_p_{pid}"):
                    # 從婚姻中移除
                    for m in t["marriages"].values():
                        m["spouses"] = [x for x in m.get("spouses",[]) if x!=pid]
                        m["children"]= [x for x in m.get("children",[]) if x!=pid]
                    del t["persons"][pid]
                    st.rerun()
                if cc[3].button("改名", key=f"ren_{pid}"):
                    st.session_state[f"ren_{pid}"]=True
                if st.session_state.get(f"ren_{pid}"):
                    new = st.text_input("新姓名", value=p.get("name",""), key=f"in_{pid}")
                    if st.button("確定", key=f"ok_{pid}"):
                        t["persons"][pid]["name"]=new.strip()
                        st.session_state[f"ren_{pid}"]=False
                        st.rerun()

def _marriage_form(t):
    st.subheader("② 婚姻關係")
    with st.form("add_marriage", clear_on_submit=True):
        c = st.columns(4)
        s1 = c[0].selectbox("配偶 A", [""]+list(t["persons"].keys()),
                            format_func=lambda x: t["persons"].get(x,{}).get("name",x) if x else "")
        s2 = c[1].selectbox("配偶 B", [""]+list(t["persons"].keys()),
                            format_func=lambda x: t["persons"].get(x,{}).get("name",x) if x else "")
        ok = c[3].form_submit_button("新增婚姻")
        if ok:
            if not s1 or not s2 or s1==s2:
                st.warning("請選兩位不同人物")
            else:
                mid = _next_mid()
                t["marriages"][mid]={"spouses":[s1,s2],"children":[]}
                # 一建立婚姻就強制刷新，讓夫妻立刻相鄰（由硬規則實現）
                st.success(f"已新增婚姻：{mid}（視覺上已強制相鄰）")
                st.rerun()

    if t["marriages"]:
        with st.expander("婚姻清單（點開管理）", expanded=False):
            for mid, m in t["marriages"].items():
                sps = m.get("spouses",[])
                kids= m.get("children",[])
                title = " × ".join([t["persons"].get(s,{}).get("name",s) for s in sps]) or "（未登記配偶）"
                st.markdown(f"**{mid}**｜{title}｜子女 {len(kids)}")
                cc = st.columns([5,3,2,2])
                kid = cc[0].selectbox("新增子女", [""]+list(t["persons"].keys()),
                                      format_func=lambda x: t["persons"].get(x,{}).get("name",x) if x else "",
                                      key=f"k_{mid}")
                if cc[1].button("加入子女", key=f"addk_{mid}") and kid:
                    if kid not in m["children"]:
                        m["children"].append(kid); st.rerun()
                if cc[2].button("清空子女", key=f"clr_{mid}"):
                    m["children"]=[]; st.rerun()
                if cc[3].button("刪除此婚姻", key=f"del_{mid}"):
                    del t["marriages"][mid]; st.rerun()

                # 子女局部排序（可選）— 視覺上仍會被硬規則包成一段
                if len(kids)>=2:
                    st.caption("子女順序（此婚姻）")
                    for i,k in enumerate(kids):
                        nm = t["persons"].get(k,{}).get("name",k)
                        r = st.columns([6,1,1,1,1])
                        r[0].write(f"{i+1}. {k}｜{nm}")
                        if r[1].button("↑", key=f"u_{mid}_{k}") and i>0:
                            kids[i-1],kids[i]=kids[i],kids[i-1]; st.rerun()
                        if r[2].button("↓", key=f"d_{mid}_{k}") and i<len(kids)-1:
                            kids[i+1],kids[i]=kids[i],kids[i+1]; st.rerun()
                        if r[3].button("置頂", key=f"t_{mid}_{k}") and i>0:
                            x=kids.pop(i); kids.insert(0,x); st.rerun()
                        if r[4].button("置底", key=f"b_{mid}_{k}") and i<len(kids)-1:
                            x=kids.pop(i); kids.append(x); st.rerun()

# =========================================================
# 6) UI：排序工具 + 一鍵自動減交錯
# =========================================================
def _ui_autoreduce(t):
    with st.expander("②-0 一鍵自動減少交錯（建議）", expanded=False):
        st.caption("說明：先跑重心法，再強制『夫妻相鄰』與『同父母子女成段（含子女之配偶）』兩個硬規則。")
        if st.button("⚙️ 自動減少交錯", type="primary"):
            gen_order, group_order = _auto_layout(t, sweeps=5)
            st.session_state.gen_order = gen_order
            st.session_state.group_order = group_order
            st.success("已套用建議排序，若需要可再用 ②-2 / ②-3 微調。")
            st.rerun()

def _ui_same_layer_reorder(t):
    with st.expander("②-2 同層排序", expanded=False):
        depth = _compute_generations(t)
        if not depth:
            st.info("請先建立人物/婚姻"); return
        gens = sorted(set(depth.values()))
        gsel = st.selectbox("選擇世代", gens, format_func=lambda d:f"第 {d} 層（{sum(1 for p in depth if depth[p]==d)} 人）")
        people = [p for p,d in depth.items() if d==gsel]
        cur = list(st.session_state.gen_order.get(str(gsel), []))
        order = [p for p in cur if p in people] + [p for p in people if p not in cur]
        # 提示：即使手動調整，繪圖時仍會自動把夫妻黏緊、同父母子女成段
        for i,pid in enumerate(order):
            nm = t["persons"].get(pid,{}).get("name",pid)
            r = st.columns([6,1,1,1,1])
            r[0].write(f"{i+1}. {pid}｜{nm}")
            if r[1].button("↑", key=f"su_{gsel}_{pid}") and i>0:
                order[i-1],order[i]=order[i],order[i-1]; st.session_state.gen_order[str(gsel)]=order; st.rerun()
            if r[2].button("↓", key=f"sd_{gsel}_{pid}") and i<len(order)-1:
                order[i+1],order[i]=order[i],order[i+1]; st.session_state.gen_order[str(gsel)]=order; st.rerun()
            if r[3].button("置頂", key=f"st_{gsel}_{pid}") and i>0:
                x=order.pop(i); order.insert(0,x); st.session_state.gen_order[str(gsel)]=order; st.rerun()
            if r[4].button("置底", key=f"sb_{gsel}_{pid}") and i<len(order)-1:
                x=order.pop(i); order.append(x); st.session_state.gen_order[str(gsel)]=order; st.rerun()

def _ui_group_reorder(t):
    with st.expander("②-3 夫妻群排序（整代群組）", expanded=False):
        depth = _compute_generations(t)
        marriages = t.get("marriages",{})
        if not depth or not marriages:
            st.info("請先建立人物/婚姻"); return
        gens = sorted(set(depth.values()))
        gsel = st.selectbox("選擇世代（以配偶所在層為準）", gens, format_func=lambda d:f"第 {d} 層")
        mids=[]
        for mid,m in marriages.items():
            sps=m.get("spouses",[])
            if any(depth.get(s)==gsel for s in sps):
                mids.append(mid)
        if not mids:
            st.info("此層沒有夫妻群"); return
        cur = list(st.session_state.group_order.get(str(gsel), []))
        order = [m for m in cur if m in mids] + [m for m in mids if m not in cur]
        def _fmt(mid):
            sps = marriages[mid].get("spouses",[])
            names = " × ".join([t["persons"].get(s,{}).get("name",s) for s in sps]) or "（未登記配偶）"
            return f"{mid}｜{names}"
        for i,mid in enumerate(order):
            r = st.columns([7,1,1,1,1])
            r[0].write(f"{i+1}. {_fmt(mid)}")
            if r[1].button("↑", key=f"gu_{gsel}_{mid}") and i>0:
                order[i-1],order[i]=order[i],order[i-1]; st.session_state.group_order[str(gsel)]=order; st.rerun()
            if r[2].button("↓", key=f"gd_{gsel}_{mid}") and i<len(order)-1:
                order[i+1],order[i]=order[i],order[i+1]; st.session_state.group_order[str(gsel)]=order; st.rerun()
            if r[3].button("置頂", key=f"gt_{gsel}_{mid}") and i>0:
                x=order.pop(i); order.insert(0,x); st.session_state.group_order[str(gsel)]=order; st.rerun()
            if r[4].button("置底", key=f"gb_{gsel}_{mid}") and i<len(order)-1:
                x=order.pop(i); order.append(x); st.session_state.group_order[str(gsel)]=order; st.rerun()

# =========================================================
# 7) 視覺化 & 匯入/匯出
# =========================================================
def _ui_visualize(t):
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))

def _ui_import_export(t):
    with st.expander("④ 匯入 / 匯出", expanded=False):
        c1,c2 = st.columns(2)
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
# 8) 入口
# =========================================================
def render():
    _init_state()
    st.title("家族樹")
    t = st.session_state.tree

    _person_form(t)
    _marriage_form(t)

    _ui_autoreduce(t)        # 一鍵自動減少交錯（可選）
    _ui_same_layer_reorder(t)
    _ui_group_reorder(t)

    _ui_visualize(t)
    _ui_import_export(t)

    st.caption("familytree • r11 (spouse-adjacent + siblings-block)")

if __name__ == "__main__":
    st.set_page_config(page_title="家族樹", layout="wide")
    render()

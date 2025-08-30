# -*- coding: utf-8 -*-
import streamlit as st
import json
from collections import deque, Counter
from graphviz import Digraph

# =========================================================
# 0) 狀態
# =========================================================
def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    if "gen_order" not in st.session_state:
        st.session_state.gen_order = {}   # ②-2 同層排序（使用者指定 / 規則產生）
    if "group_order" not in st.session_state:
        st.session_state.group_order = {} # ②-3 夫妻群排序（使用者指定 / 規則產生）
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
# 2) 佈局規則工具（手足群、配偶相鄰、跨家庭靠攏）
# =========================================================
def _year(person):
    try:
        v = person.get("birth", "")
        return int(str(v).strip()[:4]) if v else None
    except Exception:
        return None

def _base_key(pid, persons):
    y = _year(persons.get(pid, {}))
    return (y is None, y if y is not None else 9999, persons.get(pid, {}).get("name", ""))

def _parents_mid_of(pid, marriages):
    """回傳 pid 的『父母那段婚姻 mid』；找不到回 None。"""
    for mid, m in marriages.items():
        if pid in (m.get("children", []) or []):
            return mid
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

def _move_to_front(lst, x):
    if x in lst:
        lst.remove(x); lst.insert(0, x)

def _move_to_back(lst, x):
    if x in lst:
        lst.remove(x); lst.append(x)

def _ensure_adjacent_inside(lst, a, b):
    """確保 a、b 在同一 list 中相鄰（盡量保持其他順序）。"""
    if a not in lst or b not in lst: 
        return
    ia, ib = lst.index(a), lst.index(b)
    if abs(ia - ib) == 1:
        return
    # 將 b 移到 a 旁邊（右側）
    lst.pop(ib)
    ia = lst.index(a)  # a 的位置可能因 pop(b) 改變
    lst.insert(ia + 1, b)

def _apply_rules(tree, focus_child=None):
    """
    產生 gen_order / group_order，滿足：
      1) 建立婚姻後，同層配偶相鄰（不打散兄弟姊妹群）
      2) 同父母的小孩形成『手足群』，不同家庭的手足群不互插
      3) 新增小孩且其配偶有父母時：把兩個手足群靠在一起，並把兩人排在交界
    """
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth     = _compute_generations(tree)

    # 先把每層的人分出來
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order = {}

    # 逐層建立順序（自上而下，因為下層要參考上一層父母位置）
    maxd = max(layers.keys()) if layers else 0
    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))

        # ---- 形成「群」：同父母的小孩 = 同群；無父母者（或最上層）各自成群
        # 群 ID：有父母用 mid，否則用 'orph:pid'
        clusters = {}
        for p in members:
            pmid = _parents_mid_of(p, marriages)
            cid = pmid if (pmid is not None and d > 0) else f"orph:{p}"
            clusters.setdefault(cid, []).append(p)

        # 群內排序：以出生年/姓名為主，並讓同群內的夫妻相鄰
        for cid, lst in clusters.items():
            lst.sort(key=lambda x: _base_key(x, persons))
            # 同群內的夫妻相鄰（僅限雙方都在此群）
            for mid, m in marriages.items():
                sps = [s for s in (m.get("spouses", []) or []) if s in lst and depth.get(s) == d]
                if len(sps) >= 2:
                    _ensure_adjacent_inside(lst, sps[0], sps[1])

        # 群之間的順序：若有父母群，依上一層父母的位置（重心）排序
        cluster_ids = list(clusters.keys())
        if d > 0:
            parent_pos = {p: i for i, p in enumerate(gen_order.get(str(d - 1), []))}
            def _anchor(cid):
                if not cid.startswith("M"):
                    return None
                m = marriages.get(cid)
                if not m:
                    return None
                pts = [parent_pos.get(s) for s in (m.get("spouses", []) or []) if parent_pos.get(s) is not None]
                return sum(pts) / len(pts) if pts else None

            cluster_ids.sort(key=lambda cid: ( _anchor(cid) is None, _anchor(cid) if _anchor(cid) is not None else 10**9 ))

        # ③ 規則：若本層是 focus_child，且其配偶有父母 → 讓兩個手足群相鄰，並把兩人排在交界
        if focus_child and depth.get(focus_child) == d:
            spouses = _spouses_of(focus_child, marriages)
            spouse_with_parents = None
            for s in spouses:
                if _parents_mid_of(s, marriages):
                    spouse_with_parents = s; break
            if spouse_with_parents:
                cid_a = _parents_mid_of(focus_child, marriages) if d > 0 else f"orph:{focus_child}"
                cid_b = _parents_mid_of(spouse_with_parents, marriages) if d > 0 else f"orph:{spouse_with_parents}"
                if cid_a != cid_b and cid_a in cluster_ids and cid_b in cluster_ids:
                    ia, ib = cluster_ids.index(cid_a), cluster_ids.index(cid_b)
                    # 把 B 放在 A 的右邊（若 B 在左側就抽出插入 A 右邊）
                    cluster_ids.pop(ib)
                    if ib < ia:
                        ia -= 1
                    cluster_ids.insert(ia + 1, cid_b)
                    # A 末端放 child，B 開頭放其配偶，確保二人交界相鄰
                    _move_to_back(clusters[cid_a], focus_child)
                    _move_to_front(clusters[cid_b], spouse_with_parents)

        # 規則 1：本層所有「跨群」夫妻也要相鄰（把兩群併排，兩人放在交界）
        for mid, m in marriages.items():
            sps = [s for s in (m.get("spouses", []) or []) if depth.get(s) == d]
            if len(sps) < 2:
                continue
            a, b = sps[0], sps[1]
            ca = _parents_mid_of(a, marriages) if d > 0 else f"orph:{a}"
            cb = _parents_mid_of(b, marriages) if d > 0 else f"orph:{b}"
            if ca == cb:
                # 同群內已在前面處理相鄰
                continue
            if ca not in cluster_ids or cb not in cluster_ids:
                continue
            ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
            if abs(ia - ib) != 1:
                # 把較遠的一群移到較近的一群旁邊；預設放在 ca 的右側
                cluster_ids.pop(ib)
                if ib < ia:
                    ia -= 1
                cluster_ids.insert(ia + 1, cb)
            # 兩人放在交界：若 ca 在左、cb 在右 → a 放右端、b 放左端；反之亦然
            ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
            if ia < ib:
                _move_to_back(clusters[ca], a)
                _move_to_front(clusters[cb], b)
            else:
                _move_to_back(clusters[cb], b)
                _move_to_front(clusters[ca], a)

        # 整層拍扁
        final_list = []
        for cid in cluster_ids:
            final_list.extend(clusters[cid])
        gen_order[str(d)] = final_list

    # 生成夫妻群排序（供 ②-3 使用；以該層 anchor 出現順序）
    group_order = {}
    for d, order in gen_order.items():
        d_int = int(d)
        pos = {p: i for i, p in enumerate(order)}
        mids = []
        for mid, m in marriages.items():
            sps = m.get("spouses", []) or []
            anchor = None
            for s in sps:
                if depth.get(s) == d_int:
                    anchor = s; break
            if anchor is None and sps:
                anchor = sps[0]
            if anchor in pos:
                mids.append((pos[anchor], mid))
        if mids:
            mids.sort()
            group_order[str(d_int)] = [mid for _, mid in mids]

    # 寫回狀態
    st.session_state.gen_order = gen_order
    st.session_state.group_order = group_order
    return gen_order, group_order

# =========================================================
# 3) Graphviz（夫妻同層；婚姻點在中線；子女從中線往下）
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

    # 每層順序：先取規則產生 / 使用者覆蓋；否則以基本排序
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    def _base_key2(pid):
        y = _year(persons.get(pid, {}))
        return (y is None, y if y is not None else 9999, persons.get(pid,{}).get("name",""))

    per_layer_order = {}
    for d, nodes in layers.items():
        per_layer_order[d] = sorted(nodes, key=_base_key2)

    if st.session_state.get("gen_order"):
        for d, people in layers.items():
            seq = [p for p in st.session_state.gen_order.get(str(d), []) if p in people] + \
                  [p for p in people if p not in st.session_state.gen_order.get(str(d), [])]
            if seq: per_layer_order[d] = seq

    # -- 婚姻與子女 --
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

    # ②-3 夫妻群排序（優先度最高）
    if st.session_state.get("group_order"):
        for d_str, mids in st.session_state.group_order.items():
            try:
                d = int(d_str)
            except Exception:
                continue
            anchors=[]
            for mid in [m for m in mids if m in marriages]:
                sps = marriages[mid].get("spouses", [])
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
# 4) UI：基本資料
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
                    _apply_rules(t)  # 重新套規則
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
                # 規則 ①：立刻讓配偶相鄰（不破壞手足群）
                _apply_rules(t)
                st.success(f"已新增婚姻：{mid}（已自動把配偶排為相鄰）")
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
                        m["children"].append(kid)
                        # 規則 ③：若此子女的配偶有父母 → 讓兩個家庭靠攏、夫妻在交界相鄰
                        _apply_rules(t, focus_child=kid)
                        st.rerun()
                if cc[2].button("清空子女", key=f"clr_{mid}"):
                    m["children"]=[]; _apply_rules(t); st.rerun()
                if cc[3].button("刪除此婚姻", key=f"del_{mid}"):
                    del t["marriages"][mid]; _apply_rules(t); st.rerun()

                # 子女局部排序（可選）
                if len(kids)>=2:
                    st.caption("子女順序（此婚姻）")
                    for i,k in enumerate(kids):
                        nm = t["persons"].get(k,{}).get("name",k)
                        r = st.columns([6,1,1,1,1])
                        r[0].write(f"{i+1}. {k}｜{nm}")
                        if r[1].button("↑", key=f"u_{mid}_{k}") and i>0:
                            kids[i-1],kids[i]=kids[i],kids[i-1]; _apply_rules(t); st.rerun()
                        if r[2].button("↓", key=f"d_{mid}_{k}") and i<len(kids)-1:
                            kids[i+1],kids[i]=kids[i],kids[i+1]; _apply_rules(t); st.rerun()
                        if r[3].button("置頂", key=f"t_{mid}_{k}") and i>0:
                            x=kids.pop(i); kids.insert(0,x); _apply_rules(t); st.rerun()
                        if r[4].button("置底", key=f"b_{mid}_{k}") and i<len(kids)-1:
                            x=kids.pop(i); kids.append(x); _apply_rules(t); st.rerun()

# =========================================================
# 5) UI：排序工具（保留，必要時可微調）
# =========================================================
def _ui_same_layer_reorder(t):
    with st.expander("②-2 同層排序（微調）", expanded=False):
        depth = _compute_generations(t)
        if not depth:
            st.info("請先建立人物/婚姻"); return
        gens = sorted(set(depth.values()))
        gsel = st.selectbox("選擇世代", gens, format_func=lambda d:f"第 {d} 層（{sum(1 for p in depth if depth[p]==d)} 人）")
        people = [p for p,d in depth.items() if d==gsel]
        cur = list(st.session_state.gen_order.get(str(gsel), []))
        order = [p for p in cur if p in people] + [p for p in people if p not in cur]
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
# 6) 視覺化 & 匯入/匯出
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
                                _apply_rules(st.session_state.tree)  # 重新套規則
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
# 7) 入口
# =========================================================
def render():
    _init_state()
    st.title("家族樹")
    t = st.session_state.tree

    _person_form(t)
    _marriage_form(t)

    _ui_same_layer_reorder(t)   # 可選：手動微調
    _ui_group_reorder(t)        # 可選：夫妻群整體調整

    _ui_visualize(t)
    _ui_import_export(t)

    st.caption("familytree • rules v1")

if __name__ == "__main__":
    st.set_page_config(page_title="家族樹", layout="wide")
    render()

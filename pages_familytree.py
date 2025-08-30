# -*- coding: utf-8 -*-
import streamlit as st
import json
from collections import deque, defaultdict
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
    # 只做為演算法輸出（沒有手動 UI）
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
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})

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
# 2) 排序規則：手足群、配偶相鄰、跨家庭靠攏（防拆）
# =========================================================
def _parents_mid_of(pid, marriages):
    for mid, m in marriages.items():
        if pid in (m.get("children", []) or []):
            return mid
    return None

def _spouses_of(pid, marriages):
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
    """在同一 list 內，讓 a、b 相鄰（盡量不動其它人）。"""
    if a not in lst or b not in lst:
        return
    ia, ib = lst.index(a), lst.index(b)
    if abs(ia - ib) == 1:
        return
    lst.pop(ib)
    ia = lst.index(a)  # a 的位置可能因 pop 而變動
    lst.insert(ia + 1, b)

def _ensure_clusters_adjacent(cluster_ids, ca, cb, placed_neighbors):
    """
    讓群 ca 與 cb 成為鄰居；優先不破壞既有相鄰（placed_neighbors）。
    placed_neighbors 是 dict[cluster] -> set(已鎖定的鄰居)。
    回傳是否真的調整了 cluster_ids（或本來就相鄰）。
    """
    if ca == cb or ca not in cluster_ids or cb not in cluster_ids:
        return False

    ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
    if abs(ia - ib) == 1:
        # 已相鄰，直接記鎖定
        placed_neighbors[ca].add(cb); placed_neighbors[cb].add(ca)
        return False

    # 決定放在 ca 的哪一側：若一側已被鎖定，放另一側；都未鎖定則放較靠近的一側
    left_locked  = None
    right_locked = None
    if ia - 1 >= 0:
        left_locked  = cluster_ids[ia - 1] in placed_neighbors[ca]
    if ia + 1 < len(cluster_ids):
        right_locked = cluster_ids[ia + 1] in placed_neighbors[ca]

    prefer_side = None
    if left_locked and not right_locked:
        prefer_side = "right"
    elif right_locked and not left_locked:
        prefer_side = "left"
    elif left_locked and right_locked:
        # 兩側都被鎖死，只能放最接近側（但無法鎖定鄰接，交給上層處理）
        prefer_side = "left" if ib < ia else "right"
    else:
        prefer_side = "left" if ib < ia else "right"

    # 把 cb 抽出，插到 ca 的 prefer_side
    cluster_ids.pop(ib)
    if ib < ia:
        ia -= 1
    insert_at = ia if prefer_side == "left" else ia + 1
    cluster_ids.insert(insert_at, cb)

    placed_neighbors[ca].add(cb); placed_neighbors[cb].add(ca)
    return True

def _apply_rules(tree, focus_child=None):
    """
    產生 gen_order / group_order，滿足：
      1) 建立婚姻後，同層配偶必相鄰（僅在群內調整到邊界，不打散手足群）
      2) 同父母的小孩固定成群（sibling cluster），不同家庭不互插
      3) 新增子女且其配偶有父母：兩個家庭靠攏，夫妻在交界相鄰
      4) 防拆：已成為鄰居的群會被鎖定，再處理新的跨群婚姻時盡量不破壞
    """
    persons   = tree.get("persons", {})
    marriages = tree.get("marriages", {})
    depth     = _compute_generations(tree)

    # 各層的人
    layers = {}
    for pid, d in depth.items():
        layers.setdefault(d, []).append(pid)

    gen_order = {}
    maxd = max(layers.keys()) if layers else 0

    for d in range(0, maxd + 1):
        members = sorted(layers.get(d, []), key=lambda x: _base_key(x, persons))

        # ---- Step A：形成手足群（cluster）
        clusters = {}  # cid -> [pids]
        for p in members:
            pmid = _parents_mid_of(p, marriages)
            cid = pmid if (pmid is not None and d > 0) else f"orph:{p}"
            clusters.setdefault(cid, []).append(p)

        # 群內排序：基本排序 + 同群配偶相鄰
        for cid, lst in clusters.items():
            lst.sort(key=lambda x: _base_key(x, persons))
            for mid, m in marriages.items():
                sps = [s for s in (m.get("spouses", []) or []) if s in lst and depth.get(s) == d]
                if len(sps) >= 2:
                    _ensure_adjacent_inside(lst, sps[0], sps[1])

        # 初始群順序：以父母在上一層的平均位置排序 (d>0)，否則按基本鍵
        cluster_ids = list(clusters.keys())
        if d > 0:
            parent_pos = {p: i for i, p in enumerate(gen_order.get(str(d - 1), []))}
            def _anchor(cid):
                if not cid.startswith("M"):  # 無父母：None
                    return None
                m = marriages.get(cid)
                if not m:
                    return None
                pts = [parent_pos.get(s) for s in (m.get("spouses", []) or []) if parent_pos.get(s) is not None]
                return sum(pts) / len(pts) if pts else None
            cluster_ids.sort(key=lambda cid: ( _anchor(cid) is None, _anchor(cid) if _anchor(cid) is not None else 10**9 ))
        else:
            cluster_ids.sort(key=lambda cid: _base_key(cid.replace("orph:",""), persons)
                             if cid.startswith("orph:") else (False, 0, cid))

        # 方便後續：鄰接鎖定表
        placed_neighbors = defaultdict(set)

        # ---- Step B（規則 3先行）：若 focus_child 的配偶有父母，先把兩群靠攏
        if focus_child and depth.get(focus_child) == d:
            spouses = _spouses_of(focus_child, marriages)
            spouse_with_parents = None
            for s in spouses:
                if _parents_mid_of(s, marriages):
                    spouse_with_parents = s; break
            if spouse_with_parents:
                ca = _parents_mid_of(focus_child, marriages) if d > 0 else f"orph:{focus_child}"
                cb = _parents_mid_of(spouse_with_parents, marriages) if d > 0 else f"orph:{spouse_with_parents}"
                if ca != cb and ca in cluster_ids and cb in cluster_ids:
                    _ensure_clusters_adjacent(cluster_ids, ca, cb, placed_neighbors)
                    # 把兩人推到交界
                    ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
                    if ia < ib:
                        _move_to_back(clusters[ca], focus_child)
                        _move_to_front(clusters[cb], spouse_with_parents)
                    else:
                        _move_to_back(clusters[cb], spouse_with_parents)
                        _move_to_front(clusters[ca], focus_child)

        # ---- Step C：處理本層所有跨家庭婚姻（由近到遠，盡量不破壞已鎖定鄰接）
        # 蒐集跨群配偶對
        cross_pairs = []
        for mid, m in marriages.items():
            sps = [s for s in (m.get("spouses", []) or []) if depth.get(s) == d]
            if len(sps) < 2:
                continue
            a, b = sps[0], sps[1]
            ca = _parents_mid_of(a, marriages) if d > 0 else f"orph:{a}"
            cb = _parents_mid_of(b, marriages) if d > 0 else f"orph:{b}"
            if ca == cb or ca not in cluster_ids or cb not in cluster_ids:
                continue
            ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
            gap = abs(ia - ib) - 1
            cross_pairs.append((gap, ca, cb, a, b))
        cross_pairs.sort(key=lambda x: x[0])  # gap 小者優先

        for _, ca, cb, a, b in cross_pairs:
            _ensure_clusters_adjacent(cluster_ids, ca, cb, placed_neighbors)
            ia, ib = cluster_ids.index(ca), cluster_ids.index(cb)
            if ia < ib:
                _move_to_back(clusters[ca], a)
                _move_to_front(clusters[cb], b)
            else:
                _move_to_back(clusters[cb], b)
                _move_to_front(clusters[ca], a)

        # ---- Step D：拍扁成層序列
        final_list = []
        for cid in cluster_ids:
            final_list.extend(clusters[cid])
        gen_order[str(d)] = final_list

    # 產生 group_order（供圖上同層鍊接使用；沒有手動 UI）
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

    st.session_state.gen_order = gen_order
    st.session_state.group_order = group_order
    return gen_order, group_order

# =========================================================
# 3) 視覺化（婚姻點居中，子女從婚姻點往下）
# =========================================================
def _graph(tree):
    depth     = _compute_generations(tree)
    persons   = tree.get("persons", {})
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

    # 各層順序
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

    # 婚姻與子女：婚姻點當中線，子女自中線往下
    for mid, m in marriages.items():
        sps  = m.get("spouses", []) or []
        kids = m.get("children", []) or []

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
                    for i in range(len(kids)-1):
                        kg.edge(kids[i], kids[i+1], style="invis", weight="60", constraint="true")

            for c in kids:
                g.edge(anchor, c, style="invis", weight="120", minlen="1", constraint="true")
                g.edge(mid, c, weight="3", minlen="1")

    # 強制同層 rank
    for d, members in layers.items():
        with g.subgraph() as same:
            same.attr(rank="same")
            for pid in members:
                same.node(pid)

    # 同層穩定鏈（保持橫向順序）
    for d, order in per_layer_order.items():
        if len(order) >= 2:
            with g.subgraph() as gg:
                gg.attr(rank="same")
                for i in range(len(order)-1):
                    gg.edge(order[i], order[i+1], style="invis", weight="220", constraint="true")

    return g

# =========================================================
# 4) UI：人物／婚姻（建立或變更時自動套規則）
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
                    for m in t["marriages"].values():
                        m["spouses"] = [x for x in m.get("spouses",[]) if x!=pid]
                        m["children"]= [x for x in m.get("children",[]) if x!=pid]
                    del t["persons"][pid]
                    _apply_rules(t)
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
                _apply_rules(t)  # 規則 1：立即讓配偶相鄰（不破壞手足群）
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
                        _apply_rules(t, focus_child=kid)  # 規則 3：靠攏配偶家庭＋交界相鄰
                        st.rerun()
                if cc[2].button("清空子女", key=f"clr_{mid}"):
                    m["children"]=[]; _apply_rules(t); st.rerun()
                if cc[3].button("刪除此婚姻", key=f"del_{mid}"):
                    del t["marriages"][mid]; _apply_rules(t); st.rerun()

# =========================================================
# 5) 視覺化 & 匯入/匯出（無手動排序 UI）
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

    st.caption("familytree • rules v3 (auto layout, no manual UI)")

if __name__ == "__main__":
    render()

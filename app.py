# app.py
# -*- coding: utf-8 -*-
# 依賴：streamlit, pyvis
# 功能亮點：
# 1) 兄弟姐妹依年齡由左到右排序（年紀由大到小；出生年小者在左）。
# 2) 配偶呈現：現任配偶在人物右側、前配偶在左側（盡量滿足；多婚況採就近規則）。
# 3) 使用 marriage(婚姻) 中介點連結雙親 → 子女，降低交錯線。
# 4) PyVis 互動：可縮放、平移、拖曳；拖曳時邊線自動跟隨。
# 5) 一鍵「整體重排」；支援 JSON 匯入/匯出；一鍵載入示例資料。
# 6) 簡易資料維護：新增人物、建立婚姻（現任/前任）、在婚姻下新增子女。

import json
import math
import uuid
from collections import defaultdict, deque

import streamlit as st
from pyvis.network import Network

st.set_page_config(page_title="家族樹（自動排序與配偶位置優化）", page_icon="🌳", layout="wide")

# -----------------------------
# 資料結構與工具
# -----------------------------
def _uid() -> str:
    return uuid.uuid4().hex[:12]

def init_state():
    if "persons" not in st.session_state:
        st.session_state["persons"] = {}  # id -> {id,name,birth_year,gender,note}
    if "marriages" not in st.session_state:
        st.session_state["marriages"] = {}  # id -> {id, p1, p2, status}
    if "children" not in st.session_state:
        st.session_state["children"] = []   # list of {id, marriage_id, child_id}
    if "positions" not in st.session_state:
        st.session_state["positions"] = {}  # id -> (x,y)
    if "anchor_id" not in st.session_state:
        st.session_state["anchor_id"] = None

def person_label(p):
    name = p.get("name", f"未命名-{p['id'][:4]}")
    by = p.get("birth_year")
    if by:
        return f"{name}\n({by})"
    return name

def add_person(name, birth_year=None, gender=None, note=None):
    pid = _uid()
    st.session_state["persons"][pid] = {
        "id": pid,
        "name": name.strip() if name else f"未命名-{pid[:4]}",
        "birth_year": int(birth_year) if birth_year not in (None, "",) else None,
        "gender": gender or "",
        "note": note or "",
    }
    return pid

def add_marriage(p1, p2, status="current"):
    mid = _uid()
    st.session_state["marriages"][mid] = {
        "id": mid,
        "p1": p1,
        "p2": p2,
        "status": status,  # "current" 或 "former"
    }
    return mid

def add_child(marriage_id, child_id):
    cid = _uid()
    st.session_state["children"].append({
        "id": cid,
        "marriage_id": marriage_id,
        "child_id": child_id,
    })
    return cid

def get_person(pid):
    return st.session_state["persons"].get(pid)

def birth_year_of(pid):
    p = get_person(pid)
    return p.get("birth_year") if p else None

def age_order_key(pid):
    # 年紀由大到小（左到右）：出生年小者靠左 → sort by birth_year ASC, None 置後
    by = birth_year_of(pid)
    return (99999 if by is None else by, get_person(pid).get("name",""))

def person_spouse_counts():
    # 統計每人前任數、現任數
    ex_cnt = defaultdict(int)
    cur_cnt = defaultdict(int)
    for m in st.session_state["marriages"].values():
        p1, p2 = m["p1"], m["p2"]
        if m["status"] == "former":
            ex_cnt[p1] += 1
            ex_cnt[p2] += 1
        else:
            cur_cnt[p1] += 1
            cur_cnt[p2] += 1
    return ex_cnt, cur_cnt

def marriages_of(pid):
    res = []
    for m in st.session_state["marriages"].values():
        if pid in (m["p1"], m["p2"]):
            res.append(m)
    return res

def children_of_marriage(mid):
    kids = [c["child_id"] for c in st.session_state["children"] if c["marriage_id"] == mid]
    # 兄弟姊妹排序：年紀由大到小（出生年小 → 左）
    kids_sorted = sorted(kids, key=age_order_key)
    return kids_sorted

def parents_of_child(pid):
    """回傳該子女的所有父母（跨多段婚姻也可），set"""
    parents = set()
    for ch in st.session_state["children"]:
        if ch["child_id"] == pid:
            m = st.session_state["marriages"].get(ch["marriage_id"])
            if m:
                parents.add(m["p1"])
                parents.add(m["p2"])
    return parents

def children_of_parent(pid):
    kids = set()
    for ch in st.session_state["children"]:
        m = st.session_state["marriages"].get(ch["marriage_id"])
        if m and (pid in (m["p1"], m["p2"])):
            kids.add(ch["child_id"])
    return kids

def compute_generations(anchor_id):
    """以 anchor_id 為中心，父母在上（負數層），子女在下（正數層）"""
    levels = {anchor_id: 0}
    q = deque([anchor_id])
    while q:
        cur = q.popleft()
        cur_lvl = levels[cur]

        # 子女：層 +1
        for kid in children_of_parent(cur):
            if kid not in levels or cur_lvl + 1 < levels[kid]:
                levels[kid] = cur_lvl + 1
                q.append(kid)

        # 父母：層 -1
        for par in parents_of_child(cur):
            if par not in levels or cur_lvl - 1 > levels[par]:
                levels[par] = cur_lvl - 1
                q.append(par)

        # 配偶：同層
        for m in marriages_of(cur):
            other = m["p2"] if m["p1"] == cur else m["p1"]
            if other not in levels:
                levels[other] = cur_lvl
                q.append(other)

    # 可能有孤立節點（未連到 anchor），仍給 0 層
    for pid in st.session_state["persons"]:
        if pid not in levels:
            levels[pid] = 0

    return levels  # pid -> level (負數在上)

def order_spouses_in_block(m, anchor_id=None):
    """回傳此婚姻內部左右順序（left_id, right_id）。
    規則：
    1) 若其中一方有前任，盡量讓「有前任」那一方在左、現任在右（貼近中文閱讀直覺）。
    2) 若兩方皆無前任或無法判定，則年長者在左（出生年小者在左）。
    3) 若與 anchor 是其中之一，且此婚姻為「current」，盡量讓 anchor 在左、配偶在右。
    """
    p1, p2 = m["p1"], m["p2"]
    status = m.get("status", "current")
    ex_cnt, _ = person_spouse_counts()

    # Anchor 優先（若此段是現任婚姻）
    if status == "current" and anchor_id in (p1, p2):
        if anchor_id == p1:
            return (p1, p2)
        else:
            return (p2, p1)

    # 有前任的人偏左，另一側作為其現任（視覺上 "人-現任" 朝右）
    p1_ex = ex_cnt.get(p1, 0)
    p2_ex = ex_cnt.get(p2, 0)
    if p1_ex != p2_ex:
        if p1_ex > p2_ex:
            return (p1, p2)
        else:
            return (p2, p1)

    # 年長者在左
    left, right = sorted([p1, p2], key=age_order_key)
    return (left, right)

# -----------------------------
# 版面配置計算（核心）
# -----------------------------
X_STEP = 180
Y_STEP = 160
COUPLE_GAP = 20
MARRIAGE_Y_OFFSET = 30

def layout_positions(levels, anchor_id=None):
    """計算每個人與婚姻節點的 (x, y) 位置，避免邊線交錯、兄弟姊妹依年齡排序。
       回傳：pos_persons: pid -> (x,y), pos_marriages: mid -> (x,y)
    """
    # 按層收集
    layer_to_people = defaultdict(list)
    for pid, lvl in levels.items():
        layer_to_people[lvl].append(pid)

    # 層由上至下排序（上方為負數）
    layers_sorted = sorted(layer_to_people.keys())

    pos_persons = {}
    pos_marriages = {}

    # 第一階段：同層內先對「現任婚姻」建立 couple block，盡量相鄰；其它單身/前任再穿插
    for lvl in layers_sorted:
        people = layer_to_people[lvl]

        # 找出此層的婚姻（雙方皆在同層）
        marriages_here = []
        for m in st.session_state["marriages"].values():
            if m["p1"] in people and m["p2"] in people:
                marriages_here.append(m)

        # 先過濾出「現任」婚姻，按年齡排序（較年長的夫婦靠左）
        cur_ms = [m for m in marriages_here if m["status"] == "current"]
        cur_ms.sort(key=lambda m: min(
            birth_year_of(m["p1"]) or 99999, birth_year_of(m["p2"]) or 99999))

        # 對已放置人員做紀錄
        placed = set()

        x_cursor = 0
        y_val = -lvl * Y_STEP  # 上面是負層，讓 y 值逐層往上
        # 先放現任婚姻
        for m in cur_ms:
            left, right = order_spouses_in_block(m, anchor_id=anchor_id)
            if left in placed or right in placed:
                continue
            pos_persons[left] = (x_cursor, y_val)
            pos_persons[right] = (x_cursor + X_STEP, y_val)
            # 婚姻節點放在兩人中點、略低
            pos_marriages[m["id"]] = (x_cursor + X_STEP // 2, y_val + MARRIAGE_Y_OFFSET)
            placed.add(left); placed.add(right)
            x_cursor += X_STEP * 2  # 夫婦佔兩格

        # 放同層剩餘人（單身/僅前任）
        remaining = [p for p in people if p not in placed]
        # 年長者靠左
        remaining.sort(key=age_order_key)
        for pid in remaining:
            pos_persons[pid] = (x_cursor, y_val)
            x_cursor += X_STEP

        # 為此層的「前任婚姻」建立婚姻節點（不強制兩人緊鄰，但仍建立 marriage node）
        ex_ms = [m for m in marriages_here if m["status"] == "former"]
        for m in ex_ms:
            p1, p2 = m["p1"], m["p2"]
            # 婚姻點放在兩者中點（若有人未定位則略過）
            if p1 in pos_persons and p2 in pos_persons:
                x1, y1 = pos_persons[p1]
                x2, y2 = pos_persons[p2]
                pos_marriages[m["id"]] = ((x1 + x2) // 2, y_val + MARRIAGE_Y_OFFSET)

    # 第二階段：將「子女」依婚姻節點投影至下一層，且兄弟姐妹依年齡由左到右
    # 採 family-first：以上一層 marriage 中點為中心，子女橫向展開
    # 建立每層已占用的 x 座標集合，避免互相覆蓋
    used_x_by_level = defaultdict(set)
    for pid, (x, y) in pos_persons.items():
        lvl = levels[pid]
        used_x_by_level[lvl].add(x)

    for m in st.session_state["marriages"].values():
        kids = children_of_marriage(m["id"])
        if not kids:
            continue
        # 父母層
        p_lvl = levels[m["p1"]]
        child_lvl = p_lvl + 1
        # 找婚姻節點的 x 作為中心
        if m["id"] not in pos_marriages:
            # 若未先前建立（如某配偶不同層），以單一父母位置代替
            base_x = 0
            if m["p1"] in pos_persons:
                base_x = pos_persons[m["p1"]][0]
            elif m["p2"] in pos_persons:
                base_x = pos_persons[m["p2"]][0]
            base_y = -p_lvl * Y_STEP + MARRIAGE_Y_OFFSET
            pos_marriages[m["id"]] = (base_x, base_y)
        mx, my = pos_marriages[m["id"]]

        # 子女水平展開（年長靠左），以 mx 為中心
        n = len(kids)
        start_x = int(mx - (n - 1) * (X_STEP // 2))
        for i, kid in enumerate(kids):
            target_x = start_x + i * X_STEP
            target_y = -child_lvl * Y_STEP

            # 若該層座標已被佔用，向右尋找空位
            while target_x in used_x_by_level[child_lvl]:
                target_x += X_STEP

            pos_persons[kid] = (target_x, target_y)
            used_x_by_level[child_lvl].add(target_x)

    return pos_persons, pos_marriages

# -----------------------------
# 視覺化（PyVis）
# -----------------------------
def render_graph(pos_persons, pos_marriages):
    net = Network(height="720px", width="100%", directed=False, bgcolor="#ffffff")
    net.toggle_physics(False)  # 使用固定座標

    # 加入人物節點
    for pid, p in st.session_state["persons"].items():
        x, y = pos_persons.get(pid, (0, 0))
        label = person_label(p)
        net.add_node(
            pid,
            label=label,
            shape="box",
            x=x, y=y,
            physics=False,
            font={"multi": "html", "size": 18},
            borderWidth=1,
            color={"background": "#fff", "border": "#555"}
        )

    # 加入婚姻節點（小圓點）
    for mid, (x, y) in pos_marriages.items():
        m = st.session_state["marriages"].get(mid)
        dashes = True if (m and m.get("status") == "former") else False
        net.add_node(
            mid,
            label="",
            shape="dot",
            size=8,
            x=x, y=y,
            physics=False,
            color="#888"
        )

    # 連線：配偶 → 婚姻點
    for m in st.session_state["marriages"].values():
        mid = m["id"]
        p1, p2 = m["p1"], m["p2"]
        dashes = True if m["status"] == "former" else False
        if mid in pos_marriages:
            if p1 in pos_persons:
                net.add_edge(p1, mid, dashes=dashes, color="#666")
            if p2 in pos_persons:
                net.add_edge(p2, mid, dashes=dashes, color="#666")

    # 連線：婚姻點 → 子女
    for ch in st.session_state["children"]:
        mid = ch["marriage_id"]
        kid = ch["child_id"]
        if (mid in pos_marriages) and (kid in pos_persons):
            net.add_edge(mid, kid, color="#999")

    return net

# -----------------------------
# UI 元件
# -----------------------------
def sidebar_data_ops():
    st.sidebar.header("📦 資料維護")
    with st.sidebar.expander("➕ 新增人物", expanded=False):
        name = st.text_input("姓名", key="p_name")
        by = st.text_input("出生年（選填）", key="p_by")
        gender = st.selectbox("性別（選填）", ["", "男", "女", "其他"], index=0, key="p_gender")
        note = st.text_area("備註（選填）", key="p_note", height=80)
        if st.button("新增人物", use_container_width=True):
            pid = add_person(name, by, gender, note)
            st.success(f"已新增人物：{get_person(pid)['name']}")

    with st.sidebar.expander("💍 建立婚姻", expanded=False):
        all_people = list(st.session_state["persons"].values())
        opts = {f"{p['name']} ({p.get('birth_year','?')})": p["id"] for p in all_people}
        if not opts:
            st.info("請先新增人物")
        else:
            c1, c2 = st.columns(2)
            with c1:
                p1_label = st.selectbox("配偶 A", list(opts.keys()), key="m_p1") if opts else ""
            with c2:
                p2_label = st.selectbox("配偶 B", list(opts.keys()), key="m_p2") if opts else ""
            status = st.radio("婚姻狀態", ["current", "former"], horizontal=True, key="m_status")
            if st.button("建立婚姻", use_container_width=True, key="btn_add_marriage"):
                if p1_label and p2_label and opts[p1_label] != opts[p2_label]:
                    add_marriage(opts[p1_label], opts[p2_label], status)
                    st.success("已建立婚姻")
                else:
                    st.error("請選擇兩位不同的人物")

    with st.sidebar.expander("👶 在婚姻下新增子女", expanded=False):
        if not st.session_state["marriages"]:
            st.info("請先建立婚姻")
        else:
            m_opts = {}
            for m in st.session_state["marriages"].values():
                p1 = get_person(m["p1"])["name"]
                p2 = get_person(m["p2"])["name"]
                tag = "現任" if m["status"] == "current" else "前任"
                m_opts[f"{p1} ⟷ {p2}（{tag}）"] = m["id"]
            m_label = st.selectbox("選擇婚姻", list(m_opts.keys()))
            # 選現有人物或新建
            all_people = list(st.session_state["persons"].values())
            opts_child = {"（新增新人物）": None}
            for p in all_people:
                opts_child[f"{p['name']} ({p.get('birth_year','?')})"] = p["id"]
            copt = st.selectbox("選擇子女（或新增）", list(opts_child.keys()))
            if opts_child[copt] is None:
                cname = st.text_input("新子女姓名")
                cby = st.text_input("新子女出生年（選填）")
                cgender = st.selectbox("新子女性別（選填）", ["", "男", "女", "其他"], index=0)
            else:
                cname = None; cby = None; cgender = None

            if st.button("新增子女到此婚姻", use_container_width=True):
                kid_id = opts_child[copt]
                if kid_id is None:
                    kid_id = add_person(cname or "未命名", cby, cgender, None)
                add_child(m_opts[m_label], kid_id)
                st.success("已新增子女")

    with st.sidebar.expander("🧭 Anchor/視角人物", expanded=False):
        if st.session_state["persons"]:
            opts = {p["name"]: p["id"] for p in st.session_state["persons"].values()}
            cur = st.session_state["anchor_id"]
            default_idx = 0
            if cur:
                # 嘗試將 anchor 放在預設
                try:
                    default_idx = list(opts.values()).index(cur)
                except Exception:
                    default_idx = 0
            sel = st.selectbox("選擇視角人物", list(opts.keys()), index=default_idx)
            st.session_state["anchor_id"] = opts[sel]
        else:
            st.info("請先新增人物")

    st.sidebar.divider()
    with st.sidebar.expander("🗂 匯入 / 匯出", expanded=False):
        exp = {
            "persons": st.session_state["persons"],
            "marriages": st.session_state["marriages"],
            "children": st.session_state["children"],
        }
        st.text_area("匯出 JSON（唯讀）", value=json.dumps(exp, ensure_ascii=False, indent=2), height=220)
        up = st.text_area("匯入 JSON（貼上後按下方按鈕）", height=160, placeholder="貼上先前匯出的 JSON")
        if st.button("匯入資料（將覆蓋現有）", use_container_width=True):
            try:
                data = json.loads(up)
                st.session_state["persons"] = data.get("persons", {})
                st.session_state["marriages"] = data.get("marriages", {})
                st.session_state["children"] = data.get("children", [])
                st.success("已匯入資料")
            except Exception as e:
                st.error(f"JSON 解析失敗：{e}")

    st.sidebar.divider()
    if st.sidebar.button("🧹 整體重排（套用自動排序規則）", use_container_width=True):
        # 重新計算座標
        anchor = st.session_state.get("anchor_id") or (next(iter(st.session_state["persons"].keys())) if st.session_state["persons"] else None)
        if anchor:
            lv = compute_generations(anchor)
            pos_p, pos_m = layout_positions(lv, anchor_id=anchor)
            st.session_state["positions"] = {"persons": pos_p, "marriages": pos_m}
            st.sidebar.success("已完成整體重排")
        else:
            st.sidebar.info("尚無人物可排版")

    st.sidebar.divider()
    if st.sidebar.button("🧪 一鍵載入示例資料", use_container_width=True):
        seed_example()
        st.sidebar.success("已載入示例資料（可立即重排查看）")

def seed_example():
    st.session_state["persons"].clear()
    st.session_state["marriages"].clear()
    st.session_state["children"].clear()

    # 與使用者此前案例相近的人名，做測試
    pid_father = add_person("陳志明", 1962, "男")
    pid_mother = add_person("王春嬌", 1965, "女")
    pid_exwife = add_person("陳前妻", 1963, "女")
    pid_m1 = add_marriage(pid_father, pid_mother, "current")
    pid_m0 = add_marriage(pid_father, pid_exwife, "former")

    # 子女（示範：年長者靠左）
    c1 = add_person("陳小明", 1988, "男")
    c2 = add_person("陳小芳", 1990, "女")
    c3 = add_person("二代1", 1992, "男")
    c4 = add_person("二代2", 1995, "女")
    add_child(pid_m1, c1)
    add_child(pid_m1, c2)
    add_child(pid_m1, c3)
    add_child(pid_m1, c4)

    # 小明的現任配偶與前任測試
    ex = add_person("王子前任", 1989, "女")
    wife = add_person("王子妻", 1991, "女")
    m_ex = add_marriage(c1, ex, "former")
    m_cur = add_marriage(c1, wife, "current")

    # 再給兩個孩子測試排序
    k1 = add_person("陳二", 2016, "男")
    k2 = add_person("陳三", 2019, "男")
    add_child(m_cur, k1)
    add_child(m_cur, k2)

    # 預設 anchor
    st.session_state["anchor_id"] = c1  # 以陳小明為視角測試

# -----------------------------
# 主畫面
# -----------------------------
def main():
    init_state()
    st.title("🌳 家族樹｜自動排序 & 配偶位置優化")
    st.caption("兄弟姐妹依年齡由左到右、現任配偶在右、前任在左；支援縮放/平移/拖曳與一鍵重排。")

    sidebar_data_ops()

    # 計算座標（若尚未計算，先做一次）
    anchor = st.session_state.get("anchor_id") or (next(iter(st.session_state["persons"].keys())) if st.session_state["persons"] else None)
    if anchor:
        levels = compute_generations(anchor)
        pos_p, pos_m = layout_positions(levels, anchor_id=anchor)
    else:
        levels = {}
        pos_p, pos_m = {}, {}

    # 若用戶剛按過「整體重排」，優先採用 session_state 儲存的結果
    saved = st.session_state.get("positions")
    if saved and "persons" in saved and "marriages" in saved:
        pos_p, pos_m = saved["persons"], saved["marriages"]
    else:
        st.session_state["positions"] = {"persons": pos_p, "marriages": pos_m}

    # 視覺化
    net = render_graph(pos_p, pos_m)
    html = net.generate_html()
    st.components.v1.html(html, height=760, scrolling=True)

    # 簡要統計
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("人物數", len(st.session_state["persons"]))
    with c2:
        st.metric("婚姻數", len(st.session_state["marriages"]))
    with c3:
        st.metric("親子連結", len(st.session_state["children"]))

    with st.expander("📝 資料檢視（唯讀）", expanded=False):
        st.json({
            "persons": st.session_state["persons"],
            "marriages": st.session_state["marriages"],
            "children": st.session_state["children"],
        })

if __name__ == "__main__":
    main()

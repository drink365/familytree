import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

# -------------------------------
# Session & Data Management
# -------------------------------

def _empty_data():
    """返回一個空的資料結構。"""
    return {
        "persons": {},          # pid -> {name, sex('男'/'女'), alive(True/False), note}
        "marriages": {},        # mid -> {a, b, divorced(bool)}
        "children": [],         # list of {mid, child}
        "sibling_links": [],    # list of (pid1, pid2) (無序對；用排序後的tuple去重)
        "_seq": 0,              # 用於生成 ID
    }

def ensure_session():
    """確保 session state 中有資料結構。"""
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def next_id():
    """生成一個新的唯一 ID。"""
    st.session_state.data["_seq"] += 1
    return str(st.session_state.data["_seq"])

# -------------------------------
# Demo Data Loader
# -------------------------------

def ensure_person(name, sex="男", alive=True, note=""):
    """根據姓名尋找或建立人物，返回 pid。"""
    d = st.session_state.data
    for pid, p in d["persons"].items():
        if p["name"] == name:
            return pid
    pid = next_id()
    d["persons"][pid] = {"name": name, "sex": sex, "alive": alive, "note": note}
    return pid

def add_marriage(a, b, divorced=False):
    """新增婚姻關係，返回 mid。"""
    d = st.session_state.data
    # 檢查是否已存在相同的婚姻關係
    for mid, m in d["marriages"].items():
        if {m["a"], m["b"]} == {a, b}:
            return mid
    mid = f"M{next_id()}"
    d["marriages"][mid] = {"a": a, "b": b, "divorced": divorced}
    return mid

def add_child(mid, child_pid):
    """新增子女關係。"""
    d = st.session_state.data
    # 避免重複添加
    if not any(c["mid"] == mid and c["child"] == child_pid for c in d["children"]):
        d["children"].append({"mid": mid, "child": child_pid})

def load_demo(clear=False):
    """載入一個示範用的家族資料。"""
    if clear:
        st.session_state.data = _empty_data()

    # 第一代
    p1 = ensure_person("陳大明", "男", False)
    p2 = ensure_person("林秀英", "女", False)
    m1 = add_marriage(p1, p2)

    # 第二代
    p3 = ensure_person("陳一郎", "男", True)
    p4 = ensure_person("王美惠", "女", True)
    p5 = ensure_person("陳二妹", "女", True)
    p6 = ensure_person("李國強", "男", True)
    add_child(m1, p3)
    add_child(m1, p5)
    m2 = add_marriage(p3, p4)
    m3 = add_marriage(p6, p5)

    # 第三代
    p7 = ensure_person("陳小龍", "男", True)
    p8 = ensure_person("陳小鳳", "女", True)
    p9 = ensure_person("李文傑", "男", True)
    add_child(m2, p7)
    add_child(m2, p8)
    add_child(m3, p9)

# -------------------------------
# Data Helper Functions
# -------------------------------

def get_person_options():
    """獲取所有人物選項，用於下拉選單。"""
    return {pid: p["name"] for pid, p in st.session_state.data["persons"].items()}

def get_marriage_options():
    """獲取所有婚姻關係選項。"""
    d = st.session_state.data
    return {mid: f"{d['persons'][m['a']]['name']} & {d['persons'][m['b']]['name']}"
            for mid, m in d["marriages"].items()}

def show_names(pids):
    """根據 pids 列表顯示姓名，若為空則顯示 '無'。"""
    if not pids: return "無"
    d = st.session_state.data
    return "、".join(d["persons"][pid]["name"] for pid in pids)

def build_child_map():
    """建立 parent_map 和 child_map 以便快速查找。"""
    d = st.session_state.data
    child_map = defaultdict(list)  # mid -> [child_pids]
    parent_map = defaultdict(set) # child_pid -> {parent_pids}
    for row in d["children"]:
        mid, child = row["mid"], row["child"]
        child_map[mid].append(child)
        m = d["marriages"][mid]
        parent_map[child].add(m["a"])
        parent_map[child].add(m["b"])
    return child_map, parent_map

# -------------------------------
# UI: Person Management
# -------------------------------

def page_persons():
    st.subheader("人物管理")
    st.markdown("新增、編輯或刪除家族成員。")

    with st.expander("➕ 新增人物", expanded=True):
        with st.form("add_person_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("姓名*", placeholder="例如：王小明")
            sex = c2.selectbox("性別*", ["男", "女"])
            alive = c3.selectbox("存歿*", ["存", "殁"])
            note = st.text_input("備註（選填）", placeholder="例如：排行、職業等")
            submitted = st.form_submit_button("新增人物", type="primary")
            if submitted and name:
                pid = next_id()
                st.session_state.data["persons"][pid] = {
                    "name": name, "sex": sex, "alive": alive == "存", "note": note
                }
                st.success(f"已新增「{name}」。")
                st.rerun()

    st.divider()
    persons = st.session_state.data["persons"]
    if not persons:
        st.info("目前沒有任何人物資料。")
        return

    st.write("**現有成員列表**")
    cols = st.columns([2, 1, 1, 3, 1])
    headers = ["姓名", "性別", "存歿", "備註", "操作"]
    for col, header in zip(cols, headers):
        col.write(f"**{header}**")

    for pid, p in persons.items():
        cols = st.columns([2, 1, 1, 3, 1])
        cols[0].write(p["name"])
        cols[1].write(p["sex"])
        cols[2].write("存" if p["alive"] else "殁")
        cols[3].write(p["note"])
        if cols[4].button("刪除", key=f"del_p_{pid}", type="secondary"):
            # TODO: 增加刪除前的二次確認和相關關係的處理
            st.session_state.data["persons"].pop(pid, None)
            # 這裡也應該清理相關的關係
            st.rerun()

# -------------------------------
# UI: Relationship Management
# -------------------------------

def page_relations():
    st.subheader("關係管理")
    st.markdown("定義成員之間的婚姻、親子與手足關係。")
    person_opts = get_person_options()

    if len(person_opts) < 2:
        st.warning("請先新增至少兩位人物，才能建立關係。")
        return

    # --- 婚姻關係 ---
    with st.expander("💍 新增/管理婚姻關係", expanded=True):
        with st.form("add_marriage_form", clear_on_submit=True):
            st.write("**建立新的婚姻關係**")
            c1, c2, c3 = st.columns(3)
            a = c1.selectbox("配偶 A", person_opts.keys(), format_func=lambda x: person_opts[x])
            b = c2.selectbox("配偶 B", person_opts.keys(), format_func=lambda x: person_opts[x])
            divorced = c3.checkbox("已離婚")
            submitted = st.form_submit_button("建立婚姻", type="primary")
            if submitted:
                if a == b:
                    st.error("不能選擇同一個人。")
                else:
                    add_marriage(a, b, divorced)
                    st.success("已建立婚姻關係。")
                    st.rerun()

        st.divider()
        st.write("**現有婚姻列表**")
        marriages = st.session_state.data["marriages"]
        if not marriages:
            st.info("尚無婚姻關係。")
        else:
            for mid, m in marriages.items():
                st.text(f"• {person_opts[m['a']]} 與 {person_opts[m['b']]} {'(已離婚)' if m['divorced'] else ''}")

    # --- 子女關係 ---
    with st.expander("👶 新增子女關係"):
        marriage_opts = get_marriage_options()
        if not marriage_opts:
            st.info("請先建立婚姻關係，才能新增子女。")
        else:
            with st.form("add_child_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                mid = c1.selectbox("父母*", marriage_opts.keys(), format_func=lambda x: marriage_opts[x])
                child_pid = c2.selectbox("子女*", person_opts.keys(), format_func=lambda x: person_opts[x])
                submitted = st.form_submit_button("新增子女", type="primary")
                if submitted:
                    add_child(mid, child_pid)
                    st.success("已新增子女關係。")
                    st.rerun()

    # --- 手足關係 ---
    with st.expander("🧑‍🤝‍🧑 手動新增兄弟姊妹關係"):
        st.caption("注意：若已設定共同父母，則系統會自動視為手足，不需手動新增。此功能用於連結父母不詳或關係複雜的同輩。")
        with st.form("add_sibling_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            a = c1.selectbox("手足 A", person_opts.keys(), format_func=lambda x: person_opts[x])
            b = c2.selectbox("手足 B", person_opts.keys(), format_func=lambda x: person_opts[x])
            submitted = st.form_submit_button("新增手足連結", type="primary")
            if submitted:
                if a == b:
                    st.error("不能選擇同一個人。")
                else:
                    # 排序以確保唯一性
                    link = tuple(sorted((a, b)))
                    if link not in st.session_state.data["sibling_links"]:
                        st.session_state.data["sibling_links"].append(link)
                        st.success("已新增手足連結。")
                    else:
                        st.warning("此連結已存在。")
                    st.rerun()

# -------------------------------
# Logic: Inheritance Calculation
# -------------------------------

def find_heirs(decedent_pid):
    d = st.session_state.data
    persons = d["persons"]
    if not persons.get(decedent_pid) or persons[decedent_pid]["alive"]:
        return {"error": "指定的人物不存在或仍然在世。"}

    child_map, parent_map = build_child_map()

    def get_spouse(pid):
        for m in d["marriages"].values():
            if pid in {m["a"], m["b"]} and not m["divorced"]:
                other = m["b"] if m["a"] == pid else m["a"]
                if persons[other]["alive"]:
                    return other
        return None

    def get_children(pid):
        children = []
        for m in d["marriages"].values():
            if pid in {m["a"], m["b"]}:
                mid = next(k for k, v in d["marriages"].items() if v == m)
                children.extend(child_map.get(mid, []))
        return children

    def get_parents(pid):
        return list(parent_map.get(pid, []))

    def get_siblings(pid):
        parents = get_parents(pid)
        if not parents: return []
        siblings = set()
        # 找到父母的所有婚姻
        for p_pid in parents:
            for m in d["marriages"].values():
                if p_pid in {m["a"], m["b"]}:
                    mid = next(k for k, v in d["marriages"].items() if v == m)
                    for c in child_map.get(mid, []):
                        if c != pid:
                            siblings.add(c)
        return list(siblings)

    spouse = get_spouse(decedent_pid)
    heirs = {spouse} if spouse else set()

    # Rank 1: 直系血親卑親屬
    descendants = []
    q = deque(get_children(decedent_pid))
    visited = set(q)
    while q:
        curr_pid = q.popleft()
        if persons[curr_pid]["alive"]:
            descendants.append(curr_pid)
        else: # 代位繼承
            grandchildren = get_children(curr_pid)
            for gc in grandchildren:
                if gc not in visited:
                    q.append(gc)
                    visited.add(gc)

    if descendants:
        heirs.update(descendants)
        return {"rank": 1, "heirs": list(heirs)}

    # Rank 2: 父母
    parents = [p for p in get_parents(decedent_pid) if persons[p]["alive"]]
    if parents:
        heirs.update(parents)
        return {"rank": 2, "heirs": list(heirs)}

    # Rank 3: 兄弟姊妹
    siblings = [s for s in get_siblings(decedent_pid) if persons[s]["alive"]]
    if siblings:
        heirs.update(siblings)
        return {"rank": 3, "heirs": list(heirs)}

    # Rank 4: 祖父母
    grandparents = []
    for p_pid in get_parents(decedent_pid):
        grandparents.extend(gp for gp in get_parents(p_pid) if persons[gp]["alive"])
    if grandparents:
        heirs.update(grandparents)
        return {"rank": 4, "heirs": list(heirs)}

    # 僅有配偶
    if spouse:
        return {"rank": 0, "heirs": [spouse]}

    return {"rank": -1, "heirs": []} # 無繼承人

# -------------------------------
# UI: Inheritance Page
# -------------------------------

def page_inheritance():
    st.subheader("⚖️ 法定繼承順位分析")
    person_opts = get_person_options()
    dead_person_opts = {pid: name for pid, name in person_opts.items() if not st.session_state.data["persons"][pid]["alive"]}

    if not dead_person_opts:
        st.warning("請先在「人物管理」中將某位成員的狀態設為「殁」，才能進行繼承分析。")
        return

    decedent_pid = st.selectbox("選擇被繼承人（僅顯示已歿者）", dead_person_opts.keys(), format_func=lambda x: dead_person_opts[x])

    if st.button("開始分析", type="primary"):
        result = find_heirs(decedent_pid)
        if "error" in result:
            st.error(result["error"])
            return

        st.success(f"**分析結果：** 被繼承人 **{dead_person_opts[decedent_pid]}**")

        spouse = get_spouse(decedent_pid)
        if spouse:
            st.markdown(f"**配偶（當然繼承人）**：{person_opts[spouse]}")
        else:
            st.markdown("**配偶**：無")

        rank_txt = {
            -1: "無繼承人，遺產歸屬國庫",
            0: "僅配偶為繼承人",
            1: "第一順位：直系血親卑親屬",
            2: "第二順位：父母",
            3: "第三順位：兄弟姊妹",
            4: "第四順位：祖父母",
        }
        st.markdown(f"**適用順位**：{rank_txt[result['rank']]}")
        st.markdown(f"**本順位繼承人**：{show_names(result['heirs'])}")

        st.caption("說明：依民法第1138條，配偶為當然繼承人；先檢視第一順位（直系卑親屬），無者再依序檢視第二至第四順位。代位繼承僅適用於直系卑親屬。")

# -------------------------------
# UI: Family Tree Drawing (Corrected Version)
# -------------------------------

COLOR_MALE   = "#d8eaff"
COLOR_FEMALE = "#ffdbe1"
COLOR_DEAD   = "#e6e6e6"
BORDER_COLOR = "#164b5f"

def person_node(dot, pid, p):
    """繪製單個人物節點。"""
    label = p["name"]
    if not p["alive"]:
        label += "（殁）"

    shape = "box" if p["sex"] == "男" else "ellipse"
    fill = COLOR_DEAD if not p["alive"] else (COLOR_MALE if p["sex"] == "男" else COLOR_FEMALE)

    dot.node(pid, label, shape=shape, style="filled", fillcolor=fill,
             color=BORDER_COLOR, fontcolor="#0b2430", penwidth="1.4")

def draw_tree():
    """繪製整個家族樹。"""
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")

    # 1. 繪製所有人物節點
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # 2. 處理婚姻與子女關係
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]

        # 建立一個代表「婚姻」的隱形中心節點
        dot.node(mid, "", shape="point", width="0", height="0")

        # 使用 subgraph 強制夫妻與婚姻中心點在同一水平階層 (rank)
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a)
            s.node(mid)
            s.node(b)
        
        # 將夫妻分別連到婚姻中心點，形成穩定水平線
        style = "dashed" if divorced else "solid"
        dot.edge(a, mid, dir="none", style=style, color=BORDER_COLOR)
        dot.edge(mid, b, dir="none", style=style, color=BORDER_COLOR)

        # 找出這段婚姻的所有子女
        kids = [row["child"] for row in d["children"] if row["mid"] == mid]
        if kids:
            # 從婚姻中心點連線到每個子女，形成乾淨的垂直線
            for c in kids:
                dot.edge(mid, c, color=BORDER_COLOR)

    # 3. 處理手動指定的兄弟姊妹關係
    _, parent_map = build_child_map()
    def has_same_parents(x, y):
        px = parent_map.get(x, set())
        py = parent_map.get(y, set())
        return px and px == py

    for a, b in d["sibling_links"]:
        if has_same_parents(a, b):
            continue
        # 僅在沒有共同父母時才手動繪製連結
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a)
            s.node(b)
        dot.edge(a, b, style="dashed", color=BORDER_COLOR, dir="none")

    st.graphviz_chart(dot, use_container_width=True)


def page_tree():
    st.subheader("🧬 家族樹")
    draw_tree()

# -------------------------------
# Main App Layout
# -------------------------------

st.set_page_config(page_title="家族平台", layout="wide")
ensure_session()

st.title("🌳 家族平台")
st.caption("一個用於管理家族成員、關係、分析法定繼承順位並視覺化家族樹的工具。")

# --- Actions Bar ---
c1, c2 = st.columns([1, 1])
with c1:
    if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
        load_demo(clear=True)
        st.success("已載入示範資料。")
        st.rerun()
with c2:
    with st.popover("🧹 開始我的資料（清空）", use_container_width=True):
        st.warning("此動作會刪除目前所有資料，且無法復原。")
        agree = st.checkbox("我了解並同意清空")
        if st.button("確認清空", disabled=not agree):
            st.session_state.data = _empty_data()
            st.success("已清空所有資料。")
            st.rerun()

st.divider()

# --- Main Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["人物管理", "關係管理", "法定繼承分析", "家族樹"])

with tab1:
    page_persons()

with tab2:
    page_relations()

with tab3:
    page_inheritance()

with tab4:
    page_tree()

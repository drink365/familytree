# app.py
import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

# -------------------------------
# Session & Data
# -------------------------------

def _empty_data():
    return {
        "persons": {},          # pid -> {name, sex('男'/'女'), alive(True/False), note}
        "marriages": {},        # mid -> {a, b, divorced(bool)}
        "children": [],         # list of {mid, child}
        "sibling_links": [],    # list of (pid1, pid2)  (無序對；用排序後的tuple去重)
        "_seq": 0,              # for id generation
        "_demo_loaded": False,
    }

def _ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def _new_id(d: dict, prefix: str) -> str:
    d["_seq"] += 1
    return f"{prefix}{d['_seq']}"

# -------------------------------
# CRUD helpers
# -------------------------------

def add_person(name, sex, alive=True, note=""):
    d = st.session_state.data
    pid = _new_id(d, "P")
    d["persons"][pid] = {"name": name.strip() or "（未命名）", "sex": sex, "alive": bool(alive), "note": note.strip()}
    return pid

def update_person(pid, name=None, sex=None, alive=None, note=None):
    d = st.session_state.data
    if pid not in d["persons"]:
        return
    if name is not None:
        d["persons"][pid]["name"] = name.strip()
    if sex is not None:
        d["persons"][pid]["sex"] = sex
    if alive is not None:
        d["persons"][pid]["alive"] = bool(alive)
    if note is not None:
        d["persons"][pid]["note"] = note.strip()

def remove_person(pid):
    d = st.session_state.data
    if pid in d["persons"]:
        del d["persons"][pid]
    # also clean marriages & children & sibling links
    mids_to_del = [mid for mid, m in d["marriages"].items() if m["a"] == pid or m["b"] == pid]
    for mid in mids_to_del:
        if mid in d["marriages"]:
            del d["marriages"][mid]
        d["children"] = [row for row in d["children"] if row["mid"] != mid]
    d["children"] = [row for row in d["children"] if row["child"] != pid]
    # sibling links
    cleaned = []
    for x, y in d["sibling_links"]:
        if x == pid or y == pid:
            continue
        cleaned.append((x, y))
    d["sibling_links"] = cleaned

def list_persons():
    return st.session_state.data["persons"]

def add_marriage(a, b, divorced=False, anchor='mid'):
    """
    anchor: 'mid' 夫妻中點；'a' 配偶A下方；'b' 配偶B下方
    """
    d = st.session_state.data
    # 如果已存在同一對，直接更新
    for mid, m in d["marriages"].items():
        if {m["a"], m["b"]} == {a, b}:
            m["divorced"] = bool(divorced)
            m["anchor"] = m.get("anchor", anchor)
            return mid
    mid = _new_id(d, "M")
    d["marriages"][mid] = {"a": a, "b": b, "divorced": bool(divorced), "anchor": anchor}
    return mid

def add_child(mid, child):
    d = st.session_state.data
    d["children"].append({"mid": mid, "child": child})

def remove_marriage(mid):
    d = st.session_state.data
    if mid in d["marriages"]:
        del d["marriages"][mid]
    d["children"] = [row for row in d["children"] if row["mid"] != mid]

def build_child_map():
    """
    返回:
        children_map: mid -> [child_ids]
        parent_map  : child -> set([parent_ids]) (如果能推得)
    """
    d = st.session_state.data
    children_map = defaultdict(list)
    for row in d["children"]:
        children_map[row["mid"]].append(row["child"])
    parent_map = defaultdict(set)
    for mid, m in d["marriages"].items():
        a, b = m["a"], m["b"]
        for c in children_map.get(mid, []):
            if a in d["persons"]:
                parent_map[c].add(a)
            if b in d["persons"]:
                parent_map[c].add(b)
    return children_map, parent_map

def add_sibling_link(x, y):
    if x == y:
        return
    d = st.session_state.data
    pair = tuple(sorted([x, y]))
    if pair not in d["sibling_links"]:
        d["sibling_links"].append(pair)

# -------------------------------
# Graphviz Node/Edge
# -------------------------------

BORDER_COLOR = "#333333"
MALE_COLOR   = "#E3F2FD"
FEMALE_COLOR = "#FCE4EC"
DECEASED_BG  = "#F5F5F5"
DECEASED_TXT = "#9E9E9E"

def person_node(dot: Digraph, pid, p):
    label = p["name"]
    fillcolor = MALE_COLOR if p["sex"] == "男" else FEMALE_COLOR
    fontcolor = BORDER_COLOR
    if not p["alive"]:
        fillcolor = DECEASED_BG
        fontcolor = DECEASED_TXT
    dot.node(pid,
             label=label,
             shape="box",
             style="rounded,filled",
             color=BORDER_COLOR,
             fillcolor=fillcolor,
             fontcolor=fontcolor)

# -------------------------------
# Demo
# -------------------------------

def load_demo():
    d = st.session_state.data = _empty_data()
    # 建幾個人
    a = add_person("當事人", "男", True)
    x1 = add_person("前任A", "女", True)
    x2 = add_person("前任B", "女", True)
    c1 = add_person("現任", "女", True)
    s1 = add_person("子1", "男", True)
    s2 = add_person("子2", "女", True)
    s3 = add_person("子3", "男", True)
    # 婚姻：與前任A(離婚)、與現任(未離)
    m1 = add_marriage(a, x1, divorced=True, anchor="b")   # 孩子從前任A的一側往下
    m2 = add_marriage(a, c1, divorced=False, anchor="a")  # 孩子從當事人這一側往下
    add_child(m2, s1)
    add_child(m2, s2)
    add_child(m1, s3)
    st.session_state.data["_demo_loaded"] = True

# -------------------------------
# Inheritance (簡易試算占位)
# -------------------------------

def page_inheritance():
    st.subheader("⚖️ 法定繼承試算（簡易）")
    st.caption("此頁為範例占位，僅示意。")
    d = st.session_state.data
    st.json({"persons": d["persons"], "marriages": d["marriages"], "children": d["children"]})

# -------------------------------
# Drawing
# -------------------------------

def draw_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    dot = Digraph("Family", format="svg", engine="dot")
    dot.graph_attr.update(
        rankdir="TB",
        splines="ortho",
        nodesep="0.5",
        ranksep="0.7",
        concentrate="false",   # 重要：避免把多條邊合併成一條
    )

    # 節點
    for pid, p in d["persons"].items():
        person_node(dot, pid, p)

    # —— 多段婚姻：配偶分列於當事人兩側（不固定左右），且相鄰 ——
    spouse_groups = {}
    for mid, m in d["marriages"].items():
        a, b, _div = m["a"], m["b"], m["divorced"]
        spouse_groups.setdefault(a, []).append(b)
        spouse_groups.setdefault(b, []).append(a)

    for person, sids in spouse_groups.items():
        if len(sids) < 2:
            continue
        try:
            sids_sorted = sorted(sids, key=lambda x: d["persons"][x]["name"])
        except Exception:
            sids_sorted = sorted(sids)
        left  = sids_sorted[::2]
        right = sids_sorted[1::2]
        seq = left + [person] + right
        with dot.subgraph() as s:
            s.attr(rank="same", ordering="out")
            for n in seq:
                s.node(n)
            # 高權重 + 有約束的不可見邊 → 保證水平相鄰
            for i in range(len(seq) - 1):
                s.edge(seq[i], seq[i+1], style="invis", weight="100", constraint="true", minlen="1")

    # —— 夫妻（婚姻接點）+ 子女 —— 
    # anchor：mid=夫妻中點、a=配偶A下方、b=配偶B下方
    for mid, m in d["marriages"].items():
        a, b, divorced = m["a"], m["b"], m["divorced"]
        anchor = m.get("anchor", "mid")
        jn = f"J_{mid}"

        # 用不可見的小方塊做接點（有上下port，才能強制垂直）
        dot.node(
            jn, "",
            shape="box", width="0.01", height="0.01",
            style="invis", fixedsize="true", color=BORDER_COLOR
        )

        style = "dashed" if divorced else "solid"

        # 夫妻同一水平
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

        if anchor == "mid":
            # A — jn — B：兩段可見橫線；jn 與 A/B 同 rank，看起來像一條直線
            with dot.subgraph() as s:
                s.attr(rank="same")
                s.node(a); s.node(jn); s.node(b)
            dot.edge(a, jn, dir="none", style=style, color=BORDER_COLOR,
                     weight="100", minlen="1", tailport="e", headport="w")
            dot.edge(jn, b, dir="none", style=style, color=BORDER_COLOR,
                     weight="100", minlen="1", tailport="e", headport="w")
        elif anchor == "a":
            # 夫妻橫線 + 從 A 垂直下接點
            dot.edge(a, b, dir="none", style=style, color=BORDER_COLOR, constraint="false")
            dot.edge(a, jn, color=BORDER_COLOR,
                     weight="100", minlen="1", tailport="s", headport="n")
        else:
            # anchor == "b"
            dot.edge(a, b, dir="none", style=style, color=BORDER_COLOR, constraint="false")
            dot.edge(b, jn, color=BORDER_COLOR,
                     weight="100", minlen="1", tailport="s", headport="n")

        # 子女：一律從接點「純垂直」往下，不再形成水平幹線
        kids = [row["child"] for row in d["children"] if row["mid"] == mid]
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(jn, c, color=BORDER_COLOR,
                         weight="100", minlen="1", tailport="s", headport="n")

    # —— 無共同父母的兄弟姊妹（虛線水平相連） ——
    _, parent_map = build_child_map()
    def has_same_parents(x, y):
        return parent_map.get(x, set()) and parent_map.get(x, set()) == parent_map.get(y, set())

    sib_groups, visited = [], set()
    for pid in d["persons"].keys():
        if pid in visited:
            continue
        q, group = deque([pid]), set([pid])
        visited.add(pid)
        while q:
            cur = q.popleft()
            for x, y in d["sibling_links"]:
                other = None
                if x == cur: other = y
                elif y == cur: other = x
                if other and other not in visited and not has_same_parents(cur, other):
                    group.add(other); visited.add(other); q.append(other)
        if len(group) >= 2:
            sib_groups.append(sorted(list(group)))

    for grp in sib_groups:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for node in grp:
                s.node(node)
        for i in range(len(grp) - 1):
            dot.edge(grp[i], grp[i+1], style="dashed", color=BORDER_COLOR)

    st.graphviz_chart(dot)


# -------------------------------
# Pages
# -------------------------------

def page_people():
    d = st.session_state.data

    st.subheader("👤 人物")
    st.caption("先新增人物，再到「關係」分頁建立婚姻與子女。")

    # 新增人物
    with st.form("add_person"):
        st.markdown("**新增人物**")
        name = st.text_input("姓名", "")
        sex  = st.radio("性別", ["男", "女"], horizontal=True, index=0)
        alive = st.checkbox("尚在人世", value=True)
        note = st.text_input("備註", "")
        ok = st.form_submit_button("新增")
        if ok:
            add_person(name, sex, alive, note)
            st.success("已新增。")

    # 人物清單與編輯
    if not d["persons"]:
        with st.expander("快速載入示範資料"):
            if st.button("載入示範"):
                load_demo()
                st.success("已載入示範。")
        return

    st.markdown("**人物清單**")
    for pid, p in list(d["persons"].items()):
        with st.expander(f"{p['name']} ({p['sex']})"):
            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                new_name = st.text_input("姓名", value=p["name"], key=f"nm_{pid}")
                new_note = st.text_input("備註", value=p["note"], key=f"nt_{pid}")
            with col2:
                new_sex  = st.radio("性別", ["男", "女"], horizontal=True, index=0 if p["sex"]=="男" else 1, key=f"sx_{pid}")
                new_alive= st.checkbox("尚在人世", value=p["alive"], key=f"al_{pid}")
            with col3:
                if st.button("儲存", key=f"sv_{pid}"):
                    update_person(pid, new_name, new_sex, new_alive, new_note)
                    st.success("已更新。")
                if st.button("刪除", key=f"rm_{pid}"):
                    remove_person(pid)
                    st.warning("已刪除。")

def page_relations():
    d = st.session_state.data

    st.subheader("🔗 關係")
    st.caption("建立婚姻、子女與（無共同父母的）兄弟姊妹連結。")

    # 建立婚姻
    st.markdown("**建立婚姻**")
    if len(d["persons"]) < 2:
        st.info("至少需要兩個人物。")
    else:
        persons = d["persons"]
        options = {f"{p['name']} ({pid})": pid for pid, p in persons.items()}
        with st.form("add_marriage"):
            colA, colB, colC, colD = st.columns([2,2,1,2])
            with colA:
                a = st.selectbox("配偶A", list(options.keys()))
            with colB:
                b = st.selectbox("配偶B", list(options.keys()))
            with colC:
                divorced = st.checkbox("此婚姻為離婚/前配偶", value=False)
            with colD:
                anchor = st.radio("孩子連接點", ["夫妻中點","配偶A下方","配偶B下方"], index=0, horizontal=True)
            ok = st.form_submit_button("建立婚姻")
            if ok:
                a_id = options[a]; b_id = options[b]
                if a_id == b_id:
                    st.error("請選擇不同人物。")
                else:
                    anchor_key = {'夫妻中點':'mid','配偶A下方':'a','配偶B下方':'b'}[anchor]
                    add_marriage(a_id, b_id, divorced, anchor_key)
                    st.success("已建立婚姻。")

    # 建立子女
    st.markdown("**建立子女**")
    if not d["marriages"]:
        st.info("請先建立至少一段婚姻。")
    else:
        marriages_opt = {f"{d['persons'][m['a']]['name']} ❤️ {d['persons'][m['b']]['name']} ({mid})": mid for mid, m in d["marriages"].items() if m["a"] in d["persons"] and m["b"] in d["persons"]}
        persons_opt   = {f"{p['name']} ({pid})": pid for pid, p in d["persons"].items()}
        with st.form("add_child"):
            col1, col2 = st.columns([2,2])
            with col1:
                mid_label = st.selectbox("選擇婚姻", list(marriages_opt.keys()))
            with col2:
                child_label = st.selectbox("選擇子女", list(persons_opt.keys()))
            ok = st.form_submit_button("建立子女")
            if ok:
                add_child(marriages_opt[mid_label], persons_opt[child_label])
                st.success("已建立子女關係。")

    # 無共同父母之兄弟姊妹（手動）
    st.markdown("**無共同父母之兄弟姊妹（手動連結）**")
    if len(d["persons"]) < 2:
        st.info("至少需要兩個人物。")
    else:
        persons_opt = {f"{p['name']} ({pid})": pid for pid, p in d["persons"].items()}
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            s1 = st.selectbox("兄弟/姊妹 1", list(persons_opt.keys()), key="sib1")
        with col2:
            s2 = st.selectbox("兄弟/姊妹 2", list(persons_opt.keys()), key="sib2")
        with col3:
            if st.button("建立無共同父母之兄弟姊妹連結"):
                add_sibling_link(persons_opt[s1], persons_opt[s2])
                st.success("已建立。")

def page_tree():
    st.subheader("🧬 家族樹")
    st.caption('FT-v20250824-1219')
    draw_tree()

# -------------------------------
# App
# -------------------------------

def main():
    _ensure_session()

    st.set_page_config(page_title="家庭樹", page_icon="🌳", layout="wide")
    st.title("📚 家庭樹平台")
    st.caption("建立人物、婚姻與子女關係，並產生清晰的家族關係圖。")

    # 操作說明
    with st.expander("使用提示", expanded=False):
        st.markdown(
            """
            - 夫妻之間一律**橫線**：現任＝實線、前任＝虛線  
            - 建立婚姻時可選擇**孩子連接點**（夫妻中點 / 配偶A下方 / 配偶B下方）  
            - 若同一人有多段婚姻，系統自動讓**配偶分列在當事人的兩側**，且**相鄰**，減少長距離繞線  
            - 可在「關係」頁新增「無共同父母」的兄弟姊妹連結（會以虛線水平相連）
            """
        )

    tab1, tab2, tab3, tab4 = st.tabs(["人物", "關係", "法定繼承試算", "家族樹"])

    with tab1:
        page_people()
    with tab2:
        page_relations()
    with tab3:
        page_inheritance()
    with tab4:
        page_tree()

if __name__ == "__main__":
    main()

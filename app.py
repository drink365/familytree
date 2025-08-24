# app.py  — 家族平台（人物 | 關係 | 家族樹）
# 特色：可把原本不在樹上的人，透過「兄弟姐妹」掛接進來（虛擬父母 junction）

import streamlit as st
from graphviz import Digraph

# ---------------- Session 初始化 ----------------
def _blank():
    return {
        "_seq": 0,
        "persons": {},          # {pid: {name, gender("男"/"女"), deceased(bool)}}
        "marriages": {},        # {mid: {p1, p2, dashed(bool)}}
        "children": {},         # {mid: [pid, ...]}  (婚姻的孩子)
        "parents_of": {},       # {pid: mid}  (孩子 -> 父母的婚姻/父母junction)
        "sibling_junctions": {} # {mid: {"type":"junction"}}  (沒有顯示父母，只用來群組兄弟姐妹)
    }

if "data" not in st.session_state:
    st.session_state.data = _blank()

DATA = st.session_state.data

# ---------------- 工具 ----------------
def _next_id(prefix="P"):
    DATA["_seq"] += 1
    return f"{prefix}{DATA['_seq']}"

def add_person(name, gender, deceased=False):
    pid = _next_id("P")
    DATA["persons"][pid] = {"name": name.strip(), "gender": gender, "deceased": deceased}
    return pid

def ensure_person(name, gender, deceased=False):
    # 以名字比對（簡化）－實務可再精緻化
    for pid, p in DATA["persons"].items():
        if p["name"].strip() == name.strip():
            # 同步更新基本屬性
            p["gender"] = gender
            p["deceased"] = deceased
            return pid
    return add_person(name, gender, deceased)

def add_marriage(p1, p2, dashed=False):
    mid = _next_id("M")
    DATA["marriages"][mid] = {"p1": p1, "p2": p2, "dashed": dashed}
    if mid not in DATA["children"]:
        DATA["children"][mid] = []
    return mid

def add_child_to_marriage(mid, child_pid):
    kids = DATA["children"].setdefault(mid, [])
    if child_pid not in kids:
        kids.append(child_pid)
    DATA["parents_of"][child_pid] = mid

def ensure_sibling_junction_for(pid):
    """
    回傳此人的父母婚姻/父母junction的 mid。
    若該人尚未有父母節點，建立一個「虛擬父母」junction：
      - 這類 junction 不會顯示父母，只當作兄弟姐妹共用的父母節點
    """
    if pid in DATA["parents_of"]:
        return DATA["parents_of"][pid]
    mid = _next_id("M")
    DATA["sibling_junctions"][mid] = {"type": "junction"}  # 標記為父母junction
    DATA["children"][mid] = [pid]
    DATA["parents_of"][pid] = mid
    return mid

def label_of(pid):
    p = DATA["persons"][pid]
    name = p["name"] + ("（殁）" if p.get("deceased") else "")
    return name

def node_style_of(pid):
    p = DATA["persons"][pid]
    if p.get("deceased"):
        fill = "#d0d0d0"
    else:
        fill = "#D2E9FF" if p["gender"] == "男" else "#FFDADF"
    shape = "ellipse" if p["gender"] == "女" else "box"
    return {"fillcolor": fill, "shape": shape}

# ---------------- 示範資料（可按鈕注入） ----------------
def load_demo():
    # 清空後重建
    st.session_state.data = _blank()
    d = st.session_state.data

    yilang = ensure_person("陳一郎", "男")
    exwife = ensure_person("陳前妻", "女")
    wife   = ensure_person("陳妻", "女")
    wangzi = ensure_person("王子", "男")
    wz_w   = ensure_person("王子妻", "女")
    cda    = ensure_person("陳大", "男")
    cer    = ensure_person("陳二", "男")
    csan   = ensure_person("陳三", "男")
    wsun   = ensure_person("王孫", "男")

    m_curr = add_marriage(yilang, wife, dashed=False)
    m_ex   = add_marriage(yilang, exwife, dashed=True)
    m_w    = add_marriage(wangzi, wz_w, dashed=False)

    add_child_to_marriage(m_curr, cda)
    add_child_to_marriage(m_curr, cer)
    add_child_to_marriage(m_curr, csan)

    add_child_to_marriage(m_ex, wangzi)
    add_child_to_marriage(m_w,  wsun)

# ---------------- 介面：標題／導覽 ----------------
st.set_page_config(page_title="家族平台", layout="wide")
st.title("🌳 家族平台（人物｜關係｜家族樹）")

tabs = st.tabs(["人物", "關係", "家族樹"])

# ---------------- 人物 ----------------
with tabs[0]:
    st.subheader("人物清單")
    colA, colB = st.columns([1,2])

    with colA:
        with st.form("add_person_form", clear_on_submit=True):
            st.markdown("**新增人物**")
            name = st.text_input("姓名")
            gender = st.radio("性別", ["男", "女"], horizontal=True, index=0)
            deceased = st.checkbox("已過世")
            ok = st.form_submit_button("新增")
            if ok and name.strip():
                pid = add_person(name, gender, deceased)
                st.success(f"已新增：{name}（ID: {pid}）")

        st.markdown("---")
        if st.button("載入示範資料（陳一郎家族）"):
            load_demo()
            st.success("已載入示範資料。")

    with colB:
        if not DATA["persons"]:
            st.info("目前尚無人物。請在左側新增，或載入示範資料。")
        else:
            for pid, p in DATA["persons"].items():
                st.write(f"- {p['name']}（{p['gender']}）{'（殁）' if p.get('deceased') else ''} — ID: {pid}")

# ---------------- 關係 ----------------
with tabs[1]:
    st.subheader("關係（婚姻／子女／兄弟姐妹）")
    c1, c2, c3 = st.columns(3)

    # 婚姻
    with c1:
        st.markdown("**建立婚姻**")
        if len(DATA["persons"]) >= 2:
            all_opts = {f"{p['name']} ({pid})": pid for pid, p in DATA["persons"].items()}
            p1 = st.selectbox("人物A", list(all_opts.keys()), key="m_p1")
            p2 = st.selectbox("人物B", list(all_opts.keys()), key="m_p2")
            dashed = st.checkbox("離婚（虛線）", key="m_dash")
            if st.button("建立婚姻"):
                pid1, pid2 = all_opts[p1], all_opts[p2]
                if pid1 == pid2:
                    st.warning("同一個人不能和自己結婚 😅")
                else:
                    mid = add_marriage(pid1, pid2, dashed=dashed)
                    st.success(f"已建立婚姻 {mid}：{DATA['persons'][pid1]['name']} ↔ {DATA['persons'][pid2]['name']}")
        else:
            st.info("先新增至少兩位人物。")

    # 子女
    with c2:
        st.markdown("**把子女掛到父母（某段婚姻/父母junction）**")
        if DATA["marriages"] or DATA["sibling_junctions"]:
            all_mid = {**DATA["marriages"], **DATA["sibling_junctions"]}
            mid_opts = {}
            for mid in all_mid:
                if mid in DATA["marriages"]:
                    m = DATA["marriages"][mid]
                    a = DATA["persons"][m["p1"]]["name"]
                    b = DATA["persons"][m["p2"]]["name"]
                    edge = "（離）" if m.get("dashed") else "（現）"
                    mid_opts[f"{mid}：{a} ↔ {b} {edge}"] = mid
                else:
                    mid_opts[f"{mid}：父母Junction（僅用於兄弟姐妹）"] = mid

            mid_label = st.selectbox("選擇父母婚姻/父母junction", list(mid_opts.keys()), key="child_mid")
            all_people = {f"{p['name']} ({pid})": pid for pid, p in DATA["persons"].items()}
            kid_label = st.selectbox("選擇子女", list(all_people.keys()), key="child_pid")
            if st.button("掛上子女"):
                mid = mid_opts[mid_label]
                kid = all_people[kid_label]
                add_child_to_marriage(mid, kid)
                st.success(f"已將 {DATA['persons'][kid]['name']} 掛到 {mid}")

        else:
            st.info("目前尚無婚姻或父母junction。可先建立婚姻，或到『兄弟姐妹』建立父母junction。")

    # 兄弟姐妹
    with c3:
        st.markdown("**掛接兄弟姐妹（把不在樹上的人接進來）**")
        if DATA["persons"]:
            anchor_map = {f"{p['name']} ({pid})": pid for pid, p in DATA["persons"].items()}
            anch_label = st.selectbox("選擇錨點人物（已在樹上）", list(anchor_map.keys()), key="sib_anchor")
            mode = st.radio("要掛入的人", ["已存在的人", "新增一個人"], horizontal=True, key="sib_mode")

            target_pid = None
            if mode == "已存在的人":
                exist_map = {f"{p['name']} ({pid})": pid for pid, p in DATA["persons"].items()}
                targ_label = st.selectbox("選擇此人", list(exist_map.keys()), key="sib_exist")
                if st.button("掛為兄弟姐妹", key="sib_btn_exist"):
                    target_pid = exist_map[targ_label]
            else:
                with st.form("form_new_sibling", clear_on_submit=True):
                    name = st.text_input("姓名")
                    gender = st.radio("性別", ["男", "女"], key="sib_gender", horizontal=True)
                    deceased = st.checkbox("已過世", key="sib_dec")
                    ok = st.form_submit_button("建立並掛入")
                if ok and name.strip():
                    target_pid = add_person(name, gender, deceased)

            if target_pid:
                anch_pid = anchor_map[anch_label]
                mid = ensure_sibling_junction_for(anch_pid)  # 若無父母，建立 junction
                # 若 target 尚無父母，直接放進同個 junction；有父母也強制改掛同個 junction（以兄弟姐妹為準）
                add_child_to_marriage(mid, target_pid)
                st.success(f"已將「{DATA['persons'][target_pid]['name']}」掛為 {DATA['persons'][anch_pid]['name']} 的兄弟姐妹")
        else:
            st.info("請先新增至少一位人物。")

# ---------------- 家族樹（Graphviz） ----------------
with tabs[2]:
    st.subheader("家族樹（配偶相鄰；子女向下；兄弟姐妹共父母junction）")

    if not DATA["persons"]:
        st.info("目前沒有資料，請先在『人物』與『關係』頁建立內容，或回到人物頁載入示範資料。")
        st.stop()

    dot = Digraph(comment="Family Tree", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")
    dot.node_attr.update(style="filled", color="#0e2d3b", penwidth="1.2", fontname="Noto Sans CJK TC")
    dot.edge_attr.update(color="#0e2d3b")

    # 1) 先畫人物節點
    for pid in DATA["persons"]:
        style = node_style_of(pid)
        dot.node(pid, label_of(pid), fillcolor=style["fillcolor"], shape=style["shape"])

    # 2) 婚姻節點（把配偶排成同層，並從中間引出子女）
    for mid, m in DATA["marriages"].items():
        p1, p2 = m["p1"], m["p2"]
        # 婚姻小點
        dot.node(mid, "", shape="point", width="0.02", color="#0e2d3b")
        style = "dashed" if m.get("dashed") else "solid"
        dot.edge(p1, mid, dir="none", style=style)
        dot.edge(p2, mid, dir="none", style=style)
        # 夫妻同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(p1); s.node(p2)
        # 子女
        for kid in DATA["children"].get(mid, []):
            dot.edge(mid, kid)

    # 3) 兄弟姐妹用的「父母junction」：只顯示 junction 與孩子，不畫父母
    for mid in DATA["sibling_junctions"]:
        dot.node(mid, "", shape="point", width="0.02", color="#0e2d3b")
        # 讓同個 junction 的孩子同層
        kids = DATA["children"].get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for k in kids:
                    s.node(k)
        for kid in kids:
            dot.edge(mid, kid)

    st.graphviz_chart(dot, use_container_width=True)

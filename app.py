# app.py
import streamlit as st
from graphviz import Digraph
from datetime import date

# -----------------------------
# 基礎：Session data 結構與工具
# -----------------------------
def _empty_data():
    return {
        "_seq": 0,
        "persons": {},          # pid -> {name, gender('男'/'女'), alive(True/False)}
        "marriages": {},        # mid -> {p1, p2, divorced:bool}
        "children": {},         # mid -> [pid, ...]
    }

def next_id():
    st.session_state.data["_seq"] += 1
    return f"id_{st.session_state.data['_seq']}"

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = _empty_data()

def display_name(pid: str) -> str:
    d = st.session_state.data
    p = d["persons"][pid]
    suffix = "（殁）" if not p["alive"] else ""
    return f"{p['name']}{suffix}"

def add_person(name: str, gender: str, alive: bool=True) -> str:
    pid = next_id()
    st.session_state.data["persons"][pid] = {
        "name": name.strip(),
        "gender": gender,
        "alive": alive,
    }
    return pid

def add_marriage(p1: str, p2: str, divorced: bool=False) -> str:
    mid = next_id()
    st.session_state.data["marriages"][mid] = {"p1": p1, "p2": p2, "divorced": divorced}
    st.session_state.data["children"][mid] = []
    return mid

def attach_child(mid: str, child: str):
    kids = st.session_state.data["children"].setdefault(mid, [])
    if child not in kids:
        kids.append(child)

# -----------------------------
# 示範資料
# -----------------------------
def load_demo(clear=True):
    if clear:
        st.session_state.data = _empty_data()

    # 人物
    yilang   = add_person("陳一郎", "男", True)
    wife     = add_person("陳妻",   "女", True)
    exwife   = add_person("陳前妻", "女", True)
    wangzi   = add_person("王子",   "男", True)
    wangwife = add_person("王子妻", "女", True)
    wangsun  = add_person("王孫",   "男", True)
    chenda   = add_person("陳大",   "男", True)
    chener   = add_person("陳二",   "男", True)
    chensan  = add_person("陳三",   "男", True)

    # 婚姻
    m_curr = add_marriage(yilang, wife, divorced=False)   # 現任
    m_ex   = add_marriage(yilang, exwife, divorced=True)  # 前任（虛線）

    # 子女
    attach_child(m_curr, chenda)
    attach_child(m_curr, chener)
    attach_child(m_curr, chensan)
    attach_child(m_ex,   wangzi)

    # 王子家庭
    m_wang = add_marriage(wangzi, wangwife, divorced=False)
    attach_child(m_wang, wangsun)

# -----------------------------
# 畫家族樹（Graphviz）
# -----------------------------
COLOR_MALE   = "#d9ecff"
COLOR_FEMALE = "#ffe1e8"
COLOR_DEAD   = "#e5e7eb"
BORDER       = "#0e2d3b"
FILL         = "#1f4b63"

def render_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或點上方『載入示範（陳一郎家族）』。")
        return

    dot = Digraph(format="png", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.4", ranksep="0.6")
    dot.edge_attr.update(color=BORDER)

    # 節點：男女不同外觀，已故灰色 + 名字加（殁）
    for pid, p in d["persons"].items():
        alive = p["alive"]
        label = f"{p['name']}{'' if alive else '（殁）'}"
        if not alive:
            fill = COLOR_DEAD
            shape = "box" if p["gender"] == "男" else "ellipse"
        else:
            if p["gender"] == "男":
                fill, shape = COLOR_MALE, "box"
            else:
                fill, shape = COLOR_FEMALE, "ellipse"
        dot.node(pid, label=label, shape=shape, style="filled", fillcolor=fill, color=BORDER, penwidth="1.2")

    # 婚姻 junction（小圓點），子女自 junction 垂直連下
    # 前任：虛線；在婚：實線
    for mid, m in d["marriages"].items():
        dot.node(mid, "", shape="point", width="0.02", color=BORDER)
        style = "dashed" if m["divorced"] else "solid"
        dot.edge(m["p1"], mid, dir="none", style=style)
        dot.edge(m["p2"], mid, dir="none", style=style)
        # 父母同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(m["p1"])
            s.node(m["p2"])
        # 子女同層
        kids = d["children"].get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(mid, c)

    st.graphviz_chart(dot, use_container_width=True)

# -----------------------------
# UI：頁首
# -----------------------------
st.set_page_config(page_title="家族平台", layout="wide")
ensure_session()

st.title("🌳 家族平台（人物｜關係｜法定繼承｜家族樹）")

col_demo, col_blank = st.columns([1, 2])
with col_demo:
    if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
        load_demo(clear=True)
        st.success("已載入示範資料。")

# -----------------------------
# Tabs
# -----------------------------
tab_people, tab_rel, tab_inherit, tab_tree = st.tabs(["人物", "關係", "法定繼承試算", "家族樹"])

# ---- 人物 ----
with tab_people:
    d = st.session_state.data
    st.subheader("新增人物")
    with st.form("form_add_person"):
        name = st.text_input("姓名")
        gender = st.selectbox("性別", ["男", "女"], index=0)
        alive = st.checkbox("仍在世", value=True)
        ok = st.form_submit_button("新增人物")
        if ok:
            if not name.strip():
                st.error("請輸入姓名。")
            else:
                pid = add_person(name, gender, alive)
                st.success(f"已新增：{display_name(pid)}")
                st.rerun()

    st.markdown("#### 目前人物")
    if not d["persons"]:
        st.info("尚無人物。")
    else:
        for pid, p in d["persons"].items():
            alive = "在世" if p["alive"] else "已故"
            st.write(f"- {display_name(pid)}｜性別：{p['gender']}｜{alive}")

# ---- 關係 ----
with tab_rel:
    d = st.session_state.data
    st.subheader("建立婚姻（現任／離婚）")

    persons = list(d["persons"].keys())
    if not persons:
        st.info("請先新增人物。")
    else:
        with st.form("form_add_marriage"):
            p1 = st.selectbox("配偶 A", ["請選擇"] + persons,
                              format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
            p2 = st.selectbox("配偶 B", ["請選擇"] + persons,
                              format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
            is_divorce = st.checkbox("此婚姻為『離婚/前配偶』", value=False)
            okm = st.form_submit_button("建立婚姻")
            if okm:
                if p1 == "請選擇" or p2 == "請選擇":
                    st.error("請選擇兩位配偶。")
                elif p1 == p2:
                    st.error("不可選同一人。")
                else:
                    mid = add_marriage(p1, p2, divorced=is_divorce)
                    st.success(f"已建立婚姻：{display_name(p1)}－{display_name(p2)}（{'離婚' if is_divorce else '在婚'}）")
                    st.rerun()

        st.markdown("---")
        st.subheader("把子女掛到父母（某段婚姻）")
        with st.form("form_attach_child"):
            d = st.session_state.data                                # <= 這行確保 d 存在！
            mar_ids = list(d["marriages"].keys())
            if not mar_ids:
                st.info("目前尚無婚姻，請先在上方建立婚姻。")
                st.form_submit_button("（不可送出）", disabled=True)
            else:
                def mar_fmt(mid):
                    m = d["marriages"][mid]
                    tag = "（離婚）" if m["divorced"] else "（在婚）"
                    return f"{display_name(m['p1'])}－{display_name(m['p2'])} {tag}"

                mid_sel = st.selectbox("選擇父母（某段婚姻）",
                                       ["請選擇"] + mar_ids,
                                       format_func=lambda x: mar_fmt(x) if x != "請選擇" else "請選擇")
                child_sel = st.selectbox("子女",
                                         ["請選擇"] + persons,
                                         format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
                okc = st.form_submit_button("掛上子女")
                if okc:
                    if mid_sel == "請選擇" or child_sel == "請選擇":
                        st.error("請選擇婚姻與子女。")
                    else:
                        attach_child(mid_sel, child_sel)
                        st.success(f"已將「{display_name(child_sel)}」掛到：{mar_fmt(mid_sel)}")
                        st.rerun()

# ---- 法定繼承試算（簡化版：只展示規則說明與統計）----
with tab_inherit:
    st.subheader("法定繼承試算（示意）")
    st.markdown("""
- 依民法第1138條：**配偶為當然繼承人**，並與下列順序之一並行：
  1. 第一順位：直系血親卑親屬  
  2. 第二順位：父母  
  3. 第三順位：兄弟姐妹  
  4. 第四順位：祖父母  

> 只要有前順位存在，就不會輪到後順位。此頁為示意，之後可擴充精算比例。
""")

# ---- 家族樹 ----
with tab_tree:
    st.subheader("家族樹")
    render_tree()

# app.py
# ------------------------------------------------------------
# 家族平台（Graphviz 版）
# - 前任在左、本人置中、現任在右（以不可見邊 + 高權重固定水平順序）
# - 三代分層（根人物/其配偶=第1層；子女=第2層；孫輩=第3層）
# - 離婚虛線、在婚實線；子女自父母中點垂直往下
# - 可一鍵載入示範 / 匯入JSON / 匯出JSON
#
# JSON 資料格式（匯入/匯出使用）：
# {
#   "persons": {
#     "c_yilang": {"name": "陳一郎"},
#     "c_exwife": {"name": "陳前妻"},
#     ...
#   },
#   "marriages": [
#     {"id":"m_ex", "a":"c_yilang", "b":"c_exwife", "status":"ex"},
#     {"id":"m_current", "a":"c_yilang", "b":"c_wife", "status":"current"},
#     {"id":"m_wang", "a":"wang_zi", "b":"wang_zi_wife", "status":"current"}
#   ],
#   "children": [
#     {"marriage_id":"m_ex", "children":["wang_zi"]},
#     {"marriage_id":"m_current", "children":["chen_da","chen_er","chen_san"]},
#     {"marriage_id":"m_wang", "children":["wang_sun"]}
#   ]
# }
# ------------------------------------------------------------

import json
import io
import streamlit as st
from graphviz import Digraph

# ---------------------- UI 外觀 ----------------------
st.set_page_config(page_title="家族平台（Graphviz）", layout="wide")
st.title("🌳 家族平台（Graphviz 版）")
st.caption("前任在左、本人置中、現任在右；三代分層；離婚用虛線")

# ---------------------- 預設樣式 ----------------------
NODE_STYLE = {
    "shape": "box",
    "style": "filled",
    "fillcolor": "#184a5a",   # 深藍綠
    "fontcolor": "white",
    "color": "#0e2d3b",
    "penwidth": "1.2",
}
EDGE_STYLE = {"color": "#184a5a"}

# ---------------------- 一鍵示範資料 ----------------------
DEMO = {
    "persons": {
        "c_yilang":    {"name": "陳一郎"},
        "c_wife":      {"name": "陳妻"},
        "c_exwife":    {"name": "陳前妻"},
        "wang_zi":     {"name": "王子"},
        "wang_zi_wife":{"name": "王子妻"},
        "wang_sun":    {"name": "王孫"},
        "chen_da":     {"name": "陳大"},
        "chen_er":     {"name": "陳二"},
        "chen_san":    {"name": "陳三"},
    },
    "marriages": [
        {"id":"m_current", "a":"c_yilang", "b":"c_wife",   "status":"current"},
        {"id":"m_ex",      "a":"c_yilang", "b":"c_exwife", "status":"ex"},
        {"id":"m_wang",    "a":"wang_zi",  "b":"wang_zi_wife", "status":"current"},
    ],
    "children": [
        {"marriage_id":"m_current", "children":["chen_da","chen_er","chen_san"]},
        {"marriage_id":"m_ex",      "children":["wang_zi"]},
        {"marriage_id":"m_wang",    "children":["wang_sun"]},
    ]
}

# ---------------------- State 初始化 ----------------------
if "data" not in st.session_state:
    st.session_state.data = DEMO

# ---------------------- 工具函式 ----------------------
def partner_of(m, pid):
    """回傳在婚姻 m 中 pid 的對象 id。"""
    return m["b"] if m["a"] == pid else m["a"]

def build_graph(data: dict, root_id: str) -> Digraph:
    """依據資料與根人物，建構 Graphviz 圖物件。"""
    dot = Digraph(comment="Family Tree", engine="dot", format="svg")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.7")
    dot.node_attr.update(NODE_STYLE)
    dot.edge_attr.update(EDGE_STYLE)

    persons  = data.get("persons", {})
    marriages = data.get("marriages", [])
    children  = data.get("children", [])

    # ---- 1) 先把所有人建節點 ----
    for pid, info in persons.items():
        dot.node(pid, info.get("name", pid))

    # 建婚姻 -> 子女對應
    ch_map = {c["marriage_id"]: c.get("children", []) for c in children}

    # ---- 2) 先畫婚姻 junction（小圓點）與父母關係線 ----
    # 並且把每段婚姻的父母排在同一層（rank=same）
    for m in marriages:
        mid = m["id"]
        a, b = m["a"], m["b"]
        dashed = (m.get("status") == "ex")
        dot.node(mid, "", shape="point", width="0.02", color="#184a5a")
        style = "dashed" if dashed else "solid"
        dot.edge(a, mid, dir="none", style=style)
        dot.edge(b, mid, dir="none", style=style)
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

    # ---- 3) 把子女從婚姻 junction 往下接；子女同層、順序固定 ----
    for mid, kids in ch_map.items():
        if not kids:
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for cid in kids:
                s.node(cid)         # 確保此層建好
        # 固定左→右（以不可見邊鏈住）
        for i in range(len(kids)-1):
            dot.edge(kids[i], kids[i+1], style="invis", weight="200")
        for cid in kids:
            dot.edge(mid, cid)

    # ---- 4) 對每個人：以前任→本人→現任的不可見邊「鎖順序」 ----
    # 「現任只有一位」的前提下，ex 可多位（都放左邊）
    # 收集每個人的 ex / current
    ex_map = {pid: [] for pid in persons}
    cur_map = {pid: [] for pid in persons}
    # 找出每人的各種配偶
    for m in marriages:
        a, b, status = m["a"], m["b"], m.get("status")
        ex_map[a]  = ex_map.get(a, [])
        ex_map[b]  = ex_map.get(b, [])
        cur_map[a] = cur_map.get(a, [])
        cur_map[b] = cur_map.get(b, [])
        if status == "ex":
            ex_map[a].append(b); ex_map[b].append(a)
        elif status == "current":
            cur_map[a].append(b); cur_map[b].append(a)

    # 對每個人做 rank=same 分組 + 左中右不可見邊
    for me in persons.keys():
        exes = ex_map.get(me, [])
        curs = cur_map.get(me, [])
        # 分組：同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            for x in exes: s.node(x)
            s.node(me)
            for c in curs: s.node(c)
        # 左→中→右不可見邊（高權重，鎖水平）
        chain = exes + [me] + curs
        for i in range(len(chain)-1):
            dot.edge(chain[i], chain[i+1], style="invis", weight="9999")

    # ---- 5) 三代分層：以 root 為基準（root & 其配偶=第1層；子女=第2層；孫=第3層）----
    gen0 = set([root_id]) | set(cur_map.get(root_id, [])) | set(ex_map.get(root_id, []))
    # root 與他所有婚姻的子女 = 第二層
    gen1 = set()
    for m in marriages:
        if m["a"] == root_id or m["b"] == root_id:
            for kid in ch_map.get(m["id"], []):
                gen1.add(kid)
    # 孫 = 第三層
    gen2 = set()
    for kid in list(gen1):
        for m in marriages:
            if m["a"] == kid or m["b"] == kid:
                for g in ch_map.get(m["id"], []):
                    gen2.add(g)

    # 設 rank=same 群組（分三代）
    if gen0:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for pid in gen0: s.node(pid)
    if gen1:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for pid in gen1: s.node(pid)
        # 試著把root所有婚姻的 junction 也壓到 gen0，避免 junction 下沉
        for m in marriages:
            if m["a"] == root_id or m["b"] == root_id:
                with dot.subgraph() as s:
                    s.attr(rank="same")
                    s.node(m["id"])
    if gen2:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for pid in gen2: s.node(pid)

    return dot


# ---------------------- 側欄：資料維護 ----------------------
st.sidebar.header("資料維護 / 匯入匯出")

colA, colB = st.sidebar.columns(2)
if colA.button("🧪 一鍵載入示範", use_container_width=True):
    st.session_state.data = json.loads(json.dumps(DEMO))  # 深拷貝
    st.success("已載入示範資料：陳一郎家庭")

uploaded = st.sidebar.file_uploader("匯入 JSON", type=["json"])
if uploaded:
    try:
        data = json.load(uploaded)
        # 粗略驗證
        assert isinstance(data.get("persons"), dict)
        assert isinstance(data.get("marriages"), list)
        assert isinstance(data.get("children"), list)
        st.session_state.data = data
        st.success("✅ 匯入成功")
    except Exception as e:
        st.error(f"匯入失敗：{e}")

# 下載匯出
buf = io.BytesIO()
buf.write(json.dumps(st.session_state.data, ensure_ascii=False, indent=2).encode("utf-8"))
st.sidebar.download_button(
    "⬇️ 下載 JSON 備份", data=buf.getvalue(),
    file_name="family.json", mime="application/json",
    use_container_width=True
)

# ---------------------- 主畫面：家族樹 ----------------------
data = st.session_state.data
persons = data.get("persons", {})

# 根人物選擇（預設為第一個或示範中的陳一郎）
default_root = next(iter(persons.keys())) if persons else ""
root_id = st.selectbox(
    "選擇根人物（第1層）",
    options=list(persons.keys()),
    index=(list(persons.keys()).index("c_yilang") if "c_yilang" in persons else 0)
)
st.caption("第 1 層：根人物與其配偶；第 2 層：其子女；第 3 層：孫輩。離婚為虛線；在婚為實線。")

if persons:
    dot = build_graph(data, root_id)
    st.graphviz_chart(dot.source, use_container_width=True)
else:
    st.info("尚未有資料，請用左側的「一鍵載入示範」或「匯入 JSON」。")

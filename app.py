import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Tuple, List

from tree_layout import build_tree_from_marriages, tidy_layout

# ========= 內建示範資料 =========
DEMO_MARRIAGES = {
    "陳一郎|陳妻": {"label": "陳一郎╳陳妻", "children": ["王子", "陳大", "陳二", "陳三"]},
    "王子|王子妻": {"label": "王子╳王子妻", "children": ["王孫"]},
    "陳大|陳大嫂": {"label": "陳大╳陳大嫂", "children": ["二孩A", "二孩B", "二孩C"]},
    "陳二|陳二嫂": {"label": "陳二╳陳二嫂", "children": ["三孩A"]},
}
DEMO_PERSONS = {
    "王子": {"label": "王子", "children_marriages": ["王子|王子妻"]},
    "陳大": {"label": "陳大", "children_marriages": ["陳大|陳大嫂"]},
    "陳二": {"label": "陳二", "children_marriages": ["陳二|陳二嫂"]},
    "陳三": {"label": "陳三", "children_marriages": []},
    "王孫": {"label": "王孫", "children_marriages": []},
    "二孩A": {"label": "二孩A", "children_marriages": []},
    "二孩B": {"label": "二孩B", "children_marriages": []},
    "二孩C": {"label": "二孩C", "children_marriages": []},
    "三孩A": {"label": "三孩A", "children_marriages": []},
}

# ========= 視覺預設 =========
NODE_W = 120       # 只用於軸域預留邊界與線段端點
NODE_H = 40
MIN_SEP = 140
LEVEL_GAP = 140
BOX_COLOR = "rgba(12,74,110,1.0)"
TEXT_COLOR = "white"

st.set_page_config(page_title="家族樹（簡易版）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹（簡易版）")

# ========= 小工具 =========
def ensure_person(name: str):
    if not name:
        return
    persons = st.session_state.data["persons"]
    if name not in persons:
        persons[name] = {"label": name, "children_marriages": []}

def add_marriage(p1: str, p2: str, set_as_root_if_empty=True):
    if not p1 or not p2:
        return False, "請輸入父母雙方姓名"
    marriages = st.session_state.data["marriages"]
    mid = f"{p1}|{p2}"
    if mid in marriages:
        return False, "這對父母已存在"
    marriages[mid] = {"label": f"{p1}╳{p2}", "children": []}
    ensure_person(p1); ensure_person(p2)
    if set_as_root_if_empty and not st.session_state.data.get("root_marriage_id"):
        st.session_state.data["root_marriage_id"] = mid
    return True, "已新增父母"

def add_child_to_marriage(marriage_id: str, child_name: str, child_spouse: str = ""):
    if not marriage_id: return False, "請先選擇父母"
    if not child_name:  return False, "請輸入孩子姓名"
    marriages = st.session_state.data["marriages"]
    persons = st.session_state.data["persons"]
    if marriage_id not in marriages: return False, "父母不存在"

    ensure_person(child_name)
    if child_name not in marriages[marriage_id]["children"]:
        marriages[marriage_id]["children"].append(child_name)

    if child_spouse:
        ensure_person(child_spouse)
        child_mid = f"{child_name}|{child_spouse}"
        if child_mid not in marriages:
            marriages[child_mid] = {"label": f"{child_name}╳{child_spouse}", "children": []}
        persons[child_name]["children_marriages"] = list(
            set(persons[child_name].get("children_marriages", []) + [child_mid])
        )
    return True, "已新增孩子"

def edges_for_plot(marriages: Dict, persons: Dict) -> List[Tuple[str, str]]:
    e = []
    for m_id, m in marriages.items():
        for child in m.get("children", []):
            e.append((m_id, child))
    for pid, p in persons.items():
        for sub_m in p.get("children_marriages", []):
            e.append((pid, sub_m))
    return e

def draw_tree_generic(marriages: Dict, persons: Dict, root_id: str, title: str):
    """用最穩定的 Scatter 畫法產圖（給示範與實際都能共用）。"""
    # 1) 佈局
    root, _ = build_tree_from_marriages(marriages, persons, root_id)
    pos = tidy_layout(root, min_sep=MIN_SEP, level_gap=LEVEL_GAP)
    if not pos:
        st.warning("沒有可顯示的節點。")
        return

    # 2) 節點與邊
    def is_marriage(nid: str) -> bool: return nid in marriages
    nodes_x, nodes_y, labels = [], [], []
    for nid, (x, y) in pos.items():
        nodes_x.append(x); nodes_y.append(y)
        labels.append(marriages.get(nid, {}).get("label") if is_marriage(nid) else persons.get(nid, {}).get("label", nid))

    ex, ey = [], []
    for a, b in edges_for_plot(marriages, persons):
        if a in pos and b in pos:
            x0, y0 = pos[a]; x1, y1 = pos[b]
            y0 += NODE_H/2; y1 -= NODE_H/2
            ex.extend([x0, x1, None]); ey.extend([y0, y1, None])

    # 3) 軸域（向下為正）
    pad_x = NODE_W * 0.75
    pad_y = NODE_H * 2.0
    min_x, max_x = min(nodes_x) - pad_x, max(nodes_x) + pad_x
    min_y, max_y = min(nodes_y) - pad_y, max(nodes_y) + pad_y

    # 4) 畫圖（只用 Scatter，避免 shapes 在某些前端版面沒渲染）
    fig = go.Figure()
    if ex:
        fig.add_trace(go.Scatter(
            x=ex, y=ey, mode="lines",
            line=dict(width=2, color="rgba(80,80,80,1)"),
            hoverinfo="none", name=""
        ))
    fig.add_trace(go.Scatter(
        x=nodes_x, y=nodes_y,
        mode="markers+text",
        marker=dict(symbol="square", size=34, color=BOX_COLOR, line=dict(width=1, color="rgba(0,0,0,0.25)")),
        text=labels, textposition="middle center",
        textfont=dict(color=TEXT_COLOR, size=12),
        hoverinfo="text", name=""
    ))
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.98, xanchor="left", yanchor="top"),
        xaxis=dict(visible=False, range=[min_x, max_x]),
        yaxis=dict(visible=False, range=[max_y, min_y]),
        margin=dict(l=20, r=20, t=40, b=20),
        height=520, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ========= 頁面最上方：兩張「保證可見」的小圖 =========
# 1) Plotly 環境測試（這張一定會出現）
test = go.Figure(go.Scatter(x=[0,1,2], y=[0,1,0], mode="lines+markers"))
test.update_layout(height=140, margin=dict(l=10, r=10, t=10, b=10), title="✅ Plotly 測試圖（用來確認前端可渲染）")
st.plotly_chart(test, use_container_width=True)

# 2) 直接用示範資料畫一張（不依賴任何表單或 session 狀態）
draw_tree_generic(DEMO_MARRIAGES, DEMO_PERSONS, "陳一郎|陳妻", title="🧪 示範家族樹（固定示例）")

st.markdown("---")

# ========= 下方才是你的互動區 =========
# 狀態初始化（給互動用）
if "data" not in st.session_state:
    st.session_state.data = {"root_marriage_id": "", "marriages": {}, "persons": {}}
if not st.session_state.data.get("marriages"):
    st.session_state.data["marriages"] = {**DEMO_MARRIAGES}
    st.session_state.data["persons"] = {**DEMO_PERSONS}
    st.session_state.data["root_marriage_id"] = "陳一郎|陳妻"

left, right = st.columns([0.9, 1.1])

with left:
    st.subheader("快速建立")

    # ① 新增父母
    with st.form("add_parents", clear_on_submit=True):
        st.markdown("**① 新增一對父母**（或伴侶）")
        p1 = st.text_input("父母一（例：陳一郎）")
        p2 = st.text_input("父母二（例：陳妻）")
        make_root = st.checkbox("設為家族根節點", value=not bool(st.session_state.data.get("root_marriage_id")))
        s = st.form_submit_button("新增父母")
        if s:
            ok, msg = add_marriage(p1.strip(), p2.strip(), set_as_root_if_empty=make_root)
            (st.success if ok else st.error)(msg)
            st.rerun()

    # ② 在某對父母下新增孩子
    with st.form("add_child", clear_on_submit=True):
        st.markdown("**② 在某對父母下新增孩子**")
        marriages_keys = list(st.session_state.data["marriages"].keys())
        msel = st.selectbox("選擇父母", marriages_keys, index=0 if marriages_keys else None, placeholder="請先建立父母")
        cname = st.text_input("孩子姓名")
        csp = st.text_input("（可選）孩子的配偶姓名（會同步建立孩子的婚姻）")
        s2 = st.form_submit_button("新增孩子")
        if s2:
            ok, msg = add_child_to_marriage(msel, cname.strip(), csp.strip())
            (st.success if ok else st.error)(msg)
            st.rerun()

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範資料"):
            st.session_state.data["marriages"] = {**DEMO_MARRIAGES}
            st.session_state.data["persons"] = {**DEMO_PERSONS}
            st.session_state.data["root_marriage_id"] = "陳一郎|陳妻"
            st.success("已載入示範資料")
            st.rerun()
    with c2:
        if st.button("清除全部資料"):
            st.session_state.data = {"root_marriage_id": "", "marriages": {}, "persons": {}}
            st.info("已清空資料")
            st.rerun()

with right:
    # 狀態面板（方便你確認）
    data = st.session_state.data
    marriages = data.get("marriages", {})
    persons = data.get("persons", {})
    root_id = data.get("root_marriage_id") or (next(iter(marriages), ""))

    with st.expander("狀態檢查（看不到圖時展開）", expanded=False):
        st.write({"root_marriage_id": root_id, "#marriages": len(marriages), "#persons": len(persons)})

    if root_id:
        draw_tree_generic(marriages, persons, root_id, title="📍 你的家族樹（可用左側表單即時擴充）")
    else:
        st.info("先建立至少一對父母，畫面就會出現家族樹。")

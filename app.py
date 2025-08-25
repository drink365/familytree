import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Tuple, List
from tree_layout import build_tree_from_marriages, tidy_layout

# === 內建示範資料 ===
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

# === 視覺參數（固定的好看預設） ===
NODE_W, NODE_H = 120, 40
MIN_SEP, LEVEL_GAP = 140, 140
BOX_COLOR = "rgba(12,74,110,1.0)"
TEXT_COLOR = "white"

st.set_page_config(page_title="家族樹（簡易版）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹（簡易版）")
st.caption("build stamp: 2025-08-25 16:00（若你看不到這行，代表雲端跑的不是這份 app.py）")

# ===== 共用：把 marriages/persons 畫成圖（只用 Scatter，最穩定） =====
def draw_tree_generic(marriages: Dict, persons: Dict, root_id: str, title: str):
    from math import inf

    root, _ = build_tree_from_marriages(marriages, persons, root_id)
    pos = tidy_layout(root, min_sep=MIN_SEP, level_gap=LEVEL_GAP)
    if not pos:
        st.warning("沒有可顯示的節點。"); return

    # 節點與標籤
    def is_m(nid: str) -> bool: return nid in marriages
    xs, ys, labels = [], [], []
    for nid, (x, y) in pos.items():
        xs.append(x); ys.append(y)
        labels.append(marriages.get(nid, {}).get("label") if is_m(nid) else persons.get(nid, {}).get("label", nid))

    # 邊
    ex, ey = [], []
    for m_id, m in marriages.items():
        for child in m.get("children", []):
            if m_id in pos and child in pos:
                x0,y0 = pos[m_id]; x1,y1 = pos[child]
                y0 += NODE_H/2; y1 -= NODE_H/2
                ex.extend([x0,x1,None]); ey.extend([y0,y1,None])
    for pid, p in persons.items():
        for sub_m in p.get("children_marriages", []):
            if pid in pos and sub_m in pos:
                x0,y0 = pos[pid]; x1,y1 = pos[sub_m]
                y0 += NODE_H/2; y1 -= NODE_H/2
                ex.extend([x0,x1,None]); ey.extend([y0,y1,None])

    # 軸域（向下為正）
    pad_x, pad_y = NODE_W*0.75, NODE_H*2.0
    min_x, max_x = min(xs)-pad_x, max(xs)+pad_x
    min_y, max_y = min(ys)-pad_y, max(ys)+pad_y

    fig = go.Figure()
    if ex:
        fig.add_trace(go.Scatter(x=ex,y=ey,mode="lines",line=dict(width=2,color="rgba(80,80,80,1)"),hoverinfo="none"))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker=dict(symbol="square", size=34, color=BOX_COLOR, line=dict(width=1, color="rgba(0,0,0,0.25)")),
        text=labels, textposition="middle center", textfont=dict(color=TEXT_COLOR, size=12),
        hoverinfo="text"
    ))
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.98, xanchor="left"),
        xaxis=dict(visible=False, range=[min_x, max_x]),
        yaxis=dict(visible=False, range=[max_y, min_y]),  # 倒序：向下為正
        margin=dict(l=20,r=20,t=40,b=20), height=520, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ====== 頂部兩張「保證可見」的圖 ======
# 1) Plotly 測試圖（一定會畫）
test = go.Figure(go.Scatter(x=[0,1,2], y=[0,1,0], mode="lines+markers"))
test.update_layout(height=140, margin=dict(l=10,r=10,t=10,b=10), title="✅ Plotly 測試圖（確認前端可渲染）")
st.plotly_chart(test, use_container_width=True)

# 2) 固定示範家族樹（不吃任何表單/狀態）
draw_tree_generic(DEMO_MARRIAGES, DEMO_PERSONS, "陳一郎|陳妻", "🧪 示範家族樹（固定示例）")
st.markdown("---")

# ====== 下面才是你的互動版 ======
if "data" not in st.session_state:
    st.session_state.data = {"root_marriage_id":"陳一郎|陳妻","marriages":{**DEMO_MARRIAGES},"persons":{**DEMO_PERSONS}}

left, right = st.columns([0.9,1.1])

with left:
    st.subheader("快速建立")
    def ensure_person(n): 
        if n and n not in st.session_state.data["persons"]:
            st.session_state.data["persons"][n] = {"label": n, "children_marriages": []}

    with st.form("add_parents", clear_on_submit=True):
        st.markdown("**① 新增一對父母**（或伴侶）")
        p1 = st.text_input("父母一（例：陳一郎）")
        p2 = st.text_input("父母二（例：陳妻）")
        make_root = st.checkbox("設為家族根節點", value=False)
        s = st.form_submit_button("新增父母")
        if s:
            if not p1 or not p2:
                st.error("請輸入父母雙方姓名")
            else:
                mid = f"{p1}|{p2}"
                d = st.session_state.data
                if mid in d["marriages"]:
                    st.warning("這對父母已存在")
                else:
                    d["marriages"][mid] = {"label": f"{p1}╳{p2}", "children": []}
                    ensure_person(p1); ensure_person(p2)
                    if make_root: d["root_marriage_id"] = mid
                    st.success("已新增父母")
            st.rerun()

    with st.form("add_child", clear_on_submit=True):
        st.markdown("**② 在某對父母下新增孩子**")
        mkeys = list(st.session_state.data["marriages"].keys())
        msel = st.selectbox("選擇父母", mkeys, index=0 if mkeys else None, placeholder="請先建立父母")
        cname = st.text_input("孩子姓名")
        csp = st.text_input("（可選）孩子的配偶姓名（會同步建立孩子的婚姻）")
        s2 = st.form_submit_button("新增孩子")
        if s2:
            if not (msel and cname):
                st.error("請選擇父母並輸入孩子姓名")
            else:
                d = st.session_state.data
                ensure_person(cname)
                if cname not in d["marriages"][msel]["children"]:
                    d["marriages"][msel]["children"].append(cname)
                if csp:
                    ensure_person(csp)
                    cmid = f"{cname}|{csp}"
                    if cmid not in d["marriages"]:
                        d["marriages"][cmid] = {"label": f"{cname}╳{csp}", "children": []}
                    d["persons"][cname]["children_marriages"] = list(set(d["persons"][cname].get("children_marriages", []) + [cmid]))
                st.success("已新增孩子")
            st.rerun()

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範資料"):
            st.session_state.data = {"root_marriage_id":"陳一郎|陳妻","marriages":{**DEMO_MARRIAGES},"persons":{**DEMO_PERSONS}}
            st.rerun()
    with c2:
        if st.button("清除全部資料"):
            st.session_state.data = {"root_marriage_id":"", "marriages":{}, "persons":{}}
            st.rerun()

with right:
    d = st.session_state.data
    marriages, persons = d.get("marriages", {}), d.get("persons", {})
    root_id = d.get("root_marriage_id") or (next(iter(marriages), "") if marriages else "")
    with st.expander("狀態檢查（看不到圖時展開）", expanded=False):
        st.write({"root_marriage_id": root_id, "#marriages": len(marriages), "#persons": len(persons)})
    if root_id:
        draw_tree_generic(marriages, persons, root_id, "📍 你的家族樹（可用左側表單擴充）")
    else:
        st.info("先建立至少一對父母，畫面就會出現家族樹。")

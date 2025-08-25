# app.py
import json
from typing import Dict, Tuple, List
import streamlit as st
import plotly.graph_objects as go

from tree_layout import build_tree_from_marriages, tidy_layout
import demo_data

st.set_page_config(page_title="家族樹佈局（婚姻錨點）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹佈局（孩子先掛在自己的父母下方）")

with st.sidebar:
    st.subheader("參數")
    min_sep = st.slider("兄弟子樹最小水平距離 (px)", 60, 240, 140, 10)
    level_gap = st.slider("代際垂直距離 (px)", 80, 220, 140, 10)
    node_w = st.slider("節點寬度 (px)", 90, 200, 120, 5)
    node_h = st.slider("節點高度 (px)", 30, 80, 40, 2)
    hide_marriage = st.checkbox("隱藏婚姻節點（僅作為錨點）", value=False)

    st.markdown("---")
    st.caption("資料格式（JSON）：")
    st.code(
        """{
  "root_marriage_id": "陳一郎|陳妻",
  "marriages": { "陳一郎|陳妻": {"label":"陳一郎╳陳妻","children":["王子"]}, ... },
  "persons":   { "王子": {"label":"王子","children_marriages":["王子|王子妻"]}, ... }
}""",
        language="json",
    )

# 狀態：資料
if "data" not in st.session_state:
    st.session_state.data = {
        "root_marriage_id": "陳一郎|陳妻",
        "marriages": demo_data.marriages,
        "persons": demo_data.persons,
    }

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("載入示範資料", use_container_width=True):
        st.session_state.data = {
            "root_marriage_id": "陳一郎|陳妻",
            "marriages": demo_data.marriages,
            "persons": demo_data.persons,
        }
with col2:
    if st.button("清空資料（從零開始）", use_container_width=True):
        st.session_state.data = {"root_marriage_id": "", "marriages": {}, "persons": {}}

data_text = st.text_area(
    "貼上或編輯 JSON 資料（按下方『套用』生效）",
    value=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
    height=300,
)
apply = st.button("套用 JSON", type="primary")
if apply:
    try:
        st.session_state.data = json.loads(data_text)
        st.success("JSON 已套用")
    except Exception as e:
        st.error(f"JSON 解析失敗：{e}")

root_id = st.session_state.data.get("root_marriage_id", "")
marriages: Dict = st.session_state.data.get("marriages", {})
persons: Dict = st.session_state.data.get("persons", {})

if not root_id or root_id not in marriages:
    st.info("請設定有效的 root_marriage_id 與 marriages/persons。")
    st.stop()

# —— 1) 建樹（以婚姻節點作為錨點，孩子先掛在父母節點下） ——
root, node_map = build_tree_from_marriages(marriages, persons, root_id)

# —— 2) 佈局（確保最小間距 & 整掛平移） ——
pos: Dict[str, Tuple[float, float]] = tidy_layout(root, min_sep=min_sep, level_gap=level_gap)

# —— 3) 轉成 Plotly ——
def _edges() -> List[Tuple[str, str]]:
    e = []
    # 婚姻節點 -> 孩子（人）
    for m_id, m in marriages.items():
        for child in m.get("children", []):
            e.append((m_id, child))
    # 人 -> 其婚姻節點
    for pid, p in persons.items():
        for sub_m in p.get("children_marriages", []):
            e.append((pid, sub_m))
    return e

def _rect_shape(x, y, w, h, visible=True):
    return dict(
        type="rect",
        x0=x - w / 2, y0=y - h / 2,
        x1=x + w / 2, y1=y + h / 2,
        line=dict(width=1),
        fillcolor="rgba(12,74,110,1.0)",  # 深青色
        opacity=1.0,
        layer="above",
        visible=visible,
    )

def _is_marriage(nid: str) -> bool:
    return nid in marriages

# 收集 shapes & annotations（節點）
shapes = []
annotations = []

for nid, (x, y) in pos.items():
    is_m = _is_marriage(nid)
    show_box = not (hide_marriage and is_m)
    shapes.append(_rect_shape(x, y, node_w, node_h, visible=show_box))
    label = marriages.get(nid, {}).get("label") if is_m else persons.get(nid, {}).get("label", nid)
    if show_box:
        annotations.append(
            dict(
                x=x, y=y, text=label or nid,
                showarrow=False, font=dict(color="white"),
                xanchor="center", yanchor="middle",
            )
        )

# 線段（父子連線）
edge_x = []
edge_y = []
for a, b in _edges():
    if a in pos and b in pos:
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        # 垂直向下的感覺：從父節點下邊到子節點上邊
        if _is_marriage(a):
            y0 = y0 + node_h / 2
        else:
            y0 = y0 + node_h / 2
        if _is_marriage(b):
            y1 = y1 - node_h / 2
        else:
            y1 = y1 - node_h / 2
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

fig = go.Figure()

# 畫線
fig.add_trace(go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    hoverinfo="none", line=dict(width=2)
))

# 節點是用 shapes 畫框＋ annotations 畫文字
fig.update_layout(
    shapes=shapes,
    annotations=annotations,
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    margin=dict(l=20, r=20, t=20, b=20),
    height=700,
)
# 讓 y 往下是正方向
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
**說明**
- 先把每個孩子「錨定」在自己的父母（婚姻節點）正下方，再檢查左右子樹的最小距離 `min_sep`。
- 若距離不足，會**整掛平移**（包含祖先對齊修正），避免擠壓與重疊。
- 若不想顯示婚姻節點，可以勾選「隱藏婚姻節點」，它仍是佈局的錨點。
"""
)

import streamlit as st
import plotly.graph_objects as go
from tree_layout import build_tree_from_marriages, tidy_layout

# —— 示範資料（固定）——
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

# —— 視覺參數（專業預設）——
NODE_W, NODE_H = 120, 40
MIN_SEP, LEVEL_GAP = 140, 140
BOX_COLOR = "rgba(12,74,110,1.0)"   # 深青色
TEXT_COLOR = "white"

st.set_page_config(page_title="家族樹（示範）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹（示範）")

def draw_demo_tree():
    root_id = "陳一郎|陳妻"

    # 1) 依婚姻節點建樹 + 自動佈局（孩子一定在自己父母下面，子樹距離不足會整掛平移）
    root, _ = build_tree_from_marriages(DEMO_MARRIAGES, DEMO_PERSONS, root_id)
    pos = tidy_layout(root, min_sep=MIN_SEP, level_gap=LEVEL_GAP)

    # 2) 準備節點與標籤
    def is_marriage(nid: str) -> bool: return nid in DEMO_MARRIAGES
    xs, ys, labels = [], [], []
    for nid, (x, y) in pos.items():
        xs.append(x); ys.append(y)
        labels.append(
            DEMO_MARRIAGES.get(nid, {}).get("label")
            if is_marriage(nid) else
            DEMO_PERSONS.get(nid, {}).get("label", nid)
        )

    # 3) 準備連線
    ex, ey = [], []
    # 父母→孩子
    for m_id, m in DEMO_MARRIAGES.items():
        for child in m.get("children", []):
            if m_id in pos and child in pos:
                x0, y0 = pos[m_id]; x1, y1 = pos[child]
                y0 += NODE_H/2; y1 -= NODE_H/2
                ex.extend([x0, x1, None]); ey.extend([y0, y1, None])
    # 人→其婚姻
    for pid, p in DEMO_PERSONS.items():
        for sub_m in p.get("children_marriages", []):
            if pid in pos and sub_m in pos:
                x0, y0 = pos[pid]; x1, y1 = pos[sub_m]
                y0 += NODE_H/2; y1 -= NODE_H/2
                ex.extend([x0, x1, None]); ey.extend([y0, y1, None])

    # 4) 軸域（向下為正）
    pad_x, pad_y = NODE_W * 0.75, NODE_H * 2.0
    min_x, max_x = min(xs) - pad_x, max(xs) + pad_x
    min_y, max_y = min(ys) - pad_y, max(ys) + pad_y

    # 5) 最穩定的作圖方式：完全用 Scatter（方塊節點 + 白字 + 線）
    fig = go.Figure()
    if ex:
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines",
                                 line=dict(width=2, color="rgba(80,80,80,1)"),
                                 hoverinfo="none", name=""))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker=dict(symbol="square", size=34, color=BOX_COLOR,
                    line=dict(width=1, color="rgba(0,0,0,0.25)")),
        text=labels, textposition="middle center",
        textfont=dict(color=TEXT_COLOR, size=12),
        hoverinfo="text", name=""
    ))
    fig.update_layout(
        title=dict(text="🧪 示範家族樹（固定示例）", x=0.02, y=0.98, xanchor="left"),
        xaxis=dict(visible=False, range=[min_x, max_x]),
        yaxis=dict(visible=False, range=[max_y, min_y]),  # 倒序：向下為正
        margin=dict(l=20, r=20, t=40, b=20),
        height=560, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

draw_demo_tree()
st.success("上面那張就是『家族樹示範圖』。如果你看得到，代表前端完全沒問題。接下來再換回完整互動版即可。")

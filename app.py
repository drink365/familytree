import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Tuple, List

from tree_layout import build_tree_from_marriages, tidy_layout

# ---- 視覺與間距：使用專業預設（一般用戶不需調） ----
NODE_W = 120
NODE_H = 40
MIN_SEP = 140    # 子樹最小水平距離（專業預設）
LEVEL_GAP = 140  # 代際垂直距離（專業預設）
BOX_COLOR = "rgba(12,74,110,1.0)"  # 深青色

st.set_page_config(page_title="家族樹（簡易版）", page_icon="🌳", layout="wide")
st.title("🌳 家族樹（簡易版）")

# ---- 初始化資料結構 ----
if "data" not in st.session_state:
    st.session_state.data = {"root_marriage_id": "", "marriages": {}, "persons": {}}

def ensure_person(name: str):
    """若人不存在就建立；僅設 label，婚姻列表先空。"""
    if not name:
        return
    persons = st.session_state.data["persons"]
    if name not in persons:
        persons[name] = {"label": name, "children_marriages": []}

def add_marriage(p1: str, p2: str, set_as_root_if_empty=True):
    """建立一對父母（婚姻節點）。"""
    if not p1 or not p2:
        return False, "請輸入父母雙方姓名"
    marriages = st.session_state.data["marriages"]
    mid = f"{p1}|{p2}"
    if mid in marriages:
        return False, "這對父母已存在"
    marriages[mid] = {"label": f"{p1}╳{p2}", "children": []}
    ensure_person(p1)
    ensure_person(p2)
    # 第一次建立父母時，把它當作根
    if set_as_root_if_empty and not st.session_state.data.get("root_marriage_id"):
        st.session_state.data["root_marriage_id"] = mid
    return True, "已新增父母"

def add_child_to_marriage(marriage_id: str, child_name: str, child_spouse: str = ""):
    """在指定父母節點下新增孩子；可選擇同時建立孩子的婚姻（配偶）。"""
    if not marriage_id:
        return False, "請先選擇父母"
    if not child_name:
        return False, "請輸入孩子姓名"

    marriages = st.session_state.data["marriages"]
    persons = st.session_state.data["persons"]

    if marriage_id not in marriages:
        return False, "父母不存在"

    ensure_person(child_name)
    if child_name not in marriages[marriage_id]["children"]:
        marriages[marriage_id]["children"].append(child_name)

    # 如果填了配偶，一併建立孩子的婚姻節點（方便繼續往下）
    if child_spouse:
        ensure_person(child_spouse)
        child_mid = f"{child_name}|{child_spouse}"
        if child_mid not in marriages:
            marriages[child_mid] = {"label": f"{child_name}╳{child_spouse}", "children": []}
        persons[child_name]["children_marriages"] = list(set(persons[child_name].get("children_marriages", []) + [child_mid]))

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

def draw_tree():
    data = st.session_state.data
    marriages = data["marriages"]
    persons = data["persons"]
    root_id = data.get("root_marriage_id") or (next(iter(marriages), ""))

    if not root_id:
        st.info("先建立至少一對父母，畫面就會出現家族樹。")
        return

    # 建樹＋佈局（自動間距、整掛平移）
    root, _ = build_tree_from_marriages(marriages, persons, root_id)
    pos = tidy_layout(root, min_sep=MIN_SEP, level_gap=LEVEL_GAP)

    # 節點框＋文字
    shapes, annotations = [], []
    def is_marriage(nid: str) -> bool:
        return nid in marriages

    for nid, (x, y) in pos.items():
        show_box = True
        shapes.append(dict(
            type="rect",
            x0=x - NODE_W/2, y0=y - NODE_H/2,
            x1=x + NODE_W/2, y1=y + NODE_H/2,
            line=dict(width=1),
            fillcolor=BOX_COLOR, opacity=1.0, layer="above",
            visible=show_box,
        ))
        label = marriages.get(nid, {}).get("label") if is_marriage(nid) else persons.get(nid, {}).get("label", nid)
        annotations.append(dict(
            x=x, y=y, text=label or nid, showarrow=False,
            font=dict(color="white"), xanchor="center", yanchor="middle"
        ))

    # 連線
    ex, ey = [], []
    for a, b in edges_for_plot(marriages, persons):
        if a in pos and b in pos:
            x0, y0 = pos[a]
            x1, y1 = pos[b]
            y0 += NODE_H/2
            y1 -= NODE_H/2
            ex.extend([x0, x1, None])
            ey.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", hoverinfo="none", line=dict(width=2)))
    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
        height=720,
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ---- 版面：左側操作、右側家族樹 ----
left, right = st.columns([0.9, 1.1])

with left:
    st.subheader("快速建立")
    with st.form("add_parents", clear_on_submit=True):
        st.markdown("**① 新增一對父母**（或伴侶）")
        p1 = st.text_input("父母一（例：陳一郎）")
        p2 = st.text_input("父母二（例：陳妻）")
        make_root = st.checkbox("設為家族根節點", value=not bool(st.session_state.data.get("root_marriage_id")))
        s = st.form_submit_button("新增父母")
        if s:
            ok, msg = add_marriage(p1.strip(), p2.strip(), set_as_root_if_empty=make_root)
            st.success(msg) if ok else st.error(msg)

    with st.form("add_child", clear_on_submit=True):
        st.markdown("**② 在某對父母下新增孩子**")
        marriages_keys = list(st.session_state.data["marriages"].keys())
        msel = st.selectbox("選擇父母", marriages_keys, index=0 if marriages_keys else None, placeholder="請先建立父母")
        cname = st.text_input("孩子姓名")
        csp = st.text_input("（可選）孩子的配偶姓名（會同步建立孩子的婚姻）")
        s2 = st.form_submit_button("新增孩子")
        if s2:
            ok, msg = add_child_to_marriage(msel, cname.strip(), csp.strip())
            st.success(msg) if ok else st.error(msg)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("載入示範資料"):
            from demo_data import marriages as demo_m, persons as demo_p  # 可移除
            st.session_state.data["marriages"] = {**demo_m}
            st.session_state.data["persons"] = {**demo_p}
            st.session_state.data["root_marriage_id"] = "陳一郎|陳妻"
            st.success("已載入示範")
    with c2:
        if st.button("清除全部資料"):
            st.session_state.data = {"root_marriage_id": "", "marriages": {}, "persons": {}}
            st.info("已清空")

    with st.expander("進階（匯入/匯出資料）", expanded=False):
        import json
        data_text = st.text_area("匯出/匯入 JSON（非必要）", value=json.dumps(st.session_state.data, ensure_ascii=False, indent=2), height=240)
        colA, colB = st.columns(2)
        with colA:
            st.download_button("下載目前資料", data=data_text.encode("utf-8"), file_name="family_data.json", mime="application/json")
        with colB:
            if st.button("套用上方 JSON"):
                try:
                    st.session_state.data = json.loads(data_text)
                    st.success("已套用")
                except Exception as e:
                    st.error(f"格式錯誤：{e}")

with right:
    draw_tree()

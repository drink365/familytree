import streamlit as st
from graphviz import Digraph
from typing import Dict, List, Tuple

"""
可直接複製為 `pages_familytree.py` 使用。
重點：
1) 以 Graphviz dot 進行分層排版（Sugiyama 法），自動幫你做 crossing minimization。
2) 引入「婚姻節點（marriage node）」：
   - 配偶以水平線相連（rank=same），
   - 子女從婚姻節點往下延伸，線條清楚、不再上彎。
3) 多處參數與技巧協助減少交錯：
   - rankdir=TB、ordering=out、splines=ortho、nodesep/ranksep 優化間距。
   - spouse 子圖（subgraph）強制同層且相鄰，並用隱形 rank guide 減少交錯。

資料格式（建議）：
family = {
    "people": {
        "p1": {"name": "清風", "gender": "M"},
        "p2": {"name": "連春", "gender": "F"},
        ...
    },
    # 每組婚姻一筆，children 為此婚姻所生的所有小孩（可為 0 個）
    "marriages": [
        {"id": "m1", "spouses": ["p1", "p2"], "children": ["c1", "c2"]},
        {"id": "m2", "spouses": ["p3", "p4"], "children": []},
        ...
    ]
}
"""

# -------------- 視覺屬性 -------------- #
NODE_STYLE = {
    "shape": "box",
    "style": "rounded",
    "fontname": "Noto Sans CJK TC, PingFang TC, Microsoft JhengHei, Arial",
    "fontsize": "12",
    "color": "#90A4AE",
    "penwidth": "1.2"
}

FEMALE_FILL = "#F3F6FF"
MALE_FILL = "#F7FBFF"

EDGE_STYLE = {
    "dir": "none",
    "color": "#6E7E8A",
    "penwidth": "1.2"
}

# 婚姻節點（小圓點）
MARRIAGE_NODE_ATTR = {
    "shape": "point",
    "width": "0.02",
    "height": "0.02",
    "label": "",
    "color": "#6E7E8A",
    "penwidth": "1.2"
}


def _add_person(g: Digraph, pid: str, name: str, gender: str):
    fill = FEMALE_FILL if (gender or "").upper().startswith("F") else MALE_FILL
    g.node(pid, label=name, fillcolor=fill, **NODE_STYLE, style="rounded,filled")


def _add_marriage(g: Digraph, mid: str, a: str, b: str):
    """建立婚姻節點，並把配偶以水平線相連：
    - 建立小圓點 m(mid)
    - 用 subgraph(rank=same) 強制 [a, m, b] 同層且相鄰
    - 以無方向邊 a--m、b--m 形成水平配偶線
    """
    m = f"m_{mid}"
    g.node(m, **MARRIAGE_NODE_ATTR)

    # 讓配偶與婚姻點在同一層且並排，降低交錯機率
    with g.subgraph(name=f"cluster_spouse_{mid}") as s:
        s.attr(rank="same")
        # invisible chain 確保左右順序（a, m, b）
        s.edge(a, m, style="invis", weight="100", constraint="false")
        s.edge(m, b, style="invis", weight="100", constraint="false")

    g.edge(a, m, **EDGE_STYLE, weight="5", constraint="false")
    g.edge(b, m, **EDGE_STYLE, weight="5", constraint="false")
    return m


def build_graph(family: Dict) -> Digraph:
    g = Digraph("FamilyTree", graph_attr={
        "rankdir": "TB",            # 上下分層
        "nodesep": "0.4",           # 同層節點間距
        "ranksep": "0.7",           # 上下層距離
        "splines": "ortho",          # 直角連線更清晰
        "ordering": "out",           # 盡量穩定輸出、減少交錯
        "pad": "0.2"
    })

    g.attr("node", **NODE_STYLE)
    g.attr("edge", **EDGE_STYLE)

    people = family.get("people", {})
    marriages: List[Dict] = family.get("marriages", [])

    # 1) 先畫人
    for pid, info in people.items():
        _add_person(g, pid, info.get("name", pid), info.get("gender", ""))

    # 2) 再畫婚姻與子女（子女從婚姻節點往下）
    for mi, m in enumerate(marriages):
        mid = m.get("id") or f"auto_m{mi+1}"
        spouses = m.get("spouses", [])
        if len(spouses) != 2:
            continue
        a, b = spouses
        mnode = _add_marriage(g, mid, a, b)

        children = m.get("children", [])
        for c in children:
            # 從婚姻點到子女；使子女明確在下一層
            g.edge(mnode, c, **EDGE_STYLE, weight="3")

    return g


# ----------------- Streamlit UI ----------------- #
st.set_page_config(page_title="③ 家族樹視覺化", page_icon="🌳", layout="wide")
st.header("③ 家族樹視覺化")

# 取得外部導入的 family 結構；若沒有就用 demo
def _demo_family():
    return {
        "people": {
            "p1": {"name": "清風", "gender": "M"},
            "p2": {"name": "連春", "gender": "F"},
            "p3": {"name": "榮如", "gender": "F"},
            "p4": {"name": "碩文", "gender": "M"},
            "c1": {"name": "冠瑜", "gender": "F"},
            "c2": {"name": "宥芸", "gender": "F"},
            "c3": {"name": "宥萱", "gender": "F"},
            "u1": {"name": "瀚晨", "gender": "M"},
            "u2": {"name": "冬彩", "gender": "F"},
            "n1": {"name": "威翔", "gender": "M"},
            "n2": {"name": "美杏", "gender": "F"},
            "n3": {"name": "秋芬", "gender": "F"},
            "n4": {"name": "鄺國", "gender": "M"},
            "x1": {"name": "婉郁", "gender": "F"},
            "x2": {"name": "忠義", "gender": "M"},
        },
        "marriages": [
            {"id": "M_A", "spouses": ["p1", "p2"], "children": ["p3", "u1"]},
            {"id": "M_B", "spouses": ["p3", "p4"], "children": ["c1", "c2", "c3"]},
            {"id": "M_C", "spouses": ["u1", "u2"], "children": ["n3", "n4"]},
            {"id": "M_D", "spouses": ["n1", "n2"], "children": ["x1", "x2"]},
        ]
    }

# 你的導入器可以把資料存到 st.session_state["family"]
family = st.session_state.get("family") or _demo_family()

# 左側控制參數
with st.sidebar:
    st.subheader("顯示設定")
    ranksep = st.slider("上下層距離 (ranksep)", 0.3, 1.5, 0.7, 0.1)
    nodesep = st.slider("同層節點距離 (nodesep)", 0.2, 1.0, 0.4, 0.1)
    ortho = st.checkbox("直角連線 (splines=ortho)", value=True)

# 產生圖
G = build_graph(family)
# 動態套參數
G.graph_attr.update({
    "ranksep": str(ranksep),
    "nodesep": str(nodesep),
    "splines": "ortho" if ortho else "true",
})

st.graphviz_chart(G, use_container_width=True)

# 說明區
with st.expander("使用說明 / 實作重點"):
    st.markdown(
        """
        - **配偶為水平線**：以 `rank=same` 讓配偶與婚姻節點在同層，再用兩條無方向邊連到 **婚姻節點**（小圓點）。
        - **子女從婚姻點垂直往下**：所有子女都從該婚姻點往下延伸，結構一目了然。
        - **減少交錯**：Graphviz 的 dot 會自動做 crossing minimization；本程式再用 `ordering=out`、`subgraph` 排序與 `invisible edges` 穩定布局，能有效降低交錯。
        - **多婚姻/再婚**：同一人可在多個 marriage record 中出現，Graphviz 仍可計算分層與最小交錯（必要時你可以為不同婚姻加上 `rank=same` 的引導 subgraph 來固定相對位置）。
        """
    )

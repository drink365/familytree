import streamlit as st
from graphviz import Digraph

def build_graph(family):
    g = Digraph("FamilyTree", graph_attr={
        "rankdir": "TB",
        "splines": "ortho",
        "nodesep": "0.5",
        "ranksep": "0.7",
        "ordering": "out"
    })

    g.attr("node", shape="box", style="rounded,filled", fontname="Microsoft JhengHei", fontsize="12", color="#90A4AE", penwidth="1.2")
    g.attr("edge", dir="none", color="#6E7E8A", penwidth="1.2")

    # 1. 畫出人物節點
    for pid, info in family.get("people", {}).items():
        fill = "#F3F6FF" if info.get("gender", "") == "F" else "#F7FBFF"
        g.node(pid, label=info.get("name", pid), fillcolor=fill)

    # 2. 每組婚姻建立一個婚姻節點 m
    for i, m in enumerate(family.get("marriages", [])):
        spouses = m.get("spouses", [])
        if len(spouses) != 2:
            continue
        a, b = spouses

        mnode = f"m{i}"
        g.node(mnode, shape="point", width="0.01", label="", color="#6E7E8A", penwidth="1.2")

        # 配偶與婚姻點在同層
        with g.subgraph() as s:
            s.attr(rank="same")
            s.edge(a, mnode, weight="5")
            s.edge(b, mnode, weight="5")

        # 子女從婚姻點往下
        for c in m.get("children", []):
            g.edge(mnode, c, weight="3")

    return g

st.set_page_config(page_title="家族樹", layout="wide")
st.header("③ 家族樹視覺化")

# 假資料示例，實際請換成你匯入的 family 結構
family = {
    "people": {},
    "marriages": []
}

G = build_graph(family)
st.graphviz_chart(G, use_container_width=True)


import streamlit as st
import json
import networkx as nx
from pyvis.network import Network
import tempfile

st.title("家族樹 (直角折線版)")

# 匯入 JSON
uploaded = st.file_uploader("匯入 JSON", type="json")
family_data = None
if uploaded:
    family_data = json.load(uploaded)
    st.success("已匯入資料！")

if family_data:
    # 建立 NetworkX 圖
    G = nx.DiGraph()
    for m in family_data["members"]:
        G.add_node(m["id"], label=m["name"])

    # 加入親子關係
    for c in family_data["children"]:
        G.add_edge(c["father"], c["child"])
        G.add_edge(c["mother"], c["child"])

    # 使用 PyVis 繪圖
    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(G)

    # 婚姻線
    for m in family_data["marriages"]:
        style = "dash" if m["status"] != "married" else "line"
        net.add_edge(m["husband"], m["wife"], dashes=(style=="dash"), physics=False)

    # 直角折線配置
    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "hubsize"
            }
        },
        "edges": {
            "smooth": {
                "enabled": True,
                "type": "horizontal"
            }
        },
        "physics": {"enabled": False}
    }

    import json as js
    net.set_options(js.dumps(options))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        st.components.v1.html(open(tmp.name, "r", encoding="utf-8").read(), height=600)

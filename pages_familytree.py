import json
from typing import Dict, List

import streamlit as st
from graphviz import Digraph

# =============================
# pages_familytree.py — 強制分層（世代一定分開）
# =============================
# 方式：
# 1) 仍採「婚姻節點」：配偶水平、子女由婚姻點往下。
# 2) 以 **不可見父母→子女邊**（style=invis, constraint=true, weight 高, minlen>=2）
#    強制 Graphviz 在層級上把父母放在子女之上；
#    同時 mnode→child 邊也保留 constraint=true，讓子女往下落位。
# 3) 不再依賴事前計算世代；任何資料都會正確分層。

# ---------- 匿名示範資料（可改為你的匯入資料） ---------- #
DEMO_FAMILY: Dict = {
    "people": {
        "p1": {"name": "人甲", "gender": "M"},
        "p2": {"name": "人乙", "gender": "F"},
        "p3": {"name": "人丙", "gender": "F"},
        "p4": {"name": "人丁", "gender": "M"},
        "u1": {"name": "外戚甲", "gender": "M"},
        "u2": {"name": "外戚乙", "gender": "F"},
        "c1": {"name": "子一", "gender": "M"},
        "c2": {"name": "子二", "gender": "F"},
        "c3": {"name": "子三", "gender": "F"}
    },
    "marriages": [
        {"id": "m1", "spouses": ["p1", "p2"], "children": ["p3", "u1"]},
        {"id": "m2", "spouses": ["p3", "p4"], "children": ["c1", "c2", "c3"]},
        {"id": "m3", "spouses": ["u1", "u2"], "children": []}
    ]
}

# ---------- 視覺屬性 ---------- #
NODE_COMMON = dict(shape="box", style="rounded,filled", fontname="Microsoft JhengHei, PingFang TC, Arial",
                   fontsize="12", color="#90A4AE", penwidth="1.2")
EDGE_COMMON = dict(dir="none", color="#6E7E8A", penwidth="1.2")
FILL_MALE = "#F7FBFF"
FILL_FEMALE = "#F3F6FF"


def normalize_gender(val: str) -> str:
    v = (val or "").strip().lower()
    if v in ("f", "female", "女", "女性"):
        return "F"
    return "M"


def build_graph(family: Dict, nodesep: float = 0.5, ranksep: float = 1.0, ortho: bool = True) -> Digraph:
    g = Digraph("FamilyTree", graph_attr=dict(
        rankdir="TB",
        nodesep=str(nodesep),
        ranksep=str(ranksep),
        splines="ortho" if ortho else "true",
        ordering="out",
        pad="0.2"
    ))

    g.attr("node", **NODE_COMMON)
    g.attr("edge", **EDGE_COMMON)

    people = family.get("people", {})
    marriages: List[Dict] = family.get("marriages", [])

    # 1) 人物節點
    for pid, info in people.items():
        name = info.get("name", pid)
        gender = normalize_gender(info.get("gender", ""))
        fill = FILL_FEMALE if gender == "F" else FILL_MALE
        g.node(pid, label=name, fillcolor=fill)

    # 2) 婚姻 + 子女
    for i, m in enumerate(marriages):
        spouses = m.get("spouses", [])
        children = m.get("children", [])
        if len(spouses) != 2:
            continue
        a, b = spouses
        mid = m.get("id") or f"m{i+1}"
        mnode = f"_m_{mid}"

        # 婚姻節點（小圓點）
        g.node(mnode, shape="point", width="0.02", height="0.02", label="", color="#6E7E8A", penwidth="1.2")

        # 讓 a, mnode, b 在同層（水平配偶線）
        with g.subgraph(name=f"cluster_spouse_{mid}") as s:
            s.attr(rank="same")
            # 用隱形邊固定順序 a - m - b（不影響分層）
            s.edge(a, mnode, style="invis", weight="50", constraint="false")
            s.edge(mnode, b, style="invis", weight="50", constraint="false")

        # 真實配偶線（保持水平；不參與分層）
        g.edge(a, mnode, weight="4", constraint="false")
        g.edge(b, mnode, weight="4", constraint="false")

        # 子女由婚姻節點往下（參與分層、最少一階）
        for c in children:
            g.edge(mnode, c, weight="6", constraint="true", minlen="1")
            # 關鍵：加「不可見父母→子女」邊，強制父母在子女之上
            # 這兩條邊只用來約束層級，不顯示
            g.edge(a, c, style="invis", constraint="true", weight="100", minlen="2")
            g.edge(b, c, style="invis", constraint="true", weight="100", minlen="2")

    return g


# ---------- 匯入 / 匯出 ---------- #

def _export_family_download_btn(family: Dict):
    data = json.dumps(family, ensure_ascii=False, indent=2)
    st.download_button("下載 JSON", data=data, file_name="family.json", mime="application/json")


def _import_family_from_uploader(key: str = "family_upload") -> Dict:
    up = st.file_uploader("上傳 family.json（UTF‑8）", type=["json"], key=key)
    if up is not None:
        try:
            text = up.read().decode("utf-8")
            data = json.loads(text)
            if isinstance(data, dict) and "people" in data and "marriages" in data:
                return data
            st.error("JSON 結構不正確，需包含 people 與 marriages。")
        except Exception as e:
            st.error(f"解析 JSON 失敗：{e}")
    return {}


# ---------- 主渲染 ---------- #

def render():
    st.markdown("## ③ 家族樹視覺化（強制分層 / 配偶水平 / 子女垂直）")

    # 取得資料（優先用 session_state）
    if "family" not in st.session_state or not st.session_state.get("family"):
        st.session_state["family"] = DEMO_FAMILY
    family: Dict = st.session_state.get("family", DEMO_FAMILY)

    with st.sidebar:
        st.subheader("資料管理")
        imported = _import_family_from_uploader()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("匯入到畫面", use_container_width=True):
                if imported:
                    st.session_state["family"] = imported
                    family = imported
                    st.success("已匯入。")
                else:
                    st.warning("請先選擇可解析的 JSON。")
        with c2:
            if st.button("載入示範", use_container_width=True):
                st.session_state["family"] = DEMO_FAMILY
                family = DEMO_FAMILY
                st.info("已載入示範資料。")
        with c3:
            if st.button("清空資料", use_container_width=True):
                st.session_state["family"] = {"people": {}, "marriages": []}
                family = st.session_state["family"]
                st.info("已清空。")

        st.caption("完成後可下載目前資料：")
        _export_family_download_btn(family)

        st.subheader("版面設定")
        nodesep = st.slider("同層距離 nodesep", 0.2, 2.0, 0.5, 0.1)
        ranksep = st.slider("層距 ranksep", 0.4, 2.5, 1.0, 0.1)
        ortho = st.checkbox("直角連線 (splines=ortho)", value=True)

    # 畫圖
    G = build_graph(family, nodesep=nodesep, ranksep=ranksep, ortho=ortho)
    st.graphviz_chart(G, use_container_width=True)

    with st.expander("JSON 資料結構說明", expanded=False):
        st.markdown(
            """
            ```json
            {
              "people": {
                "id1": {"name": "姓名", "gender": "M|F|男|女"},
                "id2": {"name": "姓名", "gender": "F"}
              },
              "marriages": [
                {"id": "m1", "spouses": ["id1", "id2"], "children": ["cid1", "cid2"]}
              ]
            }
            ```
            - **強制分層**：以不可見的「父母→子女」邊（`style=invis, constraint=true, minlen>=2`）確保父母在上、子女在下。
            - **配偶水平**：以婚姻節點連接配偶，線條不再上彎。
            - **子女垂直**：所有子女自婚姻節點往下延伸。
            - 支援再婚/多婚姻。
            """
        )


if __name__ == "__main__":
    render()

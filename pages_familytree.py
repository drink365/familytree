import json
from typing import Dict, List

import streamlit as st
from graphviz import Digraph

# =============================
# Family Tree (Graphviz + 婚姻節點 + render())
# =============================
# 本頁面符合你專案對 page 模組需要有 render() 的要求。
# 特色：
# 1) 以 Graphviz dot 做分層排版（TB），自帶最小交錯優化。
# 2) 採用「婚姻節點」：配偶以水平線相連；子女由婚姻節點垂直往下延伸。
# 3) 內建簡易匯入/匯出（JSON），並使用 st.session_state["family"] 保存。
# 4) 絕不包含任何你的真實姓名資料；示範資料全為匿名。
#
# 資料格式 family：
# family = {
#   "people": {
#       "p1": {"name": "人甲", "gender": "M"},
#       "p2": {"name": "人乙", "gender": "F"},
#       ...
#   },
#   "marriages": [
#       {"id": "m1", "spouses": ["p1", "p2"], "children": ["c1", "c2"]},
#       ...
#   ]
# }

# ---------- Demo Data（匿名） ---------- #
DEMO_FAMILY: Dict = {
    "people": {
        "p1": {"name": "人甲", "gender": "M"},
        "p2": {"name": "人乙", "gender": "F"},
        "p3": {"name": "人丙", "gender": "F"},
        "p4": {"name": "人丁", "gender": "M"},
        "c1": {"name": "子一", "gender": "M"},
        "c2": {"name": "子二", "gender": "F"},
        "c3": {"name": "子三", "gender": "F"},
        "u1": {"name": "外戚甲", "gender": "M"},
        "u2": {"name": "外戚乙", "gender": "F"}
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
FILL_MALE = "#F7FBFF"   # 淡藍
FILL_FEMALE = "#F3F6FF" # 淡靛


# ---------- 工具 ---------- #
def normalize_gender(val: str) -> str:
    v = (val or "").strip().lower()
    if v in ("f", "female", "女", "女性"):
        return "F"
    return "M"


def build_graph(family: Dict) -> Digraph:
    g = Digraph("FamilyTree", graph_attr=dict(
        rankdir="TB",         # 上 -> 下
        nodesep="0.5",        # 同層距離
        ranksep="0.8",        # 層距
        splines="ortho",      # 直角線
        ordering="out",
        pad="0.2"
    ))

    # 預設樣式（這裡已經指定 style，後續 g.node() 不再傳 style 以避免「multiple values for style」）
    g.attr("node", **NODE_COMMON)
    g.attr("edge", **EDGE_COMMON)

    people = family.get("people", {})

    # 1) 人物節點
    for pid, info in people.items():
        name = info.get("name", pid)
        gender = normalize_gender(info.get("gender", ""))
        fill = FILL_FEMALE if gender == "F" else FILL_MALE
        g.node(pid, label=name, fillcolor=fill)

    # 2) 婚姻 + 子女
    for i, m in enumerate(family.get("marriages", [])):
        spouses: List[str] = m.get("spouses", [])
        if len(spouses) != 2:
            continue
        a, b = spouses
        mid = m.get("id") or f"m{i+1}"
        mnode = f"_m_{mid}"

        # 婚姻節點（小圓點）
        g.node(mnode, shape="point", width="0.02", height="0.02", label="", color="#6E7E8A", penwidth="1.2")

        # 讓 a, mnode, b 三者在同層並相鄰（水平配偶線）
        with g.subgraph(name=f"cluster_spouse_{mid}") as s:
            s.attr(rank="same")
            # 用隱形邊固定左右順序，提升穩定度／減少交錯
            s.edge(a, mnode, style="invis", weight="100", constraint="false")
            s.edge(mnode, b, style="invis", weight="100", constraint="false")

        # 真正的配偶線（水平）
        g.edge(a, mnode, weight="5", constraint="false")
        g.edge(b, mnode, weight="5", constraint="false")

        # 子女自婚姻節點往下
        for c in m.get("children", []):
            g.edge(mnode, c, weight="3")

    return g


# ---------- 匯入 / 匯出 ---------- #

def _export_family_download_btn(family: Dict):
    data = json.dumps(family, ensure_ascii=False, indent=2)
    st.download_button(
        label="下載 JSON",
        data=data,
        file_name="family.json",
        mime="application/json"
    )


def _import_family_from_uploader(key: str = "family_upload") -> Dict:
    up = st.file_uploader("上傳 family.json（UTF‑8）", type=["json"], key=key)
    if up is not None:
        try:
            text = up.read().decode("utf-8")
            data = json.loads(text)
            if not isinstance(data, dict) or "people" not in data or "marriages" not in data:
                st.error("JSON 結構不正確，請確認包含 people 與 marriages。")
                return {}
            return data
        except Exception as e:
            st.error(f"解析 JSON 失敗：{e}")
    return {}


# ---------- 主渲染 ---------- #

def render():
    st.markdown("## ③ 家族樹視覺化")

    # 取得 family（優先用 session_state，其次用 Demo）
    if "family" not in st.session_state or not st.session_state.get("family"):
        st.session_state["family"] = DEMO_FAMILY
    family: Dict = st.session_state.get("family", DEMO_FAMILY)

    # ---- 左側：資料控件 ---- #
    with st.sidebar:
        st.subheader("資料管理")
        imported = _import_family_from_uploader()
        colA, colB, colC = st.columns([1,1,1])
        with colA:
            if st.button("匯入到畫面", use_container_width=True, help="將上傳的 JSON 匯入到本頁（不自動儲存）"):
                if imported:
                    st.session_state["family"] = imported
                    family = imported
                    st.success("已匯入。")
                else:
                    st.warning("尚未選擇或解析成功的檔案。")
        with colB:
            if st.button("載入示範", use_container_width=True):
                st.session_state["family"] = DEMO_FAMILY
                family = DEMO_FAMILY
                st.info("已載入示範資料。")
        with colC:
            if st.button("清空資料", use_container_width=True):
                st.session_state["family"] = {"people": {}, "marriages": []}
                family = st.session_state["family"]
                st.info("已清空。")

        st.caption("完成調整後可下載 JSON：")
        _export_family_download_btn(family)

        st.subheader("版面設定")
        nodesep = st.slider("同層距離 nodesep", 0.2, 1.5, 0.5, 0.1)
        ranksep = st.slider("層距 ranksep", 0.4, 1.6, 0.8, 0.1)
        ortho = st.checkbox("直角連線 (splines=ortho)", value=True)

    # ---- 畫圖 ---- #
    G = build_graph(family)
    G.graph_attr.update({
        "nodesep": f"{nodesep}",
        "ranksep": f"{ranksep}",
        "splines": "ortho" if ortho else "true"
    })

    st.graphviz_chart(G, use_container_width=True)

    with st.expander("資料格式說明 / 注意事項", expanded=False):
        st.markdown(
            """
            **JSON 結構**
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
            - **配偶顯示為水平線**，系統會在兩人之間建立一個「婚姻節點」（小圓點）。
            - **子女**會由該婚姻節點**垂直**往下延伸，層次清楚。
            - 佈局使用 Graphviz `dot`，已內建 crossing minimization。如仍有交錯，可調整 `nodesep/ranksep` 或在資料上調整婚姻與子女順序。
            - 支援**一人多段婚姻**：同一個 person id 可出現在多筆 `marriages` 的 `spouses` 中。
            """
        )


# 讓此檔可獨立執行（可選）
if __name__ == "__main__":
    render()

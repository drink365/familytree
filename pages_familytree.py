import json
from collections import defaultdict, deque
from typing import Dict, List, Set

import streamlit as st
from graphviz import Digraph

# =============================
# pages_familytree.py — 分代清楚、不交錯（婚姻節點 + 自動世代計算 + render()）
# =============================
# - 以 Graphviz dot 的分層排版，並加入「世代(rank)」約束，強化父母在上、子女在下。
# - 配偶以水平線相連（婚姻節點），子女從婚姻節點垂直往下延伸。
# - 支援多段婚姻；以 crossing-minimization + rank 約束儘量減少交錯。
# - 內建 JSON 匯入/匯出與匿名示範資料。

# ---------- 匿名示範資料（你可改為自己的匯入資料） ---------- #
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


# ---------- 輔助：性別正規化 ---------- #
def normalize_gender(val: str) -> str:
    v = (val or "").strip().lower()
    if v in ("f", "female", "女", "女性"):
        return "F"
    return "M"


# ---------- 計算世代（層級） ---------- #
# 規則：
# - 若某人沒有父母（未出現在任何 children）→ 視為根（世代=0）。
# - 子女的世代 = min(父母世代) + 1（若有多段婚姻，取最小以保持保守層級）。

def compute_generations(family: Dict) -> Dict[str, int]:
    marriages: List[Dict] = family.get("marriages", [])

    parents_of: Dict[str, Set[str]] = defaultdict(set)  # child -> {parent ids}
    all_people: Set[str] = set(family.get("people", {}).keys())

    for m in marriages:
        spouses = m.get("spouses", [])
        children = m.get("children", [])
        if len(spouses) == 2:
            a, b = spouses
            for c in children:
                parents_of[c].update([a, b])

    children_all = set(parents_of.keys())
    # roots: never a child in any marriage
    roots = sorted(list(all_people - children_all))

    gen: Dict[str, int] = {p: 0 for p in roots}

    # 建立親子圖（有向：parent -> child）
    graph: Dict[str, List[str]] = defaultdict(list)
    indeg: Dict[str, int] = defaultdict(int)

    for c, parents in parents_of.items():
        for p in parents:
            graph[p].append(c)
            indeg[c] += 1
            all_people.update([p, c])

    # 對未出現在任何邊上的人也要在 gen 給初值
    for p in all_people:
        gen.setdefault(p, 0)

    # 拓撲式 BFS：從 roots 往下推層級
    q = deque(roots)
    visited = set(roots)
    while q:
        u = q.popleft()
        for v in graph.get(u, []):
            # v 可能有兩個父母，取更小的父母層級 + 1
            new_g = gen[u] + 1
            if v not in gen:
                gen[v] = new_g
            else:
                gen[v] = min(gen[v], new_g)
            if v not in visited:
                visited.add(v)
                q.append(v)

    return gen


# ---------- 建圖（套用世代 rank） ---------- #

def build_graph(family: Dict, nodesep: float = 0.5, ranksep: float = 0.9, ortho: bool = True) -> Digraph:
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

    # 計算每個人的世代
    generations = compute_generations(family)
    # 將人依世代分組
    level_people: Dict[int, List[str]] = defaultdict(list)
    for pid in people.keys():
        level_people[generations.get(pid, 0)].append(pid)

    # 先把所有人物節點畫好
    for pid, info in people.items():
        name = info.get("name", pid)
        gender = normalize_gender(info.get("gender", ""))
        fill = FILL_FEMALE if gender == "F" else FILL_MALE
        g.node(pid, label=name, fillcolor=fill)

    # 依世代建立 rank=same 子圖，強制同代同層
    for lvl, ids in sorted(level_people.items()):
        with g.subgraph(name=f"cluster_lvl_{lvl}") as s:
            s.attr(rank="same")
            for pid in ids:
                s.node(pid)

    # 婚姻節點：放在配偶所在世代（取較小的那一方），以維持水平
    for i, m in enumerate(marriages):
        spouses = m.get("spouses", [])
        children = m.get("children", [])
        if len(spouses) != 2:
            continue
        a, b = spouses
        mid = m.get("id") or f"m{i+1}"
        mnode = f"_m_{mid}"

        level = min(generations.get(a, 0), generations.get(b, 0))

        # 婚姻點本身（小圓點）
        g.node(mnode, shape="point", width="0.02", height="0.02", label="", color="#6E7E8A", penwidth="1.2")
        # 使婚姻點也在該層
        with g.subgraph(name=f"cluster_mar_{mid}") as s:
            s.attr(rank="same")
            s.node(mnode)

        # 用隱形邊固定左右順序，讓 a - mnode - b 並排
        with g.subgraph(name=f"cluster_spouse_{mid}") as s:
            s.attr(rank="same")
            s.edge(a, mnode, style="invis", weight="100", constraint="false")
            s.edge(mnode, b, style="invis", weight="100", constraint="false")

        # 真實的配偶線（水平）
        g.edge(a, mnode, weight="6", constraint="false")
        g.edge(b, mnode, weight="6", constraint="false")

        # 子女自婚姻點往下
        for c in children:
            g.edge(mnode, c, weight="3")

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
    st.markdown("## ③ 家族樹視覺化（分代清楚 / 減少交錯）")

    # 取得家族資料（優先用 session_state）
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
        nodesep = st.slider("同層距離 nodesep", 0.2, 1.5, 0.5, 0.1)
        ranksep = st.slider("世代間距 ranksep", 0.4, 2.0, 0.9, 0.1)
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
            - **配偶水平連線**：在兩人之間建立小圓點「婚姻節點」，線不再往上彎。
            - **子女垂直向下**：所有子女從婚姻節點往下延伸，層次清楚。
            - **世代固定**：系統自動計算世代，將同代放在同一層，能夠明顯降低交錯。
            - **再婚/多婚姻**：同一人可出現在多筆 `marriages` 的 `spouses` 中。
            """
        )


if __name__ == "__main__":
    render()

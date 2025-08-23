# app.py
# ==========================================================
# 家族平台（Graphviz 家族樹 + 台灣民法法定繼承試算, 嚴格順位制）
# - 家族樹：前任在左、本人置中、現任在右；三代分層；在婚實線、離婚虛線
# - 繼承試算：配偶為當然繼承人，僅與「第一個有人的順位」共同繼承
#   * 子女：配偶視同一子，平均分
#   * 父母或兄弟姊妹：配偶 1/2，該順位均分 1/2
#   * 祖父母：配偶 2/3，祖父母均分 1/3
# - 不需任何除錯開關；行銷友善的簡潔 UI
#
# 需求（requirements.txt）
# streamlit==1.37.0
# graphviz==0.20.3
# ==========================================================

import io
import json
from typing import Dict, List, Set, Tuple

import streamlit as st
from graphviz import Digraph

# =============== 外觀設定 ===============
st.set_page_config(page_title="家族平台｜家族樹＋法定繼承", layout="wide")
PRIMARY = "#184a5a"
ACCENT = "#0e2d3b"

st.markdown(
    """
    <style>
    .stApp {background-color: #f7fbfd;}
    .big-title {font-size: 32px; font-weight: 800; color:#0e2d3b; letter-spacing:1px;}
    .subtle {color:#55707a}
    .pill {
        display:inline-block; padding:6px 10px; border-radius:999px;
        background:#e7f3f6; color:#184a5a; font-size:12px; margin-right:8px;
    }
    .card {
        border:1px solid #e8eef0; border-radius:12px; padding:14px 16px; background:#fff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">🌳 家族平台（家族樹＋法定繼承）</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">前任在左、本人置中、現任在右；三代分層；台灣民法法定繼承（嚴格順位制）</div>', unsafe_allow_html=True)
st.write("")

# =============== 節點/線條樣式 ===============
NODE_STYLE = {
    "shape": "box",
    "style": "filled",
    "fillcolor": PRIMARY,
    "fontcolor": "white",
    "color": ACCENT,
    "penwidth": "1.2",
}
EDGE_STYLE = {"color": PRIMARY}

# =============== 一鍵示範資料 ===============
DEMO = {
    "persons": {
        "c_yilang": {"name": "陳一郎"},
        "c_wife": {"name": "陳妻"},
        "c_exwife": {"name": "陳前妻"},
        "wang_zi": {"name": "王子"},
        "wang_zi_wife": {"name": "王子妻"},
        "wang_sun": {"name": "王孫"},
        "chen_da": {"name": "陳大"},
        "chen_er": {"name": "陳二"},
        "chen_san": {"name": "陳三"},
    },
    "marriages": [
        {"id": "m_current", "a": "c_yilang", "b": "c_wife", "status": "current"},
        {"id": "m_ex", "a": "c_yilang", "b": "c_exwife", "status": "ex"},
        {"id": "m_wang", "a": "wang_zi", "b": "wang_zi_wife", "status": "current"},
    ],
    "children": [
        {"marriage_id": "m_current", "children": ["chen_da","chen_er","chen_san"]},
        {"marriage_id": "m_ex", "children": ["wang_zi"]},
        {"marriage_id": "m_wang", "children": ["wang_sun"]},
    ]
}

if "data" not in st.session_state:
    st.session_state["data"] = DEMO

# =============== 共用工具 ===============
def map_children(children_list: List[Dict]) -> Dict[str, List[str]]:
    return {c["marriage_id"]: list(c.get("children", [])) for c in children_list}

def marriages_of(pid: str, marriages: List[Dict]) -> List[Dict]:
    return [m for m in marriages if m["a"] == pid or m["b"] == pid]

def partner_of(m: Dict, pid: str) -> str:
    return m["b"] if m["a"] == pid else m["a"]

def current_spouses_of(pid: str, marriages: List[Dict]) -> List[str]:
    return [partner_of(m, pid) for m in marriages if (m["a"] == pid or m["b"] == pid) and m.get("status") == "current"]

def ex_spouses_of(pid: str, marriages: List[Dict]) -> List[str]:
    return [partner_of(m, pid) for m in marriages if (m["a"] == pid or m["b"] == pid) and m.get("status") == "ex"]

def children_of_via_marriage(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    """被繼承人的子女（透過其所有婚姻的 children）"""
    kids: List[str] = []
    for m in marriages:
        if m["a"] == pid or m["b"] == pid:
            kids += ch_map.get(m["id"], [])
    # 去重保序
    seen, ordered = set(), []
    for k in kids:
        if k not in seen:
            seen.add(k); ordered.append(k)
    return ordered

def parents_of_person(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    """找父母：在任何 marriage 的 children 裏面含有 pid，則 a/b 即父母"""
    parents: List[str] = []
    for m in marriages:
        if pid in ch_map.get(m["id"], []):
            for p in [m["a"], m["b"]]:
                if p not in parents:
                    parents.append(p)
    return parents

def siblings_of_person(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    """找兄弟姊妹：全血（同父同母），再加半血（同父或同母）"""
    sibs: Set[str] = set()
    # 全血：與我同在的 marriage 的其它 children
    for m in marriages:
        kids = ch_map.get(m["id"], [])
        if pid in kids:
            for k in kids:
                if k != pid:
                    sibs.add(k)
    # 半血：我每一位父或母，去找他/她「其他」婚姻所生子女
    my_parents = parents_of_person(pid, marriages, ch_map)
    for par in my_parents:
        for m in marriages_of(par, marriages):
            kids = ch_map.get(m["id"], [])
            for k in kids:
                if k != pid:
                    sibs.add(k)
    return list(sorted(sibs))

def grandparents_of_person(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    gps: Set[str] = set()
    for par in parents_of_person(pid, marriages, ch_map):
        for g in parents_of_person(par, marriages, ch_map):
            gps.add(g)
    return list(sorted(gps))

# =============== 家族樹 ===============
def build_graph(data: dict, root_id: str) -> Digraph:
    dot = Digraph(comment="Family Tree", engine="dot", format="svg")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.7")
    dot.node_attr.update(NODE_STYLE)
    dot.edge_attr.update(EDGE_STYLE)

    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    # 節點
    for pid, info in persons.items():
        dot.node(pid, info.get("name", pid))

    # 婚姻 junction + 父母邊
    for m in marriages:
        mid = m["id"]; a, b = m["a"], m["b"]
        dotted = (m.get("status") == "ex")
        dot.node(mid, "", shape="point", width="0.02", color=PRIMARY)
        style = "dashed" if dotted else "solid"
        dot.edge(a, mid, dir="none", style=style)
        dot.edge(b, mid, dir="none", style=style)
        with dot.subgraph() as s:
            s.attr(rank="same"); s.node(a); s.node(b)

    # 子女：同層；左→右以不可見邊固定
    for mid, kids in ch_map.items():
        if not kids: continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for cid in kids: s.node(cid)
        for i in range(len(kids)-1):
            dot.edge(kids[i], kids[i+1], style="invis", weight="200")
        for cid in kids:
            dot.edge(mid, cid)

    # 鎖「前任→本人→現任」橫向順序
    ex_map = {pid: [] for pid in persons}
    cur_map = {pid: [] for pid in persons}
    for m in marriages:
        a, b, status = m["a"], m["b"], m.get("status")
        if status == "ex":
            ex_map[a].append(b); ex_map[b].append(a)
        elif status == "current":
            cur_map[a].append(b); cur_map[b].append(a)
    for me in persons:
        exes = ex_map.get(me, [])
        curs = cur_map.get(me, [])
        with dot.subgraph() as s:
            s.attr(rank="same")
            for x in exes: s.node(x)
            s.node(me)
            for c in curs: s.node(c)
        chain = exes + [me] + curs
        for i in range(len(chain)-1):
            dot.edge(chain[i], chain[i+1], style="invis", weight="9999")

    # 三代分層
    gen0 = {root_id} | set(current_spouses_of(root_id, marriages)) | set(ex_spouses_of(root_id, marriages))
    gen1 = set(children_of_via_marriage(root_id, marriages_of(root_id, marriages), ch_map))
    gen2 = set()
    for kid in list(gen1):
        gen2 |= set(children_of_via_marriage(kid, marriages_of(kid, marriages), ch_map))

    if gen0:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for p in gen0: s.node(p)
        # 把 root 的婚姻 junction 壓回第一層
        for m in marriages_of(root_id, marriages):
            with dot.subgraph() as s:
                s.attr(rank="same"); s.node(m["id"])
    if gen1:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for p in gen1: s.node(p)
    if gen2:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for p in gen2: s.node(p)

    return dot

# =============== 法定繼承（嚴格順位制） ===============
def intestate_shares_tw(data: dict, decedent: str) -> Tuple[Dict[str, float], str, List[str]]:
    """
    嚴格依順位選擇唯一一個血親群組與配偶共同繼承（若存在）。
    - ① 直系卑親屬（子女；本版不實作「代位」與死亡判斷，預設皆在世）
    - ② 父母
    - ③ 兄弟姊妹（含半血）
    - ④ 祖父母
    比例依民法第1144條（配偶為當然繼承人）：
      * 與①並存：配偶與全部子女「平均分」
      * 與②並存：配偶 1/2，其餘 1/2 父母均分
      * 與③並存：配偶 1/2，其餘 1/2 手足均分
      * 與④並存：配偶 2/3，其餘 1/3 祖父母均分
    """
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    spouse_list = current_spouses_of(decedent, marriages)  # 依你的規則：現任只能一人
    spouse = spouse_list[0] if spouse_list else None

    # ① 子女
    group_children = children_of_via_marriage(decedent, marriages_of(decedent, marriages), ch_map)

    # ② 父母
    group_parents = parents_of_person(decedent, marriages, ch_map)

    # ③ 兄弟姊妹（含半血）
    group_sibs = siblings_of_person(decedent, marriages, ch_map)

    # ④ 祖父母
    group_grand = grandparents_of_person(decedent, marriages, ch_map)

    shares: Dict[str, float] = {}
    heirs_seq: List[str] = []

    def avg_assign(ids: List[str], portion: float):
        if not ids: return
        each = portion / len(ids)
        for i in ids:
            shares[i] = shares.get(i, 0) + each

    if group_children:
        heirs_seq = ["直系卑親屬（子女）"] + (["配偶"] if spouse else [])
        # 與子女並存：全部平均（配偶視同一子）
        base = group_children + ([spouse] if spouse else [])
        avg_assign(base, 1.0)
        return shares, "順位①（子女）", [persons.get(x, {}).get("name", x) for x in base]

    if group_parents:
        heirs_seq = ["直系尊親屬（父母）"] + (["配偶"] if spouse else [])
        if spouse:
            shares[spouse] = 0.5
            avg_assign(group_parents, 0.5)
            return shares, "順位②（父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_parents]
        else:
            avg_assign(group_parents, 1.0)
            return shares, "順位②（父母）", [persons.get(x, {}).get("name", x) for x in group_parents]

    if group_sibs:
        heirs_seq = ["兄弟姊妹"] + (["配偶"] if spouse else [])
        if spouse:
            shares[spouse] = 0.5
            avg_assign(group_sibs, 0.5)
            return shares, "順位③（兄弟姊妹）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_sibs]
    else:
        # 沒有兄弟姊妹也繼續往下
        pass

    if group_grand:
        heirs_seq = ["祖父母"] + (["配偶"] if spouse else [])
        if spouse:
            shares[spouse] = 2/3
            avg_assign(group_grand, 1/3)
            return shares, "順位④（祖父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_grand]
        else:
            avg_assign(group_grand, 1.0)
            return shares, "順位④（祖父母）", [persons.get(x, {}).get("name", x) for x in group_grand]

    # 都沒有 → 只有配偶或無繼承人
    if spouse:
        return {spouse: 1.0}, "僅配偶", [persons.get(spouse, {}).get("name", spouse)]
    return {}, "無繼承人（資料不足）", []

# =============== 分頁 ===============
tab_tree, tab_inherit, tab_data = st.tabs(["🧭 家族樹", "⚖️ 法定繼承試算", "🗂️ 資料"])

# ---------- 家族樹 ----------
with tab_tree:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    if not persons:
        st.info("請先到「資料」分頁載入或匯入 JSON。")
    else:
        root_id = st.selectbox(
            "請選擇家族樹的根人物（第1層）",
            options=list(persons.keys()),
            format_func=lambda x: persons[x]["name"],
            index=(list(persons.keys()).index("c_yilang") if "c_yilang" in persons else 0),
        )
        st.caption("第1層：根人物＋配偶/前任；第2層：其子女；第3層：孫輩。離婚為虛線、婚姻為實線。")
        dot = build_graph(data, root_id)
        st.graphviz_chart(dot.source, use_container_width=True)

# ---------- 法定繼承（嚴格順位） ----------
with tab_inherit:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    if not persons:
        st.info("請先到「資料」分頁載入或匯入 JSON。")
    else:
        st.markdown('<div class="pill">台灣民法．法定繼承（嚴格順位制）</div>', unsafe_allow_html=True)
        decedent = st.selectbox(
            "被繼承人（過世者）",
            options=list(persons.keys()),
            format_func=lambda x: persons[x]["name"],
        )

        shares, note, heirs_used = intestate_shares_tw(data, decedent)

        st.markdown("#### 結果")
        if not shares:
            st.warning("無繼承人（或資料不足）。")
        else:
            # 卡片式呈現
            cols = st.columns(min(3, len(shares)))
            i = 0
            for pid, ratio in shares.items():
                with cols[i % len(cols)]:
                    st.markdown(
                        f"""
                        <div class="card">
                          <div class="subtle">繼承人</div>
                          <div style="font-size:20px;font-weight:700;color:{ACCENT}">{persons.get(pid, {}).get('name', pid)}</div>
                          <div style="font-size:32px;font-weight:800;color:{PRIMARY};margin-top:4px;">{ratio:.2%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                i += 1

            st.markdown(
                f'<div class="subtle">採用：{note}。依《民法》第1138條先定順位，並依第1144條計算比例；配偶為當然繼承人。</div>',
                unsafe_allow_html=True,
            )

# ---------- 資料（示範／匯入／匯出） ----------
with tab_data:
    st.markdown("### 📦 資料維護")
    c1, c2 = st.columns([1, 2])

    with c1:
        if st.button("🧪 一鍵載入示範：陳一郎家庭", use_container_width=True):
            st.session_state["data"] = json.loads(json.dumps(DEMO))
            st.success("已載入示範資料")
    with c2:
        uploaded = st.file_uploader("匯入 JSON（符合本平台格式）", type=["json"])
        if uploaded:
            try:
                data = json.load(uploaded)
                assert isinstance(data.get("persons"), dict)
                assert isinstance(data.get("marriages"), list)
                assert isinstance(data.get("children"), list)
                st.session_state["data"] = data
                st.success("✅ 匯入成功")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

    st.write("")
    st.markdown("#### ⬇️ 匯出資料")
    buf = io.BytesIO()
    buf.write(json.dumps(st.session_state["data"], ensure_ascii=False, indent=2).encode("utf-8"))
    st.download_button(
        "下載 family.json",
        data=buf.getvalue(),
        file_name="family.json",
        mime="application/json",
        use_container_width=True,
    )

    st.write("")
    st.markdown("#### 📘 JSON 結構（簡要）")
    st.code(
        """
{
  "persons": { "id": {"name": "姓名"}, ... },
  "marriages": [
    {"id":"m1","a":"人ID","b":"人ID","status":"current|ex"},
    ...
  ],
  "children": [
    {"marriage_id":"m1","children":["kid1","kid2"]},
    ...
  ]
}
        """,
        language="json",
    )

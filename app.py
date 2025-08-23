# app.py
# ==========================================================
# 家族平台（Graphviz 家族樹 + 台灣民法法定繼承試算）
# - 前任在左、本人置中、現任在右（水平順序鎖定）
# - 三代分層（根人物第1層；子女第2層；孫輩第3層）
# - 離婚虛線、在婚實線；直角線更清楚
# - 新增【法定繼承試算】（台灣民法：配偶 + 1~4順位）
# -「資料」分頁：一鍵載入示範、匯入/匯出 JSON
#
# 需求套件（requirements.txt）
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
st.markdown('<div class="subtle">前任在左、本人置中、現任在右；三代分層；台灣民法法定繼承快速試算</div>', unsafe_allow_html=True)
st.write("")

# =============== 預設樣式 ===============
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
        {"marriage_id": "m_current", "children": ["chen_da", "chen_er", "chen_san"]},
        {"marriage_id": "m_ex", "children": ["wang_zi"]},
        {"marriage_id": "m_wang", "children": ["wang_sun"]},
    ],
}

if "data" not in st.session_state:
    st.session_state["data"] = DEMO

# =============== 共用工具 ===============
def partner_of(m: Dict, pid: str) -> str:
    return m["b"] if m["a"] == pid else m["a"]

def map_children(children_list: List[Dict]) -> Dict[str, List[str]]:
    """marriage_id -> children ids"""
    return {c["marriage_id"]: list(c.get("children", [])) for c in children_list}

def marriages_of(pid: str, marriages: List[Dict]) -> List[Dict]:
    return [m for m in marriages if m["a"] == pid or m["b"] == pid]

def current_spouses_of(pid: str, marriages: List[Dict]) -> List[str]:
    return [partner_of(m, pid) for m in marriages if (m["a"] == pid or m["b"] == pid) and m.get("status") == "current"]

def ex_spouses_of(pid: str, marriages: List[Dict]) -> List[str]:
    return [partner_of(m, pid) for m in marriages if (m["a"] == pid or m["b"] == pid) and m.get("status") == "ex"]

def children_of(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    kids: List[str] = []
    for m in marriages:
        if m["a"] == pid or m["b"] == pid:
            kids += ch_map.get(m["id"], [])
    # 去重 & 保持順序
    seen = set()
    ordered = []
    for k in kids:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered

# =============== 繪圖 ===============
def build_graph(data: dict, root_id: str) -> Digraph:
    dot = Digraph(comment="Family Tree", engine="dot", format="svg")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.7")
    dot.node_attr.update(NODE_STYLE)
    dot.edge_attr.update(EDGE_STYLE)

    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    # 人節點
    for pid, info in persons.items():
        dot.node(pid, info.get("name", pid))

    # 婚姻 junction + 父母邊
    for m in marriages:
        mid = m["id"]
        a, b = m["a"], m["b"]
        dotted = (m.get("status") == "ex")
        dot.node(mid, "", shape="point", width="0.02", color=PRIMARY)
        style = "dashed" if dotted else "solid"
        dot.edge(a, mid, dir="none", style=style)
        dot.edge(b, mid, dir="none", style=style)
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

    # 子女（同層，左→右順序保持）
    for mid, kids in ch_map.items():
        if not kids:
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for cid in kids:
                s.node(cid)
        for i in range(len(kids)-1):
            dot.edge(kids[i], kids[i+1], style="invis", weight="200")
        for cid in kids:
            dot.edge(mid, cid)

    # 釘住「前任→本人→現任」水平順序
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

    # 三代分層：root(含配偶/前任)=第一層、其子女第二層、孫第三層
    gen0 = {root_id} | set(current_spouses_of(root_id, marriages)) | set(ex_spouses_of(root_id, marriages))
    gen1 = set(children_of(root_id, marriages_of(root_id, marriages), ch_map))
    gen2 = set()
    for kid in list(gen1):
        gen2 |= set(children_of(kid, marriages_of(kid, marriages), ch_map))

    if gen0:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for p in gen0: s.node(p)
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

# =============== 法定繼承（台灣民法） ===============
def taiwan_intestate_shares(
    data: dict, decedent: str, include: Set[str]
) -> Tuple[Dict[str, float], str, List[str]]:
    """
    依台灣民法（簡化版）計算法定繼承比例。
    - 順位：①直系卑親屬②父母③兄弟姊妹④祖父母
    - 配偶為當然繼承人：
       * 與直系卑親屬並存：配偶與子女『均分』（配偶視同一個子）
       * 與父母並存：配偶 1/2，父母 1/2（父母均分）
       * 與兄弟姊妹並存：配偶 1/2，兄弟姊妹 1/2（均分）
       * 其他：只有配偶 → 全部配偶
    - 代位繼承：僅直系卑親屬（此版未做「已故標註」邏輯，預設皆存活）
    - include：可由 UI 勾選要納入的候選人（快速排除）
    回傳：({繼承人: 比例}, 說明文字, 實際採用的順位名單)
    """
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    # 取得配偶（現任）
    spouses = set(current_spouses_of(decedent, marriages)) & include
    spouse = list(spouses)[0] if spouses else None

    # 直系卑親屬（子女）
    children_ids = set(children_of(decedent, marriages_of(decedent, marriages), ch_map)) & include

    # 父母（此資料模型未直接儲存父母，需由 child->parents 反推；
    # 為避免過度推論，此處讓使用者 UI 勾選候選人來限定 include 名單。）
    # 簡化策略：若有子女 → 取順位①；否則嘗試②父母（由 include 決定）；
    # 否則③兄弟姊妹；否則④祖父母；否則僅配偶
    order_used = []
    heirs: List[str] = []
    shares: Dict[str, float] = {}

    if children_ids:
        # 順位①：子女
        order_used = ["直系卑親屬（子女）", "配偶"]
        if spouse:
            heirs = [spouse] + sorted(children_ids)
            n = len(heirs)
            for h in heirs:
                shares[h] = 1 / n
        else:
            heirs = sorted(children_ids)
            n = len(heirs)
            for h in heirs:
                shares[h] = 1 / n
        return shares, "順位①（子女）", heirs

    # 沒子女 → 嘗試父母
    # 父母、兄弟姊妹、祖父母的辨識需外部協助，此處以 include 補強手動勾選
    # 我們用關鍵字協助（名稱含「父」「母」「爸」「媽」等），若無，視為使用者手動勾選
    def pick_by_keywords(cands: Set[str], keywords: List[str]) -> Set[str]:
        out = set()
        for cid in cands:
            name = persons.get(cid, {}).get("name", "")
            if any(k in name for k in keywords):
                out.add(cid)
        return out

    # 候選清單（剔除自己 & 子女）
    remain = set(include) - {decedent} - set(children_ids)
    parent_like = pick_by_keywords(remain, ["父", "母", "爸", "媽", "親"])
    sibling_like = pick_by_keywords(remain, ["兄", "弟", "姐", "妹"])
    grandparent_like = pick_by_keywords(remain, ["祖父", "祖母", "阿公", "阿嬤", "祖"])

    # 若關鍵字沒抓到，就把剩下的人交由使用者勾選後的 include 做順位嘗試（簡化）
    def if_empty_use_remain(group: Set[str]) -> Set[str]:
        return group if group else remain

    # 順位② 父母
    p2 = if_empty_use_remain(parent_like)
    if p2:
        p2 = p2 & remain
        if p2:
            order_used = ["直系尊親屬（父母）", "配偶"]
            if spouse:
                half = 0.5
                shares[spouse] = half
                rest = list(sorted(p2))
                for h in rest:
                    shares[h] = (1 - half) / len(rest)
                heirs = [spouse] + rest
            else:
                rest = list(sorted(p2))
                for h in rest:
                    shares[h] = 1 / len(rest)
                heirs = rest
            return shares, "順位②（父母）", heirs

    # 順位③ 兄弟姊妹
    p3 = if_empty_use_remain(sibling_like)
    if p3:
        p3 = p3 & remain
        if p3:
            order_used = ["兄弟姊妹", "配偶"]
            if spouse:
                half = 0.5
                shares[spouse] = half
                rest = list(sorted(p3))
                for h in rest:
                    shares[h] = (1 - half) / len(rest)
                heirs = [spouse] + rest
            else:
                rest = list(sorted(p3))
                for h in rest:
                    shares[h] = 1 / len(rest)
                heirs = rest
            return shares, "順位③（兄弟姊妹）", heirs

    # 順位④ 祖父母
    p4 = if_empty_use_remain(grandparent_like)
    if p4:
        p4 = p4 & remain
        if p4:
            order_used = ["祖父母", "配偶"]
            if spouse:
                half = 0.5
                shares[spouse] = half
                rest = list(sorted(p4))
                for h in rest:
                    shares[h] = (1 - half) / len(rest)
                heirs = [spouse] + rest
            else:
                rest = list(sorted(p4))
                for h in rest:
                    shares[h] = 1 / len(rest)
                heirs = rest
            return shares, "順位④（祖父母）", heirs

    # 都沒有 → 只有配偶 or 無繼承人（此版回傳空）
    if spouse:
        return {spouse: 1.0}, "僅配偶", [spouse]
    return {}, "無繼承人（資料不足或未勾選）", []

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

# ---------- 法定繼承 ----------
with tab_inherit:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])

    if not persons:
        st.info("請先到「資料」分頁載入或匯入 JSON。")
    else:
        st.markdown('<div class="pill">台灣民法．法定繼承（簡化版）</div>', unsafe_allow_html=True)
        decedent = st.selectbox(
            "被繼承人（過世者）",
            options=list(persons.keys()),
            format_func=lambda x: persons[x]["name"],
        )

        # 讓使用者從所有人勾選「候選繼承人」（協助父母/兄弟姐妹/祖父母判定）
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**候選繼承人**（請勾選實際可能繼承的人；子女與配偶系統會自動辨識）")
        all_people = {pid: persons[pid]["name"] for pid in persons if pid != decedent}
        default_checked = list(all_people.keys())
        picks = st.multiselect(
            "勾選候選人",
            options=list(all_people.keys()),
            default=default_checked,
            format_func=lambda x: all_people[x],
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        shares, note, heirs_used = taiwan_intestate_shares(data, decedent, set(picks))

        # 結果呈現
        st.markdown("#### 結果")
        if not shares:
            st.warning("無繼承人（或資料不足）。")
        else:
            total = sum(shares.values())
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
                f'<div class="subtle">採用：{note}；共 {len(heirs_used)} 位繼承人（配偶若存在，以民法與其並列計算）。</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="subtle">提示：本計算為「簡化版」且假設所有繼承人均存活；直系卑親屬才有代位繼承。若需更精確（排除已故、代位份內分配、特留分/特種繼承等），我可以為你擴充。</div>',
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
    st.markdown("#### 📘 JSON 結構說明（簡要）")
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

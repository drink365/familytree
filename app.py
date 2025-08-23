# app.py
# ==========================================================
# 家族平台（Graphviz 家族樹 + 台灣民法法定繼承試算 + 表單式資料輸入）
# - 家族樹：前任在左、本人置中、現任在右；三代分層；在婚實線、離婚虛線
# - 繼承試算：配偶為當然繼承人，只與「第一個有人的順位」共同繼承
# - 資料分頁：一鍵示範、表單新增人物／婚姻／親子、匯入、匯出
#
# requirements.txt 建議：
#   streamlit==1.37.0
#   graphviz==0.20.3
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
        margin-bottom:12px;
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
def normalize_name(s: str) -> str:
    return (s or "").strip()

def ensure_person_id(data: dict, display_name: str) -> str:
    """依姓名尋找既有人物；沒有就新建 ID 並回傳。"""
    display_name = normalize_name(display_name)
    if not display_name:
        raise ValueError("姓名不可空白")
    persons = data.setdefault("persons", {})
    for pid, info in persons.items():
        if info.get("name") == display_name:
            return pid
    # 建新 ID
    base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in display_name)
    pid = base
    i = 1
    while pid in persons:
        i += 1
        pid = f"{base}_{i}"
    persons[pid] = {"name": display_name}
    return pid

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
    parents: List[str] = []
    for m in marriages:
        if pid in ch_map.get(m["id"], []):
            for p in [m["a"], m["b"]]:
                if p not in parents:
                    parents.append(p)
    return parents

def siblings_of_person(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    sibs = set()
    # 全血
    for m in marriages:
        kids = ch_map.get(m["id"], [])
        if pid in kids:
            for k in kids:
                if k != pid:
                    sibs.add(k)
    # 半血
    my_parents = parents_of_person(pid, marriages, ch_map)
    for par in my_parents:
        for m in marriages_of(par, marriages):
            kids = ch_map.get(m["id"], [])
            for k in kids:
                if k != pid:
                    sibs.add(k)
    return list(sorted(sibs))

def grandparents_of_person(pid: str, marriages: List[Dict], ch_map: Dict[str, List[str]]) -> List[str]:
    gps = set()
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
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    spouse_list = current_spouses_of(decedent, marriages)  # 現任（此版假設最多一位）
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

    def avg_assign(ids: List[str], portion: float):
        if not ids: return
        each = portion / len(ids)
        for i in ids:
            shares[i] = shares.get(i, 0) + each

    if group_children:
        base = group_children + ([spouse] if spouse else [])
        avg_assign(base, 1.0)  # 與①並存：全部平均（配偶視同一子）
        return shares, "順位①（直系卑親屬）", [persons.get(x, {}).get("name", x) for x in base]

    if group_parents:
        if spouse:
            shares[spouse] = 0.5
            avg_assign(group_parents, 0.5)
            return shares, "順位②（父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_parents]
        else:
            avg_assign(group_parents, 1.0)
            return shares, "順位②（父母）", [persons.get(x, {}).get("name", x) for x in group_parents]

    if group_sibs:
        if spouse:
            shares[spouse] = 0.5
            avg_assign(group_sibs, 0.5)
            return shares, "順位③（兄弟姊妹）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_sibs]
        else:
            avg_assign(group_sibs, 1.0)
            return shares, "順位③（兄弟姊妹）", [persons.get(x, {}).get("name", x) for x in group_sibs]

    if group_grand:
        if spouse:
            shares[spouse] = 2/3
            avg_assign(group_grand, 1/3)
            return shares, "順位④（祖父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_grand]
        else:
            avg_assign(group_grand, 1.0)
            return shares, "順位④（祖父母）", [persons.get(x, {}).get("name", x) for x in group_grand]

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

# ---------- 法定繼承 ----------
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

# ---------- 資料（示範／表單輸入／匯入／匯出） ----------
with tab_data:
    st.markdown("### 📦 資料維護")
    data = st.session_state["data"]
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("🧪 一鍵載入示範：陳一郎家庭", use_container_width=True):
            st.session_state["data"] = json.loads(json.dumps(DEMO))
            st.success("已載入示範資料")

    # ---- 表單：新增人物 ----
    st.markdown("#### 👤 新增人物")
    with st.form("form_add_person", clear_on_submit=True):
        nm = st.text_input("姓名 *")
        submitted = st.form_submit_button("新增人物")
        if submitted:
            try:
                pid = ensure_person_id(data, nm)
                st.success(f"已新增/存在：{nm}（ID: {pid}）")
            except Exception as e:
                st.error(f"失敗：{e}")

    # ---- 表單：新增／更新婚姻 ----
    st.markdown("#### 💍 新增／更新婚姻")
    all_names = [info["name"] for info in persons.values()]
    with st.form("form_add_marriage", clear_on_submit=True):
        a_name = st.text_input("配偶 A（姓名） *")
        b_name = st.text_input("配偶 B（姓名） *")
        status = st.selectbox("關係狀態", ["current", "ex"])
        submitted = st.form_submit_button("建立／更新 婚姻")
        if submitted:
            try:
                a_id = ensure_person_id(data, a_name)
                b_id = ensure_person_id(data, b_name)
                if a_id == b_id:
                    st.error("同一人不能和自己結婚")
                else:
                    # 找是否已有 a-b 婚姻；沒有就建新
                    mid = None
                    for m in marriages:
                        if {m["a"], m["b"]} == {a_id, b_id}:
                            mid = m["id"]; break
                    if not mid:
                        base = f"m_{min(a_id,b_id)}_{max(a_id,b_id)}"
                        mid = base
                        i = 1
                        existing = {m["id"] for m in marriages}
                        while mid in existing:
                            i += 1; mid = f"{base}_{i}"
                        marriages.append({"id": mid, "a": a_id, "b": b_id, "status": status})
                        st.success(f"已建立婚姻：{data['persons'][a_id]['name']} × {data['persons'][b_id]['name']}（{status}）")
                    else:
                        for m in marriages:
                            if m["id"] == mid:
                                m["status"] = status
                                st.success(f"已更新婚姻狀態：{data['persons'][a_id]['name']} × {data['persons'][b_id]['name']} → {status}")
                                break
            except Exception as e:
                st.error(f"失敗：{e}")

    # ---- 表單：新增親子（把孩子掛到某段婚姻） ----
    st.markdown("#### 👶 新增親子（掛到某段婚姻）")
    # 以現有婚姻建立下拉
    marriage_options = {m["id"]: f"{data['persons'].get(m['a'],{}).get('name','?')} × {data['persons'].get(m['b'],{}).get('name','?')}（{m.get('status','')}）" for m in marriages}
    with st.form("form_add_child", clear_on_submit=True):
        mid_pick = st.selectbox("選擇父母（婚姻）", options=list(marriage_options.keys()), format_func=lambda x: marriage_options[x])
        child_name = st.text_input("子女姓名 *")
        submitted = st.form_submit_button("新增子女到此婚姻")
        if submitted:
            try:
                cid = ensure_person_id(data, child_name)
                # children 結構是婚姻id -> list
                found = False
                for c in children:
                    if c["marriage_id"] == mid_pick:
                        if cid not in c["children"]:
                            c["children"].append(cid)
                        found = True
                        break
                if not found:
                    children.append({"marriage_id": mid_pick, "children": [cid]})
                st.success(f"已加入：{data['persons'][cid]['name']} → {marriage_options[mid_pick]}")
            except Exception as e:
                st.error(f"失敗：{e}")

    st.markdown("---")

    # ---- 匯入／匯出 ----
    st.markdown("#### ⬇️ 匯出資料")
    buf = io.BytesIO()
    buf.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    st.download_button(
        "下載 family.json",
        data=buf.getvalue(),
        file_name="family.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("#### ⬆️ 匯入資料（JSON）")
    uploaded = st.file_uploader("匯入 JSON（符合本平台格式）", type=["json"])
    if uploaded:
        try:
            newdata = json.load(uploaded)
            assert isinstance(newdata.get("persons"), dict)
            assert isinstance(newdata.get("marriages"), list)
            assert isinstance(newdata.get("children"), list)
            st.session_state["data"] = newdata
            st.success("✅ 匯入成功")
        except Exception as e:
            st.error(f"匯入失敗：{e}")

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

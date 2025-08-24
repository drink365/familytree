# app.py
# ==========================================================
# 家族平台（Graphviz 家族樹 + 台灣民法法定繼承試算 + 表單輸入）
# - 前任在左、本人置中、現任在右；三代分層；在婚實線、離婚虛線
# - 人物：性別＋已過世（顏色：男淡藍、女淡紅、已殁灰＋「（殁）」）
# - 法定繼承：配偶當然繼承人，只與「第一個有人的順位」共同繼承
# - 資料：表單新增/修改、匯入/匯出
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

st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🌳 家族平台（家族樹＋法定繼承）</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">前任在左、本人置中、現任在右；三代分層；台灣民法法定繼承（嚴格順位制）</div>', unsafe_allow_html=True)
st.write("")

# =============== 顏色規則 ===============
COLOR_MALE = "#D2E9FF"     # 男淡藍
COLOR_FEMALE = "#FFD2D2"   # 女淡紅
COLOR_DECEASED = "#D9D9D9" # 已殁灰

# =============== 一鍵示範資料 ===============
DEMO = {
    "persons": {
        "c_yilang": {"name": "陳一郎", "gender": "男", "deceased": False},
        "c_wife": {"name": "陳妻", "gender": "女", "deceased": False},
        "c_exwife": {"name": "陳前妻", "gender": "女", "deceased": False},
        "wang_zi": {"name": "王子", "gender": "男", "deceased": False},
        "wang_zi_wife": {"name": "王子妻", "gender": "女", "deceased": False},
        "wang_sun": {"name": "王孫", "gender": "男", "deceased": False},
        "chen_da": {"name": "陳大", "gender": "男", "deceased": False},
        "chen_er": {"name": "陳二", "gender": "男", "deceased": False},
        "chen_san": {"name": "陳三", "gender": "男", "deceased": False},
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

# 初始資料
if "data" not in st.session_state:
    st.session_state["data"] = DEMO

# =============== 共用工具 ===============
def normalize(s: str) -> str:
    return (s or "").strip()

def ensure_person_id(data: dict, name: str, gender: str = "男", deceased: bool = False) -> str:
    """依姓名尋找人物；沒有就新建 ID（同時可更新性別與生死狀態）。"""
    name = normalize(name)
    if not name:
        raise ValueError("姓名不可空白")
    persons = data.setdefault("persons", {})
    for pid, info in persons.items():
        if info.get("name") == name:
            # 更新欄位
            info["gender"] = gender or info.get("gender") or "男"
            info["deceased"] = bool(deceased)
            return pid
    base = "p_" + "".join(ch if ch.isalnum() else "_" for ch in name)
    pid = base; i = 1
    while pid in persons:
        i += 1; pid = f"{base}_{i}"
    persons[pid] = {"name": name, "gender": gender, "deceased": bool(deceased)}
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
    for par in parents_of_person(pid, marriages, ch_map):
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

def node_color(info: dict) -> str:
    if info.get("deceased"):
        return COLOR_DECEASED
    return COLOR_MALE if info.get("gender") == "男" else COLOR_FEMALE

def node_label(info: dict) -> str:
    return f"{info.get('name','')}（殁）" if info.get("deceased") else info.get("name","")

# =============== 自動選根（刪除使用者選單） ===============
def pick_root(data: dict) -> str:
    """選關係『最多』的人當根（婚姻數＋子女數＋父母數），若平手取字典序最小 id。"""
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    if not persons:
        return ""

    score: Dict[str, int] = {pid: 0 for pid in persons}
    for m in marriages:
        score[m["a"]] += 1
        score[m["b"]] += 1
        for kid in ch_map.get(m["id"], []):
            score[kid] += 0  # 子女分數另外算

    # 子女
    for mid, kids in ch_map.items():
        for k in kids:
            score[k] += 1
        # 父母加分：m.a/m.b
        #（已在婚姻處加分，不重複）

    # 父母（作為子）
    for pid in persons:
        for m in marriages:
            if pid in ch_map.get(m["id"], []):
                score[m["a"]] += 0
                score[m["b"]] += 0

    # 再把有「現任配偶」的人稍微加權，通常為當代核心
    for pid in persons:
        if current_spouses_of(pid, marriages):
            score[pid] += 2

    # 取最高分
    best = sorted(score.items(), key=lambda x: (-x[1], x[0]))[0][0]
    return best

# =============== 家族樹繪製（前任左/現任右/本人中；三代分層） ===============
def build_graph(data: dict, root_id: str) -> Digraph:
    dot = Digraph(comment="Family Tree", engine="dot", format="svg")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.7")
    dot.edge_attr.update({"color": PRIMARY})

    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    # 節點
    for pid, info in persons.items():
        dot.node(pid, node_label(info), shape="box", style="filled", fillcolor=node_color(info), color=ACCENT, penwidth="1.2", fontcolor="black" if info.get("deceased") else "black")

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

    # 子女：同層；左→右不可見固定
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

    # 三代分層（根第1層、其子女第2層、孫輩第3層；並把根的婚姻junction壓回第一層）
    gen0 = {root_id} | set(current_spouses_of(root_id, marriages)) | set(ex_spouses_of(root_id, marriages))
    gen1 = set(children_of_via_marriage(root_id, marriages_of(root_id, marriages), ch_map))
    gen2 = set()
    for kid in list(gen1):
        gen2 |= set(children_of_via_marriage(kid, marriages_of(kid, marriages), ch_map))

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

# =============== 法定繼承（嚴格順位制） ===============
def intestate_shares_tw(data: dict, decedent: str) -> Tuple[Dict[str, float], str, List[str]]:
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    spouse_list = current_spouses_of(decedent, marriages)
    spouse = spouse_list[0] if spouse_list else None

    group_children = children_of_via_marriage(decedent, marriages_of(decedent, marriages), ch_map)
    group_parents  = parents_of_person(decedent, marriages, ch_map)
    group_sibs     = siblings_of_person(decedent, marriages, ch_map)
    group_grand    = grandparents_of_person(decedent, marriages, ch_map)

    shares: Dict[str, float] = {}
    def avg(ids: List[str], portion: float):
        if not ids: return
        each = portion / len(ids)
        for i in ids:
            shares[i] = shares.get(i, 0) + each

    # ① 子女
    if group_children:
        base = group_children + ([spouse] if spouse else [])
        avg(base, 1.0)  # 配偶視同一子，均分
        return shares, "順位①（直系卑親屬）", [persons.get(x, {}).get("name", x) for x in base]
    # ② 父母
    if group_parents:
        if spouse:
            shares[spouse] = 0.5; avg(group_parents, 0.5)
            return shares, "順位②（父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_parents]
        else:
            avg(group_parents, 1.0)
            return shares, "順位②（父母）", [persons.get(x, {}).get("name", x) for x in group_parents]
    # ③ 兄弟姊妹
    if group_sibs:
        if spouse:
            shares[spouse] = 0.5; avg(group_sibs, 0.5)
            return shares, "順位③（兄弟姊妹）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_sibs]
        else:
            avg(group_sibs, 1.0)
            return shares, "順位③（兄弟姊妹）", [persons.get(x, {}).get("name", x) for x in group_sibs]
    # ④ 祖父母
    if group_grand:
        if spouse:
            shares[spouse] = 2/3; avg(group_grand, 1/3)
            return shares, "順位④（祖父母）", [persons.get(spouse, {}).get("name", spouse)] + [persons.get(x, {}).get("name", x) for x in group_grand]
        else:
            avg(group_grand, 1.0)
            return shares, "順位④（祖父母）", [persons.get(x, {}).get("name", x) for x in group_grand]

    if spouse:
        return {spouse: 1.0}, "僅配偶", [persons.get(spouse, {}).get("name", spouse)]
    return {}, "無繼承人（資料不足）", []

# =============== 分頁 ===============
tab_tree, tab_inherit, tab_data = st.tabs(["🧭 家族樹", "⚖️ 法定繼承試算", "🗂️ 資料"])

# ---------- 家族樹（自動選根） ----------
with tab_tree:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    if not persons:
        st.info("請先到『資料』分頁新增或匯入 JSON。")
    else:
        root_id = pick_root(data)
        root_name = data["persons"][root_id]["name"]
        st.caption(f"本圖自動以「{root_name}」為中心（關係最多），顯示其三代分層。")
        dot = build_graph(data, root_id)
        st.graphviz_chart(dot.source, use_container_width=True)

# ---------- 法定繼承 ----------
with tab_inherit:
    data = st.session_state["data"]
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    if not persons:
        st.info("請先到『資料』分頁新增或匯入 JSON。")
    else:
        # 以自動根為預設被繼承人，亦可改選
        default_pid = pick_root(data)
        decedent = st.selectbox(
            "被繼承人（可改選）",
            options=list(persons.keys()),
            index=list(persons.keys()).index(default_pid) if default_pid in persons else 0,
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
                info = persons.get(pid, {})
                color = node_color(info)
                name = node_label(info)
                with cols[i % len(cols)]:
                    st.markdown(
                        f"""
                        <div class="card" style="background:{color}33">
                          <div class="subtle">繼承人</div>
                          <div style="font-size:20px;font-weight:700;color:{ACCENT}">{name}</div>
                          <div style="font-size:32px;font-weight:800;color:{PRIMARY};margin-top:4px;">{ratio:.2%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                i += 1
            st.markdown(f'<div class="subtle">採用：{note}（配偶為當然繼承人；僅與第一個有人的順位共同繼承）。</div>', unsafe_allow_html=True)

# ---------- 資料（表單輸入／匯入／匯出） ----------
with tab_data:
    st.markdown("### 📦 資料維護")

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("🧪 一鍵載入示範：陳一郎家庭", use_container_width=True):
            st.session_state["data"] = json.loads(json.dumps(DEMO))
            st.success("已載入示範資料")

    data = st.session_state["data"]
    persons = data.get("persons", {})
    marriages = data.get("marriages", [])
    children = data.get("children", [])
    ch_map = map_children(children)

    # ---- 新增/更新 人物 ----
    st.markdown("#### 👤 新增／更新人物")
    with st.form("form_add_person", clear_on_submit=True):
        name = st.text_input("姓名 *")
        gender = st.selectbox("性別 *", ["男", "女"])
        deceased = st.checkbox("已過世（顯示灰底與「（殁）」）", value=False)
        s1 = st.form_submit_button("新增／更新人物")
        if s1:
            try:
                pid = ensure_person_id(data, name, gender, deceased)
                st.success(f"已新增／更新人物：{name}（ID: {pid}）")
            except Exception as e:
                st.error(f"失敗：{e}")

    # ---- 新增／更新 婚姻 ----
    st.markdown("#### 💍 新增／更新婚姻（現任/前任）")
    with st.form("form_add_marriage", clear_on_submit=True):
        a_name = st.text_input("配偶 A（姓名） *")
        b_name = st.text_input("配偶 B（姓名） *")
        status = st.selectbox("關係狀態", ["current", "ex"])
        s2 = st.form_submit_button("建立／更新 婚姻")
        if s2:
            try:
                a_id = ensure_person_id(data, a_name, "男")
                b_id = ensure_person_id(data, b_name, "女")
                if a_id == b_id:
                    st.error("同一人不能與自己結婚")
                else:
                    mid = None
                    for m in marriages:
                        if {m["a"], m["b"]} == {a_id, b_id}:
                            mid = m["id"]; break
                    if not mid:
                        base = f"m_{min(a_id,b_id)}_{max(a_id,b_id)}"
                        mid = base; i = 1
                        ids = {m["id"] for m in marriages}
                        while mid in ids:
                            i += 1; mid = f"{base}_{i}"
                        marriages.append({"id": mid, "a": a_id, "b": b_id, "status": status})
                        st.success(f"已建立婚姻：{data['persons'][a_id]['name']} × {data['persons'][b_id]['name']}（{status}）")
                    else:
                        for m in marriages:
                            if m["id"] == mid:
                                m["status"] = status
                                st.success(f"已更新婚姻：{data['persons'][a_id]['name']} × {data['persons'][b_id]['name']} → {status}")
                                break
            except Exception as e:
                st.error(f"失敗：{e}")

    # ---- 新增 子女（掛到某段婚姻）----
    st.markdown("#### 👶 新增子女到婚姻")
    marriage_options = {m["id"]: f"{data['persons'].get(m['a'],{}).get('name','?')} × {data['persons'].get(m['b'],{}).get('name','?')}（{m.get('status','')}）" for m in marriages}
    with st.form("form_add_child", clear_on_submit=True):
        if marriage_options:
            mid_pick = st.selectbox("選擇父母（婚姻）", options=list(marriage_options.keys()), format_func=lambda x: marriage_options[x])
            child_name = st.text_input("子女姓名 *")
            child_gender = st.selectbox("子女性別 *", ["男", "女"])
            child_deceased = st.checkbox("子女已過世", value=False)
            s3 = st.form_submit_button("加入子女到此婚姻")
            if s3:
                try:
                    cid = ensure_person_id(data, child_name, child_gender, child_deceased)
                    found = False
                    for c in children:
                        if c["marriage_id"] == mid_pick:
                            if cid not in c["children"]:
                                c["children"].append(cid)
                            found = True; break
                    if not found:
                        children.append({"marriage_id": mid_pick, "children": [cid]})
                    st.success(f"已加入：{data['persons'][cid]['name']} → {marriage_options[mid_pick]}")
                except Exception as e:
                    st.error(f"失敗：{e}")
        else:
            st.info("尚無婚姻資料，請先建立婚姻。")

    st.markdown("---")

    # ---- 匯出／匯入 ----
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
  "persons": { "id": {"name": "姓名", "gender":"男|女", "deceased": false}, ... },
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

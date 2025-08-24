# app.py
import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

st.set_page_config(page_title="家族平台（人物｜關係｜法定繼承｜家族樹）", layout="wide")

# -----------------------------
# 顏色與樣式
# -----------------------------
MALE_COLOR    = "#d9ecff"  # 淡藍
FEMALE_COLOR  = "#ffe0e6"  # 淡紅
DECEASED_COLOR= "#e6e6e6"  # 灰
NODE_BORDER   = "#16465f"
LINE_COLOR    = "#1f4b63"

def node_style_by_person(p):
    if p.get("deceased"):
        return {
            "shape": "box",
            "style": "filled",
            "fillcolor": DECEASED_COLOR,
            "color": NODE_BORDER,
            "fontcolor": "#333333",
            "penwidth": "1.2",
        }
    if p.get("gender") == "女":
        return {
            "shape": "box",
            "style": "filled",
            "fillcolor": FEMALE_COLOR,
            "color": NODE_BORDER,
            "fontcolor": "#0e2531",
            "penwidth": "1.2",
        }
    # 預設男
    return {
        "shape": "box",
        "style": "filled",
        "fillcolor": MALE_COLOR,
        "color": NODE_BORDER,
        "fontcolor": "#0e2531",
        "penwidth": "1.2",
    }

# -----------------------------
# 資料初始化
# -----------------------------
def init_data():
    return {
        "persons": {},     # pid -> {name, gender, deceased}
        "marriages": [],   # [{id, a, b, divorced}]
        "children": [],    # [{marriage_id, children:[pid,...]}]
        "_seq": 1          # id 產生器
    }

def next_id():
    st.session_state.data["_seq"] += 1
    return f"P{st.session_state.data['_seq']}"

def next_mid():
    st.session_state.data["_seq"] += 1
    return f"M{st.session_state.data['_seq']}"

def ensure_person_id(data, name, gender, deceased=False):
    # 以「同名+性別」視為同一人（簡化處理）
    for pid, p in data["persons"].items():
        if p["name"] == name and p.get("gender") == gender:
            # 更新過世狀態
            if deceased: p["deceased"] = True
            return pid
    pid = next_id()
    data["persons"][pid] = {"name": name, "gender": gender, "deceased": deceased}
    return pid

def load_demo():
    data = init_data()
    # 人
    yilang = ensure_person_id(data, "陳一郎", "男")
    exwife = ensure_person_id(data, "陳前妻", "女")
    wife   = ensure_person_id(data, "陳妻", "女")
    wangzi = ensure_person_id(data, "王子", "男")
    wz_wife= ensure_person_id(data, "王子妻", "女")
    wz_sun = ensure_person_id(data, "王孫", "男")
    a      = ensure_person_id(data, "陳大", "男")
    b      = ensure_person_id(data, "陳二", "男")
    c      = ensure_person_id(data, "陳三", "男")

    # 婚姻
    m_ex = {"id": next_mid(), "a": yilang, "b": exwife, "divorced": True}
    m_w  = {"id": next_mid(), "a": yilang, "b": wife,   "divorced": False}
    m_wz = {"id": next_mid(), "a": wangzi, "b": wz_wife, "divorced": False}
    data["marriages"] = [m_ex, m_w, m_wz]

    # 子女
    data["children"] = [
        {"marriage_id": m_ex["id"], "children": [wangzi]},
        {"marriage_id": m_w["id"],  "children": [a, b, c]},
        {"marriage_id": m_wz["id"], "children": [wz_sun]},
    ]
    return data

if "data" not in st.session_state:
    st.session_state.data = load_demo()

data = st.session_state.data

# -----------------------------
# 工具：反查父母、子女、兄弟姊妹、祖父母
# -----------------------------
def build_parent_map(data):
    # child -> set(parents)
    parents_of = defaultdict(set)
    marriage_of = {}
    for m in data["marriages"]:
        marriage_of[m["id"]] = (m["a"], m["b"])
    for ck in data["children"]:
        mid = ck["marriage_id"]
        if mid not in marriage_of:
            continue
        pa, pb = marriage_of[mid]
        for ch in ck["children"]:
            parents_of[ch].add(pa); parents_of[ch].add(pb)
    return parents_of, marriage_of

def children_of_person(data, pid):
    res = []
    for ck in data["children"]:
        if ck["marriage_id"] in {m["id"] for m in data["marriages"] if m["a"] == pid or m["b"] == pid}:
            res.extend(ck["children"])
    return list(dict.fromkeys(res))

def descendants_of(data, pid):
    parents_of, marriage_of = build_parent_map(data)
    # 建 child->children 查找
    kids_by_parent = defaultdict(list)
    for ck in data["children"]:
        pa, pb = marriage_of.get(ck["marriage_id"], (None, None))
        for ch in ck["children"]:
            if pa: kids_by_parent[pa].append(ch)
            if pb: kids_by_parent[pb].append(ch)
    res = []
    q = deque(kids_by_parent.get(pid, []))
    seen = set()
    while q:
        c = q.popleft()
        if c in seen: continue
        seen.add(c)
        res.append(c)
        for nxt in kids_by_parent.get(c, []):
            q.append(nxt)
    return res

def parents_of_person(data, pid):
    parents_of, _ = build_parent_map(data)
    return list(parents_of.get(pid, []))

def siblings_of(data, pid):
    # 共享任一父/母的都視為兄弟姐妹（同父同母或半血親），排除自己
    parents = set(parents_of_person(data, pid))
    if not parents: return []
    sib = set()
    for ck in data["children"]:
        for ch in ck["children"]:
            if ch == pid: continue
            if parents & set(parents_of_person(data, ch)):
                sib.add(ch)
    return list(sib)

def grandparents_of(data, pid):
    gps = set()
    for p in parents_of_person(data, pid):
        gps.update(parents_of_person(data, p))
    return list(gps)

# -----------------------------
# 法定繼承：配偶為當然繼承人 + 最前順位
# -----------------------------
def spouses_of(data, pid):
    sp = []
    for m in data["marriages"]:
        if m["a"] == pid:
            sp.append((m["b"], m["divorced"]))
        elif m["b"] == pid:
            sp.append((m["a"], m["divorced"]))
    return sp

def legal_heirs_ordered(data, decedent_id):
    """回傳『配偶放最前』+ 有哪一順位的人"""
    # 先抓配偶（包含已離婚者不列入繼承）
    spouse_alive = [sid for sid, divorced in spouses_of(data, decedent_id) if not divorced]

    # 第一順位：直系卑親屬（所有後代）
    des = [p for p in descendants_of(data, decedent_id) if not data["persons"][p].get("deceased")]
    if des:
        principal = des
        rank_name = "第一順位（直系卑親屬）"
    else:
        # 第二：父母
        pa = [p for p in parents_of_person(data, decedent_id) if not data["persons"][p].get("deceased")]
        if pa:
            principal = pa
            rank_name = "第二順位（父母）"
        else:
            # 第三：兄弟姐妹
            sib = [p for p in siblings_of(data, decedent_id) if not data["persons"][p].get("deceased")]
            if sib:
                principal = sib
                rank_name = "第三順位（兄弟姐妹）"
            else:
                # 第四：祖父母
                gp = [p for p in grandparents_of(data, decedent_id) if not data["persons"][p].get("deceased")]
                principal = gp
                rank_name = "第四順位（祖父母）"

    # 整理人名，配偶優先
    heirs = []
    for s in spouse_alive:
        heirs.append(s)
    for h in principal:
        if h not in heirs:
            heirs.append(h)
    return heirs, rank_name

# -----------------------------
# 家族樹：Graphviz（無區塊；同代同層；前任左/現任右；子女垂直）
# -----------------------------
def draw_tree(data: dict) -> Digraph:
    dot = Digraph(engine="dot", format="svg")
    dot.attr(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.8")
    dot.attr("graph", bgcolor="white")
    dot.attr("edge", color=LINE_COLOR, penwidth="1.2")

    # 父母地圖
    parents_of_map, marriage_of = build_parent_map(data)

    # 先建立所有人節點（帶顏色、(殁) 後綴）
    for pid, p in data["persons"].items():
        label = p["name"] + ("（殁）" if p.get("deceased") else "")
        style = node_style_by_person(p)
        dot.node(pid, label=label, **style)

    # 建婚姻節點 + 線
    for m in data["marriages"]:
        mid = m["id"]; a = m["a"]; b = m["b"]; divorced = m["divorced"]
        # 小圓點作為結合點
        dot.node(mid, "", shape="point", width="0.03", color=LINE_COLOR)
        # 婚姻線
        style = "dashed" if divorced else "solid"
        dot.edge(a, mid, dir="none", style=style)
        dot.edge(b, mid, dir="none", style=style)
        # 夫妻同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(a); s.node(b)

    # 子女從婚姻節點垂直往下
    for ck in data["children"]:
        mid = ck["marriage_id"]
        for ch in ck["children"]:
            dot.edge(mid, ch)

    # 排序：若某人同時有前任與現任 -> 無形邊：前任 -> 本人 -> 現任
    # 找某人所有婚姻，分成 ex/current
    marriages_by_person = defaultdict(list)
    for m in data["marriages"]:
        marriages_by_person[m["a"]].append(m)
        marriages_by_person[m["b"]].append(m)

    for person, m_list in marriages_by_person.items():
        exes = [m for m in m_list if m["divorced"]]
        curs = [m for m in m_list if not m["divorced"]]
        # 取對象pid
        def spouse_id(m, person):
            return m["b"] if m["a"] == person else m["a"]
        if exes or curs:
            with dot.subgraph() as s:
                s.attr(rank="same")
                # 先把前任們排左
                prev = None
                for m in exes:
                    ex_id = spouse_id(m, person)
                    s.node(ex_id)
                    if prev:
                        s.edge(prev, ex_id, style="invis", weight="100")
                    prev = ex_id
                # 中間是本人
                s.node(person)
                if prev:
                    s.edge(prev, person, style="invis", weight="100")
                    prev = person
                else:
                    prev = person
                # 右側現任
                for m in curs:
                    cur_id = spouse_id(m, person)
                    s.node(cur_id)
                    s.edge(prev, cur_id, style="invis", weight="100")
                    prev = cur_id

    return dot

# -----------------------------
# 介面：抬頭與導覽
# -----------------------------
st.title("🌳 家族平台（人物｜關係｜法定繼承｜家族樹）")
st.caption("本圖以「陳一郎家族」為示範。你可以按下右側的「馬上輸入自己的資料」，清空示範並開始建立你自己的家族。")

colA, colB = st.columns([1,1])
with colA:
    if st.button("📥 重新載入示範家族"):
        st.session_state.data = load_demo()
        st.success("已載入示範資料。")
with colB:
    if st.button("✏️ 馬上輸入自己的資料（清空示範）"):
        st.session_state.data = init_data()
        st.success("已清空，開始輸入你自己的家族資料吧！")

st.divider()

tab_people, tab_rel, tab_inherit, tab_tree = st.tabs(
    ["👤 人物", "🔗 關係（婚姻 / 子女）", "⚖️ 法定繼承試算", "🧭 家族樹"]
)

# -----------------------------
# 人物
# -----------------------------
with tab_people:
    st.subheader("新增人物")
    with st.form("form_person", clear_on_submit=True):
        name = st.text_input("姓名 *")
        gender = st.selectbox("性別 *", ["男", "女"])
        deceased = st.checkbox("此人已過世", value=False)
        ok = st.form_submit_button("新增 / 更新")
        if ok:
            if not name.strip():
                st.error("請輸入姓名")
            else:
                pid = ensure_person_id(st.session_state.data, name.strip(), gender, deceased)
                st.success(f"已新增 / 更新：{st.session_state.data['persons'][pid]['name']}")

    st.subheader("現有人物")
    if not st.session_state.data["persons"]:
        st.info("目前尚無人物，請在上方新增。")
    else:
        for pid, p in st.session_state.data["persons"].items():
            label = p["name"] + ("（殁）" if p.get("deceased") else "")
            st.write(f"- {label}｜性別：{p.get('gender','?')}")

# -----------------------------
# 關係（婚姻／子女）
# -----------------------------
with tab_rel:
    st.subheader("建立一段婚姻")
    with st.form("form_marriage", clear_on_submit=True):
        persons_opts = list(st.session_state.data["persons"].keys())
        def fmt(x): 
            p = st.session_state.data["persons"][x]
            return p["name"] + ("（殁）" if p.get("deceased") else "")
        if len(persons_opts) >= 2:
            p1 = st.selectbox("配偶 A *", persons_opts, format_func=fmt)
            p2 = st.selectbox("配偶 B *", [k for k in persons_opts if k != p1], format_func=fmt)
            divorced = st.checkbox("這段婚姻已離婚？（離婚會顯示虛線）", value=False)
            ok2 = st.form_submit_button("建立婚姻")
            if ok2:
                # 檢查是否已有同一對
                duplicated = False
                for m in st.session_state.data["marriages"]:
                    if {m["a"], m["b"]} == {p1, p2}:
                        duplicated = True; break
                if duplicated:
                    st.warning("這段婚姻已存在。")
                else:
                    st.session_state.data["marriages"].append(
                        {"id": next_mid(), "a": p1, "b": p2, "divorced": divorced}
                    )
                    st.success(f"已建立婚姻：{fmt(p1)} － {fmt(p2)}")
        else:
            st.info("請先在『人物』頁籤新增至少兩人。")
            st.form_submit_button("（無法建立）")

    # 子女
    st.subheader("把子女掛到父母（某段婚姻）")
    # 準備婚姻選單
    marriage_options = {}
    for m in st.session_state.data["marriages"]:
        a = st.session_state.data["persons"].get(m["a"], {"name": "?"})["name"]
        b = st.session_state.data["persons"].get(m["b"], {"name": "?"})["name"]
        tag = "（離婚）" if m["divorced"] else "（在婚）"
        marriage_options[m["id"]] = f"{a} － {b} {tag}"

    with st.form("form_child", clear_on_submit=True):
        if marriage_options:
            mid_pick = st.selectbox("選擇父母（婚姻）", options=list(marriage_options.keys()),
                                    format_func=lambda x: marriage_options[x])
            child_name = st.text_input("子女姓名 *")
            child_gender = st.selectbox("子女性別 *", ["男", "女"])
            child_deceased = st.checkbox("子女已過世", value=False)
            ok3 = st.form_submit_button("加入子女")
            if ok3:
                if not child_name.strip():
                    st.error("請輸入子女姓名")
                else:
                    cid = ensure_person_id(st.session_state.data, child_name.strip(), child_gender, child_deceased)
                    # 掛到 children 結構
                    found = False
                    for c in st.session_state.data["children"]:
                        if c["marriage_id"] == mid_pick:
                            if cid not in c["children"]:
                                c["children"].append(cid)
                            found = True; break
                    if not found:
                        st.session_state.data["children"].append({"marriage_id": mid_pick, "children":[cid]})
                    st.success(f"已加入：{st.session_state.data['persons'][cid]['name']} → {marriage_options[mid_pick]}")
        else:
            st.info("目前尚無婚姻，請先在上方建立一段婚姻。")
            st.form_submit_button("（無法加入子女）")

    st.subheader("已建立婚姻")
    if not st.session_state.data["marriages"]:
        st.info("尚無婚姻。")
    else:
        for m in st.session_state.data["marriages"]:
            a = st.session_state.data["persons"].get(m["a"], {"name": "?"})["name"]
            b = st.session_state.data["persons"].get(m["b"], {"name": "?"})["name"]
            st.write(f"- {a} － {b}｜{'離婚' if m['divorced'] else '在婚'}")

# -----------------------------
# 法定繼承試算
# -----------------------------
with tab_inherit:
    st.subheader("法定繼承試算（民法第 1138 條）")
    st.caption("配偶為當然繼承人，並與最前順位（直系卑親屬 / 父母 / 兄弟姐妹 / 祖父母）共同繼承。只要有前順位，就不會往後順位。")
    persons_opts = list(st.session_state.data["persons"].keys())
    if not persons_opts:
        st.info("請先在『人物』頁籤新增人物。")
    else:
        def fmt(x):
            p = st.session_state.data["persons"][x]
            return p["name"] + ("（殁）" if p.get("deceased") else "")
        decedent = st.selectbox("選擇被繼承人", persons_opts, format_func=fmt)
        heirs, rank_name = legal_heirs_ordered(st.session_state.data, decedent)
        st.write(f"**順位判定**：{rank_name}")
        if not heirs:
            st.warning("找不到任何繼承人（可能全數過世或血親資料不足）。")
        else:
            st.write("**繼承人（配偶最前）**：")
            cols = st.columns(min(4, len(heirs)))
            for i, pid in enumerate(heirs):
                p = st.session_state.data["persons"][pid]
                label = p["name"] + ("（殁）" if p.get("deceased") else "")
                cols[i % len(cols)].write(f"- {label}（{p.get('gender','?')}）")

# -----------------------------
# 家族樹
# -----------------------------
with tab_tree:
    st.subheader("家族樹（前任在左・本人置中・現任在右；同代同層；子女垂直）")
    if not st.session_state.data["persons"]:
        st.info("請先新增人物與關係。")
    else:
        dot = draw_tree(st.session_state.data)
        st.graphviz_chart(dot, use_container_width=True)

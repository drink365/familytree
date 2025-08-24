# app.py — v8.1 友善表單 + Graphviz 家族樹（女生圓形、過世灰底）+ 法定繼承 + 兄弟姊妹群組
import streamlit as st
from graphviz import Digraph
from collections import defaultdict

st.set_page_config(page_title="家族平台（人物｜關係｜法定繼承｜家族樹）", layout="wide")

# =========================
# 顏色與樣式
# =========================
MALE_COLOR     = "#d9ecff"   # 淡藍
FEMALE_COLOR   = "#ffe0e6"   # 淡紅
DECEASED_COLOR = "#e6e6e6"   # 灰
NODE_BORDER    = "#16465f"
LINE_COLOR     = "#1f4b63"

def node_style_by_person(p):
    """依性別/是否過世回傳 Graphviz node 樣式"""
    if p.get("deceased"):
        return {
            "shape": "box",
            "style": "filled",
            "fillcolor": DECEASED_COLOR,
            "color": NODE_BORDER,
            "fontcolor": "#333",
            "penwidth": "1.2",
        }
    if p.get("gender") == "女":
        return {
            "shape": "ellipse",    # 女生 → 圓形/橢圓
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

# =========================
# 內部資料結構
# =========================
def init_data():
    return {
        "persons": {},    # pid -> {name, gender, deceased}
        "marriages": [],  # [{id, a, b, divorced}]
        "children": [],   # [{marriage_id, children: [pid,...]}]
        "_seq": 0,        # for id issuing
    }

def next_id():
    if "data" not in st.session_state:
        st.session_state.data = init_data()
    if "_seq" not in st.session_state.data:
        st.session_state.data["_seq"] = 0
    st.session_state.data["_seq"] += 1
    return f"P{st.session_state.data['_seq']}"

def next_mid():
    if "data" not in st.session_state:
        st.session_state.data = init_data()
    if "_seq" not in st.session_state.data:
        st.session_state.data["_seq"] = 0
    st.session_state.data["_seq"] += 1
    return f"M{st.session_state.data['_seq']}"

def next_sib_id():
    # 兄弟姊妹群組的虛擬「原生家庭」ID（沒有父母/婚姻，也能放手足在一起）
    if "data" not in st.session_state:
        st.session_state.data = init_data()
    if "_seq" not in st.session_state.data:
        st.session_state.data["_seq"] = 0
    st.session_state.data["_seq"] += 1
    return f"SIB{st.session_state.data['_seq']}"

def ensure_person_id(data, name, gender, deceased=False):
    for pid, p in data["persons"].items():
        if p["name"] == name and p.get("gender") == gender:
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
    chen_a = ensure_person_id(data, "陳大", "男")
    chen_b = ensure_person_id(data, "陳二", "男")
    chen_c = ensure_person_id(data, "陳三", "男")

    # 婚姻
    m_ex = {"id": next_mid(), "a": yilang, "b": exwife, "divorced": True}
    m_w  = {"id": next_mid(), "a": yilang, "b": wife,   "divorced": False}
    m_wz = {"id": next_mid(), "a": wangzi, "b": wz_wife,"divorced": False}
    data["marriages"] = [m_ex, m_w, m_wz]

    # 子女（順序＝左→右）
    data["children"] = [
        {"marriage_id": m_ex["id"], "children": [wangzi]},
        {"marriage_id": m_w["id"],  "children": [chen_a, chen_b, chen_c]},
        {"marriage_id": m_wz["id"], "children": [wz_sun]},
    ]
    return data

def reset_to_empty():
    st.session_state.data = init_data()

if "data" not in st.session_state:
    st.session_state.data = load_demo()

# =========================
# 資料查詢工具
# =========================
def person_label(pid):
    p = st.session_state.data["persons"][pid]
    name = p["name"]
    if p.get("deceased"):
        name = f"{name}（殁）"
    return name

def find_marriage(a, b):
    for m in st.session_state.data["marriages"]:
        if {m["a"], m["b"]} == {a, b}:
            return m
    return None

def parents_of(child_pid):
    out = []
    for row in st.session_state.data["children"]:
        if child_pid in row["children"]:
            mid = row["marriage_id"]
            m = next((mm for mm in st.session_state.data["marriages"] if mm["id"] == mid), None)
            if m:
                out.append((mid, m["a"], m["b"]))
    return out

# =========================
# 家族樹（Graphviz）
# =========================
def draw_tree():
    data = st.session_state.data
    dot = Digraph(comment="Family", format="svg", engine="dot")

    # 更強的版面約束：同層距離與輸出順序
    dot.graph_attr.update(
        rankdir="TB",         # 上下分層
        splines="ortho",      # 直角線，較少與節點穿插
        nodesep="0.55",
        ranksep="0.8",
        ordering="out"        # 盡量依我們提供的相鄰邊順序輸出
    )
    dot.edge_attr.update(color=LINE_COLOR)

    # 1) 先畫所有人（含男女/過世的樣式）
    for pid, p in data["persons"].items():
        dot.node(pid, person_label(pid), **node_style_by_person(p))

    # 2) 畫每段婚姻的 junction + 可見邊
    marriage_ids = set()
    for m in data["marriages"]:
        marriage_ids.add(m["id"])
        jid = f"J_{m['id']}"
        dot.node(jid, "", shape="point", width="0.02", color=LINE_COLOR)
        style = "dashed" if m.get("divorced") else "solid"
        dot.edge(m["a"], jid, dir="none", style=style)
        dot.edge(m["b"], jid, dir="none", style=style)

        # 讓該段婚姻的兩位配偶同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(m["a"])
            s.node(m["b"])

    # 2.1 為「每個人」建立不可見的水平鏈：
    #     [所有前任...] -> 本人 -> [所有現任...]
    #     這會強制「前任永遠在左、現任永遠在右」，避免前任被擠到中間
    spouses_left  = {pid: [] for pid in data["persons"]}
    spouses_right = {pid: [] for pid in data["persons"]}

    for m in data["marriages"]:
        a, b = m["a"], m["b"]
        if m.get("divorced"):     # 視為「前任」
            spouses_left[a].append(b)
            spouses_left[b].append(a)
        else:                     # 視為「現任」
            spouses_right[a].append(b)
            spouses_right[b].append(a)

    for pid in data["persons"].keys():
        chain = spouses_left[pid] + [pid] + spouses_right[pid]
        if len(chain) > 1:
            # 同層 + 高權重不可見邊，形成嚴格的左右順序
            with dot.subgraph() as s:
                s.attr(rank="same")
                for x in chain:
                    s.node(x)
            for u, v in zip(chain, chain[1:]):
                dot.edge(u, v, style="invis", weight="200", minlen="1")

    # 3) 子女連線：為每段婚姻建立一個「children spine」（不可見點）在子女那一層
    #    由 junction 先連到 spine（不可見、高權重），再由 spine 垂直分支到各子女；
    #    並用不可見水平邊強制手足的左右順序（出生序），可明顯減少交錯。
    for row in data["children"]:
        kids = [k for k in row.get("children", []) if k in data["persons"]]
        if not kids:
            continue

        mid = row["marriage_id"]
        if mid in marriage_ids:
            jid = f"J_{mid}"
        else:
            # 沒有父母/婚姻的兄弟姊妹群組，也給一個群組 junction
            jid = f"SIB_{mid}"
            dot.node(jid, "", shape="point", width="0.02", color=LINE_COLOR)

        # 這個婚姻/群組的 children spine
        spine = f"S_{mid}"
        dot.node(spine, "", shape="point", width="0.02", color=LINE_COLOR)

        # spine 與所有子女在同一層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(spine)
            for k in kids:
                s.node(k)

        # junction → spine：不可見、高權重，讓分支從同一水平點出發
        dot.edge(jid, spine, style="invis", weight="150", minlen="1")

        # 用不可見水平邊固定兄弟姊妹的左右順序（依資料排列）
        for u, v in zip(kids, kids[1:]):
            dot.edge(u, v, style="invis", weight="80", minlen="1")

        # 最後才畫出 spine → 每個孩子（可見）
        for k in kids:
            dot.edge(spine, k)

    st.graphviz_chart(dot, use_container_width=True)


# =========================
# 民法 §1138 法定繼承試算
# =========================
def heirs_by_civil_law(target_pid):
    persons = st.session_state.data["persons"]
    marriages = st.session_state.data["marriages"]
    children_rows = st.session_state.data["children"]

    # 直系卑親屬（含代位一層）
    def descendants(root):
        child_map = defaultdict(list)
        for row in children_rows:
            for c in row["children"]:
                child_map[row["marriage_id"]].append(c)

        mids_for_root = [m["id"] for m in marriages if root in (m["a"], m["b"])]
        kids = []
        for mid in mids_for_root:
            kids.extend(child_map.get(mid, []))

        if not kids:
            return set()

        heirs = set()
        for k in kids:
            if not persons[k].get("deceased"):
                heirs.add(k)
            else:
                kmids = [m["id"] for m in marriages if k in (m["a"], m["b"])]
                gkids = []
                for mid in kmids:
                    gkids.extend([c for c in child_map.get(mid, []) if not persons[c].get("deceased")])
                heirs.update(gkids)
        return heirs

    # 父母
    def parents(pid):
        ps = []
        for row in children_rows:
            if pid in row["children"]:
                m = next((mm for mm in marriages if mm["id"] == row["marriage_id"]), None)
                if m:
                    ps.extend([m["a"], m["b"]])
        uniq = []
        for p in ps:
            if p not in uniq and not persons[p].get("deceased"):
                uniq.append(p)
        return set(uniq)

    # 兄弟姊妹（含兄弟姊妹群組 SIBx）
    def siblings(pid):
        sib = set()
        for row in children_rows:
            if pid in row["children"]:
                for c in row["children"]:
                    if c != pid and not persons[c].get("deceased"):
                        sib.add(c)
        return sib

    # 祖父母（簡化：父母的父母）
    def grandparents(pid):
        out = set()
        for p in parents(pid):
            for row in children_rows:
                if p in row["children"]:
                    m = next((mm for mm in marriages if mm["id"] == row["marriage_id"]), None)
                    if m:
                        for gp in (m["a"], m["b"]):
                            if not persons[gp].get("deceased"):
                                out.add(gp)
        return out

    # 配偶（未離婚、未過世）
    spouse = []
    for m in marriages:
        if (m["a"] == target_pid or m["b"] == target_pid) and not m.get("divorced"):
            s = m["b"] if m["a"] == target_pid else m["a"]
            if not persons[s].get("deceased"):
                spouse.append(s)
    spouse = list(dict.fromkeys(spouse))

    lvl1 = descendants(target_pid)
    if lvl1:
        return spouse + sorted(list(lvl1))

    lvl2 = parents(target_pid)
    if lvl2:
        return spouse + sorted(list(lvl2))

    lvl3 = siblings(target_pid)
    if lvl3:
        return spouse + sorted(list(lvl3))

    lvl4 = grandparents(target_pid)
    if lvl4:
        return spouse + sorted(list(lvl4))

    return spouse

# =========================
# UI：標頭 / 導引
# =========================
st.title("家族平台（人物｜關係｜法定繼承｜家族樹）")

with st.expander("📢 說明 / 初學者引導", expanded=True):
    st.markdown(
        """
**本圖以「陳一郎家族譜」為示範。**  
如果你要輸入自己的資料，請點下方按鈕，我會把示範資料清空，並引導你開始新增家族成員、建立婚姻、子女或兄弟姊妹關係。
"""
    )
    colA, colB = st.columns([1,3])
    with colA:
        if st.button("📝 馬上輸入自己的資料", use_container_width=True, type="primary"):
            reset_to_empty()
            st.success("已清空示範資料，請到下方分頁依序新增人物、建立婚姻、掛上子女或兄弟姊妹。")

st.divider()

tabs = st.tabs(["👤 人物", "🔗 關係", "⚖️ 法定繼承試算", "🌳 家族樹"])

# =========================
# Tab 1: 人物
# =========================
with tabs[0]:
    st.subheader("新增人物")
    with st.form("form_add_person", clear_on_submit=True):
        name = st.text_input("姓名", max_chars=30)
        gender = st.radio("性別", ["男", "女"], horizontal=True)
        deceased = st.checkbox("已過世？")
        submitted = st.form_submit_button("新增人物")
        if submitted:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = next_id()
                st.session_state.data["persons"][pid] = {
                    "name": name.strip(),
                    "gender": gender,
                    "deceased": deceased
                }
                st.success(f"已新增：{name}（{gender}）")

    st.markdown("### 目前人物")
    persons = st.session_state.data["persons"]
    if not persons:
        st.info("尚無人物，請先新增。")
    else:
        cols = st.columns(4)
        i = 0
        for pid, p in persons.items():
            with cols[i % 4]:
                st.write(f"**{person_label(pid)}**　（{p['gender']}）")
                st.caption(f"ID: {pid}")
            i += 1

# =========================
# Tab 2: 關係（婚姻 / 子女 / 兄弟姊妹）
# =========================
with tabs[1]:
    st.subheader("建立婚姻關係（現任實線；離婚虛線）")
    if len(st.session_state.data["persons"]) < 2:
        st.info("請先新增至少 2 位人物。")
    else:
        with st.form("form_add_marriage"):
            pids = list(st.session_state.data["persons"].keys())
            a = st.selectbox("配偶 A", options=pids, format_func=lambda x: person_label(x))
            b = st.selectbox("配偶 B", options=pids, index=1 if len(pids) > 1 else 0, format_func=lambda x: person_label(x))
            divorced = st.checkbox("是否離婚？（離婚以虛線呈現）")
            ok = st.form_submit_button("建立婚姻")
            if ok:
                if a == b:
                    st.warning("兩個欄位不可選同一人")
                elif find_marriage(a, b):
                    st.warning("這對已存在婚姻紀錄")
                else:
                    mid = next_mid()
                    st.session_state.data["marriages"].append({"id": mid, "a": a, "b": b, "divorced": divorced})
                    st.success(f"已建立婚姻：{person_label(a)} － {person_label(b)}")

    st.markdown("### 把子女掛到父母（某段婚姻）")
    if not st.session_state.data["marriages"]:
        st.info("目前尚無婚姻，請先在上方建立一段婚姻。")
    else:
        with st.form("form_add_children"):
            mids = [m["id"] for m in st.session_state.data["marriages"]]
            def mid_to_label(mid):
                m = next(mm for mm in st.session_state.data["marriages"] if mm["id"] == mid)
                style = "（離婚）" if m.get("divorced") else ""
                return f"{person_label(m['a'])} × {person_label(m['b'])}{style}"
            sel_mid = st.selectbox("選擇婚姻", options=mids, format_func=mid_to_label)
            kid_pids = st.multiselect(
                "選擇子女（可複選）", 
                options=list(st.session_state.data["persons"].keys()),
                format_func=lambda x: person_label(x)
            )
            ok2 = st.form_submit_button("掛上子女")
            if ok2:
                rows = [row for row in st.session_state.data["children"] if row["marriage_id"] == sel_mid]
                if not rows:
                    st.session_state.data["children"].append({"marriage_id": sel_mid, "children": []})
                    rows = [st.session_state.data["children"][-1]]
                row = rows[0]
                added = 0
                for k in kid_pids:
                    if k not in row["children"]:
                        row["children"].append(k)
                        added += 1
                if added:
                    st.success(f"已新增 {added} 位子女。")
                else:
                    st.info("沒有新增，可能都已經掛過了。")

    st.markdown("### 建立兄弟姊妹群組（原生家庭，不必輸入父母）")
    with st.form("form_add_siblings"):
        all_pids = list(st.session_state.data["persons"].keys())
        sibs = st.multiselect("選擇成員（至少 2 人）", options=all_pids, format_func=lambda x: person_label(x))
        ok3 = st.form_submit_button("建立兄弟姊妹群組")
        if ok3:
            if len(sibs) < 2:
                st.warning("請至少選擇 2 人。")
            else:
                sid = next_sib_id()          # 例如 SIB12
                st.session_state.data["children"].append({"marriage_id": sid, "children": sibs})
                st.success("已建立兄弟姊妹群組。")
                st.caption("（此群組將在家族樹中以一個原生家庭節點挂上，法定繼承也會把他們視為第三順位的手足）")

    # 顯示
    st.markdown("### 目前婚姻與子女 / 兄弟姊妹群組")
    if not st.session_state.data["marriages"] and not st.session_state.data["children"]:
        st.info("尚無關係資料。")
    else:
        # 婚姻
        for m in st.session_state.data["marriages"]:
            style = "（離婚）" if m.get("divorced") else ""
            st.write(f"- **{person_label(m['a'])}**  ×  **{person_label(m['b'])}** {style}")
            rows = [row for row in st.session_state.data["children"] if row["marriage_id"] == m["id"]]
            kids = []
            for r in rows:
                kids.extend(r["children"])
            if kids:
                st.caption("　子女： " + "、".join(person_label(k) for k in kids))
            else:
                st.caption("　子女：－")
        # 兄弟姊妹群組（沒有對應婚姻 id）
        sib_rows = [row for row in st.session_state.data["children"]
                    if not any(m["id"] == row["marriage_id"] for m in st.session_state.data["marriages"])]
        if sib_rows:
            st.write("—")
            for row in sib_rows:
                st.write("• 兄弟姊妹： " + "、".join(person_label(k) for k in row["children"]))

# =========================
# Tab 3: 法定繼承試算
# =========================
with tabs[2]:
    st.subheader("法定繼承試算（民法 §1138）")
    persons = st.session_state.data["persons"]
    if not persons:
        st.info("請先建立人物。")
    else:
        target = st.selectbox("被繼承人", options=list(persons.keys()), format_func=lambda x: person_label(x))
        if target:
            heirs = heirs_by_civil_law(target)
            if heirs:
                st.success("繼承人： " + "、".join(person_label(h) for h in heirs))
                st.caption("（配偶為當然繼承人；僅同一順位與配偶共同分配）")
            else:
                st.warning("依目前資料，查無繼承人。")

# =========================
# Tab 4: 家族樹
# =========================
with tabs[3]:
    st.subheader("家族樹（婚姻中點垂直連子女；離婚虛線；兄弟姊妹群組由原生家庭點掛上）")
    if not st.session_state.data["persons"]:
        st.info("尚無人物，請先新增。")
    else:
        draw_tree()

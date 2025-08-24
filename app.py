# app.py — v8.0 友善表單 + Graphviz 家族樹（女生圓形、過世灰底）+ 法定繼承試算
import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

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
# st.session_state.data = {
#   "persons": { pid: {"name":..., "gender": "男/女", "deceased": bool} },
#   "marriages": [ {"id":mid, "a":pid1, "b":pid2, "divorced": bool} ],
#   "children": [ {"marriage_id": mid, "children": [pid,...]} ],
#   "_seq": int
# }

def init_data():
    return {
        "persons": {},
        "marriages": [],
        "children": [],
        "_seq": 0,     # 一定要有，避免 KeyError
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

def ensure_person_id(data, name, gender, deceased=False):
    # 若已存在同名同性別，復用；否則新增
    for pid, p in data["persons"].items():
        if p["name"] == name and p.get("gender") == gender:
            if deceased: p["deceased"] = True
            return pid
    pid = next_id()
    data["persons"][pid] = {"name": name, "gender": gender, "deceased": deceased}
    return pid

def load_demo():
    """建立示範：陳一郎/前妻(虛線)/現任妻，子女陳大陳二陳三；王子-王子妻-王孫"""
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

# 啟動：若無資料 → 載入示範
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
    """找有沒有 a-b 的婚姻（不管順序）"""
    for m in st.session_state.data["marriages"]:
        if {m["a"], m["b"]} == {a, b}:
            return m
    return None

def parents_of(child_pid):
    """回傳 child_pid 的父母（可能 0~2人）與婚姻 id"""
    out = []
    for row in st.session_state.data["children"]:
        if child_pid in row["children"]:
            mid = row["marriage_id"]
            m = next((mm for mm in st.session_state.data["marriages"] if mm["id"] == mid), None)
            if m:
                out.append((mid, m["a"], m["b"]))
    return out  # 可能多個（重婚/不同家庭），一般 1 個

# =========================
# 家族樹繪製（Graphviz）
# =========================
def draw_tree():
    data = st.session_state.data
    dot = Digraph(comment="Family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")
    dot.edge_attr.update(color=LINE_COLOR)

    # 先畫所有人
    for pid, p in data["persons"].items():
        style = node_style_by_person(p)
        dot.node(pid, person_label(pid), **style)

    # 建婚姻 junction
    for m in data["marriages"]:
        jid = f"J_{m['id']}"
        dot.node(jid, "", shape="point", width="0.02", color=LINE_COLOR)
        style = "dashed" if m.get("divorced") else "solid"
        dot.edge(m["a"], jid, dir="none", style=style)
        dot.edge(m["b"], jid, dir="none", style=style)
        # 夫妻同列
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(m["a"])
            s.node(m["b"])

    # 子女由婚姻 junction 垂直連下來，並將同代排同一層
    for row in data["children"]:
        jid = f"J_{row['marriage_id']}"
        kids = row.get("children", [])
        if not kids: 
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for cid in kids:
                s.node(cid)
        for cid in kids:
            dot.edge(jid, cid)

    st.graphviz_chart(dot, use_container_width=True)

# =========================
# 民法 §1138 法定繼承試算
# =========================
def heirs_by_civil_law(target_pid):
    """回傳合法繼承人清單（含配偶 + 一個順位）"""
    persons = st.session_state.data["persons"]
    marriages = st.session_state.data["marriages"]
    children_rows = st.session_state.data["children"]

    # 直系卑親屬（子女與更下代代位）
    def descendants(root):
        # BFS 找所有子孫（透過 children_rows）
        child_map = defaultdict(list)
        parent_to_mid = {}
        for row in children_rows:
            mid = row["marriage_id"]
            for c in row["children"]:
                child_map[mid].append(c)
        # 找 root 的所有子女（root 與任何配偶的孩子）
        kids = []
        mids_for_root = [m["id"] for m in marriages if root in (m["a"], m["b"])]
        for mid in mids_for_root:
            kids.extend(child_map.get(mid, []))

        # 若無子女就回空
        if not kids:
            return set()

        # 目前策略：只要有直系卑親屬，就以**子女（含代位）**為繼承人
        # 代位：若子女已殁，就由其子女代位（再下一層）。
        # 為簡化，這裡只做一層代位（一般案例夠用；可擴充成遞迴）
        heirs = set()
        for k in kids:
            if not persons[k].get("deceased"):
                heirs.add(k)
            else:
                # 代位：k 的孩子
                kmids = [m["id"] for m in marriages if k in (m["a"], m["b"])]
                gkids = []
                for mid in kmids:
                    gkids.extend([c for c in child_map.get(mid, []) if not persons[c].get("deceased")])
                heirs.update(gkids)
        return heirs

    # 父母
    def parents(pid):
        ps = []
        for mid, a, b in parents_of(pid):
            ps.extend([a, b])
        # 可能重複
        uniq = []
        for p in ps:
            if p not in uniq:
                uniq.append(p)
        # 排除過世者
        uniq = [p for p in uniq if not persons[p].get("deceased")]
        return set(uniq)

    # 兄弟姐妹
    def siblings(pid):
        sib = set()
        # 經由共同父母的 children_rows 推得
        fam_by_mid = defaultdict(list)
        for row in children_rows:
            for c in row["children"]:
                fam_by_mid[row["marriage_id"]].append(c)
        for row in children_rows:
            if pid in row["children"]:
                for c in row["children"]:
                    if c != pid and not persons[c].get("deceased"):
                        sib.add(c)
        return sib

    # 祖父母（簡化：找父母的父母）
    def grandparents(pid):
        out = set()
        for p in parents(pid):
            for gp in parents(p):
                if not persons[gp].get("deceased"):
                    out.add(gp)
        return out

    # 配偶：與 target 有婚姻者（不含已離婚），且未過世
    spouse = []
    for m in marriages:
        if (m["a"] == target_pid or m["b"] == target_pid) and not m.get("divorced"):
            s = m["b"] if m["a"] == target_pid else m["a"]
            if not persons[s].get("deceased"):
                spouse.append(s)

    spouse = list(dict.fromkeys(spouse))  # 去重

    # 順位判斷
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

    # 若都沒有（非常少見），只剩配偶或空
    return spouse

# =========================
# UI：標頭與導覽
# =========================
st.title("家族平台（人物｜關係｜法定繼承｜家族樹）")

with st.expander("📢 說明 / 初學者引導", expanded=True):
    st.markdown(
        """
**本圖以「陳一郎家族譜」為示範。**  
如果你要輸入自己的資料，請點下方按鈕，我會把示範資料清空，並引導你開始新增家族成員、建立婚姻與小孩關係。

"""
    )
    colA, colB = st.columns([1,3])
    with colA:
        if st.button("📝 馬上輸入自己的資料", use_container_width=True, type="primary"):
            reset_to_empty()
            st.success("已清空示範資料，請到下方分頁依序新增人物、建立婚姻、掛上小孩。")

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
# Tab 2: 關係（婚姻 ＆ 子女掛父母）
# =========================
with tabs[1]:
    st.subheader("建立婚姻關係（現任實線；離婚虛線）")
    if len(st.session_state.data["persons"]) < 2:
        st.info("請先新增至少 2 位人物。")
    else:
        with st.form("form_add_marriage"):
            pids = list(st.session_state.data["persons"].keys())
            labels = [person_label(pid) for pid in pids]
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
                # 找這段婚姻的 children row
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

    # 顯示目前婚姻＆子女
    st.markdown("### 目前婚姻與子女")
    if not st.session_state.data["marriages"]:
        st.info("尚無婚姻。")
    else:
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

# =========================
# Tab 3: 法定繼承試算（民法 §1138）
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
    st.subheader("家族樹（前任在左；本人置中；現任在右；孩子由中點垂直）")
    if not st.session_state.data["persons"]:
        st.info("尚無人物，請先新增。")
    else:
        draw_tree()

# app.py
import streamlit as st
from graphviz import Digraph

st.set_page_config(page_title="家族平台", page_icon="🌳", layout="wide")

# ---------- 資料結構與初始化 ----------
def init_data():
    return {
        "_seq": 0,  # 統一流水號
        "persons": {},  # pid -> {name, gender: '男'/'女', deceased: bool}
        "marriages": {},  # mid -> {p1, p2, divorced: bool}
        "children": {},  # mid -> [child_pid, ...]
        # 沒有父母資料也能掛兄弟姐妹：用群組方式
        "sibling_groups": []  # list[list[pid,...]]
    }

def ensure_session():
    if "data" not in st.session_state:
        st.session_state.data = init_data()

def next_id(prefix="p"):
    d = st.session_state.data
    d["_seq"] += 1
    return f"{prefix}{d['_seq']}"

# ---------- 顏色與外觀 ----------
MALE_FILL = "#dbeafe"   # 淡藍
FEMALE_FILL = "#ffe0e6" # 淡粉
DECEASED_FILL = "#e5e7eb" # 灰
LINE_COLOR = "#123a4a"
NODE_BORDER = "#0e2d3b"

def person_label(info):
    label = info["name"]
    if info.get("deceased"):
        label += "（殁）"
    return label

def person_style(info):
    if info.get("deceased"):
        fill = DECEASED_FILL
    else:
        fill = MALE_FILL if info.get("gender") == "男" else FEMALE_FILL
    shape = "box" if info.get("gender") == "男" else "ellipse"
    return shape, fill

# ---------- 載入示範 / 清空 ----------
def load_demo():
    st.session_state.data = init_data()
    d = st.session_state.data

    # 人
    yilang = add_person("陳一郎", "男", False)
    exwife = add_person("陳前妻", "女", False)
    curr   = add_person("陳妻", "女", False)

    wangzi = add_person("王子", "男", False)
    wzwife = add_person("王子妻", "女", False)
    wgsun  = add_person("王孫", "男", False)

    chenda = add_person("陳大", "男", False)
    chener = add_person("陳二", "男", False)
    chensan= add_person("陳三", "男", False)

    # 婚姻：前任（離婚）與現任
    m_ex = new_marriage(yilang, exwife, divorced=True)
    m_cu = new_marriage(yilang, curr, divorced=False)

    # 子女：前一段婚姻生王子，現任生陳大陳二陳三
    attach_child(m_ex, wangzi)
    attach_child(m_cu, chenda)
    attach_child(m_cu, chener)
    attach_child(m_cu, chensan)

    # 王子婚姻與子女
    m_wz = new_marriage(wangzi, wzwife, False)
    attach_child(m_wz, wgsun)

def clear_all():
    st.session_state.data = init_data()

# ---------- CRUD: 人 / 婚姻 / 子女 / 兄弟姐妹 ----------
def add_person(name, gender, deceased):
    d = st.session_state.data
    pid = next_id("p")
    d["persons"][pid] = {"name": name.strip(), "gender": gender, "deceased": bool(deceased)}
    return pid

def new_marriage(p1, p2, divorced):
    d = st.session_state.data
    mid = next_id("m")
    d["marriages"][mid] = {"p1": p1, "p2": p2, "divorced": bool(divorced)}
    if mid not in d["children"]:
        d["children"][mid] = []
    return mid

def attach_child(mid, child_pid):
    d = st.session_state.data
    d["children"].setdefault(mid, [])
    if child_pid not in d["children"][mid]:
        d["children"][mid].append(child_pid)

def add_siblings(a, b):
    """把兩個人放在同一個兄弟姐妹群組；若其中有人已在群組，就合併群組。"""
    d = st.session_state.data
    gidx_a, gidx_b = None, None
    for idx, grp in enumerate(d["sibling_groups"]):
        if a in grp: gidx_a = idx
        if b in grp: gidx_b = idx
    if gidx_a is not None and gidx_b is not None:
        if gidx_a != gidx_b:
            # 合併
            d["sibling_groups"][gidx_a] = sorted(list(set(d["sibling_groups"][gidx_a] + d["sibling_groups"][gidx_b])))
            d["sibling_groups"].pop(gidx_b)
    elif gidx_a is not None:
        if b not in d["sibling_groups"][gidx_a]:
            d["sibling_groups"][gidx_a].append(b)
            d["sibling_groups"][gidx_a].sort()
    elif gidx_b is not None:
        if a not in d["sibling_groups"][gidx_b]:
            d["sibling_groups"][gidx_b].append(a)
            d["sibling_groups"][gidx_b].sort()
    else:
        d["sibling_groups"].append(sorted([a, b]))

def display_name(pid):
    d = st.session_state.data
    info = d["persons"].get(pid, {})
    return info.get("name", pid)

# ---------- 法定繼承（1138，配偶當然+各順位） ----------
def living_children_of(pid):
    """僅示範：找某人的直系卑親屬（子女，未做代位/再代位）。"""
    d = st.session_state.data
    kids = []
    for mid, chs in d["children"].items():
        mar = d["marriages"][mid]
        if mar["p1"] == pid or mar["p2"] == pid:
            kids.extend(chs)
    # 僅取「在世」直系卑親屬
    alive = [c for c in kids if not d["persons"][c].get("deceased")]
    return alive

def parents_of(pid):
    d = st.session_state.data
    # 透過子女反查父母（父母若過世仍列入父母順位，繼承人要在世）
    # 這裡僅示意：只要找到把 pid 掛在某段婚姻，就可得該婚姻雙方為父母
    res = []
    for mid, chs in d["children"].items():
        if pid in chs:
            p1, p2 = d["marriages"][mid]["p1"], d["marriages"][mid]["p2"]
            if p1 not in res: res.append(p1)
            if p2 not in res: res.append(p2)
    # 僅取在世
    return [p for p in res if not d["persons"][p].get("deceased")]

def siblings_of(pid):
    d = st.session_state.data
    sibs = set()
    # 1) 同婚姻接點的其他子女
    for mid, chs in d["children"].items():
        if pid in chs:
            for c in chs:
                if c != pid:
                    sibs.add(c)
    # 2) sibling_groups 內的同組
    for grp in d["sibling_groups"]:
        if pid in grp:
            for c in grp:
                if c != pid:
                    sibs.add(c)
    # 僅在世
    return [s for s in sibs if not d["persons"][s].get("deceased")]

def grandparents_of(pid):
    d = st.session_state.data
    gps = set()
    for p in parents_of(pid):
        for gp in parents_of(p):
            gps.add(gp)
    # 僅在世
    return [g for g in gps if not d["persons"][g].get("deceased")]

def current_spouse_of(pid):
    """回傳『在婚』配偶（1138條僅現任配偶）。若同時多段在婚，擇一示意。"""
    d = st.session_state.data
    rv = []
    for mid, m in d["marriages"].items():
        if not m["divorced"] and (m["p1"] == pid or m["p2"] == pid):
            other = m["p2"] if m["p1"] == pid else m["p1"]
            if not d["persons"][other].get("deceased"):
                rv.append(other)
    return rv[:1]  # 示意取一位

def legal_heirs_1138(decedent):
    """配偶當然 + (一順位 直系卑親屬 → 二 父母 → 三 兄弟姐妹 → 四 祖父母)"""
    spouse = current_spouse_of(decedent)  # 可能空
    # 順位
    r1 = living_children_of(decedent)
    if r1:
        return spouse + r1
    r2 = parents_of(decedent)
    if r2:
        return spouse + r2
    r3 = siblings_of(decedent)
    if r3:
        return spouse + r3
    r4 = grandparents_of(decedent)
    return spouse + r4

# ---------- 繪圖 ----------
def render_tree():
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    dot = Digraph(comment="Family Tree", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.7")
    dot.node_attr.update(style="filled", color=NODE_BORDER, fontcolor="#0b2530", penwidth="1.2")
    dot.edge_attr.update(color=LINE_COLOR, penwidth="1.6")

    # 1) 畫所有人
    for pid, info in d["persons"].items():
        shape, fill = person_style(info)
        dot.node(pid, person_label(info), shape=shape, fillcolor=fill)

    # 2) 婚姻接點 + 夫妻 + 子女
    for mid, m in d["marriages"].items():
        j = f"j_{mid}"
        dot.node(j, "", shape="point", width="0.02", color=LINE_COLOR)
        style = "dashed" if m["divorced"] else "solid"
        dot.edge(m["p1"], j, dir="none", style=style)
        dot.edge(m["p2"], j, dir="none", style=style)

        # 夫妻同一排
        with dot.subgraph() as s:
            s.attr(rank="same")
            # 優先把「前任、本人、現任」順序在同一層（僅提供排序提示）
            for pid in ordered_couple(m["p1"], m["p2"]):
                s.node(pid)

        # 子女
        for c in d["children"].get(mid, []):
            dot.edge(j, c)

    # 3) 兄弟姐妹群組：建立群組接點（像父母接點）向下接線，僅當無父母資訊時才畫
    for grp in d["sibling_groups"]:
        if len(grp) < 2:
            continue
        # 如果他們任何一人已有父母接點，通常就不再額外畫兄弟群組線，以避免重疊混亂
        if any(has_parent(pid) for pid in grp):
            continue
        sid = f"sg_{'_'.join(grp)}"
        dot.node(sid, "", shape="point", width="0.02", color=LINE_COLOR)
        with dot.subgraph() as s:
            s.attr(rank="same")
            for pid in grp:
                s.node(pid)
        for pid in grp:
            dot.edge(sid, pid)

    st.graphviz_chart(dot, use_container_width=True)

def has_parent(pid):
    d = st.session_state.data
    for mid, chs in d["children"].items():
        if pid in chs:
            return True
    return False

def ordered_couple(p1, p2):
    """盡力把『前任、本人、現任』順序排在同一層（Graphviz 不保證，但有助於呈現）。"""
    d = st.session_state.data

    def role_of(target, partner):
        # partner 的某段婚姻相對於 target 而言是前任或現任
        for mid, m in d["marriages"].items():
            if (m["p1"], m["p2"]) in [(target, partner), (partner, target)]:
                return "ex" if m["divorced"] else "cur"
        return "cur"

    # 盡量讓：前任, 本人, 現任
    # 這個函式只回傳兩個節點的順序（誰在誰前面），單純盡力把離婚者放左、在婚者放右
    # 若都在婚/都離婚，就依名字排序避免閃動
    r1 = role_of(p1, p2)
    r2 = role_of(p2, p1)
    if r1 == "ex" and r2 == "cur":
        return [p1, p2]
    if r1 == "cur" and r2 == "ex":
        return [p2, p1]
    # 相同狀態時，按名稱
    n1, n2 = display_name(p1), display_name(p2)
    return [p1, p2] if n1 <= n2 else [p2, p1]

# ---------- UI：頁面 ----------
def page_header():
    st.markdown(
        "<h1 style='margin:0'>🌳 家族平台（人物｜關係｜法定繼承｜家族樹）</h1>",
        unsafe_allow_html=True
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
            load_demo()
            st.rerun()
    with c2:
        if st.button("📝 馬上輸入自己的資料（清空）", use_container_width=True):
            clear_all()
            st.rerun()
    st.caption("本圖以「陳一郎家族譜」為示範。點選上方按鈕可立即清空並開始輸入自己的家族資料。")

def tab_people():
    st.subheader("人物")
    with st.form("add_person"):
        name = st.text_input("姓名")
        gender = st.selectbox("性別", ["請選擇", "男", "女"], index=0)
        deceased = st.checkbox("已過世？")
        ok = st.form_submit_button("新增人物")
        if ok:
            if not name.strip():
                st.error("請輸入姓名")
            elif gender == "請選擇":
                st.error("請選擇性別")
            else:
                add_person(name.strip(), gender, deceased)
                st.success(f"已新增：{name}")
                st.rerun()

    d = st.session_state.data
    if d["persons"]:
        st.markdown("**目前人物**")
        rows = []
        for pid, info in d["persons"].items():
            rows.append(f"- {info['name']}（{info['gender']}）" + ("｜已過世" if info.get("deceased") else ""))
        st.markdown("\n".join(rows))

def tab_relations():
    st.subheader("關係")

    d = st.session_state.data
    persons = list(d["persons"].keys())
    if not persons:
        st.info("請先新增人物，或點上方『載入示範』。")
        return

    st.markdown("### 建立婚姻（現任 / 離婚）")
    with st.form("form_marriage"):
        c1, c2, c3 = st.columns([1, 1, 0.6])
        with c1:
            p1 = st.selectbox("配偶 A", ["請選擇"] + persons, format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
        with c2:
            p2_opts = ["請選擇"] + [pid for pid in persons if pid != p1]
            p2 = st.selectbox("配偶 B", p2_opts, format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
        with c3:
            divorced = st.checkbox("此婚姻為『離婚/前配偶』", value=False)
        ok = st.form_submit_button("建立婚姻")
        if ok:
            if p1 == "請選擇" or p2 == "請選擇":
                st.error("請選擇兩位不同的人物")
            elif p1 == p2:
                st.error("配偶 A / B 不可相同")
            else:
                new_marriage(p1, p2, divorced)
                st.success(f"已建立婚姻：{display_name(p1)}－{display_name(p2)}（{'離婚' if divorced else '在婚'}）")
                st.rerun()

st.markdown("### 把子女掛到父母（某段婚姻）")
with st.form("form_attach_child"):
    mar_display = []
    mar_ids = []
    for mid, m in d["marriages"].items():
        a, b = display_name(m["p1"]), display_name(m["p2"])
        tag = "（離婚）" if m["divorced"] else "（在婚）"
        mar_display.append(f"{a}－{b} {tag}")
        mar_ids.append(mid)

    if not mar_ids:
        st.info("目前尚無婚姻，請先在上方建立婚姻。")
    else:
        which = st.selectbox("選擇父母（某段婚姻）", ["請選擇"] + mar_ids,
                             format_func=lambda x: (mar_display[mar_ids.index(x)] if x != "請選擇" else "請選擇"))
        child = st.selectbox("子女", ["請選擇"] + persons, format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")

        submit_child = st.form_submit_button("掛上子女")  # 這裡加了提交按鈕
        if submit_child:
            if which == "請選擇" or child == "請選擇":
                st.error("請選擇婚姻與子女")
            else:
                attach_child(which, child)
                st.success(f"已將「{display_name(child)}」掛到：{mar_display[mar_ids.index(which)]}")
                st.rerun()


    st.markdown("### 設定兄弟姐妹（無父母資料也能掛）")
    with st.form("form_siblings"):
        a = st.selectbox("人物 A", ["請選擇"] + persons, format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
        b = st.selectbox("人物 B", ["請選擇"] + [pid for pid in persons if pid != a],
                         format_func=lambda x: display_name(x) if x != "請選擇" else "請選擇")
        ok3 = st.form_submit_button("設為兄弟姐妹")
        if ok3:
            if a == "請選擇" or b == "請選擇":
                st.error("請選擇兩位不同的人物")
            else:
                add_siblings(a, b)
                st.success(f"已將「{display_name(a)}」與「{display_name(b)}」設為兄弟姐妹")
                st.rerun()

def tab_legal():
    st.subheader("法定繼承試算")
    d = st.session_state.data
    if not d["persons"]:
        st.info("請先新增人物，或『載入示範』。")
        return
    p = st.selectbox("選擇被繼承人", list(d["persons"].keys()), format_func=display_name)
    heirs = legal_heirs_1138(p)
    if not heirs:
        st.warning("沒有找到符合 1138 條的繼承人（此為示範邏輯，未涵蓋全部情況）。")
    else:
        st.success("繼承人（示範）：")
        st.markdown("、".join(display_name(h) for h in heirs))

def tab_tree():
    st.subheader("家族樹")
    render_tree()

# ---------- 主程式 ----------
def main():
    ensure_session()
    page_header()

    tabs = st.tabs(["人物", "關係", "法定繼承試算", "家族樹"])
    with tabs[0]:
        tab_people()
    with tabs[1]:
        tab_relations()
    with tabs[2]:
        tab_legal()
    with tabs[3]:
        tab_tree()

if __name__ == "__main__":
    main()

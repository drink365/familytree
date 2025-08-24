# app.py
# 家族平台 v7.9.x - 精簡完整版（可直接貼到 Streamlit）
import streamlit as st
from graphviz import Digraph
from collections import defaultdict

st.set_page_config(page_title="家族平台", page_icon="🌳", layout="wide")

# =========================
# 基礎：Session 資料結構
# =========================

def _blank():
    return {
        "_seq": 0,
        "persons": {},             # pid -> {name, gender, dead}
        "marriages": {},           # mid -> {p1, p2, divorced?}
        "children": defaultdict(list),  # mid -> [child_pid...]
        "parents_of": {},          # child_pid -> mid
        "sibling_junctions": {},   # sid -> {members:[pid...]}
    }

if "data" not in st.session_state:
    st.session_state.data = _blank()

DATA = st.session_state.data  # alias

# ---------- 遷移（防舊版存到錯誤型別） ----------
def migrate_schema():
    need = {
        "_seq": int,
        "persons": dict,
        "marriages": dict,
        "children": dict,
        "parents_of": dict,
        "sibling_junctions": dict,
    }
    for k, tp in need.items():
        if k not in DATA:
            DATA[k] = tp() if tp is not dict else {}
        else:
            if tp is dict and not isinstance(DATA[k], dict):
                DATA[k] = {}
            if tp is int and not isinstance(DATA[k], int):
                DATA[k] = 0
    # children 應該是 list 值
    if isinstance(DATA.get("children"), dict):
        for mid, arr in list(DATA["children"].items()):
            if not isinstance(arr, list):
                DATA["children"][mid] = list(arr)

migrate_schema()

def next_id(prefix="id"):
    DATA["_seq"] += 1
    return f"{prefix}{DATA['_seq']}"

# =========================
# Demo 與 Onboarding
# =========================
def ensure_person_id(name, gender="男", dead=False):
    # 以姓名找，若不存在就新增
    for pid, p in DATA["persons"].items():
        if p["name"] == name:
            return pid
    pid = next_id("p")
    DATA["persons"][pid] = {"name": name, "gender": gender, "dead": bool(dead)}
    return pid

def load_demo():
    st.session_state.data = _blank()
    migrate_schema()
    # 人
    yilang = ensure_person_id("陳一郎", "男")
    exw    = ensure_person_id("陳前妻", "女")
    curw   = ensure_person_id("陳妻", "女")
    wangzi = ensure_person_id("王子", "男")
    wz_w   = ensure_person_id("王子妻", "女")
    chenda = ensure_person_id("陳大", "男")
    chener = ensure_person_id("陳二", "男")
    chensan= ensure_person_id("陳三", "男")
    wangs  = ensure_person_id("王孫", "男")

    # 婚姻（現任 / 離婚）
    mid_cur = next_id("m")
    DATA["marriages"][mid_cur] = {"p1": yilang, "p2": curw, "divorced": False}
    mid_ex  = next_id("m")
    DATA["marriages"][mid_ex]  = {"p1": yilang, "p2": exw,  "divorced": True}

    # 子女
    DATA["children"][mid_cur] = [chenda, chener, chensan]
    DATA["parents_of"][chenda] = mid_cur
    DATA["parents_of"][chener] = mid_cur
    DATA["parents_of"][chensan]= mid_cur

    DATA["children"][mid_ex] = [wangzi]
    DATA["parents_of"][wangzi] = mid_ex

    # 王子成家
    mid_w = next_id("m")
    DATA["marriages"][mid_w] = {"p1": wangzi, "p2": wz_w, "divorced": False}
    DATA["children"][mid_w] = [wangs]
    DATA["parents_of"][wangs] = mid_w

    st.success("已載入示範資料：陳一郎家族。")

# =========================
# UI 小元件
# =========================
GENDER_COLOR = {
    "男":  ("#d9ebff", "box"),   # 男：淡藍，矩形
    "女":  ("#ffd9e2", "ellipse"),# 女：淡紅，橢圓
    "其他":("#efe7ff", "box")
}
DEAD_COLOR = "#e6e6e6"

def person_label(pid):
    p = DATA["persons"][pid]
    nm = p["name"]
    if p.get("dead"):
        nm += "（殁）"
    return nm

def ordered_spouses(pid):
    """
    取得此人所有配偶，回傳 (ex_list, current_list) 讓畫圖時能 ex 左、現任右。
    """
    exs, curs = [], []
    for mid, m in DATA["marriages"].items():
        if m["p1"] == pid or m["p2"] == pid:
            other = m["p2"] if m["p1"] == pid else m["p1"]
            if m.get("divorced"):
                exs.append((mid, other))
            else:
                curs.append((mid, other))
    return exs, curs

# =========================
# 家族樹（Graphviz）
# =========================
def render_tree():
    dot = Digraph(format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.4", ranksep="0.7")
    dot.node_attr.update(fontname="Noto Sans CJK TC", color="#1f3a4a", penwidth="1.5")

    # 先畫所有人
    for pid, p in DATA["persons"].items():
        fill, shape = GENDER_COLOR.get(p["gender"], GENDER_COLOR["其他"])
        if p.get("dead"):
            fill = DEAD_COLOR
        dot.node(pid, person_label(pid), style="filled", fillcolor=fill, shape=shape)

    # 婚姻 junction 與子女
    for mid, m in DATA["marriages"].items():
        p1, p2 = m["p1"], m["p2"]
        divorced = m.get("divorced", False)

        # 夫妻與婚姻點同 rank
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(p1)
            s.node(p2)

        # 婚姻 junction
        dot.node(mid, "", shape="point", width="0.02", color="#1f3a4a")

        style = "dashed" if divorced else "solid"
        dot.edge(p1, mid, dir="none", style=style)
        dot.edge(p2, mid, dir="none", style=style)

        # 子女
        kids = DATA["children"].get(mid, [])
        if kids:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for c in kids:
                    s.node(c)
            for c in kids:
                dot.edge(mid, c)

    # 兄弟姐妹 junction（讓非同婚姻卻為同輩的人併列）
    for sid, sj in (DATA.get("sibling_junctions") or {}).items():
        members = sj.get("members", [])
        if len(members) >= 2:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for m in members:
                    s.node(m)

    # 配偶相鄰：用不可見邊定序（ex —> person —> current）
    # 注意：Graphviz 不保證百分百絕對位置，但這做法通常能穩定達到需求
    for pid in DATA["persons"].keys():
        exs, curs = ordered_spouses(pid)
        if exs or curs:
            if exs:
                # 多前任：用不可見鏈 ex1->ex2->...->pid
                prev = None
                for mid, sp in exs:
                    if prev:
                        dot.edge(prev, sp, style="invis")
                    prev = sp
                dot.edge(exs[-1][1], pid, style="invis")
            if curs:
                # pid->cur1->cur2
                prev = pid
                for mid, sp in curs:
                    dot.edge(prev, sp, style="invis")
                    prev = sp

    return dot

# =========================
# 法定繼承（簡化示意）
# =========================
def legal_heirs_of(target_pid):
    """
    回傳 (heir_pids, 說明文字)
    - 配偶始終為繼承人（若存在婚姻關係，就當作存在配偶）
    - 第一順位：直系卑親屬（有則只與配偶分配）
    - 第二：父母；第三：兄弟姐妹；第四：祖父母
    - 只做示意，不含代位、收養、特留分、應繼分實際比例等複雜計算
    """
    persons = DATA["persons"]
    marriages = DATA["marriages"]

    # 配偶（無論離婚與否，這裡簡化：若有現任才列入；可視需求調整）
    spouses = []
    for mid, m in marriages.items():
        if target_pid in (m["p1"], m["p2"]) and not m.get("divorced"):
            spouses.append(m["p2"] if m["p1"] == target_pid else m["p1"])
    # 第一順位：孩子（直系卑親屬）
    children = []
    for mid, kids in DATA["children"].items():
        m = marriages.get(mid)
        if not m:
            continue
        if target_pid in (m["p1"], m["p2"]):
            children.extend(kids)

    # 若有第一順位
    if children:
        heirs = list(set(children + spouses))
        note = "配偶 + 第一順位（直系卑親屬）。"
        return heirs, note

    # 父母
    parents = []
    # 找 child 的 parents 反向：已知的是 child->mid；我們需要 pid->父母
    # 作法：從所有 mid 的 kids 中找出 target_pid 的父母
    parent_mids = set()
    for mid, kids in DATA["children"].items():
        if target_pid in kids:
            parent_mids.add(mid)
    for mid in parent_mids:
        m = marriages.get(mid)
        if not m:
            continue
        parents.extend([m["p1"], m["p2"]])
    parents = list(set(parents))

    if parents:
        heirs = list(set(parents + spouses))
        note = "配偶 + 第二順位（父母）。"
        return heirs, note

    # 兄弟姐妹（透過 sibling_junctions）
    siblings = set()
    for sid, sj in (DATA.get("sibling_junctions") or {}).items():
        mb = sj.get("members", [])
        if target_pid in mb:
            siblings |= set(mb)
    siblings.discard(target_pid)
    siblings = list(siblings)
    if siblings:
        heirs = list(set(siblings + spouses))
        note = "配偶 + 第三順位（兄弟姊妹）。"
        return heirs, note

    # 祖父母：簡化為「父母的父母」搜尋
    grandparents = set()
    for p in parents:
        gp_mids = set()
        for mid, kids in DATA["children"].items():
            if p in kids:
                gp_mids.add(mid)
        for mid in gp_mids:
            m = marriages.get(mid)
            if m:
                grandparents.add(m["p1"])
                grandparents.add(m["p2"])
    grandparents.discard(target_pid)
    grandparents = list(grandparents)
    if grandparents:
        heirs = list(set(grandparents + spouses))
        note = "配偶 + 第四順位（祖父母）。"
        return heirs, note

    # 都沒有：只有配偶或無繼承人（示意）
    if spouses:
        return spouses, "僅配偶（無其他順位）。"
    return [], "無可辨識之繼承人（示意）。"

# =========================
# 頁首 & 導引
# =========================
st.title("🌳 家族平台（人物｜關係｜法定繼承｜家族樹）")

with st.container():
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
            load_demo()
            st.experimental_rerun()
    with c2:
        if st.button("📝 馬上輸入自己的資料（清空示範）", use_container_width=True):
            st.session_state.data = _blank()
            migrate_schema()
            st.success("已清空示範資料，請開始輸入您的家族成員與關係。")
            st.experimental_rerun()

st.caption("本圖以 **陳一郎家族譜** 為示範。")

# =========================
# 分頁
# =========================
tab_people, tab_rel, tab_inherit, tab_tree = st.tabs(["👤 人物", "🔗 關係", "⚖️ 法定繼承試算", "🗺️ 家族樹"])

# ----- 人物 -----
with tab_people:
    st.subheader("新增 / 編輯人物")
    persons = DATA["persons"]

    with st.form("add_person_form", clear_on_submit=True):
        name = st.text_input("姓名")
        gender = st.selectbox("性別", ["男", "女", "其他"], index=0)
        dead = st.checkbox("是否已過世")
        submitted = st.form_submit_button("新增人物")
        if submitted:
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                ensure_person_id(name.strip(), gender, dead)
                st.success(f"已新增：{name}")
                st.experimental_rerun()

    if persons:
        st.markdown("#### 既有人物")
        for pid, p in list(persons.items()):
            with st.expander(f"{person_label(pid)}（{p['gender']}）", expanded=False):
                with st.form(f"edit_{pid}"):
                    nn = st.text_input("姓名", value=p["name"])
                    gg = st.selectbox("性別", ["男","女","其他"], index=["男","女","其他"].index(p["gender"]))
                    dd = st.checkbox("已過世", value=p.get("dead", False))
                    colx, coly = st.columns([1,1])
                    with colx:
                        ok = st.form_submit_button("保存")
                    with coly:
                        delok = st.form_submit_button("刪除")
                if ok:
                    p["name"], p["gender"], p["dead"] = nn.strip(), gg, dd
                    st.success("已保存")
                    st.experimental_rerun()
                if delok:
                    # 同步刪關聯
                    # 1) 從婚姻移除（刪該婚姻）
                    to_del = []
                    for mid, m in DATA["marriages"].items():
                        if pid in (m["p1"], m["p2"]):
                            to_del.append(mid)
                    for mid in to_del:
                        # 同時移除子女對應
                        for c in DATA["children"].get(mid, []):
                            DATA["parents_of"].pop(c, None)
                        DATA["children"].pop(mid, None)
                        DATA["marriages"].pop(mid, None)
                    # 2) 從 sibling_junctions 移除
                    for sid, sj in list((DATA.get("sibling_junctions") or {}).items()):
                        if pid in sj.get("members", []):
                            sj["members"] = [x for x in sj["members"] if x != pid]
                            if len(sj["members"]) < 2:
                                DATA["sibling_junctions"].pop(sid, None)
                    # 3) 從 parents_of（如果他是 child）
                    DATA["parents_of"].pop(pid, None)
                    # 4) 刪此人
                    persons.pop(pid, None)
                    st.success("已刪除")
                    st.experimental_rerun()
    else:
        st.info("尚無人物，請先新增。")

# ----- 關係 -----
with tab_rel:
    st.subheader("婚姻 / 子女 / 兄弟姊妹 掛接")

    # 建立婚姻
    st.markdown("### 建立婚姻")
    if len(DATA["persons"]) < 2:
        st.info("請先建立至少兩個人物。")
    else:
        all_people = {person_label(pid): pid for pid in DATA["persons"]}
        with st.form("add_marriage"):
            c1, c2 = st.columns(2)
            with c1:
                p1 = st.selectbox("配偶 A", list(all_people.keys()))
            with c2:
                p2 = st.selectbox("配偶 B", [k for k in all_people.keys() if k != p1])
            divorced = st.checkbox("是否離婚（將以虛線呈現）")
            okm = st.form_submit_button("建立婚姻")
            if okm:
                pid1, pid2 = all_people[p1], all_people[p2]
                # 不重複建立同對
                exists = any((m["p1"]==pid1 and m["p2"]==pid2) or (m["p1"]==pid2 and m["p2"]==pid1)
                             for m in DATA["marriages"].values())
                if exists:
                    st.warning("這兩人已存在婚姻關係。")
                else:
                    mid = next_id("m")
                    DATA["marriages"][mid] = {"p1": pid1, "p2": pid2, "divorced": divorced}
                    DATA["children"].setdefault(mid, [])
                    st.success("已建立婚姻")

    st.markdown("### 把子女掛到父母（選某段婚姻）")
    # mid 集合（合併 marriages 與 sibling_junctions 前先保守）
    all_mid = {}
    all_mid.update(DATA.get("marriages", {}))
    sj = DATA.get("sibling_junctions") or {}
    if isinstance(sj, dict):
        # sibling_junctions 不供子女掛接，只合併時避免 KeyError。這裡不加入 all_mid。
        pass

    if DATA["marriages"]:
        mid_opts = {f"{person_label(m['p1'])} ↔ {person_label(m['p2'])}" + ("（離）" if m.get("divorced") else ""): mid
                    for mid, m in DATA["marriages"].items()}
        kid_opts = {person_label(pid): pid for pid in DATA["persons"].keys()}
        with st.form("add_child"):
            which = st.selectbox("選擇婚姻", list(mid_opts.keys()))
            kid   = st.selectbox("選擇子女", list(kid_opts.keys()))
            okc = st.form_submit_button("掛上子女")
            if okc:
                mid = mid_opts[which]
                cid = kid_opts[kid]
                # 先把他從舊父母關係移除
                old = DATA["parents_of"].get(cid)
                if old and cid in DATA["children"].get(old, []):
                    DATA["children"][old].remove(cid)
                DATA["parents_of"][cid] = mid
                DATA["children"].setdefault(mid, [])
                if cid not in DATA["children"][mid]:
                    DATA["children"][mid].append(cid)
                st.success("已掛上子女")
    else:
        st.info("目前尚無婚姻，請先建立一段婚姻。")

    st.markdown("### 兄弟姐妹掛接")
    if len(DATA["persons"]) >= 2:
        # 建立一個新的 sibling junction，或把人加入既有 junction
        with st.form("add_sibling"):
            col1, col2 = st.columns([2,1])
            with col1:
                pA = st.selectbox("選擇一位成員（加入/建立兄弟姊妹群）",
                                  [person_label(pid) for pid in DATA["persons"]])
                pB = st.multiselect("再選擇 1 位以上，將與上方成員並列為兄弟姊妹",
                                    [person_label(pid) for pid in DATA["persons"] if person_label(pid)!=pA])
            with col2:
                oks = st.form_submit_button("建立 / 加入")
            if oks:
                pidA = [pid for pid,p in DATA["persons"].items() if person_label(pid)==pA][0]
                pidsB = [pid for pid in DATA["persons"] if person_label(pid) in pB]
                # 嘗試找到 A 已屬於的兄弟姊妹群
                belong_sid = None
                for sid, sj in DATA["sibling_junctions"].items():
                    if pidA in sj.get("members", []):
                        belong_sid = sid
                        break
                if not belong_sid:
                    belong_sid = next_id("s")
                    DATA["sibling_junctions"][belong_sid] = {"members": [pidA]}
                for x in pidsB:
                    if x not in DATA["sibling_junctions"][belong_sid]["members"]:
                        DATA["sibling_junctions"][belong_sid]["members"].append(x)
                st.success("已建立/更新兄弟姊妹關係")
    else:
        st.info("人數太少，無法建立兄弟姐妹。")

# ----- 法定繼承 -----
with tab_inherit:
    st.subheader("法定繼承試算（示意）")
    if not DATA["persons"]:
        st.info("請先新增人物。")
    else:
        who = st.selectbox("選擇被繼承人", [person_label(pid) for pid in DATA["persons"]])
        target = [pid for pid in DATA["persons"] if person_label(pid)==who][0]
        heirs, note = legal_heirs_of(target)
        if heirs:
            st.success(f"結果：{note}")
            st.write("可能的繼承參與人（示意）：")
            st.write(", ".join(person_label(h) for h in heirs))
        else:
            st.info(note)

# ----- 家族樹 -----
with tab_tree:
    st.subheader("家族樹（前任在左，本人置中，現任在右；三代分層）")
    if not DATA["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
    else:
        dot = render_tree()
        st.graphviz_chart(dot, use_container_width=True)

# app.py
# 家族平台（人物 | 關係 | 法定繼承 | 家族樹）
# - 友善表單，不用 JSON
# - 顏色/形狀：男=藍色方框；女=粉紅橢圓；過世=灰色並加（殁）
# - 家族樹：配偶相鄰、離婚虛線、子女自婚姻中點垂直往下
# - 兄弟姊妹群組：可把外部成員接到同一原生家庭

import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

st.set_page_config(page_title="家族平台", page_icon="🌳", layout="wide")

# ------------------------------------------------------------------------------
# 資料模型（全部放在 st.session_state.data，避免 alias 問題）
# ------------------------------------------------------------------------------
def _blank():
    return {
        "_seq": 1000,             # 產生 ID 用
        "persons": {},            # pid -> {"name","gender","deceased"}
        "marriages": {},          # mid -> {"p1","p2","divorced":bool}
        "children": defaultdict(list),   # mid -> [child pid,...]
        "parents_of": {},         # child pid -> mid
        "sibling_groups": {},     # gid -> [pid, pid, ...]
    }

if "data" not in st.session_state:
    st.session_state.data = _blank()

DATA = lambda: st.session_state.data  # 只是一個呼叫存取器（非 alias 物件）

def next_id(prefix="p"):
    d = DATA()
    d["_seq"] += 1
    return f"{prefix}{d['_seq']}"

def ensure_person(name, gender="男", deceased=False):
    """若同名不存在就建立；回傳 pid。"""
    d = DATA()
    for pid, p in d["persons"].items():
        if p["name"] == name:
            # 若需要更新性別/過世可在這裡做，但維持單純
            return pid
    pid = next_id("p")
    d["persons"][pid] = {"name": name, "gender": gender, "deceased": bool(deceased)}
    return pid

# ------------------------------------------------------------------------------
# 載入示範資料（陳一郎家族）
# ------------------------------------------------------------------------------
def load_demo():
    st.session_state.data = _blank()  # 直接置換，確保乾淨
    # 之後任何讀寫都透過 DATA() 取用，避免 alias 問題

    yilang = ensure_person("陳一郎", "男")
    exw    = ensure_person("陳前妻", "女")
    curw   = ensure_person("陳妻", "女")
    wangzi = ensure_person("王子",   "男")
    wz_w   = ensure_person("王子妻", "女")
    chenda = ensure_person("陳大",   "男")
    chener = ensure_person("陳二",   "男")
    chensan= ensure_person("陳三",   "男")
    wangs  = ensure_person("王孫",   "男")

    # 現任婚姻
    mid_cur = next_id("m")
    DATA()["marriages"][mid_cur] = {"p1": yilang, "p2": curw, "divorced": False}
    DATA()["children"][mid_cur] = [chenda, chener, chensan]
    for c in DATA()["children"][mid_cur]:
        DATA()["parents_of"][c] = mid_cur

    # 前配偶（離婚）
    mid_ex = next_id("m")
    DATA()["marriages"][mid_ex] = {"p1": yilang, "p2": exw, "divorced": True}
    DATA()["children"][mid_ex] = [wangzi]
    DATA()["parents_of"][wangzi] = mid_ex

    # 王子家
    mid_w = next_id("m")
    DATA()["marriages"][mid_w] = {"p1": wangzi, "p2": wz_w, "divorced": False}
    DATA()["children"][mid_w] = [wangs]
    DATA()["parents_of"][wangs] = mid_w

    st.success("已載入示範資料：陳一郎家族。")

# ------------------------------------------------------------------------------
# UI：頁首快捷按鈕
# ------------------------------------------------------------------------------
c1, c2 = st.columns([1, 1])
with c1:
    if st.button("📘 載入示範（陳一郎家族）", use_container_width=True):
        load_demo()
        st.rerun()

with c2:
    if st.button("📝 馬上輸入自己的資料（清空所有內容）", use_container_width=True, type="primary"):
        st.session_state.data = _blank()
        st.success("已清空，請從『人物』與『關係』開始建立。")
        st.rerun()

st.caption("本圖以 **陳一郎家族譜** 為示範。若要建立自己的家族，請按上方『📝 馬上輸入自己的資料』開始新增成員與關係。")

# ------------------------------------------------------------------------------
# 工具：顯示姓名（過世者加「（殁）」）
# ------------------------------------------------------------------------------
def display_name(pid):
    p = DATA()["persons"][pid]
    nm = p["name"]
    if p.get("deceased"):
        nm += "（殁）"
    return nm

# ------------------------------------------------------------------------------
# Tab 設定
# ------------------------------------------------------------------------------
tab_people, tab_rel, tab_inherit, tab_tree = st.tabs(["人物", "關係", "法定繼承試算", "家族樹"])

# ------------------------------------------------------------------------------
# 人物：新增 / 編修
# ------------------------------------------------------------------------------
with tab_people:
    st.subheader("新增人物")

    with st.form("form_add_person", clear_on_submit=True):
        name = st.text_input("姓名", "")
        gender = st.radio("性別", ["男", "女", "其他"], horizontal=True, index=0)
        deceased = st.checkbox("是否已過世", value=False)
        ok = st.form_submit_button("新增人物", use_container_width=True)
        if ok:
            if not name.strip():
                st.error("請輸入姓名")
            else:
                ensure_person(name.strip(), gender, deceased)
                st.success(f"已新增：{name.strip()}")
                st.rerun()

    st.divider()
    st.subheader("編修人物")
    d = DATA()
    if not d["persons"]:
        st.info("目前尚未有任何人物，請先上方新增。")
    else:
        pid = st.selectbox("選擇要編修的人物", list(d["persons"].keys()),
                           format_func=display_name)
        p = d["persons"][pid]
        with st.form("form_edit_person"):
            new_name = st.text_input("姓名", p["name"])
            gender = st.radio("性別", ["男", "女", "其他"],
                              index={"男":0,"女":1}.get(p["gender"],2),
                              horizontal=True)
            deceased = st.checkbox("是否已過世", value=p.get("deceased", False))
            s = st.form_submit_button("儲存變更", use_container_width=True)
            if s:
                p["name"] = new_name.strip() or p["name"]
                p["gender"] = gender
                p["deceased"] = bool(deceased)
                st.success("已更新")
                st.rerun()

# ------------------------------------------------------------------------------
# 關係：建立婚姻、掛子女、建立兄弟姊妹群組
# ------------------------------------------------------------------------------
with tab_rel:
    st.subheader("建立婚姻（現任 / 離婚）")
    d = DATA()
    if len(d["persons"]) < 2:
        st.info("請先新增至少兩個人，再建立婚姻。")
    else:
        with st.form("form_add_marriage", clear_on_submit=True):
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                p1 = st.selectbox("配偶 A", list(d["persons"].keys()), format_func=display_name)
            with col2:
                p2 = st.selectbox("配偶 B", [pid for pid in d["persons"] if pid != p1],
                                  format_func=display_name)
            with col3:
                divorced = st.checkbox("此婚姻為『離婚/前配偶』", value=False)
            ok = st.form_submit_button("建立婚姻", use_container_width=True)
            if ok:
                mid = next_id("m")
                d["marriages"][mid] = {"p1": p1, "p2": p2, "divorced": divorced}
                st.success(f"已建立婚姻：{display_name(p1)} － {display_name(p2)} （{'離婚' if divorced else '在婚'}）")
                st.rerun()

    st.divider()
    st.subheader("把子女掛到父母（某段婚姻）")
    if not d["marriages"]:
        st.info("目前無婚姻，請先在上方建立一段婚姻。")
    else:
        with st.form("form_attach_children", clear_on_submit=True):
            mid = st.selectbox(
                "選擇父母（某段婚姻）",
                list(d["marriages"].keys()),
                format_func=lambda m: f"{display_name(d['marriages'][m]['p1'])} － {display_name(d['marriages'][m]['p2'])}（{'離婚' if d['marriages'][m]['divorced'] else '在婚'}）"
            )
            candidates = [pid for pid in d["persons"]
                          if d["parents_of"].get(pid) != mid]
            kids = st.multiselect("選擇要掛上的子女", candidates, format_func=display_name)
            ok = st.form_submit_button("掛上子女", use_container_width=True)
            if ok:
                for c in kids:
                    # 從舊婚姻移除（若有）
                    old_mid = d["parents_of"].get(c)
                    if old_mid and c in d["children"].get(old_mid, []):
                        d["children"][old_mid] = [x for x in d["children"][old_mid] if x != c]
                    # 加到新婚姻
                    d["children"][mid].append(c)
                    d["parents_of"][c] = mid
                st.success("已完成掛接子女")
                st.rerun()

    st.divider()
    st.subheader("建立『兄弟姊妹群組』")
    st.caption("當原生父母未建檔時，可把一群手足掛在同一群組；畫圖時會對齊在同一層並以群組中點連到樹。")
    if len(d["persons"]) < 2:
        st.info("請先新增至少兩個人物。")
    else:
        with st.form("form_sibling_group", clear_on_submit=True):
            members = st.multiselect("選擇群組成員（兩人以上）",
                                     list(d["persons"].keys()),
                                     format_func=display_name)
            ok = st.form_submit_button("建立兄弟姊妹群組", use_container_width=True)
            if ok:
                if len(members) < 2:
                    st.error("至少需要兩位成員")
                else:
                    gid = next_id("g")
                    d["sibling_groups"][gid] = list(members)
                    st.success(f"已建立兄弟姊妹群組，共 {len(members)} 人")
                    st.rerun()

# ------------------------------------------------------------------------------
# 法定繼承試算（民法§1138：配偶 + 1~4順位）
# ------------------------------------------------------------------------------
def current_spouses_of(pid):
    """找出『在婚』配偶（可能多段；本系統以一段為主）。"""
    d = DATA()
    result = []
    for mid, m in d["marriages"].items():
        if not m["divorced"] and (m["p1"] == pid or m["p2"] == pid):
            other = m["p2"] if m["p1"] == pid else m["p1"]
            result.append(other)
    return result

def descendants_of(pid):
    """回傳所有子孫（展開多代）。"""
    d = DATA()
    out = set()
    # 找所有孩子起點
    mids = [mid for mid, m in d["marriages"].items() if m["p1"] == pid or m["p2"] == pid]
    q = deque()
    for mid in mids:
        for c in d["children"].get(mid, []):
            out.add(c); q.append(c)
    while q:
        x = q.popleft()
        # x 的孩子
        mids2 = [mid for mid, m in d["marriages"].items() if m["p1"] == x or m["p2"] == x]
        for mid2 in mids2:
            for c2 in d["children"].get(mid2, []):
                if c2 not in out:
                    out.add(c2); q.append(c2)
    return out

def parents_of_person(pid):
    d = DATA()
    pm = d["parents_of"].get(pid)
    if not pm:
        return []
    return [d["marriages"][pm]["p1"], d["marriages"][pm]["p2"]]

def siblings_of(pid):
    """血緣兄弟姊妹（同父母） + 群組兄弟姊妹（若有）"""
    d = DATA()
    sibs = set()

    # 真實父母關係
    pm = d["parents_of"].get(pid)
    if pm:
        parents = (d["marriages"][pm]["p1"], d["marriages"][pm]["p2"])
        for mid, childs in d["children"].items():
            if mid == pm:
                for c in childs:
                    if c != pid:
                        sibs.add(c)

    # 同群組
    for gid, members in d["sibling_groups"].items():
        if pid in members:
            for m in members:
                if m != pid:
                    sibs.add(m)

    return sibs

with tab_inherit:
    st.subheader("法定繼承試算（民法 §1138）")
    d = DATA()
    if not d["persons"]:
        st.info("尚無人物，請先於『人物』『關係』建立資料，或按上方『載入示範』。")
    else:
        dec = st.selectbox("被繼承人", list(d["persons"].keys()), format_func=display_name)
        if dec:
            spouse = current_spouses_of(dec)           # 配偶
            rank1  = list(descendants_of(dec))         # 直系卑親屬
            rank2  = parents_of_person(dec)            # 父母
            rank3  = list(siblings_of(dec))            # 兄弟姊妹
            # 祖父母（若父母都無且未出現在群組中，往上一階；此處示意：找父母的父母）
            rank4 = []
            for p in rank2:
                rank4.extend(parents_of_person(p))
            # 去除 dec 自己與重複
            rank4 = [x for x in set(rank4) if x not in [dec]]

            # 判斷有效順位
            effective = []
            if rank1:
                effective = rank1
                which = "第一順位（直系卑親屬）"
            elif rank2:
                effective = rank2
                which = "第二順位（父母）"
            elif rank3:
                effective = rank3
                which = "第三順位（兄弟姊妹）"
            elif rank4:
                effective = rank4
                which = "第四順位（祖父母）"
            else:
                effective = []
                which = "（無有效順位）"

            # 顯示
            st.markdown("**配偶永遠參與分配**（有配偶即一同繼承）。")
            colA, colB = st.columns([1,2])
            with colA:
                st.write("**被繼承人**")
                st.info(display_name(dec))
                st.write("**配偶**")
                if spouse:
                    st.success("、".join(display_name(s) for s in spouse))
                else:
                    st.warning("（無在婚配偶）")
            with colB:
                st.write(f"**有效順位**：{which}")
                if effective:
                    st.success("、".join(display_name(p) for p in effective))
                else:
                    st.warning("（無符合之繼承人）")

            st.caption("＊本頁先列示順位與繼承人，份額計算可於後續版本加入。")

# ------------------------------------------------------------------------------
# 家族樹（Graphviz）
# ------------------------------------------------------------------------------
def node_style(pid):
    """依性別/過世回傳 Graphviz node 參數。"""
    p = DATA()["persons"][pid]
    shape = "box" if p["gender"] != "女" else "ellipse"
    # 顏色
    if p.get("deceased"):
        fill = "#e5e7eb"  # 灰
        font = "#111827"
    else:
        fill = "#dbeafe" if p["gender"] != "女" else "#ffd6de"
        font = "#0f172a"
    return dict(shape=shape, style="filled", fillcolor=fill, color="#0e2d3b",
                fontcolor=font, penwidth="1.2")

def draw_tree():
    d = DATA()
    if not d["persons"]:
        st.info("請先新增人物與關係，或載入示範。")
        return

    dot = Digraph("family", format="svg", engine="dot")
    dot.graph_attr.update(rankdir="TB", splines="ortho", nodesep="0.35", ranksep="0.65")

    # 先畫人
    for pid in d["persons"]:
        lab = display_name(pid)
        dot.node(pid, lab, **node_style(pid))

    # 夫妻相鄰（婚姻節點）
    for mid, m in d["marriages"].items():
        p1, p2 = m["p1"], m["p2"]
        # 婚姻節點（不可見的小點），用來把孩子連到中點
        j = f"J_{mid}"
        dot.node(j, "", shape="point", width="0.02", color="#1f4b63")
        style = "dashed" if m["divorced"] else "solid"
        dot.edge(p1, j, dir="none", style=style)
        dot.edge(p2, j, dir="none", style=style)
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(p1); s.node(p2)

        # 子女：自婚姻中點往下
        for c in d["children"].get(mid, []):
            dot.edge(j, c, dir="none")

    # 兄弟姊妹群組：用小點連各人，並強制同層
    for gid, members in d["sibling_groups"].items():
        if len(members) < 2: 
            continue
        sg = f"SG_{gid}"
        dot.node(sg, "", shape="point", width="0.02", color="#1f4b63")
        with dot.subgraph() as s:
            s.attr(rank="same")
            for m in members:
                s.node(m)
        for m in members:
            dot.edge(sg, m, dir="none")

    st.graphviz_chart(dot, use_container_width=True)

with tab_tree:
    st.subheader("家族樹（前任在左，本人置中，現任在右；三代分層）")
    draw_tree()

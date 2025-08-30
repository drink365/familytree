
# -*- coding: utf-8 -*-
import streamlit as st, json
from graphviz import Digraph

# -------------------- State & Helpers --------------------
def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {"persons": {}, "marriages": {}, "child_types": {}}
    for k in ("pid_counter","mid_counter"):
        if k not in st.session_state:
            st.session_state[k] = 1

def _new_id(prefix):
    k = "pid_counter" if prefix == "P" else "mid_counter"
    v = st.session_state[k]
    st.session_state[k] = v + 1
    return f"{prefix}{v:03d}"

def _label(p):
    y = []
    if p.get("birth"): y.append(str(p["birth"]))
    if p.get("death"): y.append(str(p["death"]))
    years = "-".join(y)
    return f'{p.get("name","?")}' + (f"\n{years}" if years else "")

# -------------------- Generation Layering --------------------


def _compute_generations(tree):
    """
    Robust generation assignment:
    - Spouses share the same generation.
    - Children get generation = max(parents) + 1.
    - Works with multiple marriages and partial data.
    """
    persons = dict(tree.get("persons", {}))
    marriages = dict(tree.get("marriages", {}))

    # indices
    spouse_of_mid = {mid: list(m.get("spouses", [])) for mid, m in marriages.items()}
    children_of_mid = {mid: list(m.get("children", [])) for mid, m in marriages.items()}

    # build parent sets per child
    parents_of = {}
    for mid, sps in spouse_of_mid.items():
        for c in children_of_mid.get(mid, []):
            parents_of.setdefault(c, set()).update(sps)

    # roots = persons without recorded parents
    depth = {}
    roots = [p for p in persons if p not in parents_of]
    if not roots and persons:
        # if all have parents (data partial), pick arbitrary person as root
        roots = [next(iter(persons))]

    from collections import deque
    q = deque()
    for r in roots:
        depth[r] = 0
        q.append(r)

    # BFS with repeated relaxations (because graphs can be loopy by marriages)
    seen_loops = 0
    while q and seen_loops < 100000:
        p = q.popleft()
        dp = depth[p]

        # Spouses get same layer
        for mid, sps in spouse_of_mid.items():
            if p in sps:
                for s in sps:
                    if s not in depth or depth[s] != dp:
                        if depth.get(s, dp) != dp:
                            depth[s] = dp
                            q.append(s)

                # Children of this marriage: depth = max(parents)+1
                par_layers = [depth.get(s, dp) for s in sps]
                if par_layers:
                    cd = max(par_layers) + 1
                    for c in children_of_mid.get(mid, []):
                        if c not in depth or depth[c] < cd:
                            depth[c] = cd
                            q.append(c)
        seen_loops += 1

    # Any leftover persons get closest reasonable depth 0
    for p in persons:
        depth.setdefault(p, 0)

    return depth


def _graph(tree):
    """
    家族樹繪製規則（符合：同一代橫向、配偶相鄰、子女在父母下方、兄弟姊妹可調順序）
    """
    from graphviz import Digraph

    persons = tree.get("persons", {}) or {}
    marriages = tree.get("marriages", {}) or {}
    child_types = tree.get("child_types", {}) or {}

    # 取得每個人的世代層（同一層會橫向排列）
    try:
        depth = _compute_generations(tree)
    except Exception:
        depth = {pid: 0 for pid in persons}

    # 依層收集人員
    gens = {}
    for pid in persons:
        g = depth.get(pid, 0)
        gens.setdefault(g, []).append(pid)

    # 為了穩定輸出，先固定每層內的初始順序（依建立順序/ID）
    def pid_index(p):
        try:
            return int(str(p)[1:]) if str(p).startswith("P") else 10**9
        except Exception:
            return 10**9
    for g in gens:
        gens[g].sort(key=lambda p: (pid_index(p), persons.get(p,{}).get("name","")))

    # 建立反查：父母層 -> 子女清單（用於排兄弟姊妹）
    children_of_mar = {mid: list(m.get("children", [])) for mid, m in marriages.items()}
    spouses_of_mar = {mid: list(m.get("spouses", [])) for mid, m in marriages.items()}

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", nodesep="0.35", ranksep="0.7")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#f8fbff", color="#8aa5c8",
           fontname="Noto Sans CJK TC, Arial", fontsize="10")
    g.attr("edge", color="#7b8aa8")

    # 先建立所有人物節點
    def _label(p: dict) -> str:
        name = p.get("name","?")
        b = str(p.get("birth","")).strip()
        d = str(p.get("death","")).strip()
        years = ""
        if b and d: years = f"{b}-{d}"
        elif b: years = b
        elif d: years = d
        return f"{name}" + (f"\n{years}" if years else "")

    for pid, pdata in persons.items():
        gender = pdata.get("gender")
        shape = "ellipse" if gender == "女" else "box"
        g.node(pid, label=_label(pdata), shape=shape)

    # --- 關鍵 1：同一代橫向（每層一個 rank=same 子圖 + 隱形鏈固定左右順序） ---
    
    # Create invisible anchors per generation to enforce strict vertical order
    gen_levels = sorted(gens.keys())
    anchors = []
    for lv in gen_levels:
        an = f"_GEN_ANCHOR_{lv}"
        anchors.append(an)
        # each anchor sits with its generation (rank=same)
        with g.subgraph(name=f"rank_anchor_{lv}") as sg_a:
            sg_a.attr(rank="same")
            sg_a.node(an, label="", shape="point", width="0.01")

    # chain anchors top→down to lock rank ordering
    for i in range(len(anchors)-1):
        g.edge(anchors[i], anchors[i+1], style="invis", weight="999", constraint="true")

    for layer, nodes in sorted(gens.items(), key=lambda kv: kv[0]):
        with g.subgraph(name=f"rank_gen_{layer}") as sg:
            sg.attr(rank="same")
            prev = None
            for pid in nodes:
                # 確保節點在此層被提及（Graphviz 會尊重同層排列）
                sg.node(pid)
                # 用 invis 高權重連成一條鏈，鎖住左右順序，減少交錯
                if prev is not None:
                    sg.edge(prev, pid, style="invis", weight="400")
                prev = pid

    # --- 關鍵 2：配偶相鄰（同層 + 中間婚姻點 + 可見/虛線婚姻邊） ---
    for mid, m in marriages.items():
        sps = spouses_of_mar.get(mid, [])
        if not sps:
            continue
        # 婚姻點：用作連接孩子的中繼
        g.node(mid, label="", shape="point", width="0.01")

        # 配偶與婚姻點同層（使用父母其一的層數）
        if sps:
            parent_layer = depth.get(sps[0], 0)

            with g.subgraph(name=f"rank_mar_{mid}") as sg:
                sg.attr(rank="same")
                # 把配偶與 mid 拉在同一層，並用 invis 緊密相鄰
                prev = None
                order = list(dict.fromkeys(sps[:2]))  # 只保證前兩位相鄰（常見情境）
                # 也把 mid 放中間，s1 - mid - s2
                if len(order) == 1:
                    chain = [order[0], mid]
                elif len(order) >= 2:
                    chain = [order[0], mid, order[1]]
                else:
                    chain = [mid]

                for n in chain:
                    sg.node(n)
                    if prev is not None:
                        sg.edge(prev, n, style="invis", weight="500")
                    prev = n

            # 可見婚姻關係（實線/虛線）
            if len(sps) >= 2:
                s1, s2 = sps[0], sps[1]
                style = "dashed" if m.get("divorced") else "solid"
                g.edge(s1, s2, dir="none", constraint="true", weight="250", style=style)

            # 多配偶時，鄰接者相連，保持群聚
            if len(sps) > 2:
                for i in range(len(sps)-1):
                    g.edge(sps[i], sps[i+1], dir="none", constraint="true", weight="120", style="solid")

    # --- 關鍵 3：子女在父母下方 + 兄弟姊妹可固定左右順序 ---
    #    子女都從 mid（婚姻點）往下連，兄弟姊妹用 invis 鏈固定左右
    HIDE = {"生","bio","親生"}
    for mid, kids in children_of_mar.items():
        if not kids:
            continue

        # 以父母中的最大層 + 1 作為子女層
        sps = spouses_of_mar.get(mid, [])
        parent_layers = [depth.get(s, 0) for s in sps] or [0]
        child_layer = max(parent_layers) + 1

        # 將所有子女宣告在同一層（橫向排列）
        with g.subgraph(name=f"rank_kids_{mid}") as sg:
            sg.attr(rank="same")
            prev = None
            for cid in kids:
                # 若原本 depth 計算不一致，這邊只強制 rank，不直接改 depth 字典
                sg.node(cid)
                if prev is not None:
                    sg.edge(prev, cid, style="invis", weight="350")
                prev = cid

        # 將 mid -> child 的連線畫出來（可帶標籤）
        ctype_map = child_types.get(mid, {}) or {}
        for cid in kids:
            lbl = (ctype_map.get(cid, "") or "").strip()
            if lbl and lbl not in HIDE:
                g.edge(mid, cid, label=lbl, constraint="true")
            else:
                g.edge(mid, cid, constraint="true")

    return g


def render():
    _init_state()
    st.title("🌳 家族樹")
    st.caption("➊ 新增人物 → ➋ 建立婚姻 → ➌ 加入子女 → ➍ 匯出/匯入 JSON")

    t = st.session_state.tree
    # 匯入後的提示
    if st.session_state.get("ft_flash_msg"):
        st.success(st.session_state.pop("ft_flash_msg"))

    with st.expander("① 人物管理", expanded=True):
        cols = st.columns([2,1,1,1,1])
        name = cols[0].text_input("姓名 *", key="ft_name")
        gender = cols[1].selectbox("性別", ["男","女"], index=0, key="ft_gender")
        birth = cols[2].text_input("出生年", key="ft_birth", placeholder="1970")
        death = cols[3].text_input("逝世年", key="ft_death", placeholder="")
        if cols[4].button("➕ 新增人物", key="btn_add_person", use_container_width=True):
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _new_id("P")
                gender_code = {"男": "M", "女": "F"}.get(gender, "?")
                t["persons"][pid] = {"name": name.strip(), "gender": gender_code, "birth": birth.strip(), "death": death.strip()}
                st.success(f"已新增 {name}（{pid}）")

        if t["persons"]:
            pid_del = st.selectbox(
                "選擇人物以刪除（可選）",
                [""] + list(t["persons"].keys()),
                format_func=lambda x: x if not x else f'{x}｜{t["persons"].get(x,{}).get("name","?")}'
            )
            if st.button("🗑️ 刪除所選人物", key="btn_del_person"):
                if pid_del and pid_del in t["persons"]:
                    for mid, m in list(t["marriages"].items()):
                        if pid_del in m.get("spouses", []):
                            del t["marriages"][mid]; t.get("child_types", {}).pop(mid, None)
                        elif pid_del in m.get("children", []):
                            m["children"] = [c for c in m["children"] if c != pid_del]
                            t.get("child_types", {}).get(mid, {}).pop(pid_del, None)
                    del t["persons"][pid_del]
                    st.success("已刪除")

    with st.expander("② 婚姻關係", expanded=True):
        people = list(t["persons"].keys())
        if not people:
            st.info("請先新增至少一位人物")
        else:
            c1,c2,c3 = st.columns(3)
            a = c1.selectbox("配偶 A", [""]+people, format_func=lambda x: x if not x else f'{x}｜{t["persons"][x]["name"]}')
            b = c2.selectbox("配偶 B", [""]+people, format_func=lambda x: x if not x else f'{x}｜{t["persons"][x]["name"]}')
            if c3.button("💍 建立婚姻", key="btn_add_marriage"):
                if not a or not b or a == b:
                    st.warning("請選擇兩位不同人物")
                else:
                    mid = _new_id("M")
                    t["marriages"][mid] = {"spouses": [a,b], "children": [], "divorced": False}
                    t["child_types"][mid] = {}
                    st.success(f"已建立婚姻 {mid}")

        if t["marriages"]:
            def safe_format_marriage(x):
                spouses = t["marriages"].get(x, {}).get("spouses", [])
                names = [t["persons"].get(pid, {}).get("name", f"未知成員{pid}") for pid in spouses]
                return f"{x}｜" + " × ".join(names) if names else f"{x}｜（尚無配偶）"

            mid = st.selectbox("選擇婚姻以新增子女", list(t["marriages"].keys()), format_func=safe_format_marriage)
            # 離婚狀態
            if mid:
                div_ck = st.checkbox("該婚姻已離婚？", value=bool(t["marriages"][mid].get("divorced", False)))
                t["marriages"][mid]["divorced"] = bool(div_ck)
            if mid:
                c1,c2,c3 = st.columns([2,1,1])
                child = c1.selectbox(
                    "子女",
                    [""] + [p for p in t["persons"].keys() if p not in t["marriages"][mid]["children"]],
                    format_func=lambda x: x if not x else f'{x}｜{t["persons"][x]["name"]}'
                )
                ctype = c2.selectbox("關係", ["生","繼","認領","其他","bio"], index=0, key="sel_ctype")
                if c3.button("👶 新增子女", key="btn_add_child"):
                    if not child:
                        st.warning("請選擇子女")
                    else:
                        t["marriages"][mid]["children"].append(child)
                        t["child_types"].setdefault(mid, {})[child] = ctype
                        st.success("已新增子女")

        # ②-1 子女排序（減少交錯）
    with st.expander("②-1 子女排序（減少交錯）", expanded=False):
        t = st.session_state.tree
        marriages = t.get("marriages", {})
        persons = t.get("persons", {})
        if not marriages:
            st.info("尚未建立婚姻關係")
        else:
            for mid, m in marriages.items():
                kids = list(m.get("children", []))
                if len(kids) < 2:
                    continue
                st.caption(f"婚姻 {mid}｜" + " × ".join(persons.get(pid, {}).get("name", pid) for pid in m.get("spouses", [])))
                for idx, cid in enumerate(kids):
                    ccol1, ccol2, ccol3, ccol4 = st.columns([4,1,1,1])
                    ccol1.write(f"{idx+1}. {cid}｜{persons.get(cid,{}).get('name',cid)}")
                    if ccol2.button("⬅️ 左移", key=f"kid_left_{mid}_{idx}") and idx>0:
                        kids[idx-1], kids[idx] = kids[idx], kids[idx-1]
                    if ccol3.button("➡️ 右移", key=f"kid_right_{mid}_{idx}") and idx < len(kids)-1:
                        kids[idx], kids[idx+1] = kids[idx+1], kids[idx]
                    if ccol4.button("⟲ 反轉", key=f"kid_rev_{mid}_{idx}"):
                        kids = list(reversed(kids))
                    # write-back after any click
                    m["children"] = kids
                st.divider()

    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t), use_container_width=True, height=900)


    

    with st.expander("④ 匯入 / 匯出", expanded=True):
        # 匯出
        st.download_button(
            "⬇️ 下載 JSON",
            data=json.dumps(t, ensure_ascii=False, indent=2),
            file_name="family_tree.json",
            mime="application/json",
            key="btn_dl_json",
        )

        # 匯入（先上傳，再按「執行匯入」）
        upl = st.file_uploader("選擇 JSON 檔", type=["json"], key="ft_upload_json")
        do_import = st.button("⬆️ 執行匯入", use_container_width=True, key="btn_do_import")

        if do_import:
            if upl is None:
                st.warning("請先選擇要匯入的 JSON 檔。")
            else:
                try:
                    raw = upl.getvalue()
                    import hashlib
                    md5 = hashlib.md5(raw).hexdigest()
                    if st.session_state.get("ft_last_import_md5") == md5:
                        st.info("此檔已匯入過。若要重新匯入，請先更改檔案內容或重新選擇檔案。")
                    else:
                        data = json.loads(raw.decode("utf-8"))
                        if not isinstance(data, dict):
                            raise ValueError("檔案格式錯誤（非 JSON 物件）")
                        data.setdefault("persons", {})
                        data.setdefault("marriages", {})
                        data.setdefault("child_types", {})

                        # 重新設定計數器，避免新建 ID 衝突
                        def _max_id(prefix, keys):
                            mx = 0
                            for k in keys:
                                if isinstance(k, str) and k.startswith(prefix):
                                    try:
                                        mx = max(mx, int(k[len(prefix):] or "0"))
                                    except Exception:
                                        pass
                            return mx

                        st.session_state.tree = data
                        st.session_state["ft_last_import_md5"] = md5
                        st.session_state["pid_counter"] = _max_id("P", data["persons"].keys()) + 1
                        st.session_state["mid_counter"] = _max_id("M", data["marriages"].keys()) + 1

                        st.session_state["ft_flash_msg"] = "已匯入"
                        st.rerun()
                except Exception as e:
                    st.error(f"匯入失敗：{e}")
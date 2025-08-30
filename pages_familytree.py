
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
    """Assign generation layers so that spouses share a rank and children are the next rank."""
    persons = set(tree.get("persons", {}).keys())
    marriages = tree.get("marriages", {})

    # Build indices
    spouse_to_mids = {}
    parents_of = {}
    for mid, m in marriages.items():
        for s in m.get("spouses", []):
            spouse_to_mids.setdefault(s, set()).add(mid)
        for c in m.get("children", []):
            parents_of.setdefault(c, set()).update(m.get("spouses", []))

    # Roots: those without parents
    from collections import deque
    depth = {}
    q = deque()

    roots = [p for p in persons if p not in parents_of]
    for r in roots:
        depth[r] = 0
        q.append(r)

    # If no roots (cycle/only children recorded), seed with arbitrary node
    if not q and persons:
        anyp = next(iter(persons))
        depth[anyp] = 0
        q.append(anyp)

    while q:
        p = q.popleft()
        d = depth[p]

        # Spouses of p stay same layer
        for mid in spouse_to_mids.get(p, []):
            spouses = marriages.get(mid, {}).get("spouses", [])
            # sync spouse depth
            for s in spouses:
                if s == p: 
                    continue
                if depth.get(s) != d:
                    depth[s] = d
                    q.append(s)

            # children placed one layer below parents
            par_depths = [depth.get(s, d) for s in spouses if s in depth]
            if par_depths:
                cd = max(par_depths) + 1
                for c in marriages.get(mid, {}).get("children", []):
                    if depth.get(c, -10) < cd:
                        depth[c] = cd
                        q.append(c)

    # Default any missing
    for p in persons:
        depth.setdefault(p, 0)
    return depth


# -------------------- Graph Builder (layered) --------------------


def _graph(tree):
    depth = _compute_generations(tree)

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", nodesep="0.35", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#f8fbff", color="#8aa5c8",
           fontname="Noto Sans CJK TC, Arial", fontsize="10")
    g.attr("edge", color="#7b8aa8")

    # Persons grouped by generation
    by_depth = {}
    for pid in tree.get("persons", {}):
        by_depth.setdefault(depth.get(pid, 0), []).append(pid)

    for d, nodes in sorted(by_depth.items()):
        with g.subgraph(name=f"rank_{d}") as sg:
            sg.attr(rank="same")
            for pid in nodes:
                gender = tree["persons"].get(pid, {}).get("gender")
                shape = "ellipse" if gender == "F" else "box"
                sg.node(pid, label=_label(tree["persons"][pid]), shape=shape)

    # Draw marriages: spouse edge (solid/dashed) and hidden mid node between spouses (for children)
    for mid, m in tree.get("marriages", {}).items():
        spouses = list(m.get("spouses", []))
        if not spouses:
            continue
        # ensure rank: spouses + mid same layer
        with g.subgraph(name=f"rank_mid_{mid}") as sg:
            sg.attr(rank="same")
            # Place mid node (hidden point)
            sg.node(mid, label="", shape="point", width="0.01")

            # Create invisible edges to order: s1 -> mid -> s2
            if len(spouses) >= 2:
                s1, s2 = spouses[0], spouses[1]
                sg.edge(s1, mid, style="invis", weight="200")
                sg.edge(mid, s2, style="invis", weight="200")
                # ## SPOUSE_ORDER: enforce left-to-right spouse order to reduce crossings
                if len(spouses) >= 2:
                    for i in range(len(spouses)-1):
                        sg.edge(spouses[i], spouses[i+1], style="invis", weight="150", constraint="true")
    

        # Visible horizontal line between first two spouses
        if len(spouses) >= 2:
            s1, s2 = spouses[0], spouses[1]
            style = "dashed" if m.get("divorced") else "solid"
            g.edge(s1, s2, dir="none", constraint="true", weight="200", style=style)

        # For any additional spouses, connect them near mid with invisible ordering,
        # and draw visible edges pairing sequentially to keep adjacency.
        if len(spouses) > 2:
            for i in range(1, len(spouses)-1):
                a, b = spouses[i], spouses[i+1]
                g.edge(a, b, dir="none", constraint="true", weight="150", style="solid")  # assume married

        # Children edges
        child_types = tree.get("child_types", {})
        HIDE_LABELS = {"生", "bio", "親生"}
        for c in m.get("children", []):
            if c in tree.get("persons", {}):
                ctype = (child_types.get(mid, {}) or {}).get(c, "")
                lbl = "" if (ctype or "").strip() in HIDE_LABELS else ctype
                if lbl:
                    g.edge(mid, c, label=lbl)
                else:
                    g.edge(mid, c)
        # Enforce sibling left-to-right order to reduce edge crossings
        kids = list(m.get("children", []))
        if len(kids) >= 2:
            with g.subgraph() as kg:
                kg.attr(rank="same")
                for i in range(len(kids)-1):
                    kg.edge(kids[i], kids[i+1], style="invis", weight="50", constraint="true")
        

    return g



# -------------------- Page Render --------------------
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

            st.markdown("**配偶順序（可調整）**")
            if mid:
                sp = t["marriages"][mid].get("spouses", [])
                if len(sp) <= 1:
                    st.info("此婚姻目前只有一位配偶。")
                else:
                    for i, sid in enumerate(sp):
                        cols = st.columns([6,1,1,1,1])
                        cols[0].write(f"{i+1}. {sid}｜" + t["persons"].get(sid, {}).get("name","?"))
                        if cols[1].button("↑", key=f"sp_up_{mid}_{sid}") and i>0:
                            sp[i-1], sp[i] = sp[i], sp[i-1]
                            t["marriages"][mid]["spouses"] = sp
                            st.rerun()
                        if cols[2].button("↓", key=f"sp_dn_{mid}_{sid}") and i < len(sp)-1:
                            sp[i+1], sp[i] = sp[i], sp[i+1]
                            t["marriages"][mid]["spouses"] = sp
                            st.rerun()
                        if cols[3].button("置頂", key=f"sp_top_{mid}_{sid}") and i>0:
                            moved = sp.pop(i)
                            sp.insert(0, moved)
                            t["marriages"][mid]["spouses"] = sp
                            st.rerun()
                        if cols[4].button("置底", key=f"sp_bot_{mid}_{sid}") and i < len(sp)-1:
                            moved = sp.pop(i)
                            sp.append(moved)
                            t["marriages"][mid]["spouses"] = sp
                            st.rerun()
            st.divider()
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

            st.divider()
            st.markdown("**子女順序（可調整以減少交錯）**")
            if mid:
                kids = t["marriages"][mid].get("children", [])
                if not kids:
                    st.info("此婚姻目前沒有子女。")
                else:
                    for i, kid in enumerate(kids):
                        cols = st.columns([6,1,1,1,1])
                        cols[0].write(f"{i+1}. {kid}｜" + t["persons"].get(kid, {}).get("name","?"))
                        if cols[1].button("↑", key=f"up_{mid}_{kid}") and i>0:
                            kids[i-1], kids[i] = kids[i], kids[i-1]
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if cols[2].button("↓", key=f"dn_{mid}_{kid}") and i < len(kids)-1:
                            kids[i+1], kids[i] = kids[i], kids[i+1]
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if cols[3].button("置頂", key=f"top_{mid}_{kid}") and i>0:
                            moved = kids.pop(i)
                            kids.insert(0, moved)
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
                        if cols[4].button("置底", key=f"bot_{mid}_{kid}") and i < len(kids)-1:
                            moved = kids.pop(i)
                            kids.append(moved)
                            t["marriages"][mid]["children"] = kids
                            st.rerun()
    
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))


    

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
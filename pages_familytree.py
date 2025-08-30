# pages_familytree.py
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
    st.session_state[k] += 1
    return f"{prefix}{v}"

def _label(p: dict) -> str:
    y = []
    b = str(p.get("birth","")).strip()
    d = str(p.get("death","")).strip()
    if b: y.append(b)
    if d: y.append(d)
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

# -------------------- Graph Builder (layered with crossing minimization) --------------------
def _graph(tree):
    depth = _compute_generations(tree)

    # ---- compute left-to-right order within each generation to reduce crossings ----
    marriages = tree.get("marriages", {})
    persons = tree.get("persons", {})
    # persons by depth
    by_depth = {}
    for pid in persons:
        by_depth.setdefault(depth.get(pid, 0), []).append(pid)

    # initial order: stable by creation id then name
    def pid_index(p):
        try:
            return int(str(p)[1:]) if str(p).startswith("P") else 10**9
        except:
            return 10**9
    for d in by_depth:
        by_depth[d].sort(key=lambda x: (pid_index(x), persons.get(x, {}).get("name","")))

    # helpers
    children_of = {p: [] for p in persons}
    parents_of  = {p: [] for p in persons}
    spouse_sets = {p: set() for p in persons}
    for mid, m in marriages.items():
        sps = list(m.get("spouses", []))
        for s in sps:
            spouse_sets.setdefault(s, set()).update([x for x in sps if x!=s])
        chs = list(m.get("children", []))
        for s in sps:
            children_of.setdefault(s, []).extend(chs)
        for c in chs:
            parents_of.setdefault(c, []).extend(sps)

    # iterative barycenter sweeps
    def sweep_down(by_depth):
        positions = {p:i for d in by_depth for i,p in enumerate(by_depth[d])}
        new = {}
        for d in sorted(by_depth.keys()):
            layer = by_depth[d]
            scored=[]
            for p in layer:
                par = parents_of.get(p, [])
                if par:
                    pos = [positions.get(pp, 0) for pp in par]
                    key = sum(pos)/len(pos)
                else:
                    key = positions.get(p, 0)
                scored.append((key, p))
            scored.sort(key=lambda t: (t[0], pid_index(t[1])))
            new[d]=[p for _,p in scored]
            positions.update({p:i for i,p in enumerate(new[d])})
        return new

    def sweep_up(by_depth):
        positions = {p:i for d in by_depth for i,p in enumerate(by_depth[d])}
        new = {}
        for d in sorted(by_depth.keys(), reverse=True):
            layer = by_depth[d]
            scored=[]
            for p in layer:
                kids = [c for c in children_of.get(p, []) if depth.get(c, d+1)>=d]
                vals=[]
                if kids:
                    vals.extend(positions.get(c, 0) for c in kids)
                for s in spouse_sets.get(p, []):
                    vals.append(positions.get(s, positions.get(p,0)))
                key = sum(vals)/len(vals) if vals else positions.get(p, 0)
                scored.append((key, p))
            scored.sort(key=lambda t: (t[0], pid_index(t[1])))
            new[d]=[p for _,p in scored]
            positions.update({p:i for i,p in enumerate(new[d])})
        return new

    for _ in range(3):
        by_depth = sweep_down(by_depth)
        by_depth = sweep_up(by_depth)

    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", nodesep="0.35", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#f8fbff", color="#8aa5c8",
           fontname="Noto Sans CJK TC, Arial", fontsize="10")
    g.attr("edge", color="#7b8aa8")

    # persons per generation + invisible chain to enforce order
    for d, nodes in sorted(by_depth.items()):
        with g.subgraph(name=f"rank_{d}") as sg:
            sg.attr(rank="same")
            prev=None
            for pid in nodes:
                gender = tree["persons"].get(pid, {}).get("gender")
                shape = "ellipse" if gender == "F" else "box"
                sg.node(pid, label=_label(tree["persons"][pid]), shape=shape)
                if prev is not None:
                    sg.edge(prev, pid, style="invis", weight="300")
                prev = pid

    # marriages and children edges
    for mid, m in tree.get("marriages", {}).items():
        spouses = list(m.get("spouses", []))
        if not spouses:
            continue
        with g.subgraph(name=f"rank_mid_{mid}") as sg:
            sg.attr(rank="same")
            sg.node(mid, label="", shape="point", width="0.01")
            if len(spouses) >= 2:
                s1, s2 = spouses[0], spouses[1]
                sg.edge(s1, mid, style="invis", weight="200")
                sg.edge(mid, s2, style="invis", weight="200")

        if len(spouses) >= 2:
            s1, s2 = spouses[0], spouses[1]
            style = "dashed" if m.get("divorced") else "solid"
            g.edge(s1, s2, dir="none", constraint="true", weight="200", style=style)

        if len(spouses) > 2:
            for i in range(1, len(spouses)-1):
                a, b = spouses[i], spouses[i+1]
                g.edge(a, b, dir="none", constraint="true", weight="150", style="solid")

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
                t["persons"][pid] = {"name": name.strip(), "gender": gender, "birth": birth.strip(), "death": death.strip()}
                st.success(f"已新增人物 {pid}")

        if t["persons"]:
            st.write("目前人物：")
            for pid, p in list(t["persons"].items()):
                cols = st.columns([2,1,1,1,1])
                cols[0].text_input("姓名", p.get("name",""), key=f"{pid}_name")
                cols[1].selectbox("性別", ["男","女"], index= 0 if p.get("gender","男")=="男" else 1, key=f"{pid}_gender")
                cols[2].text_input("出生年", p.get("birth",""), key=f"{pid}_birth")
                cols[3].text_input("逝世年", p.get("death",""), key=f"{pid}_death")
                if cols[4].button("🗑️ 刪除", key=f"btn_del_{pid}"):
                    pid_del = pid
                    # remove pid from marriages & children types
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
                return f'{x}｜' + " × ".join(names)

            st.divider()
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

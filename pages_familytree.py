
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
    for pid, p in tree.get("persons", {}).items():
        by_depth.setdefault(depth.get(pid, 0), []).append(pid)

    for d, nodes in sorted(by_depth.items()):
        with g.subgraph(name=f"rank_{d}") as sg:
            sg.attr(rank="same")
            for pid in nodes:
                gender = tree["persons"].get(pid, {}).get("gender")
                shape = "ellipse" if gender == "F" else "box"
                sg.node(pid, label=_label(tree["persons"][pid]), shape=shape)

    # Marriage nodes placed at the same rank as spouses
    for mid, m in tree.get("marriages", {}).items():
        # Determine rank from first known spouse
        ranks = [depth.get(s, 0) for s in m.get("spouses", [])]
        r = min(ranks) if ranks else 0
        with g.subgraph(name=f"rank_mid_{mid}") as sg:
            sg.attr(rank="same")
            sg.node(mid, label="", shape="point", width="0.01")

        for s in m.get("spouses", []):
            if s in tree.get("persons", {}):
                g.edge(s, mid, dir="none")

    # Children edges (with optional labels)
    child_types = tree.get("child_types", {})
    HIDE_LABELS = {"生", "bio", "親生"}
    for mid, m in tree.get("marriages", {}).items():
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

    with st.expander("① 人物管理", expanded=True):
        cols = st.columns([2,1,1,1,1])
        name = cols[0].text_input("姓名 *", key="ft_name")
        gender = cols[1].selectbox("性別", ["不確定","男","女"], index=0, key="ft_gender")
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
                    t["marriages"][mid] = {"spouses": [a,b], "children": []}
                    t["child_types"][mid] = {}
                    st.success(f"已建立婚姻 {mid}")

        if t["marriages"]:
            def safe_format_marriage(x):
                spouses = t["marriages"].get(x, {}).get("spouses", [])
                names = [t["persons"].get(pid, {}).get("name", f"未知成員{pid}") for pid in spouses]
                return f"{x}｜" + " × ".join(names) if names else f"{x}｜（尚無配偶）"

            mid = st.selectbox("選擇婚姻以新增子女", list(t["marriages"].keys()), format_func=safe_format_marriage)
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

    with st.expander("④ 匯入 / 匯出", expanded=False):
        col1,col2 = st.columns(2)
        col1.download_button("⬇️ 下載 JSON", data=json.dumps(t, ensure_ascii=False, indent=2),
                             file_name="family_tree.json", mime="application/json", key="btn_dl_json")
        upl = col2.file_uploader("或：上傳 JSON 匯入", type=["json"])
        if upl is not None:
            try:
                data = json.loads(upl.read().decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("檔案格式錯誤")
                data.setdefault("persons", {}); data.setdefault("marriages", {}); data.setdefault("child_types", {})
                st.session_state.tree = data
                st.success("已匯入")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

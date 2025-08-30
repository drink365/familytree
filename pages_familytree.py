
# -*- coding: utf-8 -*-
import streamlit as st, json
from graphviz import Digraph

TITLE = "🌳 家族樹"

def _init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {
            "persons": {},          # pid -> {"name":..., "gender":"M/F/?", "birth":"", "death":""}
            "marriages": {},        # mid -> {"spouses":[pid1,pid2], "children":[]}
            "child_types": {}       # mid -> {child_pid: "生/繼/認領/其他"}
        }
    if "pid_counter" not in st.session_state:
        st.session_state.pid_counter = 1
    if "mid_counter" not in st.session_state:
        st.session_state.mid_counter = 1

def _new_pid():
    pid = f"P{st.session_state.pid_counter:03d}"
    st.session_state.pid_counter += 1
    return pid

def _new_mid():
    mid = f"M{st.session_state.mid_counter:03d}"
    st.session_state.mid_counter += 1
    return mid

def _label(p):
    y = []
    if p.get("birth"): y.append(str(p["birth"]))
    if p.get("death"): y.append(str(p["death"]))
    years = "-".join(y) if y else ""
    return f'{p.get("name","?")}\\n{years}'.strip()

def _graph(tree: dict) -> Digraph:
    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", nodesep="0.35", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#f8fbff", color="#8aa5c8", fontname="Noto Sans CJK TC, Arial", fontsize="10")
    g.attr("edge", color="#7b8aa8")
    # Draw persons
    for pid, p in tree["persons"].items():
        label = _label(p)
        shape = "box"
        if p.get("gender") == "M": shape = "box"
        elif p.get("gender") == "F": shape = "ellipse"
        g.node(pid, label=label, shape=shape)
    # Draw marriages as invisible point nodes to connect parents to children
    for mid, m in tree["marriages"].items():
        spouses = m.get("spouses", [])
        if len(spouses) == 2:
            s1, s2 = spouses
            g.node(mid, label="", shape="point", width="0.01")
            g.edge(s1, mid, dir="none")
            g.edge(s2, mid, dir="none")
            # children edges
            for c in m.get("children", []):
                lbl = ""
                ctype = tree.get("child_types", {}).get(mid, {}).get(c, "")
                if ctype and ctype != "生":
                    lbl = ctype
                g.edge(mid, c, label=lbl)
        elif len(spouses) == 1:
            s1 = spouses[0]
            g.node(mid, label="", shape="point", width="0.01")
            g.edge(s1, mid, dir="none")
            for c in m.get("children", []):
                g.edge(mid, c)
    return g

def _export_json(tree: dict) -> str:
    return json.dumps(tree, ensure_ascii=False, indent=2)

def _import_json(text: str) -> dict:
    data = json.loads(text)
    assert "persons" in data and "marriages" in data, "格式不正確"
    data.setdefault("child_types", {})
    return data

def render():
    _init_state()
    st.title(TITLE)
    st.caption("➊ 建立人物 → ➋ 建立婚姻關係 → ➌ 新增子女 → ➍ 下載 JSON 備份")
    tree = st.session_state.tree

    with st.expander("① 人物管理", expanded=True):
        cols = st.columns([2,1,1,1,1])
        name = cols[0].text_input("姓名 *", key="ft_name")
        gender = cols[1].selectbox("性別", ["?", "M", "F"], index=0, key="ft_gender")
        birth = cols[2].text_input("出生年", key="ft_birth", placeholder="1970")
        death = cols[3].text_input("逝世年", key="ft_death", placeholder="")
        if cols[4].button("➕ 新增人物", use_container_width=True):
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _new_pid()
                tree["persons"][pid] = {"name": name.strip(), "gender": gender, "birth": birth.strip(), "death": death.strip()}
                st.success(f"已新增：{name}（{pid}）")

        if tree["persons"]:
            st.write("目前人物清單：")
            pid = st.selectbox("選擇人物以刪除（可選）", [""] + list(tree["persons"].keys()), format_func=lambda x: x if not x else f'{x}｜{tree["persons"][x]["name"]}')
            if st.button("🗑️ 刪除所選人物"):
                if pid and pid in tree["persons"]:
                    # 同步移除婚姻與子女關聯
                    for mid, m in list(tree["marriages"].items()):
                        if pid in m.get("spouses", []):
                            del tree["marriages"][mid]
                            tree.get("child_types", {}).pop(mid, None)
                        else:
                            if pid in m.get("children", []):
                                m["children"] = [c for c in m["children"] if c != pid]
                                if mid in tree.get("child_types", {}):
                                    tree["child_types"][mid].pop(pid, None)
                    del tree["persons"][pid]
                    st.success("已刪除")

    with st.expander("② 婚姻關係", expanded=True):
        persons = list(tree["persons"].keys())
        if len(persons) < 1:
            st.info("請先新增至少一位人物")
        else:
            c1, c2, c3 = st.columns(3)
            a = c1.selectbox("配偶 A", [""] + persons, format_func=lambda x: x if not x else f'{x}｜{tree["persons"][x]["name"]}')
            b = c2.selectbox("配偶 B", [""] + persons, format_func=lambda x: x if not x else f'{x}｜{tree["persons"][x]["name"]}')
            if c3.button("💍 建立婚姻"):
                if not a or not b or a == b:
                    st.warning("請選擇兩位不同人物")
                else:
                    mid = _new_mid()
                    tree["marriages"][mid] = {"spouses": [a,b], "children": []}
                    tree["child_types"][mid] = {}
                    st.success(f"已建立婚姻 {mid}")

        if tree["marriages"]:
            st.write("目前婚姻（點選以新增子女）：")
            mid = st.selectbox("選擇婚姻", list(tree["marriages"].keys()), format_func=lambda x: f'{x}｜' + " × ".join(tree["persons"][pid]["name"] for pid in tree["marriages"][x]["spouses"]))
            if mid:
                c1, c2, c3 = st.columns([2,1,1])
                child = c1.selectbox("子女", [""] + [p for p in tree["persons"].keys() if p not in tree["marriages"][mid]["children"]], format_func=lambda x: x if not x else f'{x}｜{tree["persons"][x]["name"]}')
                ctype = c2.selectbox("關係", ["生","繼","認領","其他"], index=0)
                if c3.button("👶 新增子女"):
                    if not child:
                        st.warning("請選擇子女")
                    else:
                        tree["marriages"][mid]["children"].append(child)
                        tree["child_types"].setdefault(mid, {})[child] = ctype
                        st.success("已新增子女")

    with st.expander("③ 家族樹視覺化", expanded=True):
        g = _graph(tree)
        st.graphviz_chart(g)

    with st.expander("④ 匯入 / 匯出", expanded=False):
        col1, col2 = st.columns(2)
        col1.download_button("⬇️ 下載 JSON", data=_export_json(tree), file_name="family_tree.json", mime="application/json")
        uploaded = col2.file_uploader("或：上傳 JSON 匯入", type=["json"])
        if uploaded is not None:
            try:
                data = _import_json(uploaded.read().decode("utf-8"))
                st.session_state.tree = data
                st.success("已匯入")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

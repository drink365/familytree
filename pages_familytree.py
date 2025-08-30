# -*- coding: utf-8 -*-
import streamlit as st, json
from graphviz import Digraph

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
    return f'{p.get("name","?")}\\n{"-".join(y)}'.strip()

def _graph(tree):
    g = Digraph("G", format="svg")
    g.attr(rankdir="TB", nodesep="0.35", ranksep="0.6")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#f8fbff", color="#8aa5c8",
           fontname="Noto Sans CJK TC, Arial", fontsize="10")
    g.attr("edge", color="#7b8aa8")
    for pid, p in tree["persons"].items():
        shape = "ellipse" if p.get("gender") == "F" else "box"
        g.node(pid, label=_label(p), shape=shape)
    for mid, m in tree["marriages"].items():
        spouses = m.get("spouses", [])
        g.node(mid, label="", shape="point", width="0.01")
        for s in spouses:
            if s in tree["persons"]:
                g.edge(s, mid, dir="none")
        for c in m.get("children", []):
            if c in tree["persons"]:
                ctype = tree.get("child_types", {}).get(mid, {}).get(c, "")
                g.edge(mid, c, label=(ctype if ctype and ctype != "生" else ""))
    return g

def render():
    _init_state()
    st.title("🌳 家族樹")
    st.caption("➊ 新增人物 → ➋ 建立婚姻 → ➌ 加入子女 → ➍ 匯出/匯入 JSON")

    t = st.session_state.tree

    # === ① 人物管理 ===
    with st.expander("① 人物管理", expanded=True):
        cols = st.columns([2,1,1,1,1])
        name = cols[0].text_input("姓名 *", key="ft_name")
        gender = cols[1].selectbox("性別", ["?","M","F"], index=0, key="ft_gender")
        birth = cols[2].text_input("出生年", key="ft_birth", placeholder="1970")
        death = cols[3].text_input("逝世年", key="ft_death", placeholder="")
        if cols[4].button("➕ 新增人物", key="btn_add_person", use_container_width=True):
            if not name.strip():
                st.warning("請輸入姓名")
            else:
                pid = _new_id("P")
                t["persons"][pid] = {"name": name.strip(), "gender": gender, "birth": birth.strip(), "death": death.strip()}
                st.success(f"已新增 {name}（{pid}）")

        # 刪除人物
        if t["persons"]:
            pid_del = st.selectbox("選擇人物以刪除（可選）", [""] + list(t["persons"].keys()),
                                   format_func=lambda x: x if not x else f'{x}｜{t["persons"][x]["name"]}')
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

    # === ② 婚姻關係 ===
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

        # === 子女管理 ===
        if t["marriages"]:
            def safe_format_marriage(x):
                spouses = t["marriages"].get(x, {}).get("spouses", [])
                names = [t["persons"].get(pid, {}).get("name", f"未知成員{pid}") for pid in spouses]
                return f"{x}｜" + " × ".join(names) if names else f"{x}｜（尚無配偶）"

            mid = st.selectbox("選擇婚姻以新增子女", list(t["marriages"].keys()), format_func=safe_format_marriage)
            if mid:
                c1,c2,c3 = st.columns([2,1,1])
                child = c1.selectbox("子女", [""]+[p for p in t["persons"].keys() if p not in t["marriages"][mid]["children"]],
                                     format_func=lambda x: x if not x else f'{x}｜{t["persons"][x]["name"]}')
                ctype = c2.selectbox("關係", ["生","繼","認領","其他"], index=0, key="sel_ctype")
                if c3.button("👶 新增子女", key="btn_add_child"):
                    if not child:
                        st.warning("請選擇子女")
                    else:
                        t["marriages"][mid]["children"].append(child)
                        t["child_types"].setdefault(mid, {})[child] = ctype
                        st.success("已新增子女")

    # === ③ 家族樹視覺化 ===
    with st.expander("③ 家族樹視覺化", expanded=True):
        st.graphviz_chart(_graph(t))

    # === ④ 匯入 / 匯出 ===
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

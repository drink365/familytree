# app.py
# -*- coding: utf-8 -*-

import json
import uuid
from typing import Dict, List, Tuple

import streamlit as st

st.set_page_config(page_title="Family Tree", page_icon="🌳", layout="wide")


# -----------------------------
# Data model (kept in session)
# -----------------------------
# doc = {
#   "persons": { pid: {"id": pid, "name": str, "deceased": bool} },
#   "unions":  { uid: {"id": uid, "partners": [pidA, pidB], "status": "married"|"divorced"} },
#   "children": [ {"unionId": uid, "childId": pid}, ... ]
# }

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _ensure_state():
    if "doc" not in st.session_state:
        st.session_state.doc = {"persons": {}, "unions": {}, "children": []}
    if "selected" not in st.session_state:
        st.session_state.selected = (None, None)  # (type, id)


_ensure_state()


# -----------------------------
# Demo data
# -----------------------------
def load_demo():
    P = {}
    U = {}
    names = [
        "陳一郎", "陳前妻", "陳妻",
        "陳大", "陳大嫂", "陳二", "陳二嫂", "陳三", "陳三嫂",
        "王子", "王子妻", "王孫", "二孩A", "二孩B", "二孩C", "三孩A", "三孩B"
    ]
    name_to_id = {}
    for n in names:
        pid = _new_id("P")
        P[pid] = {"id": pid, "name": n, "deceased": False}
        name_to_id[n] = pid

    def union(a, b, status="married"):
        uid = _new_id("U")
        U[uid] = {"id": uid, "partners": [name_to_id[a], name_to_id[b]], "status": status}
        return uid

    m1 = union("陳一郎", "陳前妻", status="divorced")
    m2 = union("陳一郎", "陳妻")
    m3 = union("王子", "王子妻")
    m4 = union("陳大", "陳大嫂")
    m5 = union("陳二", "陳二嫂")
    m6 = union("陳三", "陳三嫂")

    children = [
        {"unionId": m1, "childId": name_to_id["王子"]},
        {"unionId": m2, "childId": name_to_id["陳大"]},
        {"unionId": m2, "childId": name_to_id["陳二"]},
        {"unionId": m2, "childId": name_to_id["陳三"]},
        {"unionId": m3, "childId": name_to_id["王孫"]},
        {"unionId": m5, "childId": name_to_id["二孩A"]},
        {"unionId": m5, "childId": name_to_id["二孩B"]},
        {"unionId": m5, "childId": name_to_id["二孩C"]},
        {"unionId": m6, "childId": name_to_id["三孩A"]},
        {"unionId": m6, "childId": name_to_id["三孩B"]},
    ]

    st.session_state.doc = {"persons": P, "unions": U, "children": children}
    st.session_state.selected = (None, None)


# -----------------------------
# Graphviz rendering
# -----------------------------
def build_dot(doc: Dict) -> str:
    """
    Render with 'marriage node' approach:
    - Each union is a small point (shape=point). Spouses connect to it (same rank).
    - Children connect from the union point downward.
    - Divorced unions: spouse-to-spouse edge is dashed.
    - Deceased person: different fillcolor/label suffix.
    """
    persons = doc["persons"]
    unions = doc["unions"]
    children = doc["children"]

    # style
    node_style = 'shape=box, style="rounded,filled", color="#0f4c5c", fillcolor="#083b4c", fontcolor="white", penwidth=2'
    node_style_dead = 'shape=box, style="rounded,filled", color="#475569", fillcolor="#6b7280", fontcolor="white", penwidth=2'
    union_style = 'shape=point, width=0.02, color="#0f3c4d"'
    edge_style = 'color="#0f3c4d", penwidth=2'
    edge_divorce = 'color="#0f3c4d", penwidth=2, style="dashed"'

    lines: List[str] = []
    lines.append('digraph G {')
    lines.append('  graph [rankdir=TB, nodesep=0.4, ranksep=0.6, splines=ortho, bgcolor="white"];')
    lines.append('  node  [{}];'.format(node_style))
    lines.append('  edge  [{}];'.format(edge_style))

    # Persons
    for pid, p in persons.items():
        label = p["name"] + ("（殁）" if p.get("deceased") else "")
        if p.get("deceased"):
            lines.append(f'  "{pid}" [{node_style_dead}, label="{label}"];')
        else:
            lines.append(f'  "{pid}" [label="{label}"];')

    # Unions as points, and spouse alignments (rank=same)
    # Also draw spouse-to-spouse line (dashed if divorced)
    for uid, u in unions.items():
        a, b = u["partners"]
        lines.append(f'  "{uid}" [{union_style}];')

        # Keep spouses on same rank by subgraph
        lines.append('  { rank=same;')
        lines.append(f'    "{a}"; "{uid}"; "{b}";')
        lines.append('  }')

        # Connect spouses to union point
        lines.append(f'  "{a}" -> "{uid}" [dir=none];')
        lines.append(f'  "{b}" -> "{uid}" [dir=none];')

        # Spouse-to-spouse visible line (aesthetics)
        if u.get("status") == "divorced":
            lines.append(f'  "{a}" -> "{b}" [dir=none, {edge_divorce}];')
        else:
            lines.append(f'  "{a}" -> "{b}" [dir=none];')

    # Children: union -> child downward; enforce generations using ranks
    # Build mapping: union -> [child ids]
    kids_by_union: Dict[str, List[str]] = {}
    for cl in children:
        kids_by_union.setdefault(cl["unionId"], []).append(cl["childId"])

    # Keep siblings on same rank
    for uid, kids in kids_by_union.items():
        # union -> child
        for c in kids:
            lines.append(f'  "{uid}" -> "{c}";')
        # siblings same rank
        lines.append('  { rank=same; ' + "; ".join(f'"{c}"' for c in kids) + '; }')

    lines.append('}')
    return "\n".join(lines)


# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.title("🌳 Family Tree")
    st.caption("不依賴外部 JS，Graphviz 內建渲染。")

    colA, colB = st.columns(2)
    if colA.button("載入示範", use_container_width=True):
        load_demo()
    if colB.button("清空", use_container_width=True):
        st.session_state.doc = {"persons": {}, "unions": {}, "children": []}
        st.session_state.selected = (None, None)

    st.divider()

    # Add person
    st.subheader("快速新增")
    with st.form("add_person", clear_on_submit=True):
        name = st.text_input("新人物姓名", "")
        submitted = st.form_submit_button("新增人物")
        if submitted:
            pid = _new_id("P")
            st.session_state.doc["persons"][pid] = {"id": pid, "name": name or f"新成員 {len(st.session_state.doc['persons'])+1}", "deceased": False}

    # Add union
    persons_list = list(st.session_state.doc["persons"].values())
    opts = {p["name"] + ("（殁）" if p.get("deceased") else ""): p["id"] for p in persons_list}
    st.caption("建立婚姻")
    c1, c2 = st.columns(2)
    A = c1.selectbox("配偶 A", [""] + list(opts.keys()), index=0)
    B = c2.selectbox("配偶 B", [""] + list(opts.keys()), index=0)
    colU1, colU2 = st.columns([2,1])
    if colU1.button("建立婚姻", use_container_width=True, disabled=not (A and B and opts.get(A) != opts.get(B))):
        uid = _new_id("U")
        st.session_state.doc["unions"][uid] = {"id": uid, "partners": [opts[A], opts[B]], "status": "married"}
    if colU2.button("設為離婚", use_container_width=True, disabled=not (A and B and opts.get(A) != opts.get(B))):
        # 若已存在該婚姻，標記離婚；否則新建為離婚
        pidA, pidB = opts[A], opts[B]
        for u in st.session_state.doc["unions"].values():
            if set(u["partners"]) == {pidA, pidB}:
                u["status"] = "divorced"
                break
        else:
            uid = _new_id("U")
            st.session_state.doc["unions"][uid] = {"id": uid, "partners": [pidA, pidB], "status": "divorced"}

    st.caption("加入子女（從某段婚姻）")
    unions_list = list(st.session_state.doc["unions"].values())
    union_opts = {}
    for u in unions_list:
        a, b = u["partners"]
        nA = st.session_state.doc["persons"].get(a, {}).get("name", "?")
        nB = st.session_state.doc["persons"].get(b, {}).get("name", "?")
        tag = "（離）" if u.get("status") == "divorced" else ""
        union_opts[f"{nA} ↔ {nB}{tag}"] = u["id"]

    ukey = st.selectbox("選擇婚姻", [""] + list(union_opts.keys()), index=0)
    child_name = st.text_input("新子女姓名", "")
    if st.button("加入子女", use_container_width=True, disabled=not ukey):
        cid = _new_id("P")
        st.session_state.doc["persons"][cid] = {"id": cid, "name": child_name or f"新子女 {len(st.session_state.doc['children'])+1}", "deceased": False}
        st.session_state.doc["children"].append({"unionId": union_opts[ukey], "childId": cid})

    st.divider()
    st.subheader("匯入 / 匯出")
    jcol1, jcol2 = st.columns(2)
    # Export
    data_str = json.dumps(st.session_state.doc, ensure_ascii=False, indent=2)
    jcol1.download_button("匯出 JSON", data=data_str, file_name="family-tree.json", mime="application/json", use_container_width=True)
    # Import
    up = jcol2.file_uploader("匯入 JSON", type=["json"])
    if up is not None:
        try:
            obj = json.loads(up.read().decode("utf-8"))
            if obj and isinstance(obj, dict) and {"persons", "unions", "children"} <= set(obj.keys()):
                st.session_state.doc = obj
                st.toast("已匯入 JSON。", icon="✅")
            else:
                st.toast("格式不正確。", icon="⚠️")
        except Exception:
            st.toast("JSON 解析失敗。", icon="⚠️")

    st.divider()
    st.subheader("編輯（選取後）")
    # Toggle deceased / delete person / delete union handled in main pane selection table


# -----------------------------
# Main pane: canvas + table
# -----------------------------
left, right = st.columns([2, 1])

with left:
    st.markdown("#### 家族樹")
    dot = build_dot(st.session_state.doc)
    # 直接用 Streamlit 內建 Graphviz 渲染（不依賴外部 CDN）
    st.graphviz_chart(dot, use_container_width=True)

with right:
    st.markdown("#### 人物清單")
    P = st.session_state.doc["persons"]
    U = st.session_state.doc["unions"]
    C = st.session_state.doc["children"]

    # 人物列表與操作
    if P:
        for pid, p in list(P.items()):
            cols = st.columns([3, 2, 2, 2])
            label = p["name"] + ("（殁）" if p.get("deceased") else "")
            cols[0].markdown(f"**{label}**")
            if cols[1].button("標記/取消身故", key=f"dead_{pid}"):
                p["deceased"] = not p.get("deceased", False)
            if cols[2].button("刪除人物", key=f"del_{pid}"):
                # 刪除人物：移除其參與的婚姻與以其為子女的關係
                # 1) 刪除婚姻
                U2 = {}
                to_remove_unions = set()
                for uid, u in U.items():
                    if pid not in u["partners"]:
                        U2[uid] = u
                    else:
                        to_remove_unions.add(uid)
                st.session_state.doc["unions"] = U2
                # 2) 刪除 children 中與被刪婚姻或該人為子女的關係
                C2 = [cl for cl in C if cl["childId"] != pid and cl["unionId"] not in to_remove_unions]
                st.session_state.doc["children"] = C2
                # 3) 刪人物本身
                del P[pid]
                st.experimental_rerun()
            new_name = cols[3].text_input("改名", value=p["name"], key=f"rename_{pid}")
            if new_name != p["name"]:
                p["name"] = new_name
    else:
        st.info("尚無人物。可從左側新增或載入示範。")

    st.markdown("---")
    st.markdown("#### 婚姻清單")
    if U:
        for uid, u in list(U.items()):
            a, b = u["partners"]
            na = P.get(a, {}).get("name", "?")
            nb = P.get(b, {}).get("name", "?")
            cols = st.columns([4, 2, 2])
            cols[0].markdown(f"**{na} ↔ {nb}**　狀態：{'離婚' if u.get('status')=='divorced' else '婚姻'}")
            if cols[1].button("切換離婚/婚姻", key=f"div_{uid}"):
                u["status"] = "married" if u.get("status") == "divorced" else "divorced"
            if cols[2].button("刪除婚姻", key=f"delu_{uid}"):
                # 刪除該婚姻與其子女關係
                del U[uid]
                st.session_state.doc["children"] = [cl for cl in C if cl["unionId"] != uid]
                st.experimental_rerun()
    else:
        st.info("尚無婚姻。")


st.markdown(
    """
    <div style="color:#64748b;font-size:13px;margin-top:8px">
      提示：此版本使用 Streamlit 內建 Graphviz 渲染，不依賴外部 CDN。
      夫妻由中間 <em>婚姻點</em> 連結，子女由婚姻點往下連，能正確對齊父母與子女。
      離婚以虛線表示、身故以節點顏色與「（殁）」標示。
    </div>
    """,
    unsafe_allow_html=True,
)

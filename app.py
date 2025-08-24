import streamlit as st
import json
import io
import copy
from typing import Dict, List, Optional

# ------------------------------
# App Config
# ------------------------------
st.set_page_config(page_title="🧬 家庭樹 Family Tree", page_icon="🧬", layout="wide")

# ------------------------------
# Utilities for State & IDs
# ------------------------------

def init_data():
    """Ensure base schema exists in session state and coerce types."""
    if "data" not in st.session_state:
        st.session_state.data = {
            "persons": {},      # pid -> {name, gender, deceased, birth_year, tag}
            "marriages": {},    # mid -> {a, b, divorced, current, note}
            "children": [],     # list of {marriage_id, children: [pid, ...]}
            "_seq": {"P": 0, "M": 0},
        }
    if "history" not in st.session_state:
        st.session_state.history = []
    if "future" not in st.session_state:
        st.session_state.future = []
    if "readonly" not in st.session_state:
        st.session_state.readonly = False
    ensure_schema_types()


def ensure_schema_types():
    """Guard against malformed JSON/imports; coerce to expected types."""
    d = st.session_state.data
    # persons
    if not isinstance(d.get("persons"), dict):
        d["persons"] = {}
    # marriages: allow list -> dict conversion
    if not isinstance(d.get("marriages"), dict):
        if isinstance(d.get("marriages"), list):
            conv = {}
            for i, m in enumerate(d["marriages"]):
                if isinstance(m, dict):
                    mid = m.get("id") or f"M_conv_{i+1}"
                    conv[mid] = {
                        "a": m.get("a"),
                        "b": m.get("b"),
                        "current": bool(m.get("current", True)),
                        "divorced": bool(m.get("divorced", False)),
                        "note": m.get("note", ""),
                    }
            d["marriages"] = conv
        else:
            d["marriages"] = {}
    # children list only
    if not isinstance(d.get("children"), list):
        d["children"] = []
    # seq
    if not isinstance(d.get("_seq"), dict):
        d["_seq"] = {"P": 0, "M": 0}


def next_id(prefix: str) -> str:
    """Generate incremental IDs for persons (P) and marriages (M)."""
    st.session_state.data["_seq"][prefix] += 1
    return f"{prefix}{st.session_state.data['_seq'][prefix]}"


def push_history():
    st.session_state.history.append(copy.deepcopy(st.session_state.data))
    st.session_state.future = []


def undo():
    if st.session_state.history:
        st.session_state.future.append(copy.deepcopy(st.session_state.data))
        st.session_state.data = st.session_state.history.pop()


def redo():
    if st.session_state.future:
        st.session_state.history.append(copy.deepcopy(st.session_state.data))
        st.session_state.data = st.session_state.future.pop()


# ------------------------------
# Demo Data (optional)
# ------------------------------

def load_demo():
    """Populate a small demo family for first‑time users."""
    d = st.session_state.data
    if d["persons"]:
        return
    # Grandparents
    pA = add_person(name="陳志明", gender="男", birth_year=1958)
    pB = add_person(name="王春嬌", gender="女", birth_year=1960)
    mid1 = add_marriage(pA, pB, current=True, divorced=False)
    # Children of (陳志明, 王春嬌)
    c1 = add_person(name="陳小明", gender="男", birth_year=1985)
    c2 = add_person(name="陳小芳", gender="女", birth_year=1988)
    c3 = add_person(name="二代1", gender="男", birth_year=1990)
    c4 = add_person(name="二代2", gender="女", birth_year=1992)
    attach_children(mid1, [c1, c2, c3, c4])
    # 現任/前任示意
    ex1 = add_person(name="前配偶A", gender="女", birth_year=1987)
    cur = add_person(name="現任配偶", gender="女", birth_year=1991)
    mid2 = add_marriage(c1, ex1, current=False, divorced=True)
    mid3 = add_marriage(c1, cur, current=True, divorced=False)
    k1 = add_person(name="小孩甲", gender="男", birth_year=2015)
    k2 = add_person(name="小孩乙", gender="女", birth_year=2018)
    attach_children(mid3, [k1, k2])


# ------------------------------
# CRUD Helpers
# ------------------------------

def add_person(name: str, gender: str, deceased: bool=False, birth_year: Optional[int]=None, tag: str="") -> str:
    pid = next_id("P")
    st.session_state.data["persons"][pid] = {
        "name": name.strip(),
        "gender": gender,
        "deceased": bool(deceased),
        "birth_year": int(birth_year) if birth_year is not None else None,
        "tag": tag.strip() if tag else "",
    }
    return pid


def update_person(pid: str, **kwargs):
    if pid in st.session_state.data["persons"]:
        st.session_state.data["persons"][pid].update(kwargs)


def delete_person(pid: str):
    d = st.session_state.data
    # Remove marriages where pid participated
    to_delete = [mid for mid, m in d["marriages"].items() if m.get("a") == pid or m.get("b") == pid]
    for mid in to_delete:
        delete_marriage(mid)
    # Remove from children arrays
    for row in d["children"]:
        if isinstance(row, dict):
            row["children"] = [c for c in row.get("children", []) if c != pid]
    # Finally remove the person
    if pid in d["persons"]:
        del d["persons"][pid]


def add_marriage(a: str, b: str, current: bool=True, divorced: bool=False, note: str="") -> str:
    mid = next_id("M")
    st.session_state.data["marriages"][mid] = {
        "a": a, "b": b, "current": bool(current), "divorced": bool(divorced), "note": note,
    }
    return mid


def update_marriage(mid: str, **kwargs):
    if mid in st.session_state.data["marriages"]:
        st.session_state.data["marriages"][mid].update(kwargs)


def delete_marriage(mid: str):
    d = st.session_state.data
    if mid in d["marriages"]:
        del d["marriages"][mid]
    d["children"] = [row for row in d["children"] if isinstance(row, dict) and row.get("marriage_id") != mid]


def attach_children(mid: str, kids: List[str]):
    d = st.session_state.data
    # find existing row for this marriage
    for row in d["children"]:
        if isinstance(row, dict) and row.get("marriage_id") == mid:
            existing = set(row.get("children", []))
            row["children"] = list(existing.union(set(kids)))
            return
    d["children"].append({"marriage_id": mid, "children": list(kids)})


def remove_child(mid: str, pid: str):
    d = st.session_state.data
    for row in d["children"]:
        if isinstance(row, dict) and row.get("marriage_id") == mid:
            row["children"] = [c for c in row.get("children", []) if c != pid]
            break


# ------------------------------
# Query Helpers
# ------------------------------

def marriages_of(pid: str) -> List[str]:
    return [mid for mid, m in st.session_state.data.get("marriages", {}).items() if isinstance(m, dict) and (m.get("a") == pid or m.get("b") == pid)]


def children_of_marriage(mid: str) -> List[str]:
    for row in st.session_state.data.get("children", []):
        if isinstance(row, dict) and row.get("marriage_id") == mid:
            return row.get("children", [])
    return []


def sort_siblings_by_age(child_ids: List[str]) -> List[str]:
    persons = st.session_state.data.get("persons", {})
    with_year = [cid for cid in child_ids if persons.get(cid, {}).get("birth_year")]
    no_year   = [cid for cid in child_ids if not persons.get(cid, {}).get("birth_year")]
    with_year.sort(key=lambda c: persons[c].get("birth_year"))  # 早生在左（年份小在左）
    return with_year + no_year


def _escape_label(s: str) -> str:
    # Ensure Graphviz-safe label
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def person_label(pid: str) -> str:
    p = st.session_state.data.get("persons", {}).get(pid, {})
    by = p.get("birth_year")
    tag = p.get("tag")
    base = p.get("name", pid)
    parts = [base]
    if by:
        parts.append(str(by))
    if tag:
        parts.append(f"[{tag}]")
    return "\n".join(parts)


# ------------------------------
# Graph (DOT) Rendering
# ------------------------------

def build_dot() -> str:
    ensure_schema_types()
    d = st.session_state.data
    persons = d.get("persons", {})
    marriages = d.get("marriages", {})
    lines = []

    lines.append("digraph G {")
    lines.append("  rankdir=TB;")
    lines.append('  node [fontname="Noto Sans CJK TC", style=filled, fillcolor="white", color="#777777"];')
    lines.append('  edge [dir=none, color="#555555"];')

    # 1) Person nodes
    for pid, p in persons.items():
        if not isinstance(p, dict):
            continue
        shape = "circle" if p.get("gender") == "女" else "box"
        fill = "#f2f2f2" if p.get("deceased") else "white"
        font = "#666666" if p.get("deceased") else "#222222"
        label = _escape_label(person_label(pid))
        lines.append(f'  "{pid}" [label="{label}", shape={shape}, fillcolor="{fill}", fontcolor="{font}"];')

    # 2) Marriage junctions + spouse edges
    if isinstance(marriages, dict):
        for mid, m in marriages.items():
            if not isinstance(m, dict):
                continue
            a = m.get("a")
            b = m.get("b")
            if not a or not b or a not in persons or b not in persons:
                continue
            jid = f"J_{mid}"
            style = "dashed" if m.get("divorced") else "solid"
            lines.append(f'  "{jid}" [shape=point, width=0.02, label="", color="#888888"];')
            lines.append(f'  "{a}" -> "{jid}" [style={style}];')
            lines.append(f'  "{jid}" -> "{b}" [style={style}];')

    # 3) Children groups (from correct marriage junction)
    for row in d.get("children", []):
        if not isinstance(row, dict):
            continue
        mid = row.get("marriage_id")
        kids = row.get("children", [])
        if not mid or not isinstance(kids, list):
            continue
        kids = [k for k in kids if k in persons]
        kids = sort_siblings_by_age(kids)
        if not kids:
            continue
        jid = f"J_{mid}"
        # keep siblings on same rank
        lines.append("  { rank=same; " + "; ".join([f'"{k}"' for k in kids]) + " }")
        for k in kids:
            lines.append(f'  "{jid}" -> "{k}";')

    # 4) Soft bias ex/current placement (subgraphs)
    for pid in persons.keys():
        mids = marriages_of(pid)
        if len(mids) <= 1:
            continue
        ex_side = []
        cur_side = []
        for mid in mids:
            m = marriages.get(mid)
            if not isinstance(m, dict):
                continue
            if not m.get("current") or m.get("divorced"):
                ex_side.append(f'"J_{mid}"')
            else:
                cur_side.append(f'"J_{mid}"')
        if ex_side:
            lines.append("  subgraph cluster_left_" + pid + " { rank=same; color=\"white\"; " + "; ".join(ex_side) + " }")
        if cur_side:
            lines.append("  subgraph cluster_right_" + pid + " { rank=same; color=\"white\"; " + "; ".join(cur_side) + " }")

    lines.append("}")
    return "\n".join(lines)


# ------------------------------
# UI Components
# ------------------------------

def toolbar():
    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,1])
    with c1:
        if st.button("↩️ 復原 (Undo)"):
            undo()
    with c2:
        if st.button("↪️ 重做 (Redo)"):
            redo()
    with c3:
        st.session_state.readonly = st.toggle(
            "唯讀模式", value=st.session_state.readonly,
            help="關閉表單輸入，適合客戶瀏覽/展示"
        )
    with c4:
        buf = io.BytesIO(json.dumps(st.session_state.data, ensure_ascii=False, indent=2).encode("utf-8"))
        st.download_button("📥 匯出 JSON", data=buf, file_name="family.json", mime="application/json")
    with c5:
        up = st.file_uploader("📤 匯入 JSON（將覆蓋目前資料）", type=["json"], label_visibility="collapsed")
        if up is not None:
            try:
                incoming = json.load(up)
                for k in ["persons", "marriages", "children", "_seq"]:
                    if k not in incoming:
                        raise ValueError(f"缺少必要欄位：{k}")
                push_history()
                st.session_state.data = incoming
                ensure_schema_types()
                st.success("匯入成功！")
            except Exception as e:
                st.error(f"匯入失敗：\n{e}")
    with c6:
        dot_src = build_dot()
        st.download_button("🧾 下載 DOT", data=dot_src.encode("utf-8"), file_name="family.dot", mime="text/vnd.graphviz")


def person_manager():
    st.subheader("👤 人物管理")
    readonly = st.session_state.readonly

    with st.expander("新增人物", expanded=False):
        with st.form("form_add_person"):
            name = st.text_input("姓名*", disabled=readonly).strip()
            gender = st.selectbox("性別*", ["男", "女"], disabled=readonly)
            by_val = st.number_input("出生年（預設 2000，可取消）", min_value=1850, max_value=2100, step=1, value=2000, format="%d", disabled=readonly)
            use_by = st.checkbox("使用上述出生年", value=False, disabled=readonly)
            deceased = st.checkbox("是否已過世", value=False, disabled=readonly)
            tag = st.text_input("標籤（關鍵角色/身份）", value="", disabled=readonly)
            submitted = st.form_submit_button("新增")
            if submitted and not readonly and name:
                push_history()
                add_person(name=name, gender=gender, deceased=deceased, birth_year=(by_val if use_by else None), tag=tag)
                st.success(f"已新增：{name}")

    # 編輯/刪除
    people = st.session_state.data.get("persons", {})
    if not people:
        st.info("目前尚無人物。可用上方『新增人物』或載入 demo。")
        return

    q = st.text_input("快速搜尋（姓名/標籤）").strip()

    def match(pid):
        p = people[pid]
        target = (p.get("name", "") + " " + p.get("tag", "")).lower()
        return q.lower() in target if q else True

    plist = [pid for pid in people.keys() if match(pid)]
    if not plist:
        st.warning("找不到符合條件的人物。")
        return

    pid = st.selectbox("選擇人物以編輯", plist, format_func=lambda x: f"{people[x]['name']} ({x})")
    p = people[pid]

    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
    with col1:
        name = st.text_input("姓名", value=p.get("name", ""), disabled=readonly)
    with col2:
        gender = st.selectbox("性別", ["男", "女"], index=0 if p.get("gender") == "男" else 1, disabled=readonly)
    with col3:
        by_val = st.number_input("出生年（可空白）", min_value=1850, max_value=2100, step=1, value=p.get("birth_year") or 2000, format="%d", disabled=readonly)
        use_by = st.checkbox("啟用出生年", value=(p.get("birth_year") is not None), disabled=readonly)
    with col4:
        deceased = st.checkbox("已過世", value=p.get("deceased", False), disabled=readonly)
    with col5:
        tag = st.text_input("標籤", value=p.get("tag", ""), disabled=readonly)

    cA, cB, cC = st.columns([1,1,1])
    with cA:
        if st.button("💾 儲存變更", disabled=readonly):
            push_history()
            update_person(pid, name=name.strip(), gender=gender, deceased=deceased, birth_year=(by_val if use_by else None), tag=tag.strip())
            st.success("已更新。")
    with cB:
        if st.button("🗑️ 刪除此人物", disabled=readonly, type="secondary"):
            push_history()
            delete_person(pid)
            st.success("已刪除。請向上方列表重新選擇。")
    with cC:
        if st.button("➕ 載入示範資料", type="secondary"):
            push_history()
            load_demo()
            st.toast("已載入 demo")


def marriage_manager():
    st.subheader("💞 婚姻關係")
    readonly = st.session_state.readonly
    people = st.session_state.data.get("persons", {})
    if len(people) < 2:
        st.info("請先建立至少兩位人物。")
        return

    with st.expander("新增婚姻/伴侶關係", expanded=False):
        col1, col2, col3, col4 = st.columns([1,1,1,1])
        with col1:
            a = st.selectbox("當事人 A", list(people.keys()), format_func=lambda x: people[x]["name"], disabled=readonly)
        with col2:
            b = st.selectbox("當事人 B", [x for x in people.keys() if x != a], format_func=lambda x: people[x]["name"], disabled=readonly)
        with col3:
            current = st.checkbox("現任/當前", value=True, disabled=readonly)
        with col4:
            divorced = st.checkbox("已離婚（虛線）", value=False, disabled=readonly)
        note = st.text_input("備註（選填）", disabled=readonly)
        if st.button("新增婚姻", disabled=readonly):
            if a == b:
                st.error("A/B 不可為同一人")
            else:
                push_history()
                mid = add_marriage(a, b, current=current, divorced=divorced, note=note)
                st.success(f"已建立婚姻：{people[a]['name']} × {people[b]['name']} ({mid})")

    # 列表 & 編輯
    marriages = st.session_state.data.get("marriages", {})
    if not marriages:
        st.info("尚無婚姻關係。")
        return

    mids = list(marriages.keys())
    mid = st.selectbox("選擇婚姻以編輯", mids, format_func=lambda x: f"{marriages[x]['a']}×{marriages[x]['b']} ({x})")
    m = marriages[mid]

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        current = st.checkbox("現任/當前", value=m.get("current", True), disabled=readonly)
    with col2:
        divorced = st.checkbox("已離婚（虛線）", value=m.get("divorced", False), disabled=readonly)
    with col3:
        note = st.text_input("備註", value=m.get("note", ""), disabled=readonly)

    cA, cB = st.columns([1,1])
    with cA:
        if st.button("💾 儲存婚姻變更", disabled=readonly):
            push_history()
            update_marriage(mid, current=current, divorced=divorced, note=note)
            st.success("已更新婚姻資訊。")
    with cB:
        if st.button("🗑️ 刪除此婚姻", disabled=readonly, type="secondary"):
            push_history()
            delete_marriage(mid)
            st.success("已刪除。")


def children_manager():
    st.subheader("👶 子女連結（一定從對應婚姻點往下）")
    readonly = st.session_state.readonly
    marriages = st.session_state.data.get("marriages", {})
    people = st.session_state.data.get("persons", {})
    if not marriages:
        st.info("請先建立婚姻/伴侶關係。")
        return

    mid = st.selectbox("選擇婚姻", list(marriages.keys()), format_func=lambda x: f"{people.get(marriages[x]['a'],{}).get('name','?')} × {people.get(marriages[x]['b'],{}).get('name','?')} ({x})")
    current_kids = children_of_marriage(mid)

    col1, col2 = st.columns([1,1])
    with col1:
        candidate = st.selectbox(
            "選擇子女以新增",
            [pid for pid in people.keys() if pid not in current_kids and pid not in [marriages[mid]['a'], marriages[mid]['b']]],
            format_func=lambda x: people[x]['name'], disabled=readonly
        )
        if st.button("➕ 新增子女", disabled=readonly):
            push_history()
            attach_children(mid, [candidate])
            st.success(f"已新增子女：{people[candidate]['name']}")
    with col2:
        if current_kids:
            rem = st.selectbox("移除已連結的子女", current_kids, format_func=lambda x: people[x]['name'], disabled=readonly)
            if st.button("➖ 移除子女", disabled=readonly):
                push_history()
                remove_child(mid, rem)
                st.success("已移除。")
        else:
            st.info("此婚姻目前尚無子女連結。")

    # 顯示目前排序（左到右 = 年長到年幼）
    if current_kids:
        ordered = sort_siblings_by_age(current_kids)
        st.caption("當前兄弟姊妹排序（左→右）：")
        st.write(" → ".join([people[k]["name"] for k in ordered]))


# ------------------------------
# Main
# ------------------------------
init_data()

st.title("🧬 家庭樹 Family Tree")
st.caption("女生圓形、男生方形、灰底為已過世；已離婚為虛線。子女只會從對應婚姻點往下連線。")

# Top toolbar
toolbar()

# Optional demo for first time
if not st.session_state.data["persons"]:
    with st.container(border=True):
        st.info("目前資料是空白的。您可以手動新增，或一鍵載入示範資料。")
        if st.button("載入示範資料"):
            push_history()
            load_demo()
            st.rerun()

# 3-column layout: managers on left/right, graph center
left, center, right = st.columns([1.2, 1.6, 1.2])

with left:
    person_manager()

with center:
    st.subheader("🗺️ 家庭樹視覺化")
    dot_src = build_dot()
    st.graphviz_chart(dot_src, use_container_width=True)
    st.caption("※ 兄弟姊妹按出生年自動排序（無出生年者保持輸入順序）。")

with right:
    marriage_manager()
    st.divider()
    children_manager()

# Footer / Disclaimer
st.divider()
st.caption("本工具僅供教育與初步規劃參考；涉及法律與稅務之正式意見，請洽合格律師與會計師。")

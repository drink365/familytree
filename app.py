# -*- coding: utf-8 -*-
import json, io
from typing import Dict, List, Tuple, Optional
import streamlit as st
import pandas as pd
from graphviz import Digraph

st.set_page_config(page_title="👨‍👩‍👧‍👦 Family Tree（穩定版）", page_icon="🌳", layout="wide")

# -------------------- Helpers --------------------
def load_sample():
    people = [
        {"id": "P1", "name": "王大樹", "gender": "M", "birth": "1955", "death": "", "spouse_id": "P2"},
        {"id": "P2", "name": "林美麗", "gender": "F", "birth": "1958", "death": "", "spouse_id": "P1"},
        {"id": "P3", "name": "王小強", "gender": "M", "birth": "1985", "death": "", "spouse_id": "P4"},
        {"id": "P4", "name": "陳心怡", "gender": "F", "birth": "1987", "death": "", "spouse_id": "P3"},
        {"id": "P5", "name": "王小美", "gender": "F", "birth": "1990", "death": "", "spouse_id": ""},
        {"id": "P6", "name": "王可可", "gender": "F", "birth": "2015", "death": "", "spouse_id": ""},
        {"id": "P7", "name": "王豆豆", "gender": "M", "birth": "2018", "death": "", "spouse_id": ""},
    ]
    # parent-child edges (parent -> child)
    links = [
        {"parent_id": "P1", "child_id": "P3"},
        {"parent_id": "P2", "child_id": "P3"},
        {"parent_id": "P1", "child_id": "P5"},
        {"parent_id": "P2", "child_id": "P5"},
        {"parent_id": "P3", "child_id": "P6"},
        {"parent_id": "P4", "child_id": "P6"},
        {"parent_id": "P3", "child_id": "P7"},
        {"parent_id": "P4", "child_id": "P7"},
    ]
    return people, links

def ensure_state():
    if "people" not in st.session_state:
        people, links = load_sample()
        st.session_state["people"] = pd.DataFrame(people)
        st.session_state["links"] = pd.DataFrame(links)

def people_df() -> pd.DataFrame:
    ensure_state()
    return st.session_state["people"]

def links_df() -> pd.DataFrame:
    ensure_state()
    return st.session_state["links"]

def set_people(df: pd.DataFrame):
    st.session_state["people"] = df

def set_links(df: pd.DataFrame):
    st.session_state["links"] = df

def id_name_map(df: pd.DataFrame) -> Dict[str, str]:
    return {row["id"]: row["name"] for _, row in df.iterrows()}

def sanitize(df: pd.DataFrame) -> pd.DataFrame:
    # Drop duplicates by id for people; ensure ids are strings
    if "id" in df.columns:
        df["id"] = df["id"].astype(str).str.strip()
        df = df.drop_duplicates(subset=["id"], keep="first")
    for col in df.columns:
        df[col] = df[col].fillna("")
    return df

def to_json_bytes() -> bytes:
    data = {
        "people": people_df().to_dict(orient="records"),
        "links": links_df().to_dict(orient="records"),
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

def import_json(file_bytes: bytes) -> Tuple[bool, str]:
    try:
        obj = json.loads(file_bytes.decode("utf-8"))
        p = pd.DataFrame(obj.get("people", []))
        l = pd.DataFrame(obj.get("links", []))
        expected_people_cols = ["id", "name", "gender", "birth", "death", "spouse_id"]
        for c in expected_people_cols:
            if c not in p.columns:
                p[c] = ""
        expected_links_cols = ["parent_id", "child_id"]
        for c in expected_links_cols:
            if c not in l.columns:
                l[c] = ""
        set_people(sanitize(p[expected_people_cols]))
        set_links(sanitize(l[expected_links_cols]))
        return True, "匯入成功"
    except Exception as e:
        return False, f"匯入失敗：{e}"

# -------------------- Graphviz rendering --------------------
def render_graphviz(people: pd.DataFrame, links: pd.DataFrame, orientation: str = "TB") -> Digraph:
    g = Digraph("FamilyTree", node_attr={"shape": "box", "style": "rounded,filled", "fontname": "Taipei Sans TC, PingFang TC, Noto Sans CJK TC, Arial"})
    g.attr(rankdir=orientation)  # TB: top-bottom, LR: left-right

    # Build lookup
    P = {row["id"]: row for _, row in people.iterrows()}
    children_map = {}
    for _, r in links.iterrows():
        parent, child = r["parent_id"], r["child_id"]
        children_map.setdefault(parent, set()).add(child)

    # Draw people nodes
    for pid, row in P.items():
        label = f'{row.get("name","")}\\n({row.get("birth","")}–{row.get("death","")})'.replace("()", "")
        color = "#e6f4ea" if row.get("gender","").upper() == "M" else "#fde6f2"
        g.node(pid, label=label, fillcolor=color)

    # Spouse/marriage nodes: create an invisible "marriage" dot to join spouses, then link children from it
    # Find spouse pairs without duplicating (A-B same as B-A)
    seen_pairs = set()
    for pid, row in P.items():
        sid = str(row.get("spouse_id","")).strip()
        if sid and sid in P and (sid, pid) not in seen_pairs and pid != sid:
            pair = (pid, sid)
            seen_pairs.add(pair)
            mid = f"m_{pid}_{sid}"
            g.node(mid, label="", shape="point", width="0.01")
            # Connect spouse → marriage node (no arrows)
            g.edge(pid, mid, dir="none")
            g.edge(sid, mid, dir="none")
            # Children of the couple: those that have both as parents
            kids = set()
            # naive: if a child has either pid or sid as parent, connect via marriage node (works for most cases)
            for c in children_map.get(pid, set()) | children_map.get(sid, set()):
                kids.add(c)
            for c in kids:
                g.edge(mid, c, dir="forward")

    # Also add direct parent->child edges (for single parent scenarios)
    for _, r in links.iterrows():
        g.edge(r["parent_id"], r["child_id"])

    return g

# -------------------- UI --------------------
st.title("🌳 家族樹（穩定版 Graphviz）")
st.caption("如果互動圖形一直出錯，這個版本以 Graphviz 繪圖，穩定度高、幾乎不會空白。也提供『清單模式』避免完全放棄畫圖。")

ensure_state()

tab_data, tab_viz, tab_list, tab_io = st.tabs(["🧾 資料", "🌿 圖形模式", "📚 清單模式", "📥 匯入/匯出"])

with tab_data:
    st.subheader("成員（People）")
    st.caption("必填欄位：id, name；性別（M/F）可用於著色；spouse_id 用來連結配偶。")
    people = st.data_editor(
        people_df(),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("ID"),
            "name": st.column_config.TextColumn("姓名"),
            "gender": st.column_config.TextColumn("性別(M/F)"),
            "birth": st.column_config.TextColumn("出生年"),
            "death": st.column_config.TextColumn("過世年"),
            "spouse_id": st.column_config.TextColumn("配偶ID"),
        },
        key="people_editor",
    )
    set_people(sanitize(people))

    st.subheader("親子關係（Parent → Child）")
    st.caption("每一列代表一條連結。若是雙親，請各自一列（父→子、母→子）。")
    links = st.data_editor(
        links_df(),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "parent_id": st.column_config.TextColumn("父/母 ID"),
            "child_id": st.column_config.TextColumn("子女 ID"),
        },
        key="links_editor",
    )
    set_links(sanitize(links))

    col = st.columns(3)
    if st.button("載入示範資料", type="secondary"):
        p, l = load_sample()
        set_people(pd.DataFrame(p))
        set_links(pd.DataFrame(l))
        st.success("已載入示範資料")

with tab_viz:
    st.subheader("Graphviz 圖形")
    orient = st.selectbox("排列方向", ["TB（由上到下）", "LR（由左到右）"])
    rd = "TB" if orient.startswith("TB") else "LR"
    g = render_graphviz(people_df(), links_df(), orientation=rd)
    st.graphviz_chart(g, use_container_width=True)
    st.info("若仍需完全不畫圖的模式，請切換到『清單模式』。")

with tab_list:
    st.subheader("家族清單（不畫圖）")
    dfp = people_df().copy()
    id2name = id_name_map(dfp)
    col1, col2 = st.columns(2)
    with col1:
        st.write("### 成員")
        st.dataframe(dfp[["id","name","gender","birth","death","spouse_id"]], use_container_width=True)
    with col2:
        st.write("### 親子關係")
        dfc = links_df().copy()
        dfc["父/母"] = dfc["parent_id"].map(id2name).fillna(dfc["parent_id"])
        dfc["子女"] = dfc["child_id"].map(id2name).fillna(dfc["child_id"])
        st.dataframe(dfc[["父/母","子女","parent_id","child_id"]], use_container_width=True)

with tab_io:
    st.subheader("匯出 JSON")
    st.download_button("下載 family.json", data=to_json_bytes(), file_name="family.json", mime="application/json")
    st.divider()
    st.subheader("匯入 JSON")
    up = st.file_uploader("選擇 JSON 檔", type=["json"])
    if up is not None:
        ok, msg = import_json(up.read())
        if ok:
            st.success(msg)
        else:
            st.error(msg)

st.caption("© 家族樹穩定版｜Graphviz + 清單模式")

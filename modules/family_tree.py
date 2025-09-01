
import uuid
import json
import pandas as pd
import streamlit as st

# 注意：graphviz 僅在實際繪圖時才 import（lazy import）

# ----------------------------- State & Helpers -----------------------------

def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

def _init_state():
    if "family_tree" not in st.session_state:
        st.session_state.family_tree = {"persons": {}, "marriages": {}}
    if "selected_mid" not in st.session_state:
        st.session_state.selected_mid = None
    if "_last_graph" not in st.session_state:
        st.session_state["_last_graph"] = None

def _reset_tree():
    st.session_state.family_tree = {"persons": {}, "marriages": {}}
    st.session_state.selected_mid = None
    st.session_state["_last_graph"] = None

# ----------------------------- Data Ops -----------------------------

def _add_person(name: str, gender: str, deceased: bool, note: str):
    pid = _uid("p")
    st.session_state.family_tree["persons"][pid] = {
        "id": pid,
        "name": name.strip(),
        "gender": gender,
        "deceased": bool(deceased),
        "note": note.strip(),
    }

def _delete_person(pid: str):
    persons = st.session_state.family_tree["persons"]
    if pid in persons:
        del persons[pid]

@st.cache_data(show_spinner=False)
def _df_from_tree(tree_json: str):
    """把 family_tree 轉為 DataFrame，供顯示用（以 JSON 當作 cache key）。"""
    data = json.loads(tree_json)
    persons = list(data.get("persons", {}).values())
    df = pd.DataFrame(persons) if persons else pd.DataFrame(columns=["id", "name", "gender", "deceased", "note"])
    return df

@st.cache_data(show_spinner=False)
def _build_graph_cached(tree_json: str):
    """以 JSON 作為 key，建立 graphviz.Digraph（只負責建圖，不繪製）。"""
    import graphviz
    data = json.loads(tree_json)

    g = graphviz.Digraph(format="png")
    g.attr(rankdir="TB")  # 垂直方向
    g.attr("node", shape="box", style="rounded,filled", color="#444444", fillcolor="#F7F7F7")

    # 節點
    for pid, p in data.get("persons", {}).items():
        label = p.get("name", pid)
        if p.get("deceased"):
            # 往生的以虛線邊框
            g.node(pid, label=label + " †", style="rounded,dashed,filled", fillcolor="#EFEFEF")
        else:
            g.node(pid, label=label)

    # TODO：若你有 marriages 結構，可在此加入婚姻連線與子女關係
    # 這裡先留簡易示意：不做邊，避免未知資料結構造成錯誤

    return g

def _build_and_store_graph():
    """計算並暫存 graph 於 session（按鈕觸發時才做）。"""
    tree = st.session_state.family_tree
    tree_key = json.dumps(tree, sort_keys=True, ensure_ascii=False)
    g = _build_graph_cached(tree_key)
    st.session_state["_last_graph"] = g

# ----------------------------- UI -----------------------------

def render():
    _init_state()
    st.title("🌳 家族樹")

    c1, c2 = st.columns([3,1])
    with c1:
        st.subheader("成員管理（提交後才更新、避免每次輸入就重跑）")
        with st.form("person_form", clear_on_submit=True):
            name = st.text_input("姓名*", placeholder="例如：王大明")
            gender = st.selectbox("性別*", options=["男", "女"])
            deceased = st.checkbox("是否往生")
            note = st.text_input("備註", placeholder="可留空")
            submitted = st.form_submit_button("新增成員")
            if submitted:
                if not name.strip():
                    st.warning("請輸入姓名")
                else:
                    _add_person(name, gender, deceased, note)
                    _safe_rerun()

    with c2:
        st.subheader("工具")
        if st.button("🔁 重置全部資料", type="secondary"):
            _reset_tree()
            _safe_rerun()

    # 清單顯示（快取資料表）
    tree_key = json.dumps(st.session_state.family_tree, sort_keys=True, ensure_ascii=False)
    df = _df_from_tree(tree_key)
    st.markdown("### 成員清單")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 刪除（集中操作，避免每列一個 input 造成頻繁重跑）
    if not df.empty:
        del_pid = st.selectbox("選擇要刪除的成員", options=["—"] + df["id"].tolist())
        if st.button("刪除所選成員", disabled=(del_pid == "—")):
            if del_pid != "—":
                _delete_person(del_pid)
                _safe_rerun()

    st.markdown("---")
    st.subheader("🖼 家族圖（展開/按鈕時才計算）")

    with st.expander("點我展開家族圖（展開時才繪製）", expanded=False):
        col_a, col_b = st.columns([1,2])
        with col_a:
            if st.button("生成 / 重新繪製 家族圖"):
                _build_and_store_graph()

        g = st.session_state.get("_last_graph")
        if g is not None:
            st.graphviz_chart(g, use_container_width=True)
        else:
            st.info("尚未生成，請按上方按鈕。")

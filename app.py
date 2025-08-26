import streamlit as st
import pandas as pd
import io
import json
from typing import Dict, Any

# =========================
# 版面與基礎設定
# =========================
st.set_page_config(
    page_title="永傳｜家族樹平台（極簡版）",
    page_icon="🌳",
    layout="wide"
)

# ---- Minimal CSS：加強版面層次與可讀性（低調不浮誇） ----
st.markdown("""
<style>
/* 全域字距與行高 */
html, body, [class*="css"]  { line-height:1.5; letter-spacing:0.01em; }

/* 主要標題間距 */
h1, h2, h3 { margin-top: 0.2rem; margin-bottom: 0.6rem; }

/* 卡片容器 */
.block-card {
  border: 1px solid #e6e6e6;
  border-radius: 14px;
  padding: 18px 16px;
  background: #fff;
  margin-bottom: 14px;
}

/* 次標題標籤 */
.subtle-tag {
  display: inline-block;
  font-size: 0.8rem;
  background: #f6f6f8;
  border: 1px solid #ececf1;
  padding: 2px 8px;
  border-radius: 999px;
  margin-left: 8px;
  color: #666;
}

/* 次要說明 */
.small-dim { color:#666; font-size:0.92rem; }

/* 表單項目間距 */
.stSelectbox, .stTextInput, .stTextArea, .stDateInput, .stFileUploader, .stRadio { margin-bottom: .4rem; }

/* 區隔線淡化 */
hr, .stDivider { opacity:.7; }
</style>
""", unsafe_allow_html=True)

# =========================
# State 初始化與工具函式
# =========================
def ensure_state():
    if "data" not in st.session_state:
        st.session_state.data = {
            "people": {},      # {id: {...}}
            "marriages": {},   # {id: {...}}
            "meta": {"title": "我的家族樹", "version": "0.1.1"}
        }
    if "next_ids" not in st.session_state:
        st.session_state.next_ids = {"person": 1, "marriage": 1}
    if "page" not in st.session_state:
        st.session_state.page = "首頁"

ensure_state()

def go(target_page: str):
    st.session_state.page = target_page
    st.toast(f"已切換至「{target_page}」")
    st.experimental_rerun()

def gen_person_id() -> str:
    pid = f"P{st.session_state.next_ids['person']}"
    st.session_state.next_ids['person'] += 1
    return pid

def gen_marriage_id() -> str:
    mid = f"M{st.session_state.next_ids['marriage']}"
    st.session_state.next_ids['marriage'] += 1
    return mid

def add_person(payload: Dict[str, Any]) -> str:
    pid = gen_person_id()
    st.session_state.data["people"][pid] = {
        "id": pid,
        "name": payload.get("name", ""),
        "gender": payload.get("gender", ""),
        "birth": payload.get("birth", ""),
        "death": payload.get("death", ""),
        "father_id": payload.get("father_id", ""),
        "mother_id": payload.get("mother_id", ""),
        "notes": payload.get("notes", "")
    }
    return pid

def add_marriage(spouse1_id: str, spouse2_id: str, date: str = "") -> str:
    mid = gen_marriage_id()
    st.session_state.data["marriages"][mid] = {
        "id": mid,
        "spouse1_id": spouse1_id,
        "spouse2_id": spouse2_id,
        "date": date
    }
    return mid

def clear_all():
    st.session_state.data = {"people": {}, "marriages": {}, "meta": {"title": "我的家族樹", "version": "0.1.1"}}
    st.session_state.next_ids = {"person": 1, "marriage": 1}

def load_demo():
    clear_all()
    gpa = add_person({"name": "外公", "gender": "M", "birth": "1935"})
    gma = add_person({"name": "外婆", "gender": "F", "birth": "1937"})
    add_marriage(gpa, gma, "1956-06-01")

    mom = add_person({"name": "媽媽", "gender": "F", "birth": "1965", "father_id": gpa, "mother_id": gma})
    dad = add_person({"name": "爸爸", "gender": "M", "birth": "1963"})
    add_marriage(mom, dad, "1988-09-12")

    me  = add_person({"name": "我", "gender": "F", "birth": "1990", "father_id": dad, "mother_id": mom})
    sis = add_person({"name": "姐姐", "gender": "F", "birth": "1988", "father_id": dad, "mother_id": mom})

def export_json_bytes() -> bytes:
    return json.dumps(st.session_state.data, ensure_ascii=False, indent=2).encode("utf-8")

def sync_next_ids_from_data():
    max_pid = 0
    for pid in st.session_state.data["people"].keys():
        if pid.startswith("P"):
            try:
                max_pid = max(max_pid, int(pid[1:]))
            except:
                pass
    max_mid = 0
    for mid in st.session_state.data["marriages"].keys():
        if mid.startswith("M"):
            try:
                max_mid = max(max_mid, int(mid[1:]))
            except:
                pass
    st.session_state.next_ids = {"person": max_pid + 1, "marriage": max_mid + 1}

def name_lookup_to_id(name: str) -> str:
    for pid, person in st.session_state.data["people"].items():
        if person.get("name") == name:
            return pid
    return ""

# Graphviz（若環境無安裝，給出替代說明）
def build_graphviz() -> str:
    from graphviz import Digraph
    dot = Digraph(comment='FamilyTree', format="svg")
    dot.attr(rankdir="TB", splines="spline", nodesep="0.4", ranksep="0.6")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="white",
             fontname="Taipei Sans TC, Noto Sans CJK TC, Arial")
    people = st.session_state.data["people"]
    marriages = st.session_state.data["marriages"]
    for pid, p in people.items():
        label = f"{p.get('name','')}\n({p.get('birth','')}{' - '+p.get('death','') if p.get('death') else ''})"
        dot.node(pid, label)
    for cid, child in people.items():
        father = child.get("father_id") or ""
        mother = child.get("mother_id") or ""
        for parent in [father, mother]:
            if parent and parent in people:
                dot.edge(parent, cid, arrowhead="normal")
    for mid, m in marriages.items():
        s1, s2 = m.get("spouse1_id"), m.get("spouse2_id")
        if s1 in people and s2 in people:
            dot.edge(s1, s2, dir="none", color="#888888")
    return dot.source

# =========================
# 側邊導覽（鎖定一致）
# =========================
with st.sidebar:
    st.markdown("### 🌳 永傳｜家族樹")
    st.caption("低調、好用、可擴充")
    # 與主畫面狀態同步的 radio
    page_selected = st.radio(
        "功能選單",
        ["首頁", "建立家族樹", "查看成員", "編輯資料", "匯入資料", "清除資料", "設定"],
        index=["首頁", "建立家族樹", "查看成員", "編輯資料", "匯入資料", "清除資料", "設定"].index(st.session_state.page),
        label_visibility="collapsed"
    )
    if page_selected != st.session_state.page:
        st.session_state.page = page_selected
        st.experimental_rerun()
    st.divider()
    st.caption(f"版本：{st.session_state.data['meta'].get('version', '0.1.1')}")

# =========================
# 頁面：首頁
# =========================
if st.session_state.page == "首頁":
    st.title("🌳 家族樹平台（極簡版）")
    st.write("專注 **乾淨與好用**。功能入口在左側；若剛開始，建議先載入示範資料、或直接新增成員。")

    colA, colB = st.columns([2, 1], vertical_alignment="center")

    with colA:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("快速開始")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("➕ 建立家族樹", use_container_width=True):
                go("建立家族樹")
        with c2:
            if st.button("👀 查看成員", use_container_width=True):
                go("查看成員")
        with c3:
            if st.button("📂 匯入資料", use_container_width=True):
                go("匯入資料")
        st.caption("小提示：如需快速體驗，可直接載入示範資料。")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("載入示範資料", type="primary", use_container_width=True):
                load_demo()
                st.success("已載入示範資料！")
        with d2:
            if st.button("清空所有資料", use_container_width=True):
                clear_all()
                st.warning("資料已清空。")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("目前概況")
        st.write(
            f"- 成員數：**{len(st.session_state.data['people'])}**　"
            f"- 婚姻數：**{len(st.session_state.data['marriages'])}**"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("匯出 / 匯入（JSON）")
        st.download_button(
            "下載目前資料（JSON）",
            data=export_json_bytes(),
            file_name="familytree.json",
            mime="application/json",
            use_container_width=True
        )
        up = st.file_uploader("匯入 JSON", type=["json"])
        if up:
            try:
                payload = json.load(up)
                st.session_state.data = payload
                sync_next_ids_from_data()
                st.success("JSON 匯入完成！")
            except Exception as e:
                st.error(f"JSON 匯入失敗：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：建立家族樹（新增人／婚姻）
# =========================
elif st.session_state.page == "建立家族樹":
    st.header("➕ 建立家族樹")
    tab1, tab2 = st.tabs(["新增成員", "新增婚姻"])

    with tab1:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("新增成員")
        with st.form("add_person_form", clear_on_submit=True):
            name = st.text_input("姓名*", placeholder="例如：王小明")
            gender = st.selectbox("性別*", ["", "M", "F"], index=0)
            birth = st.text_input("出生（YYYY 或 YYYY-MM-DD）", placeholder="例如：1985 或 1985-07-21")
            death = st.text_input("死亡（可留空）", placeholder="")
            people = st.session_state.data["people"]
            options = [""] + [f"{p['name']} ({pid})" for pid, p in people.items()]
            father_str = st.selectbox("父親（可選）", options, index=0)
            mother_str = st.selectbox("母親（可選）", options, index=0)
            notes = st.text_area("備註", placeholder="可留空")
            submitted = st.form_submit_button("新增")
            if submitted:
                if not name or not gender:
                    st.error("姓名與性別為必填。")
                else:
                    father_id = father_str.split("(")[-1][:-1] if "(" in father_str else ""
                    mother_id = mother_str.split("(")[-1][:-1] if "(" in mother_str else ""
                    pid = add_person({
                        "name": name.strip(),
                        "gender": gender,
                        "birth": birth.strip(),
                        "death": death.strip(),
                        "father_id": father_id,
                        "mother_id": mother_id,
                        "notes": notes.strip(),
                    })
                    st.success(f"新增成功：{name}（{pid}）")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("新增婚姻")
        people = st.session_state.data["people"]
        if not people:
            st.info("目前尚無成員，請先新增成員。")
        else:
            opts = [f"{p['name']} ({pid})" for pid, p in people.items()]
            a = st.selectbox("配偶 A", opts)
            b = st.selectbox("配偶 B", opts)
            date = st.text_input("結婚日期（可留空）", placeholder="YYYY-MM-DD")
            if st.button("建立婚姻"):
                a_id = a.split("(")[-1][:-1]
                b_id = b.split("(")[-1][:-1]
                if a_id == b_id:
                    st.error("請選擇不同的兩位成員。")
                else:
                    mid = add_marriage(a_id, b_id, date.strip())
                    st.success(f"婚姻已建立（{mid}）：{a} ↔ {b}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.subheader("目前家族樹（簡圖）<span class='subtle-tag'>即時更新</span>", unsafe_allow_html=True)
    if st.session_state.data["people"]:
        try:
            dot_src = build_graphviz()
            st.graphviz_chart(dot_src, use_container_width=True)
        except Exception as e:
            st.warning("尚未安裝 Graphviz，暫無法顯示樹圖。請先使用「查看成員」的表格進行管理。")
            st.caption(f"技術訊息：{e}")
    else:
        st.info("尚無資料。請先新增成員。")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：查看成員
# =========================
elif st.session_state.page == "查看成員":
    st.header("👀 查看成員")
    people = st.session_state.data["people"]
    if not people:
        st.info("尚無成員，請先到「建立家族樹」新增。")
    else:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("成員清單")
        df = pd.DataFrame(people.values())
        # 欄位排序（更直覺）
        cols = ["id","name","gender","birth","death","father_id","mother_id","notes"]
        df = df[[c for c in cols if c in df.columns]]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "下載成員（CSV）",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="people.csv",
            mime="text/csv"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("家族樹（簡圖）")
        try:
            dot_src = build_graphviz()
            st.graphviz_chart(dot_src, use_container_width=True)
        except Exception as e:
            st.warning("尚未安裝 Graphviz，暫無法顯示樹圖。")
            st.caption(f"技術訊息：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：編輯資料（簡易）
# =========================
elif st.session_state.page == "編輯資料":
    st.header("✏️ 編輯資料（簡易版）")
    people = st.session_state.data["people"]
    if not people:
        st.info("尚無資料。請先新增成員。")
    else:
        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader("選擇要編輯的成員")
        options = [f"{p['name']} ({pid})" for pid, p in people.items()]
        sel = st.selectbox("成員", options)
        pid = sel.split("(")[-1][:-1]
        person = st.session_state.data["people"][pid]
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        with st.form("edit_person_form"):
            name = st.text_input("姓名*", value=person.get("name",""))
            gender = st.selectbox("性別*", ["", "M", "F"], index=["","M","F"].index(person.get("gender","")))
            birth = st.text_input("出生", value=person.get("birth",""))
            death = st.text_input("死亡", value=person.get("death",""))
            options_parent = [""] + [f"{p['name']} ({ppid})" for ppid, p in people.items() if ppid != pid]
            def_fmt = lambda x: "" if not x else f"{people[x]['name']} ({x})" if x in people else ""
            father_def = def_fmt(person.get("father_id",""))
            mother_def = def_fmt(person.get("mother_id",""))
            father_sel = st.selectbox("父親", options_parent, index=options_parent.index(father_def) if father_def in options_parent else 0)
            mother_sel = st.selectbox("母親", options_parent, index=options_parent.index(mother_def) if mother_def in options_parent else 0)
            notes = st.text_area("備註", value=person.get("notes",""))

            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                update = st.form_submit_button("儲存")
            with col2:
                delete = st.form_submit_button("刪除此人", type="secondary")
            with col3:
                cancel = st.form_submit_button("取消")

        if update:
            if not name or not gender:
                st.error("姓名與性別為必填。")
            else:
                st.session_state.data["people"][pid].update({
                    "name": name.strip(),
                    "gender": gender,
                    "birth": birth.strip(),
                    "death": death.strip(),
                    "father_id": father_sel.split("(")[-1][:-1] if "(" in father_sel else "",
                    "mother_id": mother_sel.split("(")[-1][:-1] if "(" in mother_sel else "",
                    "notes": notes.strip()
                })
                st.success("已更新。")
        if delete:
            # 清除其作為父母的關聯
            for cid, c in list(st.session_state.data["people"].items()):
                if c.get("father_id") == pid:
                    st.session_state.data["people"][cid]["father_id"] = ""
                if c.get("mother_id") == pid:
                    st.session_state.data["people"][cid]["mother_id"] = ""
            # 移除涉及的婚姻
            for mid, m in list(st.session_state.data["marriages"].items()):
                if m.get("spouse1_id") == pid or m.get("spouse2_id") == pid:
                    del st.session_state.data["marriages"][mid]
            del st.session_state.data["people"][pid]
            st.warning("已刪除該成員與相關婚姻。")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：匯入資料（CSV/Excel/JSON）
# =========================
elif st.session_state.page == "匯入資料":
    st.header("📂 匯入資料")
    st.caption("建議先下載模板檔，填好再匯入。可選擇「合併」或「清空後匯入」。")

    def make_template_df() -> pd.DataFrame:
        return pd.DataFrame([
            {"id": "", "name": "我", "gender": "F", "birth": "1990-05-01", "death": "", "father_id": "", "mother_id": "", "notes": ""},
            {"id": "", "name": "爸爸", "gender": "M", "birth": "1963-01-01", "death": "", "father_id": "", "mother_id": "", "notes": ""},
            {"id": "", "name": "媽媽", "gender": "F", "birth": "1965-02-02", "death": "", "father_id": "", "mother_id": "", "notes": ""},
        ])

    def make_template_marriage_df() -> pd.DataFrame:
        return pd.DataFrame([
            {"id": "", "spouse1_id": "", "spouse1_name": "爸爸", "spouse2_id": "", "spouse2_name": "媽媽", "date": "1988-09-12"},
        ])

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.subheader("① 下載匯入模板")
    t1, t2 = st.columns(2)
    with t1:
        people_df = make_template_df()
        buf = io.BytesIO()
        people_df.to_excel(buf, index=False, sheet_name="people")
        st.download_button(
            "下載成員模板（Excel）",
            data=buf.getvalue(),
            file_name="people_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.download_button(
            "下載成員模板（CSV）",
            data=people_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="people_template.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("必要欄位：name, gender；可選：birth, death, father_id, mother_id, notes, id")
    with t2:
        mar_df = make_template_marriage_df()
        buf2 = io.BytesIO()
        mar_df.to_excel(buf2, index=False, sheet_name="marriages")
        st.download_button(
            "下載婚姻模板（Excel）",
            data=buf2.getvalue(),
            file_name="marriages_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.download_button(
            "下載婚姻模板（CSV）",
            data=mar_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="marriages_template.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("可用 spouse*_name 自動對應 id；或直接提供 spouse*_id。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.subheader("② 上傳匯入檔（CSV / Excel / JSON）")
    up = st.file_uploader("選擇檔案", type=["csv", "xlsx", "json"])
    mode = st.radio("匯入模式", ["合併到現有資料", "清空後再匯入"], horizontal=True)
    if up:
        try:
            if up.name.lower().endswith(".json"):
                payload = json.load(up)
                if mode == "清空後再匯入":
                    clear_all()
                st.session_state.data = payload
                sync_next_ids_from_data()
                st.success("JSON 匯入完成！")

            elif up.name.lower().endswith(".csv"):
                df = pd.read_csv(up)
                if mode == "清空後再匯入":
                    clear_all()
                for _, r in df.iterrows():
                    rid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["", "nan", "None"] else ""
                    payload = {
                        "name": str(r.get("name", "")).strip(),
                        "gender": str(r.get("gender", "")).strip(),
                        "birth": str(r.get("birth", "")).strip(),
                        "death": str(r.get("death", "")).strip(),
                        "father_id": str(r.get("father_id", "")).strip(),
                        "mother_id": str(r.get("mother_id", "")).strip(),
                        "notes": str(r.get("notes", "")).strip(),
                    }
                    if rid:
                        st.session_state.data["people"][rid] = {"id": rid, **payload}
                        if rid.startswith("P"):
                            try:
                                st.session_state.next_ids["person"] = max(st.session_state.next_ids["person"], int(rid[1:]) + 1)
                            except:
                                pass
                    else:
                        add_person(payload)
                st.success("CSV 匯入（成員）完成。")

            elif up.name.lower().endswith(".xlsx"):
                xls = pd.ExcelFile(up)
                if mode == "清空後再匯入":
                    clear_all()
                # people
                if "people" in xls.sheet_names:
                    dfp = pd.read_excel(xls, sheet_name="people")
                    for _, r in dfp.iterrows():
                        rid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["", "nan", "None"] else ""
                        payload = {
                            "name": str(r.get("name", "")).strip(),
                            "gender": str(r.get("gender", "")).strip(),
                            "birth": str(r.get("birth", "")).strip(),
                            "death": str(r.get("death", "")).strip(),
                            "father_id": str(r.get("father_id", "")).strip(),
                            "mother_id": str(r.get("mother_id", "")).strip(),
                            "notes": str(r.get("notes", "")).strip(),
                        }
                        if rid:
                            st.session_state.data["people"][rid] = {"id": rid, **payload}
                            if rid.startswith("P"):
                                try:
                                    st.session_state.next_ids["person"] = max(st.session_state.next_ids["person"], int(rid[1:]) + 1)
                                except:
                                    pass
                        else:
                            add_person(payload)
                    st.success("Excel 匯入（people）完成。")
                # marriages
                if "marriages" in xls.sheet_names:
                    dfm = pd.read_excel(xls, sheet_name="marriages")
                    for _, r in dfm.iterrows():
                        mid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["", "nan", "None"] else ""
                        s1 = str(r.get("spouse1_id", "")).strip()
                        s2 = str(r.get("spouse2_id", "")).strip()
                        s1n = str(r.get("spouse1_name", "")).strip()
                        s2n = str(r.get("spouse2_name", "")).strip()
                        date = str(r.get("date", "")).strip()
                        if not s1 and s1n:
                            s1 = name_lookup_to_id(s1n)
                        if not s2 and s2n:
                            s2 = name_lookup_to_id(s2n)
                        if s1 and s2:
                            if mid:
                                st.session_state.data["marriages"][mid] = {"id": mid, "spouse1_id": s1, "spouse2_id": s2, "date": date}
                                if mid.startswith("M"):
                                    try:
                                        st.session_state.next_ids["marriage"] = max(st.session_state.next_ids["marriage"], int(mid[1:]) + 1)
                                    except:
                                        pass
                            else:
                                add_marriage(s1, s2, date)
                    st.success("Excel 匯入（marriages）完成。")
        except Exception as e:
            st.error(f"匯入失敗：{e}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：清除資料（加入二次確認）
# =========================
elif st.session_state.page == "清除資料":
    st.header("🗑️ 清除資料")
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.warning("此動作會刪除目前所有成員與婚姻紀錄，請先備份。")
    col1, col2 = st.columns([1,1])
    with col1:
        st.download_button(
            "先備份目前資料（JSON）",
            data=export_json_bytes(),
            file_name="backup_familytree.json",
            mime="application/json",
            use_container_width=True
        )
    with col2:
        confirm = st.toggle("我已理解風險並確認清除")
        if st.button("清空所有資料", type="primary", disabled=not confirm, use_container_width=True):
            clear_all()
            st.success("已清空所有資料。")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 頁面：設定
# =========================
elif st.session_state.page == "設定":
    st.header("⚙️ 設定")
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    title = st.text_input("專案標題", value=st.session_state.data["meta"].get("title","我的家族樹"))
    if st.button("儲存設定", use_container_width=True):
        st.session_state.data["meta"]["title"] = title.strip() or "我的家族樹"
        st.success("設定已儲存。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.subheader("資料匯出")
    st.download_button(
        "下載 JSON",
        data=export_json_bytes(),
        file_name="familytree.json",
        mime="application/json",
        use_container_width=True
    )
    st.caption(
        f"目前成員數：{len(st.session_state.data['people'])}｜婚姻數：{len(st.session_state.data['marriages'])}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

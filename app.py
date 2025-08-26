import streamlit as st
import pandas as pd
import io, json, random
from typing import Dict, Any

# =========================
# 基礎設定
# =========================
st.set_page_config(
    page_title="永傳｜家族樹（清爽 + 小樂趣版）",
    page_icon="🌳",
    layout="wide"
)

# -------------------------
# 全域樣式（低調、清爽、有點溫度）
# -------------------------
BASE_CSS = """
<style>
:root{
  --brand:#4f8cff;
  --ink:#1f2328;
  --muted:#6b7280;
  --card:#ffffff;
  --soft:#f6f7fb;
  --line:#eceef3;
  --accent:#79ffe1;
  --male:#3b82f6;
  --female:#ec4899;
}
html,body,[class*="css"]{letter-spacing:.01em;}
h1,h2,h3{margin:.2rem 0 .6rem}
.small{font-size:.92rem;color:var(--muted)}
.hr{height:1px;background:var(--line);margin:.6rem 0 1rem}
.header-wrap{
  background: linear-gradient(135deg, #eef3ff 0%, #fff 100%);
  border:1px solid var(--line);
  border-radius:18px; padding:18px 20px; margin-bottom:14px;
}
.header-title{font-size:1.3rem;font-weight:700;color:var(--ink)}
.header-sub{color:var(--muted);margin-top:4px}
.wrap{display:block;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:14px}
.kbd{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:3px 8px;background:var(--soft);font-size:.85rem;color:var(--muted)}
.badge{display:inline-block;border:1px solid var(--line);background:#fff;border-radius:999px;padding:4px 10px;font-size:.8rem;color:#555}
.card{
  border:1px solid var(--line);border-radius:16px;padding:14px;background:#fff;
  transition: transform .08s ease; height:100%;
}
.card:hover{transform: translateY(-2px)}
.avatar{
  width:42px;height:42px;border-radius:999px;display:flex;align-items:center;justify-content:center;
  font-weight:700;color:#fff; background:#9ca3af;
}
.gender-m{background: var(--male)}
.gender-f{background: var(--female)}
.tag{font-size:.78rem;border:1px solid var(--line);border-radius:999px;padding:2px 8px;color:#555;background:#fafafa}
.grid{display:grid;grid-template-columns:repeat(auto-fill, minmax(260px,1fr)); gap:12px}
.row{display:flex;gap:10px;align-items:center}
.row-space{display:flex;gap:10px;align-items:center;justify-content:space-between}
.kit{display:flex;gap:8px;flex-wrap:wrap}
.btnlink a{color:var(--brand) !important;text-decoration:none !important;font-weight:600}
.note{background:#fff8e1;border:1px solid #ffe9a8;color:#7a5b00;border-radius:10px;padding:8px 10px;font-size:.92rem}
.footer-stat{color:var(--muted);font-size:.9rem}
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)

# =========================
# State & 工具
# =========================
def ensure_state():
    if "data" not in st.session_state:
        st.session_state.data = {
            "people": {}, "marriages": {},
            "meta": {"title": "我的家族樹", "version": "0.2.0"}
        }
    if "next_ids" not in st.session_state:
        st.session_state.next_ids = {"person": 1, "marriage": 1}
    if "page" not in st.session_state:
        st.session_state.page = "首頁"
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "卡片"

ensure_state()

def go(p): st.session_state.page = p; st.toast(f"→ {p}")

def gen_person_id():
    pid = f"P{st.session_state.next_ids['person']}"
    st.session_state.next_ids['person'] += 1
    return pid

def gen_marriage_id():
    mid = f"M{st.session_state.next_ids['marriage']}"
    st.session_state.next_ids['marriage'] += 1
    return mid

def add_person(obj: Dict[str, Any]) -> str:
    pid = gen_person_id()
    st.session_state.data["people"][pid] = {
        "id": pid,
        "name": obj.get("name","").strip(),
        "gender": obj.get("gender","").strip(),
        "birth": obj.get("birth","").strip(),
        "death": obj.get("death","").strip(),
        "father_id": obj.get("father_id","").strip(),
        "mother_id": obj.get("mother_id","").strip(),
        "notes": obj.get("notes","").strip(),
    }
    return pid

def add_marriage(a, b, date=""):
    mid = gen_marriage_id()
    st.session_state.data["marriages"][mid] = {"id": mid, "spouse1_id": a, "spouse2_id": b, "date": date}
    return mid

def export_json_bytes() -> bytes:
    return json.dumps(st.session_state.data, ensure_ascii=False, indent=2).encode("utf-8")

def clear_all():
    st.session_state.data = {"people": {}, "marriages": {}, "meta": {"title": "我的家族樹", "version": "0.2.0"}}
    st.session_state.next_ids = {"person": 1, "marriage": 1}

def load_demo():
    clear_all()
    gpa = add_person({"name":"外公","gender":"M","birth":"1935"})
    gma = add_person({"name":"外婆","gender":"F","birth":"1937"})
    add_marriage(gpa, gma, "1956-06-01")
    mom = add_person({"name":"媽媽","gender":"F","birth":"1965","father_id":gpa,"mother_id":gma})
    dad = add_person({"name":"爸爸","gender":"M","birth":"1963"})
    add_marriage(mom, dad, "1988-09-12")
    add_person({"name":"我","gender":"F","birth":"1990","father_id":dad,"mother_id":mom})
    add_person({"name":"姐姐","gender":"F","birth":"1988","father_id":dad,"mother_id":mom})

def initials(name:str)->str:
    if not name: return "?"
    s = "".join([w[0] for w in name.replace("（"," ").replace("("," ").split() if w])
    return (s[:2]).upper()

def build_graphviz():
    from graphviz import Digraph
    dot = Digraph(comment='FamilyTree', format="svg")
    dot.attr(rankdir="TB", splines="spline", nodesep="0.4", ranksep="0.6")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="white",
             fontname="Taipei Sans TC, Noto Sans CJK TC, Arial")
    P = st.session_state.data["people"]; M = st.session_state.data["marriages"]
    for pid, p in P.items():
        label = f"{p.get('name','')}\n({p.get('birth','')}{' - '+p.get('death','') if p.get('death') else ''})"
        dot.node(pid, label)
    for cid, c in P.items():
        for parent in [c.get("father_id",""), c.get("mother_id","")]:
            if parent and parent in P: dot.edge(parent, cid, arrowhead="normal")
    for mid, m in M.items():
        a, b = m.get("spouse1_id"), m.get("spouse2_id")
        if a in P and b in P: dot.edge(a, b, dir="none", color="#9aa3b2")
    return dot.source

def sync_next_ids_from_data():
    P = st.session_state.data["people"]; M = st.session_state.data["marriages"]
    mp = max([int(pid[1:]) for pid in P if pid.startswith("P")] + [0]) + 1
    mm = max([int(mid[1:]) for mid in M if mid.startswith("M")] + [0]) + 1
    st.session_state.next_ids = {"person": mp, "marriage": mm}

# =========================
# 側邊導覽
# =========================
with st.sidebar:
    st.markdown('<div class="header-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="header-title">🌳 永傳｜家族樹</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub small">低調、乾淨、帶點小樂趣</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    page = st.radio("功能選單",
        ["首頁","建立家族樹","查看成員","編輯資料","匯入資料","清除資料","設定"],
        index=["首頁","建立家族樹","查看成員","編輯資料","匯入資料","清除資料","設定"].index(st.session_state.page)
    )
    if page != st.session_state.page: go(page)

    st.divider()
    st.caption(f"版本：{st.session_state.data['meta'].get('version','0.2.0')}")

# =========================
# 首頁
# =========================
if st.session_state.page == "首頁":
    left, right = st.columns([2,1], vertical_alignment="center")
    with left:
        st.markdown('<div class="wrap">', unsafe_allow_html=True)
        st.subheader("開始你的家族小工作室")
        st.write("用最少步驟，把關係與故事慢慢長出來。")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("➕ 新增成員", use_container_width=True): go("建立家族樹")
        with c2:
            if st.button("👀 查看成員", use_container_width=True): go("查看成員")
        with c3:
            if st.button("📂 匯入資料", use_container_width=True): go("匯入資料")

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        # 小 checklist
        P = st.session_state.data["people"]
        steps = [
            ("新增第一位成員", len(P)>=1),
            ("連結父母/子女關係", any(v.get("father_id") or v.get("mother_id") for v in P.values())),
            ("建立一段婚姻關係", len(st.session_state.data["marriages"])>=1),
            ("成功匯出 JSON 備份", False) # 無法偵測；留作引導
        ]
        done = sum(1 for _, ok in steps if ok)
        st.write(f"完成度：**{done}/{len(steps)}**")
        for label, ok in steps:
            st.write(f"- [{'x' if ok else ' '}] {label}")
        if done in (1,3,4):
            st.balloons()
        # 小提醒
        tips = [
            "小提醒：用 Excel 模板匯入，多人資料會快很多。",
            "小提醒：成員名片右上角的彩色點點，是性別提示。",
            "小提醒：先畫直系，再補旁系，會更清楚！",
        ]
        st.info(random.choice(tips))
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="wrap">', unsafe_allow_html=True)
        st.subheader("匯出 / 匯入（JSON）")
        st.download_button("下載目前資料（JSON）", data=export_json_bytes(),
                           file_name="familytree.json", mime="application/json", use_container_width=True)
        up = st.file_uploader("匯入 JSON", type=["json"])
        if up:
            try:
                st.session_state.data = json.load(up)
                sync_next_ids_from_data()
                st.success("JSON 匯入完成！")
            except Exception as e:
                st.error(f"JSON 匯入失敗：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wrap">', unsafe_allow_html=True)
        st.subheader("目前統計")
        st.write(f"成員：**{len(st.session_state.data['people'])}**　婚姻：**{len(st.session_state.data['marriages'])}**")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 建立家族樹
# =========================
elif st.session_state.page == "建立家族樹":
    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    st.header("➕ 建立家族樹")
    tab1, tab2 = st.tabs(["新增成員","新增婚姻"])

    with tab1:
        with st.form("add-person", clear_on_submit=True):
            col1, col2, col3 = st.columns([2,1,1])
            name = col1.text_input("姓名*", placeholder="例如：王小明")
            gender = col2.selectbox("性別*", ["","M","F"], index=0)
            birth = col3.text_input("出生（YYYY 或 YYYY-MM-DD）")
            death = st.text_input("死亡（可留空）", placeholder="")
            P = st.session_state.data["people"]
            opts = [""] + [f"{p['name']} ({pid})" for pid, p in P.items()]
            c1, c2 = st.columns(2)
            father_str = c1.selectbox("父親（可選）", opts, index=0)
            mother_str = c2.selectbox("母親（可選）", opts, index=0)
            notes = st.text_area("備註（可留空）", placeholder="特殊關係、稱謂、住址等")
            ok = st.form_submit_button("新增")
            if ok:
                if not name or not gender:
                    st.error("姓名與性別必填。")
                else:
                    f = father_str.split("(")[-1][:-1] if "(" in father_str else ""
                    m = mother_str.split("(")[-1][:-1] if "(" in mother_str else ""
                    pid = add_person({"name":name,"gender":gender,"birth":birth,"death":death,
                                      "father_id":f,"mother_id":m,"notes":notes})
                    st.success(f"已新增：{name}（{pid}）")

    with tab2:
        P = st.session_state.data["people"]
        if not P:
            st.info("先新增成員，才能建立婚姻關係。")
        else:
            c1, c2, c3 = st.columns([2,2,1])
            opts = [f"{p['name']} ({pid})" for pid, p in P.items()]
            a = c1.selectbox("配偶 A", opts)
            b = c2.selectbox("配偶 B", opts)
            date = c3.text_input("結婚日期", placeholder="YYYY-MM-DD")
            if st.button("建立婚姻"):
                aid = a.split("(")[-1][:-1]
                bid = b.split("(")[-1][:-1]
                if aid == bid:
                    st.error("請選擇不同的兩位成員。")
                else:
                    mid = add_marriage(aid, bid, date.strip())
                    st.success(f"婚姻已建立（{mid}）：{a} ↔ {b}")
    st.markdown('</div>', unsafe_allow_html=True)

    # 簡圖
    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    st.subheader("家族樹（簡圖）")
    if st.session_state.data["people"]:
        try:
            dot = build_graphviz()
            st.graphviz_chart(dot, use_container_width=True)
        except Exception as e:
            st.warning("尚未安裝 Graphviz，暫無法顯示樹圖。請先用「查看成員」管理資料。")
            st.caption(f"技術訊息：{e}")
    else:
        st.info("尚無資料。")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 查看成員（卡片/表格切換）
# =========================
elif st.session_state.page == "查看成員":
    P = st.session_state.data["people"]
    st.header("👀 查看成員")
    if not P:
        st.info("尚無成員，請先到「建立家族樹」新增。")
    else:
        top = st.container()
        with top:
            left, right = st.columns([1.5,1])
            st.session_state.view_mode = left.segmented_control(
                "檢視模式", options=["卡片","表格"], default=st.session_state.view_mode
            )
            q = right.text_input("快速搜尋（姓名包含）", "")
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        # 篩選
        items = list(P.items())
        if q.strip():
            items = [(pid, p) for pid, p in items if q.strip() in p.get("name","")]

        if st.session_state.view_mode == "表格":
            st.markdown('<div class="wrap">', unsafe_allow_html=True)
            df = pd.DataFrame([p for _, p in items])
            cols = ["id","name","gender","birth","death","father_id","mother_id","notes"]
            df = df[[c for c in cols if c in df.columns]]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("下載成員（CSV）", data=df.to_csv(index=False).encode("utf-8-sig"),
                               file_name="people.csv", mime="text/csv")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # 卡片版
            st.markdown('<div class="grid">', unsafe_allow_html=True)
            for pid, p in items:
                avatar_class = "avatar gender-m" if p.get("gender")=="M" else ("avatar gender-f" if p.get("gender")=="F" else "avatar")
                gender_tag = "男" if p.get("gender")=="M" else ("女" if p.get("gender")=="F" else "—")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                colA, colB = st.columns([1,4])
                with colA:
                    st.markdown(f'<div class="{avatar_class}">{initials(p.get("name",""))}</div>', unsafe_allow_html=True)
                with colB:
                    st.markdown(f"**{p.get('name','') }**  <span class='badge'>{gender_tag}</span>", unsafe_allow_html=True)
                    span = f"{p.get('birth','')}"
                    if p.get("death"): span += f" – {p.get('death')}"
                    st.caption(span or "—")
                    with st.expander("更多"):
                        st.write(f"ID：{pid}")
                        st.write(f"父：{p.get('father_id','') or '—'}　母：{p.get('mother_id','') or '—'}")
                        st.write(p.get("notes","").strip() or "—")
                        if st.button("✏️ 去編輯這位", key=f"goedit-{pid}"):
                            st.session_state.page = "編輯資料"
                            st.session_state._preselect_pid = pid
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # 簡圖
        st.markdown('<div class="wrap">', unsafe_allow_html=True)
        st.subheader("家族樹（簡圖）")
        try:
            dot = build_graphviz()
            st.graphviz_chart(dot, use_container_width=True)
        except Exception as e:
            st.warning("尚未安裝 Graphviz，暫無法顯示樹圖。")
            st.caption(f"技術訊息：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 編輯資料
# =========================
elif st.session_state.page == "編輯資料":
    P = st.session_state.data["people"]
    st.header("✏️ 編輯資料")
    if not P:
        st.info("尚無資料。請先新增成員。")
    else:
        # 可由「查看成員」帶入指定 pid
        default_opt = 0
        options = [f"{p['name']} ({pid})" for pid, p in P.items()]
        if "_preselect_pid" in st.session_state:
            pre = st.session_state.pop("_preselect_pid")
            target = f"{P[pre]['name']} ({pre})" if pre in P else None
            if target and target in options:
                default_opt = options.index(target)

        pick = st.selectbox("選擇成員", options, index=default_opt)
        pid = pick.split("(")[-1][:-1]; person = P[pid]

        with st.form("edit-form"):
            c1,c2,c3 = st.columns([2,1,1])
            name = c1.text_input("姓名*", value=person.get("name",""))
            gender = c2.selectbox("性別*", ["","M","F"], index=["","M","F"].index(person.get("gender","")))
            birth = c3.text_input("出生", value=person.get("birth",""))
            death = st.text_input("死亡", value=person.get("death",""))
            # 父母選單
            parent_opts = [""] + [f"{p['name']} ({ppid})" for ppid, p in P.items() if ppid != pid]
            def_fmt = lambda x: "" if not x else f"{P[x]['name']} ({x})" if x in P else ""
            fdef, mdef = def_fmt(person.get("father_id","")), def_fmt(person.get("mother_id",""))
            father_sel = st.selectbox("父親", parent_opts, index=parent_opts.index(fdef) if fdef in parent_opts else 0)
            mother_sel = st.selectbox("母親", parent_opts, index=parent_opts.index(mdef) if mdef in parent_opts else 0)
            notes = st.text_area("備註", value=person.get("notes",""))
            colx, coly, colz = st.columns(3)
            update = colx.form_submit_button("儲存")
            delete = coly.form_submit_button("刪除此人", type="secondary")
            cancel = colz.form_submit_button("取消")

        if update:
            if not name or not gender:
                st.error("姓名與性別必填。")
            else:
                P[pid].update({
                    "name": name.strip(), "gender": gender, "birth": birth.strip(), "death": death.strip(),
                    "father_id": father_sel.split("(")[-1][:-1] if "(" in father_sel else "",
                    "mother_id": mother_sel.split("(")[-1][:-1] if "(" in mother_sel else "",
                    "notes": notes.strip()
                })
                st.success("已更新。")

        if delete:
            # 清除其作為父母關聯與婚姻
            for cid, c in list(P.items()):
                if c.get("father_id")==pid: P[cid]["father_id"]=""
                if c.get("mother_id")==pid: P[cid]["mother_id"]=""
            for mid, m in list(st.session_state.data["marriages"].items()):
                if m.get("spouse1_id")==pid or m.get("spouse2_id")==pid:
                    del st.session_state.data["marriages"][mid]
            del P[pid]
            st.warning("已刪除該成員與相關婚姻。")

# =========================
# 匯入資料
# =========================
elif st.session_state.page == "匯入資料":
    st.header("📂 匯入資料")
    st.caption("建議先下載模板檔，再上傳；可選擇「合併」或「清空後匯入」。")

    def make_people_tpl()->pd.DataFrame:
        return pd.DataFrame([
            {"id":"","name":"我","gender":"F","birth":"1990-05-01","death":"","father_id":"","mother_id":"","notes":""},
            {"id":"","name":"爸爸","gender":"M","birth":"1963-01-01","death":"","father_id":"","mother_id":"","notes":""},
            {"id":"","name":"媽媽","gender":"F","birth":"1965-02-02","death":"","father_id":"","mother_id":"","notes":""},
        ])
    def make_mar_tpl()->pd.DataFrame:
        return pd.DataFrame([
            {"id":"","spouse1_id":"","spouse1_name":"爸爸","spouse2_id":"","spouse2_name":"媽媽","date":"1988-09-12"}
        ])

    box = st.container()
    with box:
        c1,c2 = st.columns(2)
        # people
        ppl = make_people_tpl(); buf = io.BytesIO(); ppl.to_excel(buf, index=False, sheet_name="people")
        c1.download_button("下載成員模板（Excel）", data=buf.getvalue(),
                           file_name="people_template.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        c1.download_button("下載成員模板（CSV）",
                           data=ppl.to_csv(index=False).encode("utf-8-sig"),
                           file_name="people_template.csv", mime="text/csv",
                           use_container_width=True)
        # marriages
        mar = make_mar_tpl(); buf2 = io.BytesIO(); mar.to_excel(buf2, index=False, sheet_name="marriages")
        c2.download_button("下載婚姻模板（Excel）", data=buf2.getvalue(),
                           file_name="marriages_template.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        c2.download_button("下載婚姻模板（CSV）",
                           data=mar.to_csv(index=False).encode("utf-8-sig"),
                           file_name="marriages_template.csv", mime="text/csv",
                           use_container_width=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    up = st.file_uploader("選擇上傳檔案（CSV / Excel / JSON）", type=["csv","xlsx","json"])
    mode = st.radio("匯入模式", ["合併到現有資料", "清空後再匯入"], horizontal=True)

    def name_lookup_to_id(name: str) -> str:
        for pid, p in st.session_state.data["people"].items():
            if p.get("name")==name: return pid
        return ""

    if up:
        try:
            if up.name.lower().endswith(".json"):
                payload = json.load(up)
                if mode == "清空後再匯入": clear_all()
                st.session_state.data = payload
                sync_next_ids_from_data()
                st.success("JSON 匯入完成！")

            elif up.name.lower().endswith(".csv"):
                df = pd.read_csv(up)
                if mode == "清空後再匯入": clear_all()
                for _, r in df.iterrows():
                    rid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["","nan","None"] else ""
                    payload = {
                        "name": str(r.get("name","")).strip(), "gender": str(r.get("gender","")).strip(),
                        "birth": str(r.get("birth","")).strip(), "death": str(r.get("death","")).strip(),
                        "father_id": str(r.get("father_id","")).strip(), "mother_id": str(r.get("mother_id","")).strip(),
                        "notes": str(r.get("notes","")).strip()
                    }
                    if rid:
                        st.session_state.data["people"][rid] = {"id": rid, **payload}
                        if rid.startswith("P"):
                            try: st.session_state.next_ids["person"] = max(st.session_state.next_ids["person"], int(rid[1:])+1)
                            except: pass
                    else:
                        add_person(payload)
                st.success("CSV 匯入（成員）完成。")

            elif up.name.lower().endswith(".xlsx"):
                xls = pd.ExcelFile(up)
                if mode == "清空後再匯入": clear_all()
                if "people" in xls.sheet_names:
                    dfp = pd.read_excel(xls, sheet_name="people")
                    for _, r in dfp.iterrows():
                        rid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["","nan","None"] else ""
                        payload = {
                            "name": str(r.get("name","")).strip(), "gender": str(r.get("gender","")).strip(),
                            "birth": str(r.get("birth","")).strip(), "death": str(r.get("death","")).strip(),
                            "father_id": str(r.get("father_id","")).strip(), "mother_id": str(r.get("mother_id","")).strip(),
                            "notes": str(r.get("notes","")).strip()
                        }
                        if rid:
                            st.session_state.data["people"][rid] = {"id": rid, **payload}
                            if rid.startswith("P"):
                                try: st.session_state.next_ids["person"] = max(st.session_state.next_ids["person"], int(rid[1:])+1)
                                except: pass
                        else:
                            add_person(payload)
                    st.success("Excel 匯入（people）完成。")
                if "marriages" in xls.sheet_names:
                    dfm = pd.read_excel(xls, sheet_name="marriages")
                    for _, r in dfm.iterrows():
                        mid = str(r.get("id")) if pd.notna(r.get("id")) and str(r.get("id")).strip() not in ["","nan","None"] else ""
                        s1 = str(r.get("spouse1_id","")).strip(); s2 = str(r.get("spouse2_id","")).strip()
                        s1n = str(r.get("spouse1_name","")).strip(); s2n = str(r.get("spouse2_name","")).strip()
                        date = str(r.get("date","")).strip()
                        if not s1 and s1n: s1 = name_lookup_to_id(s1n)
                        if not s2 and s2n: s2 = name_lookup_to_id(s2n)
                        if s1 and s2:
                            if mid:
                                st.session_state.data["marriages"][mid] = {"id": mid, "spouse1_id": s1, "spouse2_id": s2, "date": date}
                                if mid.startswith("M"):
                                    try: st.session_state.next_ids["marriage"] = max(st.session_state.next_ids["marriage"], int(mid[1:])+1)
                                    except: pass
                            else:
                                add_marriage(s1, s2, date)
                    st.success("Excel 匯入（marriages）完成。")
        except Exception as e:
            st.error(f"匯入失敗：{e}")

# =========================
# 清除資料
# =========================
elif st.session_state.page == "清除資料":
    st.header("🗑️ 清除資料")
    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    st.warning("此動作會刪除所有成員與婚姻紀錄，請先備份。")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("下載備份（JSON）", data=export_json_bytes(),
                           file_name="backup_familytree.json", mime="application/json", use_container_width=True)
    with c2:
        ok = st.toggle("我已理解風險並確認刪除")
        st.button("清空所有資料", type="primary", disabled=not ok, use_container_width=True, on_click=clear_all)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 設定
# =========================
elif st.session_state.page == "設定":
    st.header("⚙️ 設定")
    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    title = st.text_input("專案標題", value=st.session_state.data["meta"].get("title","我的家族樹"))
    if st.button("儲存設定", use_container_width=True):
        st.session_state.data["meta"]["title"] = title.strip() or "我的家族樹"
        st.success("已儲存。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    st.subheader("資料匯出")
    st.download_button("下載 JSON", data=export_json_bytes(),
                       file_name="familytree.json", mime="application/json", use_container_width=True)
    st.caption(f"成員：{len(st.session_state.data['people'])}　婚姻：{len(st.session_state.data['marriages'])}")
    st.markdown('</div>', unsafe_allow_html=True)

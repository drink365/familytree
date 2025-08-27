# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import uuid, os, json, sqlite3
from datetime import datetime, timedelta, timezone
import random
import pandas as pd

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="影響力傳承平台｜互動原型（MVP）",
    page_icon="🌟",
    layout="wide",
)
TZ = timezone(timedelta(hours=8))  # 台灣時區（UTC+8）

def inject_analytics():
    # 可選：在 secrets 設定 PLAUSIBLE_DOMAIN="gracefo.com"（或你的網域）
    try:
        domain = st.secrets["PLAUSIBLE_DOMAIN"]
        import streamlit.components.v1 as components
        components.html(
            f"""<script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>""",
            height=0,
        )
    except Exception:
        pass

inject_analytics()

# =========================
# DB 初始化
# =========================
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "legacy.db")
os.makedirs(DB_DIR, exist_ok=True)

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY,
        family_name TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS assets(
        user_id TEXT PRIMARY KEY,
        json TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS plans(
        user_id TEXT PRIMARY KEY,
        json TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS versions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        family_name TEXT,
        assets_json TEXT,
        plan_json TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS badges(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        name TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    conn.commit()
    return conn

CONN = init_db()

def meta_get(key, default=None):
    cur = CONN.cursor()
    cur.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = cur.fetchone()
    return (json.loads(row[0]) if row else default)

def meta_set(key, value):
    cur = CONN.cursor()
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, json.dumps(value)))
    CONN.commit()

# 設定共享名額與截止（每月 10 名）
def setup_monthly_challenge():
    now = datetime.now(TZ)
    deadline = meta_get("consult_deadline")
    if deadline:
        deadline = datetime.fromisoformat(deadline)
    if not deadline or now > deadline:
        # 設定本月截止為當月最後一日 23:59
        first_of_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        last_of_this = first_of_next - timedelta(seconds=1)
        last_of_this = last_of_this.replace(hour=23, minute=59, second=59, microsecond=0)
        meta_set("consult_deadline", last_of_this.isoformat())
        meta_set("consult_slots_total", 10)
        meta_set("consult_slots_left", 10)

setup_monthly_challenge()

def consult_state():
    return {
        "deadline": datetime.fromisoformat(meta_get("consult_deadline")),
        "slots_total": meta_get("consult_slots_total", 10),
        "slots_left": meta_get("consult_slots_left", 10),
    }

def consult_decrement():
    cur = CONN.cursor()
    left = meta_get("consult_slots_left", 0)
    if left <= 0:
        return False
    meta_set("consult_slots_left", left - 1)
    return True

# =========================
# 使用者識別（?user=）
# =========================
def get_qs():
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()

def set_qs(params: dict):
    try:
        st.query_params.clear()
        st.query_params.update(params)
    except Exception:
        st.experimental_set_query_params(**params)

def get_or_create_user_id():
    qs = get_qs()
    incoming = qs.get("user")
    if isinstance(incoming, list):  # 兼容舊版回傳型態
        incoming = incoming[0] if incoming else None
    if incoming:
        st.session_state["user_id"] = incoming
        return incoming
    # 沒有就新建
    uid = "u_" + str(uuid.uuid4())[:8]
    st.session_state["user_id"] = uid
    qs["user"] = uid
    set_qs(qs)
    return uid

USER_ID = get_or_create_user_id()

# =========================
# 預設值
# =========================
DEFAULT_ASSETS = {"公司股權":0, "不動產":0, "金融資產":0, "保單":0, "海外資產":0, "其他":0}
DEFAULT_PLAN = {"股權給下一代":40, "保單留配偶":30, "慈善信託":10, "留現金緊急金":20}

# =========================
# 使用者資料載入/儲存
# =========================
def user_get():
    cur = CONN.cursor()
    cur.execute("SELECT id,family_name,created_at FROM users WHERE id=?", (USER_ID,))
    return cur.fetchone()

def user_create_if_missing():
    if not user_get():
        cur = CONN.cursor()
        cur.execute(
            "INSERT INTO users(id,family_name,created_at) VALUES(?,?,?)",
            (USER_ID, "", datetime.now(TZ).isoformat()),
        )
        CONN.commit()

def family_name_get():
    row = user_get()
    return row[1] if row else ""

def family_name_set(name: str):
    cur = CONN.cursor()
    cur.execute("UPDATE users SET family_name=? WHERE id=?", (name, USER_ID))
    CONN.commit()

def assets_get():
    cur = CONN.cursor()
    cur.execute("SELECT json FROM assets WHERE user_id=?", (USER_ID,))
    row = cur.fetchone()
    return (json.loads(row[0]) if row else DEFAULT_ASSETS.copy())

def assets_set(data: dict):
    cur = CONN.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO assets(user_id,json,updated_at) VALUES(?,?,?)",
        (USER_ID, json.dumps(data), datetime.now(TZ).isoformat()),
    )
    CONN.commit()

def plan_get():
    cur = CONN.cursor()
    cur.execute("SELECT json FROM plans WHERE user_id=?", (USER_ID,))
    row = cur.fetchone()
    return (json.loads(row[0]) if row else DEFAULT_PLAN.copy())

def plan_set(data: dict):
    cur = CONN.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO plans(user_id,json,updated_at) VALUES(?,?,?)",
        (USER_ID, json.dumps(data), datetime.now(TZ).isoformat()),
    )
    CONN.commit()

def version_insert(family, assets, plan):
    cur = CONN.cursor()
    cur.execute(
        "INSERT INTO versions(user_id,family_name,assets_json,plan_json,created_at) VALUES(?,?,?,?,?)",
        (USER_ID, family, json.dumps(assets), json.dumps(plan), datetime.now(TZ).isoformat()),
    )
    CONN.commit()

def versions_list():
    cur = CONN.cursor()
    cur.execute(
        "SELECT family_name,assets_json,plan_json,created_at FROM versions WHERE user_id=? ORDER BY id DESC",
        (USER_ID,),
    )
    rows = cur.fetchall()
    out = []
    for fam, aj, pj, ts in rows:
        out.append({
            "family": fam,
            "assets": json.loads(aj),
            "plan": json.loads(pj),
            "time": datetime.fromisoformat(ts),
        })
    return out

def badge_add(name: str):
    # 檢查是否已有同名徽章
    cur = CONN.cursor()
    cur.execute("SELECT 1 FROM badges WHERE user_id=? AND name=?", (USER_ID, name))
    if cur.fetchone():
        return
    cur.execute(
        "INSERT INTO badges(user_id,name,created_at) VALUES(?,?,?)",
        (USER_ID, name, datetime.now(TZ).isoformat()),
    )
    CONN.commit()

def badges_list():
    cur = CONN.cursor()
    cur.execute("SELECT name FROM badges WHERE user_id=? ORDER BY id", (USER_ID,))
    return [r[0] for r in cur.fetchall()]

def booking_insert():
    cur = CONN.cursor()
    cur.execute(
        "INSERT INTO bookings(user_id,created_at) VALUES(?,?)",
        (USER_ID, datetime.now(TZ).isoformat()),
    )
    CONN.commit()

# =========================
# 初始化 Session State（混合 DB）
# =========================
def init_state():
    user_create_if_missing()
    ss = st.session_state
    ss.setdefault("mission_ack", False)
    ss.setdefault("profile_done", False)
    ss.setdefault("assets_done", False)
    ss.setdefault("plan_done", False)
    ss.setdefault("quiz_done", False)
    ss.setdefault("advisor_booked", False)
    ss.setdefault("tips_unlocked", [])

    # 從 DB 帶入
    ss.setdefault("family_name", family_name_get())
    ss.setdefault("assets", assets_get())
    ss.setdefault("plan", plan_get())

    # 稅率示意值（可調）
    ss.setdefault("risk_rate_no_plan", 0.18)
    ss.setdefault("risk_rate_with_plan", 0.10)

init_state()

# =========================
# 工具與文案
# =========================
def human_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M")

def add_badge(name: str):
    badge_add(name)

def progress_score():
    checks = [
        st.session_state.mission_ack,
        st.session_state.profile_done,
        st.session_state.assets_done,
        st.session_state.plan_done,
        st.session_state.quiz_done,
        st.session_state.advisor_booked,
    ]
    return int(sum(checks) / len(checks) * 100)

def guidance_note(text):
    st.markdown(f":bulb: **引導**：{text}")

def section_title(emoji, title):
    st.markdown(f"### {emoji} {title}")

def chip(text):
    st.markdown(
        "<span style='padding:4px 8px;border-radius:12px;border:1px solid #ddd;'> "
        + text + " </span>",
        unsafe_allow_html=True
    )

RANDOM_TIPS = [
    "家族憲章可明確價值觀與決策機制，降低紛爭風險。",
    "跨境資產需同步考量不同稅制的課稅時點與估值規則。",
    "保單身故金可快速補足遺產稅與流動性缺口。",
    "先做資產盤點，再決定工具；先談價值觀，再定分配比例。",
    "信託可把『錢給誰、何時給、給多少、何條件下給』寫清楚。",
    "『用不完的錢如何安心交棒』是第三階段的關鍵提問。",
]

def unlock_random_tip():
    left = [t for t in RANDOM_TIPS if t not in st.session_state.tips_unlocked]
    if not left:
        return None
    tip = random.choice(left)
    st.session_state.tips_unlocked.append(tip)
    return tip

# =========================
# 側邊欄：進度、徽章、協作
# =========================
with st.sidebar:
    st.markdown("## 🧭 目前進度")
    prog = progress_score()
    st.progress(prog, text=f"完成度 {prog}%")
    st.caption("完成各區塊互動以提升完成度。")

    st.markdown("## 🏅 徽章")
    got_badges = badges_list()
    if not got_badges:
        st.caption("尚未解鎖徽章，完成任務即可獲得獎章。")
    else:
        for b in got_badges:
            chip(f"🏅 {b}")

    st.divider()
    st.markdown("**邀請家族成員共建（示意）**")
    st.code(f"{st.get_option('server.baseUrlPath') or ''}?user={USER_ID}")
    st.caption("將此連結分享給家族成員共同編輯。")

# =========================
# 頁面標頭
# =========================
st.title("🌟 影響力傳承平台｜互動原型（MVP）")
st.caption("以『準備與從容』為精神，讓家族影響力得以溫暖延續。")

tabs = st.tabs([
    "1 使命啟動",
    "2 進度與成就",
    "3 策略沙盒",
    "4 專屬與版本",
    "5 協作與關係",
    "6 限時與名額",
    "7 測驗與知識卡",
    "8 風險對比",
])

# =========================
# 1. 使命啟動
# =========================
with tabs[0]:
    section_title("📜", "家族使命與起心動念")
    st.markdown("""
**讓家族的愛與價值觀，跨越世代，溫柔延續。**  
本平台以家族傳承為核心，協助您用**可視化工具**整合 **法 / 稅 / 財**，
把「用不完的錢如何安心交棒」說清楚、做踏實。
""")
    colA, colB = st.columns([3,2])
    with colA:
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        st.caption("上線時可換成品牌短片或動態 Banner。")
    with colB:
        st.info("任務卡｜今天目標：完成『家族資料 + 資產盤點 + 初版策略』，解鎖「家族建築師」徽章。")
        guidance_note("點選上方分頁依序完成互動。")

    if st.button("我已理解並願意開始 ▶️", use_container_width=True):
        st.session_state.mission_ack = True
        add_badge("使命啟動者")
        st.success("任務已啟動，獲得徽章：使命啟動者！")

# =========================
# 2. 進度與成就
# =========================
with tabs[1]:
    section_title("🧱", "基本資料與資產盤點")
    st.write("完成以下步驟可提升完成度並解鎖徽章。")

    st.subheader("Step 1｜建立家族識別")
    fam = st.text_input("家族名稱（用於封面與報告）", value=st.session_state.family_name, placeholder="例如：黃氏家族")
    if st.button("儲存家族識別", key="btn_profile"):
        name = (fam or "").strip()
        st.session_state.family_name = name
        family_name_set(name)
        st.session_state.profile_done = bool(name)
        if name:
            add_badge("家族識別完成")
            st.success("已儲存。徽章：家族識別完成")
        else:
            st.warning("請輸入家族名稱後再儲存。")

    st.divider()
    st.subheader("Step 2｜輸入資產結構（萬元）")
    a1, a2, a3 = st.columns(3)
    a4, a5, a6 = st.columns(3)
    st.session_state.assets["公司股權"] = a1.number_input("公司股權", 0, 10_000_000, st.session_state.assets["公司股權"])
    st.session_state.assets["不動產"]   = a2.number_input("不動產",   0, 10_000_000, st.session_state.assets["不動產"])
    st.session_state.assets["金融資產"] = a3.number_input("金融資產", 0, 10_000_000, st.session_state.assets["金融資產"])
    st.session_state.assets["保單"]     = a4.number_input("保單",     0, 10_000_000, st.session_state.assets["保單"])
    st.session_state.assets["海外資產"] = a5.number_input("海外資產", 0, 10_000_000, st.session_state.assets["海外資產"])
    st.session_state.assets["其他"]     = a6.number_input("其他",     0, 10_000_000, st.session_state.assets["其他"])

    if st.button("完成資產盤點 ✅", key="btn_assets"):
        total = sum(st.session_state.assets.values())
        if total > 0:
            assets_set(st.session_state.assets)
            st.session_state.assets_done = True
            add_badge("家族建築師")
            st.success(f"已完成資產盤點（總額 {total:,} 萬元）。徽章：家族建築師")
        else:
            st.warning("尚未輸入任何資產金額。")

    with st.expander("查看我目前的完成度與徽章"):
        st.metric("目前完成度", f"{progress_score()}%")
        have = badges_list()
        st.write("徽章：", ", ".join(have) if have else "尚無")

# =========================
# 3. 策略沙盒
# =========================
with tabs[2]:
    section_title("🧪", "策略配置（拖拉比例 / 即時回饋）")
    st.write("自由調整分配比例，系統即時回饋稅務與流動性（示意模型）。")

    colL, colR = st.columns([3,2])
    with colL:
        with st.form("plan_form"):
            p1 = st.slider("股權給下一代（%）", 0, 100, st.session_state.plan["股權給下一代"])
            p2 = st.slider("保單留配偶（%）",   0, 100, st.session_state.plan["保單留配偶"])
            p3 = st.slider("慈善信託（%）",     0, 100, st.session_state.plan["慈善信託"])
            p4 = st.slider("留現金緊急金（%）", 0, 100, st.session_state.plan["留現金緊急金"])
            submitted = st.form_submit_button("更新策略並模擬")
        if submitted:
            total_pct = p1 + p2 + p3 + p4
            if total_pct != 100:
                st.error(f"目前總和為 {total_pct}%，請調整至 100%。")
            else:
                st.session_state.plan.update({
                    "股權給下一代": p1,
                    "保單留配偶": p2,
                    "慈善信託": p3,
                    "留現金緊急金": p4
                })
                plan_set(st.session_state.plan)
                st.session_state.plan_done = True
                add_badge("策略設計師")
                st.success("已更新策略。徽章：策略設計師")

    with colR:
        total_asset = sum(st.session_state.assets.values())
        st.subheader("即時回饋（示意）")
        if total_asset <= 0:
            st.info("請先於『進度與成就』完成資產盤點。")
        else:
            plan = st.session_state.plan
            base_rate = st.session_state.risk_rate_with_plan
            # 慈善信託比例越高，稅務效率越佳（示意）
            effective_rate = max(0.05, base_rate - (plan["慈善信託"]/100)*0.03)
            est_tax = int(total_asset * 10_000 * effective_rate)  # 萬元→元
            cash_liq = int(total_asset * 10_000 * (
                plan["留現金緊急金"]/100 + plan["保單留配偶"]/100*0.8
            ))

            st.metric("估算遺產稅（元）", f"{est_tax:,}")
            st.metric("估算可動用現金（元）", f"{cash_liq:,}")
            guidance_note("可增加『保單留配偶』或『留現金緊急金』比例以強化流動性。")

# =========================
# 4. 專屬與版本
# =========================
with tabs[3]:
    section_title("📁", "我的專屬藍圖（版本管理 / 下載示意）")
    colL, colR = st.columns([2,3])

    with colL:
        st.text_input("家族名稱", value=st.session_state.family_name, disabled=True)
        st.json(st.session_state.assets, expanded=False)
        st.json(st.session_state.plan, expanded=False)

        # 下載示意（文字檔）
        report_txt = f"""家族：{st.session_state.family_name or '未命名家族'}
時間：{human_time(datetime.now(TZ))}
資產（萬）：{st.session_state.assets}
策略（%）：{st.session_state.plan}
"""
        st.download_button("下載簡版報告（.txt）", report_txt, file_name="legacy_report.txt")

        if st.button("保存為新版本 💾", use_container_width=True):
            version_insert(st.session_state.family_name, st.session_state.assets, st.session_state.plan)
            add_badge("版本管理者")
            st.success("已保存版本。徽章：版本管理者")

    with colR:
        st.subheader("版本記錄")
        vers = versions_list()
        if not vers:
            st.caption("尚無版本記錄。完成前述步驟後，可在此保存版本。")
        else:
            data = [{
                "時間": human_time(v["time"]),
                "家族": v["family"] or "未命名家族",
                "股權給下一代%": v["plan"]["股權給下一代"],
                "保單留配偶%": v["plan"]["保單留配偶"],
                "慈善信託%": v["plan"]["慈善信託"],
                "留現金緊急金%": v["plan"]["留現金緊急金"],
                "資產總額(萬)": sum(v["assets"].values())
            } for v in vers]
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

# =========================
# 5. 協作與關係
# =========================
with tabs[4]:
    section_title("👥", "家族共建與顧問協作（示意）")
    st.write("把上方側欄的專屬連結分享給家族成員，即可一人一連結共同編輯（示意設計，實務可加權限）。")

    with st.chat_message("user"):
        st.write("我覺得『慈善信託』比例可以再拉高一點，因為媽媽很在意回饋社會。")
    with st.chat_message("assistant"):
        st.write("收到～我會在策略會議上把這一點列為優先討論。")

    add_badge("協作啟動者")

# =========================
# 6. 限時與名額（共享）
# =========================
with tabs[5]:
    section_title("⏳", "限時挑戰與預約名額（全站共享）")
    cs = consult_state()
    now = datetime.now(TZ)
    remain = max(0, int((cs["deadline"] - now).total_seconds()))

    colL, colR = st.columns(2)
    with colL:
        st.subheader("🎯 本月挑戰")
        st.write("在**截止前**完成『資產盤點 + 策略初稿 + 版本保存』，可獲得 30 分鐘顧問諮詢。")
        st.metric("剩餘名額", cs["slots_left"])
        st.metric("截止時間", human_time(cs["deadline"]))
        st.caption("名額與倒數為全站共享（DB 中央管理）。")

        if cs["slots_left"] > 0:
            if st.button("我要預約諮詢 📅", use_container_width=True):
                if consult_decrement():
                    booking_insert()
                    st.session_state.advisor_booked = True
                    add_badge("行動派")
                    st.success("已預約成功！徽章：行動派")
                else:
                    st.error("剛剛被搶走了，請稍後再試或下月再來～")
        else:
            st.error("本月名額已滿，請下月再試。")

    with colR:
        st.subheader("⏱️ 倒數（示意）")
        st.write(f"距離截止約 **{remain} 秒**")
        guidance_note("活動、名額、倒數能有效提升行動率，但要避免造成過度焦慮感。")

# =========================
# 7. 測驗與知識卡
# =========================
with tabs[6]:
    section_title("🎁", "小測驗 & 驚喜知識卡")
    st.write("完成 3 題小測驗，即可解鎖 1 則知識卡。")

    with st.form("quiz_form"):
        q1 = st.radio("Q1. 信託可把『何時給、給誰、給多少、何條件下給』寫清楚嗎？", ["可以", "不行"], index=0)
        q2 = st.radio("Q2. 保單身故金是否可作為遺產稅與流動性缺口的緩衝？", ["是", "否"], index=0)
        q3 = st.radio("Q3. 跨境資產規劃需留意不同法域的課稅時點與估值規則？", ["需要", "不需要"], index=0)
        ok = st.form_submit_button("提交")
    if ok:
        correct = (q1=="可以") + (q2=="是") + (q3=="需要")
        if correct == 3:
            st.success("全對！恭喜完成小測驗。")
            st.session_state.quiz_done = True
            add_badge("好奇探索者")
            tip = unlock_random_tip()
            if tip:
                st.info(f"🎉 解鎖知識卡：{tip}")
            else:
                st.caption("（你已解鎖所有知識卡！）")
        else:
            st.warning(f"目前答對 {correct}/3 題，再試試！")

    if st.session_state.tips_unlocked:
        st.markdown("**已解鎖知識卡**")
        for t in st.session_state.tips_unlocked:
            chip(t)

# =========================
# 8. 風險對比
# =========================
with tabs[7]:
    section_title("⚖️", "未規劃 vs 已規劃｜稅負對比（示意）")
    total_asset = sum(st.session_state.assets.values())
    if total_asset <= 0:
        st.info("請先完成『進度與成就』分頁的資產盤點。")
    else:
        tax_no  = int(total_asset * 10_000 * st.session_state.risk_rate_no_plan)
        tax_yes = int(total_asset * 10_000 * st.session_state.risk_rate_with_plan)
        save    = tax_no - tax_yes

        colA, colB, colC = st.columns(3)
        colA.metric("未規劃估算稅額（元）", f"{tax_no:,}")
        colB.metric("已規劃估算稅額（元）", f"{tax_yes:,}")
        colC.metric("估計節省（元）", f"{save:,}")

        df = pd.DataFrame({"稅額": [tax_no, tax_yes]}, index=["未規劃", "已規劃"])
        st.bar_chart(df, use_container_width=True)

        guidance_note("把『沒有規劃的後果』具象化，有助於推動決策；同時保持尊重與安心的語氣。")

# =========================
# 頁尾說明
# =========================
st.divider()
st.caption("《影響力》傳承策略平台｜永傳家族辦公室｜此頁為互動原型示意，非真實稅務建議。")

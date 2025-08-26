# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import uuid
from datetime import datetime, timedelta, timezone
import random
import pandas as pd

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="影響力傳承平台｜Octalysis 原型",
    page_icon="🌟",
    layout="wide",
)
TZ = timezone(timedelta(hours=8))  # 台灣時區（UTC+8）

# =========================
# 初始化 Session State
# =========================
def month_end_2359():
    today = datetime.now(TZ)
    first_of_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    last_of_this = first_of_next - timedelta(seconds=1)
    return last_of_this.replace(hour=23, minute=59, second=59, microsecond=0)

def init_state():
    ss = st.session_state
    ss.setdefault("mission_ack", False)                 # 使命召喚
    ss.setdefault("profile_done", False)                # 基本資料
    ss.setdefault("assets_done", False)                 # 資產盤點
    ss.setdefault("plan_done", False)                   # 策略配置
    ss.setdefault("quiz_done", False)                   # 小測驗
    ss.setdefault("advisor_booked", False)              # 預約顧問
    ss.setdefault("badges", set())                      # 徽章
    ss.setdefault("versions", [])                       # 版本管理
    ss.setdefault("invite_code", str(uuid.uuid4())[:8]) # 協作邀請碼
    ss.setdefault("consult_slots_total", 10)            # 本月名額
    ss.setdefault("consult_slots_left", 10)             # 剩餘名額
    ss.setdefault("consult_deadline", month_end_2359()) # 截止時間
    ss.setdefault("family_name", "")                    # 家族名稱
    ss.setdefault("assets", {                           # 六大資產
        "公司股權": 0, "不動產": 0, "金融資產": 0,
        "保單": 0, "海外資產": 0, "其他": 0
    })
    ss.setdefault("plan", {                             # 分配比例（需=100）
        "股權給下一代": 40, "保單留配偶": 30,
        "慈善信託": 10, "留現金緊急金": 20
    })
    ss.setdefault("risk_rate_no_plan", 0.18)            # 未規劃稅負率（示意）
    ss.setdefault("risk_rate_with_plan", 0.10)          # 已規劃稅負率（示意）
    ss.setdefault("tips_unlocked", [])                  # 已解鎖知識卡
init_state()

# =========================
# 工具函式
# =========================
def human_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M")

def add_badge(name: str):
    st.session_state.badges.add(name)

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
# 側邊欄：進度與徽章＆協作
# =========================
with st.sidebar:
    st.markdown("## 🧭 目前進度")
    prog = progress_score()
    st.progress(prog, text=f"完成度 {prog}%")
    st.caption("完成各區塊互動以提升完成度。")

    st.markdown("## 🏅 徽章")
    if not st.session_state.badges:
        st.caption("尚未解鎖徽章，完成任務即可獲得獎章。")
    else:
        for b in sorted(list(st.session_state.badges)):
            chip(f"🏅 {b}")

    st.divider()
    st.markdown("**邀請家族成員共建（示意）**")
    st.code(f"Invite Code: {st.session_state.invite_code}")
    st.caption("分享此代碼讓家族成員加入協作。")

# =========================
# 頁面標頭
# =========================
st.title("🌟 影響力傳承平台｜Octalysis Gamification 原型")
st.caption("以『準備與從容』為精神，讓家族影響力得以溫暖延續。")

tabs = st.tabs([
    "1 使命召喚",         # Epic Meaning & Calling
    "2 進步與成就",       # Development & Accomplishment
    "3 創意沙盒",         # Empowerment of Creativity & Feedback
    "4 擁有與版本",       # Ownership & Possession
    "5 協作與關係",       # Social Influence & Relatedness
    "6 稀缺與急迫",       # Scarcity & Impatience
    "7 驚喜與好奇",       # Unpredictability & Curiosity
    "8 風險與避免",       # Loss & Avoidance
])

# =========================
# 1. 使命召喚（Epic Meaning）
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
        st.markdown(
            "> （品牌短片位置）此處可放 15–30 秒使命影片或動態 Banner，傳遞「準備與從容」精神。"
        )
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", disabled=True)
        st.caption("示意：影片已停用播放，避免干擾。上線時可放品牌短片。")
    with colB:
        st.info("任務卡｜今天目標：完成『家族資料 + 資產盤點 + 初版策略』，解鎖「家族建築師」徽章。")
        guidance_note("點選上方分頁依序完成互動。")

    if st.button("我已理解並願意開始 ▶️", use_container_width=True):
        st.session_state.mission_ack = True
        add_badge("使命啟動者")
        st.success("任務已啟動，獲得徽章：使命啟動者！")

# =========================
# 2. 進步與成就（Development & Accomplishment）
# =========================
with tabs[1]:
    section_title("🧱", "基本資料與資產盤點（進度與成就）")
    st.write("完成以下步驟可提升完成度並解鎖徽章。")

    st.subheader("Step 1｜建立家族識別")
    fam = st.text_input("家族名稱（用於封面與報告）", value=st.session_state.family_name, placeholder="例如：黃氏家族")
    if st.button("儲存家族識別", key="btn_profile"):
        st.session_state.family_name = fam.strip()
        st.session_state.profile_done = bool(st.session_state.family_name)
        if st.session_state.profile_done:
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
            st.session_state.assets_done = True
            add_badge("家族建築師")
            st.success(f"已完成資產盤點（總額 {total:,} 萬元）。徽章：家族建築師")
        else:
            st.warning("尚未輸入任何資產金額。")

    with st.expander("查看我目前的完成度與徽章"):
        st.metric("目前完成度", f"{progress_score()}%")
        st.write("徽章：", ", ".join(sorted(list(st.session_state.badges))) if st.session_state.badges else "尚無")

# =========================
# 3. 創意沙盒（Empowerment of Creativity & Feedback）
# =========================
with tabs[2]:
    section_title("🧪", "策略沙盒（拖拉比例 / 即時回饋）")
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
                st.session_state.plan_done = True
                add_badge("策略設計師")
                st.success("已更新策略。徽章：策略設計師")

    with colR:
        total_asset = sum(st.session_state.assets.values())
        st.subheader("即時回饋（示意）")
        if total_asset <= 0:
            st.info("請先於『進步與成就』完成資產盤點。")
        else:
            plan = st.session_state.plan
            base_rate = st.session_state.risk_rate_with_plan
            effective_rate = max(0.05, base_rate - (plan["慈善信託"]/100)*0.03)  # 慈善提高稅務效率（示意）
            est_tax = int(total_asset * 10_000 * effective_rate)  # 萬元→元
            cash_liq = int(total_asset * 10_000 * (
                plan["留現金緊急金"]/100 + plan["保單留配偶"]/100*0.8
            ))

            st.metric("估算遺產稅（元）", f"{est_tax:,}")
            st.metric("估算可動用現金（元）", f"{cash_liq:,}")
            guidance_note("可增加『保單留配偶』或『留現金緊急金』比例以強化流動性。")

# =========================
# 4. 擁有與版本（Ownership & Possession）
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
            snapshot = {
                "time": datetime.now(TZ),
                "family": st.session_state.family_name,
                "assets": st.session_state.assets.copy(),
                "plan": st.session_state.plan.copy()
            }
            st.session_state.versions.append(snapshot)
            add_badge("版本管理者")
            st.success(f"已保存版本（{human_time(snapshot['time'])}）。徽章：版本管理者")

    with colR:
        st.subheader("版本記錄")
        if not st.session_state.versions:
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
            } for v in st.session_state.versions]
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

# =========================
# 5. 協作與關係（Social Influence & Relatedness）
# =========================
with tabs[4]:
    section_title("👥", "家族共建與顧問協作（示意）")
    st.write("透過邀請碼邀請家族成員加入協作，可在傳承地圖上留言、提議（示意聊天框）。")

    st.code(f"Invite Code：{st.session_state.invite_code}")
    st.caption("實作時可串接後端建立多使用者協作與權限。")

    with st.chat_message("user"):
        st.write("我覺得『慈善信託』比例可以再拉高一點，因為媽媽很在意回饋社會。")
    with st.chat_message("assistant"):
        st.write("收到～我會在策略會議上把這一點列為優先討論。")

    add_badge("協作啟動者")

# =========================
# 6. 稀缺與急迫（Scarcity & Impatience）
# =========================
with tabs[5]:
    section_title("⏳", "限時挑戰與預約名額")
    deadline = st.session_state.consult_deadline
    now = datetime.now(TZ)
    remain = max(0, int((deadline - now).total_seconds()))

    colL, colR = st.columns(2)
    with colL:
        st.subheader("🎯 本月挑戰")
        st.write("在**截止前**完成『資產盤點 + 策略初稿 + 版本保存』，可獲得 30 分鐘顧問諮詢。")
        st.metric("剩餘名額", st.session_state.consult_slots_left)
        st.metric("截止時間", human_time(deadline))
        st.caption("名額與倒數為示意，可串接真實後台。")

        if st.session_state.consult_slots_left > 0:
            if st.button("我要預約諮詢 📅", use_container_width=True):
                st.session_state.advisor_booked = True
                st.session_state.consult_slots_left -= 1
                add_badge("行動派")
                st.success("已預約成功！徽章：行動派")
        else:
            st.error("本月名額已滿，請下月再試。")

    with colR:
        st.subheader("⏱️ 倒數（示意）")
        st.write(f"距離截止約 **{remain} 秒**")
        guidance_note("活動、名額、倒數能有效提升行動率，但要避免造成過度焦慮感。")

# =========================
# 7. 驚喜與好奇（Unpredictability & Curiosity）
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
# 8. 風險與避免（Loss & Avoidance）
# =========================
with tabs[7]:
    section_title("⚖️", "未規劃 vs 已規劃｜風險對比（示意）")
    total_asset = sum(st.session_state.assets.values())
    if total_asset <= 0:
        st.info("請先完成『進步與成就』分頁的資產盤點。")
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
st.caption("《影響力》傳承策略平台｜永傳家族辦公室｜此頁為 Octalysis gamification 原型示意，非真實稅務建議。")


import streamlit as st
from datetime import date
from utils.notify import save_contact, send_email
from utils.settings import CAPTCHA_ENABLED, CAPTCHA_RANGE, FRONTEND_LOCK_SECONDS, RATE_LIMIT_SECONDS
from utils.ratelimit import should_allow, hash_payload
import time, random

def render():
    st.subheader("🤝 關於我們 / 聯絡")

    # 初始化 session_state 狀態
    if "lock_until" not in st.session_state:
        st.session_state.lock_until = 0.0
    if CAPTCHA_ENABLED and "cap_a" not in st.session_state:
        st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
        st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)

    def _arm_lock():
        # 一按下就鎖住，避免連點
        st.session_state.lock_until = time.time() + float(FRONTEND_LOCK_SECONDS)

    locked = time.time() < st.session_state.lock_until
    btn_label = "已送出，請稍候…" if locked else "送出需求"

    with st.form("contact_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("您的稱呼 *", value="")
            email = st.text_input("Email *", value="")
            phone = st.text_input("電話（可選）", value="")
            topic = st.selectbox("想了解的主題", ["體驗平台 Demo", "傳承規劃諮詢", "稅務試算討論", "保單策略設計", "其它"], index=0)
        with c2:
            when_date = st.date_input("期望日期", value=date.today())
            when_ampm = st.selectbox("時段偏好", ["上午", "下午", "晚上"], index=0)
            msg = st.text_area("想說的話（選填）", height=140)

        if CAPTCHA_ENABLED:
            a, b = st.session_state.cap_a, st.session_state.cap_b
            ans = st.number_input(f"請輸入驗證：{a} + {b} = ?", min_value=0, step=1)
        else:
            ans = 0

        # 一按就鎖；若目前正處於鎖定中，仍可提交這一次（不阻擋當前提交）
        submitted = st.form_submit_button(btn_label, on_click=_arm_lock, disabled=locked)

    if submitted:
        # ⚠️ 不阻擋本次提交，僅阻擋後續連點
        # 必填欄位檢查
        if not name.strip() or not email.strip():
            st.error("請填寫稱呼與 Email。")
            return

        # 驗證碼檢查
        if CAPTCHA_ENABLED:
            if ans != (st.session_state.cap_a + st.session_state.cap_b):
                st.error("驗證碼錯誤，請再試一次。")
                st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
                st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)
                return
            # 通過後換題，避免重放
            st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
            st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)

        payload = dict(
            name=name.strip(),
            email=email.strip(),
            phone=phone.strip(),
            topic=topic,
            when_date=str(when_date),
            when_ampm=when_ampm,
            msg=msg or ""
        )

        # 後端限流（同 email 在 RATE_LIMIT_SECONDS 內不重複處理；同內容亦忽略）
        p_hash = hash_payload(payload)
        if not should_allow(email, cooldown=RATE_LIMIT_SECONDS, content_hash=p_hash):
            st.info("我們剛剛已收到您的需求，請稍後再送。")
            return

        # 1) 儲存 CSV
        saved_ok = True
        try:
            save_contact(payload)
        except Exception as e:
            saved_ok = False
            st.warning(f"資料儲存時發生問題：{e}")

        # 2) 寄信（若已設定 SMTP）
        mailed = False
        try:
            mailed = send_email(payload)
        except Exception as e:
            st.info(f"已儲存需求；通知信未寄出（{e}）")

        if saved_ok:
            st.success("已收到，我們會盡快與您聯繫。謝謝！")
        else:
            st.success("已送出；我們將盡快與您聯繫。")

        if mailed:
            st.caption("通知信已寄出。")

        # 讓按鈕保持鎖定一段時間，但不影響顯示成功訊息
        st.session_state.lock_until = time.time() + float(FRONTEND_LOCK_SECONDS)

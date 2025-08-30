
import streamlit as st
from datetime import date
from utils.notify import save_contact, send_email
from utils.settings import CAPTCHA_ENABLED, CAPTCHA_RANGE, FRONTEND_LOCK_SECONDS, RATE_LIMIT_SECONDS
from utils.ratelimit import should_allow, hash_payload
import time, random

def render():
    st.subheader("🤝 關於我們 / 聯絡")

    # 初始化狀態
    if "lock_until" not in st.session_state:
        st.session_state.lock_until = 0.0
    if "contact_done" not in st.session_state:
        st.session_state.contact_done = False
    if CAPTCHA_ENABLED and "cap_a" not in st.session_state:
        st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
        st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)

    # 若已送出，顯示成功畫面並提供返回表單按鈕
    if st.session_state.contact_done:
        with st.container():
            st.markdown("### ✅ 需求已送出")
            st.success("我們將盡快與您聯繫，請留意您的信箱。")
            def _reset_form():
                # 清空欄位與鎖定
                st.session_state.contact_name = ""
                st.session_state.contact_email = ""
                st.session_state.contact_phone = ""
                st.session_state.contact_topic = "體驗平台 Demo"
                st.session_state.contact_msg = ""
                st.session_state.contact_when_ampm = "上午"
                st.session_state.contact_when_date = date.today()
                st.session_state.contact_done = False
                st.session_state.lock_until = 0.0
                if CAPTCHA_ENABLED:
                    st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
                    st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)
            if st.button("返回表單"):
                _reset_form()
                try:
                    st.rerun()
                except Exception:
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
        return

    # 尚未送出 → 顯示表單
    def _arm_lock():
        st.session_state.lock_until = time.time() + float(FRONTEND_LOCK_SECONDS)

    locked = time.time() < st.session_state.lock_until
    btn_label = "已送出，請稍候…" if locked else "送出需求"

    with st.form("contact_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("您的稱呼 *", key="contact_name")
            email = st.text_input("Email *", key="contact_email")
            phone = st.text_input("電話（可選）", key="contact_phone")
            topic = st.selectbox("想了解的主題", ["體驗平台 Demo", "傳承規劃諮詢", "稅務試算討論", "保單策略設計", "其它"], index=0, key="contact_topic")
        with c2:
            when_date = st.date_input("期望日期", value=st.session_state.get("contact_when_date", date.today()), key="contact_when_date")
            when_ampm = st.selectbox("時段偏好", ["上午", "下午", "晚上"], index=0, key="contact_when_ampm")
            msg = st.text_area("想說的話（選填）", height=140, key="contact_msg")

        if CAPTCHA_ENABLED:
            a, b = st.session_state.cap_a, st.session_state.cap_b
            ans = st.number_input(f"請輸入驗證：{a} + {b} = ?", min_value=0, step=1, key="contact_captcha")
        else:
            ans = 0

        submitted = st.form_submit_button(btn_label, on_click=_arm_lock, disabled=locked)

    if submitted:
        # 不阻擋本次提交，僅防連點
        if not st.session_state.contact_name.strip() or not st.session_state.contact_email.strip():
            st.error("請填寫稱呼與 Email。")
            return

        if CAPTCHA_ENABLED:
            if st.session_state.contact_captcha != (st.session_state.cap_a + st.session_state.cap_b):
                st.error("驗證碼錯誤，請再試一次。")
                st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
                st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)
                return
            st.session_state.cap_a = random.randint(*CAPTCHA_RANGE)
            st.session_state.cap_b = random.randint(*CAPTCHA_RANGE)

        payload = dict(
            name=st.session_state.contact_name.strip(),
            email=st.session_state.contact_email.strip(),
            phone=st.session_state.contact_phone.strip(),
            topic=st.session_state.contact_topic,
            when_date=str(st.session_state.contact_when_date),
            when_ampm=st.session_state.contact_when_ampm,
            msg=st.session_state.contact_msg or ""
        )

        # 後端限流
        p_hash = hash_payload(payload)
        if not should_allow(st.session_state.contact_email, cooldown=RATE_LIMIT_SECONDS, content_hash=p_hash):
            st.info("我們剛剛已收到您的需求，請稍後再送。")
            return

        # 儲存與寄信
        saved_ok = True
        try:
            save_contact(payload)
        except Exception as e:
            saved_ok = False
            st.warning(f"資料儲存時發生問題：{e}")

        mailed = False
        try:
            mailed = send_email(payload)
        except Exception as e:
            st.info(f"已儲存需求；通知信未寄出（{e}）")

        # 成功畫面
        if saved_ok:
            st.success("已收到，我們會盡快與您聯繫。謝謝！")
        else:
            st.success("已送出；我們將盡快與您聯繫。")
        if mailed:
            st.caption("通知信已寄出。")

        # 切換至成功畫面，並保持按鈕鎖定一段時間
        st.session_state.contact_done = True
        st.session_state.lock_until = time.time() + float(FRONTEND_LOCK_SECONDS)
        try:
            st.rerun()
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

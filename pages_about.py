
import streamlit as st
from datetime import date
from utils.notify import save_contact, send_email

def render():
    st.subheader("🤝 關於我們 / 聯絡")

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
        submitted = st.form_submit_button("送出需求")

    if submitted:
        if not name.strip() or not email.strip():
            st.error("請填寫稱呼與 Email。")
            return

        payload = dict(
            name=name.strip(),
            email=email.strip(),
            phone=phone.strip(),
            topic=topic,
            when_date=str(when_date),
            when_ampm=when_ampm,
            msg=msg or ""
        )

        # 1) 儲存 CSV
        try:
            save_contact(payload)
            saved_ok = True
        except Exception as e:
            saved_ok = False
            st.warning(f"資料儲存時發生問題：{e}")

        # 2) 嘗試寄信（若 secrets/環境變數已設定）
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

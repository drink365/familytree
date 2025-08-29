import streamlit as st
from datetime import date
from utils.notify import save_contact, send_email

def render():
    st.subheader("🤝 關於我們 / 聯絡")

    # ✅ 用表單包起來，才會出現送出按鈕
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

        # ✅ 表單送出按鈕
        submitted = st.form_submit_button("送出需求")

    if submitted:
        # 簡單驗證
        if not name.strip() or not email.strip():
            st.error("請填寫稱呼與 Email。")
            return

        payload = dict(
            name=name.strip(), email=email.strip(), phone=phone.strip(),
            topic=topic, when_date=str(when_date), when_ampm=when_ampm, msg=msg
        )

        # 1) 寫入 CSV
        try:
            save_contact(payload)
        except Exception as e:
            st.warning(f"資料已送出，但儲存時發生問題：{e}")

        # 2) 嘗試寄信（依 secrets 設定）
        try:
            mailed = send_email(payload)
            if mailed:
                st.success("已收到，我們會盡快與您聯繫（通知信已寄出）。謝謝！")
            else:
                st.success("已收到，我們會盡快與您聯繫。謝謝！")
                st.info("通知信未寄出：請確認 SMTP 設定是否完整。")
        except Exception as e:
            st.success("已收到，我們會盡快與您聯繫。謝謝！")
            st.info(f"通知信未寄出（{e}）")

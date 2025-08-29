
import streamlit as st
from utils.notify import save_contact, send_email
from datetime import date
def render():
    st.subheader("🤝 關於我們 / 聯絡")
    col1, col2 = st.columns([1,1])
    with col1:
        name  = st.text_input("您的稱呼 *", "")
        email = st.text_input("Email *", "")
        phone = st.text_input("電話（可選）", "")
        topic = st.selectbox("想了解的主題", ["體驗平台 Demo", "企業接班與股權", "遺產/贈與稅", "保單策略", "其它"])
    with col2:
        when_date = st.date_input("期望日期", value=date.today())
        when_ampm = st.selectbox("時段偏好", ["不限", "上午", "下午"], index=0)
        msg = st.text_area("想說的話（選填）", height=120)
        
if st.button("送出需求", type="primary"):
    # 簡單驗證
    if not name or not email:
        st.error("請填寫稱呼與 Email。")
    else:
        payload = dict(name=name, email=email, phone=phone, topic=topic, when_date=when_date, when_ampm=when_ampm, msg=msg)
        # 儲存 CSV
        try:
            save_contact(payload)
            saved_ok = True
        except Exception as e:
            saved_ok = False
            st.warning(f"資料儲存時發生問題：{e}")
        # 嘗試寄信（若尚未設定 SMTP 會略過）
        mailed = False
        try:
            mailed = send_email(payload)
        except Exception as e:
            st.info("已儲存需求；通知信未寄出（未設定或寄送失敗）。")
        if saved_ok:
            st.success("已收到，我們會盡快與您聯繫。謝謝！")
        else:
            st.success("已送出；我們將盡快與您聯繫。")


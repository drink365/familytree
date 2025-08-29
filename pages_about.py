
import streamlit as st
from datetime import date
from utils.notify import save_contact, send_email
from datetime import date
def render():
    st.subheader("🤝 關於我們 / 聯絡")
    with st.form("contact_form", clear_on_submit=False):
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
            st.success("已收到，我們會盡快與您聯繫。謝謝！")

    submitted = st.form_submit_button("送出需求")
    if submitted:
        st.success("已收到，我們會盡快與您聯繫。謝謝！")

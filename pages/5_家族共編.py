
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add)

init_session_defaults(); render_sidebar()
st.title("家族共編")

st.write("把側邊欄的專屬連結分享給家族成員，一起看同一張圖並形成共識。")
with st.chat_message("user"):
    st.write("我覺得『慈善信託』比例可以再拉高一點，因為媽媽很在意回饋社會。")
with st.chat_message("assistant"):
    st.write("收到～我會在策略會議上把這一點列為優先討論。")

badge_add("協作啟動者")

with st.expander("提示"):
    guidance_note("把連結當密碼，給對的人；共識來自一起看同一張圖。")

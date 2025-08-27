
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note,
                      consult_state, consult_decrement, booking_insert, badge_add,
                      plausible_event, maybe_fire_clarity_moment, is_view_mode)

init_session_defaults(); render_sidebar()
st.title("預約諮詢")

cs = consult_state()
section_title("⏳", "本月挑戰與名額（全站共享）")
st.metric("剩餘名額", cs["slots_left"])
st.metric("截止時間", cs["deadline"].strftime("%Y-%m-%d %H:%M"))

if is_view_mode():
    st.info("目前為唯讀模式：僅供瀏覽，不會寫入或預約。")
else:
    if cs["slots_left"] > 0:
        if st.button("我要預約諮詢 📅", use_container_width=True):
            if consult_decrement() and booking_insert():
                st.session_state.advisor_booked = True
                badge_add("行動派")
                st.success("已預約成功！徽章：行動派")
                plausible_event("Booked Consult", {})
                maybe_fire_clarity_moment()
            else:
                st.error("剛剛被搶走了，請稍後再試或下月再來～")
    else:
        st.error("本月名額已滿，請下月再試。")

with st.expander("提示"):
    guidance_note("當你看見缺口與下一步，就是最佳諮詢時機。")

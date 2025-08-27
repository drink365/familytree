
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (TZ, init_session_defaults, render_sidebar, section_title, guidance_note,
                      badge_add, inject_analytics, plausible_event, maybe_fire_clarity_moment)

st.set_page_config(page_title="影響力傳承平台｜互動原型", page_icon="🌟", layout="wide")
inject_analytics()
init_session_defaults()
render_sidebar()

st.title("🌟 把不確定，變成清晰的下一步。")
st.caption("以專業與同理，將家族傳承從焦慮化為可視、可量化、可行動。")

tab1, = st.tabs(["開始與目標"])

with tab1:
    section_title("🎯", "今天的目標")
    st.info("完成「資產盤點 + 策略初稿 + 保存快照」，達成你的 **清晰時刻**。")
    guidance_note("依序切換上方分頁：資產盤點 → 策略模擬 → 快照與匯出。")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    if st.button("我已理解並願意開始 ▶️", use_container_width=True):
        st.session_state.mission_ack = True
        badge_add("使命啟動者")
        st.success("任務已啟動，獲得徽章：使命啟動者！")
        maybe_fire_clarity_moment()

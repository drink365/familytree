
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, badge_add, inject_analytics, maybe_fire_clarity_moment)

st.set_page_config(page_title="影響力傳承平台｜互動原型", page_icon="🌟", layout="wide")
inject_analytics()
init_session_defaults()
render_sidebar()

st.title("🌟 把不確定，變成清晰的下一步。")
st.caption("以專業與同理，將家族傳承從焦慮化為可視、可量化、可行動。")

col1, col2 = st.columns([1,1])
with col1:
    if hasattr(st, "page_link"):
        st.page_link("pages/0_家族樹.py", label="建立家族樹 ▶️")
    else:
        st.button("建立家族樹 ▶️", use_container_width=True)
with col2:
    if hasattr(st, "page_link"):
        st.page_link("pages/1_快速盤點與策略.py", label="快速盤點與策略 ▶️")
    else:
        st.button("快速盤點與策略 ▶️", use_container_width=True)

st.divider()
st.info("今天的目標：完成「家族樹 + 盤點與策略 + 差異對比 + 快照」，達成你的 **清晰時刻**。")

if st.button("我已理解並願意開始 ▶️", use_container_width=True):
    st.session_state.mission_ack = True
    badge_add("使命啟動者")
    st.success("任務已啟動，達成里程碑：使命啟動者！")
    maybe_fire_clarity_moment()

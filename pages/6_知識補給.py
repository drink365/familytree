
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note,
                      badge_add, unlock_random_tip)

init_session_defaults(); render_sidebar()
st.title("知識補給")

section_title("🎁", "小測驗 & 驚喜知識卡")
with st.form("quiz_form"):
    q1 = st.radio("Q1. 信託可把『何時給、給誰、給多少、何條件下給』寫清楚嗎？", ["可以", "不行"], index=0)
    q2 = st.radio("Q2. 保單身故金是否可作為遺產稅與流動性缺口的緩衝？", ["是", "否"], index=0)
    q3 = st.radio("Q3. 跨境資產規劃需留意不同法域的課稅時點與估值規則？", ["需要", "不需要"], index=0)
    ok = st.form_submit_button("提交")
if ok:
    correct = (q1=="可以") + (q2=="是") + (q3=="需要")
    if correct == 3:
        st.success("全對！恭喜完成小測驗。")
        st.session_state.quiz_done = True
        badge_add("好奇探索者")
        tip = unlock_random_tip()
        if tip: st.info(f"🎉 解鎖知識卡：{tip}")
        else: st.caption("（你已解鎖所有知識卡！）")
    else:
        st.warning(f"目前答對 {correct}/3 題，再試試！")

if st.session_state.get("tips_unlocked"):
    section_title("📚", "已解鎖知識卡")
    for t in st.session_state.tips_unlocked:
        st.markdown(f"- {t}")

with st.expander("提示"):
    guidance_note("知識卡用來降低焦慮、建立共同語言，不用一次把所有東西都學完。")

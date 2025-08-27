
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add,
                      plan_set, plausible_event, current_gap_estimate, maybe_fire_clarity_moment)

init_session_defaults(); render_sidebar()
st.title("策略模擬")

section_title("🧪", "策略配置（拖拉比例 / 即時回饋）")

with st.form("plan_form"):
    p1 = st.slider("股權給下一代（%）", 0, 100, st.session_state.plan["股權給下一代"])
    p2 = st.slider("保單留配偶（%）",   0, 100, st.session_state.plan["保單留配偶"])
    p3 = st.slider("慈善信託（%）",     0, 100, st.session_state.plan["慈善信託"])
    p4 = st.slider("留現金緊急金（%）", 0, 100, st.session_state.plan["留現金緊急金"])
    submitted = st.form_submit_button("更新策略並模擬")
if submitted:
    total_pct = p1 + p2 + p3 + p4
    if total_pct != 100:
        st.error(f"目前總和為 {total_pct}%，請調整至 100%。")
    else:
        st.session_state.plan.update({
            "股權給下一代": p1, "保單留配偶": p2, "慈善信託": p3, "留現金緊急金": p4
        })
        plan_set(st.session_state.plan)
        st.session_state.plan_done = True
        badge_add("策略設計師")
        st.success("已更新策略。徽章：策略設計師")

st.subheader("即時回饋（示意）")
est = current_gap_estimate()
if not est:
    st.info("請先完成『資產盤點』頁面的資產輸入。")
else:
    st.metric("估算遺產稅（元）", f"{est['est_tax']:,}")
    st.metric("估算可動用現金（元）", f"{est['cash_liq']:,}")
    gap = max(0, est["est_tax"] - est["cash_liq"])
    st.metric("流動性缺口（元）", f"{gap:,}")
    plausible_event("Gap Calculated", {
        "gap": gap, "assets_total": est["total_asset"] * 10_000, "plan_charity_pct": est["plan_charity_pct"]
    })
    maybe_fire_clarity_moment()

with st.expander("提示"):
    guidance_note("調整比例，立即看到稅負與可動用現金的變化。把「感覺」變成「數字」，就能更從容。")

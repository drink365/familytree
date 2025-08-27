
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add,
                      assets_set, family_name_set, plan_set, plausible_event, current_gap_estimate, maybe_fire_clarity_moment)

init_session_defaults(); render_sidebar()
st.title("快速盤點與策略")

# ---- A. 家族識別 + 資產盤點 ----
with st.expander("🧱 家族識別與資產盤點", expanded=True):
    colA, colB = st.columns([1,2])
    with colA:
        fam = st.text_input("家族名稱（用於報告與快照）", value=st.session_state.family_name, placeholder="例如：黃氏家族")
        if st.button("儲存家族識別"):
            name = (fam or "").strip()
            st.session_state.family_name = name
            family_name_set(name)
            st.session_state.profile_done = bool(name)
            if name:
                badge_add("家族識別完成")
                st.success("已儲存。里程碑：家族識別完成")
            else:
                st.warning("請輸入家族名稱後再儲存。")
    with colB:
        a1, a2, a3 = st.columns(3)
        a4, a5, a6 = st.columns(3)
        assets = st.session_state.assets
        assets["公司股權"] = a1.number_input("公司股權（萬元）", 0, 10_000_000, assets["公司股權"])
        assets["不動產"]   = a2.number_input("不動產（萬元）",   0, 10_000_000, assets["不動產"])
        assets["金融資產"] = a3.number_input("金融資產（萬元）", 0, 10_000_000, assets["金融資產"])
        assets["保單"]     = a4.number_input("保單（萬元）",     0, 10_000_000, assets["保單"])
        assets["海外資產"] = a5.number_input("海外資產（萬元）", 0, 10_000_000, assets["海外資產"])
        assets["其他"]     = a6.number_input("其他（萬元）",     0, 10_000_000, assets["其他"])
        if st.button("完成資產盤點 ✅"):
            total = sum(assets.values())
            if total > 0:
                assets_set(assets)
                st.session_state.assets_done = True
                badge_add("家族建築師")
                st.success(f"已完成資產盤點（總額 {total:,} 萬元）。里程碑：家族建築師")
            else:
                st.warning("尚未輸入任何資產金額。")

# ---- B. 策略滑桿 + 即時回饋 ----
with st.expander("🧪 策略配置與即時回饋", expanded=True):
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
            st.success("已更新策略。里程碑：策略設計師")

    est = current_gap_estimate()
    if not est:
        st.info("請先完成資產輸入。")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("估算遺產稅（元）", f"{est['est_tax']:,}")
        c2.metric("估算可動用現金（元）", f"{est['cash_liq']:,}")
        gap = max(0, est['est_tax'] - est['cash_liq'])
        c3.metric("流動性缺口（元）", f"{gap:,}")
        plausible_event("Gap Calculated", {"gap": gap, "assets_total": est["total_asset"] * 10_000, "plan_charity_pct": est["plan_charity_pct"]})
        maybe_fire_clarity_moment()

with st.expander("提示"):
    guidance_note("把盤點與策略放在同一頁，5–10 分鐘就能看見差異與下一步。")

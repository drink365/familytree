
# -*- coding: utf-8 -*-
import streamlit as st
from utils.calculators import quick_preparedness_score, format_currency

st.set_page_config(page_title="🚦 快篩 | 影響力傳承平台", page_icon="🚦", layout="centered")

st.title("🚦 傳承風險快篩（3 分鐘）")
st.caption("回答以下問題，立即看見傳承準備度與可能的流動性缺口指標。")

with st.form("scan"):
    c1, c2 = st.columns(2)
    residence = c1.selectbox("主要稅務地/居住地", ["台灣", "大陸/中國", "美國", "其他"], index=0)
    cross_border = c2.selectbox("是否有跨境資產/家人", ["否", "是"], index=0)

    c3, c4 = st.columns(2)
    marital = c3.selectbox("婚姻狀態", ["未婚", "已婚", "離婚/分居", "再婚/有前任"], index=1)
    heirs_n = c4.number_input("潛在繼承/受贈人數（含子女、父母、配偶）", min_value=0, max_value=20, value=3, step=1)

    st.markdown("#### 主要資產概況（粗略估算即可）")
    c5, c6 = st.columns(2)
    estate_total = c5.number_input("資產總額（TWD）", min_value=0, value=150_000_000, step=1_000_000)
    liquid = c6.number_input("可動用流動資產（現金/定存/投資）（TWD）", min_value=0, value=20_000_000, step=1_000_000)

    c7, c8 = st.columns(2)
    realty = c7.number_input("不動產（TWD）", min_value=0, value=70_000_000, step=1_000_000)
    equity = c8.number_input("公司股權（TWD）", min_value=0, value=40_000_000, step=1_000_000)

    c9, c10 = st.columns(2)
    debts = c9.number_input("負債（TWD）", min_value=0, value=10_000_000, step=1_000_000)
    existing_insurance = c10.number_input("既有壽險保額（可用於稅務/現金流）（TWD）", min_value=0, value=15_000_000, step=1_000_000)

    c11, c12 = st.columns(2)
    has_will = c11.selectbox("是否已有遺囑", ["沒有", "有（但未更新）", "有（最新）"], index=0)
    has_trust = c12.selectbox("是否已有信託/保單信託", ["沒有", "規劃中", "已建立"], index=0)

    submitted = st.form_submit_button("計算準備度與風險")

if submitted:
    scan = dict(
        residence=residence, cross_border=cross_border, marital=marital, heirs_n=heirs_n,
        estate_total=estate_total, liquid=liquid, realty=realty, equity=equity,
        debts=debts, existing_insurance=existing_insurance, has_will=has_will, has_trust=has_trust
    )
    st.session_state["scan"] = scan
    score, flags = quick_preparedness_score(scan)

    st.success("✅ 快篩完成")
    st.metric("傳承準備度分數", f"{score}/100")
    if flags:
        st.markdown("**主要風險提示**：")
        for f in flags:
            st.write("• " + f)

    st.info("下一步：前往「💧 缺口與保單模擬」，調整年期/幣別，拿到第一版保單草案。")
    st.page_link("02_GapPlanner.py", label="➡️ 前往缺口與保單模擬")

else:
    st.info("請完成上方問卷並提交。若已做過，可直接到下一步。")
    st.page_link("02_GapPlanner.py", label="➡️ 我已做過，直接前往")

# -*- coding: utf-8 -*-
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="💧 缺口與保單模擬 | 影響力傳承平台", page_icon="💧", layout="centered")
st.title("💧 流動性缺口與保單策略模擬")

def taiwan_estate_tax(taxable_amount: int) -> int:
    x = int(max(0, taxable_amount))
    if x <= 56_210_000: return int(x * 0.10)
    elif x <= 112_420_000: return int(x * 0.15 - 2_810_000)
    else: return int(x * 0.20 - 8_430_000)

def liquidity_need_estimate(tax: int, fees_ratio: float = 0.01) -> int:
    tax = int(max(0, tax)); fees = int(tax * max(0.0, fees_ratio)); return tax + fees

def plan_with_insurance(need: int, available: int, cover: int, pay_years: int, premium_ratio: float):
    need = int(max(0, need)); available = int(max(0, available)); cover = int(max(0, cover))
    premium_ratio = max(1.0, float(premium_ratio)); pay_years = int(max(1, pay_years))
    annual_premium = int(cover / premium_ratio / pay_years)
    surplus_after_cover = int(available + cover - need)
    return dict(annual_premium=annual_premium, surplus_after_cover=surplus_after_cover)

def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

scan = st.session_state.get("scan")
if not scan:
    st.warning("尚未完成快篩。請先到「🚦 傳承風險快篩」。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()

st.markdown("#### 依台灣稅制（10% / 15% / 20%）與標準扣除進行估算（僅供規劃參考）")

c1, c2 = st.columns(2)
funeral = c1.number_input("喪葬費用（上限 1,380,000）", min_value=0, max_value=5_000_000, value=1_380_000, step=10_000)
supportees = c2.number_input("其他受扶養人數（每人 560,000）", min_value=0, max_value=10, value=0, step=1)

c3, c4 = st.columns(2)
spouse_deduction = c3.number_input("配偶扣除（預設 5,530,000）", min_value=0, max_value=10_000_000, value=5_530_000, step=10_000)
basic_exempt = c4.number_input("基本免稅額（預設 13,330,000）", min_value=0, max_value=50_000_000, value=13_330_000, step=10_000)

taxable_base = max(0, scan["estate_total"] - scan["debts"])
deductions = basic_exempt + spouse_deduction + funeral + supportees * 560_000
tax = taiwan_estate_tax(max(0, taxable_base - deductions))
st.metric("預估遺產稅額", format_currency(tax))

need = liquidity_need_estimate(tax=tax, fees_ratio=0.01)
st.metric("初估流動性需求（含雜費 1%）", format_currency(need))

available = scan["liquid"] + scan["existing_insurance"]
gap = max(0, need - available)
st.metric("初估流動性缺口", format_currency(gap))

st.markdown("---")
st.markdown("#### 保單策略模擬")

c5, c6 = st.columns(2)
target_cover = c5.number_input("新保單目標保額", min_value=0, value=int(gap), step=1_000_000)
pay_years = c6.selectbox("繳費年期", [1, 3, 5, 6, 7, 10], index=3)

c7, c8 = st.columns(2)
assumed_IRR = c7.slider("保單內含報酬率假設（僅估年繳）", min_value=0.0, max_value=6.0, value=2.5, step=0.1)
premium_ratio = c8.slider("年繳 / 保額 比例（粗估）", min_value=1.0, max_value=20.0, value=10.0, step=0.5)

plan = plan_with_insurance(need=need, available=available, cover=target_cover, pay_years=pay_years, premium_ratio=premium_ratio)
st.write("**估算年繳保費**：", format_currency(plan["annual_premium"]))
st.write("**補齊缺口後的剩餘**：", format_currency(plan["surplus_after_cover"]))

fig1, ax1 = plt.subplots()
labels = ["不用保單", "加上保單"]
values = [max(0, need - available), max(0, need - (available + target_cover))]
ax1.bar(labels, values)
ax1.set_ylabel("剩餘缺口（TWD）")
ax1.set_title("保單介入前後的缺口對比")
st.pyplot(fig1)

st.session_state["plan"] = dict(
    need=need, available=available, gap=gap, target_cover=target_cover,
    pay_years=pay_years, annual_premium=plan["annual_premium"],
    surplus_after_cover=plan["surplus_after_cover"],
    tax=tax, deductions=deductions, taxable_base=taxable_base
)

st.info("下一步：下載一頁式提案，帶回家與家人討論。")
st.page_link("pages/03_Proposal.py", label="➡️ 下載一頁式提案")

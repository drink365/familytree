# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

# ---------------- 基本設定 ----------------
set_page("🚦 3 分鐘快篩 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("3 分鐘傳承快篩", "先解決一次性現金缺口，避免被迫賣資產")

st.caption("輸入資產、負債與保單資訊，系統將估算遺產稅與一次性現金缺口（含 1% 雜費）。")

# --------- 金額展示（一般大小或略大一號，無換行） ---------
def money_html(value: int, size: str = "md") -> str:
    """
    size: 'sm'（小）/ 'md'（中，略大一號）
    """
    s = "NT$ {:,}".format(int(value))
    cls = "money-figure-sm" if size == "sm" else "money-figure-md"
    return f"<div class='{cls}'>{s}</div>"

# 一次注入的全域樣式（與 02_GapPlanner.py 一致）
st.markdown("""
<style>
.money-figure-md{
  font-weight: 800;
  line-height: 1.25;
  font-size: clamp(18px, 1.8vw, 22px); /* 一般大小再大一點 */
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.money-figure-sm{
  font-weight: 700;
  line-height: 1.25;
  font-size: clamp(16px, 1.6vw, 20px); /* 稍小，用於摘要數字 */
  letter-spacing: 0.2px;
  white-space: nowrap;
}
.money-label{
  color: #6B7280; font-size: 14px; margin-bottom: 4px;
}
.money-card{ display:flex; flex-direction:column; gap:4px; }
.hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

def money_card(label: str, value: int, size: str = "md"):
    st.markdown(
        f"<div class='money-card'><div class='money-label'>{label}</div>{money_html(value, size=size)}</div>",
        unsafe_allow_html=True
    )

# ---------------- 稅額公式（與先前一致） ----------------
def taiwan_estate_tax(taxable_amount: int) -> int:
    x = int(max(0, taxable_amount))
    if x <= 56_210_000: 
        return int(x * 0.10)
    elif x <= 112_420_000: 
        return int(x * 0.15 - 2_810_000)
    else: 
        return int(x * 0.20 - 8_430_000)

# ---------------- 表單輸入 ----------------
with st.form("scan_form"):
    c1, c2 = st.columns(2)
    estate_total = c1.number_input("資產總額 (TWD)", min_value=0, value=150_000_000, step=1_000_000)
    debts = c2.number_input("負債總額 (TWD)", min_value=0, value=10_000_000, step=1_000_000)

    c3, c4 = st.columns(2)
    liquid = c3.number_input("可動用流動資產 (TWD)", min_value=0, value=20_000_000, step=1_000_000)
    existing_insurance = c4.number_input("既有壽險保額 (TWD)", min_value=0, value=15_000_000, step=1_000_000)

    st.markdown("#### 扣除額（簡化參數，可依需要調整）")
    c5, c6 = st.columns(2)
    basic_exempt = c5.number_input("基本免稅額", min_value=0, value=13_330_000, step=10_000)
    spouse_deduction = c6.number_input("配偶扣除", min_value=0, value=5_530_000, step=10_000)

    c7, c8 = st.columns(2)
    funeral = c7.number_input("喪葬費用（上限 1,380,000）", min_value=0, value=1_380_000, step=10_000)
    supportees = c8.number_input("其他受扶養人數（每人 560,000）", min_value=0, max_value=10, value=0, step=1)

    submitted = st.form_submit_button("計算一次性現金缺口", use_container_width=True)

# ---------------- 計算與輸出 ----------------
if submitted:
    taxable_base = max(0, estate_total - debts)
    deductions = basic_exempt + spouse_deduction + funeral + supportees * 560_000
    tax = taiwan_estate_tax(max(0, taxable_base - deductions))

    one_time_need = tax + int(tax * 0.01)  # 1% 雜費
    available_cash = liquid + existing_insurance
    cash_gap = max(0, one_time_need - available_cash)

    st.success("快篩完成！")
    colA1, colA2, colA3 = st.columns(3)
    with colA1:
        money_card("一次性現金需求（稅 + 雜費）", one_time_need, size="md")
    with colA2:
        money_card("可用現金 + 既有保單", available_cash, size="md")
    with colA3:
        money_card("一次性現金缺口", cash_gap, size="md")

    # 寫入 Session，供下一步使用（名稱與 02/03 頁一致）
    st.session_state["scan_data"] = dict(
        estate_total=estate_total, debts=debts, liquid=liquid, existing_insurance=existing_insurance,
        basic_exempt=basic_exempt, spouse_deduction=spouse_deduction,
        funeral=funeral, supportees=supportees,
        taxable_base=taxable_base, deductions=deductions,
        tax=tax, one_time_need=one_time_need, available_cash=available_cash, cash_gap=cash_gap
    )

    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
    st.info("下一步：前往「📊 缺口與保單模擬」，把一次性現金與長期現金流一起規劃。")
    st.page_link("pages/02_GapPlanner.py", label="➡️ 前往缺口與保單模擬")

else:
    st.info("請輸入數據並提交，系統將自動計算一次性現金缺口。")

footer()

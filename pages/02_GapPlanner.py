# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer
import matplotlib.pyplot as plt
import os
from matplotlib import font_manager, rcParams

set_page("📊 缺口與保單模擬 | 影響力傳承平台", layout="centered")   # ← 已改成 📊
sidebar_brand()
brand_hero("📊 流動性缺口與保單策略模擬")                     # ← 已改成 📊

# 中文字型（圖表）
def _setup_zh_font():
    candidates = [
        "./NotoSansTC-Regular.ttf",
        "./NotoSansCJKtc-Regular.otf",
        "./TaipeiSansTCBeta-Regular.ttf",
        "./TaipeiSansTCBeta-Regular.otf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                font_manager.fontManager.addfont(p)
                rcParams['font.family'] = 'sans-serif'
                rcParams['font.sans-serif'] = ['Noto Sans TC', 'Taipei Sans TC Beta', 'Microsoft JhengHei', 'PingFang TC', 'Heiti TC']
                rcParams['axes.unicode_minus'] = False
                return True
            except Exception:
                pass
    rcParams['axes.unicode_minus'] = False
    return False

if not _setup_zh_font():
    st.caption("提示：若圖表中文字出現方塊/亂碼，請把 **NotoSansTC-Regular.ttf** 放在專案根目錄後重新載入。")

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

scan = st.session_state.get("scan_data")
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
st.metric("初估缺口", format_currency(gap))

st.markdown("---")
st.markdown("#### 保單策略模擬")

c5, c6 = st.columns(2)
target_cover = c5.number_input("新保單目標保額", min_value=0, value=int(gap), step=1_000_000)
pay_years = c6.selectbox("繳費年期", [1, 3, 5, 6, 7, 10], index=3)

c7, c8 = st.columns(2)
assumed_IRR = c_

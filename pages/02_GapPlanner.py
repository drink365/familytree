# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib import font_manager, rcParams
from math import pow

# ---------------- 基本設定 ----------------
set_page("📊 缺口與保單模擬 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("📊 一次性現金缺口 ＋ 長期現金流 模擬", "先補足現金，再設計穩定現金流")

# ---------------- 圖表中文字型 ----------------
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
                rcParams['font.sans-serif'] = [
                    'Noto Sans TC', 'Taipei Sans TC Beta',
                    'Microsoft JhengHei', 'PingFang TC', 'Heiti TC'
                ]
                rcParams['axes.unicode_minus'] = False
                return True
            except Exception:
                pass
    rcParams['axes.unicode_minus'] = False
    return False

if not _setup_zh_font():
    st.caption("提示：若圖表中文字出現方塊/亂碼，請把 **NotoSansTC-Regular.ttf** 放在專案根目錄後重新載入。")

# ---------------- 通用工具 ----------------
def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

def annuity_pv(annual: float, r: float, n: int) -> float:
    """年金現值：annual × (1 - (1+r)^-n) / r；r=0 時回傳 annual × n"""
    if n <= 0: return 0.0
    if r <= 0: return annual * n
    return annual * (1 - pow(1 + r, -n)) / r

def plan_with_insurance(one_time_need: int, available_cash: int, long_term_pv: int,
                        target_cover: int, pay_years: int, premium_ratio: float):
    """
    年繳估算：年繳 ≈ 保額 / 年繳係數 / 繳費年期
    注意：此為粗估（無產品/費率），正式報價以商品條款為準。
    """
    need_total = max(0, int(one_time_need + long_term_pv))
    after_cover_gap = max(0, need_total - (available_cash + target_cover))
    annual_premium = int(target_cover / max(1.0, premium_ratio) / max(1, pay_years))
    return dict(
        need_total=need_total,
        after_cover_gap=after_cover_gap,
        annual_premium=annual_premium
    )

# --------- 金額展示（一般大小或略大一號，無換行） ---------
def money_html(value: int, size: str = "md") -> str:
    """
    size: 'sm'（小）/ 'md'（中，略大一號）
    """
    s = "NT$ {:,}".format(int(value))
    cls = "money-figure-sm" if size == "sm" else "money-figure-md"
    return f"<div class='{cls}'>{s}</div>"

# 一次注入的全域樣式（桌面與手機都維持單行，不做逗號換行）
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

# ---------------- 需要快篩資料 ----------------
scan = st.session_state.get("scan_data")
if not scan:
    st.warning("尚未完成快篩。請先到「🚦 3 分鐘快篩」。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()

# ---------------- A. 一次性現金缺口（已估算） ----------------
st.markdown("### A. 一次性現金缺口（已估算）")
colA1, colA2, colA3 = st.columns(3)

with colA1:
    money_card("一次性現金需求", scan["one_time_need"], size="md")
with colA2:
    money_card("可用現金 + 既有保單", scan["available_cash"], size="md")
with colA3:
    money_card("一次性現金缺口", scan["cash_gap"], size="md")

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ---------------- B. 長期現金流（年金型給付） ----------------
st.markdown("### B. 長期現金流（年金型給付）")
c1, c2 = st.columns(2)
annual_cashflow = c1.number_input("每年期望給付（TWD）", min_value=0, value=2_000_000, step=100_000)
years = c2.number_input("給付年期（年）", min_value=0, max_value=60, value=10, step=1)

c3, c4 = st.columns(2)
discount_rate_pct = c3.slider("折現率（估）%", min_value=0.0, max_value=8.0, value=2.0, step=0.1)
funding_mode = c4.selectbox("資金來源策略", ["保單一次到位（保額扣抵）", "自有資金（不納入保額）"], index=0)

r = discount_rate_pct / 100.0
lt_total = int(annual_cashflow * years)
lt_pv = int(annuity_pv(annual_cashflow, r, years))

st.write(f"• 長期現金流 **總額**：{format_currency(lt_total)}")
st.write(f"• 以折現率 {discount_rate_pct:.1f}% 計算之 **現值**：{format_currency(lt_pv)}")

# 決定是否將長期現金流現值納入保額目標
include_pv_in_cover = (funding_mode == "保單一次到位（保額扣抵）")
long_term_need_for_cover = lt_pv if include_pv_in_cover else 0

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ---------------- C. 保單策略模擬 ----------------
st.markdown("### C. 保單策略模擬（合併一次性現金 + 長期現金流現值）")

c5, c6 = st.columns(2)
suggested_cover = max(0, scan["cash_gap"] + long_term_need_for_cover)
target_cover = c5.number_input("新保單目標保額", min_value=0, value=int(suggested_cover), step=1_000_000)
pay_years = c6.selectbox("繳費年期", [1, 3, 5, 6, 7, 10], index=3)

c7, c8 = st.columns(2)
premium_ratio = c7.slider("年繳 / 保額 比例（粗估年繳係數）", min_value=1.0, max_value=20.0, value=10.0, step=0.5)
c8.caption("提示：正式年繳以商品與保費試算為準，本處僅粗估。")

plan = plan_with_insurance(
    one_time_need=scan["one_time_need"],
    available_cash=scan["available_cash"],
    long_term_pv=long_term_need_for_cover,
    target_cover=target_cover,
    pay_years=pay_years,
    premium_ratio=premium_ratio
)

# 下方兩個數字採「小字」樣式
colR1, colR2 = st.columns(2)
with colR1:
    money_card("合併需求現值（一次性 + 長期）", plan["need_total"], size="sm")
with colR2:
    money_card("補齊後剩餘缺口", plan["after_cover_gap"], size="sm")
st.write("估算年繳保費：", format_currency(plan["annual_premium"]))

# ---------------- 年度現金流分布（替代視覺化） ----------------
st.markdown("#### 年度現金流分布（示意）")
if years > 0 and annual_cashflow > 0:
    years_range = np.arange(1, years + 1)
    needs = np.array([annual_cashflow] * years)

    if include_pv_in_cover:
        source_label = "保單預期給付（目標）"
        source = np.array([annual_cashflow] * years)
    else:
        source_label = "自有資金/投資收益（假設）"
        source = np.array([annual_cashflow] * years)  # 若未納入保額，示意由自有資金供應

    fig, ax = plt.subplots()
    ax.plot(years_range, needs, label="年度現金需求", marker="o")
    ax.plot(years_range, source, label=source_label, marker="s")
    ax.set_xlabel("年份")
    ax.set_ylabel("金額（TWD）")
    ax.set_title("年度現金需求與資金來源")
    ax.legend()
    st.pyplot(fig)
else:
    st.info("請設定『每年期望給付』與『給付年期』以顯示年度現金流分布。")

# ---------------- 寫入 Session（供 PDF 使用） ----------------
st.session_state["plan_data"] = dict(
    # 來自快篩
    tax=scan["tax"],
    one_time_need=scan["one_time_need"],
    available_cash=scan["available_cash"],
    cash_gap=scan["cash_gap"],
    # 長期現金流
    annual_cashflow=annual_cashflow,
    years=years,
    discount_rate_pct=discount_rate_pct,
    lt_total=lt_total,
    lt_pv=lt_pv,
    include_pv_in_cover=include_pv_in_cover,
    lt_need_for_cover=long_term_need_for_cover,
    # 保單策略
    target_cover=target_cover,
    pay_years=pay_years,
    annual_premium=plan["annual_premium"],
    need_total=plan["need_total"],
    after_cover_gap=plan["after_cover_gap"],
)

st.info("下一步：產生一頁式報告，清楚呈現一次性現金與長期現金流的方案。")
st.page_link("pages/03_Proposal.py", label="➡️ 下載一頁式提案")

footer()

# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer
import matplotlib.pyplot as plt
import os
from matplotlib import font_manager, rcParams
from math import pi

# ---------------- 基本設定 ----------------
set_page("🧭 資產配置策略 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("資產配置策略（保險的正確位置）", "先補一次性現金，再做長期現金流，最後看整體資產配置")

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
                rcParams["font.family"] = "sans-serif"
                rcParams["font.sans-serif"] = [
                    "Noto Sans TC", "Taipei Sans TC Beta",
                    "Microsoft JhengHei", "PingFang TC", "Heiti TC"
                ]
                rcParams["axes.unicode_minus"] = False
                return True
            except Exception:
                pass
    rcParams["axes.unicode_minus"] = False
    return False

if not _setup_zh_font():
    st.caption("提示：若圖表中文字出現方塊/亂碼，請把 **NotoSansTC-Regular.ttf** 放在專案根目錄後重新載入。")

# ---------------- 金額與文字樣式（與 01/02 頁一致 + bullet-text） ----------------
def money_html(value: int, size: str = "md") -> str:
    s = "NT$ {:,}".format(int(value))
    cls = "money-figure-sm" if size == "sm" else "money-figure-md"
    return f"<div class='{cls}'>{s}</div>"

st.markdown("""
<style>
.money-figure-md{
  font-weight: 800;
  line-height: 1.25;
  font-size: clamp(18px, 1.8vw, 22px);
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.money-figure-sm{
  font-weight: 700;
  line-height: 1.25;
  font-size: clamp(16px, 1.6vw, 20px);
  letter-spacing: 0.2px;
  white-space: nowrap;
}
.money-label{
  color: #6B7280; font-size: 14px; margin-bottom: 4px;
}
.money-card{ display:flex; flex-direction:column; gap:4px; }
.hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 24px 0; }

/* 統一「說明與依據」的段落字型與大小 */
.bullet-text{
  font-size: 16px;
  color: #374151;           /* Gray-700 */
  line-height: 1.7;
  font-family: "Noto Sans TC","Microsoft JhengHei",sans-serif;
}
</style>
""", unsafe_allow_html=True)

def money_card(label: str, value: int, size: str = "md"):
    st.markdown(
        f"<div class='money-card'><div class='money-label'>{label}</div>{money_html(value, size=size)}</div>",
        unsafe_allow_html=True
    )

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def format_currency(x) -> str:
    try:
        return "NT$ {:,}".format(int(round(float(x))))
    except Exception:
        return "NT$ -"

# ---------------- 取用先前頁面結果（若有） ----------------
scan = st.session_state.get("scan_data", {})
plan = st.session_state.get("plan_data", {})

default_liquid = int(scan.get("liquid", 2_000_000))           # 與首頁一致
default_existing_ins = int(scan.get("existing_insurance", 3_000_000))

one_time_need = int(scan.get("one_time_need", 0))
available_cash = int(scan.get("available_cash", default_liquid + default_existing_ins))
cash_gap = max(0, int(scan.get("cash_gap", max(0, one_time_need - available_cash))))

lt_pv = int(plan.get("lt_pv", 0))
include_pv_in_cover = bool(plan.get("include_pv_in_cover", False))

st.info("此模組將整合：一次性『現金』缺口 + 長期『現金流』現值（可選），並輸出整體資產配置建議。")

# ---------------- 一、輸入資產結構（方案 A：總額自動等於合計） ----------------
st.markdown("### 一、輸入資產結構（粗略即可）")

with st.form("asset_form"):
    c1, c2, c3 = st.columns(3)
    cash_holdings = c1.number_input("現金 / 定存", min_value=0, value=default_liquid, step=1_000_000)
    financials   = c2.number_input("金融資產（股票/基金/債券）", min_value=0, value=30_000_000, step=1_000_000)
    realty       = c3.number_input("不動產", min_value=0, value=70_000_000, step=1_000_000)

    c4, c5, c6 = st.columns(3)
    equity      = c4.number_input("企業股權", min_value=0, value=40_000_000, step=1_000_000)
    overseas    = c5.number_input("海外資產", min_value=0, value=10_000_000, step=1_000_000)
    existing_insurance = c6.number_input("既有壽險保額（可用於現金/稅務）", min_value=0, value=default_existing_ins, step=1_000_000)

    c7, c8 = st.columns(2)
    include_lt = c7.selectbox("將長期現金流『現值』納入保額規劃？", ["否（自有資金）", "是（保單一次到位）"],
                              index=1 if include_pv_in_cover else 0)
    submitted = st.form_submit_button("生成策略建議", use_container_width=True)

if not submitted:
    st.stop()

# 直接以各項合計作為資產總額（不再獨立輸入）
assets_sum = cash_holdings + financials + realty + equity + overseas
total_base = assets_sum
st.caption(f"資產各項合計：**{format_currency(total_base)}**（自動作為資產總額）")

# ---------------- 二、風險評分 ----------------
liq_weights  = {"cash": 5, "fin": 4, "realty": 1, "equity": 1, "overseas": 2}
grow_weights = {"cash": 1, "fin": 4, "realty": 3, "equity": 5, "overseas": 4}
tax_weights  = {"cash": 1, "fin": 2, "realty": 3, "equity": 4, "overseas": 4}
legal_weights= {"cash": 1, "fin": 2, "realty": 3, "equity": 4, "overseas": 4}

def weighted_score(weights):
    if total_base == 0: return 0
    return (
        weights["cash"]   * cash_holdings +
        weights["fin"]    * financials +
        weights["realty"] * realty +
        weights["equity"] * equity +
        weights["overseas"] * overseas
    ) / total_base

liq_score     = weighted_score(liq_weights)
grow_score    = weighted_score(grow_weights)
tax_sens      = weighted_score(tax_weights)
legal_complex = weighted_score(legal_weights)

# ---------------- 三、建議保護/現金/成長比例 ----------------
lt_need_for_cover = lt_pv if include_lt == "是（保單一次到位）" else 0
protection_amount = max(0, cash_gap + lt_need_for_cover)

equity_share = 0 if total_base == 0 else (equity / total_base)
extra_for_business = 0
if equity_share >= 0.5:
    extra_for_business = int(0.05 * total_base)
    protection_amount += extra_for_business

cash_reserve_pct = 0.10 if liq_score < 3 else 0.05
target_cash_reserve = int(cash_reserve_pct * total_base)

protection_pct = (protection_amount / total_base) if total_base else 0
protection_pct = clamp(protection_pct, 0.10, 0.35) if total_base > 0 else 0
cash_pct = clamp(target_cash_reserve / total_base if total_base else 0, 0.05, 0.15)
growth_pct = max(0.0, 1.0 - protection_pct - cash_pct)

# ---------------- 視覺化 1：現況資產分布（圓餅圖） ----------------
st.markdown("### 二、現況資產分布")
fig1, ax1 = plt.subplots()
labels1 = ["現金/定存", "金融資產", "不動產", "企業股權", "海外資產"]
values1 = [cash_holdings, financials, realty, equity, overseas]
if sum(values1) == 0:
    st.info("尚未輸入資產數字，略過分布圖。")
else:
    ax1.pie(values1, labels=labels1, autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
    ax1.set_title("資產結構（現況）")
    st.pyplot(fig1)

# ---------------- 視覺化 2：風險屬性（雷達圖） ----------------
st.markdown("### 三、風險屬性雷達圖（0~5分）")
metrics = ["流動性", "成長性", "稅務敏感", "法務複雜"]
scores = [liq_score, grow_score, tax_sens, legal_complex]

angles = [n / float(len(metrics)) * 2 * pi for n in range(len(metrics))]
angles += angles[:1]
scores_plot = scores + scores[:1]

fig2 = plt.figure()
ax2 = plt.subplot(111, polar=True)
ax2.set_theta_offset(pi / 2)
ax2.set_theta_direction(-1)
plt.xticks(angles[:-1], metrics)
ax2.set_rlabel_position(0)
ax2.plot(angles, scores_plot, linewidth=2)
ax2.fill(angles, scores_plot, alpha=0.1)
ax2.set_ylim(0, 5)
st.pyplot(fig2)

# ---------------- 視覺化 3：建議配置（圓餅圖） ----------------
st.markdown("### 四、整體配置藍圖（建議比例）")
fig3, ax3 = plt.subplots()
labels2 = ["保護（保單/信託/一次性）", "核心現金準備", "成長資產"]
values2 = [protection_pct, cash_pct, growth_pct]
if sum(values2) == 0:
    st.info("無法生成配置建議（基數為 0）。")
else:
    ax3.pie(values2, labels=labels2, autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
    ax3.set_title("建議資產配置比例")
    st.pyplot(fig3)

# ---------------- 金額摘要（一致樣式） ----------------
st.markdown("#### 建議配置明細（以金額表示）")
protect_amt = int(protection_pct * total_base)
cash_amt    = int(cash_pct * total_base)
growth_amt  = max(0, total_base - protect_amt - cash_amt)

cA, cB, cC = st.columns(3)
with cA:
    money_card("保護（保單/信託/一次性）", protect_amt, size="md")
with cB:
    money_card("核心現金準備", cash_amt, size="md")
with cC:
    money_card("成長資產", growth_amt, size="md")

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ---------------- 說明/依據（統一字體大小） ----------------
st.markdown("**說明與依據：**")
bullets = []
if cash_gap > 0:
    bullets.append(f"• 一次性『現金』缺口 {format_currency(cash_gap)} 以保單或等值現金鎖定，避免被迫賣資產。")
else:
    bullets.append("• 一次性『現金』缺口為 0，仍建議保留基本保額以對沖法律與稅務不確定性。")
if include_lt == "是（保單一次到位）" and lt_pv > 0:
    bullets.append(f"• 長期『現金流』現值（PV）{format_currency(lt_pv)} 納入保額規劃，一次到位。")
else:
    bullets.append("• 長期『現金流』由自有資金或投資收益供應（不納入保額）。")
if equity_share >= 0.5:
    bullets.append(f"• 企業股權占比較高（{equity_share*100:.1f}%），建議額外 {format_currency(extra_for_business)} 作為『經營延續/關鍵人』緩衝（保單信託或定期壽險）。")
if cash_reserve_pct == 0.10:
    bullets.append("• 整體流動性偏低，核心現金準備提高到 **10%**，確保家庭/企業現金部位。")
else:
    bullets.append("• 流動性尚可，核心現金準備維持 **5%**。")

# 用自訂樣式一次輸出，確保字體/大小一致
st.markdown("<div class='bullet-text'>" + "<br/>".join(bullets) + "</div>", unsafe_allow_html=True)

# ---------------- 保存到 Session（供 PDF/匯出） ----------------
strategy = dict(
    total_base=total_base,
    # 現況
    cash=cash_holdings, financials=financials, realty=realty, equity=equity, overseas=overseas,
    liq_score=float(liq_score), grow_score=float(grow_score),
    tax_sens=float(tax_sens), legal_complex=float(legal_complex),
    # 需求
    one_time_need=one_time_need, cash_gap=cash_gap,
    lt_pv=lt_pv, include_lt_pv=(include_lt == "是（保單一次到位）"),
    # 建議
    protection_pct=float(protection_pct), cash_pct=float(cash_pct), growth_pct=float(growth_pct),
    protection_amount=protect_amt, cash_amount=cash_amt, growth_amount=growth_amt,
    extra_for_business=extra_for_business
)
st.session_state["asset_strategy"] = strategy

st.markdown("**摘要**")
st.write(f"• 一次性現金缺口：{format_currency(cash_gap)}")
st.write(f"• 長期現金流現值（是否納入保額）：{format_currency(lt_pv)}（{'是' if strategy['include_lt_pv'] else '否'}）")
st.write(f"• 建議保護金額（保單/信託/一次性）：{format_currency(protect_amt)}")
st.write(f"• 核心現金準備：{format_currency(cash_amt)}")
st.write(f"• 成長資產：{format_currency(growth_amt)}")

footer()

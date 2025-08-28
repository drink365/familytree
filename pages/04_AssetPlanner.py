# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer
import matplotlib.pyplot as plt
import os
from matplotlib import font_manager, rcParams
from math import pi

set_page("🧭 資產配置策略 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("資產配置策略（保險的正確位置）", "先補一次性現金，再做長期現金流，最後看整體資產配置")

# ---------- 字型設定（圖表中文） ----------
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

# ---------- 工具 ----------
def format_currency(x: float | int) -> str:
    try:
        return "NT$ {:,}".format(int(round(float(x))))
    except Exception:
        return "NT$ -"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ---------- 取用既有快篩/模擬數據（若有） ----------
scan = st.session_state.get("scan_data", {})  # 可能包含 estate_total、liquid、existing_insurance、one_time_need、available_cash、cash_gap
plan = st.session_state.get("plan_data", {})  # 可能包含 lt_pv / include_pv_in_cover 等

default_estate = int(scan.get("estate_total", 150_000_000))
default_liquid = int(scan.get("liquid", 20_000_000))
default_existing_ins = int(scan.get("existing_insurance", 15_000_000))

one_time_need = int(scan.get("one_time_need", 0))
available_cash = int(scan.get("available_cash", default_liquid + default_existing_ins))
cash_gap = max(0, int(scan.get("cash_gap", max(0, one_time_need - available_cash))))

lt_pv = int(plan.get("lt_pv", 0))
include_pv_in_cover = bool(plan.get("include_pv_in_cover", False))
lt_need_for_cover = lt_pv if include_pv_in_cover else 0

st.info("此模組將整合：一次性『現金』缺口 + 長期『現金流』現值（可選），並輸出整體資產配置建議。")

# ---------- 輸入：資產結構 ----------
st.markdown("### 一、輸入資產結構（粗略即可）")
st.caption("若與快篩的資產總額不同也能計算；建議最終對齊快篩數據以便報告一致。")

with st.form("asset_form"):
    c1, c2, c3 = st.columns(3)
    estate_total = c1.number_input("資產總額", min_value=0, value=default_estate, step=1_000_000)
    cash_holdings = c2.number_input("現金 / 定存", min_value=0, value=default_liquid, step=1_000_000)
    financials = c3.number_input("金融資產（股票/基金/債券）", min_value=0, value=30_000_000, step=1_000_000)

    c4, c5, c6 = st.columns(3)
    realty = c4.number_input("不動產", min_value=0, value=70_000_000, step=1_000_000)
    equity = c5.number_input("企業股權", min_value=0, value=40_000_000, step=1_000_000)
    overseas = c6.number_input("海外資產", min_value=0, value=10_000_000, step=1_000_000)

    c7, c8 = st.columns(2)
    existing_insurance = c7.number_input("既有壽險保額（可用於現金/稅務）", min_value=0, value=default_existing_ins, step=1_000_000)
    include_lt_pv = c8.selectbox("將長期現金流『現值』納入保額規劃？", ["否（自有資金）", "是（保單一次到位）"],
                                 index=1 if include_pv_in_cover else 0)

    submitted = st.form_submit_button("生成策略建議", use_container_width=True)

if not submitted:
    st.stop()

assets_sum = cash_holdings + financials + realty + equity + overseas
if assets_sum != estate_total:
    st.warning(f"目前各項合計 {format_currency(assets_sum)} 與『資產總額』 {format_currency(estate_total)} 不一致，將以合計值計算。")
    total_base = assets_sum
else:
    total_base = estate_total

# ---------- 評分與風險屬性（0~5 分） ----------
# 流動性：現金5、金融4、不動產1、股權1、海外2（粗略）
liq_weights = {"cash": 5, "fin": 4, "realty": 1, "equity": 1, "overseas": 2}
# 成長性：股權5、金融4、不動產3、海外視為4、現金1
grow_weights = {"cash": 1, "fin": 4, "realty": 3, "equity": 5, "overseas": 4}
# 稅務敏感：股權4、不動產3、海外4、金融2、現金1（分數高=更敏感/風險高）
tax_weights = {"cash": 1, "fin": 2, "realty": 3, "equity": 4, "overseas": 4}
# 法務複雜度：海外4、股權4、不動產3、金融2、現金1
legal_weights = {"cash": 1, "fin": 2, "realty": 3, "equity": 4, "overseas": 4}

def weighted_score(weights):
    if total_base == 0: return 0
    return (
        weights["cash"] * cash_holdings +
        weights["fin"] * financials +
        weights["realty"] * realty +
        weights["equity"] * equity +
        weights["overseas"] * overseas
    ) / total_base

liq_score = weighted_score(liq_weights)          # 越高越安全
grow_score = weighted_score(grow_weights)        # 越高越成長
tax_sens = weighted_score(tax_weights)           # 越高越敏感
legal_complex = weighted_score(legal_weights)    # 越高越複雜

# ---------- 建議：保險的「保護/現金」角色 ----------
lt_need_for_cover = lt_pv if include_lt_pv == "是（保單一次到位）" else 0
protection_amount = max(0, cash_gap + lt_need_for_cover)

# 若企業股權占比過高，增加經營延續的緩衝（保單信託/關鍵人風險）
equity_share = equity / total_base if total_base else 0
extra_for_business = 0
if equity_share >= 0.5:
    extra_for_business = int(0.05 * total_base)  # 額外建議5%
    protection_amount += extra_for_business

# 建議核心現金準備：若整體流動性偏低，建議提高到10%，否則5%
cash_reserve_pct = 0.10 if liq_score < 3 else 0.05
target_cash_reserve = int(cash_reserve_pct * total_base)
delta_cash = target_cash_reserve - cash_holdings

# 建議比例（保護 / 現金準備 / 成長）
protection_pct = protection_amount / total_base if total_base else 0
# 合理邊界（避免過大或過小）
protection_pct = clamp(protection_pct, 0.10, 0.35) if total_base > 0 else 0
cash_pct = clamp(target_cash_reserve / total_base if total_base else 0, 0.05, 0.15)
growth_pct = max(0.0, 1.0 - protection_pct - cash_pct)

# ---------- 視覺化：現況資產分布 ----------
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

# ---------- 視覺化：雷達圖（流動性/成長/稅務敏感/法務複雜） ----------
st.markdown("### 三、風險屬性雷達圖（0~5分）")
metrics = ["流動性", "成長性", "稅務敏感", "法務複雜"]
scores = [liq_score, grow_score, tax_sens, legal_complex]
# 雷達圖需要閉合
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

# ---------- 建議：整體配置藍圖 ----------
st.markdown("### 四、整體配置藍圖（建議比例）")
fig3, ax3 = plt.subplots()
labels2 = ["保護（保單/信託/一次性現金）", "核心現金準備", "成長資產"]
values2 = [protection_pct, cash_pct, growth_pct]
if sum(values2) == 0:
    st.info("無法生成配置建議（基數為 0）。")
else:
    ax3.pie(values2, labels=labels2,
            autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
    ax3.set_title("建議資產配置比例")
    st.pyplot(fig3)

st.markdown("#### 建議配置明細（以金額表示）")
protect_amt = int(protection_pct * total_base)
cash_amt = int(cash_pct * total_base)
growth_amt = max(0, total_base - protect_amt - cash_amt)

colT1, colT2, colT3 = st.columns(3)
colT1.metric("保護（保單/信託/一次性）", format_currency(protect_amt))
colT2.metric("核心現金準備", format_currency(cash_amt))
colT3.metric("成長資產", format_currency(growth_amt))

st.markdown("**說明與依據**：")
bullets = []
if cash_gap > 0:
    bullets.append(f"• 一次性『現金』缺口 {format_currency(cash_gap)} 以保單或等值現金鎖定，避免被迫賣資產。")
else:
    bullets.append("• 一次性『現金』缺口為 0，仍建議保留基本保額以對沖法律與稅務不確定性。")
if include_lt_pv == "是（保單一次到位）" and lt_pv > 0:
    bullets.append(f"• 長期『現金流』現值（PV）{format_currency(lt_pv)} 納入保額規劃，一次到位。")
else:
    bullets.append("• 長期『現金流』由自有資金或投資收益供應（不納入保額）。")
if equity_share >= 0.5:
    bullets.append(f"• 企業股權占比較高（{equity_share*100:.1f}%），建議額外 {format_currency(extra_for_business)} 作為『經營延續/關鍵人』緩衝（保單信託或定期壽險）。")
if cash_reserve_pct == 0.10:
    bullets.append("• 整體流動性偏低，核心現金準備提高到 **10%**，確保家庭/企業現金部位。")
else:
    bullets.append("• 流動性尚可，核心現金準備維持 **5%**。")
st.write("\n".join(bullets))

# ---------- 保存到 Session（供日後 PDF/匯出） ----------
strategy = dict(
    total_base=total_base,
    # 現況
    cash=cash_holdings, financials=financials, realty=realty, equity=equity, overseas=overseas,
    liq_score=float(liq_score), grow_score=float(grow_score),
    tax_sens=float(tax_sens), legal_complex=float(legal_complex),
    # 需求
    one_time_need=one_time_need, cash_gap=cash_gap,
    lt_pv=lt_pv, include_lt_pv=include_lt_pv == "是（保單一次到位）",
    # 建議
    protection_pct=float(protection_pct), cash_pct=float(cash_pct), growth_pct=float(growth_pct),
    protection_amount=protect_amt, cash_amount=cash_amt, growth_amount=growth_amt,
    extra_for_business=extra_for_business
)
st.session_state["asset_strategy"] = strategy

st.markdown("---")
st.markdown("**摘要**")
st.write(f"• 一次性現金缺口：{format_currency(cash_gap)}")
st.write(f"• 長期現金流現值（是否納入保額）：{format_currency(lt_pv)}（{'是' if strategy['include_lt_pv'] else '否'}）")
st.write(f"• 建議保護金額（保單/信託/一次性）：{format_currency(protect_amt)}")
st.write(f"• 核心現金準備：{format_currency(cash_amt)}")
st.write(f"• 成長資產：{format_currency(growth_amt)}")

st.success("已生成『資產配置策略』，可回到 📄 一頁式提案，把策略摘要加入報告（若需要我可幫你擴充 PDF 版面）。")

footer()

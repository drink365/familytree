# -*- coding: utf-8 -*-
import streamlit as st
import matplotlib.pyplot as plt

from utils.branding import set_page, sidebar_brand, brand_hero, footer

set_page("🚦 快篩（3 分鐘） | 影響力傳承平台", layout="centered")
sidebar_brand()

brand_hero(
    "快篩：先看一次性『現金』缺口",
    "輸入 3 個數字，立刻看懂是否需要保單/信託先把現金鎖定。"
)

# ===== 視覺樣式：一致的小而清楚 =====
st.markdown("""
<style>
.money-figure{
  font-weight: 800; line-height: 1.25;
  font-size: clamp(18px, 1.8vw, 22px);
  letter-spacing: 0.3px; white-space: nowrap;
}
.money-label{ color:#6B7280; font-size:14px; margin-bottom:4px; }
.money-card{ display:flex; flex-direction:column; gap:4px; }
.hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 18px 0; }
</style>
""", unsafe_allow_html=True)

def money_card(label: str, value: int):
    st.markdown(
        f"<div class='money-card'><div class='money-label'>{label}</div>"
        f"<div class='money-figure'>NT$ {int(value):,}</div></div>",
        unsafe_allow_html=True
    )

# ===== 表單：3 個輸入就好 =====
with st.form("quickscan"):
    c1, c2, c3 = st.columns(3)
    need_once = c1.number_input("一次性現金需求（稅+雜費）", min_value=0, value=12_000_000, step=500_000)
    cash_now  = c2.number_input("可用現金（含存款/可動用）", min_value=0, value=2_000_000, step=500_000)
    life_cov  = c3.number_input("既有壽險保額（可用於現金/稅務）", min_value=0, value=3_000_000, step=500_000)
    go = st.form_submit_button("看結果", use_container_width=True)

if not go:
    st.stop()

available = cash_now + life_cov
gap = max(0, need_once - available)

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ===== 結果卡：三個數字，一眼懂 =====
cA, cB, cC = st.columns(3)
with cA: money_card("一次性現金需求", need_once)
with cB: money_card("可用現金（含既有保單）", available)
with cC: money_card("缺口", gap)

# ===== 小圖：Need vs Available vs Gap =====
fig, ax = plt.subplots()
labels = ["需求", "可用", "缺口"]
values = [need_once, available, gap]
bars = ax.bar(labels, values)
ax.set_title("一次性現金：需求 vs 可用 vs 缺口")
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{int(b.get_height()):,}",
            ha='center', va='bottom', fontsize=9)
st.pyplot(fig, use_container_width=True)

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ===== 行動建議（溫暖、人話） =====
if gap > 0:
    st.success(
        "結論：你有一次性現金缺口，需要先用**保單/信託/等值現金**把這個缺口鎖定，"
        "避免臨到交棒時被迫賣資產。下一步：把**長期現金流**也納入，估算合併需求與建議保額。"
    )
else:
    st.info(
        "結論：一次性現金缺口為 **0**。仍建議檢視長期現金流與法稅不確定性，"
        "維持基本保障並安排核心現金。"
    )

# 將結果存入 Session，供 02/03/04 頁接續使用
st.session_state["scan_data"] = dict(
    one_time_need=int(need_once),
    available_cash=int(available),
    cash_gap=int(gap),
    liquid=int(cash_now),
    existing_insurance=int(life_cov),
    tax=int(need_once)  # 保留欄位名稱相容（若你把稅額單獨拆分，可再調）
)

# 下一步 CTA（只有一個）
st.markdown("### 下一步")
st.page_link("pages/02_GapPlanner.py", label="📊 納入長期『現金流』，估算保額與年繳", use_container_width=True)

# 可直接去下載提案（給熟客/回訪用）
st.page_link("pages/03_Proposal.py", label="🧾 直接下載一頁式提案（草案）", use_container_width=True)

footer()

# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

# ---------------- 基本設定 ----------------
set_page("🏦 資產配置建議 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("資產配置建議", "一次性現金、核心現金流、成長資產的平衡規劃")

# --------- 金額展示（與 01/02 頁一致） ---------
def money_html(value: int, size: str = "md") -> str:
    s = "NT$ {:,}".format(int(value))
    cls = "money-figure-sm" if size == "sm" else "money-figure-md"
    return f"<div class='{cls}'>{s}</div>"

# 全域樣式：統一全站
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
</style>
""", unsafe_allow_html=True)

def money_card(label: str, value: int, size: str = "md"):
    st.markdown(
        f"<div class='money-card'><div class='money-label'>{label}</div>{money_html(value, size=size)}</div>",
        unsafe_allow_html=True
    )

# ---------------- 模擬資料（實務上會從 Session 或計算結果來） ----------------
protection = 28642342
core_cash = 15200000
growth_assets = 108157000

# ---------------- 主體內容 ----------------
st.markdown("## 建議配置明細（以金額表示）")

c1, c2, c3 = st.columns(3)
with c1:
    money_card("保護（保單/信託/一次性）", protection, size="md")
with c2:
    money_card("核心現金準備", core_cash, size="md")
with c3:
    money_card("成長資產", growth_assets, size="md")

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ---------------- 說明文字 ----------------
st.markdown("#### 說明與依據：")
st.markdown("""
- 一次性『現金』缺口 NT 10,677,220 以保單或等值現金鎖定，避免被迫賣資產。  
- 長期『現金流』現值 (PV) NT 17,965,170 納入保額規劃，一次到位。  
- 整體流動性偏低，核心現金準備提高到 10%，確保家庭/企業現金部位。  
""")

footer()

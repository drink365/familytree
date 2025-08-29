# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

# 首頁只做一件事：讓使用者按下開始快篩
set_page("🏠 首頁 | 影響力傳承平台", layout="centered")
sidebar_brand()

brand_hero(
    title="3 分鐘，看懂你的傳承『現金＋現金流』差多少",
    subtitle="多數人買錯保單，不是因為不努力，而是不知道真正的缺口在哪。先看缺口，再談保單。"
)

# 主 CTA：單一按鈕
st.page_link("pages/01_QuickScan.py", label="🚦 立即開始快篩（3 分鐘）", use_container_width=True)

# 短敘事：為什麼有價值（30 秒可讀完）
with st.expander("為什麼要做這一步？（點開 20 秒）", expanded=True):
    st.markdown("""
- **少走冤枉路**：先知道一次性『現金』與長期『現金流』的缺口，之後才需要談商品。  
- **更快做決策**：你會拿到一張清楚的一頁式摘要，能和家人/股東一起討論。  
- **更安心**：我們用數據與圖像，不用行話，讓你真正看懂在做什麼。
""")

footer()

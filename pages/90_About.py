# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer, BRAND

set_page("關於我們 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("關於我們 / 聯絡方式", "以人為本，整合法稅與金融科技，一站式家族傳承")

st.markdown(f"""
**{BRAND['name']}**（{BRAND['english']}）  
{BRAND['tagline']}

- 官方網站：[{BRAND['site']['website']}]({BRAND['site']['website']})
- Email：{BRAND['site']['email']}
- 地址：{BRAND['site']['address']}
""")

st.divider()
st.markdown("### 立即行動")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/01_QuickScan.py", label="🚦 立即快篩")
with col2:
    st.page_link("pages/02_GapPlanner.py", label="📊 缺口模擬")

footer()

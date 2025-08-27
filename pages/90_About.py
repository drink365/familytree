# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer, BRAND

set_page("關於我們 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("關於我們 / 聯絡方式", "以人為本，整合法稅與金融科技，一站式家族傳承")

st.markdown(f"""
**{BRAND['name']}**（{BRAND['english']}）  
{BRAND['tagline']}

- 官方網站：{BRAND['site']['website']}
- Email：{BRAND['site']['email']}
- 電話：{BRAND['site']['phone']}
- LINE：{BRAND['site']['line']}
- 地址：{BRAND['site']['address']}

我們整合國際律師、會計師、財稅專家團隊，協助客戶完備財富載體、建立風險防範與法稅合規、打造家族永續現金流模型，達到「財富永續、基業長青、幸福永傳」。
""")

st.divider()
st.markdown("### 立即行動")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/01_QuickScan.py", label="🚦 立即快篩")
with col2:
    st.page_link("pages/02_GapPlanner.py", label="💧 缺口模擬")

footer()

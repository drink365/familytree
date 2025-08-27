# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer, BRAND

set_page("隱私與免責 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("隱私權政策與免責聲明")

st.markdown(f"**隱私權政策**  \n{BRAND['legal']['privacy']}")
st.markdown(f"**免責聲明**  \n{BRAND['legal']['disclaimer']}")

st.info("提醒：本平台做的所有試算均為教育與規劃參考，實際保單與稅務以正式文件與申報結果為準。")

footer()

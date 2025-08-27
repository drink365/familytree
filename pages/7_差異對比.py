
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, current_gap_estimate)

init_session_defaults(); render_sidebar()
st.title("差異對比")

est = current_gap_estimate()
if not est:
    st.info("請先完成『資產盤點』頁面的資產輸入。")
else:
    total_asset = st.session_state.assets
    tax_no  = int(sum(total_asset.values()) * 10_000 * st.session_state.risk_rate_no_plan)
    tax_yes = est["est_tax"]; save = tax_no - tax_yes
    c1, c2, c3 = st.columns(3)
    c1.metric("未規劃估算稅額（元）", f"{tax_no:,}")
    c2.metric("已規劃估算稅額（元）", f"{tax_yes:,}")
    c3.metric("估計節省（元）", f"{save:,}")
    df = pd.DataFrame({"稅額":[tax_no,tax_yes]}, index=["未規劃","已規劃"])
    st.bar_chart(df, use_container_width=True)

with st.expander("提示"):
    guidance_note("不是為了製造焦慮，而是幫你看見「做與不做」的實際差異。")

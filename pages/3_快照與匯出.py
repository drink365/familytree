
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from app_core import (TZ, init_session_defaults, render_sidebar, section_title, guidance_note, badge_add,
                      versions_list, version_insert, current_gap_estimate, plausible_event, maybe_fire_clarity_moment)

init_session_defaults(); render_sidebar()
st.title("快照與匯出")

section_title("💾", "保存當前快照")
if st.button("保存為新版本", use_container_width=True):
    version_insert(st.session_state.family_name, st.session_state.assets, st.session_state.plan)
    badge_add("版本管理者")
    st.success("已保存版本。徽章：版本管理者")
    plausible_event("Saved Snapshot", {})
    maybe_fire_clarity_moment()

section_title("📜", "版本記錄")
vers = versions_list()
if not vers:
    st.caption("尚無版本記錄。完成前述步驟後，可在此保存版本。")
else:
    data = [{
        "時間": v["time"].strftime("%Y-%m-%d %H:%M"),
        "家族": v["family"] or "未命名家族",
        "股權給下一代%": v["plan"]["股權給下一代"],
        "保單留配偶%": v["plan"]["保單留配偶"],
        "慈善信託%": v["plan"]["慈善信託"],
        "留現金緊急金%": v["plan"]["留現金緊急金"],
        "資產總額(萬)": sum(v["assets"].values()),
    } for v in vers]
    st.dataframe(pd.DataFrame(data), use_container_width=True)

section_title("⬇️", "下載簡版報告（HTML）")
est = current_gap_estimate()
report_html = f"""
<h2>家族傳承初診斷報告</h2>
<p>時間：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}</p>
<p>家族：{st.session_state.family_name or '未命名家族'}</p>
<h3>資產彙總（萬元）</h3>
<pre>{st.session_state.assets}</pre>
<h3>策略比例（%）</h3>
<pre>{st.session_state.plan}</pre>
<h3>重點指標（示意）</h3>
<ul>
<li>估算遺產稅：{est['est_tax'] if est else '-'} 元</li>
<li>估算可動用現金：{est['cash_liq'] if est else '-'} 元</li>
<li>流動性缺口：{(est['est_tax']-est['cash_liq']) if est else '-'} 元</li>
</ul>
<small>本報告為教育與模擬用途，非正式法律／稅務建議。</small>
"""
st.download_button("下載 HTML 報告", report_html, file_name="legacy_report.html")
if st.button("（記錄）我已下載報告"):
    plausible_event("Downloaded Report", {})
    maybe_fire_clarity_moment()

with st.expander("提示"):
    guidance_note("保存一次快照，就等於把今天的共識定格；下次打開直接延續。")

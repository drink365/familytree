
# -*- coding: utf-8 -*-
import streamlit as st
from utils.calculators import format_currency
from utils.proposal_pdf import build_proposal_pdf

st.set_page_config(page_title="📄 提案下載 | 影響力傳承平台", page_icon="📄", layout="centered")
st.title("📄 一頁式提案下載")

scan = st.session_state.get("scan")
plan = st.session_state.get("plan")

if not scan:
    st.warning("尚未完成快篩。請先到「🚦 傳承風險快篩」。")
    st.page_link("01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()
if not plan:
    st.warning("尚未完成缺口模擬。請先到「💧 缺口與保單模擬」。")
    st.page_link("02_GapPlanner.py", label="➡️ 前往模擬")
    st.stop()

client_name = st.text_input("客戶稱呼（用於提案頁面）", value="尊榮客戶")
advisor = st.text_input("顧問署名", value="Grace Huang | 永傳家族傳承教練")
notes = st.text_area("備註（選填）", value="此報告僅供教育與規劃參考，非法律與稅務意見。")

if st.button("📄 產生 PDF 提案"):
    pdf_path = build_proposal_pdf(client_name=client_name, advisor=advisor, notes=notes, scan=scan, plan=plan)
    st.success("已完成！")
    with open(pdf_path, "rb") as f:
        st.download_button("⬇ 下載一頁式提案（PDF）", data=f.read(), file_name="proposal.pdf", mime="application/pdf")

st.markdown("---")
st.markdown("**提案重點摘要**")
st.write("• 傳承準備度：{} / 100".format(st.session_state.get("scan_score", "—")))
st.write("• 預估遺產稅額：{}".format(format_currency(plan["tax"])))
st.write("• 初估流動性需求：{}".format(format_currency(plan["need"])))
st.write("• 目前可動用現金＋既有保單：{}".format(format_currency(plan["available"])))
st.write("• 初估缺口：{}".format(format_currency(plan["gap"])))
st.write("• 建議新保單：保額 {}；年繳 {}；年期 {} 年".format(
    format_currency(plan["target_cover"]), format_currency(plan["annual_premium"]), plan["pay_years"]
))

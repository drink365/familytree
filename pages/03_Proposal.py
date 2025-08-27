# -*- coding: utf-8 -*-
import io
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(page_title="📄 提案下載 | 影響力傳承平台", page_icon="📄", layout="centered")
st.title("📄 一頁式提案下載")

def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

scan = st.session_state.get("scan")
plan = st.session_state.get("plan")

if not scan:
    st.warning("尚未完成快篩。請先到「🚦 傳承風險快篩」。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()
if not plan:
    st.warning("尚未完成缺口模擬。請先到「💧 缺口與保單模擬」。")
    st.page_link("pages/02_GapPlanner.py", label="➡️ 前往模擬")
    st.stop()

def build_proposal_pdf_bytes(client_name, advisor, notes, scan, plan) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    styles = getSampleStyleSheet()
    elems = [Paragraph("傳承規劃建議（摘要）｜{}".format(client_name), styles["Title"]), Spacer(1, 6)]

    summary = [
        ["傳承準備度", "{} / 100".format(st.session_state.get("scan_score","—"))],
        ["預估遺產稅額", format_currency(plan["tax"])],
        ["初估流動性需求", format_currency(plan["need"])],
        ["可動用現金＋既有保單", format_currency(plan["available"])],
        ["初估缺口", format_currency(plan["gap"])],
    ]
    t1 = Table(summary, hAlign='LEFT', colWidths=[70*mm, 90*mm])
    t1.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
    ]))
    elems += [t1, Spacer(1, 8)]

    advice = [
        ["建議保單保額", format_currency(plan["target_cover"])],
        ["估算年繳保費", format_currency(plan["annual_premium"])],
        ["繳費年期", "{} 年".format(plan["pay_years"])],
    ]
    t2 = Table(advice, hAlign='LEFT', colWidths=[70*mm, 90*mm])
    t2.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
    ]))
    elems += [Paragraph("保單策略（以流動性為核心）", styles["Heading2"]), t2, Spacer(1, 8)]

    bullets = """
    <bullet>①</bullet> 彙整資產清單（我們提供模板），建立資產—法律—稅務對照表；
    <br/><bullet>②</bullet> 召開家族會議，討論公平機制與受益人安排；
    <br/><bullet>③</bullet> 優先啟動「流動性保額」，在完整規劃期間也能確保風險已被承接。
    """
    elems += [Paragraph("建議下一步（兩週內）", styles["Heading2"]),
              Paragraph(bullets, styles["BodyText"]), Spacer(1, 10)]

    elems += [Paragraph("備註", styles["Heading2"]), Paragraph(notes, styles["BodyText"]), Spacer(1, 6)]
    elems += [Paragraph(advisor, styles["Normal"])]

    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

client_name = st.text_input("客戶稱呼（用於提案頁面）", value="尊榮客戶")
advisor = st.text_input("顧問署名", value="Grace Huang | 永傳家族傳承教練")
notes = st.text_area("備註（選填）", value="此報告僅供教育與規劃參考，非法律與稅務意見。")

if st.button("📄 產生 PDF 提案"):
    pdf_bytes = build_proposal_pdf_bytes(client_name=client_name, advisor=advisor, notes=notes, scan=scan, plan=plan)
    st.success("已完成！")
    st.download_button("⬇ 下載一頁式提案（PDF）", data=pdf_bytes, file_name="proposal.pdf", mime="application/pdf")

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

# -*- coding: utf-8 -*-
import io, os
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer, BRAND
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

set_page("📄 提案下載 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("一頁式提案下載")

def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

scan = st.session_state.get("scan_data")
plan = st.session_state.get("plan_data")

if not scan:
    st.warning("尚未完成快篩。請先到「🚦 傳承風險快篩」。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()
if not plan:
    st.warning("尚未完成缺口模擬。請先到「📊 缺口與保單模擬」。")
    st.page_link("pages/02_GapPlanner.py", label="➡️ 前往模擬")
    st.stop()

# ---- 註冊中文字型（使用根目錄的 NotoSansTC-Regular.ttf）----
DEFAULT_FONT = "Helvetica"
try:
    if os.path.exists("NotoSansTC-Regular.ttf"):
        pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))
        DEFAULT_FONT = "NotoSansTC"
    else:
        st.caption("提示：未找到 NotoSansTC-Regular.ttf，PDF 將以預設英文字型輸出。")
except Exception as e:
    st.caption(f"字型註冊失敗（改用預設字型）：{e}")

def _logo_image_preserve_ratio(path, max_w_mm=40, max_h_mm=16):
    """讀取圖片原始尺寸，按比例縮放至不超過 max_w x max_h 的盒子。"""
    try:
        ir = ImageReader(path)
        iw, ih = ir.getSize()
        max_w = max_w_mm * mm
        max_h = max_h_mm * mm
        scale = min(max_w / iw, max_h / ih)
        img = RLImage(path)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
        return img
    except Exception:
        return None

def build_proposal_pdf_bytes(client_name, advisor, notes, scan, plan) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20*mm, bottomMargin=20*mm, leftMargin=18*mm, rightMargin=18*mm
    )

    # 樣式表統一切到中文字型
    styles = getSampleStyleSheet()
    for name in ["Title", "Heading1", "Heading2", "Heading3", "BodyText", "Normal"]:
        if name in styles:
            styles[name].fontName = DEFAULT_FONT
    styles.add(ParagraphStyle(name="H2TC", parent=styles["Heading2"], fontName=DEFAULT_FONT, spaceBefore=8, spaceAfter=4))

    elems = []

    # ---- 標題 + 右上角 LOGO（等比例縮放）----
    title_para = Paragraph(f"傳承規劃建議（摘要）｜{client_name}", styles["Title"])
    logo = _logo_image_preserve_ratio("logo.png", max_w_mm=40, max_h_mm=16) if os.path.exists("logo.png") else None
    if logo:
        header = Table([[title_para, logo]], colWidths=[130*mm, 40*mm])
        header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                                    ("ALIGN", (1,0), (1,0), "RIGHT")]))
        elems += [header, Spacer(1, 6)]
    else:
        elems += [title_para, Spacer(1, 6)]

    # ---- 摘要表 ----
    summary = [
        ["傳承準備度", f"{st.session_state.get('scan_score','—')} / 100"],
        ["預估遺產稅額", format_currency(plan["tax"])],
        ["初估流動性需求", format_currency(plan["need"])],
        ["可動用現金＋既有保單", format_currency(plan["available"])],
        ["初估缺口", format_currency(plan["gap"])],
    ]
    t1 = Table(summary, hAlign='LEFT', colWidths=[70*mm, 90*mm])
    t1.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), DEFAULT_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems += [t1, Spacer(1, 10)]

    # ---- 建議方案 ----
    elems += [Paragraph("保單策略（以流動性為核心）", styles["H2TC"])]
    advice = [
        ["建議保單保額", format_currency(plan["target_cover"])],
        ["估算年繳保費", format_currency(plan["annual_premium"])],
        ["繳費年期", f"{plan['pay_years']} 年"],
    ]
    t2 = Table(advice, hAlign='LEFT', colWidths=[70*mm, 90*mm])
    t2.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), DEFAULT_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems += [t2, Spacer(1, 10)]

    # ---- 下一步 ----
    elems += [Paragraph("建議下一步（兩週內）", styles["H2TC"])]
    bullets_text = (
        "1) 彙整資產清單（我們提供模板），建立資產—法律—稅務對照表；"
        "<br/>2) 召開家族會議，討論公平機制與受益人安排；"
        "<br/>3) 優先啟動「流動性保額」，在完整規劃期間也能確保風險已被承接。"
    )
    elems += [Paragraph(bullets_text, styles["BodyText"]), Spacer(1, 10)]

    # ---- 備註與署名 ----
    elems += [Paragraph("備註", styles["H2TC"]), Paragraph(notes, styles["BodyText"]), Spacer(1, 6)]
    elems += [Paragraph(advisor, styles["Normal"]), Spacer(1, 8)]

    # ---- 聯絡資訊（與網站一致，僅三項）----
    contact_html = (
        f"官方網站：{BRAND['site']['website']}"
        f"<br/>Email：{BRAND['site']['email']}"
        f"<br/>地址：{BRAND['site']['address']}"
    )
    elems += [Paragraph("聯絡資訊", styles["H2TC"]), Paragraph(contact_html, styles["BodyText"])]

    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

# ---- UI ----
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

footer()

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
brand_hero("一頁式提案下載", "一次性現金＋長期現金流的雙層方案")

def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

scan = st.session_state.get("scan_data")
plan = st.session_state.get("plan_data")

if not scan:
    st.warning("尚未完成快篩。請先到「🚦 3 分鐘快篩」。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()
if not plan:
    st.warning("尚未完成缺口與保單模擬。請先到「📊 缺口與保單模擬」。")
    st.page_link("pages/02_GapPlanner.py", label="➡️ 前往模擬")
    st.stop()

# 註冊中文字型
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

    styles = getSampleStyleSheet()
    for name in ["Title", "Heading1", "Heading2", "Heading3", "BodyText", "Normal"]:
        if name in styles:
            styles[name].fontName = DEFAULT_FONT
    styles.add(ParagraphStyle(name="H2TC", parent=styles["Heading2"], fontName=DEFAULT_FONT, spaceBefore=8, spaceAfter=4))

    elems = []

    # 標題 + 右上角 LOGO
    title_para = Paragraph(f"傳承規劃建議（摘要）｜{client_name}", styles["Title"])
    logo = _logo_image_preserve_ratio("logo.png", max_w_mm=40, max_h_mm=16) if os.path.exists("logo.png") else None
    if logo:
        header = Table([[title_para, logo]], colWidths=[130*mm, 40*mm])
        header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (1,0), (1,0), "RIGHT")]))
        elems += [header, Spacer(1, 6)]
    else:
        elems += [title_para, Spacer(1, 6)]

    # A. 一次性現金需求
    elems += [Paragraph("A. 一次性現金需求", styles["H2TC"])]
    tA = Table([
        ["預估遺產稅額", format_currency(scan["tax"])],
        ["一次性現金需求（稅 + 雜費）", format_currency(plan["one_time_need"] if "one_time_need" in plan else scan["one_time_need"])],
        ["可用現金 + 既有保單", format_currency(scan["available_cash"])],
        ["一次性現金缺口", format_currency(scan["cash_gap"])],
    ], colWidths=[80*mm, 80*mm])
    tA.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), DEFAULT_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems += [tA, Spacer(1, 10)]

    # B. 長期現金流
    elems += [Paragraph("B. 長期現金流（年金型）", styles["H2TC"])]
    tB = Table([
        ["每年給付金額", format_currency(plan["annual_cashflow"])],
        ["給付年期", f"{plan['years']} 年"],
        ["折現率（估）", f"{plan['discount_rate_pct']:.1f}%"],
        ["長期現金流總額", format_currency(plan["lt_total"])],
        ["長期現金流現值（PV）", format_currency(plan["lt_pv"])],
        ["是否以保單一次到位（納入保額）", "是" if plan["include_pv_in_cover"] else "否"],
    ], colWidths=[80*mm, 80*mm])
    tB.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), DEFAULT_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems += [tB, Spacer(1, 10)]

    # C. 保單策略（合併一次性 + 長期PV）
    elems += [Paragraph("C. 保單策略（合併一次性現金 + 長期現金流現值）", styles["H2TC"])]
    tC = Table([
        ["建議保單保額", format_currency(plan["target_cover"])],
        ["估算年繳保費（粗估）", format_currency(plan["annual_premium"])],
        ["繳費年期", f"{plan['pay_years']} 年"],
        ["合併需求現值", format_currency(plan["need_total"])],
        ["補齊後剩餘缺口", format_currency(plan["after_cover_gap"])],
    ], colWidths=[80*mm, 80*mm])
    tC.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), DEFAULT_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems += [tC, Spacer(1, 10)]

    # 備註與署名 + 聯絡資訊
    elems += [Paragraph("備註", styles["H2TC"]), Paragraph(notes, styles["BodyText"]), Spacer(1, 6)]
    elems += [Paragraph(advisor, styles["Normal"]), Spacer(1, 8)]

    contact_html = (
        f"官方網站：{BRAND['site']['website']}"
        f"<br/>Email：{BRAND['site']['email']}"
        f"<br/>地址：{BRAND['site']['address']}"
    )
    elems += [Paragraph("聯絡資訊", styles["H2TC"]), Paragraph(contact_html, styles["BodyText"])]

    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()

# UI 區
client_name = st.text_input("客戶稱呼（用於提案頁面）", value="尊榮客戶")
advisor = st.text_input("顧問署名", value="Grace Huang | 永傳家族傳承教練")
notes = st.text_area("備註（選填）", value="此報告僅供教育與規劃參考，非法律與稅務意見。")

# 將快篩一次性需求數字也帶進 plan（保險起見）
plan.setdefault("one_time_need", scan["one_time_need"])

if st.button("📄 產生 PDF 提案"):
    pdf_bytes = build_proposal_pdf_bytes(client_name=client_name, advisor=advisor, notes=notes, scan=scan, plan=plan)
    st.success("已完成！")
    st.download_button("⬇ 下載一頁式提案（PDF）", data=pdf_bytes, file_name="proposal.pdf", mime="application/pdf")

# 頁面摘要
st.markdown("---")
st.markdown("**提案重點摘要**")
st.write("• 一次性現金需求：{}".format(format_currency(plan['one_time_need'])))
st.write("• 可用現金 + 既有保單：{}".format(format_currency(scan['available_cash'])))
st.write("• 一次性現金缺口：{}".format(format_currency(scan['cash_gap'])))
st.write("• 長期現金流（每年 × 年期）：{} × {} 年 = {}".format(
    format_currency(plan['annual_cashflow']), plan['years'], format_currency(plan['lt_total'])
))
st.write("• 長期現金流現值（PV）：{}".format(format_currency(plan['lt_pv'])))
st.write("• 合併需求現值：{}".format(format_currency(plan['need_total'])))
st.write("• 建議新保單：保額 {}；年繳 {}；年期 {} 年".format(
    format_currency(plan["target_cover"]), format_currency(plan["annual_premium"]), plan["pay_years"]
))

footer()

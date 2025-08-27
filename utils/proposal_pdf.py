
# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from .calculators import format_currency

def build_proposal_pdf(client_name, advisor, notes, scan, plan) -> str:
    path = "/tmp/proposal.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=18*mm, rightMargin=18*mm)
    styles = getSampleStyleSheet()
    title = f"傳承規劃建議（摘要）｜{client_name}"
    elems = [Paragraph(title, styles["Title"]), Spacer(1, 6)]

    # 摘要區
    summary = [
        ["傳承準備度", f'{scan.get("score","—") if "score" in scan else "—"} / 100'],
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

    # 建議方案
    advice = [
        ["建議保單保額", format_currency(plan["target_cover"])],
        ["估算年繳保費", format_currency(plan["annual_premium"])],
        ["繳費年期", f'{plan["pay_years"]} 年'],
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

    # 下一步
    bullets = """
    <bullet>①</bullet> 彙整資產清單（我們提供模板），建立資產—法律—稅務對照表；
    <br/><bullet>②</bullet> 召開家族會議，討論公平機制與受益人安排；
    <br/><bullet>③</bullet> 優先啟動「流動性保額」，在完整規劃期間也能確保風險已被承接。
    """
    elems += [Paragraph("建議下一步（兩週內）", styles["Heading2"]), Paragraph(bullets, styles["BodyText"]), Spacer(1, 10)]

    # 備註與署名
    elems += [Paragraph("備註", styles["Heading2"]), Paragraph(notes, styles["BodyText"]), Spacer(1, 6)]
    elems += [Paragraph(advisor, styles["Normal"])]

    doc.build(elems)
    return path

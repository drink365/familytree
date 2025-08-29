
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import json, os, datetime

_BRAND = json.load(open(os.path.join(os.path.dirname(__file__), "..", "brand.json"), "r", encoding="utf-8"))
_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", _BRAND.get("FONT_TTF", "NotoSansTC-Regular.ttf"))

FONT_NAME = "NotoSansTC"
try:
    if os.path.isfile(_FONT_PATH) and (FONT_NAME not in pdfmetrics.getRegisteredFontNames()):
        pdfmetrics.registerFont(TTFont(FONT_NAME, _FONT_PATH))
except Exception:
    FONT_NAME = "Helvetica"

_styles = getSampleStyleSheet()
styles = {
    "title": ParagraphStyle("title", parent=_styles["Heading1"], fontName=FONT_NAME, fontSize=18, leading=22, spaceAfter=8, textColor=colors.HexColor(_BRAND["PRIMARY"])),
    "h2": ParagraphStyle("h2", parent=_styles["Heading2"], fontName=FONT_NAME, fontSize=13, leading=18, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#0f172a")),
    "body": ParagraphStyle("body", parent=_styles["Normal"], fontName=FONT_NAME, fontSize=10.5, leading=14),
    "small": ParagraphStyle("small", parent=_styles["Normal"], fontName=FONT_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#64748b")),
}

def _resolve_logo_path():
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    cand = [
        os.path.join(base_dir, _BRAND.get("LOGO_WIDE", "logo.png")),
        os.path.join(base_dir, _BRAND.get("LOGO_SQUARE", "logo2.png")),
        os.path.join(base_dir, "logo.png"),
        os.path.join(base_dir, "logo2.png"),
    ]
    for p in cand:
        if os.path.isfile(p):
            return p
    return None

def _draw_header_footer(c: canvas.Canvas, doc):
    w, h = A4
    band_h = 20 * mm
    c.saveState()

    # Top band
    c.setFillColor(colors.HexColor(_BRAND["BG"]))
    c.rect(0, h - band_h, w, band_h, stroke=0, fill=1)

    # Left logo (auto-fit)
    try:
        logo_path = _resolve_logo_path()
        if logo_path:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            target_h = band_h - 6 * mm  # padding
            scale = target_h / float(ih)
            draw_w = iw * scale
            draw_h = ih * scale
            x = 10 * mm
            y = h - band_h + (band_h - draw_h) / 2
            c.drawImage(img, x, y, width=draw_w, height=draw_h, mask="auto")
    except Exception:
        pass

    # Right title
    c.setFont(FONT_NAME, 10)
    c.setFillColor(colors.HexColor("#344054"))
    c.drawRightString(w - 15 * mm, h - 6 * mm, _BRAND["NAME"])

    # Footer center: org + domain (no date to keep clean)
    c.setFillColor(colors.HexColor("#6b7280"))
    c.setFont(FONT_NAME, 9)
    footer_text = "永傳家族辦公室  gracefo.com"
    text_width = c.stringWidth(footer_text, FONT_NAME, 9)
    c.drawString((w - text_width) / 2, 10 * mm, footer_text)

    c.restoreState()

def build_branded_pdf_bytes(story_flow):
    from io import BytesIO
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=28*mm, bottomMargin=20*mm, title=_BRAND["NAME"])
    def _on_page(c, d): _draw_header_footer(c, d)
    doc.build(story_flow, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()

def p(text, style="body"): return Paragraph(text, styles[style])
def h2(text): return Paragraph(text, styles["h2"])
def title(text): return Paragraph(text, styles["title"])
def spacer(h=6): return Spacer(0, h)

def table(data, colWidths=None):
    t = Table(data, colWidths=colWidths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), FONT_NAME),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("LINEABOVE", (0,0), (-1,0), 0.5, colors.HexColor("#e5e7eb")),
        ("LINEBELOW", (0,0), (-1,0), 0.5, colors.HexColor("#e5e7eb")),
        ("GRID", (0,1), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f8fafc")),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fcfcfd")]),
    ]))
    return t

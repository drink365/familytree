# -*- coding: utf-8 -*-
import io
import os
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

# ---------- PDF ----------
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ---------- Charts (for appendix) ----------
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# ---------------- 基本設定 ----------------
set_page("📄 一頁式提案 | 影響力傳承平台", layout="centered")
sidebar_brand()
brand_hero("一頁式提案（摘要）", "先補足一次性現金，再設計穩定現金流")

# ---------------- 共用樣式（與 01/02/04 統一） ----------------
def money_html(value: int, size: str = "md") -> str:
    s = "NT$ {:,}".format(int(value))
    cls = "money-figure-sm" if size == "sm" else "money-figure-md"
    return f"<div class='{cls}'>{s}</div>"

st.markdown("""
<style>
.money-figure-md{
  font-weight: 800;
  line-height: 1.25;
  font-size: clamp(18px, 1.8vw, 22px);
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.money-figure-sm{
  font-weight: 700;
  line-height: 1.25;
  font-size: clamp(16px, 1.6vw, 20px);
  letter-spacing: 0.2px;
  white-space: nowrap;
}
.money-label{ color:#6B7280; font-size:14px; margin-bottom:4px; }
.money-card{ display:flex; flex-direction:column; gap:4px; }
.hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 24px 0; }
.bullet-text{ font-size:16px; color:#374151; line-height:1.7;
  font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif; }
</style>
""", unsafe_allow_html=True)

def money_card(label: str, value: int, size: str = "md"):
    st.markdown(
        f"<div class='money-card'><div class='money-label'>{label}</div>{money_html(value, size=size)}</div>",
        unsafe_allow_html=True
    )

def fmt(x:int) -> str:
    return "NT$ {:,}".format(int(x))

# ---------------- 取用資料 ----------------
scan = st.session_state.get("scan_data")
plan = st.session_state.get("plan_data")
strategy = st.session_state.get("asset_strategy")  # 04_AssetPlanner.py 寫入

if not scan or not plan:
    st.warning("資料不足。請先完成：🚦 快篩 → 📊 缺口與保單模擬。")
    st.page_link("pages/01_QuickScan.py", label="➡️ 前往快篩")
    st.stop()

# 快篩
one_time_need   = int(scan.get("one_time_need", 0))
available_cash  = int(scan.get("available_cash", 0))
cash_gap        = int(scan.get("cash_gap", 0))
tax_amount      = int(scan.get("tax", 0))

# 模擬
annual_cashflow = int(plan.get("annual_cashflow", 0))
years           = int(plan.get("years", 0))
lt_pv           = int(plan.get("lt_pv", 0))
discount_rate   = float(plan.get("discount_rate_pct", 0.0))
include_pv      = bool(plan.get("include_pv_in_cover", False))
target_cover    = int(plan.get("target_cover", 0))
pay_years       = int(plan.get("pay_years", 0))
annual_premium  = int(plan.get("annual_premium", 0))
need_total      = int(plan.get("need_total", 0))
after_gap       = int(plan.get("after_cover_gap", 0))

# ---------------- 頁面預覽（與其它頁一致的字級） ----------------
st.markdown("### 提案重點（摘要）")
c1, c2, c3 = st.columns(3)
with c1:
    money_card("一次性現金需求（稅+雜費）", one_time_need, "md")
with c2:
    money_card("長期現金流現值（PV）", lt_pv, "md")
with c3:
    money_card("合併需求現值", need_total, "md")

c4, c5, c6 = st.columns(3)
with c4:
    money_card("缺口（可用現金後）", cash_gap, "sm")
with c5:
    money_card("建議保額（草案）", target_cover, "sm")
with c6:
    money_card("估算年繳保費", annual_premium, "sm")

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

st.markdown("**說明與依據：**")
bullets = [
    f"• 已估算遺產稅 {fmt(tax_amount)}，一次性『現金』需求 {fmt(one_time_need)}。",
    f"• 長期『現金流』每年 {fmt(annual_cashflow)} × {years} 年；折現率 {discount_rate:.1f}% → 現值（PV）{fmt(lt_pv)}。",
    f"• 合併需求現值 = 一次性現金 + 現金流PV → {fmt(need_total)}；可用現金 {fmt(available_cash)}。",
    f"• 建議以保單/信託先把缺口 {fmt(cash_gap)} 鎖定，再依風險承受度配置核心現金與成長資產。",
]
st.markdown("<div class='bullet-text'>" + "<br/>".join(bullets) + "</div>", unsafe_allow_html=True)

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ---------------- PDF 設定 ----------------
EMAIL   = "123@gracefo.com"
ADDRESS = "台北市中山區南京東路二段101號9樓"
WEBSITE = "https://gracefo.com"

def register_font_for_pdf():
    ttf_candidates = ["./NotoSansTC-Regular.ttf", "NotoSansTC-Regular.ttf"]
    for p in ttf_candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("NotoSansTC", p))
                return "NotoSansTC"
            except Exception:
                pass
    return "Helvetica"

def setup_font_for_matplotlib():
    # 讓附錄圖表中文字使用 NotoSansTC（若存在）
    for p in ["./NotoSansTC-Regular.ttf", "NotoSansTC-Regular.ttf"]:
        if os.path.exists(p):
            try:
                font_manager.fontManager.addfont(p)
                plt.rcParams["font.family"] = ["Noto Sans TC", "Microsoft JhengHei", "sans-serif"]
                break
            except Exception:
                pass
    plt.rcParams["axes.unicode_minus"] = False

def draw_logo_keep_ratio(c: canvas.Canvas, img_path: str, x: float, y: float, target_h: float):
    """把 logo 放在 (x,y) 的上方，固定高度 target_h，以等比例縮放。"""
    try:
        img = ImageReader(img_path)
        iw, ih = img.getSize()
        scale = target_h / float(ih)
        w = iw * scale
        h = target_h
        # y 是「上緣」座標，ReportLab 需要左下角，所以減去高度
        c.drawImage(img, x, y - h, width=w, height=h, preserveAspectRatio=True, mask='auto')
        return w, h
    except Exception:
        return 0, 0

def fig_to_imagereader(fig, dpi=160):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return ImageReader(buf)

# ---------------- 產生 PDF（表格版） ----------------
def build_pdf_bytes():
    font_name = register_font_for_pdf()
    setup_font_for_matplotlib()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 16 * mm
    left = margin
    right = W - margin
    top = H - margin

    # ====== 頁首：Logo + 標題（Logo 定位固定不飄） ======
    # 固定高度 14mm，放左上角；再在其右側畫標題
    logo_w, logo_h = draw_logo_keep_ratio(c, "./logo.png", left, top, target_h=14*mm)
    title_x = left + (logo_w + 6*mm)
    title_y = top - 2*mm

    c.setFont(font_name, 20)
    c.drawString(title_x, title_y - 4*mm, "傳承規劃建議（摘要）")
    c.setFont(font_name, 11)
    c.setFillColorRGB(0.35, 0.35, 0.38)
    c.drawString(title_x, title_y - 11*mm, "先補足現金，再設計穩定現金流")
    c.setFillColorRGB(0, 0, 0)

    cursor_y = top - (logo_h + 18*mm)

    # ====== 表格外框 ======
    # 表格的列（左欄標題 / 右欄金額）
    rows = [
        ("一次性現金需求（稅+雜費）", fmt(one_time_need), True),
        ("可用現金 + 既有保單",       fmt(available_cash), False),
        ("一次性現金缺口",           fmt(cash_gap), False),
        ("", "", False),  # 分隔線
        (f"長期現金流（每年×年數）", f"{fmt(annual_cashflow)} × {years}", False),
        ("折現率（估）",            f"{discount_rate:.1f}%", False),
        ("現金流現值（PV）",        fmt(lt_pv), False),
        ("", "", False),  # 分隔線
        ("合併需求現值（一次性 + 現金流PV）", fmt(need_total), True),
        ("建議保額（草案）",         fmt(target_cover), False),
        ("估算年繳保費",             fmt(annual_premium), False),
    ]

    # 表格尺寸與欄寬
    col1_w = 90 * mm
    col2_w = (right - left) - col1_w
    row_h  = 9 * mm
    table_top = cursor_y
    table_left = left

    # 表格背景與邊框
    c.setLineWidth(0.8)
    c.rect(table_left, table_top - row_h*len(rows), col1_w + col2_w, row_h*len(rows), stroke=1, fill=0)

    # 橫線
    for i in range(1, len(rows)):
        y = table_top - row_h * i
        c.line(table_left, y, table_left + col1_w + col2_w, y)

    # 直線（分欄）
    c.line(table_left + col1_w, table_top, table_left + col1_w, table_top - row_h*len(rows))

    # 逐列填入
    for idx, (label, value, is_big) in enumerate(rows):
        y = table_top - row_h * idx - 6*mm  # 內縮 3mm + 行高
        if label:  # 分隔列 label 為空
            c.setFont(font_name, 11)
            c.drawString(table_left + 3*mm, y, label)
        c.setFont(font_name, 16 if is_big else 13)
        if value:
            c.drawRightString(table_left + col1_w + col2_w - 3*mm, y, value)

    cursor_y = table_top - row_h*len(rows) - 10*mm

    # ====== 說明（bullet） ======
    c.setFont(font_name, 12)
    c.drawString(left, cursor_y, "重點與依據")
    cursor_y -= 6*mm
    c.setFont(font_name, 10.5)
    lines = [
        f"• 已估算遺產稅 {fmt(tax_amount)}；一次性『現金』需求 {fmt(one_time_need)}。",
        f"• 長期『現金流』每年 {fmt(annual_cashflow)} × {years} 年；折現率 {discount_rate:.1f}% → 現值（PV）{fmt(lt_pv)}。",
        f"• 合併需求現值 = 一次性現金 + 現金流PV → {fmt(need_total)}；可用現金 {fmt(available_cash)}。",
        "• 先用保單/信託鎖定缺口，再依風險承受度配置核心現金與成長資產。",
        "• 本報告僅供教育與規劃參考，非法律與稅務意見。",
    ]
    for sline in lines:
        c.drawString(left, cursor_y, sline)
        cursor_y -= 6*mm

    # ====== 底部品牌 ======
    c.setFont(font_name, 9.5)
    c.setFillColorRGB(0.35, 0.35, 0.38)
    c.drawString(left, 14*mm, "Grace Huang | 永傳家族傳承練")
    c.drawRightString(right, 14*mm, f"{EMAIL}  |  {WEBSITE}")
    c.drawRightString(right, 9*mm, ADDRESS)
    c.setFillColorRGB(0, 0, 0)

    # ====== 附錄頁：資產配置藍圖（若有 strategy） ======
    if strategy:
        c.showPage()
        # 標題
        c.setFont(font_name, 18)
        c.drawString(left, H - margin - 8*mm, "附錄：資產配置藍圖（進階）")

        # 取資料
        total_base = float(strategy.get("total_base", 0))
        cash = float(strategy.get("cash", 0))
        financials = float(strategy.get("financials", 0))
        realty = float(strategy.get("realty", 0))
        equity = float(strategy.get("equity", 0))
        overseas = float(strategy.get("overseas", 0))

        protection_pct = float(strategy.get("protection_pct", 0.0))
        cash_pct = float(strategy.get("cash_pct", 0.0))
        growth_pct = float(strategy.get("growth_pct", 0.0))

        liq_score = float(strategy.get("liq_score", 0.0))
        grow_score = float(strategy.get("grow_score", 0.0))
        tax_sens = float(strategy.get("tax_sens", 0.0))
        legal_complex = float(strategy.get("legal_complex", 0.0))

        # 1) 現況資產分布
        fig1, ax1 = plt.subplots()
        labels1 = ["現金/定存", "金融資產", "不動產", "企業股權", "海外資產"]
        values1 = [cash, financials, realty, equity, overseas]
        if sum(values1) > 0:
            ax1.pie(values1, labels=labels1, autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
            ax1.set_title("資產結構（現況）")
        img1 = fig_to_imagereader(fig1)

        # 2) 風險雷達
        metrics = ["流動性", "成長性", "稅務敏感", "法務複雜"]
        scores = [liq_score, grow_score, tax_sens, legal_complex]
        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]
        scores_plot = scores + scores[:1]
        fig2 = plt.figure()
        ax2 = plt.subplot(111, polar=True)
        ax2.set_theta_offset(np.pi/2)
        ax2.set_theta_direction(-1)
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels(metrics)
        ax2.plot(angles, scores_plot, linewidth=2)
        ax2.fill(angles, scores_plot, alpha=0.1)
        ax2.set_ylim(0, 5)
        img2 = fig_to_imagereader(fig2)

        # 3) 建議配置
        fig3, ax3 = plt.subplots()
        labels2 = ["保護（保單/信託/一次性）", "核心現金準備", "成長資產"]
        values2 = [protection_pct, cash_pct, growth_pct]
        if sum(values2) > 0:
            ax3.pie(values2, labels=labels2, autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
            ax3.set_title("建議資產配置比例")
        img3 = fig_to_imagereader(fig3)

        # 佈局
        c.drawImage(img1, left, 120*mm, width=85*mm, height=70*mm, mask='auto')
        c.drawImage(img2, left + 95*mm, 120*mm, width=85*mm, height=70*mm, mask='auto')
        c.drawImage(img3, left, 28*mm, width=180*mm, height=80*mm, mask='auto')

        c.setFont(font_name, 10.5)
        c.setFillColorRGB(0.35, 0.35, 0.38)
        c.drawString(left, 18*mm, "註：此附錄基於使用者在『資產配置策略』頁輸入之示意數據，僅供規劃溝通參考。")
        c.setFillColorRGB(0, 0, 0)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf

# 下載按鈕
pdf_buf = build_pdf_bytes()
st.download_button(
    label="📥 下載一頁式提案（PDF，表格版）",
    data=pdf_buf,
    file_name="Proposal.pdf",
    mime="application/pdf",
    use_container_width=True,
)

footer()

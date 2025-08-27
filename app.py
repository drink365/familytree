# -*- coding: utf-8 -*-
"""
影響力｜傳承決策平台（單檔版）
- Tabs：🚦 快篩 → 💧 缺口&保單模擬 → 📄 一頁式提案
- 內含：稅額/缺口/分數計算、ReportLab 產生 PDF、matplotlib 單圖對比
- 不使用 st.page_link（避免多頁架構需求），部署最簡單
"""
from typing import Dict, Tuple, List
import io
import streamlit as st
import matplotlib.pyplot as plt

# ====== 基本設定 ======
st.set_page_config(page_title="影響力｜傳承決策平台", page_icon="📦", layout="wide")
st.title("📦 保單策略規劃｜影響力傳承平台")
st.caption("為高資產家庭設計最適保障結構，讓每一分資源，都能守護最重要的事。")

# ====== 計算函式 ======
# 台灣遺產稅級距（速算扣除）
# 0～56,210,000：10%（速算 0）
# 56,210,001～112,420,000：15%（速算 2,810,000）
# 112,420,001 以上：20%（速算 8,430,000）
def taiwan_estate_tax(taxable_amount: int) -> int:
    x = int(max(0, taxable_amount))
    if x <= 56_210_000:
        return int(x * 0.10)
    elif x <= 112_420_000:
        return int(x * 0.15 - 2_810_000)
    else:
        return int(x * 0.20 - 8_430_000)

def liquidity_need_estimate(tax: int, fees_ratio: float = 0.01) -> int:
    tax = int(max(0, tax))
    fees = int(tax * max(0.0, fees_ratio))
    return tax + fees

def plan_with_insurance(need: int, available: int, cover: int, pay_years: int, premium_ratio: float):
    """
    估算年繳保費（粗估）：annual ≈ cover / premium_ratio / pay_years
    premium_ratio 例：10 代表保額/年繳 ≈ 10*年期
    """
    need = int(max(0, need))
    available = int(max(0, available))
    cover = int(max(0, cover))
    premium_ratio = max(1.0, float(premium_ratio))
    pay_years = int(max(1, pay_years))
    annual_premium = int(cover / premium_ratio / pay_years)
    surplus_after_cover = int(available + cover - need)
    return dict(annual_premium=annual_premium, surplus_after_cover=surplus_after_cover)

def quick_preparedness_score(scan: Dict) -> Tuple[int, List[str]]:
    """簡易打分：100滿分，以缺口風險與治理狀態加權。"""
    score = 100
    flags = []

    estate = max(1, int(scan.get("estate_total", 0)))
    liquid = int(scan.get("liquid", 0))
    liquid_ratio = liquid / estate
    if liquid_ratio < 0.10:
        score -= 20; flags.append("流動性比例偏低（<10%），遇遺產稅可能需賣資產。")
    elif liquid_ratio < 0.20:
        score -= 10; flags.append("流動性比例較低（<20%）。")

    if scan.get("cross_border") == "是":
        score -= 10; flags.append("存在跨境資產/家人，需另行檢視法稅合規與受益人居住地。")

    marital = scan.get("marital")
    if marital in ["離婚/分居", "再婚/有前任"]:
        score -= 10; flags.append("婚姻結構較複雜，建議儘早訂定遺囑/信託避免爭議。")

    if scan.get("has_will") in ["沒有", "有（但未更新）"]:
        score -= 10; flags.append("沒有有效遺囑或未更新。")
    if scan.get("has_trust") in ["沒有", "規劃中"]:
        score -= 10; flags.append("尚未建立信託/保單信託。")

    existing_ins = int(scan.get("existing_insurance", 0))
    if existing_ins < estate * 0.05:
        score -= 10; flags.append("既有保額偏低，恐不足以應付稅務與現金流衝擊。")

    score = max(0, min(100, score))
    return score, flags

def format_currency(x: int) -> str:
    return "NT$ {:,}".format(int(x))

# ====== PDF 產生（ReportLab） ======
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm

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

# ====== Tabs：主流程 ======
tab1, tab2, tab3 = st.tabs(["🚦 快篩（3 分鐘）", "💧 缺口 & 保單模擬", "📄 一頁式提案"])

with tab1:
    st.subheader("傳承風險快篩")
    with st.form("scan"):
        c1, c2 = st.columns(2)
        residence = c1.selectbox("主要稅務地/居住地", ["台灣", "大陸/中國", "美國", "其他"], index=0)
        cross_border = c2.selectbox("是否有跨境資產/家人", ["否", "是"], index=0)

        c3, c4 = st.columns(2)
        marital = c3.selectbox("婚姻狀態", ["未婚", "已婚", "離婚/分居", "再婚/有前任"], index=1)
        heirs_n = c4.number_input("潛在繼承/受贈人數（含子女、父母、配偶）", min_value=0, max_value=20, value=3, step=1)

        st.markdown("#### 主要資產概況（粗略估算即可）")
        c5, c6 = st.columns(2)
        estate_total = c5.number_input("資產總額（TWD）", min_value=0, value=150_000_000, step=1_000_000)
        liquid = c6.number_input("可動用流動資產（現金/定存/投資）（TWD）", min_value=0, value=20_000_000, step=1_000_000)

        c7, c8 = st.columns(2)
        realty = c7.number_input("不動產（TWD）", min_value=0, value=70_000_000, step=1_000_000)
        equity = c8.number_input("公司股權（TWD）", min_value=0, value=40_000_000, step=1_000_000)

        c9, c10 = st.columns(2)
        debts = c9.number_input("負債（TWD）", min_value=0, value=10_000_000, step=1_000_000)
        existing_insurance = c10.number_input("既有壽險保額（可用於稅務/現金流）（TWD）", min_value=0, value=15_000_000, step=1_000_000)

        c11, c12 = st.columns(2)
        has_will = c11.selectbox("是否已有遺囑", ["沒有", "有（但未更新）", "有（最新）"], index=0)
        has_trust = c12.selectbox("是否已有信託/保單信託", ["沒有", "規劃中", "已建立"], index=0)

        submitted = st.form_submit_button("計算準備度與風險")

    if submitted:
        scan = dict(
            residence=residence, cross_border=cross_border, marital=marital, heirs_n=heirs_n,
            estate_total=estate_total, liquid=liquid, realty=realty, equity=equity,
            debts=debts, existing_insurance=existing_insurance, has_will=has_will, has_trust=has_trust
        )
        st.session_state["scan"] = scan
        score, flags = quick_preparedness_score(scan)
        st.session_state["scan_score"] = score

        st.success("✅ 快篩完成")
        st.metric("傳承準備度分數", f"{score}/100")
        if flags:
            st.markdown("**主要風險提示**：")
            for f in flags:
                st.write("• " + f)
        st.info("下一步 → 轉到「💧 缺口 & 保單模擬」分頁，調整年期/幣別，拿到第一版保單草案。")
    else:
        st.info("完成上方問卷並提交；或直接切換到下一分頁繼續。")

with tab2:
    st.subheader("流動性缺口與保單策略模擬")
    scan = st.session_state.get("scan")
    if not scan:
        st.warning("尚未完成快篩。請先到『🚦 快篩』分頁。")
    else:
        st.markdown("依台灣稅制（10% / 15% / 20%）與標準扣除進行估算（僅供規劃參考）")

        c1, c2 = st.columns(2)
        funeral = c1.number_input("喪葬費用（上限 1,380,000）", min_value=0, max_value=5_000_000, value=1_380_000, step=10_000)
        supportees = c2.number_input("其他受扶養人數（每人 560,000）", min_value=0, max_value=10, value=0, step=1)

        c3, c4 = st.columns(2)
        spouse_deduction = c3.number_input("配偶扣除（預設 5,530,000）", min_value=0, max_value=10_000_000, value=5_530_000, step=10_000)
        basic_exempt = c4.number_input("基本免稅額（預設 13,330,000）", min_value=0, max_value=50_000_000, value=13_330_000, step=10_000)

        taxable_base = max(0, scan["estate_total"] - scan["debts"])
        deductions = basic_exempt + spouse_deduction + funeral + supportees * 560_000
        tax = taiwan_estate_tax(max(0, taxable_base - deductions))
        st.metric("預估遺產稅額", format_currency(tax))

        need = liquidity_need_estimate(tax=tax, fees_ratio=0.01)
        st.metric("初估流動性需求（含雜費 1%）", format_currency(need))

        available = scan["liquid"] + scan["existing_insurance"]
        gap = max(0, need - available)
        st.metric("初估流動性缺口", format_currency(gap))

        st.markdown("---")
        st.markdown("#### 保單策略模擬")

        c5, c6 = st.columns(2)
        target_cover = c5.number_input("新保單目標保額", min_value=0, value=int(gap), step=1_000_000)
        pay_years = c6.selectbox("繳費年期", [1, 3, 5, 6, 7, 10], index=3)

        c7, c8 = st.columns(2)
        assumed_IRR = c7.slider("保單內含報酬率假設（僅估年繳）", min_value=0.0, max_value=6.0, value=2.5, step=0.1)
        premium_ratio = c8.slider("年繳 / 保額 比例（粗估）", min_value=1.0, max_value=20.0, value=10.0, step=0.5)

        plan = plan_with_insurance(need=need, available=available, cover=target_cover,
                                   pay_years=pay_years, premium_ratio=premium_ratio)
        st.write("**估算年繳保費**：", format_currency(plan["annual_premium"]))
        st.write("**補齊缺口後的剩餘**：", format_currency(plan["surplus_after_cover"]))

        # 對比圖（每圖單獨一張，無指定顏色）
        fig1, ax1 = plt.subplots()
        labels = ["不用保單", "加上保單"]
        values = [max(0, need - available), max(0, need - (available + target_cover))]
        ax1.bar(labels, values)
        ax1.set_ylabel("剩餘缺口（TWD）")
        ax1.set_title("保單介入前後的缺口對比")
        st.pyplot(fig1)

        # 保存到 session 提供 PDF 使用
        st.session_state["plan"] = dict(
            need=need, available=available, gap=gap, target_cover=target_cover,
            pay_years=pay_years, annual_premium=plan["annual_premium"],
            surplus_after_cover=plan["surplus_after_cover"],
            tax=tax, deductions=deductions, taxable_base=taxable_base
        )
        st.info("下一步：切到『📄 一頁式提案』分頁，下載 PDF。")

with tab3:
    st.subheader("一頁式提案下載")
    scan = st.session_state.get("scan")
    plan = st.session_state.get("plan")
    if not scan:
        st.warning("尚未完成快篩。請先到『🚦 快篩』分頁。")
    elif not plan:
        st.warning("尚未完成缺口模擬。請先到『💧 缺口 & 保單模擬』分頁。")
    else:
        client_name = st.text_input("客戶稱呼（用於提案頁面）", value="尊榮客戶")
        advisor = st.text_input("顧問署名", value="Grace Huang｜永傳家族傳承教練")
        notes = st.text_area("備註（選填）", value="此報告僅供教育與規劃參考，非法律與稅務意見。")

        if st.button("📄 產生 PDF 提案"):
            pdf_bytes = build_proposal_pdf_bytes(client_name=client_name, advisor=advisor,
                                                 notes=notes, scan=scan, plan=plan)
            st.success("已完成！")
            st.download_button("⬇ 下載一頁式提案（PDF）", data=pdf_bytes,
                               file_name="proposal.pdf", mime="application/pdf")

st.divider()
st.markdown("""
**隱私聲明**：本平台不會將資料上傳至第三方伺服器；資料僅保存於您的瀏覽器工作階段。  
**免責聲明**：本工具僅供教育與規劃參考，非法律與稅務意見；請與您的專業顧問確認後再做決策。
""")

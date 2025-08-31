# pages_policy.py
import os
import io
import streamlit as st
from datetime import datetime
from typing import Optional

# （舊版備援）簡易 PDF 工具：若找不到 ReportLab 會用它輸出文字版
try:
    from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer  # type: ignore
    LEGACY_PDF_AVAILABLE = True
except Exception:
    LEGACY_PDF_AVAILABLE = False

# ReportLab（新版，含 Logo 與表格）
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# ----------------------------- Helpers -----------------------------
def _fmt_currency(n: float, currency: str) -> str:
    """四捨五入至個位數並加千分位，依幣別顯示 NT$/US$（一般用，非 Markdown）。"""
    try:
        sym = "NT$" if currency == "TWD" else "US$"
        return f"{sym}{float(round(n)):,.0f}"
    except Exception:
        return "—"

def _fmt_currency_md(n: float, currency: str) -> str:
    """供 Markdown 使用的貨幣字串（把 $ 轉成 \$，避免被當 LaTeX）。"""
    s = _fmt_currency(n, currency)
    return s.replace("$", "\\$")

def _currency_name(currency: str) -> str:
    return "新台幣" if currency == "TWD" else "美元"

def _safe_int(x: Optional[float], default: int = 0) -> int:
    try:
        return int(x) if x is not None else default
    except Exception:
        return default

def _safe_float(x: Optional[float], default: float = 0.0) -> float:
    try:
        return float(x) if x is not None else default
    except Exception:
        return default

def _estimate_cash_value(premium: float, years: int, irr_pct: float, horizon: int) -> int:
    """以 IRR 為年化報酬率，估算第 horizon 年的示意現金價值（年末投入；僅會談示意）。"""
    try:
        irr = max(0.0, float(irr_pct) / 100.0)
        horizon = max(1, int(horizon))
        terms = min(int(years), horizon)
        fv = 0.0
        for t in range(1, terms + 1):
            fv += float(premium) * (1.0 + irr) ** (horizon - t)
        return int(round(fv))
    except Exception:
        return 0

# ------------------ 動態現金價值模擬（含防穿透） ------------------
def _simulate_path(
    premium: float,
    years: int,
    irr_pct: float,
    inflow_enabled: bool,
    inflow_mode: str,   # "fixed" / "ratio"
    start_year: int,
    years_in: int,
    inflow_amt: float,
    inflow_ratio_pct: float,
    sim_years: Optional[int] = None,
):
    """
    年度序列：投入保費 → 依 IRR 成長 → 進行提領；若提領超過可用現金價值則降額（防穿透）。
    回傳：timeline, cv(年末現金價值), annual_cf, cum_cf, clamped_years(list)
    """
    r = max(0.0, _safe_float(irr_pct) / 100.0)
    T = sim_years or max(_safe_int(years), _safe_int(start_year) + _safe_int(years_in) - 1, _safe_int(years) + 10)
    T = max(T, 1)

    cv = 0.0
    cv_series, ann_cf_series, cum_cf_series, clamped_years = [], [], [], []
    cum = 0.0

    for y in range(1, T + 1):
        premium_y = float(premium) if y <= int(years) else 0.0
        cv += premium_y
        cv *= (1.0 + r)

        withdraw = 0.0
        if inflow_enabled and (int(start_year) <= y < int(start_year) + int(years_in)):
            if inflow_mode == "fixed" and float(inflow_amt) > 0:
                withdraw = float(inflow_amt)
            elif inflow_mode == "ratio" and float(inflow_ratio_pct) > 0:
                withdraw = cv * (float(inflow_ratio_pct) / 100.0)
            if withdraw > cv:
                withdraw = cv
                clamped_years.append(y)
            cv -= withdraw

        annual_cf = withdraw - premium_y
        cum += annual_cf

        cv_series.append(cv)
        ann_cf_series.append(annual_cf)
        cum_cf_series.append(cum)

    return {
        "timeline": list(range(1, T + 1)),
        "cv": cv_series,
        "annual_cf": ann_cf_series,
        "cum_cf": cum_cf_series,
        "clamped_years": clamped_years,
    }

# 倍數（已減半）
FACE_MULTIPLIERS = {
    "保守": {"放大財富傳承": 5, "補足遺產稅": 4, "退休現金流": 3, "企業風險隔離": 4},
    "中性": {"放大財富傳承": 6, "補足遺產稅": 5, "退休現金流": 4, "企業風險隔離": 5},
    "積極": {"放大財富傳承": 7, "補足遺產稅": 6, "退休現金流": 5, "企業風險隔離": 6},
}

# --------------- ReportLab PDF：Logo + 表格（若可用） ---------------
def _build_pdf_reportlab(
    title_text: str,
    summary_lines: list[str],
    table_headers: list[str],
    table_rows: list[list[str]],
    logo_path: Optional[str] = None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2s = styles["Heading2"]
    normal = styles["Normal"]
    # 調整字距大小（Heading1 太大可略縮）
    h1.fontSize = 20
    h1.leading = 24

    flow = []
    # Logo（可選）
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image(logo_path)
            # 縮放到適合的寬度
            max_w = 140
            iw, ih = img.drawWidth, img.drawHeight
            if iw > max_w:
                ratio = max_w / iw
                img.drawWidth = iw * ratio
                img.drawHeight = ih * ratio
            flow.append(img)
            flow.append(Spacer(1, 12))
        except Exception:
            pass

    flow.append(Paragraph(title_text, h1))
    flow.append(Spacer(1, 6))

    for s in summary_lines:
        flow.append(Paragraph(s, normal))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph("現金價值與現金流（示意）", h2s))
    flow.append(Spacer(1, 6))

    # 表格資料
    data = [table_headers] + table_rows
    # 欄寬配置（百分比）
    # 年度 | 當年度現金流 | 累積現金流 | 年末現金價值
    col_w = [doc.width * 0.12, doc.width * 0.29, doc.width * 0.29, doc.width * 0.30]
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa0a6")),
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, colors.HexColor("#9aa0a6")),
        ("LINEBEFORE", (2, 0), (2, -1), 0.5, colors.HexColor("#9aa0a6")),
        ("LINEBEFORE", (3, 0), (3, -1), 0.5, colors.HexColor("#9aa0a6")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(tbl)

    doc.build(flow)
    return buf.getvalue()

# ----------------------------- Page -----------------------------
def render():
    st.subheader("📦 保單策略規劃（會談示意）")
    st.caption("此頁以 IRR 近似估算現金價值與年度現金流，方便會談討論；正式方案請以商品條款與保險公司試算為準。")
    st.warning("【重要提醒】以下數字為 **AI 依您輸入參數的示意模擬**，僅供教育與討論；不構成任何投資/保險建議或保證值。最終以保險公司官方試算與契約為準。")

    # 基本參數（年期預設 6；模擬總年數固定 20）
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        currency = st.selectbox("幣別", ["TWD", "USD"], index=0)
    with c2:
        premium = st.number_input("年繳保費（元）", min_value=100_000, step=10_000, value=500_000)
    with c3:
        years = st.number_input("繳費年期（年）", min_value=1, max_value=30, value=6, step=1)
    with c4:
        goal = st.selectbox("策略目標", ["放大財富傳承", "補足遺產稅", "退休現金流", "企業風險隔離"], index=0)

    stance = st.radio("倍數策略強度", ["保守", "中性", "積極"], index=0, horizontal=True)
    irr = st.slider("示意 IRR（不代表商品保證）", 1.0, 6.0, 3.0, 0.1)
    horizon = st.number_input("現金價值觀察年（示意）", min_value=5, max_value=40, value=10)
    SIM_YEARS_FIXED = 20

    # PDF 設定（選填）：Logo 路徑
    with st.expander("PDF 設定（選填）", expanded=False):
        st.caption("PDF 將置頂顯示 Logo；若留空或找不到檔案會自動略過。")
        default_logo = st.session_state.get("pdf_logo_path", "assets/logo.png")
        logo_path = st.text_input("Logo 檔案路徑", value=default_logo, key="pdf_logo_path")

    # 摘要（Markdown 安全字串）
    total_premium = _safe_int(premium) * _safe_int(years)
    face_mult = FACE_MULTIPLIERS[stance][goal]
    indicative_face = _safe_int(total_premium * face_mult)
    cv_h = _estimate_cash_value(_safe_float(premium), _safe_int(years), _safe_float(irr), _safe_int(horizon))
    cur_zh = _currency_name(currency)

    st.markdown("#### 摘要")
    st.markdown(
        f"- 年繳保費 × 年期（幣別：{cur_zh}）："
        f"**{_fmt_currency_md(premium, currency)}** × **{int(years)}** ＝ 總保費 **{_fmt_currency_md(total_premium, currency)}**"
    )
    st.markdown(
        f"- 估計身故保額（倍數示意）：**{_fmt_currency_md(indicative_face, currency)}**"
        f"（使用倍數 **{face_mult}×**｜{stance}）"
    )
    st.markdown(
        f"- 第 **{int(horizon)}** 年估計現金價值（IRR **{irr:.1f}%**）：**{_fmt_currency_md(cv_h, currency)}**"
    )

    st.markdown("---")

    # 設定現金流入（可選，含一鍵情境）
    with st.expander("設定現金流入（可選）", expanded=(goal == "退休現金流")):
        ss = st.session_state
        ss.setdefault("pol_inflow_enabled", goal == "退休現金流")
        ss.setdefault("pol_mode", "固定年領金額")
        ss.setdefault("pol_start_year", int(years) + 1)
        ss.setdefault("pol_years_in", max(1, 20 - int(years)))
        ss.setdefault("pol_inflow_amt", 300_000)
        ss.setdefault("pol_inflow_ratio", 2.0)

        c0a, c0b, _ = st.columns([1.3, 1.6, 3])
        with c0a:
            if st.button("一鍵：退休年領（保守）", use_container_width=True):
                ss.update(pol_inflow_enabled=True, pol_mode="固定年領金額",
                          pol_start_year=int(years) + 1, pol_years_in=20, pol_inflow_amt=300_000)
        with c0b:
            if st.button("一鍵：比例提領 2%（保守）", use_container_width=True):
                ss.update(pol_inflow_enabled=True, pol_mode="以現金價值比例提領",
                          pol_start_year=int(years) + 1, pol_years_in=20, pol_inflow_ratio=2.0)

        inflow_enabled = st.checkbox("加入正現金流（退休提領／配息／部分解約等示意）", key="pol_inflow_enabled")
        mode_label = st.radio("提領模式", ["固定年領金額", "以現金價值比例提領"],
                              key="pol_mode", horizontal=True, disabled=not inflow_enabled)
        st.number_input("起領年份（第幾年開始）", min_value=1, max_value=60, step=1,
                        key="pol_start_year", disabled=not inflow_enabled)
        st.number_input("領取年數", min_value=1, max_value=60, step=1,
                        key="pol_years_in", disabled=not inflow_enabled)
        if mode_label == "固定年領金額":
            st.number_input("年領金額（元）", min_value=0, step=10_000,
                            key="pol_inflow_amt", disabled=not inflow_enabled)
        else:
            st.slider("每年提領比例（%／以現金價值計）", 0.5, 6.0,
                      key="pol_inflow_ratio", disabled=not inflow_enabled)

    # 模擬（固定 20 年）
    ss = st.session_state
    inflow_mode = "fixed" if ss.get("pol_mode", "固定年領金額") == "固定年領金額" else "ratio"
    sim = _simulate_path(
        premium=_safe_float(premium, 0.0),
        years=max(1, _safe_int(years, 1)),
        irr_pct=_safe_float(irr, 0.0),
        inflow_enabled=bool(ss.get("pol_inflow_enabled", goal == "退休現金流")),
        inflow_mode=inflow_mode,
        start_year=max(1, _safe_int(ss.get("pol_start_year", int(years) + 1), 1)),
        years_in=max(0, _safe_int(ss.get("pol_years_in", max(1, 20 - int(years))), 0)),
        inflow_amt=max(0.0, _safe_float(ss.get("pol_inflow_amt", 300_000), 0.0)),
        inflow_ratio_pct=max(0.0, _safe_float(ss.get("pol_inflow_ratio", 2.0), 0.0)),
        sim_years=SIM_YEARS_FIXED,
    )

    if all(v == 0 for v in sim["annual_cf"]):
        st.info("目前年度現金流全為 0：請確認「繳費年期 > 0」且（固定年領金額 > 0 或 提領比例 > 0）。")
    if sim["clamped_years"]:
        yrs = ", ".join(str(y) for y in sim["clamped_years"][:5])
        more = "…" if len(sim["clamped_years"]) > 5 else ""
        st.warning(f"已啟用防穿透：在第 {yrs}{more} 年自動降額提領以避免現金價值歸零。")
    breakeven = next((y for y, v in zip(sim["timeline"], sim["cum_cf"]) if v >= 0), None)
    if breakeven:
        st.success(f"損益平衡年約為 **第 {breakeven} 年**（累積現金流轉正）。")

    # 頁面表格
    st.markdown("#### 現金價值與現金流（示意）")
    rows = []
    for y, cv, v, acc in zip(sim["timeline"], sim["cv"], sim["annual_cf"], sim["cum_cf"]):
        rows.append({
            "年度": y,
            "當年度現金流": _fmt_currency(v, currency),
            "累積現金流": _fmt_currency(acc, currency),
            "年末現金價值": _fmt_currency(cv, currency),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # ---------------- PDF 下載：優先用 ReportLab（Logo + 表格），否則退回簡易版 ----------------
    try:
        headers = ["年度", "當年度現金流", "累積現金流", "年末現金價值"]
        table_rows = [
            [str(y), _fmt_currency(v, currency), _fmt_currency(acc, currency), _fmt_currency(cv, currency)]
            for y, v, acc, cv in zip(sim["timeline"], sim["annual_cf"], sim["cum_cf"], sim["cv"])
        ]

        if REPORTLAB_AVAILABLE:
            summary_lines = [
                f"年繳保費 × 年期（幣別：{cur_zh}）：{_fmt_currency(premium, currency)} × {int(years)} ＝ 總保費 {_fmt_currency(total_premium, currency)}",
                f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}（使用倍數 {face_mult}×｜{stance}）",
                f"第 {int(horizon)} 年估計現金價值（IRR {irr:.1f}%）：{_fmt_currency(cv_h, currency)}",
            ]
            pdf = _build_pdf_reportlab(
                title_text="保單策略（示意）",
                summary_lines=summary_lines,
                table_headers=headers,
                table_rows=table_rows,
                logo_path=logo_path,
            )
        elif LEGACY_PDF_AVAILABLE:
            # 備援：文字表格
            # 動態等寬表格
            widths = [len(h) for h in headers]
            for r in table_rows:
                for i, cell in enumerate(r):
                    widths[i] = max(widths[i], len(cell))
            def _fmt_row(arr): return " | ".join(str(arr[i]).ljust(widths[i]) for i in range(len(arr)))
            sep = " | ".join("─" * w for w in widths)

            flow = [
                title("保單策略（示意）"),
                p("【重要提醒】本檔所有數字為 AI 根據輸入參數之示意模擬，僅供教育與討論，不構成任何投資/保險建議或保證值。"),
                p("正式方案請以保險公司官方試算與契約條款為準。"),
                spacer(4),
                h2("摘要"),
                p(f"年繳保費 × 年期（幣別：{cur_zh}）：{_fmt_currency(premium, currency)} × {int(years)} ＝ 總保費 {_fmt_currency(total_premium, currency)}"),
                p(f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}（使用倍數 {face_mult}×｜{stance}）"),
                p(f"第 {int(horizon)} 年估計現金價值（IRR {irr:.1f}%）：{_fmt_currency(cv_h, currency)}"),
                spacer(6),
                h2("現金價值與現金流（示意）"),
                p(_fmt_row(headers)),
                p(sep),
            ]
            for r in table_rows:
                flow.append(p(_fmt_row(r)))
            pdf = build_branded_pdf_bytes(flow)
        else:
            pdf = b""

        if pdf:
            st.download_button(
                "⬇️ 下載保單策略 PDF",
                data=pdf,
                file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("目前環境無法產生 PDF（缺少 ReportLab 與內建 PDF 工具）。")
    except Exception:
        st.info("建立 PDF 時發生例外，但不影響頁面使用。若需要我幫你排查，請貼出錯訊。")

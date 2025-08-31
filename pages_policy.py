# pages_policy.py
import streamlit as st
from datetime import datetime
from typing import List, Dict

# 若你的專案已有品牌化 PDF 工具，沿用此匯入；沒有則可先註解相關段落
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer  # noqa: F401

# ------------------------------------------------
# 工具函式
# ------------------------------------------------
def _wan(n: float | int) -> int:
    """四捨五入換算成萬元的整數（TWD常用顯示單位）"""
    try:
        return int(round(float(n) / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: float | int) -> str:
    """格式化為「#,### 萬元」"""
    try:
        return f"{_wan(n):,} 萬元"
    except Exception:
        return "—"

def _fmt_currency(n: float | int, currency: str) -> str:
    """格式化為帶幣別字首：NT$ / US$"""
    try:
        sym = "NT$" if currency == "TWD" else "US$"
        return f"{sym}{float(n):,.0f}"
    except Exception:
        return "—"

def _estimate_cash_value(premium: int, years: int, irr_pct: float, horizon: int) -> int:
    """
    以 IRR 作為年化報酬率，粗估 horizon 年的「示意現金值」。
    假設每年年末投入 premium，投入年數 = min(years, horizon)。
    注意：這是會談用的近似示意，非商品精算。
    """
    irr = max(0.0, float(irr_pct) / 100.0)
    horizon = max(1, int(horizon))
    terms = min(int(years), horizon)
    fv = 0.0
    for t in range(1, terms + 1):
        fv += premium * (1.0 + irr) ** (horizon - t)
    return int(round(fv))

def _build_cashflow_table(
    currency: str,
    premium: int,
    years: int,
    irr: float,
    inflow_enabled: bool,
    inflow_mode: str,          # "fixed" or "ratio"
    start_year: int,
    years_in: int,
    inflow_amt: int | None,
    inflow_ratio_pct: float | None,
) -> Dict[str, List]:
    """
    建立年度現金流（含支出與可選的流入），回傳用於顯示與PDF的結構。
    """
    # 決定時間軸長度
    last_year = years
    if inflow_enabled:
        last_year = max(years, start_year + years_in - 1)
    timeline = list(range(1, last_year + 1))

    # 先放入「保費支出」（負號）
    cash_flow = [0 for _ in timeline]
    for y in range(1, years + 1):
        cash_flow[y - 1] -= int(premium)

    # 加入「現金流入」
    if inflow_enabled:
        for y in range(start_year, start_year + years_in):
            if 1 <= y <= last_year:
                if inflow_mode == "fixed" and inflow_amt:
                    cash_flow[y - 1] += int(inflow_amt)
                elif inflow_mode == "ratio" and inflow_ratio_pct:
                    cv_y = _estimate_cash_value(int(premium), int(years), float(irr), int(y))
                    cash_flow[y - 1] += int(round(cv_y * (float(inflow_ratio_pct) / 100.0)))

    # 累計現金流
    cum = []
    run = 0
    for v in cash_flow:
        run += v
        cum.append(run)

    # 建表（依幣別決定顯示格式）
    rows = []
    is_twd = (currency == "TWD")
    for idx, y in enumerate(timeline):
        out = cash_flow[idx]
        acc = cum[idx]
        rows.append({
            "年度": y,
            "當年度現金流": _fmt_wan(out) if is_twd else _fmt_currency(out, currency),
            "累計現金流": _fmt_wan(acc) if is_twd else _fmt_currency(acc, currency),
        })

    return {
        "timeline": timeline,
        "cash_flow": cash_flow,
        "cum": cum,
        "rows": rows,
    }

# ------------------------------------------------
# 主渲染函式（供 app.py 或路由呼叫）
# ------------------------------------------------
def render():
    st.subheader("📦 保單策略規劃（會談示意）")
    st.caption("說明：本頁以 IRR 近似估算現金值與年度現金流，方便會談引導；正式方案請以商品條款與保險公司試算為準。")

    # ✅ 額外醒目提醒（AI 模擬）
    st.warning(
        "本頁所有數字為 **AI 依您輸入參數的示意模擬**，僅供教育與討論，不構成任何投資/保險建議或保證值；"
        "最終資料以保險公司官方試算與契約為準。"
    )

    # ---- 基本參數 ----
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        currency = st.selectbox("幣別", ["TWD", "USD"], index=0)
    with c2:
        premium = st.number_input("年繳保費（元）", min_value=100_000, step=10_000, value=500_000)
    with c3:
        years   = st.number_input("繳費年期（年）", min_value=1, max_value=30, value=10, step=1)
    with c4:
        goal = st.selectbox("策略目標", ["放大財富傳承","補足遺產稅","退休現金流","企業風險隔離"], index=0)

    c5, c6 = st.columns(2)
    with c5:
        irr = st.slider("示意 IRR（不代表商品保證）", 1.0, 6.0, 3.0, 0.1)
    with c6:
        horizon = st.number_input("現金值觀察年（示意）", min_value=5, max_value=40, value=10)

    # ---- 摘要 ----
    total_premium = int(premium) * int(years)
    face_mult = {"放大財富傳承": 18, "補足遺產稅": 14, "退休現金流": 10, "企業風險隔離": 12}[goal]
    indicative_face = int(total_premium * face_mult)
    cv_h = _estimate_cash_value(int(premium), int(years), float(irr), int(horizon))
    is_twd = (currency == "TWD")

    st.markdown("#### 摘要")
    if is_twd:
        st.write(f"- 年繳保費 × 年期：{_fmt_wan(premium)} × {int(years)} ＝ **總保費 {_fmt_wan(total_premium)}**")
        st.write(f"- 估計身故保額（倍數示意）：**{_fmt_wan(indicative_face)}**")
        st.write(f"- 第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：**{_fmt_wan(cv_h)}**")
    else:
        st.write(f"- 年繳保費 × 年期：{_fmt_currency(premium, currency)} × {int(years)} ＝ **總保費 {_fmt_currency(total_premium, currency)}**")
        st.write(f"- 估計身故保額（倍數示意）：**{_fmt_currency(indicative_face, currency)}**")
        st.write(f"- 第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：**{_fmt_currency(cv_h, currency)}**")

    st.markdown("---")

    # ---- 年度現金流（支援正現金流）----
    st.markdown("#### 年度現金流（示意）")
    with st.expander("設定現金流入（可選）", expanded=(goal == "退休現金流")):
        inflow_enabled = st.checkbox("加入正現金流（退休提領／配息／部分解約等示意）", value=(goal == "退休現金流"))
        mode_label = st.radio("提領模式", ["固定年領金額", "以現金值比例提領"], index=0, horizontal=True, disabled=not inflow_enabled)
        inflow_mode = "fixed" if mode_label == "固定年領金額" else "ratio"

        c7, c8, c9 = st.columns(3)
        with c7:
            start_year = st.number_input("起領年份（第幾年開始）", min_value=1, max_value=60, value=int(years) + 1, step=1, disabled=not inflow_enabled)
        with c8:
            years_in = st.number_input("領取年數", min_value=1, max_value=60, value=max(1, 20 - int(years)), step=1, disabled=not inflow_enabled)
        with c9:
            if inflow_mode == "fixed":
                inflow_amt = st.number_input("年領金額（元）", min_value=0, step=10_000, value=300_000, disabled=not inflow_enabled)
                inflow_ratio_pct = None
            else:
                inflow_ratio_pct = st.slider("每年提領比例（%／以示意現金值計）", 0.5, 6.0, 2.0, 0.1, disabled=not inflow_enabled)
                inflow_amt = None

    table = _build_cashflow_table(
        currency=currency,
        premium=int(premium),
        years=int(years),
        irr=float(irr),
        inflow_enabled=bool(inflow_enabled),
        inflow_mode=inflow_mode,
        start_year=int(start_year),
        years_in=int(years_in),
        inflow_amt=int(inflow_amt) if inflow_mode == "fixed" and inflow_enabled else None,
        inflow_ratio_pct=float(inflow_ratio_pct) if inflow_mode == "ratio" and inflow_enabled else None,
    )

    st.dataframe(table["rows"], use_container_width=True, hide_index=True)

    # ---- 下載 PDF（可選；若沒有 utils.pdf_utils 可註解以下區塊）----
    try:
        flow = [
            title("保單策略（示意）"),
            p("【重要提醒】本頁所有數字為 AI 根據輸入參數之示意模擬，僅供教育與討論，不構成任何投資/保險建議或保證值。"),
            p("正式方案請以保險公司官方試算與契約條款為準。"),
            spacer(4),
            h2("摘要"),
        ]
        if is_twd:
            flow.extend([
                p(f"年繳保費 × 年期：{_fmt_wan(premium)} × {int(years)} ＝ 總保費 {_fmt_wan(total_premium)}"),
                p(f"估計身故保額（倍數示意）：{_fmt_wan(indicative_face)}"),
                p(f"第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：{_fmt_wan(cv_h)}"),
            ])
        else:
            flow.extend([
                p(f"年繳保費 × 年期：{_fmt_currency(premium, currency)} × {int(years)} ＝ 總保費 {_fmt_currency(total_premium, currency)}"),
                p(f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}"),
                p(f"第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：{_fmt_currency(cv_h, currency)}"),
            ])

        flow.append(spacer(6))
        flow.append(h2("年度現金流（示意）"))
        for y, v, acc in zip(table["timeline"], table["cash_flow"], table["cum"]):
            if is_twd:
                flow.append(p(f"第 {y} 年：{_fmt_wan(v)}（累計 {_fmt_wan(acc)}）"))
            else:
                flow.append(p(f"第 {y} 年：{_fmt_currency(v, currency)}（累計 {_fmt_currency(acc, currency)}）"))

        pdf = build_branded_pdf_bytes(flow)
        st.download_button(
            "⬇️ 下載保單策略 PDF",
            data=pdf,
            file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception:
        # 若無 PDF 工具或拋錯，靜默忽略下載區塊，避免影響頁面操作
        pass

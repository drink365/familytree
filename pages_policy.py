# pages_policy.py
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# PDF 工具（若專案無此模組，將自動略過下載功能）
try:
    from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer  # type: ignore
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

# ----------------------------- Helpers -----------------------------
def _wan(n: float) -> int:
    """四捨五入換算成萬元的整數（TWD 常用顯示單位）"""
    try:
        return int(round(float(n) / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: float) -> str:
    """格式化為「#,### 萬元」"""
    try:
        return f"{_wan(n):,} 萬元"
    except Exception:
        return "—"

def _fmt_currency(n: float, currency: str) -> str:
    """格式化為帶幣別：NT$ / US$"""
    try:
        sym = "NT$" if currency == "TWD" else "US$"
        return f"{sym}{float(n):,.0f}"
    except Exception:
        return "—"

def _estimate_cash_value(premium: float, years: int, irr_pct: float, horizon: int) -> int:
    """
    以 IRR 為年化報酬率，估算第 horizon 年的「示意現金值」。
    假設每年年末投入 premium，投入年數 = min(years, horizon)。（僅供會談示意，非商品精算）
    """
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

def _build_cashflow_table(
    currency: str,
    premium: float,
    years: int,
    irr: float,
    inflow_enabled: bool,
    inflow_mode: str,                 # "fixed" or "ratio"
    start_year: int,
    years_in: int,
    inflow_amt: Optional[float],
    inflow_ratio_pct: Optional[float],
) -> Dict[str, List]:
    """
    產生年度現金流表（含支出與可選的流入）。
    回傳：timeline / cash_flow / cum / rows
    """
    # --- 安全轉型 ---
    premium_i = _safe_float(premium, 0.0)
    years_i = _safe_int(years, 0)
    start_year_i = _safe_int(start_year, 0)
    years_in_i = _safe_int(years_in, 0)
    inflow_amt_f = _safe_float(inflow_amt, 0.0)
    inflow_ratio_f = _safe_float(inflow_ratio_pct, 0.0)
    irr_f = _safe_float(irr, 0.0)

    # 時間軸需涵蓋繳費與提領區間
    last_year = years_i
    if inflow_enabled:
        last_year = max(years_i, start_year_i + years_in_i - 1)
    last_year = max(1, last_year)  # 至少顯示一年
    timeline = list(range(1, last_year + 1))

    # 保費支出（負號）
    cash_flow = [0 for _ in timeline]
    for y in range(1, years_i + 1):
        cash_flow[y - 1] -= int(round(premium_i))

    # 流入（固定金額或比例）
    if inflow_enabled and years_in_i > 0:
        for y in range(start_year_i, start_year_i + years_in_i):
            if 1 <= y <= last_year:
                if inflow_mode == "fixed" and inflow_amt_f > 0:
                    cash_flow[y - 1] += int(round(inflow_amt_f))
                elif inflow_mode == "ratio" and inflow_ratio_f > 0:
                    cv_y = _estimate_cash_value(premium_i, years_i, irr_f, y)
                    cash_flow[y - 1] += int(round(cv_y * (inflow_ratio_f / 100.0)))

    # 累計
    cum = []
    run = 0
    for v in cash_flow:
        run += v
        cum.append(run)

    # 顯示列
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

    return {"timeline": timeline, "cash_flow": cash_flow, "cum": cum, "rows": rows}

# ----------------------------- 倍數設定（已減半，與年齡無關） -----------------------------
FACE_MULTIPLIERS = {
    "保守": {"放大財富傳承": 5, "補足遺產稅": 4, "退休現金流": 3, "企業風險隔離": 4},
    "中性": {"放大財富傳承": 6, "補足遺產稅": 5, "退休現金流": 4, "企業風險隔離": 5},
    "積極": {"放大財富傳承": 7, "補足遺產稅": 6, "退休現金流": 5, "企業風險隔離": 6},
}

# ----------------------------- Page -----------------------------
def render():
    st.subheader("📦 保單策略規劃（會談示意）")
    st.caption("此頁以 IRR 近似估算現金值與年度現金流，方便會談討論；正式方案請以商品條款與保險公司試算為準。")
    st.warning(
        "【重要提醒】以下數字為 **AI 依您輸入參數的示意模擬**，僅供教育與討論；"
        "不構成任何投資/保險建議或保證值。最終以保險公司官方試算與契約為準。"
    )

    # 基本參數
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        currency = st.selectbox("幣別", ["TWD", "USD"], index=0)
    with c2:
        premium = st.number_input("年繳保費（元）", min_value=100_000, step=10_000, value=500_000)
    with c3:
        years   = st.number_input("繳費年期（年）", min_value=1, max_value=30, value=10, step=1)
    with c4:
        goal = st.selectbox("策略目標", ["放大財富傳承","補足遺產稅","退休現金流","企業風險隔離"], index=0)

    stance = st.radio("倍數策略強度", ["保守","中性","積極"], index=0, horizontal=True)

    c5, c6 = st.columns(2)
    with c5:
        irr = st.slider("示意 IRR（不代表商品保證）", 1.0, 6.0, 3.0, 0.1)
    with c6:
        horizon = st.number_input("現金值觀察年（示意）", min_value=5, max_value=40, value=10)

    # 摘要（倍數僅依策略強度決定）
    total_premium = _safe_int(premium) * _safe_int(years)
    face_mult = FACE_MULTIPLIERS[stance][goal]
    indicative_face = _safe_int(total_premium * face_mult)
    cv_h = _estimate_cash_value(_safe_float(premium), _safe_int(years), _safe_float(irr), _safe_int(horizon))
    is_twd = (currency == "TWD")

    st.markdown("#### 摘要")
    if is_twd:
        st.write(f"- 年繳保費 × 年期：{_fmt_wan(premium)} × {int(years)} ＝ **總保費 {_fmt_wan(total_premium)}**")
        st.write(f"- 估計身故保額（倍數示意）：**{_fmt_wan(indicative_face)}**（使用倍數 **{face_mult}×**｜{stance}）")
        st.write(f"- 第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：**{_fmt_wan(cv_h)}**")
    else:
        st.write(f"- 年繳保費 × 年期：{_fmt_currency(premium, currency)} × {int(years)} ＝ **總保費 {_fmt_currency(total_premium, currency)}**")
        st.write(f"- 估計身故保額（倍數示意）：**{_fmt_currency(indicative_face, currency)}**（使用倍數 **{face_mult}×**｜{stance}）")
        st.write(f"- 第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：**{_fmt_currency(cv_h, currency)}**")

    st.markdown("---")

    # 年度現金流（含正流入）
    st.markdown("#### 年度現金流（示意）")
    with st.expander("設定現金流入（可選）", expanded=(goal == "退休現金流")):
        inflow_enabled = st.checkbox("加入正現金流（退休提領／配息／部分解約等示意）", value=(goal == "退休現金流"))

        # radio -> 'fixed' / 'ratio'
        mode_label = st.radio("提領模式", ["固定年領金額", "以現金值比例提領"],
                              index=0, horizontal=True, disabled=not inflow_enabled)
        inflow_mode = "fixed" if mode_label == "固定年領金額" else "ratio"

        c7, c8, c9 = st.columns(3)
        with c7:
            start_year = st.number_input("起領年份（第幾年開始）", min_value=1, max_value=60,
                                         value=int(years) + 1, step=1, disabled=not inflow_enabled)
        with c8:
            years_in = st.number_input("領取年數", min_value=1, max_value=60,
                                       value=max(1, 20 - int(years)), step=1, disabled=not inflow_enabled)
        with c9:
            # ✅ 正確依 inflow_mode 顯示對應欄位（修正 bug）
            if inflow_mode == "fixed":
                inflow_amt = st.number_input("年領金額（元）", min_value=0, step=10_000,
                                             value=300_000, disabled=not inflow_enabled)
                inflow_ratio_pct = 0.0
            else:
                inflow_ratio_pct = st.slider("每年提領比例（%／以示意現金值計）",
                                             0.5, 6.0, 2.0, 0.1, disabled=not inflow_enabled)
                inflow_amt = 0.0

    # 計算表格
    table = _build_cashflow_table(
        currency=currency,
        premium=premium,
        years=int(years),
        irr=irr,
        inflow_enabled=bool(inflow_enabled),
        inflow_mode=inflow_mode,
        start_year=int(start_year),
        years_in=int(years_in),
        inflow_amt=inflow_amt,
        inflow_ratio_pct=inflow_ratio_pct,
    )

    # 自動找出第一筆正現金流
    first_positive = next((y for y, v in zip(table["timeline"], table["cash_flow"]) if v > 0), None)

    # 提示狀態
    if inflow_enabled:
        if (inflow_mode == "fixed" and _safe_float(inflow_amt) <= 0) or \
           (inflow_mode == "ratio" and _safe_float(inflow_ratio_pct) <= 0):
            st.info("尚未看到正現金流：因年領金額為 0 或提領比例為 0%。請調整數值。")
        elif first_positive is None:
            st.info("目前參數下沒有出現正現金流（可能是起領年份超出範圍或提領金額過低）。")
        else:
            st.success(f"第一筆正現金流出現在 **第 {first_positive} 年**。")

    # 先顯示「重點區段」，再顯示完整表
    if inflow_enabled and first_positive:
        start_focus = max(1, first_positive - 1)
        end_focus = min(table["timeline"][-1], first_positive + max(4, _safe_int(years_in) - 1))
        focus_rows = [r for r in table["rows"] if start_focus <= r["年度"] <= end_focus]
        st.markdown(f"**重點區段：第 {start_focus}～{end_focus} 年（含第一筆正現金流）**")
        st.dataframe(focus_rows, use_container_width=True, hide_index=True)

    st.markdown("**完整年度現金流**")
    st.dataframe(table["rows"], use_container_width=True, hide_index=True)

    # 下載 PDF（若可用）
    if PDF_AVAILABLE:
        try:
            flow = [
                title("保單策略（示意）"),
                p("【重要提醒】本檔所有數字為 AI 根據輸入參數之示意模擬，僅供教育與討論，不構成任何投資/保險建議或保證值。"),
                p("正式方案請以保險公司官方試算與契約條款為準。"),
                spacer(4),
                h2("摘要"),
            ]
            if is_twd:
                flow.extend([
                    p(f"年繳保費 × 年期：{_fmt_wan(premium)} × {int(years)} ＝ 總保費 {_fmt_wan(total_premium)}"),
                    p(f"估計身故保額（倍數示意）：{_fmt_wan(indicative_face)}（使用倍數 {face_mult}×｜{stance}）"),
                    p(f"第 {int(horizon)} 年估計現金值（IRR {irr:.1f}%）：{_fmt_wan(cv_h)}"),
                ])
            else:
                flow.extend([
                    p(f"年繳保費 × 年期：{_fmt_currency(premium, currency)} × {int(years)} ＝ 總保費 {_fmt_currency(total_premium, currency)}"),
                    p(f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}（使用倍數 {face_mult}×｜{stance}）"),
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
            pass

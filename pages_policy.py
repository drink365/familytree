import math
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer

# ----------------------------- Helpers -----------------------------

def _wan(n: float | int) -> int:
    "四捨五入換算成萬元的整數"
    try:
        return int(round(float(n) / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: float | int) -> str:
    "格式化為「#,### 萬元」"
    return f"{_wan(n):,} 萬元"

def _fmt_currency(n: float | int, currency: str) -> str:
    "非 TWD 情況下的簡單格式器"
    try:
        return f"{int(n):,} {currency}"
    except Exception:
        return f"{n} {currency}"

# 估算：以 IRR 為年化報酬率，計算第 N 年現金值（極簡示意，不代表實際保單）
def _estimate_cash_value(premium: int, years: int, irr_pct: float, horizon: int) -> int:
    irr = irr_pct / 100.0
    # 把每年的保費視為年末投入，估算在 horizon 年時的價值（示意）。
    # FV = Σ premium * (1+irr)^(horizon - t), t=1..min(years, horizon)
    horizon = max(1, int(horizon))
    terms = min(years, horizon)
    fv = 0.0
    for t in range(1, terms + 1):
        fv += premium * (1.0 + irr) ** (horizon - t)
    return int(round(fv))

# ----------------------------- Page -----------------------------

def render():
    st.subheader("📦 保單策略模擬（萬元）")

    c1, c2 = st.columns(2)
    with c1:
        # 輸入仍以「元」為單位，以避免既有資料斷裂；所有顯示統一轉為「萬元」
        premium = st.number_input("年繳保費（元）", min_value=0, value=1_000_000, step=50_000)
        years   = st.selectbox("繳費期間（年）", [6, 7, 10, 12, 20], index=0)
        currency= st.selectbox("幣別", ["TWD","USD"], index=0)
    with c2:
        goal    = st.selectbox("策略目標", ["放大財富傳承", "補足遺產稅", "退休現金流", "企業風險隔離"], index=0)
        irr     = st.slider("假設內部報酬率 IRR（示意）", 1.0, 6.0, 3.0, 0.1)

    is_twd = (currency == "TWD")
    years_range = list(range(1, years + 1))

    # 總保費
    total_premium = premium * years

    # 示意保額倍數（僅用於說明，非實際產品承諾）
    face_mult = {"放大財富傳承": 18, "補足遺產稅": 14, "退休現金流": 10, "企業風險隔離": 12}[goal]
    indicative_face = int(total_premium * face_mult)

    # 假設第 10 年現金值（若年期不足 10 年，就以實際年期）
    horizon = 10
    cv_10y = _estimate_cash_value(premium, years, irr, horizon)

    # 年度現金流（保費支出視為負值的現金流）
    cash_out = [-premium for _ in years_range]
    cum_out  = []
    running = 0
    for v in cash_out:
        running += v
        cum_out.append(running)

    # ----------------------------- 顯示（統一萬為單位 for TWD） -----------------------------
    st.markdown("#### 摘要")
    if is_twd:
        st.write("年繳保費 × 年期：", _fmt_wan(premium), "×", years, "＝ 總保費", _fmt_wan(total_premium))
        st.write("估計身故保額（倍數示意）：", _fmt_wan(indicative_face))
        st.write(f"{horizon} 年估計現金值（IRR {irr:.1f}%）：", _fmt_wan(cv_10y))
    else:
        st.write("年繳保費 × 年期：", _fmt_currency(premium, currency), "×", years, "＝ 總保費", _fmt_currency(total_premium, currency))
        st.write("估計身故保額（倍數示意）：", _fmt_currency(indicative_face, currency))
        st.write(f"{horizon} 年估計現金值（IRR {irr:.1f}%）：", _fmt_currency(cv_10y, currency))

    st.markdown("#### 年度現金流")
    if is_twd:
        table_rows = [{ "年度": y, "保費現金流": _fmt_wan(cash_out[y-1]), "累計現金流": _fmt_wan(cum_out[y-1]) } for y in years_range]
    else:
        table_rows = [{ "年度": y, "保費現金流": _fmt_currency(cash_out[y-1], currency), "累計現金流": _fmt_currency(cum_out[y-1], currency) } for y in years_range]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # ----------------------------- PDF 匯出 -----------------------------
    flow = [
        title("保單策略摘要"), spacer(6),
        p("策略目標：" + goal),
        p((f"年繳保費 × 年期：{_fmt_wan(premium)} × {years} ＝ 總保費 {_fmt_wan(total_premium)}") if is_twd else f"年繳保費 × 年期：{_fmt_currency(premium, currency)} × {years} ＝ 總保費 {_fmt_currency(total_premium, currency)}"),
        p((f"估計身故保額（倍數示意）：{_fmt_wan(indicative_face)}") if is_twd else f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}"),
        p((f"{horizon} 年估計現金值（IRR {irr:.1f}%）：{_fmt_wan(cv_10y)}") if is_twd else f"{horizon} 年估計現金值（IRR {irr:.1f}%）：{_fmt_currency(cv_10y, currency)}"),
        spacer(6), h2("年度現金流")
    ]
    for y in years_range:
        if is_twd:
            flow.append(p(f"第 {y} 年：{_fmt_wan(cash_out[y-1])}（累計 {_fmt_wan(cum_out[y-1])}）"))
        else:
            flow.append(p(f"第 {y} 年：{_fmt_currency(cash_out[y-1], currency)}（累計 {_fmt_currency(cum_out[y-1], currency)}）"))

    pdf = build_branded_pdf_bytes(flow)
    st.download_button(
        "⬇️ 下載保單策略 PDF",
        data=pdf,
        file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
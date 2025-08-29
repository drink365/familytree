
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer

def _wan(n: int | float) -> int:
    try:
        return int(round(n / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: int | float) -> str:
    return f"{_wan(n):,} 萬元"

def _fmt_wan_signed(n: int | float) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}{_wan(abs(n)):,} 萬元"

def render():
    st.subheader("📦 保單策略模擬（萬元）")

    c1, c2 = st.columns(2)
    with c1:
        premium_wan = st.number_input("年繳保費（單位：萬元）", min_value=0, value=100, step=5)
        years       = st.selectbox("繳費期間（年）", [6,7,10,12,20], index=0)
        currency    = st.selectbox("幣別", ["TWD","USD"], index=0)
        premium     = premium_wan * 10000  # 換回元計算
    with c2:
        goal        = st.selectbox("策略目標", ["放大財富傳承","補足遺產稅","退休現金流","企業風險隔離"], index=0)
        irr         = st.slider("假設內部報酬率 IRR（示意）", 1.0, 6.0, 3.0, 0.1)

    total_premium = premium * years
    is_twd = (currency == 'TWD')
    face_mult = {"放大財富傳承":18, "補足遺產稅":14, "退休現金流":10, "企業風險隔離":12}[goal]
    indicative_face = int(total_premium * face_mult)
    cv_10y = int(total_premium * (1 + irr/100.0)**10)

    st.write({
        "總保費": (_fmt_wan(total_premium) if is_twd else f"{total_premium:,} {currency}"),
        "估計身故保額": (_fmt_wan(indicative_face) if is_twd else f"{indicative_face:,} {currency}"),
        "10 年估計現金值": (_fmt_wan(cv_10y) if is_twd else f"{cv_10y:,} {currency}"),
        "IRR（示意）": f"{irr:.1f}%",
        "策略目標": goal
    })

    years_range = list(range(1, years+1))
    cash_out = [-premium for _ in years_range]
    cum_out  = [sum(cash_out[:i]) for i in range(1, years+1)]
    st.write([{
        "年度": y,
        "保費現金流": (_fmt_wan_signed(cash_out[y-1]) if is_twd else f"{cash_out[y-1]:,}"),
        "累計現金流": (_fmt_wan_signed(cum_out[y-1]) if is_twd else f"{cum_out[y-1]:,}")
    } for y in years_range])

    flow = [
        title("保單策略摘要"), spacer(6),
        p("策略目標：" + goal),
        (p(f"年繳保費 × 年期：{_fmt_wan(premium)} × {years} ＝ 總保費 {_fmt_wan(total_premium)}") if is_twd else p(f"年繳保費 × 年期：{premium:,} × {years} ＝ 總保費 {total_premium:,} {currency}")),
        (p(f"估計身故保額（倍數示意）：{_fmt_wan(indicative_face)}") if is_twd else p(f"估計身故保額（倍數示意）：{indicative_face:,} {currency}")),
        (p(f"10 年估計現金值（IRR {irr:.1f}%）：{_fmt_wan(cv_10y)}") if is_twd else p(f"10 年估計現金值（IRR {irr:.1f}%）：{cv_10y:,} {currency}")),
        spacer(6), h2("年度現金流")
    ] + [ (p(f"第 {y} 年：{_fmt_wan_signed(cash_out[y-1])}（累計 {_fmt_wan_signed(cum_out[y-1])}）") if is_twd else p(f"第 {y} 年：{cash_out[y-1]:,}（累計 {cum_out[y-1]:,}）")) for y in years_range ]

    pdf = build_branded_pdf_bytes(flow)
    st.download_button("⬇️ 下載保單策略 PDF", data=pdf, file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

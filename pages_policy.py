# pages_policy.py
import streamlit as st
from datetime import datetime
from typing import Optional

# PDF：與其他頁一致的品牌工具
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer, table

# ----------------------------- Helpers -----------------------------
def _fmt_currency(n: float, currency: str) -> str:
    """整數四捨五入＋千分位，顯示 NT$/US$（一般用，非 Markdown）"""
    try:
        sym = "NT$" if currency == "TWD" else "US$"
        return f"{sym}{float(round(n)):,.0f}"
    except Exception:
        return "—"

def _fmt_currency_md(n: float, currency: str) -> str:
    """供 Markdown 顯示（將 $ 轉義避免被當 LaTeX）"""
    return _fmt_currency(n, currency).replace("$", "\\$")

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
    """IRR 近似估算第 horizon 年現金價值（年末投入；示意用途）"""
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

# ------------------ 年度模擬（含防穿透） ------------------
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

# ----------------------------- 倍數（已減半） -----------------------------
FACE_MULTIPLIERS = {
    "保守": {"放大財富傳承": 5, "補足遺產稅": 4, "退休現金流": 3, "企業風險隔離": 4},
    "中性": {"放大財富傳承": 6, "補足遺產稅": 5, "退休現金流": 4, "企業風險隔離": 5},
    "積極": {"放大財富傳承": 7, "補足遺產稅": 6, "退休現金流": 5, "企業風險隔離": 6},
}

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

    # 摘要（畫面：幣別中文、數字加粗、$ 轉義）
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
        # 初次預設（避免 default 與 session_state 衝突）
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

    # 頁面表格（年度、當年度現金流、累積現金流、年末現金價值）
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

    # ---------------- PDF（參考你那頁的風格，A→B→fallback） ----------------
    try:
        headers = ["年度", "當年度現金流", "累積現金流", "年末現金價值"]
        table_rows = [
            [str(y), _fmt_currency(v, currency), _fmt_currency(acc, currency), _fmt_currency(cv, currency)]
            for y, v, acc, cv in zip(sim["timeline"], sim["annual_cf"], sim["cum_cf"], sim["cv"])
        ]

        flow = [
            title("保單策略（示意）"),
            p("【重要提醒】本檔所有數字為 AI 根據輸入參數之示意模擬，僅供教育與討論，不構成任何投資/保險建議或保證值。"),
            p("正式方案請以保險公司官方試算與契約條款為準。"),
            spacer(6),
            h2("摘要"),
            p(f"年繳保費 × 年期（幣別：{_currency_name(currency)}）：{_fmt_currency(premium, currency)} × {int(years)} ＝ 總保費 {_fmt_currency(total_premium, currency)}"),
            p(f"估計身故保額（倍數示意）：{_fmt_currency(indicative_face, currency)}（使用倍數 {face_mult}×｜{stance}）"),
            p(f"第 {int(horizon)} 年估計現金價值（IRR {irr:.1f}%）：{_fmt_currency(cv_h, currency)}"),
            spacer(6),
            h2("現金價值與現金流（示意）"),
        ]

        # 方案 A：明確 data + 欄寬（多數版本支援）
        table_node = None
        try:
            table_node = table(data=[headers] + table_rows, widths=[0.12, 0.29, 0.29, 0.30])
        except Exception:
            # 方案 B：位置參數（headers, rows, widths）
            try:
                table_node = table(headers, table_rows, widths=[0.12, 0.29, 0.29, 0.30])
            except Exception:
                table_node = None

        if table_node is not None:
            flow.append(table_node)
        else:
            # 最後備援：文字表格，確保不中斷
            flow.append(p("｜".join(headers)))
            for r in table_rows:
                flow.append(p("｜".join(r)))

        flow.extend([spacer(6), p("產出日期：" + datetime.now().strftime("%Y/%m/%d"))])

        pdf_bytes = build_branded_pdf_bytes(flow)
        st.download_button(
            "⬇️ 下載保單策略 PDF",
            data=pdf_bytes,
            file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"PDF 仍無法建立：{e}")

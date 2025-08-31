# pages_policy.py
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# 圖表資料：pandas 優先，沒有就用 numpy 備援
try:
    import pandas as pd  # type: ignore
    PANDAS_AVAILABLE = True
except Exception:
    import numpy as np  # type: ignore
    PANDAS_AVAILABLE = False

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
    """以 IRR 為年化報酬率，估算第 horizon 年的示意現金值（年末投入；僅會談示意）。"""
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

# ------------------ 動態現金值模擬（含防穿透） ------------------
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
    年度序列模擬：先投入保費 → 依 IRR 成長 → 進行提領；
    若提領超過可用現金值，會自動降額（防穿透）。
    回傳：timeline, cv(年末現金值), annual_cf, cum_cf, clamped_years(list)
    """
    r = max(0.0, _safe_float(irr_pct) / 100.0)
    T = sim_years or max(_safe_int(years), _safe_int(start_year) + _safe_int(years_in) - 1, _safe_int(years) + 10)
    T = max(T, 1)

    cv = 0.0
    cv_series, ann_cf_series, cum_cf_series = [], [], []
    clamped_years = []
    cum = 0.0

    for y in range(1, T + 1):
        # 投入保費（尚在繳費期）
        premium_y = float(premium) if y <= int(years) else 0.0
        cv += premium_y

        # 依 IRR 成長
        cv *= (1.0 + r)

        # 提領（若啟用且在提領區間）
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

        # 當年度現金流（+提領 − 保費）
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
        years = st.number_input("繳費年期（年）", min_value=1, max_value=30, value=10, step=1)
    with c4:
        goal = st.selectbox("策略目標", ["放大財富傳承", "補足遺產稅", "退休現金流", "企業風險隔離"], index=0)

    stance = st.radio("倍數策略強度", ["保守", "中性", "積極"], index=0, horizontal=True)

    c5, c6, c7 = st.columns(3)
    with c5:
        irr = st.slider("示意 IRR（不代表商品保證）", 1.0, 6.0, 3.0, 0.1)
    with c6:
        horizon = st.number_input("現金值觀察年（示意）", min_value=5, max_value=40, value=10)
    with c7:
        sim_years = st.number_input(
            "模擬總年數（圖表）",
            min_value=5, max_value=60,
            value=max(int(years) + 10, int(horizon)),
            help="用於下方動態模擬與折線圖。"
        )

    # 摘要
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

    # ─────────「設定現金流入（可選）」＋ 一鍵情境 ─────────
    with st.expander("設定現金流入（可選）", expanded=(goal == "退休現金流")):
        ss = st.session_state
        # 初始預設（僅第一次）
        ss.setdefault("pol_inflow_enabled", goal == "退休現金流")
        ss.setdefault("pol_mode", "固定年領金額")
        ss.setdefault("pol_start_year", int(years) + 1)
        ss.setdefault("pol_years_in", max(1, 20 - int(years)))
        ss.setdefault("pol_inflow_amt", 300_000)   # 固定年領預設 30 萬
        ss.setdefault("pol_inflow_ratio", 2.0)     # 比例提領預設 2%

        # 一鍵情境
        c0a, c0b, _ = st.columns([1.3, 1.6, 3])
        with c0a:
            if st.button("一鍵：退休年領（保守）", use_container_width=True):
                ss["pol_inflow_enabled"] = True
                ss["pol_mode"] = "固定年領金額"
                ss["pol_start_year"] = int(years) + 1
                ss["pol_years_in"] = 20
                ss["pol_inflow_amt"] = 300_000
        with c0b:
            if st.button("一鍵：比例提領 2%（保守）", use_container_width=True):
                ss["pol_inflow_enabled"] = True
                ss["pol_mode"] = "以現金值比例提領"
                ss["pol_start_year"] = int(years) + 1
                ss["pol_years_in"] = 20
                ss["pol_inflow_ratio"] = 2.0

        # 控制項（綁定 session_state）
        inflow_enabled = st.checkbox(
            "加入正現金流（退休提領／配息／部分解約等示意）",
            value=ss["pol_inflow_enabled"], key="pol_inflow_enabled"
        )
        mode_label = st.radio(
            "提領模式", ["固定年領金額", "以現金值比例提領"],
            key="pol_mode", horizontal=True, disabled=not inflow_enabled
        )
        inflow_mode = "fixed" if mode_label == "固定年領金額" else "ratio"

        c7, c8, c9 = st.columns(3)
        with c7:
            start_year = st.number_input(
                "起領年份（第幾年開始）", min_value=1, max_value=60,
                value=ss["pol_start_year"], step=1,
                key="pol_start_year", disabled=not inflow_enabled
            )
        with c8:
            years_in = st.number_input(
                "領取年數", min_value=1, max_value=60,
                value=ss["pol_years_in"], step=1,
                key="pol_years_in", disabled=not inflow_enabled
            )
        with c9:
            if inflow_mode == "fixed":
                inflow_amt = st.number_input(
                    "年領金額（元）", min_value=0, step=10_000,
                    value=ss["pol_inflow_amt"], key="pol_inflow_amt",
                    disabled=not inflow_enabled
                )
                inflow_ratio_pct = 0.0
            else:
                inflow_ratio_pct = st.slider(
                    "每年提領比例（%／以示意現金值計）",
                    0.5, 6.0, float(ss["pol_inflow_ratio"]),
                    key="pol_inflow_ratio", disabled=not inflow_enabled
                )
                inflow_amt = 0.0

    # ───────── 📈 動態現金值模擬（統一來源 & 安全下限） ─────────
    st.markdown("#### 📈 動態現金值模擬（示意）")
    st.caption("順序：投入保費 → 依 IRR 成長 → 進行提領；若提領超過可用現金值，系統會自動降額（防穿透）。")

    years_safe = max(1, _safe_int(years, 1))
    start_year_safe = max(1, _safe_int(start_year, 1))
    years_in_safe = max(0, _safe_int(years_in, 0))
    inflow_amt_safe = max(0.0, _safe_float(inflow_amt, 0.0))
    inflow_ratio_safe = max(0.0, _safe_float(inflow_ratio_pct, 0.0))

    sim = _simulate_path(
        premium=_safe_float(premium, 0.0),
        years=years_safe,
        irr_pct=_safe_float(irr, 0.0),
        inflow_enabled=bool(inflow_enabled),
        inflow_mode=inflow_mode,
        start_year=start_year_safe,
        years_in=years_in_safe,
        inflow_amt=inflow_amt_safe,
        inflow_ratio_pct=inflow_ratio_safe,
        sim_years=max(_safe_int(sim_years, years_safe + 10), years_safe),
    )

    if all(v == 0 for v in sim["annual_cf"]):
        st.info("目前年度現金流全為 0：請確認「繳費年期 > 0」且（固定年領金額 > 0 或 提領比例 > 0）。")

    if sim["clamped_years"]:
        yrs = ", ".join(str(y) for y in sim["clamped_years"][:5])
        more = "…" if len(sim["clamped_years"]) > 5 else ""
        st.warning(f"已啟用防穿透：在第 {yrs}{more} 年自動降額提領以避免現金值歸零。")

    breakeven = next((y for y, v in zip(sim["timeline"], sim["cum_cf"]) if v >= 0), None)
    if breakeven:
        st.success(f"損益平衡年約為 **第 {breakeven} 年**（累計現金流轉正）。")

    # 圖表：可選擇拆兩張（較易讀）
    split = st.checkbox("將圖拆成兩張（較易讀）", value=True)
    try:
        if PANDAS_AVAILABLE:
            if split:
                flows_df = pd.DataFrame({
                    "當年度現金流": sim["annual_cf"],
                    "累計現金流": sim["cum_cf"],
                }, index=sim["timeline"])
                flows_df.index.name = "年度"
                st.line_chart(flows_df, height=280, use_container_width=True)

                cv_df = pd.DataFrame({"現金值(模擬)": sim["cv"]}, index=sim["timeline"])
                cv_df.index.name = "年度"
                st.line_chart(cv_df, height=280, use_container_width=True)
            else:
                df_chart = pd.DataFrame({
                    "現金值(模擬)": sim["cv"],
                    "累計現金流": sim["cum_cf"],
                    "當年度現金流": sim["annual_cf"],
                }, index=sim["timeline"])
                df_chart.index.name = "年度"
                st.line_chart(df_chart, height=320, use_container_width=True)
        else:
            if split:
                st.line_chart(np.column_stack([sim["annual_cf"], sim["cum_cf"]]), height=280, use_container_width=True)
                st.line_chart(np.column_stack([sim["cv"]]), height=280, use_container_width=True)
            else:
                st.line_chart(np.column_stack([sim["cv"], sim["cum_cf"], sim["annual_cf"]]), height=320, use_container_width=True)
    except Exception:
        st.info("圖表建立時發生例外，但不影響頁面其他功能。若需協助排查請截圖給我。")

    # ───────── 年度現金流表（直接用 sim 結果） ─────────
    is_twd = (currency == "TWD")
    rows = []
    for y, v, acc in zip(sim["timeline"], sim["annual_cf"], sim["cum_cf"]):
        rows.append({
            "年度": y,
            "當年度現金流": _fmt_wan(v) if is_twd else _fmt_currency(v, currency),
            "累計現金流": _fmt_wan(acc) if is_twd else _fmt_currency(acc, currency),
        })

    st.markdown("**完整年度現金流**")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # （選配）顯示計算檢查（以元為單位，不四捨五入）
    with st.expander("顯示計算檢查（元）", expanded=False):
        try:
            if PANDAS_AVAILABLE:
                df_dbg = pd.DataFrame({
                    "年度": sim["timeline"],
                    "當年度現金流(元)": sim["annual_cf"],
                    "累計現金流(元)": sim["cum_cf"],
                    "現金值年末(元)": sim["cv"],
                })
                st.dataframe(df_dbg, use_container_width=True, hide_index=True)
            else:
                st.write("年度：", sim["timeline"])
                st.write("當年度現金流(元)：", sim["annual_cf"])
                st.write("累計現金流(元)：", sim["cum_cf"])
                st.write("現金值年末(元)：", sim["cv"])
        except Exception:
            st.info("檢查表建立時發生例外，但不影響主要功能。")

    # 下載 PDF（不含圖）
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
            for y, v, acc in zip(sim["timeline"], sim["annual_cf"], sim["cum_cf"]):
                if is_twd:
                    flow.append(p(f"第 {y} 年：{_fmt_wan(v)}（累計 {_fmt_wan(acc)}）"))
                else:
                    flow.append(p(f"第 {y} 年：{_fmt_currency(v, currency)}（累計 {_fmt_currency(acc, currency)}）"))

            pdf = build_branded_pdf_bytes(flow)
            st.download_button(
                "⬇️ 下載保單策略 PDF（不含圖）",
                data=pdf,
                file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            pass

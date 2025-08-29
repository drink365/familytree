
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer, table
from tax import determine_heirs_and_shares, eligible_deduction_counts_by_heirs, apply_brackets, ESTATE_BRACKETS, GIFT_BRACKETS

# 顯示單位：萬元（四捨五入到個位數），內部計算以元為單位
def _wan(n: int | float) -> int:
    try:
        return int(round(n / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: int | float) -> str:
    return f"{_wan(n):,} 萬元"

def render():
    st.subheader("🧮 稅務試算（依民法繼承人計算扣除額）")

    # --- Inputs for heirs ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        spouse_alive = st.checkbox("配偶存活", value=True)
    with c2:
        child_count = st.number_input("子女數", min_value=0, value=2, step=1)
    with c3:
        parent_count = st.number_input("父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)
    with c4:
        sibling_count = st.number_input("兄弟姊妹數", min_value=0, value=0, step=1)
    with c5:
        grandparent_count = st.number_input("祖父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)

    order, shares = determine_heirs_and_shares(spouse_alive, child_count, parent_count, sibling_count, grandparent_count)
    display_order = ("配偶＋" + order) if spouse_alive else order
    st.markdown("**法定繼承人**：" + display_order)
    st.write({k: f"{v:.2%}" for k, v in shares.items()} if shares else {"提示": "尚無可辨識之繼承人，或僅配偶"})

    st.markdown("---")
    st.markdown("**扣除額與稅額（單位：萬元）**")

    eligible = eligible_deduction_counts_by_heirs(spouse_alive, shares)

    # --- Inputs (萬元) ---
    colA, colB, colC = st.columns(3)
    with colA:
        estate_base_wan = st.number_input("遺產總額（單位：萬元）", min_value=0, value=12000, step=10)
        funeral_wan     = st.number_input("喪葬費（上限 138 萬；單位：萬元）", min_value=0, value=138, step=1)
    with colB:
        spouse_ded = 5_530_000 if eligible["spouse"] == 1 else 0  # 元
        st.text_input("配偶扣除（自動，單位：萬元）", value=_fmt_wan(spouse_ded), disabled=True)
        basic_ex_wan    = st.number_input("基本免稅（1,333 萬；單位：萬元）", min_value=0, value=1333, step=1)
    with colC:
        dep_children = eligible["children"]
        asc_count    = eligible["ascendants"]
        st.text_input("直系卑親屬人數（自動 ×56 萬）", value=str(dep_children), disabled=True)
        st.text_input("直系尊親屬人數（自動，最多2 ×138 萬）", value=str(asc_count), disabled=True)

    # 換算回元做計算
    estate_base   = int(estate_base_wan * 10000)
    funeral       = int(funeral_wan * 10000)
    basic_ex      = int(basic_ex_wan * 10000)

    # 計算扣除金額（元）
    funeral_capped = min(funeral, 1_380_000)
    amt_children   = dep_children * 560_000
    amt_asc        = asc_count * 1_380_000

    total_deductions = int(funeral_capped + spouse_ded + basic_ex + amt_children + amt_asc)
    taxable = max(0, int(estate_base - total_deductions))
    result = apply_brackets(taxable, ESTATE_BRACKETS)

    st.write({
        "可扣除總額": _fmt_wan(total_deductions),
        "課稅基礎": _fmt_wan(taxable),
        "適用稅率": f"{result['rate']}%",
        "速算扣除": f"{result['quick']:,}",
        "預估應納稅額": _fmt_wan(result['tax']),
    })

    # ---- Build PDF flow (single page, no cover) ----
    flow = [
        title("遺產稅試算結果"), spacer(8),
        h2("法定繼承人與應繼分"),
        p("法定繼承人：" + display_order),
        p("應繼分：" + (", ".join([f"{k} {v:.2%}" for k, v in shares.items()]) if shares else "N/A")),
        spacer(6),
        h2("扣除額計算（僅法定繼承人；單位：萬元）"),
    ]

    # 動態列出扣除項目（排除 0 元）
    deduction_items = [
        ("喪葬費", funeral_capped, None),
        ("配偶扣除", spouse_ded, None),
        ("基本免稅", basic_ex, None),
        ("直系卑親屬", amt_children, f"（{dep_children} 人 × 56 萬）"),
        ("直系尊親屬", amt_asc, f"（{asc_count} 人 × 138 萬）"),
    ]
    for label, amt, extra in deduction_items:
        if int(amt) > 0:
            flow.append(p(f"{label}{extra or ''}：" + _fmt_wan(amt)))

    flow += [
        p("可扣除總額：" + _fmt_wan(total_deductions)),
        spacer(6),
        h2("稅額試算（單位：萬元）"),
        p("課稅基礎：" + _fmt_wan(taxable)),
        p(f"適用稅率：{result['rate']}% ／ 速算扣除：{result['quick']:,}"),
        p("預估應納稅額：" + _fmt_wan(result['tax'])),
    ]

    pdf1 = build_branded_pdf_bytes(flow)
    st.download_button("⬇️ 下載稅務試算 PDF", data=pdf1, file_name=f"estate_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

    # ---- 贈與稅（單位：萬元） ----
    st.markdown("---")
    st.markdown("**贈與稅（單位：萬元）**")
    g1, g2, g3 = st.columns(3)
    with g1:
        gift_total_wan = st.number_input("本年贈與總額（單位：萬元）", min_value=0, value=1000, step=10)
        annual_ex_wan  = st.number_input("每年基本免稅（單位：萬元）", min_value=0, value=244, step=1)
    with g2:
        pay_by     = st.selectbox("納稅義務人", ["贈與人", "受贈人"], index=0)
        donees     = st.number_input("受贈人數（統計用途）", min_value=1, value=1, step=1)
    with g3:
        note       = st.text_input("備註（可填用途/安排）", "")

    gift_total = int(gift_total_wan * 10000)
    annual_ex  = int(annual_ex_wan * 10000)
    gift_taxable = max(0, int(gift_total - annual_ex))
    g_result = apply_brackets(gift_taxable, GIFT_BRACKETS)

    st.write({
        "贈與總額": _fmt_wan(gift_total),
        "免稅額": _fmt_wan(annual_ex),
        "課稅基礎": _fmt_wan(gift_taxable),
        "適用稅率": f"{g_result['rate']}%",
        "速算扣除": f"{g_result['quick']:,}",
        "預估應納稅額": _fmt_wan(g_result['tax']),
    })

    flow2 = [
        title("贈與稅試算結果"), spacer(8),
        p("贈與總額：" + _fmt_wan(gift_total)), p("基本免稅：" + _fmt_wan(annual_ex)),
        p("課稅基礎：" + _fmt_wan(gift_taxable)),
        p(f"適用稅率：{g_result['rate']}% ／ 速算扣除：{g_result['quick']:,}"),
        p("預估應納稅額：" + _fmt_wan(g_result['tax'])), spacer(6),
        p(f"備註：{note or '（無）'} ／ 納稅義務人：{pay_by} ／ 受贈人數：{donees}"),
    ]
    pdf2 = build_branded_pdf_bytes(flow2)
    st.download_button("⬇️ 下載贈與稅試算 PDF", data=pdf2, file_name=f"gift_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

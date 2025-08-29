
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer, table
from tax import determine_heirs_and_shares, eligible_deduction_counts_by_heirs, apply_brackets, ESTATE_BRACKETS, GIFT_BRACKETS

def render():
    st.subheader("🧮 稅務試算（依民法繼承人計算扣除額）")

    # --- Inputs for heirs ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: spouse_alive = st.checkbox("配偶存活", value=True)
    with c2: child_count = st.number_input("子女數", min_value=0, value=2, step=1)
    with c3: parent_count = st.number_input("父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)
    with c4: sibling_count = st.number_input("兄弟姊妹數", min_value=0, value=0, step=1)
    with c5: grandparent_count = st.number_input("祖父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)

    order, shares = determine_heirs_and_shares(spouse_alive, child_count, parent_count, sibling_count, grandparent_count)
    display_order = ("配偶＋" + order) if spouse_alive else order
    st.markdown("**法定繼承人**：" + display_order)
    st.write({k: f"{v:.2%}" for k, v in shares.items()} if shares else {"提示": "尚無可辨識之繼承人，或僅配偶"})

    st.markdown("---")
    st.markdown("**扣除額與稅額**（一般字級顯示避免截斷）")

    eligible = eligible_deduction_counts_by_heirs(spouse_alive, shares)

    colA, colB, colC = st.columns(3)
    with colA:
        estate_base = st.number_input("遺產總額 (TWD)", min_value=0, value=120_000_000, step=1_000_000)
        funeral     = st.number_input("喪葬費（上限 1,380,000）", min_value=0, value=1_380_000, step=10_000)
    with colB:
        spouse_ded  = 5_530_000 if eligible["spouse"] == 1 else 0
        st.text_input("配偶扣除（自動）", value=f"{spouse_ded:,}", disabled=True)
        basic_ex    = st.number_input("基本免稅（13,330,000）", min_value=0, value=13_330_000, step=10_000)
    with colC:
        dep_children = eligible["children"]; asc_count = eligible["ascendants"]
        st.text_input("直系卑親屬人數（自動 ×560,000）", value=str(dep_children), disabled=True)
        st.text_input("直系尊親屬人數（自動，最多2 ×1,380,000）", value=str(asc_count), disabled=True)

    # Compute
    funeral_capped = min(funeral, 1_380_000)
    amt_children = dep_children * 560_000
    amt_asc = asc_count * 1_380_000

    total_deductions = int(funeral_capped + spouse_ded + basic_ex + amt_children + amt_asc)
    taxable = max(0, int(estate_base - total_deductions))
    result = apply_brackets(taxable, ESTATE_BRACKETS)

    st.write({
        "可扣除總額": f"{total_deductions:,}",
        "課稅基礎": f"{taxable:,}",
        "適用稅率": f"{result['rate']}%",
        "速算扣除": f"{result['quick']:,}",
        "預估應納稅額": f"{result['tax']:,}",
    })

    # ---- Build PDF flow (without cover page) ----
    flow = [
        title("遺產稅試算結果"), spacer(8),
        h2("法定繼承人與應繼分"),
        p("法定繼承人：" + display_order),
        p("應繼分：" + (", ".join([f"{k} {v:.2%}" for k, v in shares.items()]) if shares else "N/A")),
        spacer(6),
        h2("扣除額計算（僅法定繼承人）"),
    ]

    # Dynamic deduction rows (skip zero items except total)
    deduction_items = [
        ("喪葬費", funeral_capped),
        ("配偶扣除", spouse_ded),
        ("基本免稅", basic_ex),
        ("直系卑親屬", amt_children if amt_children > 0 else 0),
        ("直系尊親屬", amt_asc if amt_asc > 0 else 0),
    ]
    for label, amt in deduction_items:
        if amt and int(amt) > 0:
            if label == "直系卑親屬":
                flow.append(p(f"直系卑親屬（{dep_children} 人 × 560,000）：{amt:,}"))
            elif label == "直系尊親屬":
                flow.append(p(f"直系尊親屬（{asc_count} 人 × 1,380,000）：{amt:,}"))
            else:
                flow.append(p(f"{label}：{int(amt):,}"))

    # Always include total line
    flow += [
        p(f"可扣除總額：{total_deductions:,}"),
        spacer(6),
        h2("稅額試算"),
        p(f"課稅基礎：{taxable:,}"),
        p(f"適用稅率：{result['rate']}% ／ 速算扣除：{result['quick']:,}"),
        p(f"預估應納稅額：{result['tax']:,}"),
    ]

    pdf1 = build_branded_pdf_bytes(flow)
    st.download_button("⬇️ 下載稅務試算 PDF", data=pdf1, file_name=f"estate_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

    # ---- Gift tax (keep simple, single page, no cover) ----
    st.markdown("---"); st.markdown("**贈與稅（一般字級）**")
    g1, g2, g3 = st.columns(3)
    with g1:
        gift_total = st.number_input("本年贈與總額 (TWD)", min_value=0, value=10_000_000, step=500_000)
        annual_ex  = st.number_input("每年基本免稅", min_value=0, value=2_440_000, step=10_000)
    with g2:
        pay_by     = st.selectbox("納稅義務人", ["贈與人", "受贈人"], index=0)
        donees     = st.number_input("受贈人數（統計用途）", min_value=1, value=1, step=1)
    with g3:
        note       = st.text_input("備註（可填用途/安排）", "")

    gift_taxable = max(0, int(gift_total - annual_ex))
    g_result = apply_brackets(gift_taxable, GIFT_BRACKETS)
    st.write({
        "贈與總額": f"{gift_total:,}",
        "免稅額": f"{annual_ex:,}",
        "課稅基礎": f"{gift_taxable:,}",
        "適用稅率": f"{g_result['rate']}%",
        "速算扣除": f"{g_result['quick']:,}",
        "預估應納稅額": f"{g_result['tax']:,}",
    })

    flow2 = [
        title("贈與稅試算結果"), spacer(8),
        p(f"贈與總額：{gift_total:,}"), p(f"基本免稅：{annual_ex:,}"),
        p(f"課稅基礎：{gift_taxable:,}"),
        p(f"適用稅率：{g_result['rate']}% ／ 速算扣除：{g_result['quick']:,}"),
        p(f"預估應納稅額：{g_result['tax']:,}"), spacer(6),
        p(f"備註：{note or '（無）'} ／ 納稅義務人：{pay_by} ／ 受贈人數：{donees}"),
    ]
    pdf2 = build_branded_pdf_bytes(flow2)
    st.download_button("⬇️ 下載贈與稅試算 PDF", data=pdf2, file_name=f"gift_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

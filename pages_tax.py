# pages_tax.py
# -*- coding: utf-8 -*-
import streamlit as st
from datetime import datetime

from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer
# 若已建立相容小工具（我先前提供的），PDF 會用正式表格；沒有也會自動退回文字列表
try:
    from utils.pdf_compat import table_compat as pdf_table
except Exception:
    pdf_table = None

from tax import (
    determine_heirs_and_shares,
    eligible_deduction_counts_by_heirs,
    apply_brackets,
    ESTATE_BRACKETS,
)

# ===== 小工具：畫面顯示以「萬元」；內部運算仍用「元」 =====
def _wan(n: int | float) -> int:
    try:
        return int(round(n / 10000.0))
    except Exception:
        return 0

def _fmt_wan(n: int | float) -> str:
    return f"{_wan(n):,} 萬元"

# ============================== Page ==============================
def render():
    # 標題（可改成你喜歡的其中一個）
    st.subheader("🧾 法稅工具｜遺產稅試算與法定繼承人")
    st.caption("此頁為示意試算，僅供會談討論；正式申報請以主管機關規定與專業人士意見為準。")

    st.divider()

    # ===== ① 家屬結構（決定繼承順位與扣除名額） =====
    st.markdown("### ① 家屬結構")
    st.caption("勾選/輸入家屬狀況，系統自動判定法定繼承人與應繼分，並帶入可適用的扣除名額。")

    ss = st.session_state
    ss.setdefault("tx_spouse", True)
    ss.setdefault("tx_child", 2)
    ss.setdefault("tx_parent", 0)
    ss.setdefault("tx_sibling", 0)
    ss.setdefault("tx_gparent", 0)

    # 快速情境
    c0a, c0b, c0c, _ = st.columns([1.3, 1.3, 1.3, 3])
    with c0a:
        if st.button("一鍵：配偶＋2子女", use_container_width=True):
            ss.update(tx_spouse=True, tx_child=2, tx_parent=0, tx_sibling=0, tx_gparent=0)
    with c0b:
        if st.button("一鍵：未婚／無子女", use_container_width=True):
            ss.update(tx_spouse=False, tx_child=0, tx_parent=2, tx_sibling=0, tx_gparent=0)
    with c0c:
        if st.button("一鍵：配偶＋父母", use_container_width=True):
            ss.update(tx_spouse=True, tx_child=0, tx_parent=2, tx_sibling=0, tx_gparent=0)

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        spouse_alive = st.checkbox("配偶存活", value=ss.get("tx_spouse", True), key="tx_spouse")
    with a2:
        child_count = st.number_input("子女數", min_value=0, step=1, value=ss.get("tx_child", 2), key="tx_child")
    with a3:
        parent_count = st.number_input("父母存活數（0-2）", min_value=0, max_value=2, step=1, value=ss.get("tx_parent", 0), key="tx_parent")
    with a4:
        sibling_count = st.number_input("兄弟姊妹數", min_value=0, step=1, value=ss.get("tx_sibling", 0), key="tx_sibling")
    with a5:
        grandparent_count = st.number_input("祖父母存活數（0-2）", min_value=0, max_value=2, step=1, value=ss.get("tx_gparent", 0), key="tx_gparent")

    order, shares = determine_heirs_and_shares(spouse_alive, child_count, parent_count, sibling_count, grandparent_count)
    display_order = ("配偶＋" + order) if spouse_alive else order

    b1, b2 = st.columns([2, 1])
    with b1:
        st.markdown(f"**法定繼承人**：{display_order or '（無）'}")
        if shares:
            st.write({k: f"{v:.2%}" for k, v in shares.items()})
        else:
            st.info("目前無可辨識之繼承人（或僅配偶）。")
    with b2:
        eligible = eligible_deduction_counts_by_heirs(spouse_alive, shares)
        st.markdown("**名額（自動）**")
        st.write({
            "配偶": f"{eligible['spouse']} 人",
            "直系卑親屬": f"{eligible['children']} 人",
            "直系尊親屬": f"{eligible['ascendants']} 人（最多 2）",
        })

    st.divider()

    # ===== ② 遺產與扣除（萬） =====
    st.markdown("### ② 遺產與扣除（單位：萬元）")
    cA, cB, cC = st.columns(3)
    with cA:
        estate_base_wan = st.number_input("遺產總額", min_value=0, value=12000, step=10)
        funeral_wan     = st.number_input("喪葬費（上限 138 萬）", min_value=0, value=138, step=1)
    with cB:
        spouse_ded = 5_530_000 if eligible["spouse"] == 1 else 0  # 元
        st.text_input("配偶扣除（自動）", value=_fmt_wan(spouse_ded), disabled=True)
        basic_ex_wan    = st.number_input("基本免稅（1,333 萬）", min_value=0, value=1333, step=1)
    with cC:
        st.text_input("直系卑親屬人數（自動 ×56 萬）", value=str(eligible["children"]), disabled=True)
        st.text_input("直系尊親屬人數（自動 ×138 萬｜最多 2）", value=str(eligible["ascendants"]), disabled=True)

    # 換算回元
    estate_base   = int(estate_base_wan * 10000)
    funeral       = int(funeral_wan * 10000)
    basic_ex      = int(basic_ex_wan * 10000)

    # 扣除金額（元）
    funeral_capped = min(funeral, 1_380_000)
    amt_children   = eligible["children"] * 560_000
    amt_asc        = eligible["ascendants"] * 1_380_000

    total_deductions = int(funeral_capped + spouse_ded + basic_ex + amt_children + amt_asc)
    taxable = max(0, int(estate_base - total_deductions))
    result = apply_brackets(taxable, ESTATE_BRACKETS)

    # ===== ③ 試算結果（摘要卡片） =====
    st.markdown("### ③ 試算結果")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("可扣除總額", _fmt_wan(total_deductions))
    with m2:
        st.metric("課稅基礎", _fmt_wan(taxable))
    with m3:
        st.metric("適用稅率", f"{result['rate']}%")
    with m4:
        st.metric("預估應納稅額", _fmt_wan(result["tax"]))

    with st.expander("查看扣除明細", expanded=False):
        st.write({
            "喪葬費（上限 138 萬）": _fmt_wan(funeral_capped),
            "配偶扣除": _fmt_wan(spouse_ded),
            "基本免稅": _fmt_wan(basic_ex),
            "直系卑親屬（56 萬/人）": _fmt_wan(amt_children),
            "直系尊親屬（138 萬/人，最多 2 人）": _fmt_wan(amt_asc),
        })

    st.divider()

    # ===== 下載 PDF =====
    st.markdown("### 下載 PDF")
    flow = [
        title("遺產稅試算結果"), spacer(6),
        h2("法定繼承人與應繼分"),
        p("法定繼承人：" + (display_order or "（無）")),
        p("應繼分：" + (", ".join([f"{k} {v:.2%}" for k, v in shares.items()]) if shares else "N/A")),
        spacer(6),
        h2("扣除額計算（單位：萬元）"),
    ]

    # 扣除表（PDF：優先正式表格）
    rows = []
    if funeral_capped > 0: rows.append(["喪葬費", "上限 138 萬", _fmt_wan(funeral_capped)])
    if spouse_ded > 0:     rows.append(["配偶扣除", "", _fmt_wan(spouse_ded)])
    if basic_ex > 0:       rows.append(["基本免稅", "", _fmt_wan(basic_ex)])
    if amt_children > 0:   rows.append(["直系卑親屬", f"{eligible['children']} 人 × 56 萬", _fmt_wan(amt_children)])
    if amt_asc > 0:        rows.append(["直系尊親屬", f"{eligible['ascendants']} 人 × 138 萬（最多 2）", _fmt_wan(amt_asc)])

    if pdf_table and rows:
        try:
            flow.append(pdf_table(["項目", "說明", "金額"], rows, widths=[0.2, 0.5, 0.3]))
        except Exception:
            for r in rows:
                flow.append(p(f"{r[0]}{('｜' + r[1]) if r[1] else ''}：{r[2]}"))
    else:
        for r in rows:
            flow.append(p(f"{r[0]}{('｜' + r[1]) if r[1] else ''}：{r[2]}"))

    flow += [
        spacer(6),
        h2("稅額試算（單位：萬元）"),
        p("課稅基礎：" + _fmt_wan(taxable)),
        p(f"適用稅率：{result['rate']}% ／ 速算扣除：{_wan(result['quick'])} 萬元"),
        p("預估應納稅額：" + _fmt_wan(result['tax'])),
        spacer(6),
        p("產出日期：" + datetime.now().strftime("%Y/%m/%d")),
    ]

    pdf_bytes = build_branded_pdf_bytes(flow)
    st.download_button(
        "⬇️ 下載稅務試算 PDF",
        data=pdf_bytes,
        file_name=f"estate_tax_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


import streamlit as st

def _calc_estate_tax(taxable_base: float) -> float:
    # 台灣遺產稅級距（簡化示意；實務請依最新法規調整）
    # 0～56,210,000：10%，速算扣除 0
    # 56,210,001～112,420,000：15%，速算扣除 2,810,000
    # 112,420,001 以上：20%，速算扣除 8,430,000
    if taxable_base <= 0:
        return 0.0
    if taxable_base <= 56210000:
        return taxable_base * 0.10
    if taxable_base <= 112420000:
        return taxable_base * 0.15 - 2810000
    return taxable_base * 0.20 - 8430000

def render():
    st.title("🧾 稅務規劃（示意版）")
    st.write("此頁採用 **表單提交**，減少不必要重跑。")

    with st.form("tax_form"):
        gross_estate = st.number_input("遺產總額（TWD）", min_value=0.0, step=100000.0, value=0.0, format="%.0f")
        deductions  = st.number_input("扣除額（免稅/喪葬/撫養等，TWD）", min_value=0.0, step=100000.0, value=0.0, format="%.0f")
        submitted = st.form_submit_button("計算")
        if submitted:
            taxable = max(0.0, gross_estate - deductions)
            tax     = _calc_estate_tax(taxable)
            st.session_state["tax_result"] = {"taxable": taxable, "tax": tax}

    res = st.session_state.get("tax_result")
    if res:
        st.success(f"應稅額：{res['taxable']:,.0f} 元；預估稅額：{res['tax']:,.0f} 元（示意）")
    else:
        st.info("請輸入資料並按「計算」。")


# -*- coding: utf-8 -*-
import streamlit as st, json

# -------------------- App Config --------------------
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- Branding --------------------
try:
    _BRAND = json.load(open("brand.json", "r", encoding="utf-8"))
except Exception:
    _BRAND = {"PRIMARY":"#D33B2C","BG":"#F7FAFC","LOGO_SQUARE":"logo2.png"}

BRAND_PRIMARY = _BRAND.get("PRIMARY", "#D33B2C")

# -------------------- Router --------------------
def navigate(key: str):
    """Set page via query params then rerun."""
    st.query_params.update({"page": key})
    st.rerun()

q = st.query_params
page = q.get("page") if isinstance(q.get("page"), str) else (q.get("page")[0] if q.get("page") else "home")
if not page:
    page = "home"

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown("## 導覽")
    st.image(_BRAND.get("LOGO_SQUARE", "logo2.png"), width=64)
    st.caption("《影響力》AI 傳承規劃平台")
    st.markdown("---")

def nav_button(label: str, page_key: str, icon: str):
    if st.sidebar.button(f"{icon} {label}", use_container_width=True, key=f"nav_{page_key}"):
        navigate(page_key)

for label, key, icon in [
    ("首頁", "home", "🏠"),
    ("家族樹", "familytree", "🌳"),
    ("法稅傳承", "legacy", "🏛️"),
    ("稅務工具", "tax", "🧾"),
    ("保單策略", "policy", "📦"),
    ("價值觀探索", "values", "💬"),
    ("關於我們", "about", "👩‍💼"),
]:
    nav_button(label, key, icon)

# Sidebar style (safe)
st.markdown(f"""
<style>
section[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    padding: 10px 12px !important;
    margin-bottom: 8px !important;
    font-weight: 600 !important;
    text-align: left !important;
    cursor: pointer !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: #f3f4f6 !important;
    border-color: #cbd5e1 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
}}
</style>
""", unsafe_allow_html=True)

# -------------------- Pages --------------------
def render_home():
    st.markdown(
        f"""
        <div style="max-width:860px">
            <img src="logo2.png" style="height:42px" />
            <p style="margin-top:16px;line-height:1.8">
            10 分鐘完成高資產家族 10 年的傳承規劃<br/>
            專業 × 快速 × 可信任｜整合法稅、保單策略與價值觀，幫助顧問有效成交、幫助家庭安心決策。
            </p>
            <div style="color:#6b7280">《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Router
if page == "home":
    render_home()
elif page == "legacy":
    from pages_legacy import render; render()
elif page == "tax":
    from pages_tax import render; render()
elif page == "policy":
    from pages_policy import render; render()
elif page == "familytree":
    from pages_familytree import render; render()
elif page == "values":
    from pages_values import render; render()
elif page == "about":
    from pages_about import render; render()
else:
    render_home()

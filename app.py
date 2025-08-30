
# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
import streamlit as st

# -------------------- App Config --------------------
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- Branding --------------------
def load_brand():
    try:
        return json.load(open("brand.json", "r", encoding="utf-8"))
    except Exception:
        return {"PRIMARY": "#D33B2C", "BG": "#F7FAFC", "LOGO_SQUARE": "logo2.png", "SHOW_SIDEBAR_LOGO": False}

_BRAND = load_brand()
BRAND_PRIMARY = _BRAND.get("PRIMARY", "#D33B2C")
LOGO_PATH = _BRAND.get("LOGO_SQUARE") or "logo2.png"
SHOW_SIDEBAR_LOGO = bool(_BRAND.get("SHOW_SIDEBAR_LOGO", False))

# fallback 檢查
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = "logo.png" if os.path.exists("logo.png") else ("logo2.png" if os.path.exists("logo2.png") else None)

# -------------------- Router --------------------
def navigate(key: str):
    st.query_params.update({"page": key})
    st.rerun()

def get_page_from_query() -> str:
    q = st.query_params
    if not q or "page" not in q:
        return "home"
    v = q.get("page")
    return v if isinstance(v, str) else (v[0] if v else "home")

page = get_page_from_query()

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown("## 導覽")

    # 預設不顯示側邊欄 Logo，保持全站一致；如需顯示可在 brand.json 設 SHOW_SIDEBAR_LOGO=true
    if SHOW_SIDEBAR_LOGO:
        sidebar_logo = "logo.png" if os.path.exists("logo.png") else (LOGO_PATH if LOGO_PATH else None)
        if sidebar_logo:
            st.image(sidebar_logo, use_container_width=False, width=140)

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

# 側欄按鈕樣式
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] .stButton > button {
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
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f3f4f6 !important;
        border-color: #cbd5e1 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Pages --------------------
def render_home():
    # 置中顯示首頁 Logo
    main_logo = "logo.png" if os.path.exists("logo.png") else (LOGO_PATH if LOGO_PATH else None)
    if main_logo:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.image(main_logo, use_container_width=False, width=280)

    TAGLINE = "說清楚，做得到"
    SUBLINE = "把傳承變簡單。"

    st.markdown(
        f"""
        ### 10 分鐘完成高資產家族 10 年的傳承規劃

        {TAGLINE}｜{SUBLINE}
        """.strip()
    )

    st.caption(f"《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime('%Y/%m/%d')}")

def _safe_import_and_render(module_name: str):
    try:
        mod = __import__(module_name, fromlist=['render'])
        if hasattr(mod, "render"):
            mod.render()
        else:
            st.warning(f"模組 `{module_name}` 缺少 `render()`。")
    except Exception as e:
        st.error(f"載入 `{module_name}` 失敗：{e}")

# 路由
if page == "home":
    render_home()
elif page == "familytree":
    _safe_import_and_render("pages_familytree")
elif page == "legacy":
    _safe_import_and_render("pages_legacy")
elif page == "tax":
    _safe_import_and_render("pages_tax")
elif page == "policy":
    _safe_import_and_render("pages_policy")
elif page == "values":
    _safe_import_and_render("pages_values")
elif page == "about":
    _safe_import_and_render("pages_about")
else:
    render_home()

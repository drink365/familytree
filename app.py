
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
    sidebar_logo = "logo2.png" if os.path.exists("logo2.png") else (LOGO_PATH if LOGO_PATH else None)
    if sidebar_logo:
        st.image(sidebar_logo, use_container_width=False, width=72)
        st.markdown(
            "<style>section[data-testid='stSidebar'] img {display:block; margin: 6px auto;}</style>",
            unsafe_allow_html=True,
        )
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
    # 首頁 LOGO：橫式置左顯示（logo.png，寬 200）
    main_logo = "logo.png" if os.path.exists("logo.png") else (LOGO_PATH if LOGO_PATH else None)
    if main_logo:
        st.image(main_logo, use_container_width=False, width=200)

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


# 路由（以字典單點呼叫，避免任何情況下的重複渲染）
def _page_familytree(): _safe_import_and_render("pages_familytree")
def _page_legacy(): _safe_import_and_render("pages_legacy")
def _page_tax(): _safe_import_and_render("pages_tax")
def _page_policy(): _safe_import_and_render("pages_policy")
def _page_values(): _safe_import_and_render("pages_values")
def _page_about(): _safe_import_and_render("pages_about")

_ROUTES = {
    "home": render_home,
    "familytree": _page_familytree,
    "legacy": _page_legacy,
    "tax": _page_tax,
    "policy": _page_policy,
    "values": _page_values,
    "about": _page_about,
}

_ROUTES.get(page, render_home)()

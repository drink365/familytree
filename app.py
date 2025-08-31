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
        # 預設品牌設定
        return {
            "PRIMARY": "#D33B2C",
            "BG": "#F7FAFC",
            "LOGO_SQUARE": "logo2.png",
            "SHOW_SIDEBAR_LOGO": True,
            "TAGLINE": "說清楚，做得到",
            "SUBLINE": "把傳承變簡單。",
            "RETINA_FACTOR": 3,
        }

_BRAND = load_brand()
BRAND_PRIMARY = _BRAND.get("PRIMARY", "#D33B2C")
LOGO_PATH = _BRAND.get("LOGO_SQUARE") or "logo2.png"
SHOW_SIDEBAR_LOGO = bool(_BRAND.get("SHOW_SIDEBAR_LOGO", True))
TAGLINE = _BRAND.get("TAGLINE", "說清楚，做得到")
SUBLINE = _BRAND.get("SUBLINE", "把傳承變簡單。")
RETINA_FACTOR = int(_BRAND.get("RETINA_FACTOR", 3))

if not os.path.exists(LOGO_PATH):
    LOGO_PATH = "logo2.png" if os.path.exists("logo2.png") else ("logo.png" if os.path.exists("logo.png") else None)

# -------------------- Router helpers --------------------
def navigate(key: str):
    """更新網址參數；不要在回呼裡呼叫 st.rerun()。按鈕本身會觸發 rerun。"""
    st.query_params.update({"page": key})

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

    if SHOW_SIDEBAR_LOGO:
        sidebar_logo_path = "logo2.png" if os.path.exists("logo2.png") else (LOGO_PATH if LOGO_PATH else None)
        if sidebar_logo_path:
            from PIL import Image, ImageFilter
            import base64, io

            def _b64_from_path(path: str, target_px_w: int):
                img = Image.open(path).convert("RGBA")
                if img.width < target_px_w:
                    ratio = target_px_w / img.width
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
                    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2))
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return base64.b64encode(buf.getvalue()).decode("utf-8")

            b64 = _b64_from_path(sidebar_logo_path, 72 * 2)  # 2x for small logo
            st.markdown(
                f"""
                <div class="gfo-logo" style="display:flex;justify-content:center;align-items:center;">
                    <img src="data:image/png;base64,{b64}" class="gfo-logo-img" alt="logo2">
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <style>
                .gfo-logo-img { width: 72px !important; height: auto !important; display:block; }
                @media (max-width: 1200px) { .gfo-logo-img { width: 64px !important; } }
                @media (max-width: 900px)  { .gfo-logo-img { width: 56px !important; } }
                </style>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="gfo-caption">《影響力》AI 傳承規劃平台</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        .gfo-caption { text-align:center; color: rgba(75,85,99,0.9); font-size: 0.9rem; }
        @media (max-width: 900px) { .gfo-caption { font-size: 0.85rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

def nav_button(label: str, page_key: str, icon: str):
    # 頂層 if-statement：按下按鈕後，Streamlit 自動 rerun；navigate 只需改 query。
    if st.sidebar.button(f"{icon} {label}", use_container_width=True, key=f"nav_{page_key}"):
        navigate(page_key)

for label, key, icon in [
    ("首頁", "home", "🏠"),
    ("家族樹", "familytree", "🌳"),
    ("法稅傳承", "legacy", "🏛️"),
    ("稅務工具", "tax", "🧾"),
    ("保單策略", "policy", "📦"),  # ← 保持不改名
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
    @media (max-width: 900px) {
        section[data-testid="stSidebar"] .stButton > button {
            padding: 8px 10px !important;
            font-size: 0.95rem !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------- Cached image upscale for Retina --------
@st.cache_data(show_spinner=False)
def logo_b64_highres(path: str, target_px_width: int, mtime: float, size: int):
    from PIL import Image, ImageFilter
    import base64, io
    img = Image.open(path).convert("RGBA")
    if img.width < target_px_width:
        ratio = target_px_width / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# -------------------- Pages --------------------
def render_home():
    # 首頁 LOGO：高解析輸出
    main_logo_path = "logo.png" if os.path.exists("logo.png") else (LOGO_PATH or None)
    if main_logo_path:
        mtime = os.path.getmtime(main_logo_path); fsize = os.path.getsize(main_logo_path)
        target_css_width = 200
        target_px_width = max(target_css_width * RETINA_FACTOR, 600)
        b64 = logo_b64_highres(main_logo_path, target_px_width, mtime, fsize)
        st.markdown(f'<img src="data:image/png;base64,{b64}" style="width:200px;height:auto;">', unsafe_allow_html=True)

    # Hero（站在客戶角度，不談工具）
    st.title("留下的不只財富，更是愛與責任。")
    st.caption("少紛爭、多世代安穩——合規、現金節奏、家族共識一次到位。")
    st.caption("私密保護｜數字可檢核｜專業共作")

    st.divider()
    st.subheader("從這裡開始")

    # 三顆主按鈕（用客戶語言）
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("① 先把關係畫清楚 🌳", use_container_width=True):
            navigate("familytree")
    with c2:
        if st.button("② 看見風險與稅務缺口 🏛️", use_container_width=True):
            navigate("legacy")  # 或 navigate("tax")
    with c3:
        if st.button("③ 設計可持續的現金節奏（萬元） 📦", use_container_width=True):
            navigate("policy")  # 保留名稱「保單策略」

    # 次要入口（貼近動機）
    st.caption("或：我還不確定，要先想清楚｜我想知道你們是誰")
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("🧭 我還不確定，要先想清楚", use_container_width=True):
            navigate("values")
    with cc2:
        if st.button("👥 我想知道你們是誰", use_container_width=True):
            navigate("about")

    st.divider()
    # 信任條（極簡）
    st.markdown("✅ **私密與保密優先**　　✅ **一切有數字可檢核**　　✅ **與律師/會計師協作**")
    st.caption(f"《影響力》傳承策略平台｜{datetime.now().strftime('%Y/%m/%d')}")

def _safe_import_and_render(module_name: str):
    try:
        mod = __import__(module_name, fromlist=['render'])
        if hasattr(mod, "render"):
            mod.render()
        else:
            st.warning(f"模組 `{module_name}` 缺少 `render()`。")
    except Exception as e:
        st.error(f"載入 `{module_name}` 失敗：{e}")

# 路由（字典單一呼叫）
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

import streamlit as st
from datetime import datetime
from typing import Dict

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",  
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Global Styles (CSS)
# =========================
BRAND_PRIMARY = "#1F4A7A"   
BRAND_ACCENT  = "#C99A2E"   
BRAND_BG      = "#F7F9FB"   
CARD_BG       = "white"

st.markdown(
    f"""
    <style>
      html, body, [class*="css"]  {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
        background-color: {BRAND_BG};
      }}
      .main > div {{
        padding-top: 0.5rem;
        padding-bottom: 2rem;
      }}
      .title-xl {{
        font-size: 40px;
        font-weight: 800;
        color: {BRAND_PRIMARY};
        margin: 0 0 10px 0;
      }}
      .subtitle {{
        font-size: 18px;
        color: #334155;
        margin-bottom: 24px;
      }}
      .hero {{
        border-radius: 18px;
        padding: 40px;
        background: radial-gradient(1000px 400px at 10% 10%, #ffffff 0%, #f3f6fa 45%, #eef2f7 100%);
        border: 1px solid #e6eef5;
        box-shadow: 0 6px 18px rgba(10, 18, 50, 0.04);
      }}
      .card {{
        background: {CARD_BG};
        border-radius: 16px;
        padding: 18px;
        border: 1px solid #e8eef5;
        box-shadow: 0 8px 16px rgba(17, 24, 39, 0.04);
        height: 100%;
      }}
      .card h4 {{
        margin: 6px 0;
        color: {BRAND_PRIMARY};
        font-weight: 800;
      }}
      .muted {{
        color: #64748b;
        font-size: 14px;
        line-height: 1.5;
      }}
      header[data-testid="stHeader"] {{
        background: transparent;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Helper: Feature Card
# =========================
def feature_card(title: str, desc: str, emoji: str):
    st.markdown(
        f"""
        <div class="card">
          <div style="font-size:26px">{emoji}</div>
          <h4>{title}</h4>
          <div class="muted">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================
# Pages
# =========================
def page_home():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="title-xl">10 分鐘完成高資產家族 10 年的傳承規劃</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">專業 × 快速 × 可信任｜將法稅知識、保單策略與家族價值觀整合為行動方案，幫助顧問有效成交、幫助家庭安心決策。</div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 核心功能")
    c1, c2, c3 = st.columns(3)
    with c1:
        feature_card("AI 傳承地圖", "快速產出可視化傳承地圖，成為顧問面談神器。", "🗺️")
    with c2:
        feature_card("稅務試算引擎", "即時計算遺產/贈與稅，支援情境比較。", "🧮")
    with c3:
        feature_card("保單策略模擬", "模擬終身壽/美元儲蓄等方案的傳承效益。", "📦")

def page_legacy_map():
    st.subheader("🗺️ 傳承地圖（示範版）")
    st.caption("快速輸入家族與資產資訊，產出可視化傳承地圖。")

def page_tax():
    st.subheader("🧮 稅務試算（示範版）")
    st.caption("即時計算遺產/贈與稅，支援情境比較。")

def page_policy():
    st.subheader("📦 保單策略（示範版）")
    st.caption("模擬保單策略對現金流與傳承效益的影響。")

def page_values():
    st.subheader("❤️ 價值觀探索（示範版）")
    st.caption("將家族價值觀轉化為傳承行動。")

def page_about():
    st.subheader("🤝 關於我們 / 聯絡")
    st.caption("聯絡資訊與平台介紹。")

# =========================
# Sidebar 導覽按鈕
# =========================
with st.sidebar:
    st.image("logo2.png", width=64)
    st.markdown("### 影響力｜AI 傳承規劃平台")
    st.caption("專業 × 快速 × 可信任")
    st.markdown("---")

    if st.button("🏠 首頁總覽", use_container_width=True):
        st.query_params.update({"page": "home"}); st.rerun()
    if st.button("🗺️ 傳承地圖", use_container_width=True):
        st.query_params.update({"page": "legacy"}); st.rerun()
    if st.button("🧮 稅務試算", use_container_width=True):
        st.query_params.update({"page": "tax"}); st.rerun()
    if st.button("📦 保單策略", use_container_width=True):
        st.query_params.update({"page": "policy"}); st.rerun()
    if st.button("❤️ 價值觀探索", use_container_width=True):
        st.query_params.update({"page": "values"}); st.rerun()
    if st.button("🤝 關於我們 / 聯絡", use_container_width=True):
        st.query_params.update({"page": "about"}); st.rerun()

# =========================
# Router
# =========================
q = st.query_params
page = (q.get("page") or ["home"])
page = page[0] if isinstance(page, list) else page

if page == "home":
    page_home()
elif page == "legacy":
    page_legacy_map()
elif page == "tax":
    page_tax()
elif page == "policy":
    page_policy()
elif page == "values":
    page_values()
elif page == "about":
    page_about()
else:
    page_home()

# =========================
# Footer
# =========================
st.markdown(
    f"""
    <div style="color:#6b7280;font-size:13px;margin-top:20px;">
      《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}
    </div>
    """,
    unsafe_allow_html=True
)

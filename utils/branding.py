# -*- coding: utf-8 -*-
import os
import streamlit as st

# ========= 你的品牌資訊 =========
EMAIL   = "123@gracefo.com"
ADDRESS = "台北市中山區南京東路二段101號9樓"
WEBSITE = "https://gracefo.com"
LOGO_PATH = "./logo.png"   # 側欄與頁首使用

# ========= 基本 Page 設定 =========
def set_page(title: str, layout: str = "centered"):
    """
    設定頁面標題與 layout，並注入全站 CSS。
    這裡同時「隱藏 Streamlit 自動生成的英文頁面選單」。
    """
    st.set_page_config(page_title=title, layout=layout)

    st.markdown("""
    <style>
    /* 隱藏 Streamlit 自動生成的頁面清單（QuickScan、GapPlanner...） */
    section[data-testid="stSidebarNav"] { display: none; }

    /* 全站微調：字距、分隔線、Hero 樣式 */
    html, body, [class*="css"] {
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      letter-spacing: 0.2px;
    }
    hr, .hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 18px 0; }
    .hero-wrap { padding: 8px 0 16px 0; }
    .hero-title { font-size: 28px; font-weight: 800; margin-bottom: 6px; }
    .hero-sub { font-size: 16px; color: #374151; line-height: 1.7; }
    </style>
    """, unsafe_allow_html=True)

# ========= 頁首 Hero =========
def brand_hero(title: str, subtitle: str = ""):
    st.markdown("<div class='hero-wrap'>", unsafe_allow_html=True)
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=120, use_container_width=False)
    st.markdown(f"<div class='hero-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='hero-sub'>{subtitle}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ========= 側欄品牌與分組導航 =========
def _safe_page_link(path: str, label: str, icon: str = ""):
    """避免檔案不存在時報錯。"""
    try:
        if icon:
            st.sidebar.page_link(path, label=f"{icon} {label}")
        else:
            st.sidebar.page_link(path, label=label)
    except Exception:
        pass  # 缺檔就靜默略過

def sidebar_brand():
    with st.sidebar:
        # 品牌卡
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        st.markdown(
            """<div style="font-size:13px; color:#374151; line-height:1.5;">
                <div><strong>影響力傳承平台</strong></div>
                <div>先補足一次性現金，再設計長期現金流，最後擺回資產配置。</div>
            </div>""",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 入門
        st.sidebar.header("入門")
        _safe_page_link("app.py",                 "首頁",          "🏠")
        _safe_page_link("pages/01_QuickScan.py",  "快篩（3 分鐘）","🚦")
        _safe_page_link("pages/02_GapPlanner.py", "缺口與現金流",  "📊")
        _safe_page_link("pages/03_Proposal.py",   "一頁式提案",    "🧾")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 進階
        st.sidebar.header("進階")
        _safe_page_link("pages/04_AssetPlanner.py","資產配置藍圖","🧭")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 關於
        st.sidebar.header("關於")
        _safe_page_link("pages/90_About.py", "關於我們 / 聯絡", "🏢")

        # 聯絡資訊
        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
        st.markdown(
            f"""<div style="font-size:12px; color:#6B7280; line-height:1.6;">
                <div><strong>聯絡我們</strong></div>
                <div>{EMAIL}</div>
                <div>{ADDRESS}</div>
                <div><a href="{WEBSITE}" target="_blank">{WEBSITE}</a></div>
            </div>""",
            unsafe_allow_html=True
        )

# ========= 頁腳 =========
def footer():
    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)
    st.caption("© 永傳家族辦公室｜本平台僅供教育與規劃溝通，非法律或稅務意見。")

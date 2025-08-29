# -*- coding: utf-8 -*-
import os
import streamlit as st

# ========= 你提供的品牌資訊 =========
EMAIL   = "123@gracefo.com"
ADDRESS = "台北市中山區南京東路二段101號9樓"
WEBSITE = "https://gracefo.com"
LOGO_PATH = "./logo.png"   # 側欄與頁首使用
FAVICON   = "./logo2.png"  # 若需要另設 favicon，可在 app 部署層處理

# ========= 基本 Page 設定 =========
def set_page(title: str, layout: str = "centered"):
    """
    設定頁面標題與 layout，並載入全站注入式 CSS（必要時）。
    """
    st.set_page_config(page_title=title, layout=layout)

    # 全站可用的微型 CSS（避免文字大小不一致、改善行距）
    st.markdown("""
    <style>
    /* 調整預設字距與中文渲染 */
    html, body, [class*="css"]  {
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      letter-spacing: 0.2px;
    }
    /* 更柔和的分隔線 */
    hr, .hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 18px 0; }
    /* Hero 封面樣式 */
    .hero-wrap { padding: 8px 0 16px 0; }
    .hero-title { font-size: 28px; font-weight: 800; margin-bottom: 6px; }
    .hero-sub { font-size: 16px; color: #374151; line-height: 1.7; }
    </style>
    """, unsafe_allow_html=True)

# ========= 頁首 Hero =========
def brand_hero(title: str, subtitle: str = ""):
    """
    首頁/各頁上方的標題區塊（簡潔、溫暖）
    """
    st.markdown("<div class='hero-wrap'>", unsafe_allow_html=True)
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=120, use_container_width=False)
    st.markdown(f"<div class='hero-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='hero-sub'>{subtitle}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ========= 側欄品牌與分組導航 =========
def _safe_page_link(path: str, label: str, icon: str = ""):
    """
    包一層 try/except，避免某頁缺檔導致整站報錯。
    """
    try:
        if icon:
            st.sidebar.page_link(path, label=f"{icon} {label}")
        else:
            st.sidebar.page_link(path, label=label)
    except Exception:
        # 若頁面不存在，就不顯示（靜默跳過）
        pass

def sidebar_brand():
    """
    側欄：品牌卡片 + 三段式分組導航（入門 / 進階 / 關於）
    """
    with st.sidebar:
        # 品牌卡
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        st.markdown(
            f"""<div style="font-size:13px; color:#374151; line-height:1.5;">
                <div><strong>影響力傳承平台</strong></div>
                <div>先補足一次性現金，再設計長期現金流，最後擺回資產配置。</div>
            </div>""",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 入門
        st.sidebar.header("入門")
        _safe_page_link("app.py",                "首頁",         "🏠")
        _safe_page_link("pages/01_QuickScan.py","快篩（3 分鐘）","🚦")
        _safe_page_link("pages/02_GapPlanner.py","缺口與現金流","📊")
        _safe_page_link("pages/03_Proposal.py", "一頁式提案",   "🧾")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 進階
        st.sidebar.header("進階")
        _safe_page_link("pages/04_AssetPlanner.py","資產配置藍圖","🧭")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        # 關於
        st.sidebar.header("關於")
        _safe_page_link("pages/90_About.py", "關於我們 / 聯絡", "🏢")

        # 品牌資訊（小一號）
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

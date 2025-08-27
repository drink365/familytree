# -*- coding: utf-8 -*-
import streamlit as st
from pathlib import Path

BRAND = {
    "name": "永傳家族辦公室",
    "english": "Grace Family Office",
    "tagline": "以流動性為核心的家族傳承規劃",
    "logo": "logo.png",
    "favicon": "logo.png",
    "primary": "#B21E2B",
    "text_muted": "#6B7280",
    "site": {
        "email": "service@gracefamilyoffice.example",
        "phone": "+886-2-1234-5678",
        "line": "@gracefamily",
        "address": "台北市信義區君悅大道 1 號 18 樓",
        "website": "https://gracefamilyoffice.example"
    },
    "legal": {
        "disclaimer": "本工具僅供教育與規劃參考，非法律與稅務意見；重要決策前請與您的專業顧問確認。",
        "privacy": "我們重視您的隱私，輸入資料僅保留於瀏覽器工作階段，不會上傳至第三方伺服器。"
    },
    "cta": {"book": "預約一對一傳承健檢", "contact": "聯絡我們"}
}

def set_page(title: str, icon: str | None = None, layout: str = "wide"):
    st.set_page_config(page_title=title, page_icon=(icon or BRAND["favicon"]), layout=layout)

def _page_if_exists(path: str, label: str, icon: str | None = None):
    """只有當檔案存在於專案中時才建立 page_link，避免 StreamlitPageNotFoundError。"""
    if Path(path).exists():
        st.page_link(path, label=label, icon=icon)

def sidebar_brand():
    with st.sidebar:
        if Path(BRAND["logo"]).exists():
            st.image(BRAND["logo"], use_column_width=True)
        st.markdown(
            f"**{BRAND['name']}**  \n"
            f"<small style='color:{BRAND['text_muted']}'>{BRAND['tagline']}</small>",
            unsafe_allow_html=True
        )
        st.divider()
        st.markdown("**快速導覽**")
        _page_if_exists("app.py", "🏠 首頁", None)
        _page_if_exists("pages/01_QuickScan.py", "🚦 快篩", None)
        _page_if_exists("pages/02_GapPlanner.py", "💧 缺口模擬", None)
        _page_if_exists("pages/03_Proposal.py", "📄 一頁式提案", None)
        _page_if_exists("pages/90_About.py", "🏢 關於我們 / 聯絡", None)
        _page_if_exists("pages/91_Privacy.py", "🔒 隱私與免責", None)

def brand_hero(title:str, subtitle:str=""):
    col1, col2 = st.columns([1,4])
    with col1:
        if Path(BRAND['logo']).exists():
            st.image(BRAND['logo'])
    with col2:
        st.markdown(f"### {title}")
        if subtitle:
            st.markdown(f"<span style='color:{BRAND['text_muted']}'>{subtitle}</span>", unsafe_allow_html=True)

def footer():
    st.markdown("---")
    st.markdown(
        f"""
        <div style="font-size:13px;color:{BRAND['text_muted']}">
        {BRAND['legal']['privacy']}<br/>
        {BRAND['legal']['disclaimer']}<br/><br/>
        © {BRAND['name']} | {BRAND['english']}
        </div>
        """, unsafe_allow_html=True
    )

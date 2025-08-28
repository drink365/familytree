# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

set_page("🏠 首頁 | 影響力傳承平台", layout="centered")
sidebar_brand()

# 1) Hero
brand_hero(
    title="讓傳承規劃回到常理：先看現金，再談保單",
    subtitle="三步驟看懂一次性『現金』與長期『現金流』，用數據決定保額與配置，不再被商品推著走。"
)

# 背景價值（為什麼要用）
with st.expander("為什麼需要這個平台？（點開看 20 秒）", expanded=True):
    st.markdown("""
- 多數保單是被業績推動，而**不是**被需求推導。  
- 高資產家庭真正的難題是：**一次性現金**（稅與雜費）＋**長期現金流**（家庭與企業運轉）。  
- 我們把保單放回正確位置：**先補足現金與現金流，再放進整體資產配置**。
""")

st.divider()

# 2) 三步驟（只做一件事，CTA 明確）
st.markdown("### 3 步驟 · 3 分鐘開始")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 1) 快篩")
    st.caption("輸入幾個數字，立刻看到一次性『現金』缺口。")
    st.page_link("pages/01_QuickScan.py", label="🚦 開始快篩（3 分鐘）", use_container_width=True)

with c2:
    st.markdown("#### 2) 缺口與現金流")
    st.caption("把長期『現金流』納入，估算合併需求與建議保額。")
    st.page_link("pages/02_GapPlanner.py", label="📊 前往缺口與現金流", use_container_width=True)

with c3:
    st.markdown("#### 3) 一頁式提案")
    st.caption("自動產生 PDF，易懂、可帶走，與家人一起討論。")
    st.page_link("pages/03_Proposal.py", label="🧾 下載一頁式提案", use_container_width=True)

st.markdown("> 需要把保單放回整體視角？可選 **進階：資產配置藍圖**。")
st.page_link("pages/04_AssetPlanner.py", label="🧭 進階：資產配置藍圖", use_container_width=True)

st.divider()

# 3) 使用者角色切換（誰會用、得到什麼）
st.markdown("### 誰適合使用？")
tab1, tab2 = st.tabs(["👨‍👩‍👧‍👦 高資產家庭 / 企業主", "🧑‍💼 專業顧問"])

with tab1:
    st.markdown("""
- **看得懂**：三分鐘就知道一次性『現金』與長期『現金流』到底差多少。  
- **買對量**：先決定保額，再談商品，不再被推銷。  
- **能行動**：一頁式提案讓家人快速討論、做決策。
""")
    st.page_link("pages/01_QuickScan.py", label="我先試試快篩", use_container_width=True)

with tab2:
    st.markdown("""
- **快產生**：一次到位的計算與圖表，縮短前置時間。  
- **好說服**：以數據和圖像展現專業，建立信任感。  
- **可帶走**：PDF 草案便於會後跟進與成交。
""")
    st.page_link("pages/02_GapPlanner.py", label="用數據做一版草案", use_container_width=True)

st.divider()

# 4) 常見疑問（降低心理成本）
st.markdown("### 常見疑問（FAQ）")
with st.expander("這會強迫我買特定商品嗎？", expanded=False):
    st.markdown("不會。本平台**先決定保額與現金流策略**，商品只是眾多解法之一。")
with st.expander("資料會被儲存嗎？", expanded=False):
    st.markdown("以會談示意為主，不會自動上傳或外流；若要長期追蹤，將以你的同意建立專屬檔案。")
with st.expander("我不懂財稅，會不會很難？", expanded=False):
    st.markdown("不會。每一步只做一件事，頁面語言**避免專業術語**，看圖就懂。")

st.divider()

# 5) 末端 CTA 與品牌
st.page_link("pages/01_QuickScan.py", label="🚦 現在就開始（免費快篩 3 分鐘）", use_container_width=True)
st.page_link("pages/90_About.py", label="🏢 關於我們 / 聯絡方式", use_container_width=True)

footer()

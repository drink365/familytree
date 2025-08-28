# -*- coding: utf-8 -*-
import streamlit as st
from utils.branding import set_page, sidebar_brand, brand_hero, footer

# ─────────────────────────────────────────────────────────────
# 基本設定
# ─────────────────────────────────────────────────────────────
set_page("🏠 首頁 | 保單策略規劃｜影響力傳承平台", layout="centered")
sidebar_brand()

# ─────────────────────────────────────────────────────────────
# Hero：情境 + 情感 + 單一 CTA
# ─────────────────────────────────────────────────────────────
brand_hero(
    title="讓傳承規劃回到常理：先看現金，再談保單",
    subtitle="3 分鐘看懂一次性『現金』與長期『現金流』，用數據決定保額與配置，不再被商品推著走。"
)

st.page_link("pages/01_QuickScan.py", label="🚦 立即開始快篩（約 3 分鐘）", use_container_width=True)
st.write("")

# ─────────────────────────────────────────────────────────────
# 樣式（簡潔卡片）
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.card{
  border: 1px solid #E5E7EB; border-radius: 12px; padding: 18px 16px;
  background: #FFFFFF; transition: all .15s ease;
}
.card:hover{ box-shadow: 0 8px 24px rgba(0,0,0,.06); transform: translateY(-2px); }
.card h4{ margin: 0 0 6px 0; font-size: 18px; }
.card p{ margin: 6px 0 12px 0; color:#374151; font-size:15px; line-height:1.6; }
.small{ color:#6B7280; font-size:13px; }
.kicker{ color:#6B7280; letter-spacing:.4px; font-size:13px; text-transform:uppercase; }
.section-title{ font-size:22px; font-weight:800; margin: 6px 0 10px 0; }
.hr-soft{ border:none; border-top:1px solid #E5E7EB; margin: 18px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 三步驟：一步做一件事
# ─────────────────────────────────────────────────────────────
st.markdown("<div class='kicker'>流程</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>三步驟 · 三分鐘開始</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ① 快篩")
    st.markdown("用少量數字，先看**一次性現金缺口**與傳承準備度。")
    st.page_link("pages/01_QuickScan.py", label="🚦 開始快篩", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ② 缺口＋現金流")
    st.markdown("把**長期現金流**納入，調整年期/幣別，估算**建議保額與年繳**。")
    st.page_link("pages/02_GapPlanner.py", label="📊 前往缺口與保單模擬", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ③ 一頁式提案")
    st.markdown("自動輸出 **PDF 草案**，帶回家與家人共識第二次會面。")
    st.page_link("pages/03_Proposal.py", label="🧾 下載一頁式提案", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<p class='small'>需要把保單放回整體資產視角？可選 <strong>進階：資產配置藍圖</strong>。</p>",
    unsafe_allow_html=True
)
st.page_link("pages/04_AssetPlanner.py", label="🧭 進階：資產配置藍圖", use_container_width=True)

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 分眾價值：誰適合、得到什麼
# ─────────────────────────────────────────────────────────────
st.markdown("<div class='kicker'>對象</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>誰適合使用？</div>", unsafe_allow_html=True)

t1, t2 = st.tabs(["👨‍👩‍👧‍👦 高資產家庭 / 企業主", "🧑‍💼 專業顧問"])

with t1:
    st.markdown("""
- **看得懂**：3 分鐘就知道一次性『現金』與長期『現金流』差多少。  
- **買對量**：先決定保額與現金流策略，之後才談商品。  
- **能行動**：一頁式 PDF 好帶走，和家人快速取得共識。
""")
    st.page_link("pages/01_QuickScan.py", label="我先做快篩", use_container_width=True)

with t2:
    st.markdown("""
- **快產生**：一次到位的計算與圖表，省去試算與排版時間。  
- **好溝通**：以數據與視覺建立專業感，提升信任與效率。  
- **可跟進**：PDF 草案標準化，利於二次會面與成交。
""")
    st.page_link("pages/02_GapPlanner.py", label="用數據做一版草案", use_container_width=True)

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 安心保證（FAQ）
# ─────────────────────────────────────────────────────────────
st.markdown("<div class='kicker'>安心</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>常見疑問（FAQ）</div>", unsafe_allow_html=True)

with st.expander("這會強迫我買某個商品嗎？", expanded=False):
    st.write("不會。本平台**先決定保額與現金流策略**，商品只是眾多解法之一，會在你理解與同意後再討論。")

with st.expander("我不懂財稅／法律，會不會很難？", expanded=False):
    st.write("不會。每一步只做一件事，語言避開專業術語；看圖＋金額摘要即可理解。")

with st.expander("我的資料會被儲存或外流嗎？", expanded=False):
    st.write("不會自動外傳。僅於會談示意範圍內使用；若需長期追蹤與版本管理，會在你的同意下建立專屬檔案。")

st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 最終 CTA + 品牌
# ─────────────────────────────────────────────────────────────
st.page_link("pages/01_QuickScan.py", label="🚦 現在就開始（免費快篩 3 分鐘）", use_container_width=True)
st.page_link("pages/90_About.py", label="🏢 關於我們 / 聯絡方式", use_container_width=True)

footer()

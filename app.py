
import streamlit as st, json
from datetime import datetime
st.set_page_config(page_title="影響力｜AI 傳承規劃平台", page_icon="logo2.png", layout="wide", initial_sidebar_state="expanded")
_BRAND = json.load(open("brand.json", "r", encoding="utf-8"))
BRAND_PRIMARY = _BRAND["PRIMARY"]; BRAND_BG = _BRAND["BG"]


if 'page' not in st.session_state:
    st.session_state['page'] = 'home'
st.markdown("""
<style>
  html, body, [class*="css"] {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", Arial; background-color: {BRAND_BG}; }}
  .main > div {{ padding-top: .5rem; padding-bottom: 2rem; }}
  .hero {

  .top-logo img { max-height: 36px; }
{ border-radius: 18px; padding: 40px; background: radial-gradient(1000px 400px at 10% 10%, #ffffff 0%, #f3f6fa 45%, #eef2f7 100%); border: 1px solid #e6eef5; box-shadow: 0 6px 18px rgba(10,18,50,.04); }}
  .title-xl {{ font-size: 40px; font-weight: 800; color: {BRAND_PRIMARY}; margin: 0 0 10px 0; }}
  .subtitle {{ font-size: 18px; color: #334155; margin-bottom: 24px; }}
  header[data-testid="stHeader"] {{ background: transparent; }}
  .footer {{ color:#6b7280; font-size:13px; margin-top: 20px; }}
</style>
""", unsafe_allow_html=True)
def navigate(key: str): st.query_params.update({"page": key}); st.rerun()

with st.sidebar:
    st.image(_BRAND.get("LOGO_SQUARE", "logo2.png"), width=64)
    st.markdown("### 影響力｜AI 傳承規劃平台"); st.caption("專業 × 快速 × 可信任"); st.markdown("---")
    if st.button("🏠 首頁", use_container_width=True): navigate("home")
    if st.button("🌳 家族樹", use_container_width=True): navigate("familytree")
    if st.button("🏛️ 法稅傳承", use_container_width=True): navigate("legacy")
    if st.button("🧾 稅務工具", use_container_width=True): navigate("tax")
    if st.button("📦 保單策略", use_container_width=True): navigate("policy")
    if st.button("💬 價值觀探索", use_container_width=True): navigate("values")
    if st.button("👩‍💼 關於我們", use_container_width=True): navigate("about")
    st.markdown("---")

    if st.button("🏠 首頁總覽", use_container_width=True): navigate("home")
    if st.button("🗺️ 傳承地圖", use_container_width=True): navigate("legacy")
    if st.button("🧮 稅務試算", use_container_width=True): navigate("tax")
    if st.button("📦 保單策略", use_container_width=True): navigate("policy")
    if st.button("❤️ 價值觀探索", use_container_width=True): navigate("values")
    if st.button("🤝 關於我們 / 聯絡", use_container_width=True): navigate("about")
q = st.query_params; page = (q.get("page") or ["home"]); page = page[0] if isinstance(page, list) else page
top = st.columns([1,5])
with top[0]: st.image(_BRAND.get("LOGO_WIDE","logo.png"), width=180)
with top[1]: st.markdown('<div style="text-align:right; color:#64748b;">《影響力》傳承策略平台｜永傳家族辦公室</div>', unsafe_allow_html=True)
if page == "home":
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="title-xl">10 分鐘完成高資產家族 10 年的傳承規劃</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">專業 × 快速 × 可信任｜整合法稅、保單策略與價值觀，幫助顧問有效成交、幫助家庭安心決策。</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 開始建立傳承地圖", type="primary", use_container_width=True): navigate("legacy")
    with c2:
        if st.button("🌳 家族樹 Family Tree", use_container_width=True): navigate("about")
    st.markdown('</div>', unsafe_allow_html=True)
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
    from pages_legacy import render; render()
st.markdown(f'<div class="footer">《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}</div>', unsafe_allow_html=True)

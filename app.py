
import streamlit as st, json
from datetime import datetime
st.set_page_config(page_title="影響力｜AI 傳承規劃平台", page_icon="logo2.png", layout="wide", initial_sidebar_state="expanded")
_BRAND = json.load(open("brand.json", "r", encoding="utf-8"))
BRAND_PRIMARY = _BRAND["PRIMARY"]; BRAND_BG = _BRAND["BG"]

st.sidebar.markdown("## 導覽")
def nav_card(label, page_key, icon):
    with st.container():
        if st.button(f"{icon} {label}", key=f"btn_{page_key}", use_container_width=True):
            navigate(page_key)
    st.markdown("---")

nav_items = [
    ("首頁", "home", "🏠"),
    ("家族樹", "familytree", "🌳"),
    ("法稅傳承", "legacy", "🏛️"),
    ("稅務工具", "tax", "🧾"),
    ("保單策略", "policy", "📦"),
    ("價值觀探索", "values", "💬"),
    ("關於我們", "about", "👩‍💼"),
]

for label, key, icon in nav_items:
    nav_card(label, key, icon)



if st.button("🌳 家族樹", key="btn_familytree", use_container_width=True): navigate("familytree")
if st.button("🏛️ 法稅傳承", key="btn_legacy", use_container_width=True): navigate("legacy")
if st.button("🧾 稅務工具", key="btn_tax", use_container_width=True): navigate("tax")
if st.button("📦 保單策略", key="btn_policy", use_container_width=True): navigate("policy")
if st.button("💬 價值觀探索", key="btn_values", use_container_width=True): navigate("values")
if st.button("👩‍💼 關於我們", key="btn_about", use_container_width=True): navigate("about")



if st.button("🌳 家族樹", key="btn_familytree", use_container_width=True): navigate("familytree")
if st.button("🏛️ 法稅傳承", key="btn_legacy", use_container_width=True): navigate("legacy")
if st.button("🧾 稅務工具", key="btn_tax", use_container_width=True): navigate("tax")
if st.button("📦 保單策略", key="btn_policy", use_container_width=True): navigate("policy")
if st.button("💬 價值觀探索", key="btn_values", use_container_width=True): navigate("values")
if st.button("👩‍💼 關於我們", key="btn_about", use_container_width=True): navigate("about")



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
                    with c2:
        if st.button("🌳 家族樹 Family Tree", key="btn_家族樹_Family_Tree",  use_container_width=True): navigate("about")
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

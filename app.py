
import os
import importlib
import streamlit as st
from utils.branding import logo_b64_highres

st.set_page_config(page_title="永傳家族傳承教練", page_icon="📦", layout="wide")

# --------- Branding (一次性快取影像處理) ---------
LOGO_PATH = os.path.join("assets", "logo.png")
if os.path.exists(LOGO_PATH):
    mtime = os.path.getmtime(LOGO_PATH)
    fsize = os.path.getsize(LOGO_PATH)
    b64 = logo_b64_highres(LOGO_PATH, target_px_width=240, mtime=mtime, size=fsize)
    st.sidebar.markdown(
        f"<div style='text-align:center; margin-bottom:0.5rem'>"
        f"<img src='data:image/png;base64,{b64}' style='max-width:200px'>"
        f"</div>", unsafe_allow_html=True
    )
else:
    st.sidebar.write("Grace Family Office")

# --------- 導覽（lazy import + render()） ---------
PAGES = {
    "🏠 首頁": "pages.home",
    "🌳 家族樹": "pages.family_tree",
    "💡 價值觀探索": "pages.values",
    "🧾 稅務規劃": "pages.tax",
}

choice = st.sidebar.radio("導覽", list(PAGES.keys()), index=0, label_visibility="visible")

mod_name = PAGES[choice]
mod = importlib.import_module(mod_name)

# 所有頁面模組皆以 render() 作為進入，避免頂層做重活
if hasattr(mod, "render"):
    mod.render()
else:
    st.error(f"模組 {mod_name} 缺少 render()")

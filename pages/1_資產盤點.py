
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note,
                      badge_add, assets_set, family_name_set)

init_session_defaults(); render_sidebar()
st.title("資產盤點")

section_title("🧱", "建立家族識別")
fam = st.text_input("家族名稱（用於封面與報告）", value=st.session_state.family_name, placeholder="例如：黃氏家族")
colA, colB = st.columns([1,1])
with colA:
    if st.button("儲存家族識別", key="btn_profile"):
        name = (fam or "").strip()
        st.session_state.family_name = name
        family_name_set(name)
        st.session_state.profile_done = bool(name)
        if name:
            badge_add("家族識別完成")
            st.success("已儲存。徽章：家族識別完成")
        else:
            st.warning("請輸入家族名稱後再儲存。")

st.divider()
section_title("📦", "輸入資產結構（萬元）")
a1, a2, a3 = st.columns(3)
a4, a5, a6 = st.columns(3)
assets = st.session_state.assets
assets["公司股權"] = a1.number_input("公司股權", 0, 10_000_000, assets["公司股權"])
assets["不動產"]   = a2.number_input("不動產",   0, 10_000_000, assets["不動產"])
assets["金融資產"] = a3.number_input("金融資產", 0, 10_000_000, assets["金融資產"])
assets["保單"]     = a4.number_input("保單",     0, 10_000_000, assets["保單"])
assets["海外資產"] = a5.number_input("海外資產", 0, 10_000_000, assets["海外資產"])
assets["其他"]     = a6.number_input("其他",     0, 10_000_000, assets["其他"])

if st.button("完成資產盤點 ✅", key="btn_assets"):
    total = sum(assets.values())
    if total > 0:
        assets_set(assets)
        st.session_state.assets_done = True
        badge_add("家族建築師")
        st.success(f"已完成資產盤點（總額 {total:,} 萬元）。徽章：家族建築師")
    else:
        st.warning("尚未輸入任何資產金額。")

with st.expander("提示"):
    guidance_note("先把資產全貌放到桌上，我們再談工具。先清晰，後配置。")

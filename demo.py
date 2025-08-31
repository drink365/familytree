# demo.py（獨立頁面版本）
# 將此檔案放到主平台目錄或 pages/ 目錄下，Streamlit 會自動識別成新頁面
# 原始平台架構完全不會被改動

import streamlit as st
from typing import Dict
import math
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# 基本設定
# -----------------------------
st.set_page_config(page_title="影響力｜家族資產地圖 Demo", page_icon="🧭", layout="centered")

HIDE_SIDEBAR = """
    <style>
        [data-testid="collapsedControl"], section[data-testid="stSidebar"] {display:none}
        .small-note {color:#666; font-size:0.9em;}
        .pill {display:inline-block; padding:4px 10px; border-radius:999px; background:#eef; margin-right:6px;}
        .cta {background:#152238; color:#fff; padding:10px 14px; border-radius:10px;}
    </style>
"""
st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)

# -----------------------------
# 常數與示範數據
# -----------------------------
ASSET_CATS = ["公司股權", "不動產", "金融資產", "保單", "海外資產", "其他資產"]
TAIWAN_ESTATE_TAX_TABLE = [(56_210_000, 0.10, 0), (112_420_000, 0.15, 2_810_000), (float("inf"), 0.20, 8_430_000)]
BASIC_EXEMPTION = 13_330_000

DEMO_DATA = {
    "公司股權": 40_000_000,
    "不動產": 25_000_000,
    "金融資產": 12_000_000,
    "保單": 3_000_000,
    "海外資產": 8_000_000,
    "其他資產": 2_000_000,
}

# -----------------------------
# 計算函式
# -----------------------------
def calc_estate_tax(tax_base: int) -> int:
    if tax_base <= 0:
        return 0
    for upper, rate, quick in TAIWAN_ESTATE_TAX_TABLE:
        if tax_base <= upper:
            return math.floor(tax_base * rate - quick)
    return 0

def simulate_with_without_insurance(total_assets: int, insurance_benefit: int) -> Dict[str, int]:
    tax_base = max(0, total_assets - BASIC_EXEMPTION)
    tax = calc_estate_tax(tax_base)
    return {
        "稅基": tax_base,
        "遺產稅": tax,
        "無保單_可用資金": max(0, total_assets - tax),
        "有保單_可用資金": max(0, total_assets - tax + insurance_benefit),
        "差異": max(0, total_assets - tax + insurance_benefit) - max(0, total_assets - tax),
    }

# -----------------------------
# UI
# -----------------------------
st.title("🧭 三步驟 Demo｜家族資產地圖 × 一鍵模擬 × 報告")
st.caption("3 分鐘看懂、5 分鐘產出成果。示意版，非正式稅務或法律建議。")

cols = st.columns(3)
for i, text in enumerate(["① 建立資產地圖", "② 一鍵模擬差異", "③ 生成一頁摘要"]):
    with cols[i]:
        st.markdown(f'<div class="pill">{text}</div>', unsafe_allow_html=True)

st.divider()

# Step 1. 資產地圖
st.subheader("① 建立家族資產地圖")
if "assets" not in st.session_state:
    st.session_state.assets = {k: 0 for k in ASSET_CATS}
if "used_demo" not in st.session_state:
    st.session_state.used_demo = False

left, right = st.columns([1, 1])
with left:
    st.write("輸入六大資產類別金額（新台幣）：")
    if st.button("🔎 載入示範數據"):
        st.session_state.assets = DEMO_DATA.copy()
        st.session_state.used_demo = True
    if st.button("🧹 清除/歸零"):
        st.session_state.assets = {k: 0 for k in ASSET_CATS}
        st.session_state.used_demo = False
    for cat in ASSET_CATS:
        st.session_state.assets[cat] = st.number_input(f"{cat}", min_value=0, step=100_000, value=int(st.session_state.assets.get(cat, 0)))

with right:
    assets = st.session_state.assets
    df_assets = pd.DataFrame({"類別": list(assets.keys()), "金額": list(assets.values())})
    total_assets = int(df_assets["金額"].sum())
    st.write("**資產分布**")
    if total_assets > 0:
        fig, ax = plt.subplots()
        ax.pie(df_assets["金額"], labels=df_assets["類別"], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.info("請輸入金額或載入示範數據。")
    st.metric("目前總資產 (NT$)", f"{total_assets:,.0f}")

st.divider()

# Step 2. 模擬差異
st.subheader("② 一鍵模擬：有保單 vs 無保單")
def_ins = calc_estate_tax(max(0, total_assets - BASIC_EXEMPTION)) if st.session_state.used_demo else 0
insurance_benefit = st.number_input("預估保單理賠金（可調）", min_value=0, step=100_000, value=int(def_ins))
if st.button("⚡ 一鍵模擬差異"):
    result = simulate_with_without_insurance(total_assets, insurance_benefit)
    st.session_state.sim_result = {**result, "總資產": total_assets, "建議保額": insurance_benefit}
    st.success("模擬完成！")
    for k, v in result.items():
        st.metric(k, f"{v:,.0f}")
else:
    st.info("點擊上方按鈕查看結果")

st.divider()

# Step 3. 生成摘要
st.subheader("③ 一頁摘要")
if "sim_result" in st.session_state:
    r = st.session_state.sim_result
    st.write(f"**總資產**：NT$ {r['總資產']:,.0f}")
    st.write(f"**預估遺產稅**：NT$ {r['遺產稅']:,.0f}")
    st.write(f"**有保單 vs 無保單 差異**：NT$ {r['差異']:,.0f}")
    html = f"<h3>家族資產摘要</h3><p>總資產: NT$ {r['總資產']:,.0f}</p><p>遺產稅: NT$ {r['遺產稅']:,.0f}</p><p>差異: NT$ {r['差異']:,.0f}</p>"
    st.download_button("⬇️ 下載摘要 (HTML)", data=html, file_name="demo_summary.html", mime="text/html")
else:
    st.info("請先完成模擬")

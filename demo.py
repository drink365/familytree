# demo.py（專業版報告｜安全共存版）
# 目的：
# 1) 不影響現有架構（獨立頁面、避免 session key 衝突、set_page_config 安全）
# 2) 加入品牌 Logo 與聯絡資訊
# 3) 三步驟體驗：資產輸入 → 一鍵模擬 → 下載一頁摘要（HTML 可列印 PDF）

from typing import Dict
import math
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# -----------------------------
# Page Config（若已被其他頁設定，忽略即可）
# -----------------------------
try:
    st.set_page_config(page_title="影響力｜家族資產地圖 Demo", page_icon="🧭", layout="centered")
except Exception:
    pass

# -----------------------------
# 品牌資訊（請自行替換 LOGO 與聯絡方式）
# -----------------------------
BRAND_LOGO_URL = "https://yourdomain.com/logo.png"  # TODO: 換成實際 Logo URL
BRAND_CONTACT = (
    "《影響力》傳承策略平台｜永傳家族辦公室
"
    "https://gracefo.com
"
    "聯絡信箱：123@gracefo.com"
)

# -----------------------------
# 常數與示範資料（僅教育示意，非正式稅務建議）
# -----------------------------
ASSET_CATS = ["公司股權", "不動產", "金融資產", "保單", "海外資產", "其他資產"]
TAIWAN_ESTATE_TAX_TABLE = [
    (56_210_000, 0.10, 0),
    (112_420_000, 0.15, 2_810_000),
    (float("inf"), 0.20, 8_430_000),
]
BASIC_EXEMPTION = 13_330_000

DEMO_DATA = {
    "公司股權": 40_000_000,
    "不動產": 25_000_000,
    "金融資產": 12_000_000,
    "保單": 3_000_000,  # 現有保單的保單價值（非理賠金）
    "海外資產": 8_000_000,
    "其他資產": 2_000_000,
}

# -----------------------------
# 計算函式
# -----------------------------

def calc_estate_tax(tax_base: int) -> int:
    """依簡化級距計算遺產稅（示意）。"""
    if tax_base <= 0:
        return 0
    for upper, rate, quick in TAIWAN_ESTATE_TAX_TABLE:
        if tax_base <= upper:
            return math.floor(tax_base * rate - quick)
    return 0


def simulate_with_without_insurance(total_assets: int, insurance_benefit: int) -> Dict[str, int]:
    """示意比較：無保單 vs 有保單（理賠金假設直接給付家人）。"""
    total_assets = max(0, int(total_assets))
    insurance_benefit = max(0, int(insurance_benefit))

    tax_base = max(0, total_assets - BASIC_EXEMPTION)
    tax = calc_estate_tax(tax_base)

    cash_without = max(0, total_assets - tax)
    cash_with = max(0, total_assets - tax + insurance_benefit)

    return {
        "稅基": tax_base,
        "遺產稅": tax,
        "無保單_可用資金": cash_without,
        "有保單_可用資金": cash_with,
        "差異": cash_with - cash_without,
    }


def build_summary_html(r: Dict[str, int]) -> str:
    """輸出可列印的一頁式 HTML 摘要（含品牌 Logo 與聯絡資訊）。"""
    # 聯絡資訊換成 HTML 斷行
    contact_html = "<br/>".join(BRAND_CONTACT.split("
"))
    return f"""<!DOCTYPE html>
<html lang='zh-Hant'>
<head>
<meta charset='utf-8'>
<title>家族資產 × 策略摘要（示意）</title>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Noto Sans TC', 'Microsoft JhengHei', sans-serif; line-height:1.6; padding:24px; }}
h1, h2, h3 {{ margin: 0 0 10px; }}
.section {{ margin-bottom:18px; }}
.kpi {{ display:flex; gap:16px; flex-wrap:wrap; }}
.card {{ border:1px solid #eee; border-radius:12px; padding:12px 16px; background:#fafafa; }}
.small {{ color:#666; font-size:12px; }}
strong {{ color:#152238; }}
hr {{ border:none; border-top:1px solid #eee; margin:16px 0; }}
.footer {{ margin-top: 8px; color:#666; font-size:12px; }}
.brand {{ display:flex; align-items:center; gap:12px; margin:8px 0 16px; }}
.brand img {{ height: 36px; }}
</style>
</head>
<body>
  <div class='brand'>
    <img src='{BRAND_LOGO_URL}' alt='logo' />
    <div><strong>《影響力》傳承策略平台｜永傳家族辦公室</strong></div>
  </div>

  <h3>家族資產 × 策略摘要（示意）</h3>
  <div class='section'>
    <div class='kpi'>
      <div class='card'><div>總資產</div><div><strong>NT$ {r['總資產']:,.0f}</strong></div></div>
      <div class='card'><div>稅基</div><div><strong>NT$ {r['稅基']:,.0f}</strong></div></div>
      <div class='card'><div>預估遺產稅</div><div><strong>NT$ {r['遺產稅']:,.0f}</strong></div></div>
      <div class='card'><div>建議保額</div><div><strong>NT$ {r['建議保額']:,.0f}</strong></div></div>
    </div>
  </div>

  <div class='section'>
    <h4>情境比較</h4>
    <ul>
      <li>無保單：可用資金 <strong>NT$ {r['無保單_可用資金']:,.0f}</strong></li>
      <li>有保單（理賠金 NT$ {r['建議保額']:,.0f}）：可用資金 <strong>NT$ {r['有保單_可用資金']:,.0f}</strong></li>
    </ul>
    <p><strong>差異：</strong>提升可動用現金 <strong>NT$ {r['差異']:,.0f}</strong></p>
  </div>

  <hr />
  <div class='footer'>
    <div>{contact_html}</div>
    <div class='small'>備註：本頁為示意，不構成稅務或法律建議；細節以專業顧問與最新法令為準。</div>
  </div>
</body>
</html>"""

# -----------------------------
# 頁面：三步驟體驗
# -----------------------------
st.title("🧭 三步驟 Demo｜家族資產地圖 × 一鍵模擬 × 報告")
if BRAND_LOGO_URL:
    st.image(BRAND_LOGO_URL, width=150)
st.caption("3 分鐘看懂、5 分鐘產出成果。示意版，非正式稅務或法律建議。")

cols = st.columns(3)
labels = ["① 建立資產地圖", "② 一鍵模擬差異", "③ 生成一頁摘要"]
for i in range(3):
    with cols[i]:
        st.markdown(
            f'<div style="display:inline-block;padding:4px 10px;border-radius:999px;background:#eef;margin-right:6px;">{labels[i]}</div>',
            unsafe_allow_html=True,
        )

st.divider()

# Step 1
st.subheader("① 建立家族資產地圖")
if "demo_assets" not in st.session_state:
    st.session_state.demo_assets = {k: 0 for k in ASSET_CATS}
if "demo_used" not in st.session_state:
    st.session_state.demo_used = False

left, right = st.columns([1, 1])
with left:
    st.write("輸入六大資產類別金額（新台幣）：")
    cA, cB = st.columns(2)
    with cA:
        if st.button("🔎 載入示範數據"):
            st.session_state.demo_assets = DEMO_DATA.copy()
            st.session_state.demo_used = True
    with cB:
        if st.button("🧹 清除/歸零"):
            st.session_state.demo_assets = {k: 0 for k in ASSET_CATS}
            st.session_state.demo_used = False
            st.session_state.demo_result = None

    for cat in ASSET_CATS:
        st.session_state.demo_assets[cat] = st.number_input(
            f"{cat}", min_value=0, step=100_000, value=int(st.session_state.demo_assets.get(cat, 0))
        )

with right:
    assets = st.session_state.demo_assets
    df_assets = pd.DataFrame({"類別": list(assets.keys()), "金額": list(assets.values())})
    total_assets = int(df_assets["金額"].sum())

    st.write("**資產分布**（圓餅圖）")
    if total_assets > 0:
        fig, ax = plt.subplots()
        ax.pie(df_assets["金額"], labels=df_assets["類別"], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.info("請輸入金額或先點『載入示範數據』。")

    st.metric("目前總資產 (NT$)", f"{total_assets:,.0f}")

st.divider()

# Step 2
st.subheader("② 一鍵模擬：有保單 vs 無保單")
pre_tax = calc_estate_tax(max(0, total_assets - BASIC_EXEMPTION)) if st.session_state.demo_used else 0
insurance_benefit = st.number_input(
    "預估保單理賠金（可調）",
    min_value=0,
    step=100_000,
    value=int(pre_tax),
    help="示意用途：假設理賠金直接提供給家人，可提高可動用現金。",
)

if st.button("⚡ 一鍵模擬差異"):
    result = simulate_with_without_insurance(total_assets, insurance_benefit)
    st.session_state.demo_result = {**result, "總資產": total_assets, "建議保額": insurance_benefit}
    st.success("模擬完成！")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("稅基 (NT$)", f"{result['稅基']:,.0f}")
        st.metric("預估遺產稅 (NT$)", f"{result['遺產稅']:,.0f}")
    with c2:
        st.metric("無保單：可用資金 (NT$)", f"{result['無保單_可用資金']:,.0f}")
        st.metric("有保單：可用資金 (NT$)", f"{result['有保單_可用資金']:,.0f}")
    st.metric("差異（提升的可用現金）(NT$)", f"{result['差異']:,.0f}")
else:
    st.info("點擊『一鍵模擬差異』查看結果。")

st.caption("＊法稅提醒：此模擬僅為示意，實務須視受益人、給付方式與最新法令而定。")

st.divider()

# Step 3
st.subheader("③ 一頁摘要（可下載）")
if st.session_state.get("demo_result"):
    r = st.session_state.demo_result

    # 頁內摘要
    st.markdown(
        f"""
**總資產**：NT$ {r['總資產']:,.0f}  

**稅務簡估**  
- 稅基（總資產 − 基本免稅額 NT$ {BASIC_EXEMPTION:,.0f}）：NT$ {r['稅基']:,.0f}  
- 預估遺產稅：NT$ {r['遺產稅']:,.0f}  

**情境比較**  
- 無保單：可用資金 NT$ {r['無保單_可用資金']:,.0f}  
- 有保單（理賠金 NT$ {r['建議保額']:,.0f}）：可用資金 NT$ {r['有保單_可用資金']:,.0f}  

**差異**：提升可動用現金 **NT$ {r['差異']:,.0f}**  
> 本頁為示意，不構成稅務或法律建議；細節以專業顧問與最新法令為準。
"""
    )

    # 下載單頁 HTML（可列印成 PDF）
    html = build_summary_html(r)
    st.download_button(
        label="⬇️ 下載一頁摘要（HTML，可列印成 PDF）",
        data=html,
        file_name="家族資產_策略摘要_demo.html",
        mime="text/html",
    )
else:
    st.info("先完成上一步『一鍵模擬差異』，系統會自動生成摘要。")

st.write("---")
st.info(
    "🚀 專業版（規劃中）：進階稅務模擬、更多情境比較、白標報告與客戶 Viewer。如需試用名單，請與我們聯繫。"
)

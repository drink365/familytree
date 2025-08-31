# demo.py（專業版報告＋情境說明＋品牌自訂｜安全共存版）
# 目的：
# 1) 不影響現有架構（獨立頁面、避免 session key 衝突、set_page_config 安全）
# 2) 品牌可自訂：上傳 Logo 或填寫 Logo URL、編輯聯絡資訊（頁面與下載報告同步）
# 3) 三步驟體驗：資產輸入 → 一鍵模擬 → 下載一頁摘要（HTML 可列印 PDF）
# 4) 內建三個情境模板＋情境說明，能一鍵載入並同步寫入報告

from typing import Dict, Optional
import base64
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
# 預設品牌資訊（可被側邊欄覆蓋）
# -----------------------------
DEFAULT_BRAND_LOGO_URL = ""  # 可留空；若上傳 Logo 會自動使用
DEFAULT_BRAND_CONTACT = "《影響力》傳承策略平台｜永傳家族辦公室\nhttps://gracefo.com\n聯絡信箱：123@gracefo.com"

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

# 典型情境模板（僅示意，方便第一次上手）
SCENARIOS = {
    "創辦人A｜公司占比高": {
        "公司股權": 65_000_000,
        "不動產": 18_000_000,
        "金融資產": 7_000_000,
        "保單": 2_000_000,
        "海外資產": 6_000_000,
        "其他資產": 2_000_000,
    },
    "跨境家庭B｜海外資產高": {
        "公司股權": 28_000_000,
        "不動產": 20_000_000,
        "金融資產": 10_000_000,
        "保單": 4_000_000,
        "海外資產": 30_000_000,
        "其他資產": 3_000_000,
    },
    "保守型C｜金融資產高": {
        "公司股權": 10_000_000,
        "不動產": 22_000_000,
        "金融資產": 35_000_000,
        "保單": 5_000_000,
        "海外資產": 6_000_000,
        "其他資產": 2_000_000,
    },
}

SCENARIO_DESCRIPTIONS = {
    "創辦人A｜公司占比高": {
        "適用對象": "第一代創辦人、股權集中、資產波動度高",
        "常見痛點": "公司估值高但流動性低；二次繳稅風險；子女接班不確定",
        "建議邏輯": "用保單補流動性，確保稅金與傳承金可即時到位，避免賣股或稀釋控制權",
    },
    "跨境家庭B｜海外資產高": {
        "適用對象": "台灣/大陸/美國等多法域資產分布的家庭",
        "常見痛點": "跨境稅制差異、CRS/FBAR 合規、受益人設計複雜",
        "建議邏輯": "分帳戶分法域盤點，先確保本國稅務與現金流，再規劃境外信託/保單資金",
    },
    "保守型C｜金融資產高": {
        "適用對象": "現金部位高、偏好穩健報酬、保單比重中等以上",
        "常見痛點": "通膨與低利率侵蝕購買力；資產在世與身後的配置不清",
        "建議邏輯": "以保單與年金確保關鍵現金流，剩餘金融資產做多情境桶分配",
    },
}

# -----------------------------
# Util：將上傳圖檔轉成 data URI（HTML 內嵌）
# -----------------------------
def file_to_data_uri(file) -> Optional[str]:
    if not file:
        return None
    data = file.read()
    # 簡單推測 MIME
    mime = "image/png"
    name = (file.name or "").lower()
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        mime = "image/jpeg"
    elif name.endswith(".svg"):
        mime = "image/svg+xml"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

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

# -----------------------------
# HTML 報告（品牌＋情境說明）
# -----------------------------
def build_summary_html(
    r: Dict[str, int],
    logo_src: str,  # data uri 或 http(s) url，可為空字串
    contact_text: str,
    scenario_title: str | None = None,
    scenario_desc: dict | None = None,
) -> str:
    contact_html = "<br/>".join(contact_text.split("\n"))
    logo_img = f"<img src='{logo_src}' alt='logo' />" if logo_src else ""
    scenario_block = ""
    if scenario_title and scenario_desc:
        scenario_block = f"""
  <div class='section'>
    <h4>情境說明｜{scenario_title}</h4>
    <ul>
      <li><strong>適用對象：</strong>{scenario_desc.get('適用對象','')}</li>
      <li><strong>常見痛點：</strong>{scenario_desc.get('常見痛點','')}</li>
      <li><strong>建議邏輯：</strong>{scenario_desc.get('建議邏輯','')}</li>
    </ul>
  </div>
        """

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
    {logo_img}
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
{scenario_block}
  <hr />
  <div class='footer'>
    <div>{contact_html}</div>
    <div class='small'>備註：本頁為示意，不構成稅務或法律建議；細節以專業顧問與最新法令為準。</div>
  </div>
</body>
</html>"""

# -----------------------------
# Session 狀態（避免與主程式衝突）
# -----------------------------
if "demo_assets" not in st.session_state:
    st.session_state.demo_assets = {k: 0 for k in ASSET_CATS}
if "demo_used" not in st.session_state:
    st.session_state.demo_used = False
if "demo_selected_scenario" not in st.session_state:
    st.session_state.demo_selected_scenario = None
if "demo_brand_contact" not in st.session_state:
    st.session_state.demo_brand_contact = DEFAULT_BRAND_CONTACT
if "demo_logo_data_uri" not in st.session_state:
    st.session_state.demo_logo_data_uri = None
if "demo_logo_url" not in st.session_state:
    st.session_state.demo_logo_url = DEFAULT_BRAND_LOGO_URL

# -----------------------------
# 側邊欄：品牌自訂（Logo 與聯絡資訊）
# -----------------------------
with st.sidebar:
    st.subheader("⚙️ 品牌設定（可選）")

    uploaded_logo = st.file_uploader("上傳 Logo（PNG/JPG/SVG）", type=["png", "jpg", "jpeg", "svg"])
    if uploaded_logo:
        st.session_state.demo_logo_data_uri = file_to_data_uri(uploaded_logo)

    st.session_state.demo_logo_url = st.text_input(
        "或填 Logo 網址（擇一即可）",
        value=st.session_state.demo_logo_url or "",
        placeholder="https://example.com/logo.png",
    )

    st.session_state.demo_brand_contact = st.text_area(
        "聯絡資訊（多行）",
        value=st.session_state.demo_brand_contact,
        height=90,
        help="每一行會在報告中換行顯示",
    )

# 取得用於顯示的 Logo 來源（頁面用 URL，下載報告用 data URI 優先）
page_logo_src = st.session_state.demo_logo_data_uri or st.session_state.demo_logo_url
report_logo_src = st.session_state.demo_logo_data_uri or st.session_state.demo_logo_url
brand_contact_text = st.session_state.demo_brand_contact

# -----------------------------
# 頁面：三步驟體驗
# -----------------------------
st.title("🧭 三步驟 Demo｜家族資產地圖 × 一鍵模擬 × 報告")
if page_logo_src:
    st.image(page_logo_src, width=150)
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
left, right = st.columns([1, 1])
with left:
    st.write("輸入六大資產類別金額（新台幣）：")
    cA, cB = st.columns(2)
    with cA:
        if st.button("🔎 載入示範數據"):
            st.session_state.demo_assets = DEMO_DATA.copy()
            st.session_state.demo_used = True
            st.session_state.demo_selected_scenario = None
    with cB:
        if st.button("🧹 清除/歸零"):
            st.session_state.demo_assets = {k: 0 for k in ASSET_CATS}
            st.session_state.demo_used = False
            st.session_state.demo_result = None
            st.session_state.demo_selected_scenario = None

    # 一鍵載入典型情境
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("🏢 創辦人A"):
            st.session_state.demo_assets = SCENARIOS["創辦人A｜公司占比高"].copy()
            st.session_state.demo_used = True
            st.session_state.demo_selected_scenario = "創辦人A｜公司占比高"
            st.info("已載入情境：創辦人A｜公司占比高")
    with s2:
        if st.button("🌏 跨境家庭B"):
            st.session_state.demo_assets = SCENARIOS["跨境家庭B｜海外資產高"].copy()
            st.session_state.demo_used = True
            st.session_state.demo_selected_scenario = "跨境家庭B｜海外資產高"
            st.info("已載入情境：跨境家庭B｜海外資產高")
    with s3:
        if st.button("💼 保守型C"):
            st.session_state.demo_assets = SCENARIOS["保守型C｜金融資產高"].copy()
            st.session_state.demo_used = True
            st.session_state.demo_selected_scenario = "保守型C｜金融資產高"
            st.info("已載入情境：保守型C｜金融資產高")

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
        ax.pie(df_assets["金額"], labels=df_assets["類別"], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
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
    scenario_key = st.session_state.get("demo_selected_scenario")
    desc = SCENARIO_DESCRIPTIONS.get(scenario_key) if scenario_key else None

    # 頁內摘要（含情境說明）
    base_md = f"""
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
    if scenario_key and desc:
        base_md += f"""

**情境說明｜{scenario_key}**  
- 適用對象：{desc.get('適用對象','')}  
- 常見痛點：{desc.get('常見痛點','')}  
- 建議邏輯：{desc.get('建議邏輯','')}  
"""
    st.markdown(base_md)

    # 下載單頁 HTML（可列印成 PDF），同步帶入品牌與情境內容
    html = build_summary_html(
        r,
        logo_src=report_logo_src or "",
        contact_text=brand_contact_text,
        scenario_title=scenario_key,
        scenario_desc=desc,
    )
    st.download_button(
        label="⬇️ 下載一頁摘要（HTML，可列印成 PDF）",
        data=html,
        file_name="家族資產_策略摘要_demo.html",
        mime="text/html",
    )
else:
    st.info("先完成上一步『一鍵模擬差異』，系統會自動生成摘要。")

st.write("---")
st.info("🚀 專業版（規劃中）：進階稅務模擬、更多情境比較、白標報告與客戶 Viewer。如需試用名單，請與我們聯繫。")

# demo.py（寬版｜統一 NotoSansTC｜HTML+內建品牌PDF 雙下載｜無引導）
# - 內建 PDF：沿用 utils/pdf_utils.py 的品牌頁首/頁尾樣式（LOGO/色票/字型）
# - 標題已縮小並加粗（h2）
# - 全頁與圖表使用 NotoSansTC（根目錄或 fonts/ 內）
# - 聯絡信箱：123@gracefo.com

from typing import Dict, Optional
import base64, json, os, math
from textwrap import dedent

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import streamlit as st

# ============== 讀取你專案的 PDF 工具（品牌頁首/頁尾） ==============
try:
    # 你 ZIP 內的模組
    from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer
    from utils.pdf_compat import table_compat
    HAVE_BRANDED_PDF = True
except Exception:
    HAVE_BRANDED_PDF = False

# -----------------------------
# Page Config（若已被其他頁設定，忽略即可）
# -----------------------------
try:
    st.set_page_config(page_title="影響力｜家族資產地圖 Demo", page_icon="🧭", layout="wide")
except Exception:
    pass

# -----------------------------
# 全站字型注入（HTML/CSS 用）
# -----------------------------
def _embed_font_css() -> str:
    """優先注入本地 NotoSansTC 為 data:uri，讓頁面中文字與下載 HTML 一致。"""
    candidates = [
        "NotoSansTC-Regular.ttf", "NotoSansTC-Regular.otf",
        "fonts/NotoSansTC-Regular.ttf", "fonts/NotoSansTC-Regular.otf",
        "fonts/NotoSansCJKtc-Regular.otf", "fonts/SourceHanSansTC-Regular.otf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                b64 = base64.b64encode(open(p, "rb").read()).decode("utf-8")
                fmt = "truetype" if p.lower().endswith(".ttf") else "opentype"
                st.markdown(
                    f"""
<style>
@font-face {{
  font-family: 'NotoSansTC_Local';
  src: url(data:font/{'ttf' if fmt=='truetype' else 'otf'};base64,{b64}) format('{fmt}');
  font-weight: 400; font-style: normal; font-display: swap;
}}
@font-face {{
  font-family: 'NotoSansTC_Local';
  src: url(data:font/{'ttf' if fmt=='truetype' else 'otf'};base64,{b64}) format('{fmt}');
  font-weight: 700; font-style: normal; font-display: swap;
}}
html, body, [data-testid="stAppViewContainer"] * {{
  font-family: 'NotoSansTC_Local','Noto Sans TC','Microsoft JhengHei','PingFang TC',sans-serif !important;
}}
</style>
""",
                    unsafe_allow_html=True,
                )
                return "NotoSansTC_Local"
            except Exception:
                pass
    # 後備
    st.markdown(
        """
<style>
html, body, [data-testid="stAppViewContainer"] * {
  font-family: 'Noto Sans TC','Microsoft JhengHei','PingFang TC',sans-serif !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
    return "Noto Sans TC"

PAGE_FONT_FAMILY = _embed_font_css()

# -----------------------------
# Matplotlib 中文字型（圖表用）
# -----------------------------
@st.cache_resource(show_spinner=False)
def _setup_cjk_font_for_matplotlib() -> str:
    local_candidates = [
        "NotoSansTC-Regular.ttf", "NotoSansTC-Regular.otf",
        "fonts/NotoSansTC-Regular.ttf", "fonts/NotoSansTC-Regular.otf",
        "fonts/NotoSansCJKtc-Regular.otf", "fonts/SourceHanSansTC-Regular.otf",
    ]
    system_candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansTC-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msjh.ttc",
    ]
    family_candidates = [
        "NotoSansTC_Local", "Noto Sans TC", "Noto Sans CJK TC",
        "Source Han Sans TC", "Microsoft JhengHei", "PingFang TC"
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False

    chosen = ""
    for p in local_candidates + system_candidates:
        if os.path.exists(p):
            try:
                fm.fontManager.addfont(p)
                chosen = fm.FontProperties(fname=p).get_name()
                break
            except Exception:
                pass
    if not chosen:
        installed = {f.name for f in fm.fontManager.ttflist}
        for fam in family_candidates:
            if fam in installed:
                chosen = fam
                break
    if chosen:
        matplotlib.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": [chosen, "DejaVu Sans", "Arial", "sans-serif"],
            "font.size": 11,
            "legend.fontsize": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
        })
    return chosen

CHOSEN_MPL_FONT = _setup_cjk_font_for_matplotlib()

# -----------------------------
# 常數與示範資料（示意，非正式稅務建議）
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
    "保單": 3_000_000,
    "海外資產": 8_000_000,
    "其他資產": 2_000_000,
}

SCENARIOS = {
    "創辦人A｜公司占比高": {
        "公司股權": 65_000_000, "不動產": 18_000_000, "金融資產": 7_000_000,
        "保單": 2_000_000, "海外資產": 6_000_000, "其他資產": 2_000_000,
    },
    "跨境家庭B｜海外資產高": {
        "公司股權": 28_000_000, "不動產": 20_000_000, "金融資產": 10_000_000,
        "保單": 4_000_000, "海外資產": 30_000_000, "其他資產": 3_000_000,
    },
    "保守型C｜金融資產高": {
        "公司股權": 10_000_000, "不動產": 22_000_000, "金融資產": 35_000_000,
        "保單": 5_000_000, "海外資產": 6_000_000, "其他資產": 2_000_000,
    },
}
SCENARIO_DESCRIPTIONS = {
    "創辦人A｜公司占比高": {
        "適用對象": "第一代創辦人、股權集中、資產波動度高",
        "常見痛點": "公司估值高但流動性低；二次繳稅風險；子女接班不確定",
        "建議邏輯": "用保單補流動性，確保稅金與傳承金即時到位，避免賣股或稀釋控制權",
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
# 工具：brand.json / 圖片 data uri
# -----------------------------
def load_brand_config() -> Optional[dict]:
    for p in ["brand.json", os.path.join("familytree-main","brand.json"), os.path.join(os.path.dirname(__file__),"brand.json")]:
        if os.path.exists(p):
            try:
                return json.load(open(p, "r", encoding="utf-8"))
            except Exception:
                pass
    return None

def file_to_data_uri(file) -> Optional[str]:
    if not file: return None
    data = file.read()
    mime = "image/png"
    name = (file.name or "").lower()
    if name.endswith(".jpg") or name.endswith(".jpeg"): mime = "image/jpeg"
    elif name.endswith(".svg"): mime = "image/svg+xml"
    return f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"

def path_to_data_uri(path_or_none: Optional[str]) -> str:
    if not path_or_none or not os.path.exists(path_or_none): return ""
    mime = "image/png"
    lower = path_or_none.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"): mime = "image/jpeg"
    elif lower.endswith(".svg"): mime = "image/svg+xml"
    return f"data:{mime};base64,{base64.b64encode(open(path_or_none,'rb').read()).decode('utf-8')}"

# -----------------------------
# 稅務計算（示意）
# -----------------------------
def calc_estate_tax(tax_base: int) -> int:
    if tax_base <= 0: return 0
    for upper, rate, quick in TAIWAN_ESTATE_TAX_TABLE:
        if tax_base <= upper: return math.floor(tax_base * rate - quick)
    return 0

def simulate_with_without_insurance(total_assets: int, insurance_benefit: int) -> Dict[str, int]:
    total_assets = max(0, int(total_assets))
    insurance_benefit = max(0, int(insurance_benefit))
    tax_base = max(0, total_assets - BASIC_EXEMPTION)
    tax = calc_estate_tax(tax_base)
    cash_without = max(0, total_assets - tax)
    cash_with = max(0, total_assets - tax + insurance_benefit)
    return {
        "稅基": tax_base, "遺產稅": tax,
        "無保單_可用資金": cash_without,
        "有保單_可用資金": cash_with,
        "差異": cash_with - cash_without,
    }

# -----------------------------
# 報告 HTML（下載用，一頁式）
# -----------------------------
def build_summary_html(r: Dict[str, int], logo_src: str, contact_text: str,
                       scenario_title: Optional[str]=None, scenario_desc: Optional[dict]=None) -> str:
    contact_html = "<br/>".join((contact_text or "").split("\n"))
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
  </div>"""
    return f"""<!DOCTYPE html>
<html lang='zh-Hant'>
<head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>家族資產 × 策略摘要（示意）</title>
<style>
body {{ font-family: '{PAGE_FONT_FAMILY}','Noto Sans TC','Microsoft JhengHei','PingFang TC',sans-serif; line-height:1.6; padding:24px; }}
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
  <div class='brand'>{logo_img}<div><strong>《影響力》傳承策略平台｜永傳家族辦公室</strong></div></div>
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
# Session 狀態 & 品牌設定
# -----------------------------
if "demo_assets" not in st.session_state: st.session_state.demo_assets = {k: 0 for k in ASSET_CATS}
if "demo_used" not in st.session_state: st.session_state.demo_used = False
if "demo_selected_scenario" not in st.session_state: st.session_state.demo_selected_scenario = None
if "demo_brand_contact" not in st.session_state:
    st.session_state.demo_brand_contact = "永傳家族辦公室｜Grace Family Office\nhttps://gracefo.com\n123@gracefo.com"
if "demo_logo_data_uri" not in st.session_state: st.session_state.demo_logo_data_uri = None
if "demo_logo_url" not in st.session_state: st.session_state.demo_logo_url = ""

_brand = load_brand_config()
if _brand:
    contact = _brand.get("CONTACT")
    if contact: st.session_state.demo_brand_contact = contact
    for p in [_brand.get("LOGO_WIDE",""), _brand.get("LOGO_SQUARE",""),
              os.path.join("familytree-main", _brand.get("LOGO_WIDE","")),
              os.path.join("familytree-main", _brand.get("LOGO_SQUARE",""))]:
        if p and os.path.exists(p):
            st.session_state.demo_logo_data_uri = path_to_data_uri(p); break

# 側邊欄：品牌自訂
with st.sidebar:
    st.subheader("⚙️ 品牌設定（可選）")
    up = st.file_uploader("上傳 Logo（PNG/JPG/SVG）", type=["png","jpg","jpeg","svg"])
    if up: st.session_state.demo_logo_data_uri = file_to_data_uri(up)
    st.session_state.demo_logo_url = st.text_input("或填 Logo 網址（擇一即可）",
        value=st.session_state.demo_logo_url or "", placeholder="https://example.com/logo.png")
    st.session_state.demo_brand_contact = st.text_area("聯絡資訊（多行）",
        value=st.session_state.demo_brand_contact, height=90, help="每一行會在報告中換行顯示")

page_logo_src = st.session_state.demo_logo_data_uri or st.session_state.demo_logo_url
brand_contact_text = st.session_state.demo_brand_contact

# -----------------------------
# 頁面內容
# -----------------------------
# 標題：縮小一號並加粗（h2）
st.markdown(
    "<h2 style='font-weight:800; margin:0 0 4px 0;'>🧭 三步驟 Demo｜家族資產地圖 × 一鍵模擬 × 報告（簡化版）</h2>",
    unsafe_allow_html=True,
)
if page_logo_src: st.image(page_logo_src, width=150)
st.caption("3 分鐘看懂、5 分鐘產出成果。示意版，非正式稅務或法律建議。")
chips = ["① 建立資產地圖","② 一鍵模擬差異","③ 生成一頁摘要"]
c1,c2,c3 = st.columns(3)
for col, text in zip([c1,c2,c3], chips):
    with col:
        st.markdown(f'<div style="display:inline-block;padding:4px 10px;border-radius:999px;background:#eef;">{text}</div>', unsafe_allow_html=True)

st.divider()

# Step 1
st.subheader("① 建立家族資產地圖")
left,right = st.columns([1,1])
with left:
    st.write("輸入六大資產類別金額（新台幣）：")
    cA,cB = st.columns(2)
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

    s1,s2,s3 = st.columns(3)
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
    df = pd.DataFrame({"類別": list(assets.keys()), "金額": list(assets.values())})
    total_assets = int(df["金額"].sum())
    st.write("**資產分布**")
    if total_assets > 0:
        colors = ["#1F4A7A","#C99A2E","#4CAF50","#E64A19","#7E57C2","#455A64"][:len(df)]
        style = st.radio("圖表樣式", ["甜甜圈圖（建議）","圓餅圖"], horizontal=True, key="style_pie")
        sizes, labels = df["金額"].values, df["類別"].values
        fig, ax = plt.subplots(figsize=(6.8,5.2))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct=lambda p: f"{p:.1f}%" if p>=3 else "",
            startangle=90, colors=colors, pctdistance=0.75
        )
        ax.axis("equal")
        if style.startswith("甜甜圈"):
            ax.add_artist(plt.Circle((0,0), 0.55, fc="white"))
        if CHOSEN_MPL_FONT:
            prop = fm.FontProperties(family=CHOSEN_MPL_FONT, size=10)
            for t in autotexts: t.set_fontproperties(prop)
            for t in texts: t.set_fontproperties(prop)
        legend_labels = [f"{lbl}：NT$ {val:,.0f}" for lbl, val in zip(labels, sizes)]
        leg_prop = fm.FontProperties(family=CHOSEN_MPL_FONT, size=10) if CHOSEN_MPL_FONT else None
        title_prop = fm.FontProperties(family=CHOSEN_MPL_FONT, size=12) if CHOSEN_MPL_FONT else None
        ax.legend(wedges, legend_labels, title="資產類別", loc="center left", bbox_to_anchor=(1.02,0.5), prop=leg_prop)
        ax.set_title(f"資產分布　｜　總資產 NT$ {total_assets:,.0f}", loc="left", fontsize=12, pad=12, fontproperties=title_prop)
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("請輸入金額或先點『載入示範數據』。")
    st.metric("目前總資產 (NT$)", f"{total_assets:,.0f}")

st.divider()

# Step 2
st.subheader("② 一鍵模擬：有保單 vs 無保單")
pre_tax = calc_estate_tax(max(0, total_assets - BASIC_EXEMPTION)) if st.session_state.demo_used else 0
insurance_benefit = st.number_input(
    "預估保單理賠金（可調）", min_value=0, step=100_000, value=int(pre_tax),
    help="示意用途：假設理賠金直接提供給家人，可提高可動用現金。"
)
if st.button("⚡ 一鍵模擬差異"):
    r = simulate_with_without_insurance(total_assets, insurance_benefit)
    st.session_state.demo_result = {**r, "總資產": total_assets, "建議保額": insurance_benefit}
    st.success("模擬完成！")
    c1,c2 = st.columns(2)
    with c1:
        st.metric("稅基 (NT$)", f"{r['稅基']:,.0f}")
        st.metric("預估遺產稅 (NT$)", f"{r['遺產稅']:,.0f}")
    with c2:
        st.metric("無保單：可用資金 (NT$)", f"{r['無保單_可用資金']:,.0f}")
        st.metric("有保單：可用資金 (NT$)", f"{r['有保單_可用資金']:,.0f}")
    st.metric("差異（提升的可用現金）(NT$)", f"{r['差異']:,.0f}")
else:
    st.info("點擊『一鍵模擬差異』查看結果。")

st.caption("＊法稅提醒：此模擬僅為示意，實務須視受益人、給付方式與最新法令而定。")

st.divider()

# Step 3
st.subheader("③ 一頁摘要（可下載）")
r = st.session_state.get("demo_result")
if r:
    scenario_key = st.session_state.get("demo_selected_scenario")
    desc = SCENARIO_DESCRIPTIONS.get(scenario_key) if scenario_key else None

    # 內頁摘要（純 HTML，避免 $ 被 LaTeX 解析）
    summary_html = dedent(f"""\
<div class="summary" style="font-size:15px; line-height:1.9;">
  <p><strong>總資產</strong>：NT$ {r['總資產']:,.0f}</p>
  <p><strong>稅務簡估</strong></p>
  <ul>
    <li>稅基（總資產 − 基本免稅額 NT$ {BASIC_EXEMPTION:,.0f}）： <strong>NT$ {r['稅基']:,.0f}</strong></li>
    <li>預估遺產稅： <strong>NT$ {r['遺產稅']:,.0f}</strong></li>
  </ul>
  <p><strong>情境比較</strong></p>
  <ul>
    <li>無保單：可用資金 <strong>NT$ {r['無保單_可用資金']:,.0f}</strong></li>
    <li>有保單（理賠金 NT$ {r['建議保額']:,.0f}）：可用資金 <strong>NT$ {r['有保單_可用資金']:,.0f}</strong></li>
  </ul>
  <p><strong>差異</strong>：提升可動用現金 <strong>NT$ {r['差異']:,.0f}</strong></p>
  <blockquote style="color:#6b7280; font-size:13px;">本頁為示意，不構成稅務或法律建議；細節以專業顧問與最新法令為準。</blockquote>
</div>
""")
    if scenario_key and desc:
        summary_html += dedent(f"""\
<div style="margin-top:10px;">
  <p><strong>情境說明｜{scenario_key}</strong></p>
  <ul>
    <li>適用對象：{desc.get('適用對象','')}</li>
    <li>常見痛點：{desc.get('常見痛點','')}</li>
    <li>建議邏輯：{desc.get('建議邏輯','')}</li>
  </ul>
</div>
""")
    st.markdown(summary_html, unsafe_allow_html=True)

    # 下載：HTML（保底）
    logo_src = (st.session_state.demo_logo_data_uri or st.session_state.demo_logo_url or "")
    html = build_summary_html(r, logo_src=logo_src, contact_text=brand_contact_text,
                              scenario_title=scenario_key, scenario_desc=desc)
    st.download_button("⬇️ 下載一頁摘要（HTML，可列印成 PDF）", data=html,
                       file_name="家族資產_策略摘要_demo.html", mime="text/html")

    # 下載：PDF（沿用你專案的品牌 PDF 模組）
    if HAVE_BRANDED_PDF:
        story = []
        story.append(title("家族資產 × 策略摘要（示意）"))
        story.append(spacer(8))

        # KPI 區
        story.append(p(f"總資產：NT$ {r['總資產']:,.0f}"))
        story.append(p(f"稅基：NT$ {r['稅基']:,.0f}"))
        story.append(p(f"預估遺產稅：NT$ {r['遺產稅']:,.0f}"))
        story.append(p(f"建議保額：NT$ {r['建議保額']:,.0f}"))
        story.append(spacer(6))

        # 情境比較（表格；若失敗自動退回段落）
        headers = ["情境", "可用資金"]
        rows = [
            ["無保單", f"NT$ {r['無保單_可用資金']:,.0f}"],
            ["有保單（理賠金）", f"NT$ {r['有保單_可用資金']:,.0f}"],
            ["差異（提升現金）", f"NT$ {r['差異']:,.0f}"],
        ]
        try:
            story.append(table_compat(headers, rows, widths=[0.35, 0.65]))
        except Exception:
            story.append(p(f"無保單：NT$ {r['無保單_可用資金']:,.0f}"))
            story.append(p(f"有保單：NT$ {r['有保單_可用資金']:,.0f}"))
            story.append(p(f"差異：NT$ {r['差異']:,.0f}"))
        story.append(spacer(6))

        # 情境說明
        if scenario_key and desc:
            story.append(h2(f"情境說明｜{scenario_key}"))
            story.append(p(f"適用對象：{desc.get('適用對象','')}"))
            story.append(p(f"常見痛點：{desc.get('常見痛點','')}"))
            story.append(p(f"建議邏輯：{desc.get('建議邏輯','')}"))
            story.append(spacer(4))

        story.append(p("備註：本頁為示意，不構成稅務或法律建議；細節以專業顧問與最新法令為準。", style="small"))

        pdf_bytes = build_branded_pdf_bytes(story)  # 由內建模組注入品牌頁首/頁尾/LOGO
        st.download_button(
            "⬇️ 下載一頁摘要（PDF｜品牌頁首/頁尾）",
            data=pdf_bytes,
            file_name="家族資產_策略摘要_demo.pdf",
            mime="application/pdf",
        )
    else:
        st.caption("（偵測不到內建 PDF 模組：請確認 utils/pdf_utils.py 是否可被匯入）")
else:
    st.info("先完成上一步『一鍵模擬差異』，系統會自動生成摘要。")

st.write("---")
st.info("🚀 專業版：進階稅務模擬、更多情境比較、白標報告與客戶 Viewer。如需試用名單，請與我們聯繫。")

import streamlit as st
from datetime import datetime
from typing import List, Dict

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",     # 根目錄的方形 logo 作為 favicon
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Global Styles (CSS)
# =========================
BRAND_PRIMARY = "#1F4A7A"   # 專業藍
BRAND_ACCENT  = "#C99A2E"   # 溫暖金
BRAND_BG      = "#F7F9FB"   # 淺底
CARD_BG       = "white"

st.markdown(
    f"""
    <style>
      /* 全域字體與背景 */
      html, body, [class*="css"]  {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
        background-color: {BRAND_BG};
      }}
      /* 讓主容器更寬鬆 */
      .main > div {{
        padding-top: 0.5rem;
        padding-bottom: 2rem;
      }}
      /* 標題風格 */
      .title-xl {{
        font-size: 40px;
        font-weight: 800;
        letter-spacing: 0.2px;
        line-height: 1.2;
        color: {BRAND_PRIMARY};
        margin: 0 0 10px 0;
      }}
      .subtitle {{
        font-size: 18px;
        color: #334155;
        margin-bottom: 24px;
      }}
      /* Hero 區塊 */
      .hero {{
        border-radius: 18px;
        padding: 40px;
        background: radial-gradient(1000px 400px at 10% 10%, #ffffff 0%, #f3f6fa 45%, #eef2f7 100%);
        border: 1px solid #e6eef5;
        box-shadow: 0 6px 18px rgba(10, 18, 50, 0.04);
      }}
      .hero .badge {{
        display: inline-block;
        background: {BRAND_PRIMARY};
        color: white;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 12px;
        letter-spacing: .5px;
        margin-bottom: 12px;
      }}
      .hero-cta {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }}
      .btn-primary {{
        background: {BRAND_PRIMARY};
        color: white !important;
        padding: 10px 16px;
        border-radius: 12px;
        text-decoration: none !important;
        font-weight: 700;
        border: 1px solid {BRAND_PRIMARY};
      }}
      .btn-ghost {{
        background: white;
        color: {BRAND_PRIMARY} !important;
        padding: 10px 16px;
        border-radius: 12px;
        text-decoration: none !important;
        font-weight: 700;
        border: 1px solid #cfdae6;
      }}
      /* 卡片 */
      .card {{
        background: {CARD_BG};
        border-radius: 16px;
        padding: 18px;
        border: 1px solid #e8eef5;
        box-shadow: 0 8px 16px rgba(17, 24, 39, 0.04);
        height: 100%;
      }}
      .card h4 {{
        margin: 6px 0 6px 0;
        color: {BRAND_PRIMARY};
        font-weight: 800;
      }}
      .muted {{
        color: #64748b;
        font-size: 14px;
        line-height: 1.5;
      }}
      /* 分隔小標 */
      .section-title {{
        font-weight: 900;
        letter-spacing: .4px;
        color: #0f172a;
        margin: 20px 0 8px 0;
      }}
      /* 頂部標籤導航（模擬 tab 的視覺） */
      .topnav {{
        display: flex;
        gap: 8px;
        margin: 10px 0 18px 0;
        flex-wrap: wrap;
      }}
      .pill {{
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid #e2e8f0;
        color: #0f172a;
        font-size: 13px;
        text-decoration: none;
        background: #fff;
      }}
      .pill.active {{
        border-color: {BRAND_ACCENT};
        color: #1f2937;
        background: #fff7e6;
      }}
      /* 頁尾 */
      .footer {{
        color: #6b7280;
        font-size: 13px;
        margin-top: 6px;
      }}
      /* 隱藏 Streamlit 預設頁面標題空白 */
      header[data-testid="stHeader"] {{
        background: transparent;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Helpers
# =========================
def top_brand_bar():
    col1, col2 = st.columns([1, 5], vertical_alignment="center")
    with col1:
        st.image("logo.png", use_container_width=True)  # 橫式 Logo
    with col2:
        st.markdown(
            f"""
            <div style="text-align:right;">
              <span class="muted">《影響力》傳承策略平台｜永傳家族辦公室</span>
            </div>
            """,
            unsafe_allow_html=True
        )

def top_tabs(active: str):
    tabs = [
        ("home", "首頁 Home"),
        ("legacy", "傳承地圖"),
        ("tax", "稅務試算"),
        ("policy", "保單策略"),
        ("values", "價值觀探索"),
        ("about", "關於 / 聯絡"),
    ]
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    for key, label in tabs:
        cls = "pill active" if key == active else "pill"
        # 使用 query params 切換
        href = f"?page={key}"
        st.markdown(f'<a class="{cls}" href="{href}">{label}</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def cta_buttons():
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("🚀 立即體驗 Demo", use_container_width=True, type="primary"):
            st.query_params.update({"page": "legacy"})
            st.rerun()
    with c2:
        if st.button("📞 預約顧問 / 合作洽談", use_container_width=True):
            st.query_params.update({"page": "about"})
            st.rerun()

def feature_card(title: str, desc: str, emoji: str):
    st.markdown(
        f"""
        <div class="card">
          <div style="font-size:26px">{emoji}</div>
          <h4>{title}</h4>
          <div class="muted">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def left_nav():
    st.markdown("### 功能導覽")
    st.markdown("- 🔰 首頁總覽")
    st.markdown("- 🗺️ 傳承地圖（家族與資產視覺）")
    st.markdown("- 💰 稅務試算（遺產/贈與）")
    st.markdown("- 🧩 保單策略（放大與現金流）")
    st.markdown("- ❤️ 價值觀探索（情感連結）")
    st.markdown("- 🤝 關於我們與聯絡")
    st.divider()
    st.caption("小提醒：左側與頂部導覽都可切換頁面。")

# =========================
# Pages
# =========================
def page_home():
    top_tabs("home")
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="badge">AI 傳承教練</div>', unsafe_allow_html=True)
    st.markdown('<div class="title-xl">10 分鐘完成高資產家族 10 年的傳承規劃</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">專業 × 快速 × 可信任｜將法稅知識、保單策略與家族價值觀整合為行動方案，幫助顧問有效成交、幫助家庭安心決策。</div>',
        unsafe_allow_html=True
    )
    cta_buttons()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 核心功能")
    c1, c2, c3 = st.columns(3)
    with c1:
        feature_card("AI 傳承地圖", "以家族成員與資產六大類為主軸，快速產出「可視化傳承地圖」，成為顧問面談神器。", "🗺️")
    with c2:
        feature_card("稅務試算引擎", "即時計算遺產/贈與稅，套用本土化稅表與扣除規則，支援情境比較。", "🧮")
    with c3:
        feature_card("保單策略模擬", "以現金流與保額放大視角，模擬終身壽/美元儲蓄等方案的傳承效益。", "📦")

    c4, c5, c6 = st.columns(3)
    with c4:
        feature_card("價值觀探索", "把『想留給誰、怎麼留』說清楚，讓數字與情感同向，降低家族溝通阻力。", "❤️")
    with c5:
        feature_card("一鍵提案", "將分析結果匯整成客製化提案（章節化重點＋行動清單），提升成交通關率。", "📝")
    with c6:
        feature_card("合規與專業庫", "內建合規規則與知識庫，結合律師/會計師/保經顧問實務，降低風險。", "🛡️")

    st.markdown("#### 服務對象")
    s1, s2 = st.columns(2)
    with s1:
        feature_card("B2B2C｜專業顧問", "保險顧問、財稅顧問、家族辦公室：10 分鐘生成專業提案，提升效率與專業度。", "🏢")
    with s2:
        feature_card("B2C｜高資產家庭", "企業主與高資產家庭：以簡單明確的決策畫面，讓複雜傳承更安心。", "👨‍👩‍👧‍👦")

def page_legacy_map():
    top_tabs("legacy")
    st.subheader("🗺️ 傳承地圖（示範表單）")
    st.caption("目標：快速輸入關鍵資訊，產出『家族＋資產』的可視化地圖與行動重點。")

    with st.form("legacy_form"):
        st.markdown("**一、家族成員**")
        col1, col2, col3 = st.columns(3)
        with col1:
            family_name = st.text_input("家族姓氏 / 家族名（可選）", value="")
            patriarch   = st.text_input("主要決策者（例：李先生）", value="")
        with col2:
            spouse      = st.text_input("配偶（例：王女士）", value="")
            heirs       = st.text_input("子女 / 繼承人（逗號分隔）", value="")
        with col3:
            guardians   = st.text_input("監護/信託受託人（可選）", value="")

        st.markdown("**二、資產六大類（概略）**")
        a1, a2, a3 = st.columns(3)
        with a1:
            equity = st.text_input("公司股權（例：A公司60%）", value="")
            re_est = st.text_input("不動產（例：台北信義住辦）", value="")
        with a2:
            finance = st.text_input("金融資產（例：存款/股票/基金）", value="")
            policy  = st.text_input("保單（例：終身壽3000萬）", value="")
        with a3:
            offshore = st.text_input("海外資產（例：香港帳戶）", value="")
            others   = st.text_input("其他資產（例：藝術品）", value="")

        st.markdown("**三、特殊考量**")
        c1, c2 = st.columns(2)
        with c1:
            cross_border = st.checkbox("涉及跨境（台灣/大陸/美國等）", value=False)
            special_needs = st.checkbox("受扶養/身心狀況考量", value=False)
        with c2:
            fairness = st.selectbox("公平原則偏好", ["平均分配", "依需求與責任", "結合股權設計"], index=1)
            governance = st.selectbox("治理工具偏好", ["遺囑", "信託", "保單＋信託", "控股結構"], index=2)

        submitted = st.form_submit_button("生成傳承地圖與行動重點")
    if submitted:
        st.success("✅ 已生成！以下為示意輸出：")
        colA, colB = st.columns([1,1])
        with colA:
            st.markdown("##### 家族結構（摘要）")
            st.write(f"- 決策者：{patriarch or '（未填）'} / 配偶：{spouse or '（未填）'}")
            st.write(f"- 子女/繼承人：{heirs or '（未填）'}")
            st.write(f"- 監護/受託：{guardians or '（未填）'}")
            st.write("---")
            st.markdown("##### 資產分類（六大）")
            st.write(f"- 公司股權：{equity or '未填'}")
            st.write(f"- 不動產：{re_est or '未填'}")
            st.write(f"- 金融資產：{finance or '未填'}")
            st.write(f"- 保單：{policy or '未填'}")
            st.write(f"- 海外資產：{offshore or '未填'}")
            st.write(f"- 其他：{others or '未填'}")
        with colB:
            st.markdown("##### 建議工具與原則")
            st.write(f"- 公平原則：{fairness}")
            st.write(f"- 治理工具：{governance}")
            if cross_border:
                st.info("🌏 涉及跨境：建議先確認各地稅籍與資產所在地法律，優先處理稅務居民與扣繳風險。")
            if special_needs:
                st.warning("💛 特殊照護：建議設計專款與監護安排，避免資產被誤用。")
            st.markdown("##### 行動清單（示例）")
            st.write("- (1) 彙整資產明細與估值、確認持有人與所在地")
            st.write("- (2) 初步試算遺產/贈與稅，先看『稅務黑洞』")
            st.write("- (3) 擬定保單＋信託配置，確保現金流與公平性")
            st.write("- (4) 規劃股權與公司治理，避免營運權與所有權衝突")

def page_tax():
    top_tabs("tax")
    st.subheader("🧮 稅務試算（示範版）")
    st.caption("此為介面示意：後續可接入您既有的稅表與規則引擎。")
    col1, col2, col3 = st.columns(3)
    with col1:
        estate_base = st.number_input("遺產總額 (TWD)", min_value=0, value=120_000_000, step=1_000_000)
        funeral     = st.number_input("喪葬費（上限 1,380,000）", min_value=0, value=1_380_000, step=10_000)
    with col2:
        spouse_ded  = st.number_input("配偶扣除（5,530,000）", min_value=0, value=5_530_000, step=10_000)
        basic_ex    = st.number_input("基本免稅（13,330,000）", min_value=0, value=13_330_000, step=10_000)
    with col3:
        dependents  = st.number_input("受扶養人數（直系卑親屬每人 560,000）", min_value=0, value=2, step=1)
        disabled    = st.number_input("身心障礙人數（每人 6,930,000）", min_value=0, value=0, step=1)

    # 簡化示範：計算課稅基礎與級距（請依實務替換正式稅表）
    total_deductions = (
        min(funeral, 1_380_000)
        + spouse_ded
        + basic_ex
        + dependents * 560_000
        + disabled * 6_930_000
    )
    taxable = max(0, estate_base - total_deductions)

    def tax_calc(amount: int) -> Dict[str, int]:
        # 示範級距（請以正式表替換；支援速算扣除）
        if amount <= 56_210_000:
            rate, quick = 0.10, 0
        elif amount <= 112_420_000:
            rate, quick = 0.15, 2_810_000
        else:
            rate, quick = 0.20, 8_430_000
        tax = int(amount * rate - quick)
        return {"rate": int(rate * 100), "quick": quick, "tax": max(tax, 0)}

    result = tax_calc(taxable)

    st.markdown("#### 試算結果")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("可扣除總額", f"{total_deductions:,.0f}")
    r2.metric("課稅基礎", f"{taxable:,.0f}")
    r3.metric("適用稅率", f"{result['rate']}%")
    r4.metric("預估應納稅額", f"{result['tax']:,.0f}")

    st.caption("※ 最終結果仍需以正式稅表、扣除額與個案事實為準。此為示意介面。")

def page_policy():
    top_tabs("policy")
    st.subheader("📦 保單策略（示範版）")
    st.caption("以『保額放大 × 現金流』角度模擬，支援 6/7/10 年繳、美元或台幣等。")
    col1, col2 = st.columns([1,1])
    with col1:
        premium = st.number_input("年繳保費", min_value=0, value=1_000_000, step=50_000)
        years   = st.selectbox("繳費期間", [6, 7, 10, 12, 20])
        ccy     = st.selectbox("幣別", ["TWD", "USD"])
    with col2:
        target  = st.selectbox("策略目標", ["放大財富傳承", "補足遺產稅", "退休現金流", "企業風險隔離"])
        rate    = st.slider("假設內部報酬率 IRR（示意）", 1.0, 6.0, 3.0, 0.1)

    # 非精算：僅示意保額/現金值估算（後續可接您既有計算模組）
    total_premium = premium * years
    indicative_face = int(total_premium * (18 if target == "放大財富傳承" else 12))
    cash_value_10y = int(total_premium * (1 + rate/100) ** 10)

    st.markdown("#### 估算摘要（示意）")
    s1, s2, s3 = st.columns(3)
    s1.metric("總保費", f"{total_premium:,.0f} {ccy}")
    s2.metric("估計身故保額", f"{indicative_face:,.0f} {ccy}")
    s3.metric("10年估計現金值", f"{cash_value_10y:,.0f} {ccy}")
    st.caption("※ 以上為介面示意，實務請接保單商品真實數據與精算假設。")

def page_values():
    top_tabs("values")
    st.subheader("❤️ 價值觀探索（示範版）")
    st.caption("把家族的愛與信念先說清楚，工具與資金配置才會同向。")
    cols = st.columns(3)
    with cols[0]:
        v1 = st.multiselect("想優先照顧", ["配偶", "子女", "父母", "夥伴", "公益"], default=["子女","配偶"])
    with cols[1]:
        v2 = st.multiselect("重要原則", ["公平", "感恩", "責任", "創新", "永續"], default=["公平","責任"])
    with cols[2]:
        v3 = st.multiselect("傳承方式", ["等分", "需求導向", "信託分期", "股權分流"], default=["信託分期","股權分流"])

    st.markdown("#### 探索摘要（示意）")
    st.write(f"- 優先照顧：{', '.join(v1) if v1 else '（未選）'}")
    st.write(f"- 重要原則：{', '.join(v2) if v2 else '（未選）'}")
    st.write(f"- 傳承方式：{', '.join(v3) if v3 else '（未選）'}")
    st.info("建議：將價值觀轉譯為行動規則（例如：『不動產留長子、金融資產分期信託給長女與次女』），再連結到稅務與保單策略。")

def page_about():
    top_tabs("about")
    st.subheader("🤝 關於我們 / 聯絡")
    st.markdown(
        f"""
        **永傳家族辦公室（Grace Family Office）**  
        我們整合律師、會計師、財稅與保險專家，用 AI 工具把複雜變簡單，陪伴家庭安心決策。
        """
    )
    col1, col2 = st.columns([1,1])
    with col1:
        name = st.text_input("您的稱呼 *", "")
        email = st.text_input("Email *", "")
        phone = st.text_input("電話（可選）", "")
        topic = st.selectbox("想了解的主題", ["體驗平台 Demo", "企業接班與股權", "遺產/贈與稅", "保單策略", "其它"])
    with col2:
        when_date = st.date_input("期望日期", value=None)
        when_ampm = st.selectbox("時段偏好", ["不限", "上午", "下午"], index=0)
        msg = st.text_area("想說的話（選填）", height=120)
        if st.button("送出需求", type="primary"):
            st.success("已收到，我們會盡快與您聯繫。謝謝！")

    st.divider()
    st.caption("《影響力》傳承策略平台｜永傳家族辦公室｜https://gracefo.com｜聯絡信箱：123@gracefo.com")

# =========================
# Sidebar (Left)
# =========================
with st.sidebar:
    st.image("logo2.png", width=64)
    st.markdown("### 影響力｜AI 傳承規劃平台")
    st.caption("專業 × 快速 × 可信任")
    left_nav()
    st.markdown("---")
    st.markdown("**快速前往**")
    if st.button("🔸 傳承地圖", use_container_width=True):
        st.query_params.update({"page": "legacy"}); st.rerun()
    if st.button("🔸 稅務試算", use_container_width=True):
        st.query_params.update({"page": "tax"}); st.rerun()
    if st.button("🔸 保單策略", use_container_width=True):
        st.query_params.update({"page": "policy"}); st.rerun()
    if st.button("🔸 價值觀探索", use_container_width=True):
        st.query_params.update({"page": "values"}); st.rerun()
    if st.button("🔸 關於 / 聯絡", use_container_width=True):
        st.query_params.update({"page": "about"}); st.rerun()

# =========================
# Top Brand Bar
# =========================
top_brand_bar()

# =========================
# Router by Query Params
# =========================
q = st.query_params
page = (q.get("page") or ["home"])
page = page[0] if isinstance(page, list) else page

if page == "home":
    page_home()
elif page == "legacy":
    page_legacy_map()
elif page == "tax":
    page_tax()
elif page == "policy":
    page_policy()
elif page == "values":
    page_values()
elif page == "about":
    page_about()
else:
    page_home()

# =========================
# Footer
# =========================
st.markdown(
    f"""
    <div class="footer">
      《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}
    </div>
    """,
    unsafe_allow_html=True
)

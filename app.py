# app.py
import streamlit as st
from datetime import datetime, date
from typing import Dict, List
import math

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",   # 根目錄方形 logo 作為 favicon
    layout="wide",
    initial_sidebar_state="expanded",
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
      html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
        background-color: {BRAND_BG};
      }}
      .main > div {{
        padding-top: 0.5rem;
        padding-bottom: 2rem;
      }}
      .hero {{
        border-radius: 18px;
        padding: 40px;
        background: radial-gradient(1000px 400px at 10% 10%, #ffffff 0%, #f3f6fa 45%, #eef2f7 100%);
        border: 1px solid #e6eef5;
        box-shadow: 0 6px 18px rgba(10, 18, 50, 0.04);
      }}
      .title-xl {{
        font-size: 40px; font-weight: 800; color: {BRAND_PRIMARY}; margin: 0 0 10px 0;
      }}
      .subtitle {{
        font-size: 18px; color: #334155; margin-bottom: 24px;
      }}
      .card {{
        background: {CARD_BG}; border-radius: 16px; padding: 18px;
        border: 1px solid #e8eef5; box-shadow: 0 8px 16px rgba(17,24,39,.04); height: 100%;
      }}
      .card h4 {{ margin: 6px 0; color: {BRAND_PRIMARY}; font-weight: 800; }}
      .muted {{ color: #64748b; font-size: 14px; line-height: 1.5; }}
      .chip {{ display:inline-block; padding:6px 10px; border-radius:999px; border:1px solid #e2e8f0; margin-right:6px; margin-bottom:6px; font-size: 12px; }}
      header[data-testid="stHeader"] {{ background: transparent; }}
      .footer {{ color:#6b7280; font-size:13px; margin-top: 20px; }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Utilities
# =========================
def navigate(page_key: str):
    st.query_params.update({"page": page_key})
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

# --- Taiwan tax tables (示意，請依官方最新規定更新) ---
ESTATE_BRACKETS = [
    # (上限, 稅率, 速算扣除)
    (56_210_000, 0.10, 0),
    (112_420_000, 0.15, 2_810_000),
    (10**15, 0.20, 8_430_000),  # 大數作為上界
]

GIFT_BRACKETS = [
    (28_110_000, 0.10, 0),
    (56_210_000, 0.15, 1_405_000),
    (10**15,     0.20, 5_621_000),
]

def apply_brackets(amount: int, brackets: List[tuple]) -> Dict[str, int]:
    for ceiling, rate, quick in brackets:
        if amount <= ceiling:
            tax = max(int(amount * rate - quick), 0)
            return {"rate": int(rate * 100), "quick": quick, "tax": tax}
    return {"rate": 0, "quick": 0, "tax": 0}

# =========================
# Pages
# =========================
def page_home():
    # 頂部品牌列（僅 Logo + 右上標語）
    top = st.columns([1, 5])
    with top[0]:
        st.image("logo.png", use_container_width=True)
    with top[1]:
        st.markdown(
            '<div style="text-align:right;" class="muted">《影響力》傳承策略平台｜永傳家族辦公室</div>',
            unsafe_allow_html=True
        )

    # Hero
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="title-xl">10 分鐘完成高資產家族 10 年的傳承規劃</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">專業 × 快速 × 可信任｜將法稅知識、保單策略與家族價值觀整合為行動方案，幫助顧問有效成交、幫助家庭安心決策。</div>',
        unsafe_allow_html=True
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 開始建立傳承地圖", type="primary", use_container_width=True):
            navigate("legacy")
    with c2:
        if st.button("📞 預約顧問 / 合作洽談", use_container_width=True):
            navigate("about")
    st.markdown('</div>', unsafe_allow_html=True)

    # 功能
    st.markdown("#### 核心功能")
    a, b, c = st.columns(3)
    with a:
        feature_card("AI 傳承地圖", "家族 + 六大資產快速建模，輸出『行動清單』與提案。", "🗺️")
    with b:
        feature_card("稅務試算引擎", "遺產/贈與稅即時估算，支援速算扣除與情境比較。", "🧮")
    with c:
        feature_card("保單策略模擬", "以『保額放大 × 現金流』視角做策略對齊。", "📦")

    d, e = st.columns(2)
    with d:
        feature_card("價值觀探索", "把想留給誰、如何留先說清楚；讓數字與情感同向。", "❤️")
    with e:
        feature_card("一鍵提案下載", "將結論匯整為可分享的提案摘要，方便後續跟進。", "📝")

def page_legacy_map():
    st.subheader("🗺️ 傳承地圖（輸入 → 摘要 → 可視化）")
    st.caption("輸入家族成員與資產概況，生成摘要、行動重點與提案下載。")

    with st.form("legacy_form"):
        st.markdown("**一、家族成員**")
        c1, c2, c3 = st.columns(3)
        with c1:
            family_name = st.text_input("家族名稱（可選）", "")
            patriarch   = st.text_input("主要決策者（例：李先生）", "")
        with c2:
            spouse      = st.text_input("配偶（例：王女士）", "")
            heirs_raw   = st.text_input("子女 / 繼承人（逗號分隔）", "長子,長女")
        with c3:
            trustees    = st.text_input("受託/監護安排（可選）", "")

        st.markdown("**二、資產六大類（概略金額）**")
        a1, a2, a3 = st.columns(3)
        with a1:
            equity   = st.text_input("公司股權", "A公司60%")
            re_est   = st.text_input("不動產", "台北信義住辦")
        with a2:
            finance  = st.text_input("金融資產", "現金、股票、基金")
            policy   = st.text_input("保單", "終身壽 3000 萬")
        with a3:
            offshore = st.text_input("海外資產", "香港帳戶")
            others   = st.text_input("其他資產", "藝術品")

        st.markdown("**三、原則與工具偏好**")
        b1, b2 = st.columns(2)
        with b1:
            fairness   = st.selectbox("公平原則", ["平均分配", "依需求與責任", "結合股權設計"], index=1)
            cross      = st.checkbox("涉及跨境（台灣/大陸/美國等）", value=False)
        with b2:
            governance = st.selectbox("治理工具偏好", ["遺囑", "信託", "保單＋信託", "控股結構"], index=2)
            special    = st.checkbox("特殊照護（身心/學習/監護）", value=False)

        submitted = st.form_submit_button("✅ 生成傳承地圖摘要")
    if not submitted:
        st.info("請輸入上方資訊，點擊「生成傳承地圖摘要」。")
        return

    heirs = [h.strip() for h in heirs_raw.split(",") if h.strip()]
    st.success("已生成摘要：")

    colA, colB = st.columns([1,1])
    with colA:
        st.markdown("##### 家族結構（摘要）")
        st.write(f"- 家族：{family_name or '（未填）'}")
        st.write(f"- 決策者：{patriarch or '（未填）'} / 配偶：{spouse or '（未填）'}")
        st.write(f"- 子女/繼承人：{', '.join(heirs) if heirs else '（未填）'}")
        st.write(f"- 受託/監護：{trustees or '（未填）'}")
        st.markdown("---")
        st.markdown("##### 資產分類（六大）")
        st.write(f"- 公司股權：{equity or '未填'}")
        st.write(f"- 不動產：{re_est or '未填'}")
        st.write(f"- 金融資產：{finance or '未填'}")
        st.write(f"- 保單：{policy or '未填'}")
        st.write(f"- 海外資產：{offshore or '未填'}")
        st.write(f"- 其他資產：{others or '未填'}")

    with colB:
        st.markdown("##### 建議原則與工具")
        st.write(f"- 公平原則：{fairness}")
        st.write(f"- 治理工具：{governance}")
        if cross:
            st.info("🌏 涉及跨境：優先釐清稅籍、資產所在地、扣繳義務與外匯管制。")
        if special:
            st.warning("💛 特殊照護：建議設立專用信託/保單金專款與監護人設計。")
        st.markdown("##### 行動清單（建議）")
        st.write("- ① 彙整資產明細與估值，標註持有人/所在地/負債。")
        st.write("- ② 初步試算遺產/贈與稅，評估是否需預留稅源。")
        st.write("- ③ 依公平原則與治理工具，設計分配與監督機制（如信託分期）。")
        st.write("- ④ 以保單＋信託搭配建立流動性，確保『現金到位、爭議降低』。")

    # --- 簡易可視化（Graphviz） ---
    try:
        import graphviz
        dot = graphviz.Digraph()
        root = patriarch or "主要決策者"
        dot.node("P", root, shape="box", style="rounded,filled", color=BRAND_PRIMARY, fillcolor="#E7F0FB")
        if spouse:
            dot.node("S", spouse, shape="box", style="rounded,filled", color=BRAND_PRIMARY, fillcolor="#E7F0FB")
            dot.edge("P", "S", label="配偶")
        for i, h in enumerate(heirs):
            nid = f"H{i}"
            dot.node(nid, h, shape="ellipse", style="filled", fillcolor="#FFF7E6", color=BRAND_ACCENT)
            dot.edge("P", nid, label="子女/繼承")
        # Assets 挂在 P 底下
        assets = [("A1","公司股權",equity),("A2","不動產",re_est),("A3","金融資產",finance),
                  ("A4","保單",policy),("A5","海外資產",offshore),("A6","其他資產",others)]
        for aid, label, val in assets:
            label_txt = f"{label}\\n{val}" if val else label
            dot.node(aid, label_txt, shape="folder", style="filled", fillcolor="white", color="#9aa7b1")
            dot.edge("P", aid)
        st.markdown("##### 可視化傳承地圖（示意）")
        st.graphviz_chart(dot)
    except Exception:
        st.caption("（若未安裝 graphviz，將僅顯示摘要與清單）")

    # --- 生成提案摘要下載 ---
    proposal = []
    proposal.append(f"# {family_name or '家族'} 傳承規劃摘要（示意）\n")
    proposal.append(f"**決策者**：{patriarch or '未填'}　**配偶**：{spouse or '未填'}\n")
    proposal.append(f"**繼承人**：{', '.join(heirs) if heirs else '未填'}\n")
    proposal.append(f"**受託/監護**：{trustees or '未填'}\n")
    proposal.append("## 資產六大\n")
    for label, val in [("公司股權",equity),("不動產",re_est),("金融資產",finance),
                       ("保單",policy),("海外資產",offshore),("其他資產",others)]:
        proposal.append(f"- {label}：{val or '未填'}")
    proposal.append("\n## 原則與工具\n")
    proposal.append(f"- 公平原則：{fairness}")
    proposal.append(f"- 治理工具：{governance}")
    if cross:   proposal.append("- 涉及跨境：需先釐清稅籍/所在地/扣繳義務。")
    if special: proposal.append("- 特殊照護：建議專款信託與監護人安排。")
    proposal.append("\n## 行動清單（建議）\n- 彙整資產並初步試算稅負\n- 設計分配與監督機制\n- 以保單＋信託建立流動性\n")

    st.download_button(
        "⬇️ 下載提案摘要（Markdown）",
        data="\n".join(proposal).encode("utf-8"),
        file_name=f"{(family_name or 'family')}_proposal_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )

def page_tax():
    st.subheader("🧮 稅務試算")
    tabs = st.tabs(["遺產稅試算", "贈與稅試算"])

    # -------- Estate --------
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        with c1:
            estate_base = st.number_input("遺產總額 (TWD)", min_value=0, value=120_000_000, step=1_000_000)
            funeral     = st.number_input("喪葬費（上限 1,380,000）", min_value=0, value=1_380_000, step=10_000)
        with c2:
            spouse_ded  = st.number_input("配偶扣除（5,530,000）", min_value=0, value=5_530_000, step=10_000)
            basic_ex    = st.number_input("基本免稅（13,330,000）", min_value=0, value=13_330_000, step=10_000)
        with c3:
            dep_lineal  = st.number_input("直系卑親屬人數（每人 560,000）", min_value=0, value=2, step=1)
            disabled    = st.number_input("身心障礙人數（每人 6,930,000）", min_value=0, value=0, step=1)

        # 其他扣除（選用）
        more = st.expander("更多扣除選項（可選）", expanded=False)
        with more:
            asc_lineal  = st.number_input("直系尊親屬（最多2人，每人 1,380,000）", min_value=0, value=0, step=1)
            other_dep   = st.number_input("其他受扶養人數（每人 560,000）", min_value=0, value=0, step=1)

        total_deductions = (
            min(funeral, 1_380_000) +
            spouse_ded +
            basic_ex +
            dep_lineal * 560_000 +
            min(asc_lineal, 2) * 1_380_000 +
            other_dep * 560_000 +
            disabled * 6_930_000
        )
        taxable = max(0, int(estate_base - total_deductions))
        result = apply_brackets(taxable, ESTATE_BRACKETS)

        st.markdown("#### 結果")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("可扣除總額", f"{total_deductions:,.0f}")
        r2.metric("課稅基礎", f"{taxable:,.0f}")
        r3.metric("適用稅率", f"{result['rate']}%")
        r4.metric("預估應納稅額", f"{result['tax']:,.0f}")
        st.caption("※ 為示意介面；最終仍以官方規定與個案事實為準。")

    # -------- Gift --------
    with tabs[1]:
        g1, g2, g3 = st.columns(3)
        with g1:
            gift_total = st.number_input("本年贈與總額 (TWD)", min_value=0, value=10_000_000, step=500_000)
            annual_ex  = st.number_input("每年基本免稅", min_value=0, value=2_440_000, step=10_000)
        with g2:
            pay_by     = st.selectbox("納稅義務人", ["贈與人", "受贈人"], index=0)
            donees     = st.number_input("受贈人數（統計用途）", min_value=1, value=1, step=1)
        with g3:
            note       = st.text_input("備註（可填用途/安排）", "")

        gift_taxable = max(0, int(gift_total - annual_ex))
        g_result = apply_brackets(gift_taxable, GIFT_BRACKETS)

        st.markdown("#### 結果")
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("贈與總額", f"{gift_total:,.0f}")
        x2.metric("免稅額", f"{annual_ex:,.0f}")
        x3.metric("課稅基礎", f"{gift_taxable:,.0f}")
        x4.metric("預估應納稅額", f"{g_result['tax']:,.0f}")
        st.caption("※ 示意級距：0–28,110,000 (10%)；28,110,001–56,210,000 (15%, 速算 1,405,000)；56,210,001 以上 (20%, 速算 5,621,000)。")

def page_policy():
    st.subheader("📦 保單策略模擬（示範版）")
    st.caption("以『保額放大 × 現金流』角度進行粗估，實務請接商品真實數據與精算假設。")

    c1, c2 = st.columns(2)
    with c1:
        premium = st.number_input("年繳保費", min_value=0, value=1_000_000, step=50_000)
        years   = st.selectbox("繳費期間（年）", [6, 7, 10, 12, 20], index=0)
        currency= st.selectbox("幣別", ["TWD", "USD"], index=0)
    with c2:
        goal    = st.selectbox("策略目標", ["放大財富傳承", "補足遺產稅", "退休現金流", "企業風險隔離"], index=0)
        irr     = st.slider("假設內部報酬率 IRR（示意）", 1.0, 6.0, 3.0, 0.1)

    total_premium = premium * years
    # 簡化：不同目標給不同放大倍數（僅示意）
    face_mult = {"放大財富傳承":18, "補足遺產稅":14, "退休現金流":10, "企業風險隔離":12}[goal]
    indicative_face = int(total_premium * face_mult)
    # 現金值估算（複利示意）
    cv_10y = int(total_premium * (1 + irr/100)**10)

    st.markdown("#### 估算摘要")
    s1, s2, s3 = st.columns(3)
    s1.metric("總保費", f"{total_premium:,.0f} {currency}")
    s2.metric("估計身故保額", f"{indicative_face:,.0f} {currency}")
    s3.metric("10 年估計現金值", f"{cv_10y:,.0f} {currency}")

    st.markdown("#### 年度現金流示意")
    years_range = list(range(1, years+1))
    cash_out = [-premium for _ in years_range]
    cum_out  = [sum(cash_out[:i]) for i in range(1, years+1)]
    tbl = "| 年度 | 保費現金流 | 累計現金流 |\n|---:|---:|---:|\n" + \
          "\n".join([f"| {y} | {cash_out[y-1]:,} | {cum_out[y-1]:,} |" for y in years_range])
    st.markdown(tbl)

    summary = f"""# 保單策略摘要（示意）
- 策略目標：{goal}
- 年繳保費：{premium:,} {currency} × {years} 年
- 估計身故保額：{indicative_face:,} {currency}
- 10 年估計現金值（IRR {irr:.1f}%）：{cv_10y:,} {currency}
"""
    st.download_button(
        "⬇️ 下載保單策略摘要（Markdown）",
        data=summary.encode("utf-8"),
        file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )

def page_values():
    st.subheader("❤️ 價值觀探索（產出行動準則）")
    st.caption("把價值觀轉譯為可執行的『家規』與資金配置原則，降低溝通成本。")

    c1, c2, c3 = st.columns(3)
    with c1:
        care = st.multiselect("想優先照顧", ["配偶", "子女", "父母", "夥伴", "公益"], default=["子女","配偶"])
    with c2:
        principles = st.multiselect("重要原則", ["公平", "感恩", "責任", "創新", "永續"], default=["公平","責任"])
    with c3:
        ways = st.multiselect("傳承方式", ["等分", "需求導向", "信託分期", "股權分流", "教育基金", "公益信託"],
                              default=["信託分期","股權分流","教育基金"])

    st.markdown("#### 探索摘要")
    st.write(f"- 優先照顧：{', '.join(care) if care else '（未選）'}")
    st.write(f"- 重要原則：{', '.join(principles) if principles else '（未選）'}")
    st.write(f"- 傳承方式：{', '.join(ways) if ways else '（未選）'}")

    st.markdown("#### 建議『家規 × 資金規則』（示意）")
    bullets = []
    if "公平" in principles:
        bullets.append("重大資產依『公平＋公開』原則分配，避免模糊地帶。")
    if "責任" in principles:
        bullets.append("與公司治理連動：經營權與所有權分流，避免角色衝突。")
    if "信託分期" in ways:
        bullets.append("子女教育/生活費以信託分期給付，達成『照顧但不溺愛』。")
    if "教育基金" in ways:
        bullets.append("設立教育基金，明確用途與提領條件，受託人監管。")
    if "公益信託" in ways or "公益" in care:
        bullets.append("提撥固定比例成立公益信託，作為家族影響力的延伸。")
    if not bullets:
        bullets.append("將價值觀轉譯為具體的分配規則與審核條件，以降低爭議。")

    for b in bullets:
        st.markdown(f"- {b}")

    charter = f"""# 家族價值觀行動準則（草案）
- 優先照顧：{', '.join(care) if care else '未選'}
- 重要原則：{', '.join(principles) if principles else '未選'}
- 傳承方式：{', '.join(ways) if ways else '未選'}

## 行動規則（示意）
""" + "\n".join([f"- {b}" for b in bullets])
    st.download_button(
        "⬇️ 下載價值觀行動準則（Markdown）",
        data=charter.encode("utf-8"),
        file_name=f"value_charter_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )

def page_about():
    st.subheader("🤝 關於我們 / 聯絡")
    st.markdown("**永傳家族辦公室（Grace Family Office）**｜以 AI 工具把複雜變簡單，陪伴家庭安心決策。")

    col1, col2 = st.columns([1,1])
    with col1:
        name  = st.text_input("您的稱呼 *", "")
        email = st.text_input("Email *", "")
        phone = st.text_input("電話（可選）", "")
        topic = st.selectbox("想了解的主題", ["體驗平台 Demo", "企業接班與股權", "遺產/贈與稅", "保單策略", "其它"])
    with col2:
        when_date = st.date_input("期望日期", value=date.today())
        when_ampm = st.selectbox("時段偏好", ["不限", "上午", "下午"], index=0)
        msg = st.text_area("想說的話（選填）", height=120)
        if st.button("送出需求", type="primary"):
            st.success("已收到，我們會盡快與您聯繫。謝謝！")

    st.divider()
    st.caption("《影響力》傳承策略平台｜Grace Family Office｜https://gracefo.com｜聯絡信箱：123@gracefo.com")

# =========================
# Sidebar 導覽（可點擊）
# =========================
with st.sidebar:
    st.image("logo2.png", width=64)
    st.markdown("### 影響力｜AI 傳承規劃平台")
    st.caption("專業 × 快速 × 可信任")
    st.markdown("---")

    if st.button("🏠 首頁總覽", use_container_width=True): navigate("home")
    if st.button("🗺️ 傳承地圖", use_container_width=True): navigate("legacy")
    if st.button("🧮 稅務試算", use_container_width=True): navigate("tax")
    if st.button("📦 保單策略", use_container_width=True): navigate("policy")
    if st.button("❤️ 價值觀探索", use_container_width=True): navigate("values")
    if st.button("🤝 關於我們 / 聯絡", use_container_width=True): navigate("about")

# =========================
# Router
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
    f"""<div class="footer">《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}</div>""",
    unsafe_allow_html=True
)

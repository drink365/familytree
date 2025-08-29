# app.py
import streamlit as st
from datetime import datetime, date
from typing import Dict, List, Tuple
from io import BytesIO

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="影響力｜AI 傳承規劃平台",
    page_icon="logo2.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# Styles
# =========================
BRAND_PRIMARY = "#1F4A7A"   # 專業藍
BRAND_ACCENT  = "#C99A2E"   # 溫暖金
BRAND_BG      = "#F7F9FB"   # 淺底
CARD_BG       = "white"

st.markdown(
    f"""
    <style>
      html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", "Helvetica Neue", Arial;
        background-color: {BRAND_BG};
      }}
      .main > div {{ padding-top: .5rem; padding-bottom: 2rem; }}
      .hero {{
        border-radius: 18px; padding: 40px;
        background: radial-gradient(1000px 400px at 10% 10%, #ffffff 0%, #f3f6fa 45%, #eef2f7 100%);
        border: 1px solid #e6eef5; box-shadow: 0 6px 18px rgba(10,18,50,.04);
      }}
      .title-xl {{ font-size: 40px; font-weight: 800; color: {BRAND_PRIMARY}; margin: 0 0 10px 0; }}
      .subtitle {{ font-size: 18px; color: #334155; margin-bottom: 24px; }}
      .card {{ background: {CARD_BG}; border-radius: 16px; padding: 18px; border: 1px solid #e8eef5; box-shadow: 0 8px 16px rgba(17,24,39,.04); height: 100%; }}
      .card h4 {{ margin: 6px 0; color: {BRAND_PRIMARY}; font-weight: 800; }}
      .muted {{ color: #64748b; font-size: 14px; line-height: 1.5; }}
      header[data-testid="stHeader"] {{ background: transparent; }}
      .footer {{ color:#6b7280; font-size:13px; margin-top: 20px; }}
      .table-wrap {{ background:#fff; border:1px solid #e8eef5; border-radius: 12px; padding: 8px 12px; }}
      .label {{ color:#334155; font-weight:600; }}
      .val {{ color:#0f172a; font-variant-numeric: tabular-nums; }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# PDF Utility (ReportLab)
# =========================
def build_pdf_bytes(title: str, lines: List[str]) -> bytes:
    """
    以 ReportLab 產生簡潔 PDF；需根目錄有 NotoSansTC-Regular.ttf
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_path = "NotoSansTC-Regular.ttf"
        pdfmetrics.registerFont(TTFont("NotoSansTC", font_path))

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setTitle(title)
        width, height = A4

        left_margin = 50
        right_margin = 50
        top_margin = height - 50
        line_height = 16

        c.setFont("NotoSansTC", 18)
        c.drawString(left_margin, top_margin, title)

        y = top_margin - 30
        c.setFont("NotoSansTC", 11)
        for line in lines:
            # 自動換頁
            if y < 50:
                c.showPage()
                c.setFont("NotoSansTC", 11)
                y = top_margin
            c.drawString(left_margin, y, line)
            y -= line_height

        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    except Exception as e:
        st.error("PDF 產生失敗：請確認已在專案加入 `reportlab`，且根目錄含 `NotoSansTC-Regular.ttf`。")
        st.exception(e)
        return b""

# =========================
# Helpers
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

# =========================
# 稅務：級距（示意；可替換為正式表）
# =========================
ESTATE_BRACKETS = [
    (56_210_000, 0.10, 0),
    (112_420_000, 0.15, 2_810_000),
    (10**15, 0.20, 8_430_000),
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
# 民法：法定繼承人與應繼分（簡化）
# =========================
def determine_heirs_and_shares(
    spouse_alive: bool,
    child_count: int,
    parent_count: int,
    sibling_count: int,
    grandparent_count: int
) -> Tuple[str, Dict[str, float]]:
    """
    回傳 (繼承順序, 應繼分 dict)。配偶存在時：
      - 與子女同順序：配偶與每名子女平均分（配偶算一份）
      - 與父母、兄弟姊妹、祖父母同順序：配偶 1/2，另一群體 1/2（群體內平均）
    """
    shares: Dict[str, float] = {}
    if child_count > 0:  # 第一順序：直系卑親屬
        order = "第一順序（子女）"
        if spouse_alive:
            total_units = child_count + 1
            unit = 1 / total_units
            shares["配偶"] = unit
            for i in range(child_count):
                shares[f"子女{i+1}"] = unit
        else:
            unit = 1 / child_count
            for i in range(child_count):
                shares[f"子女{i+1}"] = unit
    elif parent_count > 0:  # 第二順序：父母
        order = "第二順序（父母）"
        if spouse_alive:
            shares["配偶"] = 0.5
            if parent_count > 0:
                unit = 0.5 / parent_count
                for i in range(parent_count):
                    shares[f"父母{i+1}"] = unit
        else:
            unit = 1 / parent_count
            for i in range(parent_count):
                shares[f"父母{i+1}"] = unit
    elif sibling_count > 0:  # 第三順序：兄弟姊妹
        order = "第三順序（兄弟姊妹）"
        if spouse_alive:
            shares["配偶"] = 0.5
            unit = 0.5 / sibling_count
            for i in range(sibling_count):
                shares[f"兄弟姊妹{i+1}"] = unit
        else:
            unit = 1 / sibling_count
            for i in range(sibling_count):
                shares[f"兄弟姊妹{i+1}"] = unit
    elif grandparent_count > 0:  # 第四順序：祖父母
        order = "第四順序（祖父母）"
        if spouse_alive:
            shares["配偶"] = 0.5
            unit = 0.5 / grandparent_count
            for i in range(grandparent_count):
                shares[f"祖父母{i+1}"] = unit
        else:
            unit = 1 / grandparent_count
            for i in range(grandparent_count):
                shares[f"祖父母{i+1}"] = unit
    else:
        order = "（無繼承人，視為國庫）"
        if spouse_alive:
            shares["配偶"] = 1.0
    return order, shares

def eligible_deduction_counts_by_heirs(
    spouse_alive: bool,
    shares: Dict[str, float]
) -> Dict[str, int]:
    """
    依「民法繼承人」決定可計算扣除額的人數：
      - 配偶扣除：配偶存在即適用
      - 直系卑親屬扣除：僅計算『子女』的人數
      - 直系尊親屬扣除：僅計算『父母／祖父母』，上限 2 人
      - 其餘類型（兄弟姊妹）不在扣除名單內
    """
    cnt_children = sum(1 for k in shares if k.startswith("子女"))
    cnt_asc = sum(1 for k in shares if k.startswith("父母") or k.startswith("祖父母"))
    return {
        "spouse": 1 if spouse_alive and ("配偶" in shares) else 0,
        "children": cnt_children,
        "ascendants": min(cnt_asc, 2),
    }

# =========================
# Pages
# =========================
def page_home():
    top = st.columns([1, 5])
    with top[0]:
        st.image("logo.png", use_container_width=True)
    with top[1]:
        st.markdown(
            '<div style="text-align:right;" class="muted">《影響力》傳承策略平台｜永傳家族辦公室</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="title-xl">10 分鐘完成高資產家族 10 年的傳承規劃</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">專業 × 快速 × 可信任｜將法稅知識、保單策略與家族價值觀整合為行動方案，幫助顧問有效成交、幫助家庭安心決策。</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 開始建立傳承地圖", type="primary", use_container_width=True):
            navigate("legacy")
    with c2:
        if st.button("📞 預約顧問 / 合作洽談", use_container_width=True):
            navigate("about")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 核心功能")
    a, b, c = st.columns(3)
    with a:
        feature_card("AI 傳承地圖", "家族 + 六大資產快速建模，輸出『行動清單』與提案。", "🗺️")
    with b:
        feature_card("稅務試算引擎", "依民法繼承人計算扣除額，支援速算扣除與 PDF 匯出。", "🧮")
    with c:
        feature_card("保單策略模擬", "以『保額放大 × 現金流』視角做策略對齊，支援摘要 PDF。", "📦")

def page_legacy_map():
    st.subheader("🗺️ 傳承地圖（輸入 → 摘要 → PDF）")
    st.caption("輸入家族成員與資產概況，生成摘要與行動重點；支援 PDF 下載。")

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

        st.markdown("**二、資產六大類（概略金額或描述）**")
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

        submitted = st.form_submit_button("✅ 生成摘要")
    if not submitted:
        st.info("請輸入上方資訊，點擊「生成摘要」。")
        return

    heirs = [h.strip() for h in heirs_raw.split(",") if h.strip()]
    st.success("已生成摘要：")

    colA, colB = st.columns([1,1])
    with colA:
        st.markdown("##### 家族結構（摘要）")
        st.write(f"- 家族：{family_name or '（未填）'}")
        st.write(f"- 決策者：{patriarch or '（未填）'}／配偶：{spouse or '（未填）'}")
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
            st.warning("💛 特殊照護：建議專款信託/保單金專款與監護人設計。")
        st.markdown("##### 行動清單（建議）")
        st.write("- ① 彙整資產明細與估值，標註持有人/所在地/負債。")
        st.write("- ② 初步試算遺產/贈與稅，評估是否需預留稅源。")
        st.write("- ③ 依公平原則與治理工具設計分配與監督機制（如信託分期）。")
        st.write("- ④ 以保單＋信託搭配建立流動性，確保『現金到位、爭議降低』。")

    # 下載 PDF
    lines = [
        f"家族：{family_name or '（未填）'}",
        f"決策者：{patriarch or '（未填）'}／配偶：{spouse or '（未填）'}",
        f"子女/繼承人：{', '.join(heirs) if heirs else '（未填）'}",
        f"受託/監護：{trustees or '（未填）'}",
        "",
        "【資產分類（六大）】",
        f"- 公司股權：{equity or '未填'}",
        f"- 不動產：{re_est or '未填'}",
        f"- 金融資產：{finance or '未填'}",
        f"- 保單：{policy or '未填'}",
        f"- 海外資產：{offshore or '未填'}",
        f"- 其他資產：{others or '未填'}",
        "",
        "【原則與工具】",
        f"- 公平原則：{fairness}",
        f"- 治理工具：{governance}",
        "- 涉及跨境：是" if cross else "- 涉及跨境：否",
        "- 特殊照護：是" if special else "- 特殊照護：否",
        "",
        "【行動清單（建議）】",
        "1. 彙整資產並初步試算稅負",
        "2. 設計分配與監督機制",
        "3. 以保單＋信託建立流動性",
        "",
        f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"
    ]
    pdf = build_pdf_bytes(f"{family_name or '家族'} 傳承規劃摘要", lines)
    st.download_button("⬇️ 下載 PDF", data=pdf, file_name=f"{(family_name or 'family')}_proposal_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", disabled=(pdf==b""))

def page_tax():
    st.subheader("🧮 稅務試算（依民法繼承人計算扣除額）")
    st.caption("說明：僅『法定繼承人』可計入扣除額。頁面使用一般字級顯示，避免因螢幕寬度受限而數字截斷。")

    # ---- 法定繼承人與應繼分 ----
    st.markdown("##### 1) 法定繼承人輸入（依民法）")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        spouse_alive = st.checkbox("配偶存活", value=True)
    with c2:
        child_count = st.number_input("子女數", min_value=0, value=2, step=1)
    with c3:
        parent_count = st.number_input("父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)
    with c4:
        sibling_count = st.number_input("兄弟姊妹數", min_value=0, value=0, step=1)
    with c5:
        grandparent_count = st.number_input("祖父母存活數（0-2）", min_value=0, max_value=2, value=0, step=1)

    order, shares = determine_heirs_and_shares(
        spouse_alive, child_count, parent_count, sibling_count, grandparent_count
    )
    st.markdown("**繼承順序**：{}".format(order))
    if not shares:
        st.warning("目前無可辨識之繼承人（或僅配偶）。如需更精確規則，後續可擴充代位繼承等情況。")

    # 顯示應繼分（一般字級）
    if shares:
        st.markdown("**應繼分（比例）**")
        with st.container():
            st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
            st.write({k: f"{v:.2%}" for k, v in shares.items()})
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- 依繼承人計算扣除額 ----
    st.markdown("##### 2) 扣除額計算（僅計入法定繼承人）")
    # 由 shares 推得可扣人數
    eligible = eligible_deduction_counts_by_heirs(spouse_alive, shares)

    colA, colB, colC = st.columns(3)
    with colA:
        estate_base = st.number_input("遺產總額 (TWD)", min_value=0, value=120_000_000, step=1_000_000)
        funeral     = st.number_input("喪葬費（上限 1,380,000）", min_value=0, value=1_380_000, step=10_000)
    with colB:
        spouse_ded  = 5_530_000 if eligible["spouse"] == 1 else 0
        st.text_input("配偶扣除（自動）", value=f"{spouse_ded:,}", disabled=True)
        basic_ex    = st.number_input("基本免稅（13,330,000）", min_value=0, value=13_330_000, step=10_000)
    with colC:
        dep_children = eligible["children"]
        asc_count    = eligible["ascendants"]
        st.text_input("直系卑親屬人數（自動 ×560,000）", value=str(dep_children), disabled=True)
        st.text_input("直系尊親屬人數（自動，最多2 ×1,380,000）", value=str(asc_count), disabled=True)

    total_deductions = (
        min(funeral, 1_380_000)
        + spouse_ded
        + basic_ex
        + dep_children * 560_000
        + asc_count * 1_380_000
    )
    taxable = max(0, int(estate_base - total_deductions))
    result = apply_brackets(taxable, ESTATE_BRACKETS)

    st.markdown("**結果（一般字級顯示）**")
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    st.write({
        "可扣除總額": f"{total_deductions:,}",
        "課稅基礎": f"{taxable:,}",
        "適用稅率": f"{result['rate']}%",
        "速算扣除": f"{result['quick']:,}",
        "預估應納稅額": f"{result['tax']:,}",
    })
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("※ 簡化示意；最終仍以官方規定與個案事實為準。代位繼承、特留分等複雜情況可於後續版本擴充。")

    # 稅務試算 PDF
    tax_lines = [
        "【法定繼承人與應繼分】",
        f"- 繼承順序：{order}",
        "- 應繼分：" + ", ".join([f"{k} {v:.2%}" for k, v in shares.items()]) if shares else "- 應繼分：N/A",
        "",
        "【扣除額計算（僅法定繼承人）】",
        f"- 喪葬費：{min(funeral, 1_380_000):,}",
        f"- 配偶扣除：{spouse_ded:,}",
        f"- 基本免稅：{basic_ex:,}",
        f"- 直系卑親屬（{dep_children} 人 × 560,000）：{dep_children * 560_000:,}",
        f"- 直系尊親屬（{asc_count} 人 × 1,380,000）：{asc_count * 1_380_000:,}",
        f"→ 可扣除總額：{total_deductions:,}",
        "",
        "【稅額試算】",
        f"- 課稅基礎：{taxable:,}",
        f"- 適用稅率：{result['rate']}%",
        f"- 速算扣除：{result['quick']:,}",
        f"→ 預估應納稅額：{result['tax']:,}",
        "",
        f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"
    ]
    tax_pdf = build_pdf_bytes("遺產稅試算結果", tax_lines)
    st.download_button("⬇️ 下載稅務試算 PDF", data=tax_pdf, file_name=f"estate_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", disabled=(tax_pdf==b""))

    # ---- 贈與稅（附在下方，數字不放大）----
    st.divider()
    st.markdown("##### 3) 贈與稅試算（一般字級）")
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

    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    st.write({
        "贈與總額": f"{gift_total:,}",
        "免稅額": f"{annual_ex:,}",
        "課稅基礎": f"{gift_taxable:,}",
        "適用稅率": f"{g_result['rate']}%",
        "速算扣除": f"{g_result['quick']:,}",
        "預估應納稅額": f"{g_result['tax']:,}",
    })
    st.markdown('</div>', unsafe_allow_html=True)

    gift_lines = [
        "【贈與稅試算】",
        f"- 贈與總額：{gift_total:,}",
        f"- 基本免稅：{annual_ex:,}",
        f"- 課稅基礎：{gift_taxable:,}",
        f"- 適用稅率：{g_result['rate']}%",
        f"- 速算扣除：{g_result['quick']:,}",
        f"→ 預估應納稅額：{g_result['tax']:,}",
        "",
        f"備註：{note or '（無）'} ／ 納稅義務人：{pay_by} ／ 受贈人數：{donees}",
        f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"
    ]
    gift_pdf = build_pdf_bytes("贈與稅試算結果", gift_lines)
    st.download_button("⬇️ 下載贈與稅試算 PDF", data=gift_pdf, file_name=f"gift_tax_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", disabled=(gift_pdf==b""))

def page_policy():
    st.subheader("📦 保單策略模擬（摘要 PDF）")
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
    face_mult = {"放大財富傳承":18, "補足遺產稅":14, "退休現金流":10, "企業風險隔離":12}[goal]
    indicative_face = int(total_premium * face_mult)
    cv_10y = int(total_premium * (1 + irr/100)**10)

    st.markdown("**估算摘要（一般字級）**")
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    st.write({
        "總保費": f"{total_premium:,} {currency}",
        "估計身故保額": f"{indicative_face:,} {currency}",
        "10 年估計現金值": f"{cv_10y:,} {currency}",
        "IRR（示意）": f"{irr:.1f}%",
        "策略目標": goal,
    })
    st.markdown('</div>', unsafe_allow_html=True)

    # 年度現金流表（一般字級）
    years_range = list(range(1, years+1))
    cash_out = [-premium for _ in years_range]
    cum_out  = [sum(cash_out[:i]) for i in range(1, years+1)]
    st.markdown("**年度現金流示意**")
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    st.write([{ "年度": y, "保費現金流": f"{cash_out[y-1]:,}", "累計現金流": f"{cum_out[y-1]:,}" } for y in years_range])
    st.markdown('</div>', unsafe_allow_html=True)

    # PDF
    lines = [
        f"策略目標：{goal}",
        f"年繳保費 × 年期：{premium:,} × {years} ＝ 總保費 {total_premium:,} {currency}",
        f"估計身故保額（倍數示意）：{indicative_face:,} {currency}",
        f"10 年估計現金值（IRR {irr:.1f}%）：{cv_10y:,} {currency}",
        "",
        "【年度現金流】",
    ] + [f"- 第 {y} 年：{cash_out[y-1]:,}（累計 {cum_out[y-1]:,}）" for y in years_range] + [
        "",
        f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"
    ]
    pdf = build_pdf_bytes("保單策略摘要", lines)
    st.download_button("⬇️ 下載保單策略 PDF", data=pdf, file_name=f"policy_strategy_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", disabled=(pdf==b""))

def page_values():
    st.subheader("❤️ 價值觀探索（PDF）")
    st.caption("把價值觀轉譯為可執行的『家規』與資金配置原則，降低溝通成本。")

    c1, c2, c3 = st.columns(3)
    with c1:
        care = st.multiselect("想優先照顧", ["配偶", "子女", "父母", "夥伴", "公益"], default=["子女","配偶"])
    with c2:
        principles = st.multiselect("重要原則", ["公平", "感恩", "責任", "創新", "永續"], default=["公平","責任"])
    with c3:
        ways = st.multiselect("傳承方式", ["等分", "需求導向", "信託分期", "股權分流", "教育基金", "公益信託"],
                              default=["信託分期","股權分流","教育基金"])

    st.markdown("**探索摘要**")
    st.write(f"- 優先照顧：{', '.join(care) if care else '（未選）'}")
    st.write(f"- 重要原則：{', '.join(principles) if principles else '（未選）'}")
    st.write(f"- 傳承方式：{', '.join(ways) if ways else '（未選）'}")

    bullets = []
    if "公平" in principles: bullets.append("重大資產依『公平＋公開』原則分配，避免模糊地帶。")
    if "責任" in principles: bullets.append("與公司治理連動：經營權與所有權分流，避免角色衝突。")
    if "信託分期" in ways:   bullets.append("子女教育/生活費以信託分期給付，達成『照顧但不溺愛』。")
    if "教育基金" in ways:   bullets.append("設立教育基金，明確用途與提領條件，受託人監管。")
    if "公益信託" in ways or "公益" in care: bullets.append("提撥固定比例成立公益信託，作為家族影響力的延伸。")
    if not bullets: bullets.append("將價值觀轉譯為具體的分配規則與審核條件，以降低爭議。")
    for b in bullets: st.markdown(f"- {b}")

    lines = [
        "【價值觀探索結果】",
        f"- 優先照顧：{', '.join(care) if care else '未選'}",
        f"- 重要原則：{', '.join(principles) if principles else '未選'}",
        f"- 傳承方式：{', '.join(ways) if ways else '未選'}",
        "",
        "【建議家規 × 資金規則（示意）】",
    ] + [f"- {b}" for b in bullets] + [
        "",
        f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"
    ]
    pdf = build_pdf_bytes("價值觀 × 行動準則", lines)
    st.download_button("⬇️ 下載價值觀 PDF", data=pdf, file_name=f"value_charter_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", disabled=(pdf==b""))

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
st.markdown(f"""<div class="footer">《影響力》傳承策略平台｜永傳家族辦公室｜{datetime.now().strftime("%Y/%m/%d")}</div>""", unsafe_allow_html=True)

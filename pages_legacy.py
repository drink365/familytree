
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf, p, h2, title, spacer, table

def render():
    st.subheader("🗺️ 傳承地圖（輸入 → 摘要 → PDF）")
    with st.form("legacy_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            family_name = st.text_input("家族名稱（可選）", "")
            patriarch   = st.text_input("主要決策者（例：李先生）", "")
        with c2:
            spouse      = st.text_input("配偶（例：王女士）", "")
            heirs_raw   = st.text_input("子女 / 繼承人（逗號分隔）", "長子,長女")
        with c3:
            trustees    = st.text_input("受託/監護安排（可選）", "")

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
    st.write({
        "家族": family_name or "（未填）",
        "決策者": patriarch or "（未填）",
        "配偶": spouse or "（未填）",
        "子女/繼承人": ", ".join(heirs) if heirs else "（未填）",
        "受託/監護": trustees or "（未填）",
    })

    # Build PDF
    filename = f"/mnt/data/{(family_name or 'family')}_proposal_{datetime.now().strftime('%Y%m%d')}.pdf"
    flow = [
        title(f"{family_name or '家族'} 傳承規劃摘要"),
        spacer(8),
        h2("家族資料"),
        p(f"決策者：{patriarch or '（未填）'}／配偶：{spouse or '（未填）'}"),
        p(f"子女/繼承人：{', '.join(heirs) if heirs else '（未填）'}"),
        p(f"受託/監護：{trustees or '（未填）'}"),
        spacer(6),
        h2("資產六大"),
        p(f"公司股權：{equity or '未填'}"),
        p(f"不動產：{re_est or '未填'}"),
        p(f"金融資產：{finance or '未填'}"),
        p(f"保單：{policy or '未填'}"),
        p(f"海外資產：{offshore or '未填'}"),
        p(f"其他資產：{others or '未填'}"),
        spacer(6),
        h2("原則與工具"),
        p(f"公平原則：{fairness}"),
        p(f"治理工具：{governance}"),
        p("涉及跨境：是" if cross else "涉及跨境：否"),
        p("特殊照護：是" if special else "特殊照護：否"),
        spacer(6),
        h2("行動清單（示意）"),
        p("1. 彙整資產並初步試算稅負"),
        p("2. 設計分配與監督機制"),
        p("3. 以保單＋信託建立流動性"),
        spacer(6),
        p(f"產出日期：{datetime.now().strftime('%Y/%m/%d')}"),
    ]
    build_branded_pdf(filename, flow)
    with open(filename, "rb") as f:
        st.download_button("⬇️ 下載 PDF", data=f.read(), file_name=filename.split("/")[-1], mime="application/pdf")

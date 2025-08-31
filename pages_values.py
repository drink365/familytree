# pages_values.py
# -*- coding: utf-8 -*-
import streamlit as st
from datetime import datetime

# 若你有品牌 PDF 工具，就能一鍵匯出；沒有也可安全移除這段 import
try:
    from utils.pdf_utils import build_branded_pdf_bytes, p, h2, spacer
    HAS_PDF = True
except Exception:
    HAS_PDF = False

# ---------------- helpers ----------------
def _parse_csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def _join(items: list[str]) -> str:
    return "、".join(items) if items else "（未填）"

def _chips_html(items: list[str]) -> str:
    if not items:
        return '<span class="chip chip-empty">（未填）</span>'
    chips = "".join([f'<span class="chip">{st.escape_markdown(i)}</span>' for i in items])
    return chips

# ---------------- page ----------------
def render():
    st.subheader("🧭 價值觀探索")
    st.caption("此頁僅做會談討論的引導與整理，非法律或投資意見。")

    # 些微品牌樣式（紅系與你站上其他頁一致）
    st.markdown(
        """
        <style>
          .card{
            border:1px solid #e5e7eb;border-radius:14px;padding:16px 18px;margin-top:10px;background:#fff
          }
          .card h4{margin:0 0 8px 0;font-size:1.05rem;color:#111827}
          .chip{
            display:inline-block;padding:6px 10px;margin:4px 6px 0 0;border-radius:9999px;
            background:#fff5f5;border:1px solid #f2b3b6;color:#c2272d;font-weight:600;font-size:.95rem
          }
          .chip-empty{
            color:#6b7280;background:#f9fafb;border:1px dashed #e5e7eb;font-weight:400
          }
          .two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
          @media (max-width: 900px){ .two-col{grid-template-columns:1fr} }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---- Inputs ----
    with st.form("values_form"):
        c1, c2 = st.columns(2)
        with c1:
            pri_raw = st.text_input("優先照顧（以逗號分隔）", "子女, 配偶")
            princ_raw = st.text_input("重要原則（以逗號分隔）", "公平, 責任")
        with c2:
            ways_raw = st.text_input("傳承方式（以逗號分隔）", "信託分期, 股權分流, 教育基金")
            notes = st.text_area("補充說明（可選）", "", height=90)
        submitted = st.form_submit_button("✅ 生成摘要")

    if not submitted:
        st.info("請輸入上方欄位後，點擊「生成摘要」。")
        return

    # ---- Normalize ----
    pri_list   = _parse_csv(pri_raw)
    princ_list = _parse_csv(princ_raw)
    ways_list  = _parse_csv(ways_raw)

    # ---- Display (卡片＋標籤，不再用大括號) ----
    st.success("已整理為摘要：")
    st.markdown('<div class="two-col">', unsafe_allow_html=True)

    st.markdown(
        f'''
        <div class="card">
          <h4>優先照顧</h4>
          {_chips_html(pri_list)}
        </div>
        ''', unsafe_allow_html=True
    )
    st.markdown(
        f'''
        <div class="card">
          <h4>重要原則</h4>
          {_chips_html(princ_list)}
        </div>
        ''', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        f'''
        <div class="card">
          <h4>傳承方式</h4>
          {_chips_html(ways_list)}
        </div>
        ''', unsafe_allow_html=True
    )

    if notes.strip():
        st.markdown(
            f'''
            <div class="card">
              <h4>補充說明</h4>
              <div style="color:#374151;line-height:1.6;">{st.escape_markdown(notes)}</div>
            </div>
            ''', unsafe_allow_html=True
        )

    # ---- Optional: PDF ----
    if HAS_PDF:
        st.divider()
        st.markdown("### 下載 PDF")
        flow = [
            h2("價值觀探索摘要"), spacer(6),
            p("優先照顧：" + _join(pri_list)),
            p("重要原則：" + _join(princ_list)),
            p("傳承方式：" + _join(ways_list)),
        ]
        if notes.strip():
            flow += [spacer(6), p("補充說明：" + notes.strip())]
        flow += [spacer(6), p("產出日期：" + datetime.now().strftime("%Y/%m/%d"))]

        pdf_bytes = build_branded_pdf_bytes(flow)
        st.download_button(
            "⬇️ 下載價值觀摘要 PDF",
            data=pdf_bytes,
            file_name=f"values_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

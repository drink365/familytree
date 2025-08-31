# pages_values.py
# -*- coding: utf-8 -*-
import streamlit as st
from datetime import datetime
from html import escape

# PDF：若你環境有 utils.pdf_utils 就會顯示下載按鈕；沒有也能正常使用本頁
try:
    from utils.pdf_utils import build_branded_pdf_bytes, p, h2, spacer
    HAS_PDF = True
except Exception:
    HAS_PDF = False

# ---------------- 預設選項 ----------------
PRIORITY_OPTIONS = [
    "配偶", "子女", "父母", "兄弟姊妹", "祖父母",
    "員工", "關鍵夥伴", "慈善", "企業永續"
]

PRINCIPLE_OPTIONS = [
    "公平", "責任", "效率", "透明", "隱私",
    "長期", "機會均等", "能力導向", "需求導向", "家族共識", "專業治理"
]

METHOD_OPTIONS = [
    "信託分期", "遺囑", "家族憲章", "控股公司",
    "股權分流", "保單繼承金", "教育基金",
    "監護/照護信託", "慈善信託", "家族理事會", "保留控制權"
]

# ---------------- helpers ----------------
def _parse_csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def _merge_unique(selected: list[str], custom_raw: str) -> list[str]:
    out, seen = [], set()
    for x in selected + _parse_csv(custom_raw):
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def _join(items: list[str]) -> str:
    return "、".join(items) if items else "（未選）"

def _chips_html(items: list[str]) -> str:
    if not items:
        return '<span class="chip chip-empty">（未選）</span>'
    chips = "".join([f'<span class="chip">{escape(i)}</span>' for i in items])
    return chips

# ---------------- page ----------------
def render():
    st.subheader("🧭 價值觀探索")
    st.caption("此頁僅做會談討論與摘要整理，非法律或投資意見。")

    # 些微品牌樣式（與站內紅色系一致）
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

    # ---- Inputs（可勾選 + 可自訂）----
    with st.form("values_form"):
        st.markdown("### 選擇與填寫")

        c1, c2 = st.columns(2)
        with c1:
            pri_sel = st.multiselect("優先照顧（可複選）", PRIORITY_OPTIONS, default=["子女", "配偶"])
            pri_custom = st.text_input("自訂優先照顧（逗號分隔，可留白）", "")
        with c2:
            princ_sel = st.multiselect("重要原則（可複選）", PRINCIPLE_OPTIONS, default=["公平", "責任"])
            princ_custom = st.text_input("自訂重要原則（逗號分隔，可留白）", "")

        ways_sel = st.multiselect("傳承方式（可複選）", METHOD_OPTIONS,
                                  default=["信託分期", "股權分流", "教育基金"])
        ways_custom = st.text_input("自訂傳承方式（逗號分隔，可留白）", "")

        notes = st.text_area("補充說明（可選）", "", height=90)

        submitted = st.form_submit_button("✅ 生成摘要")

    if not submitted:
        st.info("請勾選（或輸入）上方內容，然後點擊「生成摘要」。")
        return

    # ---- Merge selections ----
    pri_list   = _merge_unique(pri_sel, pri_custom)
    princ_list = _merge_unique(princ_sel, princ_custom)
    ways_list  = _merge_unique(ways_sel, ways_custom)

    # ---- Display（卡片＋標籤，不再用大括號）----
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
              <div style="color:#374151;line-height:1.6;">{escape(notes)}</div>
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

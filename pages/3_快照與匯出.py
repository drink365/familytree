
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from app_core import (TZ, init_session_defaults, render_sidebar, section_title, guidance_note, badge_add,
                      versions_list, version_insert, current_gap_estimate, plausible_event, maybe_fire_clarity_moment)

init_session_defaults(); render_sidebar()
st.title("快照與匯出")

# ---------- Utils to build reports ----------
def fmt_money(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)

def build_report_html(is_internal: bool = True):
    est = current_gap_estimate()
    now = datetime.now(TZ).strftime('%Y-%m-%d %H:%M')
    fam = st.session_state.family_name or '未命名家族'
    assets = st.session_state.assets
    plan = st.session_state.plan

    style = """
    <style>
    body{font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Helvetica Neue', Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif; color:#0f172a; line-height:1.6;}
    .cover{border:2px solid #0f766e;padding:16px 20px;border-radius:12px;margin:12px 0;}
    h1{margin:0;color:#0f766e;} h2{color:#0f766e;border-bottom:1px solid #e5e7eb;padding-bottom:4px;}
    table{width:100%;border-collapse:collapse;margin:8px 0 16px 0;}
    th,td{border:1px solid #e5e7eb;padding:8px;text-align:left;}
    .muted{color:#64748b;font-size:12px}
    .tag{display:inline-block;border:1px solid #e2e8f0;padding:2px 8px;border-radius:999px;margin-right:6px;}
    </style>
    """
    head = f"""
    <div class="cover">
      <div class="tag">{'內部版（完整）' if is_internal else '分享版（摘要）'}</div>
      <h1>家族傳承初診斷報告</h1>
      <div>家族：<strong>{fam}</strong></div>
      <div>時間：{now}</div>
    </div>
    """

    # Assets section
    if is_internal:
        rows = "".join([f"<tr><td>{k}</td><td>{fmt_money(v)} 萬</td></tr>" for k,v in assets.items()])
        assets_html = f"""
        <h2>資產彙總</h2>
        <table><thead><tr><th>項目</th><th>金額</th></tr></thead><tbody>{rows}</tbody></table>
        <div class="muted">單位：萬元；此區僅供規劃模擬。</div>
        """
    else:
        total = sum(assets.values())
        assets_html = f"""
        <h2>資產概覽</h2>
        <p>總額：約 <strong>{fmt_money(total)} 萬</strong>（明細留存於內部版）。</p>
        <div class="muted">本分享版僅呈現彙總資訊，避免曝露個別資產細節。</div>
        """

    # Plan section
    plan_rows = "".join([f"<tr><td>{k}</td><td>{v}%</td></tr>" for k,v in plan.items()])
    plan_html = f"""
    <h2>策略配置（比例）</h2>
    <table><thead><tr><th>項目</th><th>比例</th></tr></thead><tbody>{plan_rows}</tbody></table>
    """

    # Metrics
    if est:
        gap = max(0, est['est_tax'] - est['cash_liq'])
        if is_internal:
            metrics_html = f"""
            <h2>重點指標</h2>
            <ul>
                <li>估算遺產稅：{fmt_money(est['est_tax'])} 元</li>
                <li>估算可動用現金：{fmt_money(est['cash_liq'])} 元</li>
                <li>流動性缺口：<strong>{fmt_money(gap)} 元</strong></li>
            </ul>
            """
        else:
            # 分享版：數字改為範圍或大約值（降低敏感度）
            def approx(n):
                if n < 1_000_000: base = (n // 100_000) * 100_000
                else: base = (n // 1_000_000) * 1_000_000
                return f"約 {fmt_money(base)}+"
            metrics_html = f"""
            <h2>重點指標（摘要）</h2>
            <ul>
                <li>估算遺產稅：{approx(est['est_tax'])}</li>
                <li>估算可動用現金：{approx(est['cash_liq'])}</li>
                <li>流動性缺口：<strong>{approx(gap)}</strong></li>
            </ul>
            <div class="muted">註：分享版呈現「約略值」以降低敏感度；完整數字請見內部版。</div>
            """
    else:
        metrics_html = "<p class='muted'>尚未完成資產與策略輸入，無法生成重點指標。</p>"

    disclaimer = """
    <p class="muted">本報告為教育與模擬用途，非正式法律／稅務建議；實際規劃請與專業團隊進一步確認。</p>
    """

    return f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body>{head}{assets_html}{plan_html}{metrics_html}{disclaimer}</body></html>"

def build_report_pdf(is_internal: bool = True) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except Exception as e:
        st.error("產生 PDF 需要 `reportlab`，請確認 requirements 已包含並重新部署。")
        raise

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Heading1'], textColor=colors.HexColor("#0f766e"))
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], textColor=colors.HexColor("#0f766e"))
    body = styles['BodyText']

    est = current_gap_estimate()
    fam = st.session_state.family_name or '未命名家族'
    story = []
    story += [Paragraph("家族傳承初診斷報告", h1), Spacer(1,8)]
    story += [Paragraph(("內部版（完整）" if is_internal else "分享版（摘要）"), body), Spacer(1,4)]
    story += [Paragraph(f"家族：{fam}", body), Paragraph(f"時間：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}", body), Spacer(1,12)]

    # assets
    if is_internal:
        story += [Paragraph("資產彙總", h2)]
        data = [["項目","金額（萬）"]] + [[k, f"{int(v):,}"] for k,v in st.session_state.assets.items()]
        table = Table(data, hAlign="LEFT")
        table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor("#f1f5f9"))]))
        story += [table, Spacer(1,8)]
    else:
        total = sum(st.session_state.assets.values())
        story += [Paragraph("資產概覽", h2), Paragraph(f"總額：約 {int(total):,} 萬（明細留存於內部版）", body), Spacer(1,8)]

    # plan
    story += [Paragraph("策略配置（比例）", h2)]
    data = [["項目","比例（%）"]] + [[k, str(v)] for k,v in st.session_state.plan.items()]
    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor("#f1f5f9"))]))
    story += [table, Spacer(1,8)]

    # metrics
    if est:
        gap = max(0, est['est_tax'] - est['cash_liq'])
        story += [Paragraph("重點指標", h2)]
        if is_internal:
            items = [
                f"估算遺產稅：{int(est['est_tax']):,} 元",
                f"估算可動用現金：{int(est['cash_liq']):,} 元",
                f"流動性缺口：{int(gap):,} 元"
            ]
        else:
            def approx(n):
                base = (int(n) // 500000) * 500000
                return f"約 {base:,}+ 元"
            items = [
                f"估算遺產稅：{approx(est['est_tax'])}",
                f"估算可動用現金：{approx(est['cash_liq'])}",
                f"流動性缺口：{approx(gap)}"
            ]
        for it in items:
            story += [Paragraph("• " + it, body)]
        story += [Spacer(1,8)]
    else:
        story += [Paragraph("尚未完成資產與策略輸入，無法生成重點指標。", body), Spacer(1,8)]

    story += [Paragraph("本報告為教育與模擬用途，非正式法律／稅務建議；實際規劃請與專業團隊進一步確認。", body)]
    doc.build(story)
    return buffer.getvalue()

# ---------- UI ----------
section_title("💾", "保存當前快照")
if st.button("保存為新版本", use_container_width=True):
    version_insert(st.session_state.family_name, st.session_state.assets, st.session_state.plan)
    badge_add("版本管理者")
    st.success("已保存版本。徽章：版本管理者")
    plausible_event("Saved Snapshot", {})
    maybe_fire_clarity_moment()

section_title("📜", "版本記錄")
vers = versions_list()
if not vers:
    st.caption("尚無版本記錄。完成前述步驟後，可在此保存版本。")
else:
    data = [{
        "時間": v["time"].strftime("%Y-%m-%d %H:%M"),
        "家族": v["family"] or "未命名家族",
        "股權給下一代%": v["plan"]["股權給下一代"],
        "保單留配偶%": v["plan"]["保單留配偶"],
        "慈善信託%": v["plan"]["慈善信託"],
        "留現金緊急金%": v["plan"]["留現金緊急金"],
        "資產總額(萬)": sum(v["assets"].values()),
    } for v in vers]
    st.dataframe(pd.DataFrame(data), use_container_width=True)

section_title("⬇️", "報告輸出")
col1, col2 = st.columns(2)
with col1:
    st.subheader("內部版（完整數字）")
    html_full = build_report_html(is_internal=True)
    st.download_button("下載 HTML（內部版）", html_full, file_name="legacy_report_full.html", use_container_width=True)
    try:
        pdf_bytes = build_report_pdf(is_internal=True)
        st.download_button("下載 PDF（內部版）", data=pdf_bytes, file_name="legacy_report_full.pdf", mime="application/pdf", use_container_width=True)
    except Exception:
        st.info("若需 PDF，請在環境安裝 `reportlab` 後重試（已在 requirements.txt 列出）。")

with col2:
    st.subheader("分享版（去識別化摘要）")
    html_share = build_report_html(is_internal=False)
    st.download_button("下載 HTML（分享版）", html_share, file_name="legacy_report_share.html", use_container_width=True)
    try:
        pdf_bytes2 = build_report_pdf(is_internal=False)
        st.download_button("下載 PDF（分享版）", data=pdf_bytes2, file_name="legacy_report_share.pdf", mime="application/pdf", use_container_width=True)
    except Exception:
        st.info("若需 PDF，請在環境安裝 `reportlab` 後重試（已在 requirements.txt 列出）。")

with st.expander("提示"):
    guidance_note("內部版提供完整數字；分享版提供約略值與摘要，適合對外溝通。兩者皆具備列印友善格式。")

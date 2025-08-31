# pages_values.py
# -*- coding: utf-8 -*-
import streamlit as st
from datetime import datetime
from html import escape

# 可選：若你的專案已有品牌 PDF 工具，會顯示下載按鈕；沒有也不影響此頁使用
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

WEIGHT_TOPICS = ["子女教育", "配偶保障", "父母照護", "企業傳承", "慈善/公益"]


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

def _top3(weights_dict: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(weights_dict.items(), key=lambda x: x[1], reverse=True)[:3]

def _ensure_weight_keys(w: dict) -> dict:
    out = dict(w) if isinstance(w, dict) else {}
    defaults = {"子女教育": 5, "配偶保障": 5, "父母照護": 3, "企業傳承": 4, "慈善/公益": 2}
    for k, v in defaults.items():
        out.setdefault(k, v)
    return out

def _build_tasks(princ_list, ways_list, weights, red_flags):
    tasks = []
    if "透明" in princ_list or "家族共識" in princ_list:
        tasks.append("起草《家族憲章》（含資訊揭露節奏）")
    if "隱私" in princ_list:
        tasks.append("確認信託／保單之資訊最小化與保密作業")
    if "責任" in princ_list:
        tasks.append("設計受託人／保護人條款與里程碑撥付機制")
    if "公平" in princ_list:
        tasks.append("規劃等額現金＋不等額股權，並評估特留分")
    if "信託分期" in ways_list:
        tasks.append("擬定信託撥付節奏（教育／生活／醫療）")
    if "控股公司" in ways_list or "股權分流" in ways_list:
        tasks.append("檢視控股／SPV 結構與股東協議")
    if weights.get("子女教育", 0) >= 4:
        tasks.append("建立教育基金預算與撥付規範")
    if weights.get("企業傳承", 0) >= 4:
        tasks.append("擬定二代接班路徑與治理會議節奏")
    if weights.get("慈善/公益", 0) >= 4:
        tasks.append("規劃慈善信託或專項公益池（比例與治理）")
    if red_flags:
        tasks.append("針對紅旗議題安排法稅／跨境合規諮詢")
    # 去重並保留順序；保底三項
    seen = set(); ordered = []
    for t in tasks:
        if t not in seen:
            ordered.append(t); seen.add(t)
    if not ordered:
        ordered = ["彙整家族資產並標註可配置金額",
                   "安排家族會議確認價值宣言與分配原則",
                   "與法律／稅務顧問對齊執行路徑"]
    return ordered[:7]


# ---------------- 情境模板 ----------------
def _apply_template(name: str):
    ss = st.session_state
    # 清空
    ss.val_pri_sel = []; ss.val_pri_custom = ""
    ss.val_princ_sel = []; ss.val_princ_custom = ""
    ss.val_ways_sel = []; ss.val_ways_custom = ""
    ss.val_weights = _ensure_weight_keys({})
    ss.val_cross = False; ss.val_special = False; ss.val_equity = False
    ss.val_wont = ["", "", ""]; ss.val_notes = ""

    if name == "二代接班":
        ss.val_pri_sel = ["子女", "配偶"]
        ss.val_princ_sel = ["公平", "責任", "家族共識"]
        ss.val_ways_sel = ["信託分期", "股權分流", "家族憲章", "家族理事會", "保留控制權"]
        ss.val_weights = _ensure_weight_keys({"子女教育": 5, "配偶保障": 4, "父母照護": 3, "企業傳承": 5, "慈善/公益": 2})
        ss.val_equity = True
        ss.val_wont = ["不強迫子女接班", "股權不外流", ""]
        ss.val_notes = "以現金等額＋股權依貢獻，建立家族治理節奏。"

    elif name == "跨境資產":
        ss.val_pri_sel = ["配偶", "子女"]
        ss.val_princ_sel = ["隱私", "專業治理", "長期"]
        ss.val_ways_sel = ["控股公司", "信託分期", "遺囑"]
        ss.val_weights = _ensure_weight_keys({"子女教育": 4, "配偶保障": 4, "父母照護": 2, "企業傳承": 3, "慈善/公益": 2})
        ss.val_cross = True
        ss.val_wont = ["不在單一法域集中資產", "", ""]
        ss.val_notes = "重視資訊最小化與多法域合規，分層持有。"

    elif name == "創業股權":
        ss.val_pri_sel = ["配偶", "關鍵夥伴", "員工"]
        ss.val_princ_sel = ["能力導向", "效率", "隱私"]
        ss.val_ways_sel = ["控股公司", "股權分流", "保留控制權", "家族憲章"]
        ss.val_weights = _ensure_weight_keys({"子女教育": 3, "配偶保障": 4, "父母照護": 2, "企業傳承": 5, "慈善/公益": 2})
        ss.val_equity = True
        ss.val_wont = ["不稀釋控制權至 50% 以下", "", ""]
        ss.val_notes = "股東協議與表決權設計搭配現金池激勵。"

    elif name == "家族照護優先":
        ss.val_pri_sel = ["父母", "配偶", "子女"]
        ss.val_princ_sel = ["需求導向", "長期", "責任"]
        ss.val_ways_sel = ["監護/照護信託", "信託分期", "教育基金"]
        ss.val_weights = _ensure_weight_keys({"子女教育": 4, "配偶保障": 4, "父母照護": 5, "企業傳承": 2, "慈善/公益": 3})
        ss.val_wont = ["不降低既有照護品質", "", ""]
        ss.val_notes = "優先保障長輩與配偶的生活與醫療照護資源。"

    elif name == "慈善導向":
        ss.val_pri_sel = ["配偶", "子女", "慈善"]
        ss.val_princ_sel = ["透明", "長期", "專業治理"]
        ss.val_ways_sel = ["慈善信託", "家族理事會", "家族憲章"]
        ss.val_weights = _ensure_weight_keys({"子女教育": 3, "配偶保障": 4, "父母照護": 2, "企業傳承": 3, "慈善/公益": 5})
        ss.val_wont = ["不影響家族基本安全網", "", ""]
        ss.val_notes = "設定公益占比與治理，分階段投入。"

    elif name == "清空":
        pass

    st.rerun()


# ---------------- page ----------------
def render():
    st.subheader("🧭 價值觀探索")
    st.caption("此頁用於會談討論與摘要整理，非法律或投資意見。")

    # 輕量品牌樣式
    st.markdown(
        """
        <style>
          .card{border:1px solid #e5e7eb;border-radius:14px;padding:16px 18px;margin-top:10px;background:#fff}
          .card h4{margin:0 0 8px 0;font-size:1.05rem;color:#111827}
          .chip{display:inline-block;padding:6px 10px;margin:4px 6px 0 0;border-radius:9999px;background:#fff5f5;border:1px solid #f2b3b6;color:#c2272d;font-weight:600;font-size:.95rem}
          .chip-empty{color:#6b7280;background:#f9fafb;border:1px dashed #e5e7eb;font-weight:400}
          .two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
          @media (max-width: 900px){ .two-col{grid-template-columns:1fr} }
          .subtle{color:#6b7280}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 情境模板
    st.markdown("### 情境模板")
    t1, t2, t3, t4, t5, t6 = st.columns([1.3, 1.3, 1.5, 1.6, 1.3, 2.5])
    with t1:
        if st.button("🌱 二代接班", use_container_width=True):
            _apply_template("二代接班")
    with t2:
        if st.button("🌏 跨境資產", use_container_width=True):
            _apply_template("跨境資產")
    with t3:
        if st.button("🚀 創業股權", use_container_width=True):
            _apply_template("創業股權")
    with t4:
        if st.button("👴 家族照護優先", use_container_width=True):
            _apply_template("家族照護優先")
    with t5:
        if st.button("🎗️ 慈善導向", use_container_width=True):
            _apply_template("慈善導向")
    with t6:
        if st.button("🧼 清空", use_container_width=True):
            _apply_template("清空")

    # 初始化 session_state
    ss = st.session_state
    ss.setdefault("val_pri_sel", ["子女", "配偶"])
    ss.setdefault("val_pri_custom", "")
    ss.setdefault("val_princ_sel", ["公平", "責任"])
    ss.setdefault("val_princ_custom", "")
    ss.setdefault("val_ways_sel", ["信託分期", "股權分流", "教育基金"])
    ss.setdefault("val_ways_custom", "")
    ss.setdefault("val_weights", _ensure_weight_keys({}))
    ss.setdefault("val_cross", False)
    ss.setdefault("val_special", False)
    ss.setdefault("val_equity", False)
    ss.setdefault("val_wont", ["", "", ""])
    ss.setdefault("val_notes", "")

    # 表單（只保留一個按鈕：生成摘要）
    with st.form("values_form"):
        st.markdown("### ① 選擇與自訂")

        c1, c2 = st.columns(2)
        with c1:
            pri_sel = st.multiselect("優先照顧（可複選）", PRIORITY_OPTIONS, default=ss.val_pri_sel)
            pri_custom = st.text_input("自訂優先照顧（逗號分隔，可留白）", ss.val_pri_custom)
        with c2:
            princ_sel = st.multiselect("重要原則（可複選）", PRINCIPLE_OPTIONS, default=ss.val_princ_sel)
            princ_custom = st.text_input("自訂重要原則（逗號分隔，可留白）", ss.val_princ_custom)

        ways_sel = st.multiselect("傳承方式（可複選）", METHOD_OPTIONS, default=ss.val_ways_sel)
        ways_custom = st.text_input("自訂傳承方式（逗號分隔，可留白）", ss.val_ways_custom)

        st.markdown("### ② 重要性權重（0–5）")
        w_cols = st.columns(5)
        weights = {}
        for i, t in enumerate(WEIGHT_TOPICS):
            with w_cols[i]:
                weights[t] = st.slider(t, 0, 5, ss.val_weights.get(t, 3), step=1)

        st.markdown("### ③ 風險紅旗（是/否）")
        r1, r2, r3 = st.columns(3)
        with r1:
            cross_border = st.checkbox("涉及跨境（台／陸／美等）", value=ss.val_cross)
        with r2:
            special_care = st.checkbox("家族成員需特別照護", value=ss.val_special)
        with r3:
            equity_dispute = st.checkbox("股權／合夥可能爭議", value=ss.val_equity)

        st.markdown("### ④ Won’t-do List（不做清單）")
        no1 = st.text_input("不做事項 1（可留白）", ss.val_wont[0])
        no2 = st.text_input("不做事項 2（可留白）", ss.val_wont[1])
        no3 = st.text_input("不做事項 3（可留白）", ss.val_wont[2])

        notes = st.text_area("補充說明（可選）", ss.val_notes, height=90)

        submitted = st.form_submit_button("✅ 生成摘要")

    if not submitted:
        st.info("請勾選/輸入上方內容，點擊「生成摘要」。")
        return

    # 保存目前輸入
    ss.val_pri_sel, ss.val_pri_custom = pri_sel, pri_custom
    ss.val_princ_sel, ss.val_princ_custom = princ_sel, princ_custom
    ss.val_ways_sel, ss.val_ways_custom = ways_sel, ways_custom
    ss.val_weights = _ensure_weight_keys(weights)
    ss.val_cross, ss.val_special, ss.val_equity = cross_border, special_care, equity_dispute
    ss.val_wont = [no1, no2, no3]
    ss.val_notes = notes

    # 整理清單
    pri_list   = _merge_unique(pri_sel,   pri_custom)
    princ_list = _merge_unique(princ_sel, princ_custom)
    ways_list  = _merge_unique(ways_sel,  ways_custom)

    # 權重前三
    top3 = _top3(weights)
    top3_text = "、".join([f"{k}（{v}）" for k, v in top3]) if top3 else "（未設定）"

    # 價值宣言
    def _join_for_md(items): return "、".join(items) if items else "（未選）"
    statement = (
        f"我們以**{_join_for_md(pri_list)}**為優先，遵循**{_join_for_md(princ_list)}**；"
        f"在傳承上，傾向**{_join_for_md(ways_list)}**，兼顧家族長期與流動性。"
    )

    # 衝突偵測
    conflicts = []
    if ("公平" in princ_list) and ("能力導向" in princ_list):
        conflicts.append("「公平」與「能力導向」同時存在：可採 **現金等額＋股權依貢獻**。")
    if ("隱私" in princ_list) and ("透明" in princ_list):
        conflicts.append("「隱私」與「透明」拉扯：建議先訂 **揭露節奏與對象層級**。")
    if weights.get("企業傳承", 0) >= 4 and weights.get("慈善/公益", 0) >= 4:
        conflicts.append("「企業傳承」與「公益」皆高權重：可切分 **持股/現金池** 與專責治理。")

    # 工具建議
    tool_hints = []
    if "隱私" in princ_list:
        tool_hints += ["信託（資訊最小化）", "控股/SPV", "保密協議與內控"]
    if "透明" in princ_list or "家族共識" in princ_list:
        tool_hints += ["家族憲章", "家族理事會／固定揭露節奏", "股東協議"]
    if "責任" in princ_list:
        tool_hints += ["受託人／保護人條款", "績效里程碑撥款", "教育基金審核"]
    if "公平" in princ_list:
        tool_hints += ["等額現金＋不等額股權", "遺囑＋特留分評估"]
    tool_hints = list(dict.fromkeys(tool_hints))

    # 紅旗與任務清單（自動生成）
    red_flags = []
    if cross_border:   red_flags.append("涉及跨境（台／陸／美等）")
    if special_care:   red_flags.append("家族成員需特別照護")
    if equity_dispute: red_flags.append("股權／合夥可能爭議")
    tasks = _build_tasks(princ_list, ways_list, weights, red_flags)

    # ======= 顯示 =======
    st.success("已整理為摘要：")

    st.markdown('<div class="two-col">', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><h4>優先照顧</h4>{_chips_html(pri_list)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><h4>重要原則</h4>{_chips_html(princ_list)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="card"><h4>傳承方式</h4>{_chips_html(ways_list)}</div>', unsafe_allow_html=True)

    st.markdown(
        f'''
        <div class="card">
          <h4>重要性權重</h4>
          <div class="subtle">0 = 不重要，5 = 最高優先</div>
          <div style="margin-top:8px;">{'、'.join([f"{escape(k)}：{v}" for k, v in weights.items()])}</div>
          <div style="margin-top:6px;"><b>前三優先：</b>{escape(top3_text)}</div>
        </div>
        ''', unsafe_allow_html=True
    )

    if red_flags:
        st.markdown(
            f"<div class='card'><h4>顧問提醒（風險紅旗）</h4>{'、'.join([escape(r) for r in red_flags])}</div>",
            unsafe_allow_html=True
        )

    wont = [x for x in [ss.val_wont[0].strip(), ss.val_wont[1].strip(), ss.val_wont[2].strip()] if x.strip()]
    if wont:
        st.markdown(
            f"<div class='card'><h4>Won’t-do List（不做清單）</h4>{'；'.join([escape(x) for x in wont])}</div>",
            unsafe_allow_html=True
        )

    st.markdown(
        f"<div class='card'><h4>建議價值宣言</h4><div style='line-height:1.7;'>{statement}</div></div>",
        unsafe_allow_html=True
    )

    if conflicts:
        st.markdown(
            "<div class='card'><h4>可能的價值衝突與折衷</h4><ul style='margin:6px 0 0 18px;'>"
            + "".join([f"<li>{escape(c)}</li>" for c in conflicts])
            + "</ul></div>",
            unsafe_allow_html=True,
        )

    if tool_hints:
        st.markdown(
            f"<div class='card'><h4>建議工具／結構</h4>{'、'.join([escape(x) for x in tool_hints])}</div>",
            unsafe_allow_html=True
        )

    # ✅ 改為「靜態清單」呈現，不再使用 checkbox，避免點選導致摘要消失
    st.markdown("#### 建議下一步")
    if tasks:
        st.markdown("\n".join([f"- {i}. {escape(t)}" for i, t in enumerate(tasks, 1)]))
    else:
        st.markdown("- 1. 彙整家族資產並標註可配置金額")

    if ss.val_notes.strip():
        st.markdown(
            f"<div class='card'><h4>補充說明</h4><div style='color:#374151;line-height:1.6;'>{escape(ss.val_notes)}</div></div>",
            unsafe_allow_html=True
        )

    # ---- PDF ----
    if HAS_PDF:
        st.divider()
        st.markdown("### 下載 PDF")
        flow = [
            h2("價值觀探索摘要"), spacer(6),
            p("優先照顧：" + _join(pri_list)),
            p("重要原則：" + _join(princ_list)),
            p("傳承方式：" + _join(ways_list)),
            spacer(6),
            p("重要性權重（0–5）："),
            p("、".join([f"{k}：{v}" for k, v in ss.val_weights.items()])),
            p("前三優先：" + top3_text),
            spacer(6),
            p("建議價值宣言："),
            p(statement),
        ]

        if red_flags:
            flow += [spacer(6), p("顧問提醒（風險紅旗）："), p("、".join(red_flags))]
        if wont:
            flow += [spacer(6), p("Won’t-do List："), p("；".join(wont))]
        if conflicts:
            flow += [spacer(6), p("可能的價值衝突與折衷：")]
            for c in conflicts:
                flow.append(p("・" + c))
        if tool_hints:
            flow += [spacer(6), p("建議工具／結構："), p("、".join(tool_hints))]

        flow += [spacer(6), p("建議下一步：")]
        for i, t in enumerate(tasks, 1):
            flow.append(p(f"{i}. {t}"))

        if ss.val_notes.strip():
            flow += [spacer(6), p("補充說明："), p(ss.val_notes.strip())]

        flow += [spacer(6), p("產出日期：" + datetime.now().strftime("%Y/%m/%d"))]

        pdf_bytes = build_branded_pdf_bytes(flow)
        st.download_button(
            "⬇️ 下載價值觀摘要 PDF",
            data=pdf_bytes,
            file_name=f"values_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

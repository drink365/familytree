
import streamlit as st
from textwrap import dedent

def _summarize(values, story):
    if not values and not story.strip():
        return "尚未選擇或輸入內容。"
    parts = []
    if values:
        parts.append(f"核心價值（精選）：{', '.join(values)}。")
    if story.strip():
        parts.append(f"補充敘述：{story.strip()}")
    return " ".join(parts)

def render():
    st.title("💡 價值觀探索")
    st.write("這一頁改為表單提交，避免每次輸入即觸發 rerun。")

    presets = [
        "誠信", "責任", "家庭", "健康", "學習", "成就", "自由", "創新", "關懷", "傳承",
        "專業", "永續", "可靠", "尊重", "勇氣"
    ]

    with st.form("values_form"):
        selected = st.multiselect("請選擇最能代表你的 3-5 個價值（可多選）", options=presets)
        story = st.text_area("若願意，補充說明一段與價值相關的小故事（可選填）", height=140)
        submitted = st.form_submit_button("生成摘要")
        if submitted:
            summary = _summarize(selected, story)
            st.session_state["values_summary"] = summary

    st.markdown("---")
    st.subheader("摘要")
    st.write(st.session_state.get("values_summary", "（尚未生成）"))

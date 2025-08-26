# -*- coding: utf-8 -*-
import os, sys, time
import streamlit as st

# Local imports
from gamification.service import (
    init_db, get_or_create_user, user_points, user_level, leaderboard,
    recent_feed, available_missions, complete_mission, list_badges, award_event
)
from gamification.missions import MISSIONS, EVENT_POINTS

st.set_page_config(page_title="🎯 影響力傳承｜任務與成就", page_icon="🎯", layout="wide")

# --- INIT ---
init_db()

with st.sidebar:
    st.header("👤 使用者登入 / 註冊")
    default_email = st.session_state.get("user_email", "")
    default_name = st.session_state.get("user_name", "")
    email = st.text_input("Email（用於識別分數與成就）", value=default_email)
    name = st.text_input("稱呼 / 名字", value=default_name)
    if st.button("登入 / 建立帳號", use_container_width=True):
        if not email or "@" not in email:
            st.error("請輸入有效 Email")
        else:
            user = get_or_create_user(name=name or "使用者", email=email)
            st.session_state["user_id"] = user["id"]
            st.session_state["user_email"] = user["email"]
            st.session_state["user_name"] = user["name"]
            st.success(f"歡迎，{user['name']}！")

    st.divider()
    st.caption("📎 開發者整合：在其他頁面完成關鍵動作時呼叫：")
    st.code("""
from gamification.service import award_event
# 例：使用者完成預約
award_event(email=user_email, name=user_name, event="booked_consultation")
    """, language="python")
    st.caption("📌 事件點數可在 gamification/missions.py 中調整 EVENT_POINTS。")

st.title("🎯 任務與成就（Octalysis 應用）")
st.caption("完成任務、累積點數與徽章，讓傳承規劃更有動力 —— 準備度→行動→會談→成交。")

user_id = st.session_state.get("user_id")
user_email = st.session_state.get("user_email")
user_name = st.session_state.get("user_name")

if not user_id:
    st.info("請先在左側登入或建立帳號。")
    st.stop()

# --- TOP METRICS ---
col1, col2, col3, col4 = st.columns([1,1,1,1])
pts = user_points(user_id)
lv, cur, nxt = user_level(pts)
with col1:
    st.metric("總點數", pts)
with col2:
    st.metric("等級", lv)
with col3:
    st.progress(min(1.0, cur / max(nxt, 1.0)))
    st.caption(f"距離下一級：還差 {max(nxt - cur, 0)} 分")
with col4:
    badges = list_badges(user_id)
    st.metric("已獲得徽章", len(badges))

st.divider()

# --- MISSIONS ---
st.subheader("✅ 推薦任務")
st.caption("這些任務對成交最有幫助：評測→資產地圖→上傳保單→預約顧問→問卷→稅務試算。")

cards_per_row = 3
missions = available_missions(user_id)
if not missions:
    st.success("太棒了！你已完成目前所有任務 🎉")
else:
    rows = [missions[i:i+cards_per_row] for i in range(0, len(missions), cards_per_row)]
    for row in rows:
        cols = st.columns(cards_per_row)
        for m, c in zip(row, cols):
            with c:
                with st.container(border=True):
                    st.write(f"**{m['title']}**")
                    st.caption(m["description"])
                    st.write(f"🧠 核心動力：{', '.join(m.get('drives', []))}")
                    st.write(f"🏅 完成獎勵：{m.get('points', 0)} 分")
                    if st.button(f"標記完成：{m['title']}", key=f"done_{m['id']}", use_container_width=True):
                        result = complete_mission(user_id, m["id"])
                        st.success(f"已完成 {m['title']}！獲得 {result['awarded_points']} 分")
                        st.rerun()
                    st.caption(m.get("tip", ""))

st.divider()

# --- QUICK ACTIONS (simulate integration) ---
st.subheader("⚡ 快速動作（整合測試）")
st.caption("開發階段可用下列按鈕模擬其他頁面的動作，確認分數是否正常累積。")
ca1, ca2, ca3, ca4, ca5 = st.columns(5)
events = [
    ("完成準備度評測", "completed_readiness_assessment"),
    ("建立資產地圖", "built_legacy_map"),
    ("上傳保單", "uploaded_policies"),
    ("預約顧問", "booked_consultation"),
    ("跑稅務試算", "finished_tax_simulation"),
]
for (title, ev), col in zip(events, [ca1, ca2, ca3, ca4, ca5]):
    with col:
        if st.button(title, key=f"ev_{ev}", use_container_width=True):
            pts_award = award_event(user_email, user_name or "使用者", ev)
            st.toast(f"已記錄：{title}（+{pts_award} 分）", icon="✅")
            st.rerun()

st.divider()

# --- FEED & LEADERBOARD ---
lc1, lc2 = st.columns([1,1])
with lc1:
    st.subheader("📰 我的動態")
    feed = recent_feed(user_id, 15)
    if not feed:
        st.write("尚無紀錄")
    else:
        for item in feed:
            with st.container(border=True):
                st.write(f"**{item['event']}** 　+{item['points']} 分")
                if item.get("meta"):
                    st.caption(str(item["meta"]))
                st.caption(item["created_at"])

with lc2:
    st.subheader("🏆 排行榜")
    top = leaderboard(20)
    for i, row in enumerate(top, start=1):
        with st.container(border=True):
            st.write(f"**#{i} {row['name']}**")
            st.caption(row["email"])
            st.metric("點數", row["points"])

st.divider()
st.caption("© 永傳家族傳承教練｜Gamification Module")

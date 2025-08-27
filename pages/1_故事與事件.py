
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add, is_view_mode,
                      member_list, event_add, event_list, role_add, role_list)

init_session_defaults(); render_sidebar()
st.title("故事與事件")

members = member_list()
id2name = {m["id"]: m["name"] for m in members}

def next_steps_for_event(ev_type:str):
    mapping = {
        "結婚": ["更新受益人與遺囑", "評估家庭保障與醫療保障", "建立家族會議節奏"],
        "新生兒": ["指定監護人與醫療代理", "增加教育金與保障額度", "更新信託條款"],
        "創業/持股變動": ["公司治理與股權安排", "關鍵人風險規劃（Keyman）", "流動性與遺產稅試算"],
        "移居/跨境": ["跨境稅務時點與估值", "資產地與稅籍檢視", "文件合法化與授權"],
        "退休/交棒": ["現金流模型與信託分配", "接班與角色指派", "年度複盤與版本管理"],
        "出售/套現": ["資本利得與稅負檢視", "資金安置與風險等級", "慈善目標與稅務效率"]
    }
    return mapping.get(ev_type, ["整理文件與下一步會議"])

colA, colB = st.columns([2,3])

with colA:
    section_title("🗓️", "新增人生事件")
    if not members:
        st.info("請先到『家族樹』新增成員。")
    else:
        with st.form("add_event"):
            mname = st.selectbox("成員", [m["name"] for m in members])
            ev_type = st.selectbox("事件類型", ["結婚","新生兒","創業/持股變動","移居/跨境","退休/交棒","出售/套現"])
            date = st.text_input("日期（YYYY-MM-DD，可留空）", value="")
            location = st.text_input("地點（可留空）", value="")
            note = st.text_area("備註（可留空）", value="")
            ok = st.form_submit_button("新增事件")
        if ok:
            if is_view_mode():
                st.info("唯讀模式：無法寫入。")
            else:
                mid = [m["id"] for m in members if m["name"]==mname][0]
                event_add(mid, ev_type, date, location, note)
                st.success("事件已新增")
                badge_add("故事守護者")

    section_title("👤", "指派角色")
    if members:
        with st.form("add_role"):
            mname2 = st.selectbox("成員", [m["name"] for m in members], key="role_member")
            role_type = st.selectbox("角色", ["監護人","醫療代理（HCA）","遺囑執行人","家族會議代表"])
            note2 = st.text_input("備註（可留空）", value="")
            ok2 = st.form_submit_button("指派")
        if ok2 and not is_view_mode():
            mid2 = [m["id"] for m in members if m["name"]==mname2][0]
            role_add(mid2, role_type, note2)
            st.success("已指派角色")

with colB:
    section_title("🧭", "建議的下一步")
    evs = event_list()
    if not evs:
        st.caption("新增事件後，這裡會出現針對性的建議清單。")
    else:
        last = evs[0]
        st.write(f"最新事件：**{id2name.get(last['member_id'],'?')}**｜{last['type']}｜{last['date'] or '日期未填'}")
        for s in next_steps_for_event(last['type']):
            st.markdown(f"- {s}")

    section_title("🧾", "事件清單")
    if evs:
        st.table([{"ID":e["id"], "成員": id2name.get(e["member_id"], "?"), "事件": e["type"], "日期": e["date"], "地點": e["location"], "備註": e["note"]} for e in evs])
    else:
        st.caption("尚無事件")

    section_title("🏷️", "角色清單")
    roles = role_list()
    if roles:
        st.table([{"ID":r["id"], "成員": id2name.get(r["member_id"], "?"), "角色": r["role_type"], "備註": r["note"]} for r in roles])
    else:
        st.caption("尚無角色")

with st.expander("提示"):
    guidance_note("事件 → 下一步：用人生事件觸發建議（例如結婚、移居、出售持股），讓討論自然走向規劃與行動。完成 3 則事件即解鎖徽章『故事守護者』。")

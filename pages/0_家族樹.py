
# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add, is_view_mode,
                      member_add, member_list, member_delete, relation_add, relation_list, relation_delete, render_ascii_tree)

init_session_defaults(); render_sidebar()
st.title("家族樹")

colL, colR = st.columns([2,3])

with colL:
    section_title("➕", "新增成員")
    with st.form("add_member"):
        name = st.text_input("姓名*", placeholder="例如：王大華")
        gender = st.selectbox("性別", ["", "女", "男", "其他"], index=0)
        birth = st.text_input("出生（YYYY-MM-DD，可留空）", value="")
        death = st.text_input("過世（YYYY-MM-DD，可留空）", value="")
        note  = st.text_area("備註（可留空）", value="")
        ok = st.form_submit_button("新增")
    if ok:
        if is_view_mode():
            st.info("唯讀模式：無法寫入。")
        elif not name.strip():
            st.warning("請輸入姓名。")
        else:
            member_add(name, gender, birth, death, note)
            st.success(f"已新增 {name}")
            if len(member_list()) >= 5:
                badge_add("家族樹築者")

    section_title("🔗", "建立關係（父母 → 子女）")
    members = member_list()
    names = {m["name"]: m["id"] for m in members}
    if len(members) < 2:
        st.caption("至少需要 2 位成員。")
    else:
        with st.form("add_relation"):
            p = st.selectbox("父/母", list(names.keys()))
            c = st.selectbox("子女", [n for n in names.keys() if n != p])
            submit_rel = st.form_submit_button("建立關係")
        if submit_rel and not is_view_mode():
            relation_add(names[p], names[c], "parent")
            st.success(f"已建立關係：{p} → {c}")

with colR:
    section_title("🌳", "樹狀檢視（縮排示意）")
    st.code(render_ascii_tree())

    section_title("👪", "成員清單")
    data = [{"ID": m["id"], "姓名": m["name"], "性別": m["gender"], "出生": m["birth"], "過世": m["death"], "備註": m["note"]} for m in member_list()]
    st.dataframe(data, use_container_width=True)

    section_title("🧬", "關係清單")
    rels = relation_list()
    if rels:
        st.table([{"ID":r["id"], "父母ID":r["src"], "子女ID":r["dst"], "型別":r["type"]} for r in rels])
    else:
        st.caption("尚無關係")

st.divider()
if st.checkbox("刪除模式（謹慎）"):
    rid = st.number_input("輸入要刪除的成員ID", value=0, step=1)
    if st.button("刪除成員"):
        if not is_view_mode() and rid>0:
            member_delete(int(rid)); st.success("已刪除")
    rrid = st.number_input("輸入要刪除的關係ID", value=0, step=1)
    if st.button("刪除關係"):
        if not is_view_mode() and rrid>0:
            relation_delete(int(rrid)); st.success("已刪除關係")

with st.expander("提示"):
    guidance_note("先把成員與直系關係補齊，之後再補配偶與旁系。完成 5 位成員自動獲得徽章『家族樹築者』。")

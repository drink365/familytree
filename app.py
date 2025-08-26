def advanced_builder():
    st.subheader("🎛 進階建立｜大家族與複雜關係")
    persons = st.session_state.tree["persons"]
    if not persons:
        st.info("請至少先建立『我』或任一成員。")
        return

    # 選人編輯（固定 key）
    id_list = list(persons.keys())
    idx = st.selectbox(
        "選擇成員以編輯/加關係",
        options=list(range(len(id_list))),
        format_func=lambda i: persons[id_list[i]]["name"],
        key="adv_pick_person",
    )
    pid = id_list[idx]
    p = persons[pid]

    with st.expander("✏️ 編輯成員資料", expanded=True):
        c1, c2, c3, c4 = st.columns([2,1,1,1])
        p["name"] = c1.text_input("名稱", value=p["name"], key=f"edit_name_{pid}")
        p["gender"] = c2.selectbox(
            "性別", ["女", "男", "其他/不透漏"],
            index=["女","男","其他/不透漏"].index(p.get("gender","其他/不透漏")),
            key=f"edit_gender_{pid}",
        )
        p["year"] = c3.text_input("出生年(選填)", value=p.get("year",""), key=f"edit_year_{pid}")
        p["deceased"] = c4.toggle("已故?", value=p.get("deceased", False), key=f"edit_dec_{pid}")
        p["note"] = st.text_area("備註(收養/繼親/職業等)", value=p.get("note",""), key=f"edit_note_{pid}")
        st.caption("提示：標註『†』= 已故；可在備註註明關係特殊情形。")

    st.markdown("---")
    cA, cB, cC, cD = st.columns(4)
    with cA:
        st.markdown("**父母**")
        fa = st.text_input("父親姓名", key=f"adv_f_{pid}")
        mo = st.text_input("母親姓名", key=f"adv_m_{pid}")
        if st.button("➕ 為該成員一鍵新增父母並連結", key=f"btn_add_parents_{pid}"):
            fpid = add_person(fa or "父親", "男")
            mpid = add_person(mo or "母親", "女")
            mid = add_or_get_marriage(fpid, mpid, status="married")
            add_child(mid, pid, relation="bio")
            st.toast("已新增父母並連結", icon="👨‍👩‍👧")

    with cB:
        st.markdown("**配偶/關係**")
        spn = st.text_input("配偶姓名", key=f"adv_sp_{pid}")
        spg = st.selectbox("性別", ["女", "男", "其他/不透漏"], index=1, key=f"adv_spg_{pid}")
        sps = st.selectbox(
            "狀態", ["married","divorced","separated"], index=0,
            format_func=lambda s: {"married":"已婚","divorced":"前任(離異)","separated":"分居"}[s],
            key=f"adv_sps_{pid}",
        )
        if st.button("➕ 新增關係", key=f"btn_add_sp_{pid}"):
            spid = add_person(spn or "配偶", spg)
            add_or_get_marriage(pid, spid, status=sps)
            st.toast("已新增關係", icon="💍")

    with cC:
        st.markdown("**子女**")
        my_mids = get_marriages_of(pid)
        if my_mids:
            mid_labels = []
            for mid in my_mids:
                m = st.session_state.tree["marriages"][mid]
                s1 = persons.get(m["spouse1"], {}).get("name", "?")
                s2 = persons.get(m["spouse2"], {}).get("name", "?")
                status = m.get("status","married")
                mid_labels.append((mid, f"{s1} ❤ {s2}（{ {'married':'已婚','divorced':'離','separated':'分'}[status]}）"))
            mid_idx = st.selectbox(
                "選擇關係", options=list(range(len(mid_labels))),
                format_func=lambda i: mid_labels[i][1],
                key=f"adv_mid_{pid}",
            )
            chosen_mid = mid_labels[mid_idx][0]
            cn = st.text_input("子女姓名", key=f"adv_child_name_{pid}")
            cg = st.selectbox("性別", ["女","男","其他/不透漏"], key=f"adv_child_gender_{pid}")
            cy = st.text_input("出生年(選填)", key=f"adv_child_year_{pid}")
            cr = st.selectbox(
                "關係類型", ["bio","adopted","step"],
                format_func=lambda s: {"bio":"親生","adopted":"收養","step":"繼親"}[s],
                key=f"adv_child_rel_{pid}",
            )
            if st.button("➕ 新增子女", key=f"btn_add_child_{pid}"):
                cid = add_person(cn or "孩子", cg, year=cy)
                add_child(chosen_mid, cid, relation=cr)
                st.toast("已新增子女", icon="🧒")
        else:
            st.caption("尚無關係，請先新增配偶/另一半。")

    with cD:
        st.markdown("**兄弟姊妹（批次）**")
        pmid = get_parent_marriage_of(pid)
        if pmid:
            sibs = st.text_input("以逗號分隔：如 小明, 小美", key=f"adv_sibs_{pid}")
            sg = st.selectbox("預設性別", ["女","男","其他/不透漏"], key=f"adv_sibs_gender_{pid}")
            if st.button("➕ 批次新增兄弟姊妹", key=f"btn_add_sibs_{pid}"):
                names = [s.strip() for s in sibs.split(',') if s.strip()]
                for nm in names:
                    sid = add_person(nm, sg)
                    add_child(pmid, sid, relation="bio")
                st.toast("已新增兄弟姊妹", icon="👫")
        else:
            st.caption("此成員尚無已知父母，請先新增父母後再新增兄弟姊妹。")

    st.markdown("---")

    # 關係檢視與微調（每個 widget 都有 mid 細分的 key）
    marriages = st.session_state.tree["marriages"]
    child_types = st.session_state.tree["child_types"]
    if marriages:
        st.markdown("**關係檢視與微調**")
        for mid, m in marriages.items():
            s1 = st.session_state.tree["persons"].get(m["spouse1"], {}).get("name", "?")
            s2 = st.session_state.tree["persons"].get(m["spouse2"], {}).get("name", "?")
            with st.expander(f"{s1} ❤ {s2}"):
                new_status = st.selectbox(
                    "婚姻狀態", ["married","divorced","separated"],
                    index=["married","divorced","separated"].index(m.get("status","married")),
                    format_func=lambda s: {"married":"已婚","divorced":"前任(離異)","separated":"分居"}[s],
                    key=f"stat_{mid}",
                )
                m["status"] = new_status
                for cid in m.get("children", []):
                    cname = st.session_state.tree["persons"].get(cid, {}).get("name", cid)
                    rel_key = f"rel_{mid}_{cid}"
                    current_rel = child_types.get(mid, {}).get(cid, "bio")
                    new_rel = st.selectbox(
                        f"{cname} 的關係", ["bio","adopted","step"],
                        index=["bio","adopted","step"].index(current_rel),
                        format_func=lambda s: {"bio":"親生","adopted":"收養","step":"繼親"}[s],
                        key=rel_key,
                    )
                    set_child_relation(mid, cid, new_rel)


# -*- coding: utf-8 -*-
import streamlit as st
from app_core import (init_session_defaults, render_sidebar, section_title, guidance_note, badge_add, is_view_mode,
                      member_add, member_list, member_delete, relation_add, relation_list, relation_delete, render_ascii_tree,
                      event_add, event_list, role_add, role_list)

init_session_defaults(); render_sidebar()
st.title("家族樹")

st.caption("可上傳 JSON 匯入整個家族樹（persons/marriages 格式）。")



import json
from app_core import import_family_from_json, reset_user_data

with st.expander("🛠️ 匯入JSON", expanded=False):
    up = st.file_uploader("上傳 family_tree.json", type=["json"])
    colx, coly = st.columns([1,1])
    with colx:
        if st.button("匯入上傳檔"):
            if not up:
                st.warning("請先選擇 JSON 檔。")
            else:
                try:
                    obj = json.loads(up.getvalue().decode("utf-8"))
                    ok, msg = import_family_from_json(obj)
                    st.success(msg) if ok else st.error(msg)
                except Exception as e:
                    st.error(f"解析失敗：{e}")
    with coly:
        if st.button("載入內建示例"):
            try:
                demo_path = "/mnt/data/family_tree.json"
                with open(demo_path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                ok, msg = import_family_from_json(obj)
                st.success(msg) if ok else st.error(msg)
            except Exception as e:
                st.error(f"示例無法讀取：{e}")

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
st.subheader("故事與事件（可選）")

colA, colB = st.columns([2,3])
with colA:
    section_title("🗓️", "新增人生事件")
    members = member_list()
    id2name = {m["id"]: m["name"] for m in members}
    if not members:
        st.info("請先在上方新增成員。")
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
    if member_list():
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
    id2name = {m["id"]: m["name"] for m in member_list()}
    if not evs:
        st.caption("新增事件後，這裡會出現針對性的建議清單。")
    else:
        last = evs[0]
        st.write(f"最新事件：**{id2name.get(last['member_id'],'?')}**｜{last['type']}｜{last['date'] or '日期未填'}")
        mapping = {
            "結婚": ["更新受益人與遺囑", "評估家庭保障與醫療保障", "建立家族會議節奏"],
            "新生兒": ["指定監護人與醫療代理", "增加教育金與保障額度", "更新信託條款"],
            "創業/持股變動": ["公司治理與股權安排", "關鍵人風險規劃（Keyman）", "流動性與遺產稅試算"],
            "移居/跨境": ["跨境稅務時點與估值", "資產地與稅籍檢視", "文件合法化與授權"],
            "退休/交棒": ["現金流模型與信託分配", "接班與角色指派", "年度複盤與版本管理"],
            "出售/套現": ["資本利得與稅負檢視", "資金安置與風險等級", "慈善目標與稅務效率"]
        }
        for s in mapping.get(last['type'], ["整理文件與下一步會議"]):
            st.markdown(f"- {s}")


# ==== 圖形家族樹（互動） ====
from pyvis.network import Network
import tempfile, os, uuid
import streamlit.components.v1 as components


# ==== 圖形家族樹（夫妻合併節點） ====
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile, os, uuid

with st.expander("🕸️ 圖形家族樹（可拖曳/縮放）", expanded=True):
    def build_graph_html():
        members = member_list(); rels = relation_list()
        id2name = {m["id"]: m["name"] for m in members}

        # 1) 建立唯一的配偶組合 & 映射：人 -> 夫妻節點
        spouse_pairs = set()
        for r in rels:
            if r["type"] == "spouse":
                a, b = r["src"], r["dst"]
                spouse_pairs.add(tuple(sorted((a, b))))
        person_to_couple = {}
        for a, b in spouse_pairs:
            cid = f"c_{a}_{b}"
            person_to_couple[a] = cid
            person_to_couple[b] = cid

        # 2) 初始化圖並套用階層式版面
        net = Network(height="640px", width="100%", directed=True, notebook=False)
        net.set_options('{"layout":{"hierarchical":{"enabled":true,"direction":"UD","sortMethod":"directed","nodeSpacing":180,"treeSpacing":220}},"edges":{"smooth":{"type":"cubicBezier"}},"physics":{"enabled":false}}')

        # 3) 節點：夫妻合併節點 + 單身節點
        for a, b in sorted(spouse_pairs):
            cid = person_to_couple[a]
            label = f"{id2name.get(a,'?')} ━ {id2name.get(b,'?')}"
            net.add_node(cid, label=label, title=label, shape="box", borderWidth=1)

        singles = [m["id"] for m in members if m["id"] not in person_to_couple]
        for pid in singles:
            nid = f"p_{pid}"
            label = id2name.get(pid, "?")
            net.add_node(nid, label=label, title=label, shape="ellipse", borderWidth=1)

        # 4) 邊：父母 -> 子女（父母以夫妻節點為主；子女若已婚指向其夫妻節點，否則指向個人）
        def node_of_person(pid:int)->str:
            return person_to_couple.get(pid, f"p_{pid}")

        seen_edges = set()
        for r in rels:
            if r["type"] == "parent":
                parent_node = node_of_person(r["src"])
                child_node  = node_of_person(r["dst"])
                if parent_node == child_node:  # 避免自迴圈（極端案例）
                    continue
                key = (parent_node, child_node)
                if key in seen_edges: 
                    continue
                seen_edges.add(key)
                net.add_edge(parent_node, child_node, arrows="to")

        # 5) 匯出 HTML（使用臨時路徑）
        tmp = os.path.join(tempfile.gettempdir(), f"family_graph_{uuid.uuid4().hex}.html")
        net.save_graph(tmp)
        return tmp

    try:
        html_path = build_graph_html()
        with open(html_path, "r", encoding="utf-8") as f:
            components.html(f.read(), height=660, scrolling=True)
    except Exception as e:
        st.error(f"圖形家族樹建立失敗：{e}")

with st.expander("提示"):
    guidance_note("先把成員與直系關係補齊，之後再補配偶與旁系。完成 5 位成員即可達成里程碑『家族樹築者』。")

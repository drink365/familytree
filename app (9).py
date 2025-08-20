# app.py
# 家族樹＋法定繼承人 MVP（台灣民法規則模組 v0.1）
# 部署：將本檔放到 GitHub repo 根目錄，requirements.txt 參考下方註解
# 本版支援：
# - 新增/編輯人物、婚姻（含離婚/喪偶）、親子關係
# - 以死亡日期為基準計算「台灣法定繼承人」與「應繼分比例（基礎版）」
# - 支援非婚生子女（只要建立親子關係即可）
# - 圖形化家族樹（networkx + pyvis）
# - 匯出 / 匯入 JSON（便於版本控管）
#
# 重要說明：
# 1) 本版著重資料結構與演算法骨架，法律計算以「台灣民法」常見情境為主：
#    - 繼承順位：直系卑親屬 > 父母 > 兄弟姊妹 > 祖父母；配偶為當然繼承人（與各順位合併繼承）。
#    - 配偶應繼分：與第一順位「按人數平均」；與第二或第三順位為 1/2；與第四順位為 2/3；無其他順位時全數。
#    - 代位繼承：目前實作於「第一順位（子女線）」，採「按支分配（per stirpes）」
#    - 同父異母/同母異父視同兄弟姊妹。
# 2) 未涵蓋：喪失繼承權、特留分、經法院認定之除斥、遺囑、遺贈、夫妻剩餘財產分配、遺產債務、收養/解除收養的細節、
#    第二與第三順位之代位繼承等進階狀況。請依實務需求再擴充 InheritanceRuleTW 類別。
# 3) 本工具僅供教學與規劃初稿參考，不構成法律意見。

import json
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import streamlit as st
import networkx as nx
from pyvis.network import Network
import tempfile
import pandas as pd

# ========== 資料模型 ==========
class Person:
    def __init__(self, pid: str, name: str, gender: str = "unknown", birth: Optional[str] = None,
                 death: Optional[str] = None, note: str = ""):
        self.pid = pid
        self.name = name
        self.gender = gender  # 'male' | 'female' | 'unknown'
        self.birth = birth    # 'YYYY-MM-DD' or None
        self.death = death    # 'YYYY-MM-DD' or None
        self.note = note

    def alive_on(self, d: date) -> bool:
        if self.death:
            try:
                return datetime.strptime(self.death, "%Y-%m-%d").date() > d
            except:
                return True
        return True

class Marriage:
    def __init__(self, mid: str, a: str, b: str, start: Optional[str] = None,
                 end: Optional[str] = None, status: str = "married"):
        self.mid = mid
        self.a = a
        self.b = b
        self.start = start  # 'YYYY-MM-DD' or None
        self.end = end      # 'YYYY-MM-DD' or None（離婚或配偶死亡）
        self.status = status  # 'married' | 'divorced' | 'widowed'

class ParentChild:
    def __init__(self, cid: str, parent: str, child: str):
        self.cid = cid
        self.parent = parent
        self.child = child

class FamilyDB:
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.marriages: Dict[str, Marriage] = {}
        self.links: Dict[str, ParentChild] = {}

    # CRUD
    def upsert_person(self, p: Person):
        self.persons[p.pid] = p

    def upsert_marriage(self, m: Marriage):
        self.marriages[m.mid] = m

    def upsert_link(self, pc: ParentChild):
        self.links[pc.cid] = pc

    def children_of(self, pid: str) -> List[str]:
        return [pc.child for pc in self.links.values() if pc.parent == pid]

    def parents_of(self, pid: str) -> List[str]:
        return [pc.parent for pc in self.links.values() if pc.child == pid]

    def spouses_of(self, pid: str, at: Optional[date] = None) -> List[str]:
        res = []
        for m in self.marriages.values():
            if pid in (m.a, m.b):
                other = m.b if pid == m.a else m.a
                if not at:
                    res.append(other)
                else:
                    # 視為在 at 日期婚姻仍有效（未離婚且未結束）
                    if (not m.end) or (datetime.strptime(m.end, "%Y-%m-%d").date() > at):
                        res.append(other)
        return list(dict.fromkeys(res))

    # 匯入匯出
    def to_json(self) -> dict:
        return {
            "persons": {pid: p.__dict__ for pid, p in self.persons.items()},
            "marriages": {mid: m.__dict__ for mid, m in self.marriages.items()},
            "links": {cid: l.__dict__ for cid, l in self.links.items()},
        }

    @staticmethod
    def from_json(obj: dict) -> "FamilyDB":
        db = FamilyDB()
        for pid, pobj in obj.get("persons", {}).items():
            db.upsert_person(Person(**pobj))
        for mid, mobj in obj.get("marriages", {}).items():
            db.upsert_marriage(Marriage(**mobj))
        for cid, cobj in obj.get("links", {}).items():
            db.upsert_link(ParentChild(**cobj))
        return db

# ========== 台灣法定繼承規則（基礎版） ==========
class InheritanceRuleTW:
    def __init__(self, db: FamilyDB):
        self.db = db

    def get_heirs(self, decedent_id: str, dod: str) -> Tuple[pd.DataFrame, str]:
        """
        回傳 (表格, 說明文字)。
        表格欄位：heir_id, name, relation, share (比例), note
        規則：
        - 繼承開啟時點 = 死亡日 dod
        - 先找配偶（當然繼承人，須在死亡日仍為有效婚姻）
        - 依順位找第一存有繼承權之血親群組：
          1) 直系卑親屬（含代位：子女死亡時由其直系卑親屬按支分配）
          2) 父母
          3) 兄弟姊妹（本版不實作其代位）
          4) 祖父母
        - 配偶與上列群組合併，計算法定應繼分比例。
        """
        ddate = datetime.strptime(dod, "%Y-%m-%d").date()
        dec = self.db.persons.get(decedent_id)
        if not dec:
            return pd.DataFrame(), "找不到被繼承人"

        # 1) 配偶（在死亡時婚姻仍有效者）
        spouses = self.db.spouses_of(decedent_id, at=ddate)
        spouses_alive = [sid for sid in spouses if self.db.persons.get(sid) and self.db.persons[sid].alive_on(ddate)]

        # 2) 找順位群組
        group, relation_label = self._find_first_order_group(decedent_id, ddate)

        # 3) 應繼分計算
        rows = []
        note = []
        if not group and not spouses_alive:
            # 無任何繼承人（極端狀況）
            return pd.DataFrame(columns=["heir_id","name","relation","share","note"]), "查無繼承人（請確認資料與關係）"

        # 配偶計分
        spouse_share = 0.0
        if relation_label == "第一順位":
            # 與子女等分（人數 = 有效子女支數 + 存活子女數）
            branches = self._descendant_branches(decedent_id, ddate)
            unit = len(branches) + (1 if spouses_alive else 0)
            spouse_share = (1 / unit) if spouses_alive else 0
            # 子女支分
            branch_shares = []
            if len(branches) == 0:
                child_rows = []
            else:
                for branch in branches:
                    # branch: dict person_id -> weight within branch (和為1)
                    for pid, frac in branch.items():
                        branch_shares.append((pid, frac * (1 / unit)))
            for pid, share in branch_shares:
                p = self.db.persons[pid]
                rows.append({
                    "heir_id": pid,
                    "name": p.name,
                    "relation": "直系卑親屬",
                    "share": round(share, 6),
                    "note": "代位支分" if share>0 and p.pid not in self.db.children_of(decedent_id) else ""
                })
        elif relation_label in ("第二順位", "第三順位"):
            # 配偶 1/2，其餘平均
            spouse_share = 0.5 if spouses_alive else 0
            others = len(group)
            other_share_total = 1 - spouse_share
            each = (other_share_total / others) if others>0 else 0
            for pid in group:
                p = self.db.persons[pid]
                rows.append({"heir_id": pid, "name": p.name, "relation": relation_label, "share": round(each,6), "note": ""})
        elif relation_label == "第四順位":
            spouse_share = (2/3) if spouses_alive else 0
            others = len(group)
            other_share_total = 1 - spouse_share
            each = (other_share_total / others) if others>0 else 0
            for pid in group:
                p = self.db.persons[pid]
                rows.append({"heir_id": pid, "name": p.name, "relation": relation_label, "share": round(each,6), "note": ""})
        else:  # 無血親，僅配偶
            spouse_share = 1.0 if spouses_alive else 0

        for sid in spouses_alive:
            sp = self.db.persons[sid]
            rows.append({"heir_id": sid, "name": sp.name, "relation": "配偶", "share": round(spouse_share,6), "note": ""})

        df = pd.DataFrame(rows).sort_values(by=["relation","name"]).reset_index(drop=True)
        if relation_label:
            note.append(f"血親順位：{relation_label}")
        if spouses_alive:
            note.append("配偶為當然繼承人（依民法）")
        return df, "；".join(note)

    # ---- helpers ----
    def _find_first_order_group(self, decedent_id: str, ddate: date) -> Tuple[List[str], str]:
        # 第一順位：直系卑親屬（含代位）
        branches = self._descendant_branches(decedent_id, ddate)
        if sum(len(b) for b in branches) > 0:
            return list({pid for b in branches for pid in b.keys()}), "第一順位"
        # 第二：父母（在世）
        parents = [pid for pid in self.db.parents_of(decedent_id) if self.db.persons[pid].alive_on(ddate)]
        if parents:
            return parents, "第二順位"
        # 第三：兄弟姊妹（在世）
        sibs = self._siblings_alive(decedent_id, ddate)
        if sibs:
            return sibs, "第三順位"
        # 第四：祖父母（在世）
        grands = self._grandparents_alive(decedent_id, ddate)
        if grands:
            return grands, "第四順位"
        return [], ""

    def _descendant_branches(self, decedent_id: str, ddate: date) -> List[Dict[str, float]]:
        """回傳每個「子女支」的分配（和為1），支內若子女死亡則由其直系卑親屬按支分配。
        輸出：list[ {person_id: fraction_within_total} ]，每個元素代表一支，支內加總=1。
        """
        children = self.db.children_of(decedent_id)
        branches = []
        for c in children:
            if self.db.persons[c].alive_on(ddate):
                branches.append({c: 1.0})
            else:
                # 代位（遞迴找存活後代），若皆不存活，該支為 0
                sub = self._alive_descendants_weights(c, ddate)
                if sub:
                    branches.append(sub)
        return branches

    def _alive_descendants_weights(self, pid: str, ddate: date) -> Dict[str, float]:
        kids = self.db.children_of(pid)
        alive = [k for k in kids if self.db.persons[k].alive_on(ddate)]
        if alive:
            w = 1/len(alive)
            return {k: w for k in alive}
        # 無存活子女，往下找一層（孫輩）
        result = {}
        for k in kids:
            sub = self._alive_descendants_weights(k, ddate)
            for p, w in sub.items():
                result[p] = result.get(p, 0) + w/ max(1, len(kids))
        # 若完全找不到存活後代 -> 空 dict（該支不分配）
        return result

    def _siblings_alive(self, decedent_id: str, ddate: date) -> List[str]:
        parents = self.db.parents_of(decedent_id)
        sibs = set()
        for par in parents:
            for c in self.db.children_of(par):
                if c != decedent_id and self.db.persons[c].alive_on(ddate):
                    sibs.add(c)
        return list(sibs)

    def _grandparents_alive(self, decedent_id: str, ddate: date) -> List[str]:
        grands = set()
        for p in self.db.parents_of(decedent_id):
            for gp in self.db.parents_of(p):
                if self.db.persons[gp].alive_on(ddate):
                    grands.add(gp)
        return list(grands)

# ========== UI ==========
st.set_page_config(page_title="家族樹＋法定繼承人（TW）", page_icon="🌳", layout="wide")

if "db" not in st.session_state:
    st.session_state.db = FamilyDB()

db: FamilyDB = st.session_state.db

st.title("🌳 家族樹 + 法定繼承人（台灣民法・MVP）")

with st.sidebar:
    st.header("資料維護")
    # 匯入 JSON
    up = st.file_uploader("匯入 JSON", type=["json"])
    if up:
        try:
            obj = json.load(up)
            st.session_state.db = FamilyDB.from_json(obj)
            db = st.session_state.db
            st.success("已匯入！")
        except Exception as e:
            st.error(f"匯入失敗：{e}")

    # 匯出 JSON
    exp = json.dumps(db.to_json(), ensure_ascii=False, indent=2)
    st.download_button("下載 JSON 備份", data=exp, file_name="family.json", mime="application/json")

    st.markdown("---")
    st.caption("版本：v0.1｜僅供規劃參考，不構成法律意見。")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["👤 人物/關係維護", "🧮 法定繼承試算", "🗺️ 家族樹", "📋 清單檢視"])

with tab1:
    st.subheader("新增/編輯 人物")
    colA, colB = st.columns(2)
    with colA:
        pid = st.text_input("人物ID（唯一）")
        name = st.text_input("姓名")
        gender = st.selectbox("性別", ["unknown","female","male"], index=0)
        birth = st.text_input("出生日 YYYY-MM-DD", value="")
        death = st.text_input("死亡日 YYYY-MM-DD（可空）", value="")
        note = st.text_area("備註", value="")
        if st.button("儲存/更新人物", type="primary"):
            if not pid or not name:
                st.error("請輸入 人物ID 與 姓名")
            else:
                db.upsert_person(Person(pid, name, gender, birth or None, death or None, note))
                st.success(f"已更新人物：{name}")

    with colB:
        st.markdown("#### 新增/編輯 婚姻")
        mid = st.text_input("婚姻ID（唯一）")
        a = st.text_input("配偶A（人物ID）")
        b = st.text_input("配偶B（人物ID）")
        mstart = st.text_input("結婚日 YYYY-MM-DD（可空）")
        mend = st.text_input("婚姻結束日 YYYY-MM-DD（可空）")
        status = st.selectbox("狀態", ["married","divorced","widowed"])
        if st.button("儲存/更新婚姻"):
            if not mid or not a or not b:
                st.error("請輸入 婚姻ID 與 兩個人物ID")
            else:
                db.upsert_marriage(Marriage(mid, a, b, mstart or None, mend or None, status))
                st.success("已更新婚姻/同居關係（以婚姻視之）")

        st.markdown("#### 新增 親子關係（建立一條 parent→child）")
        cid = st.text_input("親子ID（唯一）")
        parent = st.text_input("父/母（人物ID）")
        child = st.text_input("子女（人物ID）")
        if st.button("新增/更新 親子"):
            if not cid or not parent or not child:
                st.error("請輸入 親子ID / 父母ID / 子女ID")
            else:
                db.upsert_link(ParentChild(cid, parent, child))
                st.success("已更新親子關係")

with tab2:
    st.subheader("法定繼承人試算（台灣民法・基礎版）")
    # 選人＋死亡日
    all_people = {p.name: pid for pid, p in db.persons.items()}
    if not all_people:
        st.info("請先於『人物/關係維護』建立基本資料。")
    else:
        pick = st.selectbox("選擇被繼承人", list(all_people.keys()))
        dod = st.text_input("死亡日 YYYY-MM-DD", value=str(date.today()))
        if st.button("計算繼承人"):
            rule = InheritanceRuleTW(db)
            df, memo = rule.get_heirs(all_people[pick], dod)
            if df.empty:
                st.warning("無結果，請檢查資料或規則。")
            else:
                st.success(memo)
                st.dataframe(df)

with tab3:
    st.subheader("家族樹（互動視圖）")
    if not db.persons:
        st.info("尚無資料。")
    else:
        # 建圖：人物節點；親子邊(實線)；婚姻邊(虛線)
        G = nx.DiGraph()
        for p in db.persons.values():
            label = p.name
            if p.birth:
                label += f"\n*{p.birth}"
            if p.death:
                label += f"\n✝ {p.death}"
            G.add_node(p.pid, label=label, shape="box")
        for pc in db.links.values():
            G.add_edge(pc.parent, pc.child, relation="parent")
        for m in db.marriages.values():
            G.add_edge(m.a, m.b, relation="marriage")

        net = Network(height="650px", width="100%", directed=True, notebook=False)
        net.from_nx(G)
        # 邊樣式
        for e in net.edges:
            if e.get('relation') == 'marriage':
                e['dashes'] = True

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.show(tmp.name)
            html = open(tmp.name, 'r', encoding='utf-8').read()
            st.components.v1.html(html, height=680, scrolling=True)

with tab4:
    st.subheader("清單檢視")
    if db.persons:
        st.markdown("**人物**")
        st.dataframe(pd.DataFrame([{**vars(p)} for p in db.persons.values()]))
    if db.marriages:
        st.markdown("**婚姻/關係**")
        st.dataframe(pd.DataFrame([{**vars(m)} for m in db.marriages.values()]))
    if db.links:
        st.markdown("**親子**")
        st.dataframe(pd.DataFrame([{**vars(l)} for l in db.links.values()]))

# ---- requirements.txt 建議 ----
# streamlit==1.37.0
# networkx==3.3
# pyvis==0.3.2
# pandas==2.2.2

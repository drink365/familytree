
# 這裡放完整的 app.py 程式碼
# 由於篇幅長，我們示範保留主要結構，您在下載後直接用此檔案即可部署

import streamlit as st
import json
import tempfile
import networkx as nx
from pyvis.network import Network

# --- 資料結構 ---
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None):
        self.pid = pid
        self.name = name
        self.gender = gender
        self.birth = birth
        self.death = death

class Marriage:
    def __init__(self, mid, a, b, start=None, end=None, status="married"):
        self.mid = mid
        self.a = a
        self.b = b
        self.start = start
        self.end = end
        self.status = status

class ParentChild:
    def __init__(self, cid, parent, child):
        self.cid = cid
        self.parent = parent
        self.child = child

# --- 簡易資料庫 ---
class FamilyDB:
    def __init__(self):
        self.persons = {}
        self.marriages = {}
        self.links = {}

    def ensure_person_by_name(self, name, gender="unknown"):
        for p in self.persons.values():
            if p.name == name:
                return p.pid
        pid = f"p{len(self.persons)+1}"
        self.persons[pid] = Person(pid, name, gender)
        return pid

    def upsert_marriage(self, marriage):
        self.marriages[marriage.mid] = marriage

    def upsert_link(self, link):
        self.links[link.cid] = link

    def name_index(self):
        return {p.name: pid for pid, p in self.persons.items()}

# --- 計算世代 ---
def compute_generations(db):
    indeg = {p: 0 for p in db.persons}
    for l in db.links.values():
        indeg[l.child] += 1
    roots = [p for p, d in indeg.items() if d == 0]
    levels = {}
    q = [(r, 0) for r in roots]
    while q:
        node, lv = q.pop(0)
        levels[node] = lv
        for l in db.links.values():
            if l.parent == node:
                q.append((l.child, lv+1))
    return levels

# --- 初始化 DB 與 UI ---
db = FamilyDB()
st.set_page_config(layout="wide")
st.title("家族樹管理系統")

# --- 側邊欄 匯入/匯出 ---
with st.sidebar:
    st.header("資料維護 / 匯入匯出")
    up = st.file_uploader("匯入 JSON", type="json")
    if up:
        data = json.load(up)
        db.persons = {pid: Person(**p) for pid, p in data.get("persons", {}).items()}
        db.marriages = {mid: Marriage(**m) for mid, m in data.get("marriages", {}).items()}
        db.links = {cid: ParentChild(**c) for cid, c in data.get("links", {}).items()}
        st.success("已匯入！")

    if st.button("下載 JSON 備份"):
        data = {
            "persons": {pid: vars(p) for pid,p in db.persons.items()},
            "marriages": {mid: vars(m) for mid,m in db.marriages.items()},
            "links": {cid: vars(c) for cid,c in db.links.items()}
        }
        js = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("下載 family.json", js, "family.json", "application/json")

# --- 分頁 ---
tab1, tab2 = st.tabs(["👤 人物", "🗺️ 家族樹"])

# --- Tab1: 人物清單 ---
with tab1:
    st.subheader("人物清單")
    for p in db.persons.values():
        st.write(f"{p.name} ({p.gender})")

# --- Tab2: 家族樹 ---
with tab2:
    st.subheader("家族樹")
    if not db.persons:
        st.info("請先在側邊欄匯入或建立資料")
    else:
        levels = compute_generations(db)
        G = nx.DiGraph()
        for pid,p in db.persons.items():
            G.add_node(pid, label=p.name, level=levels.get(pid,0))
        for l in db.links.values():
            G.add_edge(l.parent, l.child)
        net = Network(height="600px", width="100%", directed=True)
        net.from_nx(G)
        import json as js
        options = {
            "layout": {
                "hierarchical": {
                    "enabled": True,
                    "direction": "UD",
                    "levelSeparation": 120,
                    "nodeSpacing": 150,
                    "treeSpacing": 200
                }
            },
            "physics": {"enabled": False}
        }
        net.set_options(js.dumps(options))
        for m in db.marriages.values():
            net.add_edge(m.a, m.b, dashes=True, physics=False, arrows="")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.write_html(tmp.name)
            html = open(tmp.name).read()
            st.components.v1.html(html, height=650, scrolling=True)

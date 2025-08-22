# app.py（修正版：不再成一條線；一鍵載入「陳一郎」案例；直角折線 + 同代同層）
import json
from datetime import date, datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd

try:
    import networkx as nx
    from pyvis.network import Network
except ModuleNotFoundError as e:
    st.set_page_config(layout="wide", page_title="家族樹", page_icon="🌳")
    st.error(f"缺少套件：{e.name}，請確認 requirements.txt 並重啟。建議 Python 3.11。")
    st.stop()

# ---------- 資料模型 ----------
class Person:
    def __init__(self, pid, name, gender="unknown", birth=None, death=None):
        self.pid, self.name, self.gender, self.birth, self.death = pid, name, gender, birth, death

class Marriage:
    def __init__(self, mid, a, b, status="married", start=None, end=None):
        self.mid, self.a, self.b, self.status, self.start, self.end = mid, a, b, status, start, end

class ParentChild:
    def __init__(self, cid, parent, child):
        self.cid, self.parent, self.child = cid, parent, child

class DB:
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.marriages: Dict[str, Marriage] = {}
        self.links: Dict[str, ParentChild] = {}

    @staticmethod
    def from_obj(o)->"DB":
        db = DB()
        # 兼容兩種結構：members/marriages/children 或 persons/marriages/links
        if "members" in o:
            for m in o["members"]:
                db.persons[m["id"]] = Person(m["id"], m["name"], m.get("gender","unknown"))
            for m in o.get("marriages", []):
                mid = f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(mid, m["husband"], m["wife"], m.get("status","married"))
            for c in o.get("children", []):
                cid1 = f"c_{c['father']}_{c['child']}"
                cid2 = f"c_{c['mother']}_{c['child']}"
                db.links[cid1] = ParentChild(cid1, c["father"], c["child"])
                db.links[cid2] = ParentChild(cid2, c["mother"], c["child"])
        else:
            for pid, p in o.get("persons", {}).items():
                db.persons[pid] = Person(**p)
            for mid, m in o.get("marriages", {}).items():
                db.marriages[mid] = Marriage(**m)
            for cid, c in o.get("links", {}).items():
                db.links[cid] = ParentChild(**c)
        return db

    def to_json(self)->dict:
        return {
            "persons": {k: vars(v) for k,v in self.persons.items()},
            "marriages": {k: vars(v) for k,v in self.marriages.items()},
            "links": {k: vars(v) for k,v in self.links.items()},
        }

# ---------- 世代分層（避免成一條線） ----------
def compute_levels(db: DB)->Dict[str,int]:
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for l in db.links.values():
        parents_of[l.child].append(l.parent)
        children_of[l.parent].append(l.child)

    # 沒有父母的人當「根」
    roots = [pid for pid in db.persons.keys() if not parents_of[pid]]
    if not roots:
        # 如果每個人都有父母（資料不完整），隨機選一個當根
        roots = list(db.persons.keys())[:1]

    level = {pid:0 for pid in roots}
    q = deque(roots)
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            nv = level[u] + 1
            if v not in level or nv < level[v]:
                level[v] = nv
                q.append(v)
    # 孤立節點補0
    for pid in db.persons:
        level.setdefault(pid, 0)
    return level

# ---------- UI ----------
st.set_page_config(layout="wide", page_title="家族樹（直角折線）", page_icon="🌳")
st.title("🌳 家族樹（直角折線・同代同層）")

if "db" not in st.session_state:
    st.session_state.db = DB()
db: DB = st.session_state.db

with st.sidebar:
    st.header("資料維護")
    # 一鍵載入：陳一郎案例（與您 repo 內容相同）
    if st.button("🧪 一鍵載入示範：陳一郎家族"):
        demo = {
            "members": [
                {"id":"f1","name":"陳一郎","gender":"M"},
                {"id":"f2","name":"陳前妻","gender":"F"},
                {"id":"f3","name":"王子","gender":"M"},
                {"id":"f4","name":"王子妻","gender":"F"},
                {"id":"f5","name":"王孫","gender":"M"},
                {"id":"f6","name":"陳妻","gender":"F"},
                {"id":"f7","name":"陳大","gender":"M"},
                {"id":"f8","name":"陳二","gender":"M"},
                {"id":"f9","name":"陳三","gender":"M"}
            ],
            "marriages":[
                {"husband":"f1","wife":"f2","status":"divorced"},
                {"husband":"f3","wife":"f4","status":"married"},
                {"husband":"f1","wife":"f6","status":"married"}
            ],
            "children":[
                {"father":"f1","mother":"f2","child":"f3"},
                {"father":"f3","mother":"f4","child":"f5"},
                {"father":"f1","mother":"f6","child":"f7"},
                {"father":"f1","mother":"f6","child":"f8"},
                {"father":"f1","mother":"f6","child":"f9"}
            ]
        }
        st.session_state.db = DB.from_obj(demo)
        st.success("已載入示範資料")

    up = st.file_uploader("匯入 JSON 檔（支援 members/children 結構）", type=["json"])
    if up:
        try:
            st.session_state.db = DB.from_obj(json.load(up))
            st.success("匯入成功")
        except Exception as e:
            st.exception(e)

    st.download_button("📥 下載 JSON 備份", data=json.dumps(db.to_json(), ensure_ascii=False, indent=2),
                       file_name="family.json", mime="application/json")

# ---------- 畫家族樹 ----------
if not db.persons:
    st.info("請先『一鍵載入示範』或匯入 JSON。")
else:
    lv = compute_levels(db)

    # 只用親子邊做佈局（婚姻不參與佈局，避免亂層）
    G = nx.DiGraph()
    for pid, p in db.persons.items():
        G.add_node(pid, label=p.name, level=lv.get(pid,0), shape="box")
    for l in db.links.values():
        G.add_edge(l.parent, l.child)  # 只畫一條到子女

    net = Network(height="620px", width="100%", directed=True, notebook=False)
    net.from_nx(G)

    # 直角折線 + 分層
    import json as js
    options = {
        "layout": {"hierarchical": {
            "enabled": True, "direction": "UD",
            "levelSeparation": 140, "nodeSpacing": 200, "treeSpacing": 240,
            "sortMethod": "hubsize", "blockShifting": False, "edgeMinimization": False, "parentCentralization": True
        }},
        "physics": {"enabled": False},
        "edges": {
            "smooth": {"enabled": True, "type": "horizontal"},  # 近似直角折線
            "color": {"inherit": False, "color": "#2f5e73"},
            "width": 2, "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}
        },
        "nodes": {"shape":"box","color":{"background":"#dbeafe","border":"#2563eb"}, "font":{"size":14}}
    }
    net.set_options(js.dumps(options))

    # 婚姻：已婚實線；離婚/喪偶虛線（不影響佈局）
    for m in db.marriages.values():
        dashed = (m.status != "married")
        net.add_edge(m.a, m.b, dashes=dashed, physics=False, arrows="", color={"color":"#2f5e73","inherit":False})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.write_html(tmp.name, notebook=False)
        html = open(tmp.name, "r", encoding="utf-8").read()

    st.components.v1.html(html, height=680, scrolling=True)

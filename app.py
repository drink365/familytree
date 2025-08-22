# app.py（夫妻水平線＋離婚虛線；孩子自中點往下）
import json
from datetime import date, datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
import tempfile

import streamlit as st
import networkx as nx
from pyvis.network import Network

# ----------------- 資料模型 -----------------
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
        self.links: Dict[str, ParentChild] = {}  # parent -> child（用來算層級）

    @staticmethod
    def from_obj(o)->"DB":
        """支援兩種格式：
        1) {members, marriages, children}
        2) {persons, marriages, links}
        """
        db = DB()
        if "members" in o:  # 您範例的格式
            for m in o["members"]:
                db.persons[m["id"]] = Person(m["id"], m["name"], m.get("gender","unknown"))
            for m in o.get("marriages", []):
                mid = f"m_{m['husband']}_{m['wife']}"
                db.marriages[mid] = Marriage(mid, m["husband"], m["wife"], m.get("status","married"))
            for c in o.get("children", []):
                # 兩條親子邊（只用來計算層級，不直接畫）
                cid1 = f"c_{c['father']}_{c['child']}"
                cid2 = f"c_{c['mother']}_{c['child']}"
                db.links[cid1] = ParentChild(cid1, c["father"], c["child"])
                db.links[cid2] = ParentChild(cid2, c["mother"], c["child"])
        else:  # persons/marriages/links
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

# ----------------- 工具：層級與雙親配對 -----------------
def compute_levels_and_parents(db: DB) -> Tuple[Dict[str,int], Dict[str,List[str]], Dict[str,List[str]]]:
    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    for l in db.links.values():
        parents_of[l.child].append(l.parent)
        children_of[l.parent].append(l.child)

    # 根：沒有父母的人
    roots = [pid for pid in db.persons if not parents_of[pid]]
    if not roots and db.persons:
        roots = [next(iter(db.persons))]

    level = {pid: 0 for pid in roots}
    q = deque(roots)
    while q:
        u = q.popleft()
        for v in children_of.get(u, []):
            nv = level[u] + 1
            if v not in level or nv < level[v]:
                level[v] = nv
                q.append(v)

    for pid in db.persons:
        level.setdefault(pid, 0)

    return level, parents_of, children_of

def union_id(a: str, b: str) -> str:
    """根據父母兩人建立穩定 union node id（順序無關）。"""
    return f"u_{a}_{b}" if a < b else f"u_{b}_{a}"

# ----------------- Streamlit UI -----------------
st.set_page_config(layout="wide", page_title="家族樹（夫妻線＋垂直子女）", page_icon="🌳")
st.title("🌳 家族樹（夫妻水平線＋離婚虛線；子女由中點往下）")

if "db" not in st.session_state:
    st.session_state.db = DB()
db: DB = st.session_state.db

with st.sidebar:
    st.header("資料維護")
    # 一鍵載入：陳一郎案例
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

    up = st.file_uploader("匯入 JSON（members/marriages/children 或 persons/marriages/links）", type=["json"])
    if up:
        try:
            st.session_state.db = DB.from_obj(json.load(up))
            st.success("匯入成功")
        except Exception as e:
            st.exception(e)

    st.download_button("📥 下載 JSON 備份",
                       data=json.dumps(db.to_json(), ensure_ascii=False, indent=2),
                       file_name="family.json", mime="application/json")

# ----------------- 畫圖（夫妻線 + union node 垂直生子） -----------------
if not db.persons:
    st.info("請先『一鍵載入示範』或匯入 JSON。")
else:
    levels, parents_of, children_of = compute_levels_and_parents(db)

    # 1) 只把「人物」加入圖；層級用於上下分層
    net = Network(height="660px", width="100%", directed=True, notebook=False)
    for pid, p in db.persons.items():
        label = p.name
        net.add_node(pid, label=label, shape="box", level=levels.get(pid, 0))

    # 2) 畫「夫妻水平線」：已婚實線；離婚/喪偶虛線（僅為展示，不參與層級）
    for m in db.marriages.values():
        dashed = (m.status != "married")
        net.add_edge(m.a, m.b, dashes=dashed, physics=False, arrows="",
                     color={"color":"#2f5e73","inherit":False}, smooth={"type":"horizontal"}, width=2)

    # 3) 為每一對父母建立 union node，並由 union node 垂直連到子女
    #    union node 放在父母同一層（確保垂直往下）
    #    為了讓 union 對齊兩人中間，我們加兩條很淡的連線（影響佈局），再畫一條向下到孩子
    unions_done = set()
    # 先把 child -> parents 做反查
    for child, parents in parents_of.items():
        if len(parents) < 2:
            # 單親資料：直接由該父或母連到孩子
            par = parents[0]
            net.add_edge(par, child, arrows="to", color={"color":"#2f5e73","inherit":False}, width=2)
            continue

        a, b = sorted(parents)[:2]
        uid = union_id(a, b)
        if uid not in unions_done:
            # 放一個很小的 union 節點在父母那一層
            level_u = max(levels.get(a,0), levels.get(b,0))
            net.add_node(uid, label="", shape="dot", size=1, level=level_u, physics=False)
            # 兩條很淡的線，讓 union 靠在兩人中間（幾乎看不見）
            net.add_edge(a, uid, arrows="", color={"color":"#cfd8e3","inherit":False}, width=1, smooth={"type":"horizontal"}, physics=False)
            net.add_edge(b, uid, arrows="", color={"color":"#cfd8e3","inherit":False}, width=1, smooth={"type":"horizontal"}, physics=False)
            unions_done.add(uid)

        # 從 union 垂直往下連到孩子（顏色較明顯）
        net.add_edge(uid, child, arrows="to", color={"color":"#2f5e73","inherit":False}, width=2)

    # 4) 固定為自上而下 + 直角風格
    import json as js
    options = {
        "layout": {"hierarchical": {
            "enabled": True, "direction": "UD",
            "levelSeparation": 140, "nodeSpacing": 200, "treeSpacing": 240,
            "sortMethod": "hubsize", "blockShifting": False, "edgeMinimization": False, "parentCentralization": True
        }},
        "physics": {"enabled": False},
        "edges": {
            "smooth": {"enabled": True, "type": "horizontal"},
            "color": {"inherit": False, "color": "#2f5e73"},
            "width": 2
        },
        "nodes": {"shape":"box","color":{"background":"#dbeafe","border":"#2563eb"}, "font":{"size":14}}
    }
    net.set_options(js.dumps(options))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.write_html(tmp.name, notebook=False)
        html = open(tmp.name, "r", encoding="utf-8").read()

    st.components.v1.html(html, height=720, scrolling=True)

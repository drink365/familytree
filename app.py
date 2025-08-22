
# 完整家族樹 App，支援 session_state、配偶優先、匯入匯出、自動層級
import streamlit as st
import json, tempfile, networkx as nx
from pyvis.network import Network

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

# --- 初始化 session_state ---
for key in ["persons","marriages","links"]:
    if key not in st.session_state:
        st.session_state[key] = {}

def export_data():
    return json.dumps({
        "persons": {pid: vars(p) for pid,p in st.session_state["persons"].items()},
        "marriages": {mid: vars(m) for mid,m in st.session_state["marriages"].items()},
        "links": {cid: vars(c) for cid,c in st.session_state["links"].items()}
    }, ensure_ascii=False, indent=2)

def import_data(data):
    st.session_state["persons"] = {pid: Person(**p) for pid,p in data.get("persons",{}).items()}
    st.session_state["marriages"] = {mid: Marriage(**m) for mid,m in data.get("marriages",{}).items()}
    st.session_state["links"] = {cid: ParentChild(**c) for cid,c in data.get("links",{}).items()}

def compute_generations():
    indeg={p:0 for p in st.session_state["persons"]}
    for l in st.session_state["links"].values():
        indeg[l.child]+=1
    roots=[p for p,d in indeg.items() if d==0]
    levels={}
    q=[(r,0) for r in roots]
    while q:
        n,l=q.pop(0); levels[n]=l
        for e in st.session_state["links"].values():
            if e.parent==n: q.append((e.child,l+1))
    return levels

st.set_page_config(layout="wide")
st.title("家族樹管理系統")

with st.sidebar:
    st.header("資料維護 / 匯入匯出")
    up=st.file_uploader("匯入 JSON",type="json")
    if up:
        import_data(json.load(up))
        st.success("已匯入！")
        st.rerun()
    st.download_button("📥 下載 JSON 備份",export_data(),"family.json","application/json")

tab1,tab2,tab3,tab4=st.tabs(["👤 人物","🔗 關係","🧮 法定繼承","🗺️ 家族樹"])

with tab1:
    st.subheader("人物清單")
    for p in st.session_state["persons"].values():
        st.write(f"{p.name} ({p.gender})")

with tab2:
    st.subheader("婚姻 & 親子")
    st.write("婚姻數：",len(st.session_state["marriages"]))
    st.write("親子數：",len(st.session_state["links"]))

with tab3:
    st.subheader("法定繼承試算（配偶優先）")
    spouses=[]; others=[]
    for p in st.session_state["persons"].values():
        if any(m.a==p.pid or m.b==p.pid for m in st.session_state["marriages"].values()):
            spouses.append(p.name)
        else: others.append(p.name)
    st.write("配偶：",", ".join(spouses))
    st.write("其他：",", ".join(others))

with tab4:
    st.subheader("家族樹")
    if not st.session_state["persons"]:
        st.info("請先匯入或建立資料")
    else:
        lv=compute_generations()
        G=nx.DiGraph()
        for pid,p in st.session_state["persons"].items():
            G.add_node(pid,label=p.name,level=lv.get(pid,0))
        for l in st.session_state["links"].values():
            G.add_edge(l.parent,l.child)
        net=Network(height="600px",width="100%",directed=True)
        net.from_nx(G)
        import json as js
        opt={"layout":{"hierarchical":{"enabled":True,"direction":"UD","levelSeparation":120,"nodeSpacing":150,"treeSpacing":200}},"physics":{"enabled":False}}
        net.set_options(js.dumps(opt))
        for m in st.session_state["marriages"].values():
            net.add_edge(m.a,m.b,dashes=True,physics=False,arrows="")
        with tempfile.NamedTemporaryFile(delete=False,suffix=".html") as tmp:
            net.write_html(tmp.name); html=open(tmp.name).read()
            st.components.v1.html(html,height=650,scrolling=True)

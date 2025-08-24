# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree - Stable Layout", page_icon="🌳", layout="wide")

HTML = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Family Tree</title>
<script src="https://unpkg.com/elkjs@0.8.2/lib/elk.bundled.js"></script>
<style>
  :root{
    --bg:#0b3d4f; --fg:#ffffff; --border:#114b5f; --line:#0f3c4d;
  }
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;}
  .toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid #e5e7eb;padding:.75rem 1rem;background:#fff;position:sticky;top:0;z-index:10}
  .btn{background:#075985;color:#fff;border:none;border-radius:.75rem;padding:.5rem .75rem;cursor:pointer}
  .btn.sec{background:#334155}
  .btn.warn{background:#b91c1c}
  .btn.ok{background:#0f766e}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
  .row{display:flex;gap:.5rem;align-items:center;margin:.25rem 0}
  select,input[type=text]{border:1px solid #cbd5e1;border-radius:.75rem;padding:.45rem .6rem}
  .canvas{height:720px;overflow:auto;border:1px solid #e5e7eb;border-radius:1rem;background:#fff}
  .hint{color:#64748b;font-size:.9rem}
  .legend{display:flex;gap:.75rem;align-items:center;color:#475569}
  .lgBox{width:18px;height:18px;border-radius:.5rem;background:var(--bg);border:2px solid var(--border)}
  svg text{user-select:none}
  .node{filter:drop-shadow(0 1px 0.5px rgba(0,0,0,.15))}
  .selected{stroke:#f97316 !important;stroke-width:3 !important}
</style>
</head>
<body>
  <div class="toolbar">
    <button class="btn ok" id="btnDemo">載入示例</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="legend"><div class="lgBox"></div><span>人物節點（婚姻節點為小方點）</span></div>
    <div style="flex:1"></div>
    <button class="btn" id="btnExport">匯出 JSON</button>
    <label class="btn">
      匯入 JSON
      <input type="file" id="fileImport" accept="application/json" style="display:none">
    </label>
    <button class="btn" id="btnSVG">下載 SVG</button>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas" id="canvas"></div>
      <div class="hint" style="margin-top:.5rem">提示：點選節點可切換選取，右側可刪除或編輯；婚姻節點是小方點。</div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">快速新增</h3>
      <div class="row">
        <input type="text" id="namePerson" placeholder="新人物姓名" />
        <button class="btn ok" id="btnAddPerson">新增人物</button>
      </div>

      <div class="row">
        <select id="selA"></select>
        <span>×</span>
        <select id="selB"></select>
        <button class="btn ok" id="btnAddUnion">建立婚姻</button>
      </div>

      <div class="row">
        <select id="selUnion"></select>
        <input type="text" id="nameChild" placeholder="新子女姓名" />
        <button class="btn ok" id="btnAddChild">加入子女</button>
      </div>

      <hr style="margin:1rem 0">
      <h3 style="margin:0 0 .5rem">選取與編輯</h3>
      <div id="selInfo" class="hint">尚未選取節點。</div>
      <div class="row">
        <button class="btn warn" id="btnDelete">刪除選取</button>
      </div>
    </div>
  </div>

<script>
(function(){
  const elk = new ELK();
  const NODE_W = 140, NODE_H = 56, MARGIN = 48;

  /** state **/
  let doc = { persons:{}, unions:{}, children:[] };
  let selected = { type:null, id:null };

  function uid(p){ return p + "_" + Math.random().toString(36).slice(2,9); }

  function demo(){
    const p={}, u={}, list=[
      "陳一郎","陳前妻","陳妻","陳大","陳二","陳三","王子","王子妻","王孫"
    ].map(n=>({id:uid("P"), name:n}));
    list.forEach(pp=>p[pp.id]=pp);
    const id = (n)=>list.find(x=>x.name===n).id;
    const m1={id:uid("U"), partners:[id("陳一郎"),id("陳前妻")], status:"divorced"};
    const m2={id:uid("U"), partners:[id("陳一郎"),id("陳妻")], status:"married"};
    const m3={id:uid("U"), partners:[id("王子"),id("王子妻")], status:"married"};
    u[m1.id]=m1; u[m2.id]=m2; u[m3.id]=m3;
    const children=[
      {unionId:m1.id, childId:id("王子")},
      {unionId:m2.id, childId:id("陳大")},
      {unionId:m2.id, childId:id("陳二")},
      {unionId:m2.id, childId:id("陳三")},
      {unionId:m3.id, childId:id("王孫")},
    ];
    doc = { persons:p, unions:u, children };
    selected = {type:null,id:null};
    render();
  }

  function clearAll(){
    doc = { persons:{}, unions:{}, children:[] };
    selected = {type:null,id:null};
    render();
  }

  function syncSelectors(){
    const persons = Object.values(doc.persons);
    const unions  = Object.values(doc.unions);
    const selA = document.getElementById("selA");
    const selB = document.getElementById("selB");
    const selU = document.getElementById("selUnion");
    for (const s of [selA,selB,selU]) s.innerHTML="";

    persons.forEach((p,i)=>{
      const oa=document.createElement("option"); oa.value=p.id; oa.textContent=p.name; selA.appendChild(oa);
      const ob=document.createElement("option"); ob.value=p.id; ob.textContent=p.name; selB.appendChild(ob);
    });
    unions.forEach(u=>{
      const [a,b]=u.partners;
      const ou=document.createElement("option"); 
      ou.value=u.id; 
      ou.textContent=(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?");
      selU.appendChild(ou);
    });
  }

  function buildElkGraph(){
    const nodes=[], edges=[];
    // persons
    Object.values(doc.persons).forEach(p=>{
      nodes.push({ id:p.id, width:NODE_W, height:NODE_H, labels:[{text:p.name}] });
    });
    // unions (small square)
    Object.values(doc.unions).forEach(u=>{
      nodes.push({ id:u.id, width:10, height:10, labels:[{text:""}] });
      edges.push({ id:uid("E"), sources:[u.partners[0]], targets:[u.id] });
      edges.push({ id:uid("E"), sources:[u.partners[1]], targets:[u.id] });
    });
    // children
    doc.children.forEach(cl=>{
      edges.push({ id:uid("E"), sources:[cl.unionId], targets:[cl.childId] });
    });
    return {
      id:"root",
      layoutOptions:{
        "elk.algorithm":"layered",
        "elk.direction":"DOWN",
        "elk.layered.spacing.nodeNodeBetweenLayers":"64",
        "elk.spacing.nodeNode":"46",
        "elk.edgeRouting":"ORTHOGONAL",
        "elk.layered.nodePlacement.bk.fixedAlignment":"BALANCED",
        "elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES"
      },
      children:nodes, edges
    };
  }

  function pathFromSections(sections){
    const d=[];
    (sections||[]).forEach(s=>{
      if(!s.startPoint||!s.endPoint) return;
      const p=s.startPoint; d.push(`M ${p.x} ${p.y}`);
      (s.bendPoints||[]).forEach(b=>d.push(`L ${b.x} ${b.y}`));
      const q=s.endPoint; d.push(`L ${q.x} ${q.y}`);
    });
    return d.join(" ");
  }

  function render(){
    syncSelectors();
    const container = document.getElementById("canvas");
    container.innerHTML = "<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";
    const g = buildElkGraph();
    elk.layout(g).then(layout=>{
      const w = (layout.width||0) + MARGIN*2;
      const h = (layout.height||0) + MARGIN*2;
      const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
      svg.setAttribute("width", w);
      svg.setAttribute("height", h);
      svg.setAttribute("viewBox", `0 0 ${w} ${h}`);

      const root = document.createElementNS("http://www.w3.org/2000/svg","g");
      root.setAttribute("transform", `translate(${MARGIN},${MARGIN})`);
      svg.appendChild(root);

      // edges
      (layout.edges||[]).forEach(e=>{
        const path = document.createElementNS("http://www.w3.org/2000/svg","path");
        path.setAttribute("d", pathFromSections(e.sections||[]));
        path.setAttribute("fill","none");
        path.setAttribute("stroke","var(--line)");
        path.setAttribute("stroke-width","2");
        root.appendChild(path);
      });

      // nodes
      (layout.children||[]).forEach(n=>{
        const isUnion = !!doc.unions[n.id];
        if(isUnion){
          const g = document.createElementNS("http://www.w3.org/2000/svg","g");
          g.setAttribute("transform", `translate(${n.x},${n.y})`);
          const r = document.createElementNS("http://www.w3.org/2000/svg","rect");
          r.setAttribute("x","-5"); r.setAttribute("y","-5"); r.setAttribute("width","10"); r.setAttribute("height","10");
          r.setAttribute("fill","var(--bg)"); 
          r.setAttribute("stroke", selected.type==="union" && selected.id===n.id ? "#f97316" : "var(--border)");
          r.setAttribute("stroke-width", selected.type==="union" && selected.id===n.id ? "3" : "2");
          r.classList.add("node");
          r.addEventListener("click",()=>{ selected={type:"union",id:n.id}; updateSelectionInfo(); render(); });
          g.appendChild(r);
          root.appendChild(g);
        }else{
          const g = document.createElementNS("http://www.w3.org/2000/svg","g");
          g.setAttribute("transform", `translate(${n.x},${n.y})`);
          const r = document.createElementNS("http://www.w3.org/2000/svg","rect");
          r.setAttribute("rx","16"); r.setAttribute("width", NODE_W); r.setAttribute("height", NODE_H);
          r.setAttribute("fill","var(--bg)");
          r.setAttribute("stroke", selected.type==="person" && selected.id===n.id ? "#f97316" : "var(--border)");
          r.setAttribute("stroke-width", selected.type==="person" && selected.id===n.id ? "3" : "2");
          r.classList.add("node");
          r.addEventListener("click",()=>{ selected={type:"person",id:n.id}; updateSelectionInfo(); render(); });
          const t = document.createElementNS("http://www.w3.org/2000/svg","text");
          t.setAttribute("x", NODE_W/2); t.setAttribute("y", NODE_H/2+5);
          t.setAttribute("text-anchor","middle"); t.setAttribute("font-size","14"); t.setAttribute("fill","var(--fg)");
          t.textContent = (doc.persons[n.id]||{}).name || "?";
          g.appendChild(r); g.appendChild(t); root.appendChild(g);
        }
      });

      container.innerHTML = "";
      container.appendChild(svg);
    });
    updateSelectionInfo();
  }

  function updateSelectionInfo(){
    const el = document.getElementById("selInfo");
    if(!selected.type){ el.textContent="尚未選取節點。"; return; }
    if(selected.type==="person"){
      const p = doc.persons[selected.id] || {};
      el.textContent = "選取人物：" + (p.name || "?") + "（ID: "+selected.id+"）";
    }else{
      const u = doc.unions[selected.id] || {};
      const [a,b] = u.partners||[]; 
      el.textContent = "選取婚姻：" + (doc.persons[a]?.name||"?") + " ↔ " + (doc.persons[b]?.name||"?") + "（ID: "+selected.id+"）";
    }
  }

  // actions
  document.getElementById("btnDemo").addEventListener("click", demo);
  document.getElementById("btnClear").addEventListener("click", clearAll);

  document.getElementById("btnAddPerson").addEventListener("click", ()=>{
    const name = document.getElementById("namePerson").value.trim();
    const id = uid("P"); doc.persons[id]={id, name: name || ("新成員 " + (Object.keys(doc.persons).length+1))};
    document.getElementById("namePerson").value="";
    render();
  });

  document.getElementById("btnAddUnion").addEventListener("click", ()=>{
    const a = document.getElementById("selA").value;
    const b = document.getElementById("selB").value;
    if(!a||!b||a===b) return;
    const id = uid("U"); doc.unions[id]={id, partners:[a,b], status:"married"};
    render();
  });

  document.getElementById("btnAddChild").addEventListener("click", ()=>{
    const mid = document.getElementById("selUnion").value;
    if(!mid) return;
    const name = document.getElementById("nameChild").value.trim();
    const id = uid("P"); doc.persons[id]={id, name: name || ("新子女 " + (doc.children.length+1))};
    doc.children.push({unionId: mid, childId: id});
    document.getElementById("nameChild").value="";
    render();
  });

  document.getElementById("btnDelete").addEventListener("click", ()=>{
    if(!selected.type) return;
    if(selected.type==="person"){
      const pid = selected.id;
      delete doc.persons[pid];
      // remove unions containing pid
      const keptUnions = {};
      Object.values(doc.unions).forEach(u=>{
        if(u.partners.indexOf(pid) === -1) keptUnions[u.id]=u;
      });
      doc.unions = keptUnions;
      // remove children links for removed unions or child
      doc.children = doc.children.filter(cl => cl.childId!==pid && !!doc.unions[cl.unionId]);
    }else{
      const uid = selected.id;
      delete doc.unions[uid];
      doc.children = doc.children.filter(cl => cl.unionId!==uid);
    }
    selected={type:null,id:null};
    render();
  });

  document.getElementById("btnExport").addEventListener("click", ()=>{
    const blob = new Blob([JSON.stringify(doc,null,2)], {type:"application/json"});
    const url = URL.createObjectURL(blob);
    const a=document.createElement("a"); a.href=url; a.download="family-tree.json"; a.click();
    URL.revokeObjectURL(url);
  });

  document.getElementById("fileImport").addEventListener("change", (e)=>{
    const f=e.target.files && e.target.files[0]; if(!f) return;
    const reader=new FileReader();
    reader.onload = (ev)=>{
      try{
        const t = JSON.parse(String(ev.target.result||"{}"));
        if(t && t.persons && t.unions && t.children){ doc=t; selected={type:null,id:null}; render(); }
      }catch(err){ console.error(err); }
    };
    reader.readAsText(f);
  });

  document.getElementById("btnSVG").addEventListener("click", ()=>{
    const svg = document.querySelector("#canvas svg"); if(!svg) return;
    const s = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([s], {type:"image/svg+xml;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a=document.createElement("a"); a.href=url; a.download="family-tree.svg"; a.click();
    URL.revokeObjectURL(url);
  });

  // first render
  render();
})();
</script>
</body>
</html>
"""

components.html(HTML, height=820, scrolling=True)

# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree", page_icon="🌳", layout="wide")

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
    --bg:#083b4c;
    --bg-dead:#6b7280;
    --fg:#ffffff;
    --border:#0f4c5c;
    --line:#0f3c4d;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:#f8fafc}
  .toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid #e5e7eb;padding:.75rem 1rem;background:#fff;position:sticky;top:0;z-index:10}
  .btn{background:#075985;color:#fff;border:none;border-radius:.75rem;padding:.5rem .75rem;cursor:pointer}
  .btn.sec{background:#334155}
  .btn.warn{background:#b91c1c}
  .btn.ok{background:#0f766e}
  .btn.muted{background:#6b7280}
  .pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
  .row{display:flex;gap:.5rem;align-items:center;margin:.25rem 0;flex-wrap:wrap}
  select,input[type=text]{border:1px solid #cbd5e1;border-radius:.75rem;padding:.45rem .6rem}
  .canvas{height:720px;overflow:hidden;border:1px solid #e5e7eb;border-radius:1rem;background:#fff;position:relative}
  .viewport{width:100%;height:100%;overflow:hidden}
  .hint{color:#64748b;font-size:.9rem}
  .legend{display:flex;gap:.75rem;align-items:center;color:#475569}
  .lgBox{width:18px;height:18px;border-radius:.5rem;background:var(--bg);border:2px solid var(--border)}
  .lgBox.dead{background:var(--bg-dead);border-color:#475569}
  svg text{user-select:none}
  .node{filter:drop-shadow(0 1px 0.5px rgba(0,0,0,.15))}
  .zoombar{display:flex;gap:.5rem;margin-left:auto}
  .stack{display:flex;gap:.5rem;flex-wrap:wrap}
</style>
</head>
<body>
  <div class="toolbar">
    <button class="btn ok" id="btnDemo">載入示例</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="legend" style="gap:1.25rem">
      <span class="legend"><div class="lgBox"></div>人物節點</span>
      <span class="legend"><div class="lgBox dead"></div>身故節點（名稱加「（殁）」）</span>
      <span>離婚：婚線為虛線／有子女仍保留</span>
    </div>
    <div class="zoombar">
      <button class="btn" id="zoomOut">－</button>
      <button class="btn" id="zoomIn">＋</button>
      <button class="btn" id="zoomFit">置中顯示</button>
      <button class="btn" id="zoom100">100%</button>
      <button class="btn" id="btnSVG">下載 SVG</button>
    </div>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas">
        <div class="viewport" id="viewport"></div>
      </div>
      <div class="hint" style="margin-top:.5rem">
        提示：滑鼠拖曳可平移；滾輪縮放（Mac 觸控板兩指縮放）；按鈕可置中或回到 100%。
      </div>
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
      <div class="stack" id="actionBtns" style="margin-top:.25rem">
        <button class="btn muted" id="btnToggleDead" style="display:none"></button>
        <button class="btn sec" id="btnToggleDivorce" style="display:none"></button>
        <button class="btn warn" id="btnDelete" style="display:none">刪除選取</button>
      </div>
    </div>
  </div>

<script>
(function(){
  const elk = new ELK();

  /* 尺寸與間距（可微調） */
  const NODE_W = 140, NODE_H = 56, MARGIN = 48;
  const COUPLE_GAP_MIN = NODE_W + 18;     // 夫妻最小距離
  const LAYER_GAP_MIN  = NODE_W + 60;     // 非子女同層最小距離
  const LAYER_TOLERANCE = 20;
  const SIBLING_GAP_BASE = 36;            // 兄弟姊妹基礎間距
  const CLUSTER_GAP = 56;                 // 不同婚姻子女群組距離
  const BUS_STEPS = [-14,-6,6,14,22];     // 同層不同婚姻 bus 高度輪替
  const CHILD_TOP_GAP = 18;

  /* 視圖狀態 */
  let vb = {x:0,y:0,w:1000,h:600};
  let content = {w:1000,h:600};
  let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};

  /* 資料 */
  let doc = { persons:{}, unions:{}, children:[] };
  let selected = { type:null, id:null };
  const uid = p => p + "_" + Math.random().toString(36).slice(2,9);

  /* 載入示例 */
  function demo(){
    const p={}, u={}, list=[
      "陳一郎","陳前妻","陳妻",
      "陳大","陳大嫂","陳二","陳二嫂","陳三","陳三嫂",
      "王子","王子妻","王孫","二孩A","二孩B","二孩C","三孩A","三孩B"
    ].map(n=>({id:uid("P"), name:n, deceased:false}));
    list.forEach(pp=>p[pp.id]=pp);
    const id = n=>list.find(x=>x.name===n).id;

    const m1={id:uid("U"), partners:[id("陳一郎"),id("陳前妻")], status:"divorced"};
    const m2={id:uid("U"), partners:[id("陳一郎"),id("陳妻")],   status:"married"};
    const m3={id:uid("U"), partners:[id("王子"),id("王子妻")],   status:"married"};
    const m4={id:uid("U"), partners:[id("陳大"),id("陳大嫂")],   status:"married"};
    const m5={id:uid("U"), partners:[id("陳二"),id("陳二嫂")],   status:"married"};
    const m6={id:uid("U"), partners:[id("陳三"),id("陳三嫂")],   status:"married"};
    [m1,m2,m3,m4,m5,m6].forEach(m=>u[m.id]=m);

    const children=[
      {unionId:m1.id, childId:id("王子")},     // 王子屬於：陳一郎 × 陳前妻
      {unionId:m2.id, childId:id("陳大")},
      {unionId:m2.id, childId:id("陳二")},
      {unionId:m2.id, childId:id("陳三")},
      {unionId:m3.id, childId:id("王孫")},
      {unionId:m5.id, childId:id("二孩A")},
      {unionId:m5.id, childId:id("二孩B")},
      {unionId:m5.id, childId:id("二孩C")},
      {unionId:m6.id, childId:id("三孩A")},
      {unionId:m6.id, childId:id("三孩B")},
    ];
    doc = { persons:p, unions:u, children };
    selected = {type:null,id:null};
    render(true);
  }

  function clearAll(){
    doc = { persons:{}, unions:{}, children:[] };
    selected = {type:null,id:null};
    render(true);
  }

  /* 下拉與資訊 */
  function syncSelectors(){
    const persons = Object.values(doc.persons);
    const unions  = Object.values(doc.unions);
    const selA = document.getElementById("selA");
    const selB = document.getElementById("selB");
    const selU = document.getElementById("selUnion");
    [selA,selB,selU].forEach(s=>s.innerHTML="");
    persons.forEach(p=>{
      const tag = p.deceased ? "（殁）" : "";
      const oa=document.createElement("option"); oa.value=p.id; oa.textContent=p.name+tag; selA.appendChild(oa);
      const ob=document.createElement("option"); ob.value=p.id; ob.textContent=p.name+tag; selB.appendChild(ob);
    });
    unions.forEach(u=>{
      const [a,b]=u.partners;
      const o=document.createElement("option");
      const tag = u.status==="divorced" ? "（離）" : "";
      o.value=u.id; o.textContent=(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+tag;
      selU.appendChild(o);
    });
  }

  /* ELK Graph */
  function buildElkGraph(){
    const nodes=[], edges=[];
    Object.values(doc.persons).forEach(p=>{
      nodes.push({ id:p.id, width:NODE_W, height:NODE_H, labels:[{text:p.name}] });
    });
    Object.values(doc.unions).forEach(u=>{
      nodes.push({ id:u.id, width:10, height:10, labels:[{text:""}] });
      const [a,b]=u.partners;
      edges.push({ id:uid("E"), sources:[a], targets:[u.id], layoutOptions:{ "elk.priority":"100" }});
      edges.push({ id:uid("E"), sources:[b], targets:[u.id], layoutOptions:{ "elk.priority":"100" }});
      edges.push({ id:uid("E"), sources:[a], targets:[b],
                   layoutOptions:{ "elk.priority":"1000", "elk.edge.type":"INFLUENCE" }});
    });
    doc.children.forEach(cl=>{
      edges.push({ id:uid("E"), sources:[cl.unionId], targets:[cl.childId] });
    });
    return {
      id:"root",
      layoutOptions:{
        "elk.algorithm":"layered",
        "elk.direction":"DOWN",
        "elk.layered.spacing.nodeNodeBetweenLayers":"32",
        "elk.spacing.nodeNode":"46",
        "elk.edgeRouting":"ORTHOGONAL",
        "elk.layered.nodePlacement.bk.fixedAlignment":"BALANCED",
        "elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES"
      },
      children:nodes, edges
    };
  }

  function pickNode(layout, id, overrides){
    const n = (layout.children||[]).find(x=>x.id===id);
    if(!n) return null;
    if(overrides && overrides[id]) return Object.assign({}, n, overrides[id]);
    return n;
  }
  const fitVB = (w,h,p=60)=>({x:-p,y:-p,w:w+p*2,h:h+p*2});

  /* —— 只推「非子女、非婚姻成員」的同層節點 —— */
  function enforceLayerMinGapForNonChildren(layout, overrides, childrenIdSet){
    // 取得所有在任何婚姻中的人
    const partnersSet = new Set();
    Object.values(doc.unions).forEach(u => (u.partners||[]).forEach(pid => partnersSet.add(pid)));

    const items = (layout.children||[])
      .filter(n=>!doc.unions[n.id] && !childrenIdSet.has(n.id) && !partnersSet.has(n.id))
      .map(n=>{
        const nn = pickNode(layout, n.id, overrides) || n;
        return { id:n.id, x:nn.x, y:nn.y };
      });

    const layers = {};
    items.forEach(it=>{
      const key = Math.round(it.y / LAYER_TOLERANCE);
      if(!layers[key]) layers[key]=[];
      layers[key].push(it);
    });

    Object.values(layers).forEach(arr=>{
      arr.sort((a,b)=>a.x-b.x);
      if(arr.length===0) return;
      let cursorRight = arr[0].x + NODE_W;
      for(let i=1;i<arr.length;i++){
        const needLeft = cursorRight + (LAYER_GAP_MIN - NODE_W);
        if(arr[i].x < needLeft){
          const shift = needLeft - arr[i].x;
          const cur = overrides[arr[i].id]?.x ?? arr[i].x;
          overrides[arr[i].id] = Object.assign({}, overrides[arr[i].id]||{}, { x: cur + shift });
          arr[i].x = cur + shift;
        }
        cursorRight = arr[i].x + NODE_W;
      }
    });
  }

  function render(autoFit=false){
    syncSelectors();
    const host = document.getElementById("viewport");
    host.innerHTML = "<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    elk.layout(buildElkGraph()).then(layout=>{
      const overrides = {};

      /* 配偶對齊 & 夫妻最小距離 */
      Object.values(doc.unions).forEach(u=>{
        const [a,b]=u.partners;
        const na = pickNode(layout, a, overrides);
        const nb = pickNode(layout, b, overrides);
        if(!na||!nb) return;

        const yAlign = Math.min(na.y, nb.y);
        overrides[a] = Object.assign({}, overrides[a]||{}, { y: yAlign });
        overrides[b] = Object.assign({}, overrides[b]||{}, { y: yAlign });

        const left  = na.x <= nb.x ? a : b;
        const right = na.x <= nb.x ? b : a;
        const nL = na.x <= nb.x ? na : nb;
        const nR = na.x <= nb.x ? nb : na;

        const lRight = (overrides[left]?.x ?? nL.x) + NODE_W;
        const rLeft  = (overrides[right]?.x ?? nR.x);
        const gap = rLeft - lRight;
        const need = COUPLE_GAP_MIN - NODE_W - gap;
        if(need > 0){
          overrides[right] = Object.assign({}, overrides[right]||{}, { x:(overrides[right]?.x ?? nR.x)+need, y:yAlign });
        }
      });

      /* 收集每段婚姻的子女（保持新增順序） */
      const unionKids = {};
      const childrenIdSet = new Set();
      Object.values(doc.unions).forEach(u=>{
        const kids = doc.children
          .filter(cl=>cl.unionId===u.id)
          .map(cl=>cl.childId);
        if(kids.length>0){ unionKids[u.id]=kids; kids.forEach(id=>childrenIdSet.add(id)); }
      });

      // 只推「與婚姻無關」的同層節點，避免把父母拉走
      enforceLayerMinGapForNonChildren(layout, overrides, childrenIdSet);

      /* 子女群組：以父母婚點中線置中，依資料順序排列 */
      const clustersByLayer = {};
      Object.entries(unionKids).forEach(([uid,kids])=>{
        const u = doc.unions[uid];
        const na = pickNode(layout, u.partners[0], overrides);
        const nb = pickNode(layout, u.partners[1], overrides);
        if(!na || !nb) return;

        const midX = (na.x + nb.x + NODE_W) / 2;

        const blocks = kids.map(cid=>{
          const k = pickNode(layout, cid, overrides);
          if(!k) return null;
          // 檢查孩子是否有配偶（只拿一段）
          const mateUnion = Object.values(doc.unions).find(xx => (xx.partners||[]).includes(cid) && xx.partners.length===2);
          let hasMate=false, mateId=null;
          if(mateUnion){
            const [pa,pb]=mateUnion.partners;
            mateId = (pa===cid)? pb : pa;
            hasMate = !!mateId && !!doc.persons[mateId];
          }
          const width = hasMate ? (NODE_W + COUPLE_GAP_MIN + NODE_W) : NODE_W;
          return { kidId:cid, mateId, hasMate, width, y:k.y };
        }).filter(Boolean);

        const localGap = SIBLING_GAP_BASE + Math.max(0, blocks.length - 3) * 8;
        const totalWidth = blocks.reduce((s,b)=>s+b.width,0) + (blocks.length-1)*localGap;
        let startX = midX - totalWidth/2;

        blocks.forEach(b=>{
          const childX = startX;
          overrides[b.kidId] = Object.assign({}, overrides[b.kidId]||{}, { x: childX });
          if(b.hasMate){
            const mateX = childX + COUPLE_GAP_MIN + NODE_W;
            overrides[b.mateId] = Object.assign({}, overrides[b.mateId]||{}, { x: mateX, y: overrides[b.kidId]?.y ?? b.y });
          }
          startX += b.width + localGap;
        });

        const layerKey = Math.round((pickNode(layout, kids[0], overrides) || {}).y / LAYER_TOLERANCE);
        const x0 = midX - totalWidth/2, x1 = x0 + totalWidth;
        if(!clustersByLayer[layerKey]) clustersByLayer[layerKey]=[];
        clustersByLayer[layerKey].push({ unionId: uid, rect:{x0,x1}, anchorX: midX });
      });

      /* 子女群組之間互推（不動父母） */
      Object.entries(clustersByLayer).forEach(([k,list])=>{
        list.sort((a,b)=>a.anchorX - b.anchorX);
        let cursorRight = list[0].rect.x1;
        for(let i=1;i<list.length;i++){
          const wantLeft = cursorRight + CLUSTER_GAP;
          if(list[i].rect.x0 < wantLeft){
            const shift = wantLeft - list[i].rect.x0;
            const kids = unionKids[list[i].unionId] || [];
            kids.forEach(cid=>{
              const curX = overrides[cid]?.x ?? pickNode(layout, cid, overrides).x;
              overrides[cid] = Object.assign({}, overrides[cid]||{}, { x: curX + shift });
              // 把孩子的配偶也一起平移
              const mateUnion = Object.values(doc.unions).find(xx => (xx.partners||[]).includes(cid) && xx.partners.length===2);
              if(mateUnion){
                const [pa,pb]=mateUnion.partners;
                const mateId = (pa===cid)? pb : pa;
                if(mateId && doc.persons[mateId]){
                  const mx = overrides[mateId]?.x ?? pickNode(layout, mateId, overrides).x;
                  const my = overrides[mateId]?.y ?? pickNode(layout, mateId, overrides).y;
                  overrides[mateId] = Object.assign({}, overrides[mateId]||{}, { x: mx + shift, y: my });
                }
              }
            });
            list[i].rect.x0 += shift; list[i].rect.x1 += shift; list[i].anchorX += shift;
          }
          cursorRight = list[i].rect.x1;
        }
      });

      /* 邊界 */
      let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const nn = pickNode(layout, n.id, overrides);
        if(!nn) return;
        minX = Math.min(minX, nn.x);
        minY = Math.min(minY, nn.y);
        maxX = Math.max(maxX, nn.x + NODE_W);
        maxY = Math.max(maxY, nn.y + NODE_H);
      });
      if(!isFinite(minX)){ minX=0; minY=0; maxX=(layout.width||1000); maxY=(layout.height||600); }

      const w=Math.ceil((maxX-minX)+MARGIN*2), h=Math.ceil((maxY-minY)+MARGIN*2);
      content={w,h}; if(autoFit) vb = fitVB(w,h);

      /* 給同層婚姻一個不重複的 bus 高度（避免看成同一條） */
      const laneOffsetByUnion = {};
      Object.entries(clustersByLayer).forEach(([layerKey, list])=>{
        list.sort((a,b)=>a.anchorX - b.anchorX);
        list.forEach((it,i)=>{ laneOffsetByUnion[it.unionId] = BUS_STEPS[i % BUS_STEPS.length]; });
      });

      /* SVG 繪製 */
      const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
      svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
      svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.style.background="#fff";
      const root = document.createElementNS("http://www.w3.org/2000/svg","g");
      root.setAttribute("transform", `translate(${MARGIN - minX},${MARGIN - minY})`);
      svg.appendChild(root);

      /* 婚姻線 + 中點 + 子女連線 */
      Object.values(doc.unions).forEach(u=>{
        const [aid,bid]=u.partners;
        const na = pickNode(layout, aid, overrides);
        const nb = pickNode(layout, bid, overrides);
        if(!na||!nb) return;

        const y = na.y + NODE_H/2;
        const xLeft  = Math.min(na.x+NODE_W, nb.x);
        const xRight = Math.max(na.x+NODE_W, nb.x);
        const midX   = (na.x + nb.x + NODE_W) / 2;

        const line = document.createElementNS("http://www.w3.org/2000/svg","line");
        line.setAttribute("x1",xLeft); line.setAttribute("y1",y);
        line.setAttribute("x2",xRight); line.setAttribute("y2",y);
        line.setAttribute("stroke","var(--line)"); line.setAttribute("stroke-width","2");
        if(u.status==="divorced") line.setAttribute("stroke-dasharray","6,4");
        root.appendChild(line);

        const dot = document.createElementNS("http://www.w3.org/2000/svg","rect");
        dot.setAttribute("x",midX-5); dot.setAttribute("y",y-5);
        dot.setAttribute("width",10); dot.setAttribute("height",10);
        dot.setAttribute("fill","var(--bg)"); dot.setAttribute("stroke","var(--border)");
        dot.setAttribute("stroke-width","2");
        dot.addEventListener("click",()=>{ selected={type:"union", id:u.id}; updateSelectionInfo(); });
        root.appendChild(dot);

        const kids = (unionKids[u.id]||[]);
        if(kids.length>0){
          const offBase = laneOffsetByUnion[u.id] ?? 0;
          kids.forEach(cid=>{
            const nc = pickNode(layout, cid, overrides);
            if(!nc) return;
            const childTop = nc.y;
            let busY = childTop + offBase;
            busY = Math.min(busY, childTop - CHILD_TOP_GAP);
            const cx = nc.x + NODE_W/2;
            const path = document.createElementNS("http://www.w3.org/2000/svg","path");
            path.setAttribute("d", `M ${midX} ${y} L ${midX} ${busY} L ${cx} ${busY} L ${cx} ${childTop}`);
            path.setAttribute("fill","none");
            path.setAttribute("stroke","var(--line)");
            path.setAttribute("stroke-width","2");
            root.appendChild(path);
          });
        }
      });

      /* 人物節點 */
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const nn = pickNode(layout, n.id, overrides);
        const person = doc.persons[n.id] || {};
        const g = document.createElementNS("http://www.w3.org/2000/svg","g");
        g.setAttribute("transform", `translate(${nn.x},${nn.y})`);
        const r=document.createElementNS("http://www.w3.org/2000/svg","rect");
        r.setAttribute("rx","16"); r.setAttribute("width",NODE_W); r.setAttribute("height",NODE_H);
        r.setAttribute("fill", person.deceased ? "var(--bg-dead)" : "var(--bg)");
        r.setAttribute("stroke", person.deceased ? "#475569" : "var(--border)");
        r.setAttribute("stroke-width","2");
        r.classList.add("node");
        r.addEventListener("click",()=>{ selected={type:"person", id:n.id}; updateSelectionInfo(); });
        const t=document.createElementNS("http://www.w3.org/2000/svg","text");
        t.setAttribute("x",NODE_W/2); t.setAttribute("y",NODE_H/2+5);
        t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--fg)"); t.setAttribute("font-size","14");
        t.textContent = (person.name || "?") + (person.deceased ? "（殁）" : "");
        g.appendChild(r); g.appendChild(t); root.appendChild(g);
      });

      host.innerHTML=""; host.appendChild(svg);

      /* Pan / Zoom */
      const applyVB = ()=>svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.addEventListener("mousedown",(e)=>{ isPanning=true; panStart={x:e.clientX,y:e.clientY}; vbStart={x:vb.x,y:vb.y,w:vb.w,h:vb.h}; });
      window.addEventListener("mousemove",(e)=>{
        if(!isPanning) return;
        const dx=(e.clientX-panStart.x)*(vb.w/svg.clientWidth);
        const dy=(e.clientY-panStart.y)*(vb.h/svg.clientHeight);
        vb.x = vbStart.x - dx; vb.y = vbStart.y - dy; applyVB();
      });
      window.addEventListener("mouseup",()=>{ isPanning=false; });
      svg.addEventListener("wheel",(e)=>{
        e.preventDefault();
        const s=(e.deltaY>0)?1.1:0.9;
        const rect=svg.getBoundingClientRect();
        const px=(e.clientX-rect.left)/rect.width, py=(e.clientY-rect.top)/rect.height;
        const nw=vb.w*s, nh=vb.h*s;
        vb.x = vb.x + vb.w*px - nw*px; vb.y = vb.y + vb.h*py - nh*py;
        vb.w = nw; vb.h = nh; applyVB();
      },{passive:false});
      document.getElementById("zoomIn").onclick = ()=>{ vb.w*=0.9; vb.h*=0.9; applyVB(); };
      document.getElementById("zoomOut").onclick= ()=>{ vb.w*=1.1; vb.h*=1.1; applyVB(); };
      document.getElementById("zoomFit").onclick= ()=>{ vb = fitVB(content.w, content.h); applyVB(); };
      document.getElementById("zoom100").onclick= ()=>{ vb = {x:0,y:0,w:content.w,h:content.h}; applyVB(); };

      document.getElementById("btnSVG").onclick = ()=>{
        const svgOut = svg.cloneNode(true);
        svgOut.setAttribute("viewBox", `0 0 ${content.w} ${content.h}`);
        svgOut.setAttribute("width", content.w);
        svgOut.setAttribute("height", content.h);
        const s = new XMLSerializer().serializeToString(svgOut);
        const blob = new Blob([s], {type:"image/svg+xml;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const a=document.createElement("a"); a.href=url; a.download="family-tree.svg"; a.click();
        URL.revokeObjectURL(url);
      };
    });

    updateSelectionInfo();
  }

  function updateSelectionInfo(){
    const el = document.getElementById("selInfo");
    const btnDead = document.getElementById("btnToggleDead");
    const btnDiv  = document.getElementById("btnToggleDivorce");
    const btnDel  = document.getElementById("btnDelete");
    btnDead.style.display="none"; btnDiv.style.display="none"; btnDel.style.display="none";

    if(!selected.type){ el.textContent="尚未選取節點。"; return; }

    if(selected.type==="person"){
      const p = doc.persons[selected.id] || {};
      el.textContent = "選取人物：" + (p.name || "?") + (p.deceased?"（殁）":"") + "（ID: "+selected.id+"）";
      btnDead.style.display="inline-block";
      btnDead.textContent = p.deceased ? "取消身故" : "標記身故";
      btnDead.onclick = ()=>{ p.deceased = !p.deceased; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick = ()=>{
        const pid = selected.id;
        delete doc.persons[pid];
        const keptUnions = {};
        Object.values(doc.unions).forEach(u=>{ if(u.partners.indexOf(pid)===-1) keptUnions[u.id]=u; });
        doc.unions = keptUnions;
        doc.children = doc.children.filter(cl => cl.childId!==pid && !!doc.unions[cl.unionId]);
        selected={type:null,id:null}; render();
      };
    }else{
      const u = doc.unions[selected.id] || {};
      const [a,b]=u.partners||[];
      el.textContent = "選取婚姻：" + (doc.persons[a]?.name||"?") + " ↔ " + (doc.persons[b]?.name||"?") +
                       "（狀態：" + (u.status==="divorced"?"離婚":"婚姻") + "）";
      btnDiv.style.display="inline-block";
      btnDiv.textContent = (u.status==="divorced")?"恢復婚姻":"設為離婚";
      btnDiv.onclick = ()=>{ u.status = (u.status==="divorced")?"married":"divorced"; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick = ()=>{
        const uid_ = selected.id;
        delete doc.unions[uid_];
        doc.children = doc.children.filter(cl => cl.unionId!==uid_);
        selected={type:null,id:null}; render();
      };
    }
  }

  /* 事件 */
  document.getElementById("btnDemo").addEventListener("click", ()=>demo());
  document.getElementById("btnClear").addEventListener("click", clearAll);

  document.getElementById("btnAddPerson").addEventListener("click", ()=>{
    const name = document.getElementById("namePerson").value.trim();
    const id = uid("P");
    doc.persons[id]={id, name: name || ("新成員 " + (Object.keys(doc.persons).length+1)), deceased:false};
    document.getElementById("namePerson").value=""; render();
  });

  document.getElementById("btnAddUnion").addEventListener("click", ()=>{
    const a = document.getElementById("selA").value;
    const b = document.getElementById("selB").value;
    if(!a||!b||a===b) return;
    const id = uid("U"); doc.unions[id]={id, partners:[a,b], status:"married"}; render();
  });

  document.getElementById("btnAddChild").addEventListener("click", ()=>{
    const mid = document.getElementById("selUnion").value; if(!mid) return;
    const name = document.getElementById("nameChild").value.trim();
    const id = uid("P"); doc.persons[id]={id, name: name || ("新子女 " + (doc.children.length+1)), deceased:false};
    // 以資料順序記錄：子女永遠在自己父母婚姻的中線下方
    doc.children.push({unionId: mid, childId: id});
    document.getElementById("nameChild").value=""; render();
  });

  // 初始空白畫面；你可以按「載入示例」
  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

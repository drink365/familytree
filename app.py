# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree (stable lanes)", page_icon="🌳", layout="wide")

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
    --bg:#0b3d4f;        /* 正常節點底色 */
    --bg-dead:#6b7280;   /* 身故節點底色（灰） */
    --fg:#ffffff;
    --border:#114b5f;
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

  /* 尺寸與間距 */
  const NODE_W = 140, NODE_H = 56, MARGIN = 48;
  const COUPLE_GAP_MIN = NODE_W + 36;   // 配偶最小水平距離
  const LAYER_GAP_MIN  = NODE_W + 60;   // 同層人物最小水平距離
  const LAYER_TOLERANCE = 20;           // 判定同層 y 容差
  const BUS_OFFSET_STEPS = [-12, -4, 4, 12, 20]; // 子女水平線的偏移候選（不同婚姻用不同車道）

  /* 視圖狀態（用 viewBox pan/zoom） */
  let vb = {x:0,y:0,w:1000,h:600};
  let content = {w:1000,h:600};
  let isPanning = false, panStart = {x:0,y:0}, vbStart = {x:0,y:0};

  /* 資料 */
  let doc = { persons:{}, unions:{}, children:[] };
  let selected = { type:null, id:null };

  const uid = p => p + "_" + Math.random().toString(36).slice(2,9);

  function demo(){
    const p={}, u={}, list=[
      "陳一郎","陳前妻","陳妻","陳大","陳大嫂","陳二","陳二嫂","陳三","陳三嫂",
      "王子","王子妻","王孫","二孩A","二孩B","二孩C","三孩A"
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
      {unionId:m1.id, childId:id("王子")},
      {unionId:m2.id, childId:id("陳大")},
      {unionId:m2.id, childId:id("陳二")},
      {unionId:m2.id, childId:id("陳三")},
      {unionId:m3.id, childId:id("王孫")},
      {unionId:m5.id, childId:id("二孩A")},
      {unionId:m5.id, childId:id("二孩B")},
      {unionId:m5.id, childId:id("二孩C")},
      {unionId:m6.id, childId:id("三孩A")},
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

  function syncSelectors(){
    const persons = Object.values(doc.persons);
    const unions  = Object.values(doc.unions);
    const selA = document.getElementById("selA");
    const selB = document.getElementById("selB");
    const selU = document.getElementById("selUnion");
    [selA,selB,selU].forEach(s=>s.innerHTML="");
    persons.forEach(p=>{
      const oa=document.createElement("option"); oa.value=p.id; oa.textContent=p.name+(p.deceased?"（殁）":""); selA.appendChild(oa);
      const ob=document.createElement("option"); ob.value=p.id; ob.textContent=p.name+(p.deceased?"（殁）":""); selB.appendChild(ob);
    });
    unions.forEach(u=>{
      const [a,b]=u.partners;
      const o=document.createElement("option");
      const tag = u.status==="divorced" ? "（離）" : "";
      o.value=u.id; o.textContent=(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+tag;
      selU.appendChild(o);
    });
  }

  /* ELK 佈局（層距：32 = 原本一半） */
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

  function computeFitViewBox(w,h, padding=60){
    return { x:-padding, y:-padding, w:w+padding*2, h:h+padding*2 };
  }

  /* 同層最小水平距離 */
  function enforceLayerMinGap(layout, overrides){
    const items = (layout.children||[])
      .filter(n=>!doc.unions[n.id])
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

  /* 為每個婚姻分配穩定的「子女水平線車道」 */
  function hashInt(s){
    let h=0; for(let i=0;i<s.length;i++){ h=(h*31 + s.charCodeAt(i))>>>0; } return h>>>0;
  }
  function busYOffset(unionId){
    const h = hashInt(unionId);
    return BUS_OFFSET_STEPS[h % BUS_OFFSET_STEPS.length]; // 例如 -12 / -4 / 4 / 12 / 20
  }

  function render(autoFit=false){
    syncSelectors();
    const host = document.getElementById("viewport");
    host.innerHTML = "<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    elk.layout(buildElkGraph()).then(layout=>{
      const overrides = {};

      /* 配偶對齊 & 配偶最小距離 */
      Object.values(doc.unions).forEach(u=>{
        const [a,b]=u.partners;
        const na = (layout.children||[]).find(n=>n.id===a);
        const nb = (layout.children||[]).find(n=>n.id===b);
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

      /* 同層人物最小距離 */
      enforceLayerMinGap(layout, overrides);

      /* 邊界（考慮 overrides） */
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
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

      const w = Math.ceil((maxX - minX) + MARGIN*2);
      const h = Math.ceil((maxY - minY) + MARGIN*2);
      content = {w, h};
      if(autoFit) vb = computeFitViewBox(w, h);

      /* SVG */
      const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
      svg.setAttribute("width", "100%");
      svg.setAttribute("height", "100%");
      svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.style.background = "#fff";

      const root = document.createElementNS("http://www.w3.org/2000/svg","g");
      root.setAttribute("transform", `translate(${MARGIN - minX},${MARGIN - minY})`);
      svg.appendChild(root);

      /* 婚姻水平線 + 中點 + 子女（不同婚姻→不同水平車道） */
      Object.values(doc.unions).forEach(u=>{
        const [aid,bid]=u.partners;
        const na = pickNode(layout, aid, overrides);
        const nb = pickNode(layout, bid, overrides);
        if(!na||!nb) return;

        const y = na.y + NODE_H/2;               // 已對齊
        const xLeft  = Math.min(na.x+NODE_W, nb.x);
        const xRight = Math.max(na.x+NODE_W, nb.x);
        const midX   = (na.x + nb.x + NODE_W) / 2;

        /* 婚姻水平線 */
        const line = document.createElementNS("http://www.w3.org/2000/svg","line");
        line.setAttribute("x1", xLeft);
        line.setAttribute("y1", y);
        line.setAttribute("x2", xRight);
        line.setAttribute("y2", y);
        line.setAttribute("stroke","var(--line)");
        line.setAttribute("stroke-width","2");
        if(u.status==="divorced") line.setAttribute("stroke-dasharray","6,4");
        root.appendChild(line);

        /* 婚姻點（可點選） */
        const dot = document.createElementNS("http://www.w3.org/2000/svg","rect");
        dot.setAttribute("x", midX-5);
        dot.setAttribute("y", y-5);
        dot.setAttribute("width", 10);
        dot.setAttribute("height", 10);
        dot.setAttribute("fill","var(--bg)");
        dot.setAttribute("stroke","var(--border)");
        dot.setAttribute("stroke-width","2");
        dot.addEventListener("click",()=>{ selected={type:"union", id:u.id}; updateSelectionInfo(); });
        root.appendChild(dot);

        /* 子女連線：每個婚姻使用固定的水平車道，避免不同婚姻的水平線重疊 */
        const kids = doc.children.filter(cl=>cl.unionId===u.id);
        if(kids.length>0){
          const offset = busYOffset(u.id);  // 依 unionId 穩定取一個 y 偏移
          kids.forEach(cl=>{
            const nc = pickNode(layout, cl.childId, overrides);
            if(!nc) return;
            const busY = nc.y + offset;     // 此婚姻的水平“車道”
            const cx   = nc.x + NODE_W/2;
            const path = document.createElementNS("http://www.w3.org/2000/svg","path");
            // 垂直到 busY → 在 busY 水平走 → 到 child x → 再垂直下到 child
            const d = `M ${midX} ${y} L ${midX} ${busY} L ${cx} ${busY} L ${cx} ${nc.y}`;
            path.setAttribute("d", d);
            path.setAttribute("fill","none");
            path.setAttribute("stroke","var(--line)");
            path.setAttribute("stroke-width","2");
            root.appendChild(path);
          });
        }
      });

      /* 人物節點（身故顯示） */
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
        t.setAttribute("x", NODE_W/2); t.setAttribute("y", NODE_H/2+5);
        t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--fg)"); t.setAttribute("font-size","14");
        t.textContent = (person.name || "?") + (person.deceased ? "（殁）" : "");
        g.appendChild(r); g.appendChild(t); root.appendChild(g);
      });

      host.innerHTML=""; host.appendChild(svg);

      /* Pan / Zoom */
      function applyViewBox(){ svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`); }
      svg.addEventListener("mousedown", (e)=>{
        isPanning = true; panStart = {x:e.clientX, y:e.clientY}; vbStart = {x:vb.x, y:vb.y, w:vb.w, h:vb.h};
      });
      window.addEventListener("mousemove", (e)=>{
        if(!isPanning) return;
        const dx = (e.clientX - panStart.x) * (vb.w / svg.clientWidth);
        const dy = (e.clientY - panStart.y) * (vb.h / svg.clientHeight);
        vb.x = vbStart.x - dx; vb.y = vbStart.y - dy; applyViewBox();
      });
      window.addEventListener("mouseup", ()=>{ isPanning=false; });
      svg.addEventListener("wheel", (e)=>{
        e.preventDefault();
        const scale = (e.deltaY>0)? 1.1 : 0.9;
        const rect = svg.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width;
        const py = (e.clientY - rect.top)  / rect.height;
        const newW = vb.w * scale, newH = vb.h * scale;
        vb.x = vb.x + vb.w*px - newW*px;
        vb.y = vb.y + vb.h*py - newH*py;
        vb.w = newW; vb.h = newH;
        applyViewBox();
      }, {passive:false});

      document.getElementById("zoomIn").onclick = ()=>{ vb.w*=0.9; vb.h*=0.9; applyViewBox(); };
      document.getElementById("zoomOut").onclick= ()=>{ vb.w*=1.1; vb.h*=1.1; applyViewBox(); };
      document.getElementById("zoomFit").onclick= ()=>{ vb = computeFitViewBox(content.w, content.h); applyViewBox(); };
      document.getElementById("zoom100").onclick= ()=>{ vb = {x:0,y:0,w:content.w,h:content.h}; applyViewBox(); };

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

  /* 右側操作（身故 / 離婚 / 刪除） */
  function updateSelectionInfo(){
    const el = document.getElementById("selInfo");
    const btnDead = document.getElementById("btnToggleDead");
    const btnDiv  = document.getElementById("btnToggleDivorce");
    const btnDel  = document.getElementById("btnDelete");

    btnDead.style.display = "none";
    btnDiv.style.display  = "none";
    btnDel.style.display  = "none";

    if(!selected.type){ el.textContent="尚未選取節點。"; return; }

    if(selected.type==="person"){
      const p = doc.persons[selected.id] || {};
      el.textContent = "選取人物：" + (p.name || "?") + (p.deceased?"（殁）":"") + "（ID: "+selected.id+"）";
      btnDead.style.display = "inline-block";
      btnDead.textContent = p.deceased ? "取消身故" : "標記身故";
      btnDead.onclick = ()=>{ p.deceased = !p.deceased; render(); };
      btnDel.style.display = "inline-block";
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
      const [a,b] = u.partners||[];
      el.textContent = "選取婚姻：" + (doc.persons[a]?.name||"?") + " ↔ " + (doc.persons[b]?.name||"?") +
                       "（狀態：" + (u.status==="divorced"?"離婚":"婚姻") + "）";
      btnDiv.style.display = "inline-block";
      btnDiv.textContent = (u.status==="divorced") ? "恢復婚姻" : "設為離婚";
      btnDiv.onclick = ()=>{ u.status = (u.status==="divorced") ? "married" : "divorced"; render(); };
      btnDel.style.display = "inline-block";
      btnDel.onclick = ()=>{
        const uid_ = selected.id;
        delete doc.unions[uid_];
        doc.children = doc.children.filter(cl => cl.unionId!==uid_);
        selected={type:null,id:null}; render();
      };
    }
  }

  /* 建立資料 */
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
    doc.children.push({unionId: mid, childId: id});
    document.getElementById("nameChild").value=""; render();
  });

  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

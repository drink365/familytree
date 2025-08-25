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
    --bg:#073c49;
    --fg:#ffffff;
    --border:#0f4859;
    --line:#0f3c4d;
    --dead:#6b7280;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:#f8fafc}
  .toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid #e5e7eb;padding:.75rem 1rem;background:#fff;position:sticky;top:0;z-index:10}
  .btn{background:#0a6377;color:#fff;border:none;border-radius:.7rem;padding:.5rem .8rem;cursor:pointer}
  .btn.sec{background:#334155}
  .btn.warn{background:#b91c1c}
  .btn.muted{background:#6b7280}
  .pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
  .row{display:flex;gap:.5rem;align-items:center;margin:.35rem 0;flex-wrap:wrap}
  input[type=text],select{border:1px solid #cbd5e1;border-radius:.7rem;padding:.45rem .6rem}
  .canvas{height:720px;overflow:hidden;border:1px solid #e5e7eb;border-radius:1rem;background:#fff}
  .hint{color:#64748b;font-size:.9rem}
  svg text{user-select:none}
  .node{filter:drop-shadow(0 1px 0.5px rgba(0,0,0,.15))}
  .legend{display:flex;gap:.75rem;align-items:center;color:#475569;margin-left:.75rem}
  .zoombar{display:flex;gap:.5rem;margin-left:auto}
  .tag{display:inline-flex;gap:.25rem;align-items:center}
  .box{width:16px;height:16px;border-radius:.5rem;background:var(--bg);border:2px solid var(--border)}
  .box.dead{background:var(--dead);border-color:#475569}
</style>
</head>
<body>
  <div class="toolbar">
    <button class="btn" id="btnDemo">載入示例</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="legend">
      <span class="tag"><span class="box"></span>人物</span>
      <span class="tag"><span class="box dead"></span>身故（名後加「（殁）」）</span>
      <span>離婚：婚線為虛線；有子女仍保留</span>
    </div>
    <div class="zoombar">
      <button class="btn" id="zoomOut">－</button>
      <button class="btn" id="zoomIn">＋</button>
      <button class="btn" id="zoomFit">置中</button>
      <button class="btn" id="zoom100">100%</button>
      <button class="btn" id="btnSVG">下載SVG</button>
    </div>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas">
        <div id="viewport" style="width:100%;height:100%"></div>
      </div>
      <div class="hint" style="margin-top:.5rem">滑鼠拖曳可平移；滾輪縮放；按鈕可置中或回到 100%。</div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">快速新增</h3>
      <div class="row">
        <input type="text" id="namePerson" placeholder="新人物姓名" />
        <button class="btn" id="btnAddPerson">新增人物</button>
      </div>
      <div class="row">
        <select id="selA"></select> × <select id="selB"></select>
        <button class="btn" id="btnAddUnion">建立婚姻</button>
      </div>
      <div class="row">
        <select id="selUnion"></select>
        <input type="text" id="nameChild" placeholder="新子女姓名" />
        <button class="btn" id="btnAddChild">加入子女</button>
      </div>

      <hr>
      <h3 style="margin:0 0 .5rem">選取與編輯</h3>
      <div id="selInfo" class="hint">尚未選取節點。</div>
      <div class="row">
        <button class="btn muted" id="btnToggleDead" style="display:none"></button>
        <button class="btn sec" id="btnToggleDivorce" style="display:none"></button>
        <button class="btn warn" id="btnDelete" style="display:none">刪除選取</button>
      </div>
    </div>
  </div>

<script>
(function(){
  const elk = new ELK();

  /* 幾何參數 */
  const NODE_W=140, NODE_H=56, MARGIN=48;
  const COUPLE_GAP_MIN = NODE_W + 18;   // 夫妻最小水平距（保證方塊不重疊）
  const LAYER_GAP_MIN  = NODE_W + 60;   // 同層不同家族群的最小距
  const LAYER_TOLERANCE= 20;
  const SIBLING_GAP_BASE = 36;          // 同一婚姻的兄弟姊妹基礎距
  const CLUSTER_GAP = 56;               // 相鄰婚姻子女群之間距
  const BUS_STEPS = [-14,-6,6,14,22];   // 同層不同婚姻的水平母線高度輪替（避免看成同一條）
  const CHILD_TOP_GAP = 18;

  /* 視口狀態 */
  let vb={x:0,y:0,w:1200,h:700}, content={w:1200,h:700};
  let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0,w:0,h:0};

  /* 資料模型 */
  let doc = { persons:{}, unions:{}, children:[] }; // children: {unionId, childId}
  let selected = {type:null,id:null};

  const uid=p=>p+"_"+Math.random().toString(36).slice(2,9);

  /* 工具 */
  function fitVB(w,h,p=60){ return {x:-p,y:-p,w:w+p*2,h:h+p*2}; }
  function pick(layout,id,over){ const n=(layout.children||[]).find(x=>x.id===id); return n? Object.assign({},n,over?.[id]||{}) : null; }

  /* 範例資料 */
  function demo(){
    const p={}, u={};
    const list = [
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
    [m1,m2,m3,m4,m5,m6].forEach(x=>u[x.id]=x);

    const children = [
      {unionId:m1.id, childId:id("王子")},
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

  function clearAll(){ doc={persons:{},unions:{},children:[]}; selected={type:null,id:null}; render(true); }

  function syncSelectors(){
    const persons=Object.values(doc.persons), unions=Object.values(doc.unions);
    const A=document.getElementById("selA"), B=document.getElementById("selB"), U=document.getElementById("selUnion");
    [A,B,U].forEach(s=>s.innerHTML="");
    persons.forEach(p=>{
      const o1=document.createElement("option"); o1.value=p.id; o1.textContent=p.name+(p.deceased?"（殁）":""); A.appendChild(o1);
      const o2=document.createElement("option"); o2.value=p.id; o2.textContent=p.name+(p.deceased?"（殁）":""); B.appendChild(o2);
    });
    unions.forEach(m=>{
      const [a,b]=m.partners, tag=m.status==="divorced"?"（離）":"";
      const o=document.createElement("option"); o.value=m.id; o.textContent=(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+tag;
      U.appendChild(o);
    });
  }

  /* 產生 ELK 初始圖（讓 ELK 先決定大致層次與y） */
  function buildElk(){
    const nodes=[], edges=[];
    Object.values(doc.persons).forEach(p=>nodes.push({id:p.id,width:NODE_W,height:NODE_H,labels:[{text:p.name}]}));
    Object.values(doc.unions).forEach(u=>{
      nodes.push({id:u.id,width:10,height:10});
      const [a,b]=u.partners;
      edges.push({id:uid("E"),sources:[a],targets:[u.id]});
      edges.push({id:uid("E"),sources:[b],targets:[u.id]});
      edges.push({id:uid("E"),sources:[a],targets:[b],layoutOptions:{"elk.priority":"1000","elk.edge.type":"INFLUENCE"}});
    });
    doc.children.forEach(cl=>edges.push({id:uid("E"),sources:[cl.unionId],targets:[cl.childId]}));
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

  /* 同層非孩子（即上一代）最小距 */
  function pushNonChildMinGap(layout, overrides, childIdSet){
    const items=(layout.children||[])
      .filter(n=>!doc.unions[n.id] && !childIdSet.has(n.id))
      .map(n=>{ const nn=pick(layout,n.id,overrides); return {id:n.id,x:nn.x,y:nn.y}; });

    const layerMap={};
    items.forEach(it=>{
      const k=Math.round(it.y/LAYER_TOLERANCE);
      (layerMap[k]??=[]).push(it);
    });

    Object.values(layerMap).forEach(arr=>{
      arr.sort((a,b)=>a.x-b.x);
      if(arr.length<2) return;
      let right = arr[0].x + NODE_W;
      for(let i=1;i<arr.length;i++){
        const needLeft = right + (LAYER_GAP_MIN - NODE_W);
        if(arr[i].x < needLeft){
          const shift = needLeft - arr[i].x;
          const cur = overrides[arr[i].id]?.x ?? arr[i].x;
          overrides[arr[i].id] = Object.assign({},overrides[arr[i].id]||{}, {x:cur+shift});
          arr[i].x = cur + shift;
        }
        right = arr[i].x + NODE_W;
      }
    });
  }

  function render(autoFit=false){
    syncSelectors();
    const host=document.getElementById("viewport");
    host.innerHTML="<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    elk.layout(buildElk()).then(layout=>{
      const overrides={};

      /* 夫妻對齊 + 最小夫妻距 */
      Object.values(doc.unions).forEach(u=>{
        const [a,b]=u.partners; const na=pick(layout,a,overrides), nb=pick(layout,b,overrides); if(!na||!nb) return;
        const yAlign=Math.min(na.y,nb.y);
        overrides[a]=Object.assign({},overrides[a]||{}, {y:yAlign});
        overrides[b]=Object.assign({},overrides[b]||{}, {y:yAlign});
        const left=na.x<=nb.x?a:b, right=na.x<=nb.x?b:a;
        const nL=pick(layout,left,overrides), nR=pick(layout,right,overrides);
        const gap = nR.x - (nL.x+NODE_W);
        const need = COUPLE_GAP_MIN - NODE_W - gap;
        if(need>0){
          overrides[right]=Object.assign({},overrides[right]||{}, {x:nR.x+need,y:yAlign});
        }
      });

      /* 依婚姻收集子女（使用資料順序） */
      const unionKids={}, childIdSet=new Set();
      Object.values(doc.unions).forEach(u=>{
        const kids = doc.children.filter(cl=>cl.unionId===u.id).map(cl=>cl.childId);
        if(kids.length) unionKids[u.id]=kids;
        kids.forEach(id=>childIdSet.add(id));
      });

      /* 上一代之間的最小距 */
      pushNonChildMinGap(layout, overrides, childIdSet);

      /* —— 以父母婚點為中心置中，按照資料順序排手足 —— */
      const clustersByLayer={};             // 同層的各個子女群，用於群組互推
      const unionCenterX={};                // ★儲存每段婚姻更新後的 midX，供畫線使用

      Object.entries(unionKids).forEach(([uid,kids])=>{
        const u=doc.unions[uid];
        const na=pick(layout,u.partners[0],overrides), nb=pick(layout,u.partners[1],overrides);
        if(!na||!nb) return;

        // 先用父母調整後位置算中線
        let midX = (na.x + nb.x + NODE_W)/2;

        // 以資料順序建立 blocks
        const blocks = kids.map(cid=>{
          const k=pick(layout,cid,overrides); if(!k) return null;
          // 若此孩子有配偶，將寬度算上配偶
          const mateUnion = Object.values(doc.unions).find(xx => (xx.partners||[]).includes(cid) && xx.partners.length===2);
          let hasMate=false, mateId=null;
          if(mateUnion){
            const [pa,pb]=mateUnion.partners; mateId=(pa===cid?pb:pa);
            if(mateId && doc.persons[mateId]) hasMate=true;
          }
          const width = hasMate ? (NODE_W + COUPLE_GAP_MIN + NODE_W) : NODE_W;
          return {kidId:cid, mateId, hasMate, width, y:k.y};
        }).filter(Boolean);

        const localGap = SIBLING_GAP_BASE + Math.max(0, blocks.length-3)*8;
        const total = blocks.reduce((s,b)=>s+b.width,0) + (blocks.length-1)*localGap;
        let startX = midX - total/2;

        blocks.forEach(b=>{
          overrides[b.kidId]=Object.assign({},overrides[b.kidId]||{}, {x:startX});
          if(b.hasMate){
            const mateX = startX + COUPLE_GAP_MIN + NODE_W;
            const oy  = overrides[b.kidId]?.y ?? b.y;
            overrides[b.mateId]=Object.assign({},overrides[b.mateId]||{}, {x:mateX, y:oy});
          }
          startX += b.width + localGap;
        });

        // 建立此群的範圍，並先存入 unionCenterX
        const firstKid = pick(layout, kids[0], overrides);
        const lastKid  = pick(layout, kids[kids.length-1], overrides);
        const x0 = pick(layout, kids[0], overrides).x;
        const x1 = (lastKid.x + NODE_W) + (blocks[blocks.length-1].hasMate ? (COUPLE_GAP_MIN + NODE_W) : 0);
        unionCenterX[uid] = midX;

        const layerKey = Math.round(firstKid.y / LAYER_TOLERANCE);
        (clustersByLayer[layerKey]??=[]).push({ unionId:uid, rect:{x0,x1}, anchorX:midX, kids:[...kids] });
      });

      /* 群組互推：保持左右相對順序，若重疊就把右方整群平移 —— 同時平移該婚姻 midX */
      Object.entries(clustersByLayer).forEach(([layer,arr])=>{
        arr.sort((a,b)=>a.anchorX-b.anchorX);
        let right = arr[0].rect.x1;
        for(let i=1;i<arr.length;i++){
          const wantLeft = right + CLUSTER_GAP;
          if(arr[i].rect.x0 < wantLeft){
            const shift = wantLeft - arr[i].rect.x0;
            // 平移此群所有孩子與其配偶
            arr[i].kids.forEach(cid=>{
              const curX = overrides[cid]?.x ?? pick(layout,cid,overrides).x;
              overrides[cid]=Object.assign({},overrides[cid]||{}, {x:curX+shift});

              const mateUnion = Object.values(doc.unions).find(xx => (xx.partners||[]).includes(cid) && xx.partners.length===2);
              if(mateUnion){
                const [pa,pb]=mateUnion.partners; const mateId=(pa===cid?pb:pa);
                if(mateId && doc.persons[mateId]){
                  const mx = overrides[mateId]?.x ?? pick(layout,mateId,overrides).x;
                  const my = overrides[mateId]?.y ?? pick(layout,mateId,overrides).y;
                  overrides[mateId]=Object.assign({},overrides[mateId]||{}, {x:mx+shift,y:my});
                }
              }
            });
            // 更新群的邊界與婚姻中心
            arr[i].rect.x0 += shift; arr[i].rect.x1 += shift; arr[i].anchorX += shift;
            unionCenterX[arr[i].unionId] = (unionCenterX[arr[i].unionId] ?? arr[i].anchorX) + shift;
          }
          right = arr[i].rect.x1;
        }
      });

      /* 計算畫布大小 */
      let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const nn=pick(layout,n.id,overrides);
        minX=Math.min(minX,nn.x); minY=Math.min(minY,nn.y);
        maxX=Math.max(maxX,nn.x+NODE_W); maxY=Math.max(maxY,nn.y+NODE_H);
      });
      if(!isFinite(minX)){ minX=0; minY=0; maxX=(layout.width||1000); maxY=(layout.height||600); }
      const W=Math.ceil(maxX-minX+MARGIN*2), H=Math.ceil(maxY-minY+MARGIN*2);
      content={w:W,h:H}; if(autoFit) vb = fitVB(W,H);

      /* 為同層婚姻分配 bus 高度 */
      const laneOffsetByUnion={};
      Object.entries(clustersByLayer).forEach(([k,list])=>{
        list.sort((a,b)=>a.anchorX-b.anchorX);
        list.forEach((it,i)=>{ laneOffsetByUnion[it.unionId]=BUS_STEPS[i%BUS_STEPS.length]; });
      });

      /* SVG 繪製 */
      const svgNS="http://www.w3.org/2000/svg";
      const svg=document.createElementNS(svgNS,"svg");
      svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
      svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.style.background="#fff";

      const root=document.createElementNS(svgNS,"g");
      root.setAttribute("transform",`translate(${MARGIN-minX},${MARGIN-minY})`);
      svg.appendChild(root);

      /* 婚姻線 + 中點 + 子女連線（★使用 unionCenterX） */
      Object.values(doc.unions).forEach(u=>{
        const [aid,bid]=u.partners; const na=pick(layout,aid,overrides), nb=pick(layout,bid,overrides);
        if(!na||!nb) return;
        const y = na.y + NODE_H/2;
        const leftX  = Math.min(na.x+NODE_W, nb.x);
        const rightX = Math.max(na.x+NODE_W, nb.x);
        const midX = (unionCenterX[u.id] != null) ? unionCenterX[u.id] : (na.x+nb.x+NODE_W)/2;

        const line=document.createElementNS(svgNS,"line");
        line.setAttribute("x1",leftX); line.setAttribute("y1",y);
        line.setAttribute("x2",rightX); line.setAttribute("y2",y);
        line.setAttribute("stroke","var(--line)"); line.setAttribute("stroke-width","2");
        if(u.status==="divorced") line.setAttribute("stroke-dasharray","6,4");
        root.appendChild(line);

        const dot=document.createElementNS(svgNS,"rect");
        dot.setAttribute("x",midX-5); dot.setAttribute("y",y-5);
        dot.setAttribute("width",10); dot.setAttribute("height",10);
        dot.setAttribute("fill","var(--bg)"); dot.setAttribute("stroke","var(--border)"); dot.setAttribute("stroke-width","2");
        dot.addEventListener("click",()=>{ selected={type:"union",id:u.id}; updateSelectionInfo(); });
        root.appendChild(dot);

        const kids = unionKids[u.id]||[];
        if(kids.length){
          const offBase = laneOffsetByUnion[u.id]??0;
          kids.forEach(cid=>{
            const nc=pick(layout,cid,overrides); if(!nc) return;
            const childTop = nc.y;
            let busY = Math.min(childTop-CHILD_TOP_GAP, childTop+(offBase)); // 不要超過子女頂端
            const cx = nc.x + NODE_W/2;

            const p=document.createElementNS(svgNS,"path");
            p.setAttribute("d",`M ${midX} ${y} L ${midX} ${busY} L ${cx} ${busY} L ${cx} ${childTop}`);
            p.setAttribute("fill","none"); p.setAttribute("stroke","var(--line)"); p.setAttribute("stroke-width","2");
            root.appendChild(p);
          });
        }
      });

      /* 人物節點 */
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const nn=pick(layout,n.id,overrides);
        const person=doc.persons[n.id]||{};
        const g=document.createElementNS(svgNS,"g");
        g.setAttribute("transform",`translate(${nn.x},${nn.y})`);
        const r=document.createElementNS(svgNS,"rect");
        r.setAttribute("rx","16"); r.setAttribute("width",NODE_W); r.setAttribute("height",NODE_H);
        r.setAttribute("fill", person.deceased? "var(--dead)" : "var(--bg)");
        r.setAttribute("stroke", person.deceased? "#475569" : "var(--border)");
        r.setAttribute("stroke-width","2"); r.classList.add("node");
        r.addEventListener("click",()=>{ selected={type:"person",id:n.id}; updateSelectionInfo(); });

        const t=document.createElementNS(svgNS,"text");
        t.setAttribute("x",NODE_W/2); t.setAttribute("y",NODE_H/2+5);
        t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--fg)"); t.setAttribute("font-size","14");
        t.textContent=(person.name||"?") + (person.deceased?"（殁）":"");

        g.appendChild(r); g.appendChild(t); root.appendChild(g);
      });

      host.innerHTML=""; host.appendChild(svg);

      /* 互動：Pan/Zoom/下載 */
      function applyVB(){ svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`); }
      svg.addEventListener("mousedown",e=>{ isPanning=true; panStart={x:e.clientX,y:e.clientY}; vbStart={...vb}; });
      window.addEventListener("mousemove",e=>{
        if(!isPanning) return;
        const dx=(e.clientX-panStart.x)*(vb.w/svg.clientWidth);
        const dy=(e.clientY-panStart.y)*(vb.h/svg.clientHeight);
        vb.x=vbStart.x-dx; vb.y=vbStart.y-dy; applyVB();
      });
      window.addEventListener("mouseup",()=>{ isPanning=false; });
      svg.addEventListener("wheel",(e)=>{
        e.preventDefault();
        const s=(e.deltaY>0)?1.1:0.9;
        const rect=svg.getBoundingClientRect();
        const px=(e.clientX-rect.left)/rect.width, py=(e.clientY-rect.top)/rect.height;
        const nw=vb.w*s, nh=vb.h*s;
        vb.x = vb.x + vb.w*px - nw*px;
        vb.y = vb.y + vb.h*py - nh*py;
        vb.w=nw; vb.h=nh; applyVB();
      },{passive:false});

      document.getElementById("zoomIn").onclick = ()=>{ vb.w*=0.9; vb.h*=0.9; applyVB(); };
      document.getElementById("zoomOut").onclick= ()=>{ vb.w*=1.1; vb.h*=1.1; applyVB(); };
      document.getElementById("zoomFit").onclick= ()=>{ vb=fitVB(content.w,content.h); applyVB(); };
      document.getElementById("zoom100").onclick= ()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };

      document.getElementById("btnSVG").onclick=()=>{
        const out=svg.cloneNode(true);
        out.setAttribute("viewBox",`0 0 ${content.w} ${content.h}`);
        out.setAttribute("width",content.w); out.setAttribute("height",content.h);
        const s=new XMLSerializer().serializeToString(out);
        const blob=new Blob([s],{type:"image/svg+xml;charset=utf-8"});
        const url=URL.createObjectURL(blob);
        const a=document.createElement("a"); a.href=url; a.download="family-tree.svg"; a.click();
        URL.revokeObjectURL(url);
      };
    });

    updateSelectionInfo();
  }

  function updateSelectionInfo(){
    const info=document.getElementById("selInfo");
    const btnDead=document.getElementById("btnToggleDead");
    const btnDiv=document.getElementById("btnToggleDivorce");
    const btnDel=document.getElementById("btnDelete");
    btnDead.style.display="none"; btnDiv.style.display="none"; btnDel.style.display="none";

    if(!selected.type){ info.textContent="尚未選取節點。"; return; }

    if(selected.type==="person"){
      const p=doc.persons[selected.id]||{};
      info.textContent="選取人物："+(p.name||"?")+(p.deceased?"（殁）":"");
      btnDead.style.display="inline-block";
      btnDead.textContent=p.deceased?"取消身故":"標記身故";
      btnDead.onclick=()=>{ p.deceased=!p.deceased; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const pid=selected.id;
        delete doc.persons[pid];
        // 移除包含此人的婚姻與其子女關係
        const keep={};
        Object.values(doc.unions).forEach(u=>{ if(!u.partners.includes(pid)) keep[u.id]=u; });
        doc.unions=keep;
        doc.children=doc.children.filter(cl=>cl.childId!==pid && !!doc.unions[cl.unionId]);
        selected={type:null,id:null}; render();
      };
    }else{
      const u=doc.unions[selected.id]||{}, [a,b]=u.partners||[];
      info.textContent="選取婚姻："+(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+ "（"+(u.status==="divorced"?"離婚":"婚姻")+"）";
      btnDiv.style.display="inline-block";
      btnDiv.textContent = u.status==="divorced" ? "恢復婚姻" : "設為離婚";
      btnDiv.onclick=()=>{ u.status = (u.status==="divorced") ? "married" : "divorced"; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const uid_=selected.id; delete doc.unions[uid_];
        doc.children = doc.children.filter(cl=>cl.unionId!==uid_);
        selected={type:null,id:null}; render();
      };
    }
  }

  /* 事件 */
  document.getElementById("btnDemo").onclick=demo;
  document.getElementById("btnClear").onclick=clearAll;

  document.getElementById("btnAddPerson").onclick=()=>{
    const name=document.getElementById("namePerson").value.trim();
    const id=uid("P");
    doc.persons[id]={id,name: name || ("新成員 "+(Object.keys(doc.persons).length+1)), deceased:false};
    document.getElementById("namePerson").value="";
    render();
  };

  document.getElementById("btnAddUnion").onclick=()=>{
    const a=document.getElementById("selA").value, b=document.getElementById("selB").value;
    if(!a||!b||a===b) return;
    const id=uid("U"); doc.unions[id]={id,partners:[a,b],status:"married"}; render();
  };

  document.getElementById("btnAddChild").onclick=()=>{
    const mid=document.getElementById("selUnion").value; if(!mid) return;
    const name=document.getElementById("nameChild").value.trim();
    const id=uid("P");
    doc.persons[id]={id,name: name || ("新子女 "+(doc.children.length+1)), deceased:false};
    doc.children.push({unionId:mid, childId:id});  // 資料順序決定手足順序
    document.getElementById("nameChild").value="";
    render();
  };

  // 初始載入空白畫布
  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree", page_icon="🌳", layout="wide")

HTML = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Family Tree</title>
<script src="https://unpkg.com/elkjs@0.8.2/lib/elk.bundled.js"></script>
<style>
:root{
  --bg:#083947;
  --fg:#ffffff;
  --border:#0f4b5f;
  --line:#0e3b4b;
  --dead:#6b7280;
}
*{box-sizing:border-box}
body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:#f7fafc}
.toolbar{display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;border-bottom:1px solid #e5e7eb;background:#fff;position:sticky;top:0;z-index:10}
.btn{background:#0b5c75;color:#fff;border:none;border-radius:.75rem;padding:.45rem .75rem;cursor:pointer}
.btn.sec{background:#334155}
.btn.ok{background:#0f766e}
.btn.warn{background:#b91c1c}
.btn.muted{background:#6b7280}
.pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
.canvas{height:720px;border:1px solid #e5e7eb;border-radius:1rem;background:#fff;overflow:hidden}
.hint{color:#64748b;font-size:.9rem;margin-top:.5rem}
.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin:.25rem 0}
select,input[type=text]{border:1px solid #cbd5e1;border-radius:.75rem;padding:.45rem .6rem}
svg text{user-select:none}
.node{filter:drop-shadow(0 1px 0.6px rgba(0,0,0,.15))}
.zoombar{display:flex;gap:.5rem;margin-left:auto}
.legend{display:flex;gap:1rem;align-items:center;margin-left:.75rem;color:#475569}
.box{width:16px;height:16px;border-radius:.4rem;background:var(--bg);border:2px solid var(--border)}
.box.dead{background:var(--dead);border-color:#475569}
.stack{display:flex;gap:.5rem;flex-wrap:wrap}
</style>
</head>
<body>
  <div class="toolbar">
    <button class="btn ok" id="btnDemo">載入示例</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="legend">
      <span class="legend"><span class="box"></span>人物</span>
      <span class="legend"><span class="box dead"></span>身故（名稱加「（殁）」）</span>
      <span>離婚：婚線為虛線</span>
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
      <div class="canvas"><div id="viewport" style="width:100%;height:100%"></div></div>
      <div class="hint">滑鼠拖曳可平移；滾輪縮放；按鈕可置中或回到 100%。</div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">快速新增</h3>
      <div class="row">
        <input id="namePerson" type="text" placeholder="新人物姓名"/>
        <button class="btn ok" id="btnAddPerson">新增人物</button>
      </div>

      <div class="row">
        <select id="selA"></select>×<select id="selB"></select>
        <button class="btn ok" id="btnAddUnion">建立婚姻</button>
      </div>

      <div class="row">
        <select id="selUnion"></select>
        <input id="nameChild" type="text" placeholder="新子女姓名"/>
        <button class="btn ok" id="btnAddChild">加入子女</button>
      </div>

      <hr style="margin:1rem 0">
      <h3 style="margin:0 0 .5rem">選取與編輯</h3>
      <div id="selInfo" class="hint">尚未選取節點。</div>
      <div id="actionBtns" class="stack" style="margin-top:.25rem">
        <button class="btn muted" id="btnToggleDead" style="display:none"></button>
        <button class="btn sec" id="btnToggleDivorce" style="display:none"></button>
        <button class="btn warn" id="btnDelete" style="display:none">刪除選取</button>
      </div>
    </div>
  </div>

<script>
(function(){
  const elk = new ELK();

  /* 尺寸／間距設定 */
  const NODE_W = 140, NODE_H = 56;
  const MARGIN = 48;
  const LAYER_GAP_MIN = NODE_W + 60;         // 同層非子女最小間距
  const COUPLE_GAP_MIN = NODE_W + 18;        // 夫妻最小水平距
  const SIBLING_GAP_BASE = 36;               // 同一段婚姻孩子之間的基礎間距
  const CLUSTER_GAP = 56;                    // 不同婚姻的孩子群組間距
  const LAYER_TOLER = 20;                    // 取整層的容忍值
  const BUS_STEPS = [-12,-6,6,12,18];        // 同層不同婚姻的“bus”高度輪替
  const CHILD_TOP_GAP = 18;

  /* 視圖狀態 */
  let vb={x:0,y:0,w:1200,h:700}, content={w:1200,h:700};
  let isPan=false, pan0={x:0,y:0}, vb0={x:0,y:0,w:0,h:0};

  /* 資料 */
  let doc={persons:{}, unions:{}, children:[]};
  let selected={type:null,id:null};

  const uid = (p="id") => p+"_"+Math.random().toString(36).slice(2,9);

  function demo(){
    const make = (...names)=>names.map(n=>({id:uid("P"),name:n,deceased:false}));
    const people = make("陳一郎","陳前妻","陳妻","王子","王子妻","王孫","陳大","陳大嫂","陳二","陳二嫂","陳三","陳三嫂","二孩A","二孩B","二孩C","三孩A","三孩B");
    const id = n => people.find(p=>p.name===n).id;
    const persons={}; people.forEach(p=>persons[p.id]=p);

    const u1={id:uid("U"),partners:[id("陳一郎"),id("陳前妻")],status:"divorced"};
    const u2={id:uid("U"),partners:[id("陳一郎"),id("陳妻")],status:"married"};
    const u3={id:uid("U"),partners:[id("王子"),id("王子妻")],status:"married"};
    const u4={id:uid("U"),partners:[id("陳大"),id("陳大嫂")],status:"married"};
    const u5={id:uid("U"),partners:[id("陳二"),id("陳二嫂")],status:"married"};
    const u6={id:uid("U"),partners:[id("陳三"),id("陳三嫂")],status:"married"};
    const unions={}; [u1,u2,u3,u4,u5,u6].forEach(u=>unions[u.id]=u);

    const children=[
      {unionId:u1.id, childId:id("王子")},
      {unionId:u2.id, childId:id("陳大")},
      {unionId:u2.id, childId:id("陳二")},
      {unionId:u2.id, childId:id("陳三")},
      {unionId:u3.id, childId:id("王孫")},
      {unionId:u5.id, childId:id("二孩A")},
      {unionId:u5.id, childId:id("二孩B")},
      {unionId:u5.id, childId:id("二孩C")},
      {unionId:u6.id, childId:id("三孩A")},
      {unionId:u6.id, childId:id("三孩B")},
    ];

    doc={persons,unions,children};
    selected={type:null,id:null};
    render(true);
  }

  function clearAll(){
    doc={persons:{},unions:{},children:[]};
    selected={type:null,id:null};
    render(true);
  }

  function syncSelectors(){
    const persons=Object.values(doc.persons);
    const unions=Object.values(doc.unions);
    const selA=document.getElementById("selA");
    const selB=document.getElementById("selB");
    const selU=document.getElementById("selUnion");
    [selA,selB,selU].forEach(s=>s.innerHTML="");
    persons.forEach(p=>{
      const a=document.createElement("option");
      a.value=p.id; a.textContent=p.name+(p.deceased?"（殁）":"");
      const b=a.cloneNode(true);
      selA.appendChild(a); selB.appendChild(b);
    });
    unions.forEach(u=>{
      const [a,b]=u.partners;
      const o=document.createElement("option");
      o.value=u.id;
      o.textContent=(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+(u.status==="divorced"?"（離）":"");
      selU.appendChild(o);
    });
  }

  /* 建立 ELK 圖 */
  function buildElkGraph(){
    const nodes=[],edges=[];
    Object.values(doc.persons).forEach(p=>{
      nodes.push({id:p.id,width:NODE_W,height:NODE_H,labels:[{text:p.name}]});
    });
    Object.values(doc.unions).forEach(u=>{
      nodes.push({id:u.id,width:10,height:10,labels:[{text:""}]});
      const [a,b]=u.partners;
      edges.push({id:uid("E"),sources:[a],targets:[u.id]});
      edges.push({id:uid("E"),sources:[b],targets:[u.id]});
      // 夫妻之間給高優先權讓其同層
      edges.push({id:uid("E"),sources:[a],targets:[b],layoutOptions:{"elk.priority":"1000","elk.edge.type":"INFLUENCE"}});
    });
    doc.children.forEach(cl=>{
      edges.push({id:uid("E"),sources:[cl.unionId],targets:[cl.childId]});
    });
    return {
      id:"root",
      layoutOptions:{
        "elk.algorithm":"layered",
        "elk.direction":"DOWN",
        "elk.edgeRouting":"ORTHOGONAL",
        "elk.spacing.nodeNode":"46",
        "elk.layered.spacing.nodeNodeBetweenLayers":"32",
        "elk.layered.nodePlacement.bk.fixedAlignment":"BALANCED"
      },
      children:nodes,edges
    };
  }

  function render(autoFit=false){
    syncSelectors();
    const host=document.getElementById("viewport");
    host.innerHTML="<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    elk.layout(buildElkGraph()).then(layout=>{
      const overrides={};

      /* 夫妻同層 + 最小夫妻距 */
      Object.values(doc.unions).forEach(u=>{
        const [a,b]=u.partners;
        const na=(layout.children||[]).find(n=>n.id===a);
        const nb=(layout.children||[]).find(n=>n.id===b);
        if(!na||!nb) return;
        const y=Math.min(na.y,nb.y);
        overrides[a]=Object.assign({},overrides[a]||{}, {y});
        overrides[b]=Object.assign({},overrides[b]||{}, {y});
        const left = na.x<=nb.x? a:b, right= na.x<=nb.x? b:a;
        const nL = na.x<=nb.x? na:nb, nR= na.x<=nb.x? nb:na;
        const lRight = (overrides[left]?.x ?? nL.x)+NODE_W;
        const rLeft  = (overrides[right]?.x ?? nR.x);
        const gap = rLeft - lRight;
        const need = COUPLE_GAP_MIN - NODE_W - gap;
        if(need>0){
          overrides[right]=Object.assign({},overrides[right]||{}, {x:(overrides[right]?.x ?? nR.x)+need, y});
        }
      });

      const pick = (id)=> (layout.children||[]).find(n=>n.id===id);
      const getXY = (id)=> Object.assign({}, pick(id)||{}, overrides[id]||{});

      /* 蒐集各婚姻之子女（按資料順序） */
      const unionKids={};
      const childrenSet=new Set();
      Object.values(doc.unions).forEach(u=>{
        const kids=doc.children.filter(c=>c.unionId===u.id).map(c=>c.childId);
        if(kids.length){ unionKids[u.id]=kids; kids.forEach(k=>childrenSet.add(k)); }
      });

      /* 同層（且不是子女）保持最小間距：避免人貼太近 */
      const nonChildSameLayer={};
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;            // 跳過 union node
        if(childrenSet.has(n.id)) return;       // 跳過孩子
        const k = Math.round((overrides[n.id]?.y ?? n.y)/LAYER_TOLER);
        if(!nonChildSameLayer[k]) nonChildSameLayer[k]=[];
        nonChildSameLayer[k].push(n.id);
      });
      Object.values(nonChildSameLayer).forEach(ids=>{
        ids.sort((A,B)=> (overrides[A]?.x ?? pick(A).x) - (overrides[B]?.x ?? pick(B).x));
        let cursorR = (overrides[ids[0]]?.x ?? pick(ids[0]).x)+NODE_W;
        for(let i=1;i<ids.length;i++){
          const x=overrides[ids[i]]?.x ?? pick(ids[i]).x;
          if(x < cursorR + (LAYER_GAP_MIN - NODE_W)){
            const shift = cursorR + (LAYER_GAP_MIN - NODE_W) - x;
            overrides[ids[i]] = Object.assign({},overrides[ids[i]]||{}, {x: x+shift});
          }
          cursorR = (overrides[ids[i]]?.x ?? pick(ids[i]).x)+NODE_W;
        }
      });

      /* ===「每段婚姻」建立自己的 children block，先對齊父母中線，再檢查與同層其它婚姻是否重疊，重疊就右推 === */
      const blocksByLayer = {};            // layerKey -> [{uid,x0,x1,mid,kids}]
      const blocksInfo = {};               // uid -> {x0,x1,mid,kids}
      const kidWidthOnly = NODE_W;         // 這一版：孩子本身寬度（孩子是否已婚另行處理亦可）

      Object.entries(unionKids).forEach(([uid,kids])=>{
        const u=doc.unions[uid]; const [pa,pb]=u.partners;
        const NA=getXY(pa), NB=getXY(pb);
        const mid = (NA.x + NB.x + NODE_W)/2;            // 父母的中線
        // 估算當前孩子群的總寬
        const localGap = SIBLING_GAP_BASE + Math.max(0, kids.length-3)*8;
        const totalW = kids.length * kidWidthOnly + (kids.length-1)*localGap;
        let x0 = mid - totalW/2, x1 = mid + totalW/2;

        // 取得孩子層（用第一個孩子）
        const firstKid = getXY(kids[0]);
        const layerKey = Math.round(firstKid.y/LAYER_TOLER);

        if(!blocksByLayer[layerKey]) blocksByLayer[layerKey]=[];
        const block={uid,x0,x1,mid,kids,localGap,totalW,layerKey};
        blocksByLayer[layerKey].push(block);
        blocksInfo[uid]=block;
      });

      // 同層婚姻的 children block 右推以避免互相重疊
      Object.values(blocksByLayer).forEach(list=>{
        list.sort((a,b)=>a.x0-b.x0);
        for(let i=1;i<list.length;i++){
          const prev=list[i-1], cur=list[i];
          const wantLeft = prev.x1 + CLUSTER_GAP;
          if(cur.x0 < wantLeft){
            const shift = wantLeft - cur.x0;
            cur.x0 += shift; cur.x1 += shift; cur.mid += shift;
            blocksInfo[cur.uid]=cur;
          }
        }
      });

      // 依 block 的 x0 依序擺放孩子（確保孩子從自己父母正下方開始，不會跑到別人婚姻）
      Object.values(blocksInfo).forEach(block=>{
        let cursor = block.x0;
        block.kids.forEach(cid=>{
          const nc=getXY(cid);
          overrides[cid]=Object.assign({},overrides[cid]||{}, {x: cursor});
          cursor += kidWidthOnly + block.localGap;
        });
      });

      // --- 邊界計算（用人節點，不含 union） ---
      let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const nn=getXY(n.id);
        minX=Math.min(minX, nn.x);
        minY=Math.min(minY, nn.y);
        maxX=Math.max(maxX, nn.x+NODE_W);
        maxY=Math.max(maxY, nn.y+NODE_H);
      });
      if(!isFinite(minX)){minX=0;minY=0;maxX=layout.width||1000;maxY=layout.height||600;}
      content={w:Math.ceil((maxX-minX)+MARGIN*2),h:Math.ceil((maxY-minY)+MARGIN*2)};
      if(autoFit) vb={x:-MARGIN,y:-MARGIN,w:content.w,h:content.h};

      /* 為每層婚姻分配 bus 高度 */
      const busByUnion={};  // uid -> offset
      Object.values(blocksByLayer).forEach(list=>{
        list.sort((a,b)=>a.x0-b.x0);
        list.forEach((b,i)=> busByUnion[b.uid]=BUS_STEPS[i%BUS_STEPS.length]);
      });

      /* === 繪製 SVG === */
      const svgNS="http://www.w3.org/2000/svg";
      const svg=document.createElementNS(svgNS,"svg");
      svg.setAttribute("width","100%");
      svg.setAttribute("height","100%");
      svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.style.background="#fff";

      const root=document.createElementNS(svgNS,"g");
      root.setAttribute("transform",`translate(${MARGIN-minX},${MARGIN-minY})`);
      svg.appendChild(root);

      // 婚姻線 + union dot + 子女垂直/水平 bus
      Object.values(doc.unions).forEach(u=>{
        const [pa,pb]=u.partners;
        const NA=getXY(pa), NB=getXY(pb);
        const y=NA.y + NODE_H/2;
        const xLeft = Math.min(NA.x+NODE_W, NB.x);
        const xRight= Math.max(NA.x+NODE_W, NB.x);
        const mid = (NA.x + NB.x + NODE_W)/2;

        const line=document.createElementNS(svgNS,"line");
        line.setAttribute("x1",xLeft); line.setAttribute("y1",y);
        line.setAttribute("x2",xRight); line.setAttribute("y2",y);
        line.setAttribute("stroke","var(--line)"); line.setAttribute("stroke-width","2");
        if(u.status==="divorced") line.setAttribute("stroke-dasharray","6,4");
        root.appendChild(line);

        const dot=document.createElementNS(svgNS,"rect");
        dot.setAttribute("x",mid-5); dot.setAttribute("y",y-5);
        dot.setAttribute("width",10); dot.setAttribute("height",10);
        dot.setAttribute("fill","var(--bg)");
        dot.setAttribute("stroke","var(--border)"); dot.setAttribute("stroke-width","2");
        dot.addEventListener("click",()=>{ selected={type:"union",id:u.id}; updateSelectionInfo(); });
        root.appendChild(dot);

        // 以 block 的 mid（已處理右推）畫 bus 與孩子
        const kids=(unionKids[u.id]||[]);
        if(kids.length){
          const off = busByUnion[u.id]||0;
          const b=blocksInfo[u.id];
          kids.forEach(cid=>{
            const C=getXY(cid);
            const top = C.y;
            let busY = top + off;
            busY = Math.min(busY, top - CHILD_TOP_GAP);
            const cx = C.x + NODE_W/2;

            const path=document.createElementNS(svgNS,"path");
            path.setAttribute("d",`M ${mid} ${y} L ${mid} ${busY} L ${cx} ${busY} L ${cx} ${top}`);
            path.setAttribute("fill","none");
            path.setAttribute("stroke","var(--line)");
            path.setAttribute("stroke-width","2");
            root.appendChild(path);
          });
        }
      });

      // 人物節點
      (layout.children||[]).forEach(n=>{
        if(doc.unions[n.id]) return;
        const P=doc.persons[n.id]||{};
        const pt=getXY(n.id);
        const g=document.createElementNS(svgNS,"g");
        g.setAttribute("transform",`translate(${pt.x},${pt.y})`);
        const r=document.createElementNS(svgNS,"rect");
        r.setAttribute("rx","16"); r.setAttribute("width",NODE_W); r.setAttribute("height",NODE_H);
        r.setAttribute("fill", P.deceased? "var(--dead)":"var(--bg)");
        r.setAttribute("stroke", P.deceased? "#475569":"var(--border)");
        r.setAttribute("stroke-width","2"); r.classList.add("node");
        r.addEventListener("click",()=>{ selected={type:"person",id:n.id}; updateSelectionInfo(); });

        const t=document.createElementNS(svgNS,"text");
        t.setAttribute("x",NODE_W/2); t.setAttribute("y",NODE_H/2+5);
        t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--fg)"); t.setAttribute("font-size","14");
        t.textContent=(P.name||"?")+(P.deceased?"（殁）":"");

        g.appendChild(r); g.appendChild(t); root.appendChild(g);
      });

      host.innerHTML=""; host.appendChild(svg);

      // Pan / Zoom
      const applyVB=()=> svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      svg.addEventListener("mousedown",(e)=>{isPan=true;pan0={x:e.clientX,y:e.clientY};vb0={...vb};});
      window.addEventListener("mousemove",(e)=>{
        if(!isPan) return;
        const dx=(e.clientX-pan0.x)*(vb.w/svg.clientWidth);
        const dy=(e.clientY-pan0.y)*(vb.h/svg.clientHeight);
        vb.x=vb0.x-dx; vb.y=vb0.y-dy; applyVB();
      });
      window.addEventListener("mouseup",()=>{isPan=false;});
      svg.addEventListener("wheel",(e)=>{
        e.preventDefault();
        const s=e.deltaY>0?1.1:0.9;
        const rect=svg.getBoundingClientRect();
        const px=(e.clientX-rect.left)/rect.width, py=(e.clientY-rect.top)/rect.height;
        const nw=vb.w*s, nh=vb.h*s;
        vb.x = vb.x + vb.w*px - nw*px; vb.y = vb.y + vb.h*py - nh*py;
        vb.w=nw; vb.h=nh; applyVB();
      },{passive:false});
      document.getElementById("zoomIn").onclick = ()=>{vb.w*=0.9; vb.h*=0.9; applyVB();};
      document.getElementById("zoomOut").onclick= ()=>{vb.w*=1.1; vb.h*=1.1; applyVB();};
      document.getElementById("zoomFit").onclick= ()=>{vb={x:-MARGIN,y:-MARGIN,w:content.w,h:content.h}; applyVB();};
      document.getElementById("zoom100").onclick= ()=>{vb={x:0,y:0,w:content.w,h:content.h}; applyVB();};

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

      updateSelectionInfo();
    });
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
      info.textContent=`選取人物：${p.name||"?"}${p.deceased?"（殁）":""}（ID: ${selected.id}）`;
      btnDead.style.display="inline-block";
      btnDead.textContent=p.deceased? "取消身故":"標記身故";
      btnDead.onclick=()=>{p.deceased=!p.deceased; render();};
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const pid=selected.id;
        delete doc.persons[pid];
        // 移除與此人相關婚姻及其子女
        const kept={};
        Object.values(doc.unions).forEach(u=>{ if(!u.partners.includes(pid)) kept[u.id]=u; });
        doc.unions=kept;
        doc.children = doc.children.filter(c => c.childId!==pid && kept[c.unionId]);
        selected={type:null,id:null}; render();
      };
    }else if(selected.type==="union"){
      const u=doc.unions[selected.id]||{};
      const [a,b]=u.partners||[];
      info.textContent=`選取婚姻：${doc.persons[a]?.name||"?"} ↔ ${doc.persons[b]?.name||"?"}（狀態：${u.status==="divorced"?"離婚":"婚姻"}）`;
      btnDiv.style.display="inline-block";
      btnDiv.textContent= u.status==="divorced"? "恢復婚姻":"設為離婚";
      btnDiv.onclick=()=>{u.status = u.status==="divorced"?"married":"divorced"; render();};
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const uid_=selected.id;
        delete doc.unions[uid_];
        doc.children = doc.children.filter(c=>c.unionId!==uid_);
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
    doc.persons[id]={id,name:name||("新成員 "+(Object.keys(doc.persons).length+1)),deceased:false};
    document.getElementById("namePerson").value="";
    render();
  };

  document.getElementById("btnAddUnion").onclick=()=>{
    const a=document.getElementById("selA").value;
    const b=document.getElementById("selB").value;
    if(!a||!b||a===b) return;
    const id=uid("U");
    doc.unions[id]={id,partners:[a,b],status:"married"};
    render();
  };

  document.getElementById("btnAddChild").onclick=()=>{
    const mid=document.getElementById("selUnion").value;
    if(!mid) return;
    const name=document.getElementById("nameChild").value.trim();
    const id=uid("P");
    doc.persons[id]={id,name:name||("新子女 "+(doc.children.length+1)),deceased:false};
    // ☆ 關鍵：以資料順序 push，render 時「每段婚姻」各自建立 children block，先置中父母，再右推去避開重疊
    doc.children.push({unionId:mid, childId:id});
    document.getElementById("nameChild").value="";
    render();
  };

  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

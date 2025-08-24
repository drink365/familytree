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
<title>Family Tree – root = person, multi-marriage branches</title>
<style>
  :root{
    --bg:#0b3d4f;
    --bg-dead:#6b7280;
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
      <span class="legend"><div class="lgBox dead"></div>身故（灰底＋「（殁）」）</span>
      <span>離婚：婚線為虛線（有子女仍保留）</span>
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
        提示：拖曳平移、滾輪縮放（Mac 兩指縮放）；「載入示例」可快速測試多婚。
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
  /* 幾何參數 */
  const NODE_W = 140, NODE_H = 56;
  const COUPLE_GAP = 24;        // 夫妻固定距離（不會被拉開）
  const GEN_GAP = 90;           // 代與代距
  const SIBLING_GAP = 36;       // 同父母子女間距
  const BRANCH_GAP = 36;        // 同一人的多段婚姻分支間距（左右各自）
  const ROOT_GAP = 60;          // 不同根人物之間
  const BUS_UP = 14;
  const PAD = 80;

  /* 視圖 */
  let vb = {x:0,y:0,w:1200,h:680};
  let content = {w:1200,h:680};
  let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};

  /* 資料 */
  let doc = { persons:{}, unions:{}, children:[] };
  let selected = { type:null, id:null };

  const uid = p => p + "_" + Math.random().toString(36).slice(2,9);

  /* 工具 */
  function unionsOfPerson(pid){ return Object.values(doc.unions).filter(u=>u.partners.includes(pid)); }
  function isPersonRoot(pid){ return !doc.children.some(c=>c.childId===pid); }
  function childrenOfUnion(uid){
    return doc.children.filter(c=>c.unionId===uid).map(c=>doc.persons[c.childId]).filter(Boolean);
  }

  /* 子女 block（若孩子也有婚姻，往下接第一段） */
  function childBlockForPerson(pid){
    const myU = unionsOfPerson(pid)[0];
    if(myU){ return branchAsChild(myU, pid); }
    // 純單點
    const width=NODE_W, height=NODE_H;
    return {
      width, height, childCenterX: NODE_W/2,
      place:(x0,y0)=>({nodes:[nodeRect(pid,x0,y0)], edges:[], minX:x0, maxX:x0+width})
    };
  }

  /* 分支：由 anchor 人物 + 配偶 + 子女群（不重畫 anchor） */
  function branchAsChild(union, anchorChildId){
    // anchorChildId 只用來抓孫輩時的方向，分支本身仍照 union 畫
    return branchOfUnion(union, union.partners[0]); // 方向無所謂，外層會重新定位
  }

  function branchOfUnion(u, anchorPid){
    const spouseId = u.partners[0]===anchorPid ? u.partners[1] : u.partners[0];
    const kids = childrenOfUnion(u.id);
    const kidBlocks = kids.map(k=>childBlockForPerson(k.id));

    const spouseSpan = COUPLE_GAP + NODE_W; // 從 anchor 邊到配偶邊
    const kidsWidth = kidBlocks.length ? kidBlocks.reduce((s,b)=>s+b.width,0) + SIBLING_GAP*(kidBlocks.length-1) : 0;
    const width = Math.max(spouseSpan, kidsWidth);
    const height = NODE_H + (kidBlocks.length ? (BUS_UP + GEN_GAP + Math.max(...kidBlocks.map(b=>b.height))) : 0);

    function placeLeft(ax, y0, offset){ // ax = anchor 左上角 x
      const nodes=[], edges=[];
      const anchorLeft = ax;
      const spanRight = anchorLeft - offset;     // 這個分支的右界（貼齊 anchor 左邊留出 offset）
      const spanLeft  = spanRight - width;

      // 配偶靠此分支內側
      const spouseRight = spanRight - COUPLE_GAP;
      const spouseLeft  = spouseRight - NODE_W;
      nodes.push(nodeRect(spouseId, spouseLeft, y0));

      // 婚線
      const ymid = y0 + NODE_H/2;
      edges.push(line(spouseRight, ymid, anchorLeft, ymid, (u.status==="divorced")));
      const midX = (spouseRight + anchorLeft)/2;

      if(kidBlocks.length){
        const busY = ymid + BUS_UP;
        let cx = midX - (kidsWidth/2);
        let min=Infinity, max=-Infinity;
        kidBlocks.forEach(b=>{
          const placed = b.place ? b.place(cx, y0 + NODE_H + BUS_UP) : branchOfUnion(unionsOfPerson(doc.persons[b.personId]?.id||"")[0], anchorPid).placeRight(ax, y0, 0); // 保底
          nodes.push(...placed.nodes); edges.push(...placed.edges);
        /* 對純 childBlock */
          min=Math.min(min, cx);
          max=Math.max(max, cx+b.width);
          // drop 線
          edges.push(line(cx + (b.childCenterX||NODE_W/2), busY, cx + (b.childCenterX||NODE_W/2), y0 + NODE_H + BUS_UP));
          cx += b.width + SIBLING_GAP;
        });
        // 父母中點 → bus
        edges.push(line(midX, ymid, midX, busY));
        edges.push(line(min, busY, max, busY));
      }
      return {nodes,edges,minX:spanLeft,maxX:spanRight};
    }

    function placeRight(ax, y0, offset){ // ax = anchor 左上角 x
      const nodes=[], edges=[];
      const anchorRight = ax + NODE_W;
      const spanLeft = anchorRight + offset;     // 此分支左界（貼齊 anchor 右邊留出 offset）
      const spanRight = spanLeft + width;

      // 配偶靠此分支內側
      const spouseLeft  = spanLeft + COUPLE_GAP;
      const spouseRight = spouseLeft + NODE_W;
      nodes.push(nodeRect(spouseId, spouseLeft, y0));

      // 婚線
      const ymid = y0 + NODE_H/2;
      edges.push(line(anchorRight, ymid, spouseLeft, ymid, (u.status==="divorced")));
      const midX = (anchorRight + spouseLeft)/2;

      if(kidBlocks.length){
        const busY = ymid + BUS_UP;
        let cx = midX - (kidsWidth/2);
        let min=Infinity, max=-Infinity;
        kidBlocks.forEach(b=>{
          const placed = b.place ? b.place(cx, y0 + NODE_H + BUS_UP) : childBlockForPerson(b.personId).place(cx, y0 + NODE_H + BUS_UP);
          nodes.push(...placed.nodes); edges.push(...placed.edges);
          min=Math.min(min, cx);
          max=Math.max(max, cx+b.width);
          // drop 線
          edges.push(line(cx + (b.childCenterX||NODE_W/2), busY, cx + (b.childCenterX||NODE_W/2), y0 + NODE_H + BUS_UP));
          cx += b.width + SIBLING_GAP;
        });
        edges.push(line(midX, ymid, midX, busY));
        edges.push(line(min, busY, max, busY));
      }
      return {nodes,edges,minX:spanLeft,maxX:spanRight};
    }

    return { width, height,
      placeLeft, placeRight
    };
  }

  /* 以「人」為根的 hub：本人在中間，離婚分支往左，其餘往右 */
  function hubOfRootPerson(pid){
    const myUnions = unionsOfPerson(pid);
    // 左：離婚；右：其餘（你也可以改依時間排序等）
    const leftUs  = myUnions.filter(u=>u.status==="divorced");
    const rightUs = myUnions.filter(u=>u.status!=="divorced");

    const leftBranches  = leftUs.map(u=>branchOfUnion(u, pid));
    const rightBranches = rightUs.map(u=>branchOfUnion(u, pid));

    const leftWidth  = leftBranches.reduce((s,b)=> s + b.width, 0) + (leftBranches.length? BRANCH_GAP*(leftBranches.length-1):0);
    const rightWidth = rightBranches.reduce((s,b)=> s + b.width, 0) + (rightBranches.length? BRANCH_GAP*(rightBranches.length-1):0);

    const kidsHLeft  = leftBranches.length ? Math.max(...leftBranches.map(b=>b.height)) : 0;
    const kidsHRight = rightBranches.length ? Math.max(...rightBranches.map(b=>b.height)) : 0;
    const width  = leftWidth + NODE_W + rightWidth;
    const height = Math.max(NODE_H, NODE_H + Math.max(kidsHLeft, kidsHRight));

    function place(x0,y0){
      const nodes=[], edges=[];
      const ax = x0 + leftWidth; // 本人左上角
      nodes.push(nodeRect(pid, ax, y0));

      // 左側從靠近本人開始往左排
      let acc = 0;
      leftBranches.forEach((b,i)=>{
        const placed = b.placeLeft(ax, y0, acc);
        nodes.push(...placed.nodes); edges.push(...placed.edges);
        acc += b.width + BRANCH_GAP;
      });

      // 右側從靠近本人開始往右排
      acc = 0;
      rightBranches.forEach((b,i)=>{
        const placed = b.placeRight(ax, y0, acc);
        nodes.push(...placed.nodes); edges.push(...placed.edges);
        acc += b.width + BRANCH_GAP;
      });

      return {nodes,edges,minX:x0,maxX:x0+width};
    }

    // 回報「已涵蓋」的人（避免另一個根配偶再被當 hub 畫一次）
    const covered = new Set([pid]);
    myUnions.forEach(u=>u.partners.forEach(p=>covered.add(p)));

    return { width, height, place, covered };
  }

  /* 建立所有根人物 hub（避免重複） */
  function buildRootHubs(){
    const roots = Object.keys(doc.persons).filter(isPersonRoot)
                  .sort((a,b)=>(doc.persons[a].name||"").localeCompare(doc.persons[b].name||""));
    const hubs=[], used=new Set();
    roots.forEach(pid=>{
      if(used.has(pid)) return;
      const hub = hubOfRootPerson(pid);
      hubs.push(hub);
      hub.covered.forEach(p=>used.add(p));
    });
    return hubs;
  }

  /* SVG primitives */
  function nodeRect(pid, x, y){
    const p = doc.persons[pid] || {name:"?"};
    const g = document.createElementNS("http://www.w3.org/2000/svg","g");
    g.setAttribute("transform",`translate(${x},${y})`);
    const r = document.createElementNS("http://www.w3.org/2000/svg","rect");
    r.setAttribute("rx","16"); r.setAttribute("width",NODE_W); r.setAttribute("height",NODE_H);
    r.setAttribute("fill",p.deceased?"var(--bg-dead)":"var(--bg)");
    r.setAttribute("stroke",p.deceased?"#475569":"var(--border)"); r.setAttribute("stroke-width","2");
    r.classList.add("node");
    r.addEventListener("click",()=>{ selected={type:"person",id:pid}; updateSelectionInfo(); });
    const t=document.createElementNS("http://www.w3.org/2000/svg","text");
    t.setAttribute("x",NODE_W/2); t.setAttribute("y",NODE_H/2+5);
    t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--fg)"); t.setAttribute("font-size","14");
    t.textContent=(p.name||"?")+(p.deceased?"（殁）":"");
    g.appendChild(r); g.appendChild(t);
    return g;
  }
  function line(x1,y1,x2,y2,dashed=false){
    const ln=document.createElementNS("http://www.w3.org/2000/svg","line");
    ln.setAttribute("x1",x1); ln.setAttribute("y1",y1);
    ln.setAttribute("x2",x2); ln.setAttribute("y2",y2);
    ln.setAttribute("stroke","var(--line)"); ln.setAttribute("stroke-width","2");
    if(dashed) ln.setAttribute("stroke-dasharray","6,4");
    return ln;
  }

  /* 渲染 */
  function render(autoFit=false){
    syncSelectors();
    const host=document.getElementById("viewport"); host.innerHTML="";
    const hubs = buildRootHubs();

    let cursorX=PAD, topY=PAD;
    const nodes=[], edges=[];
    let minX=Infinity,maxX=-Infinity,maxY=0;

    hubs.forEach(h=>{
      const placed = h.place(cursorX, topY);
      nodes.push(...placed.nodes); edges.push(...placed.edges);
      minX=Math.min(minX, placed.minX); maxX=Math.max(maxX, placed.maxX);
      maxY=Math.max(maxY, topY+h.height);
      cursorX = placed.maxX + ROOT_GAP;
    });

    const w=Math.max(800,(maxX-minX)+PAD*2);
    const h=Math.max(600,(maxY-PAD)+PAD);
    content={w:h>content.h?w:content.w,h};
    if(autoFit) vb={x:0,y:0,w,h};

    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
    svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    svg.style.background="#fff";

    const g=document.createElementNS("http://www.w3.org/2000/svg","g");
    svg.appendChild(g);
    edges.forEach(e=>g.appendChild(e)); nodes.forEach(n=>g.appendChild(n));
    host.appendChild(svg);

    const applyVB=()=>svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    svg.addEventListener("mousedown",e=>{isPanning=true;panStart={x:e.clientX,y:e.clientY};vbStart={x:vb.x,y:vb.y,w:vb.w,h:vb.h};});
    window.addEventListener("mousemove",e=>{
      if(!isPanning) return;
      const rect=svg.getBoundingClientRect();
      const dx=(e.clientX-panStart.x)*(vb.w/rect.width);
      const dy=(e.clientY-panStart.y)*(vb.h/rect.height);
      vb.x=vbStart.x-dx; vb.y=vbStart.y-dy; applyVB();
    });
    window.addEventListener("mouseup",()=>{isPanning=false;});
    svg.addEventListener("wheel",e=>{
      e.preventDefault();
      const s=(e.deltaY>0)?1.1:0.9;
      const rect=svg.getBoundingClientRect();
      const px=(e.clientX-rect.left)/rect.width, py=(e.clientY-rect.top)/rect.height;
      const nw=vb.w*s, nh=vb.h*s;
      vb.x = vb.x + vb.w*px - nw*px; vb.y = vb.y + vb.h*py - nh*py;
      vb.w=nw; vb.h=nh; applyVB();
    },{passive:false});

    document.getElementById("zoomIn").onclick=()=>{ vb.w*=0.9; vb.h*=0.9; applyVB(); };
    document.getElementById("zoomOut").onclick=()=>{ vb.w*=1.1; vb.h*=1.1; applyVB(); };
    document.getElementById("zoomFit").onclick=()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };
    document.getElementById("zoom100").onclick=()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };

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
  }

  /* UI：選單與動作 */
  function syncSelectors(){
    const persons = Object.values(doc.persons);
    const unions  = Object.values(doc.unions);
    const selA=document.getElementById("selA");
    const selB=document.getElementById("selB");
    const selU=document.getElementById("selUnion");
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

  function updateSelectionInfo(){
    const el=document.getElementById("selInfo");
    const btnDead=document.getElementById("btnToggleDead");
    const btnDiv =document.getElementById("btnToggleDivorce");
    const btnDel=document.getElementById("btnDelete");
    btnDead.style.display="none"; btnDiv.style.display="none"; btnDel.style.display="none";
    if(!selected.type){ el.textContent="尚未選取節點。"; return; }

    if(selected.type==="person"){
      const p=doc.persons[selected.id]||{};
      el.textContent="選取人物："+(p.name||"?")+(p.deceased?"（殁）":"")+"（ID: "+selected.id+"）";
      btnDead.style.display="inline-block";
      btnDead.textContent=p.deceased?"取消身故":"標記身故";
      btnDead.onclick=()=>{ p.deceased=!p.deceased; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const pid=selected.id; delete doc.persons[pid];
        const kept={}; Object.values(doc.unions).forEach(u=>{ if(!u.partners.includes(pid)) kept[u.id]=u; });
        doc.unions=kept;
        doc.children=doc.children.filter(cl=>cl.childId!==pid && !!doc.unions[cl.unionId]);
        selected={type:null,id:null}; render();
      };
    }else{
      const u=doc.unions[selected.id]||{}; const [a,b]=u.partners||[];
      el.textContent="選取婚姻："+(doc.persons[a]?.name||"?")+" ↔ "+(doc.persons[b]?.name||"?")+"（"+(u.status==="divorced"?"離婚":"婚姻")+"）";
      btnDiv.style.display="inline-block";
      btnDiv.textContent=(u.status==="divorced")?"恢復婚姻":"設為離婚";
      btnDiv.onclick=()=>{ u.status=(u.status==="divorced")?"married":"divorced"; render(); };
      btnDel.style.display="inline-block";
      btnDel.onclick=()=>{
        const uid_=selected.id; delete doc.unions[uid_];
        doc.children=doc.children.filter(cl=>cl.unionId!==uid_);
        selected={type:null,id:null}; render();
      };
    }
  }

  /* 範例與新增 */
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
  [m1,m2,m3,m4,m5,m6].forEach(mm=>u[mm.id]=mm);

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
    {unionId:m6.id, childId:id("三孩B")},
  ];
  doc = { persons:p, unions:u, children };
  selected = {type:null,id:null};

  // 確保初次渲染有正確 viewBox
  vb = {x:0,y:0,w:1200,h:680};
  render(true);
}

})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

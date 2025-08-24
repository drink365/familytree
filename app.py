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
<title>Family Tree – spacing by generation</title>
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
        提示：滑鼠拖曳可平移；滾輪縮放（Mac 觸控板兩指縮放）。
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
  /* 幾何設定 */
  const NODE_W = 140, NODE_H = 56;
  const COUPLE_GAP = 24;        // 夫妻固定距離（不被拉動）
  const GEN_GAP = 90;           // 代與代之間距
  const SIBLING_GAP = 36;       // 同父母子女間距
  const ROOT_GAP = 60;          // 多個根家族左右間距
  const BUS_UP = 14;            // 婚姻中點→bus 垂直距離
  const PAD = 80;               // 畫布邊界

  /* 視圖變數 */
  let vb = {x:0,y:0,w:1200,h:680};
  let content = {w:1200,h:680};
  let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};

  /* 資料 */
  let doc = { persons:{}, unions:{}, children:[] };
  let selected = { type:null, id:null };

  const uid = p => p + "_" + Math.random().toString(36).slice(2,9);

  /* 工具 */
  function unionsOfPerson(pid){
    return Object.values(doc.unions).filter(u=>u.partners.includes(pid));
  }
  function parentsUnionOfChild(pid){
    const rec = doc.children.find(c=>c.childId===pid);
    return rec ? doc.unions[rec.unionId] : null;
  }
  function childrenOfUnion(uid){
    return doc.children.filter(c=>c.unionId===uid).map(c=>doc.persons[c.childId]).filter(Boolean);
  }
  function isPersonRoot(pid){
    // 「沒有父母」的人
    return !doc.children.some(c=>c.childId===pid);
  }
  function isUnionRoot(uid){
    const u = doc.unions[uid]; if(!u) return false;
    // 兩位配偶都沒有父母 → 這段婚姻是「根家族」
    return isPersonRoot(u.partners[0]) && isPersonRoot(u.partners[1]);
  }

  /* 佈局：建立「婚姻 block」樹，先算寬度再定位 */
  // block 結構：{width, height, place(x,y)->{nodes,edges,minX,maxX}, childCenterX}
  function blockOfUnion(uid){
    const u = doc.unions[uid];
    const kids = childrenOfUnion(uid);

    // 把孩子轉成子 block（若孩子有自己的婚姻，就用那段婚姻的 block；否則就是單點）
    const kidBlocks = kids.map(k=>{
      const myU = unionsOfPerson(k.id)[0]; // 取第一段婚姻往下（簡化）
      if(myU){
        const b = blockOfUnion(myU.id);
        return { type:"union", unionId:myU.id, block:b, width:b.width, height:b.height };
      }else{
        const w=NODE_W, h=NODE_H;
        return {
          type:"single", personId:k.id, width:w, height:h,
          place:(x0,y0)=>{
            const nodes=[nodeRect(k.id,x0,y0)], edges=[];
            return {nodes,edges,minX:x0,maxX:x0+w};
          },
          childCenterX:w/2
        };
      }
    });

    const coupleWidth = NODE_W*2 + COUPLE_GAP;
    const kidsWidth = kidBlocks.length ? kidBlocks.reduce((s,b)=>s+b.width,0) + SIBLING_GAP*(kidBlocks.length-1) : 0;
    const width = Math.max(coupleWidth, kidsWidth);
    const kidBelowY = NODE_H + BUS_UP;

    function place(x0,y0){
      const nodes=[], edges=[];
      const mid = x0 + width/2;

      // 夫妻（固定 gap）
      const [pa,pb]=u.partners;
      const leftX = mid - (COUPLE_GAP/2 + NODE_W);
      const rightX= mid + (COUPLE_GAP/2);
      nodes.push(nodeRect(pa,leftX,y0));
      nodes.push(nodeRect(pb,rightX,y0));

      // 婚線＋中點
      const ymid = y0 + NODE_H/2;
      edges.push(line(leftX+NODE_W, ymid, rightX, ymid, (u.status==="divorced")));
      const dot = rect(mid-5, ymid-5, 10, 10);
      dot.setAttribute("fill","var(--bg)");
      dot.setAttribute("stroke","var(--border)");
      dot.setAttribute("stroke-width","2");
      dot.addEventListener("click",()=>{ selected={type:"union",id:uid}; updateSelectionInfo(); });
      nodes.push(dot);

      if(kidBlocks.length){
        // 子女群組：以自己的總寬度置中於 mid，下拉 bus 到各子女
        const busY = ymid + BUS_UP;
        let cx = mid - (kidBlocks.reduce((s,b)=>s+b.width,0) + SIBLING_GAP*(kidBlocks.length-1))/2;
        let spanMin=Infinity, spanMax=-Infinity;

        kidBlocks.forEach((b,idx)=>{
          const placed = (b.type==="union")
            ? b.block.place(cx, y0 + kidBelowY)
            : b.place(cx, y0 + kidBelowY);
          nodes.push(...placed.nodes); edges.push(...placed.edges);

          const childCenter = cx + (b.type==="union" ? b.block.childCenterX : b.childCenterX);
          // bus → drop → child
          edges.push(line(childCenter, busY, childCenter, y0 + kidBelowY));
          spanMin=Math.min(spanMin, placed.minX);
          spanMax=Math.max(spanMax, placed.maxX);
          cx += b.width + SIBLING_GAP;
        });

        // 父母中點 → bus
        edges.push(line(mid, ymid, mid, busY));
        // bus（只覆蓋自己孩子的 span）
        edges.push(line(spanMin, busY, spanMax, busY));
      }

      return {nodes,edges,minX:x0,maxX:x0+width};
    }

    return { width, height: NODE_H + (kidBlocks.length? (BUS_UP + kidBelowY + Math.max(...kidBlocks.map(b=>b.height))) : 0),
             place, childCenterX: width/2 };
  }

  /* 找所有「根婚姻」做為最上層；若有獨立的 root 單身者也會擺上去 */
  function buildRootBlocks(){
    const rootUnionIds = Object.keys(doc.unions).filter(isUnionRoot);
    rootUnionIds.sort();  // 穩定順序
    const blocks = rootUnionIds.map(uid=>blockOfUnion(uid));

    // 找沒有任何婚姻、且沒有父母的單身 root
    const soloRoots = Object.keys(doc.persons).filter(pid=>{
      return isPersonRoot(pid) && unionsOfPerson(pid).length===0;
    });
    soloRoots.forEach(pid=>{
      const w=NODE_W,h=NODE_H;
      blocks.push({
        width:w,height:h,childCenterX:w/2,
        place:(x0,y0)=>{
          const nodes=[nodeRect(pid,x0,y0)], edges=[];
          return {nodes,edges,minX:x0,maxX:x0+w};
        }
      });
    });

    return blocks;
  }

  /* SVG基本元件 */
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
  function rect(x,y,w,h){
    const r=document.createElementNS("http://www.w3.org/2000/svg","rect");
    r.setAttribute("x",x); r.setAttribute("y",y); r.setAttribute("width",w); r.setAttribute("height",h);
    return r;
  }
  function line(x1,y1,x2,y2,dashed=false){
    const ln=document.createElementNS("http://www.w3.org/2000/svg","line");
    ln.setAttribute("x1",x1); ln.setAttribute("y1",y1);
    ln.setAttribute("x2",x2); ln.setAttribute("y2",y2);
    ln.setAttribute("stroke","var(--line)"); ln.setAttribute("stroke-width","2");
    if(dashed) ln.setAttribute("stroke-dasharray","6,4");
    return ln;
  }

  /* 主渲染 */
  function render(autoFit=false){
    syncSelectors();
    const host = document.getElementById("viewport");
    host.innerHTML="";

    const blocks = buildRootBlocks();
    let cursorX = PAD, topY = PAD;
    const nodes=[], edges=[];
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;

    blocks.forEach(b=>{
      const placed = b.place(cursorX, topY);
      nodes.push(...placed.nodes); edges.push(...placed.edges);
      minX=Math.min(minX, placed.minX); maxX=Math.max(maxX, placed.maxX);
      minY=Math.min(minY, topY);       maxY=Math.max(maxY, topY + b.height);
      cursorX = placed.maxX + ROOT_GAP;
    });

    const w=Math.max(800,(maxX-minX)+PAD*2), h=Math.max(600,(maxY-minY)+PAD*2);
    content={w,h}; if(autoFit) vb={x:0,y:0,w,h};

    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
    svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    svg.style.background="#fff";

    const g=document.createElementNS("http://www.w3.org/2000/svg","g");
    svg.appendChild(g);
    edges.forEach(e=>g.appendChild(e)); nodes.forEach(n=>g.appendChild(n));

    host.appendChild(svg);

    /* 平移／縮放 */
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

    document.getElementById("zoomIn").onclick = ()=>{ vb.w*=0.9; vb.h*=0.9; applyVB(); };
    document.getElementById("zoomOut").onclick= ()=>{ vb.w*=1.1; vb.h*=1.1; applyVB(); };
    document.getElementById("zoomFit").onclick= ()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };
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

    updateSelectionInfo();
  }

  /* 右側表單 / 操作 */
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

  /* 範例 & 新增動作 */
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
    render(true);
  }

  function clearAll(){
    doc = { persons:{}, unions:{}, children:[] };
    selected = {type:null,id:null};
    render(true);
  }

  document.getElementById("btnDemo").addEventListener("click", ()=>demo());
  document.getElementById("btnClear").addEventListener("click", clearAll);

  document.getElementById("btnAddPerson").addEventListener("click", ()=>{
    const name=document.getElementById("namePerson").value.trim();
    const id=uid("P");
    doc.persons[id]={id,name:(name||"新成員"),deceased:false};
    document.getElementById("namePerson").value=""; render();
  });

  document.getElementById("btnAddUnion").addEventListener("click", ()=>{
    const a=document.getElementById("selA").value;
    const b=document.getElementById("selB").value;
    if(!a||!b||a===b) return;
    const id=uid("U"); doc.unions[id]={id,partners:[a,b],status:"married"}; render();
  });

  document.getElementById("btnAddChild").addEventListener("click", ()=>{
    const mid=document.getElementById("selUnion").value; if(!mid) return;
    const name=document.getElementById("nameChild").value.trim();
    const id=uid("P");
    doc.persons[id]={id,name:(name||"新子女"),deceased:false};
    doc.children.push({unionId:mid, childId:id});   // 以建立順序呈現
    document.getElementById("nameChild").value=""; render();
  });

  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

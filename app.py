# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree (QFT)", page_icon="🌳", layout="wide")

HTML = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Family Tree</title>
<style>
  :root{
    --line:#0f3c4d;
    --nodeMan:#d8eaff;
    --nodeWoman:#ffdbe1;
    --stroke:#164b5f;
    --text:#0b2430;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:#f8fafc}
  .toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid #e5e7eb;padding:.75rem 1rem;background:#fff;position:sticky;top:0;z-index:10}
  .btn{background:#075985;color:#fff;border:none;border-radius:.7rem;padding:.5rem .8rem;cursor:pointer}
  .btn.sec{background:#334155}
  .btn.ok{background:#0f766e}
  .pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
  .row{display:flex;gap:.5rem;align-items:center;margin:.35rem 0;flex-wrap:wrap}
  select,input[type=text]{border:1px solid #cbd5e1;border-radius:.6rem;padding:.45rem .6rem}
  .canvas{height:760px;overflow:hidden;border:1px solid #e5e7eb;border-radius:1rem;background:#fff}
  .viewport{width:100%;height:100%;overflow:hidden}
  svg text{user-select:none}
  .node{filter:drop-shadow(0 1px 0.5px rgba(0,0,0,.12))}
  .zoombar{display:flex;gap:.5rem;margin-left:auto}
</style>
</head>
<body>
  <div class="toolbar">
    <strong>🌳 家族樹（Quick Family Tree 風格）</strong>
    <button class="btn ok" id="btnDemo">載入示範</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="zoombar">
      <button class="btn" id="zoomOut">－</button>
      <button class="btn" id="zoomIn">＋</button>
      <button class="btn" id="zoomFit">置中</button>
      <button class="btn" id="btnSVG">下載 SVG</button>
    </div>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas"><div class="viewport" id="vp"></div></div>
      <div style="color:#64748b;font-size:.9rem;margin-top:.5rem">提示：滑鼠拖曳平移，滾輪縮放；右上可置中與下載 SVG。</div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">快速新增</h3>
      <div class="row">
        <input type="text" id="namePerson" placeholder="新人物姓名" />
        <select id="sexPerson"><option>男</option><option>女</option></select>
        <button class="btn ok" id="btnAddPerson">新增人物</button>
      </div>

      <div class="row">
        <select id="selA"></select>
        <span>×</span>
        <select id="selB"></select>
        <label style="display:flex;align-items:center;gap:.3rem">
          <input type="checkbox" id="setDiv" /> 離婚
        </label>
        <button class="btn ok" id="btnAddUnion">建立/更新婚姻</button>
      </div>

      <div class="row">
        <select id="selUnion"></select>
        <input type="text" id="nameChild" placeholder="新子女姓名" />
        <select id="sexChild"><option>男</option><option>女</option></select>
        <button class="btn ok" id="btnAddChild">加入子女</button>
      </div>
    </div>
  </div>

<script>
(function(){
  // ─── 幾何（QFT 風格） ─────────────────────────
  const W=140, H=56;
  const G_COUPLE=36, G_SIB=36, G_UNION=72;
  const PADDING=48, BUS_UP=18, BUS_SHORT=18, FONT=14;

  // 狀態
  let doc={persons:{}, marriages:{}, children:[]};
  const uid = p => p+"_"+Math.random().toString(36).slice(2,9);

  // Demo
  function loadDemo(){
    const p={}, id={};
    const P=(n,s)=>{const i=uid("P"); p[i]={id:i,name:n,sex:s,alive:true}; id[n]=i; return i;};
    P("陳一郎","男");P("陳前妻","女");P("陳妻","女");
    P("陳大","男");P("陳大嫂","女");
    P("陳二","男");P("陳二嫂","女");
    P("陳三","男");P("陳三嫂","女");
    P("王子","男");P("王子妻","女");
    P("王孫","男");P("二孩A","女");P("二孩B","男");P("二孩C","女");
    P("三孩A","男");P("三孩B","女");
    const m={}, M=(a,b,d=false)=>{const i=uid("M"); m[i]={id:i,a:id[a],b:id[b],divorced:d}; return i;};
    const c=[]; const C=(mid,child)=>c.push({mid,child:id[child]});
    const m1=M("陳一郎","陳前妻",true);
    const m2=M("陳一郎","陳妻");
    const m3=M("王子","王子妻");
    const m4=M("陳大","陳大嫂");
    const m5=M("陳二","陳二嫂");
    const m6=M("陳三","陳三嫂");
    C(m1,"王子");
    C(m2,"陳大");C(m2,"陳二");C(m2,"陳三");
    C(m3,"王孫");
    C(m5,"二孩A");C(m5,"二孩B");C(m5,"二孩C");
    C(m6,"三孩A");C(m6,"三孩B");
    doc={persons:p, marriages:m, children:c};
    render(true);
  }
  function clearAll(){ doc={persons:{},marriages:{},children:[]}; render(true); }

  // 下拉選單同步
  function syncSelectors(){
    const A=document.getElementById("selA"), B=document.getElementById("selB"), U=document.getElementById("selUnion");
    [A,B,U].forEach(s=>s.innerHTML="");
    Object.values(doc.persons).forEach(p=>{
      for(const s of [A,B]){
        const o=document.createElement("option"); o.value=p.id; o.textContent=p.name; s.appendChild(o);
      }
    });
    Object.values(doc.marriages).forEach(m=>{
      const o=document.createElement("option");
      const a=doc.persons[m.a]?.name||"?"; const b=doc.persons[m.b]?.name||"?";
      o.value=m.id; o.textContent=`${a} ↔ ${b}${m.divorced?"（離）":""}`;
      U.appendChild(o);
    });
  }

  // 關聯表
  function buildMaps(){
    const unionsByPerson={}, parentsOf={}, kidsByUnion={}, hasChildren=new Set();
    Object.values(doc.marriages).forEach(m=>{
      (unionsByPerson[m.a]||(unionsByPerson[m.a]=[])).push(m.id);
      (unionsByPerson[m.b]||(unionsByPerson[m.b]=[])).push(m.id);
    });
    doc.children.forEach(x=>{
      (kidsByUnion[x.mid]||(kidsByUnion[x.mid]=[])).push(x.child);
      const m=doc.marriages[x.mid]; if(!m) return;
      parentsOf[x.child]=[m.a,m.b];
      hasChildren.add(m.a); hasChildren.add(m.b);
    });
    return {unionsByPerson, parentsOf, kidsByUnion, hasChildren};
  }

  // 只選「沒有父母且有子女」的根；若一個都沒有，再退回所有沒有父母者
  function pickRoots(maps){
    const all=Object.keys(doc.persons);
    const r1=all.filter(pid => !maps.parentsOf[pid] && maps.hasChildren.has(pid));
    if(r1.length>0) return r1;
    return all.filter(pid => !maps.parentsOf[pid]);
  }

  // 子樹量測
  function measurePerson(pid, maps, memoP={}, memoU={}){
    if(memoP[pid]) return memoP[pid];
    const unions=(maps.unionsByPerson[pid]||[]);
    if(unions.length===0) return memoP[pid]={w:W, t:"person"};
    let total=0; unions.forEach(mid=> total += measureUnion(mid, maps, memoP, memoU).w );
    total += (unions.length-1)*G_COUPLE;
    const minCenter = W + G_COUPLE + W;
    return memoP[pid]={w:Math.max(minCenter,total), t:"person", unions};
  }
  function measureUnion(mid, maps, memoP={}, memoU={}){
    if(memoU[mid]) return memoU[mid];
    const kids=(maps.kidsByUnion[mid]||[]);
    if(kids.length===0) return memoU[mid]={w:W+G_COUPLE+W, t:"union", kids:[]};
    let total=0; kids.forEach(cid => total += measurePerson(cid, maps, memoP, memoU).w);
    total += (kids.length-1)*G_SIB;
    total = Math.max(total, W+G_COUPLE+W);
    return memoU[mid]={w:total, t:"union", kids};
  }

  // 佈局與繪製
  let vb={x:0,y:0,w:1200,h:700}, content={w:1200,h:700}, isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};
  function render(autoFit=false){
    syncSelectors();
    const host=document.getElementById("vp");
    host.innerHTML="<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    const maps=buildMaps();
    const roots=pickRoots(maps);
    if(roots.length===0){ host.innerHTML="<div style='padding:1rem;color:#64748b'>尚無資料</div>"; return; }

    const memoP={}, memoU={};
    roots.forEach(r=>measurePerson(r, maps, memoP, memoU));

    const nodes=[]; const wires=[];
    const placedPersons=new Set();   // ← 新增：避免重畫
    const placedUnions=new Set();

    function drawPerson(pid, x, y){
      if(!doc.persons[pid]) return;
      if(!placedPersons.has(pid)){ // 第一次畫才加節點
        const p=doc.persons[pid];
        nodes.push({type:"person", id:pid, name:p.name, sex:p.sex, x, y, rx:(p.sex==="女")?26:8});
        placedPersons.add(pid);
      }
    }

    function drawUnion(mid, cx, topY){
      if(placedUnions.has(mid)) return;           // ← 新增：避免同一婚姻被不同 root 重畫
      const m=doc.marriages[mid]; if(!m) return;
      placedUnions.add(mid);

      const ax=cx-(W+G_COUPLE/2), bx=cx+(G_COUPLE/2), ay=topY, by=topY;
      drawPerson(m.a, ax, ay);
      drawPerson(m.b, bx, by);

      const hubX=cx, hubY=ay+H/2;
      nodes.push({type:"hub", x:hubX, y:hubY});
      wires.push({x1:ax+W,y1:ay+H/2,x2:hubX,y2:hubY,dashed:m.divorced});
      wires.push({x1:bx,  y1:by+H/2,x2:hubX,y2:hubY,dashed:m.divorced});

      const kids=(maps.kidsByUnion[mid]||[]);
      if(kids.length===0) return;
      const busY=topY+H+(G_UNION-BUS_UP);
      const childY=topY+H+G_UNION;

      // 中線到 bus（再左右兩個短段，避免跨婚姻）
      wires.push({x1:hubX,y1:hubY,x2:hubX,y2:busY});
      wires.push({x1:hubX,y1:busY,x2:hubX-BUS_SHORT,y2:busY});
      wires.push({x1:hubX,y1:busY,x2:hubX+BUS_SHORT,y2:busY});

      let widths = kids.map(cid => measurePerson(cid, maps, memoP, memoU).w);
      let total = widths.reduce((a,b)=>a+b,0) + (kids.length-1)*G_SIB;
      let start = cx - total/2;

      kids.forEach((cid,i)=>{
        const w=widths[i];
        const ccx=start + w/2;
        wires.push({x1:ccx,y1:busY,x2:ccx,y2:childY});
        drawPersonTree(cid, ccx, childY);
        start += w + G_SIB;
      });
    }

    function drawPersonTree(pid, cx, topY){
      const info=measurePerson(pid, maps, memoP, memoU);
      const unions=info.unions||[];
      if(unions.length===0){ drawPerson(pid, cx - W/2, topY); return; }

      // 如果這個人早就畫過了，我們仍可能需要把他「尚未畫過」的婚姻畫出來
      drawPerson(pid, cx - W/2, topY);

      const widths=unions.map(mid=>measureUnion(mid, maps, memoP, memoU).w);
      const totalW=Math.max(info.w, widths.reduce((a,b)=>a+b,0) + (unions.length-1)*G_COUPLE);
      let start=cx - totalW/2;
      unions.forEach((mid,i)=>{
        const w=widths[i];
        const midCx=start + w/2;
        drawUnion(mid, midCx, topY);
        start += w + G_COUPLE;
      });
    }

    // 擺放多個根：若某根的人其實已被先前根覆蓋，直接跳過（不再產生新的重複樹）
    const rootWidths = roots.map(r=>measurePerson(r, maps, memoP, memoU).w);
    let sumW=0; for(let i=0;i<roots.length;i++){ sumW+=rootWidths[i]; if(i) sumW+=G_SIB; }
    let cursorX = PADDING + (sumW/2); // 供置中估算

    for(let i=0;i<roots.length;i++){
      const r=roots[i];
      if(placedPersons.has(r)) continue;  // ← 新增：已被畫過就不再起一棵樹
      const w=rootWidths[i];
      const cx = cursorX - sumW/2 + w/2;
      drawPersonTree(r, cx, PADDING);
      cursorX += w + G_SIB;
    }

    // 估算畫布大小
    const bboxW = Math.max(sumW + PADDING*2, 900);
    const bboxH = PADDING*2 + 6*(H+G_UNION);
    content={w:Math.ceil(bboxW), h:Math.ceil(bboxH)};
    if(autoFit){ vb={x:0,y:0,w:content.w,h:content.h}; }

    // 繪製 SVG
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    const g=document.createElementNS("http://www.w3.org/2000/svg","g"); svg.appendChild(g);

    // 線
    wires.forEach(w=>{
      const el=document.createElementNS("http://www.w3.org/2000/svg","path");
      el.setAttribute("d", `M ${w.x1} ${w.y1} L ${w.x2} ${w.y2}`);
      el.setAttribute("fill","none");
      el.setAttribute("stroke","var(--line)");
      el.setAttribute("stroke-width","2");
      if(w.dashed) el.setAttribute("stroke-dasharray","6,4");
      g.appendChild(el);
    });

    // 節點
    nodes.forEach(n=>{
      if(n.type==="person"){
        const r=document.createElementNS("http://www.w3.org/2000/svg","rect");
        r.setAttribute("x",n.x); r.setAttribute("y",n.y);
        r.setAttribute("rx",n.rx); r.setAttribute("width",W); r.setAttribute("height",H);
        r.setAttribute("fill", n.sex==="女" ? "var(--nodeWoman)" : "var(--nodeMan)");
        r.setAttribute("stroke","var(--stroke)"); r.setAttribute("stroke-width","2");
        r.classList.add("node"); g.appendChild(r);
        const t=document.createElementNS("http://www.w3.org/2000/svg","text");
        t.setAttribute("x", n.x + W/2); t.setAttribute("y", n.y + H/2 + 5);
        t.setAttribute("text-anchor","middle"); t.setAttribute("fill","var(--text)"); t.setAttribute("font-size", String(FONT));
        t.textContent = n.name; g.appendChild(t);
      }else if(n.type==="hub"){
        const d=document.createElementNS("http://www.w3.org/2000/svg","rect");
        d.setAttribute("x",n.x-3); d.setAttribute("y",n.y-3); d.setAttribute("width",6); d.setAttribute("height",6);
        d.setAttribute("fill","var(--stroke)"); g.appendChild(d);
      }
    });

    host.innerHTML=""; host.appendChild(svg);

    // Pan / Zoom
    const applyVB=()=>svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};
    svg.addEventListener("mousedown",(e)=>{ isPanning=true; panStart={x:e.clientX,y:e.clientY}; vbStart={...vb}; });
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
    document.getElementById("zoomFit").onclick= ()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };
    document.getElementById("btnSVG").onclick = ()=>{
      const out=svg.cloneNode(true);
      out.setAttribute("viewBox", `0 0 ${content.w} ${content.h}`);
      out.setAttribute("width",content.w); out.setAttribute("height",content.h);
      const s=new XMLSerializer().serializeToString(out);
      const blob=new Blob([s], {type:"image/svg+xml;charset=utf-8"});
      const url=URL.createObjectURL(blob); const a=document.createElement("a");
      a.href=url; a.download="family-tree.svg"; a.click(); URL.revokeObjectURL(url);
    };
  }

  // 事件
  document.getElementById("btnDemo").onclick = loadDemo;
  document.getElementById("btnClear").onclick= clearAll;

  document.getElementById("btnAddPerson").onclick = ()=>{
    const name=document.getElementById("namePerson").value.trim();
    const sex =document.getElementById("sexPerson").value;
    if(!name) return;
    const id=uid("P"); doc.persons[id]={id,name,sex,alive:true};
    document.getElementById("namePerson").value=""; render();
  };

  document.getElementById("btnAddUnion").onclick = ()=>{
    const a=document.getElementById("selA").value;
    const b=document.getElementById("selB").value;
    const div=document.getElementById("setDiv").checked;
    if(!a||!b||a===b) return;
    let mid = Object.values(doc.marriages).find(m => (m.a===a && m.b===b) || (m.a===b && m.b===a))?.id;
    if(!mid){ mid=uid("M"); doc.marriages[mid]={id:mid,a,b,divorced:div}; }
    else{ doc.marriages[mid].divorced=div; }
    render();
  };

  document.getElementById("btnAddChild").onclick = ()=>{
    const mid=document.getElementById("selUnion").value;
    const name=document.getElementById("nameChild").value.trim();
    const sex =document.getElementById("sexChild").value;
    if(!mid||!name) return;
    const cid=uid("P"); doc.persons[cid]={id:cid,name,sex,alive:true};
    doc.children.push({mid, child:cid});
    document.getElementById("nameChild").value=""; render();
  };

  // 初始
  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=900, scrolling=True)

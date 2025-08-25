# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Family Tree (QFT-style)", page_icon="🌳", layout="wide")

HTML = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Family Tree</title>
<style>
  :root{
    --bg:#ffffff;
    --line:#0f3c4d;
    --nodeMan:#d8eaff;
    --nodeWoman:#ffdbe1;
    --nodeDead:#e6e6e6;
    --stroke:#164b5f;
    --text:#0b2430;
    --muted:#64748b;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:#f8fafc}
  .toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid #e5e7eb;padding:.75rem 1rem;background:#fff;position:sticky;top:0;z-index:10}
  .btn{background:#075985;color:#fff;border:none;border-radius:.7rem;padding:.5rem .8rem;cursor:pointer}
  .btn.sec{background:#334155}
  .btn.warn{background:#b91c1c}
  .btn.ok{background:#0f766e}
  .btn.muted{background:#6b7280}
  .pane{display:grid;grid-template-columns:2fr 1fr;gap:1rem;padding:1rem}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:1rem;padding:1rem}
  .row{display:flex;gap:.5rem;align-items:center;margin:.35rem 0;flex-wrap:wrap}
  select,input[type=text]{border:1px solid #cbd5e1;border-radius:.6rem;padding:.45rem .6rem}
  .canvas{height:760px;overflow:hidden;border:1px solid #e5e7eb;border-radius:1rem;background:#fff;position:relative}
  .viewport{width:100%;height:100%;overflow:hidden}
  .hint{color:#64748b;font-size:.9rem}
  svg text{user-select:none}
  .node{filter:drop-shadow(0 1px 0.5px rgba(0,0,0,.12))}
  .zoombar{display:flex;gap:.5rem;margin-left:auto}
  .stack{display:flex;gap:.5rem;flex-wrap:wrap}
</style>
</head>
<body>
  <div class="toolbar">
    <strong style="margin-right:.5rem">🌳 家族樹（Quick Family Tree 風格）</strong>
    <button class="btn ok" id="btnDemo">載入示範</button>
    <button class="btn sec" id="btnClear">清空</button>
    <div class="zoombar">
      <button class="btn" id="zoomOut">－</button>
      <button class="btn" id="zoomIn">＋</button>
      <button class="btn" id="zoomFit">置中</button>
      <button class="btn" id="zoom100">100%</button>
      <button class="btn" id="btnSVG">下載 SVG</button>
    </div>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas"><div class="viewport" id="vp"></div></div>
      <div class="hint" style="margin-top:.5rem">提示：滑鼠拖曳可平移、滾輪縮放；右上角有置中與下載 SVG。</div>
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

      <hr style="margin:1rem 0">
      <h3 style="margin:0 0 .5rem">匯入 / 匯出</h3>
      <div class="row">
        <button class="btn sec" id="btnExport">匯出 JSON</button>
        <input type="file" id="fileImport" accept=".json" />
      </div>
      <pre id="exportBox" style="white-space:pre-wrap;background:#f8fafc;border:1px solid #e5e7eb;border-radius:.5rem;padding:.5rem;max-height:160px;overflow:auto;color:#334155"></pre>
    </div>
  </div>

<script>
(function(){
  // ─────────────────────────────────────────
  // 幾何常數（QFT 風格）
  // ─────────────────────────────────────────
  const W = 140, H = 56;                     // 人物框尺寸
  const G_COUPLE = 36;                       // 夫妻水平距
  const G_SIB = 36;                          // 兄弟姊妹間距
  const G_UNION = 72;                        // 父母層與子女層之間距
  const PADDING = 48;                        // 畫布留白
  const BUS_UP = 18;                         // 子女總線距離子女頂的距離
  const BUS_SHORT = 18;                      // 婚點附近短水平段（防交疊）
  const FONT = 14;

  // 狀態
  let doc = { persons:{}, marriages:{}, children:[] }; // persons: {id,name,sex,alive}, marriages:{id,a,b,divorced}
  const uid = p => p + "_" + Math.random().toString(36).slice(2,9);

  // Demo
  function loadDemo(){
    const p={}, id={};
    const addP=(name,sex)=>{ const pid=uid("P"); p[pid]={id:pid,name,sex,alive:true}; id[name]=pid; return pid; };
    addP("陳一郎","男"); addP("陳前妻","女"); addP("陳妻","女");
    addP("陳大","男");   addP("陳大嫂","女");
    addP("陳二","男");   addP("陳二嫂","女");
    addP("陳三","男");   addP("陳三嫂","女");
    addP("王子","男");   addP("王子妻","女");
    addP("王孫","男");   addP("二孩A","女"); addP("二孩B","男"); addP("二孩C","女");
    addP("三孩A","男");  addP("三孩B","女");

    const m={}, addM=(a,b,div=false)=>{ const mid=uid("M"); m[mid]={id:mid,a:id[a],b:id[b],divorced:div}; return mid; };
    const c=[]; const addC=(mid,child)=>c.push({mid,child:id[child]});

    const m1=addM("陳一郎","陳前妻",true);
    const m2=addM("陳一郎","陳妻");
    const m3=addM("王子","王子妻");
    const m4=addM("陳大","陳大嫂");
    const m5=addM("陳二","陳二嫂");
    const m6=addM("陳三","陳三嫂");

    addC(m1,"王子");
    addC(m2,"陳大"); addC(m2,"陳二"); addC(m2,"陳三");
    addC(m3,"王孫");
    addC(m5,"二孩A"); addC(m5,"二孩B"); addC(m5,"二孩C");
    addC(m6,"三孩A"); addC(m6,"三孩B");

    doc = {persons:p, marriages:m, children:c};
    render(true);
  }

  function clearAll(){ doc={persons:{},marriages:{},children:[]}; render(true); }

  // UI 下拉同步
  function syncSelectors(){
    const A=document.getElementById("selA"), B=document.getElementById("selB"), U=document.getElementById("selUnion");
    [A,B,U].forEach(s=>s.innerHTML="");
    Object.values(doc.persons).forEach(p=>{
      const t=(p.sex||"")+(p.alive===false?"（殁）":"");
      for(const s of [A,B]){
        const o=document.createElement("option");
        o.value=p.id; o.textContent=p.name; s.appendChild(o);
      }
    });
    Object.values(doc.marriages).forEach(m=>{
      const o=document.createElement("option");
      const a=doc.persons[m.a]?.name||"?"; const b=doc.persons[m.b]?.name||"?";
      o.value=m.id; o.textContent=`${a} ↔ ${b}${m.divorced?"（離）":""}`;
      U.appendChild(o);
    });
  }

  // ─────────────────────────────────────────
  // 佈局：QFT 風格（無外部函式庫）
  // 思路：
  // 1) 以「人」為核心，找出 root（沒有父母的人）。
  // 2) 對每個人建立 block(width)，若有人有多段婚姻，將其 hub 排同層並左右展開。
  // 3) 婚姻點 hub 下方放 bus（子女總線），子女等距水平、垂直往下。
  // 4) 以 DFS 計算 subtree 寬度，自底向上排版；再輸出 SVG。
  // ─────────────────────────────────────────

  // 關聯表
  function buildMaps(){
    const unionsByPerson={}; const parentsOf={}; const kidsByUnion={};
    Object.values(doc.marriages).forEach(m=>{
      (unionsByPerson[m.a]||(unionsByPerson[m.a]=[])).push(m.id);
      (unionsByPerson[m.b]||(unionsByPerson[m.b]=[])).push(m.id);
    });
    doc.children.forEach(x=>{
      (kidsByUnion[x.mid]||(kidsByUnion[x.mid]=[])).push(x.child);
      const m=doc.marriages[x.mid]; if(!m) return;
      parentsOf[x.child]=[m.a,m.b];
    });
    return {unionsByPerson, parentsOf, kidsByUnion};
  }

  // 找 Root（沒有父母的人）
  function findRoots(parentsOf){
    const roots=[];
    Object.keys(doc.persons).forEach(pid=>{
      if(!parentsOf[pid]) roots.push(pid);
    });
    return roots;
  }

  // 計算子樹寬度
  function measurePerson(pid, maps, memoP={}, memoU={}){
    if(memoP[pid]) return memoP[pid];
    const unions=(maps.unionsByPerson[pid]||[]);
    // 沒婚姻：單人寬
    if(unions.length===0){ return memoP[pid]={w:W, t:"person"}; }
    // 有婚姻：取每段婚姻的區塊寬，整體寬 = max(本人寬, 所有婚姻寬總和 + 間距)
    let widths=[], total=0;
    unions.forEach(mid=>{
      const m=measureUnion(mid, maps, memoP, memoU);
      widths.push(m.w); total += m.w;
    });
    // 夫妻與 hub 佔用寬（最小）
    const minCenter = W + G_COUPLE + W;
    const combined = Math.max(minCenter, total + (unions.length-1)*G_COUPLE);
    return memoP[pid]={w:combined, t:"person", unions:unions};
  }

  function measureUnion(mid, maps, memoP={}, memoU={}){
    if(memoU[mid]) return memoU[mid];
    const kids=(maps.kidsByUnion[mid]||[]);
    if(kids.length===0){ // 沒子女，取夫妻最小寬
      return memoU[mid]={w: W + G_COUPLE + W, t:"union", kids:[]};
    }
    let total=0;
    kids.forEach(cid=>{
      const cw = measurePerson(cid, maps, memoP, memoU).w;
      total += cw;
    });
    total += (kids.length-1)*G_SIB;
    // 最小仍不得小於夫婦最小寬
    total = Math.max(total, W + G_COUPLE + W);
    return memoU[mid]={w: total, t:"union", kids};
  }

  // 排版：回傳所有節點的座標與繪圖指令
  function layout(){
    const maps = buildMaps();
    const roots = findRoots(maps.parentsOf);
    if(roots.length===0) return {nodes:[], edges:[], bbox:{w:800,h:400}};

    const memoP={}, memoU={};
    roots.forEach(r=>measurePerson(r, maps, memoP, memoU));

    // 佈局容器
    const nodes=[]; const wires=[];

    // 繪製人（矩形/橢圓）
    function drawPerson(pid, x, y){
      const p=doc.persons[pid]; if(!p) return;
      const rx = (p.sex==="女")? 26 : 8; // 女用橢圓、男用圓角方
      nodes.push({type:"person", id:pid, name:p.name, sex:p.sex, x, y, rx});
    }

    // 繪製婚姻群組（A hub B；down 為子女總線錨點）
    function drawUnion(mid, cx, topY){
      const m=doc.marriages[mid]; if(!m) return;
      // 配偶位置：以 union 寬來置中
      const uW = measureUnion(mid, maps, memoP, memoU).w;
      // 讓夫妻靠近中心，間隔 G_COUPLE
      const ax = cx - (W + G_COUPLE/2); const bx = cx + (G_COUPLE/2);
      const ay = topY; const by = topY;
      drawPerson(m.a, ax, ay);
      drawPerson(m.b, bx, by);

      // 婚姻點
      const hubX = cx, hubY = ay + H/2;
      nodes.push({type:"hub", id:"hub_"+mid, x:hubX, y:hubY});
      // 夫妻到 hub 的短連線（離婚虛線）
      wires.push({kind:"mate", x1:ax+W, y1:ay+H/2, x2:hubX, y2:hubY, dashed: m.divorced});
      wires.push({kind:"mate", x1:bx,    y1:by+H/2, x2:hubX, y2:hubY, dashed: m.divorced});

      // 子女層
      const kids = (maps.kidsByUnion[mid]||[]);
      if(kids.length===0) return;

      const busY = topY + H + (G_UNION - BUS_UP);
      const childrenY = topY + H + G_UNION;

      // 子女總寬（子女各自子樹寬總和 + 間隔）
      let widths = kids.map(cid => measurePerson(cid, maps, memoP, memoU).w);
      let total = widths.reduce((a,b)=>a+b,0) + (kids.length-1)*G_SIB;
      let start = cx - total/2;

      // 先畫從 hub 垂直到 bus 的線，再在 hub 周圍短水平，避免跨越其他婚姻
      const elbowL = hubX - BUS_SHORT, elbowR = hubX + BUS_SHORT;
      wires.push({kind:"v", x1:hubX, y1:hubY, x2:hubX, y2:busY});
      wires.push({kind:"h", x1:hubX, y1:busY, x2:elbowL, y2:busY});
      wires.push({kind:"h", x1:hubX, y1:busY, x2:elbowR, y2:busY});

      // 依順序畫每個子女的子樹，並從 bus 拉一條垂直下來
      kids.forEach((cid, i)=>{
        const w = widths[i];
        const childCx = start + w/2;
        // bus → child top
        wires.push({kind:"v", x1:childCx, y1:busY, x2:childCx, y2:childrenY});
        // 畫子女（含其子孫）
        drawPersonTree(cid, childCx, childrenY, maps, memoP, memoU);
        start += w + G_SIB;
      });
    }

    // 畫某人的子樹（可能有多段婚姻）
    function drawPersonTree(pid, cx, topY, maps, memoP, memoU){
      const info = measurePerson(pid, maps, memoP, memoU);
      const unions = info.unions || [];
      if(unions.length===0){
        drawPerson(pid, cx - W/2, topY);
        return;
      }
      // 多段婚姻：把所有婚姻 hub 與本人排同層，左右展開
      // 先把所有婚姻的寬加總，中心對齊 cx
      const widths = unions.map(mid=>measureUnion(mid, maps, memoP, memoU).w);
      const totalW = Math.max(info.w, widths.reduce((a,b)=>a+b,0) + (unions.length-1)*G_COUPLE);
      let start = cx - totalW/2;

      // 本人置中到 block 的幾何中心（避免被壓到左或右）
      const selfX = cx - W/2;
      drawPerson(pid, selfX, topY);

      // 依序把每段婚姻置於該人左右（以當前 start 累進）
      unions.forEach((mid, idx)=>{
        const w = widths[idx];
        const midCx = start + w/2;
        drawUnion(mid, midCx, topY);   // 這會再畫配偶、hub、子女群組
        start += w + G_COUPLE;
      });
    }

    // 以每個 root 為入口畫出一個大的家族塊，塊與塊之間保留間距
    const rootsWidth = roots.map(r=>measurePerson(r, maps, memoP, memoU).w);
    const sumW = rootsWidth.reduce((a,b)=>a+b,0) + (roots.length-1)*G_SIB;
    let xStart = PADDING + sumW/2; // 用 viewBox 置中，所以先以中心為基準
    let maxDepth = 0;

    roots.forEach((r,i)=>{
      const w = rootsWidth[i];
      const cx = xStart - sumW/2 + w/2;
      drawPersonTree(r, cx, PADDING, maps, memoP, memoU);
      xStart += w + G_SIB;
      // 粗估高度：3 層 + 子孫
      maxDepth = Math.max(maxDepth, 1);
    });

    // 粗估 bbox：寬用 sumW、 高用 4 代 * (H + G_UNION)
    const bbox = { w: sumW + PADDING*2, h: PADDING*2 + 6*(H + G_UNION) };
    return {nodes, wires, bbox};
  }

  // ─────────────────────────────────────────
  // 繪圖
  // ─────────────────────────────────────────
  let vb = {x:0,y:0,w:1200,h:700};
  let content = {w:1200,h:700};
  let isPanning=false, panStart={x:0,y:0}, vbStart={x:0,y:0};

  function render(autoFit=false){
    syncSelectors();
    const host = document.getElementById("vp");
    host.innerHTML = "<div style='padding:1rem;color:#64748b'>佈局計算中…</div>";

    const {nodes,wires,bbox} = layout();
    content = {w:Math.ceil(bbox.w), h:Math.ceil(bbox.h)};
    if(autoFit) vb = {x:0,y:0,w:content.w,h:content.h};

    const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("width","100%"); svg.setAttribute("height","100%");
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    svg.style.background="#fff";

    // 轉換座標：上方已用絕對值
    const g = document.createElementNS("http://www.w3.org/2000/svg","g");
    svg.appendChild(g);

    // 線（先畫）
    wires.forEach(w=>{
      const el = document.createElementNS("http://www.w3.org/2000/svg","path");
      let d="";
      if(w.kind==="mate"){
        d = `M ${w.x1} ${w.y1} L ${w.x2} ${w.y2}`;
        el.setAttribute("stroke-dasharray", w.dashed ? "6,4" : "");
      }else if(w.kind==="v" || w.kind==="h"){
        d = `M ${w.x1} ${w.y1} L ${w.x2} ${w.y2}`;
      }
      el.setAttribute("d", d);
      el.setAttribute("fill","none");
      el.setAttribute("stroke","var(--line)");
      el.setAttribute("stroke-width","2");
      g.appendChild(el);
    });

    // 節點
    nodes.forEach(n=>{
      if(n.type==="person"){
        const r=document.createElementNS("http://www.w3.org/2000/svg","rect");
        r.setAttribute("x", n.x);
        r.setAttribute("y", n.y);
        r.setAttribute("rx", n.rx);
        r.setAttribute("width", W);
        r.setAttribute("height", H);
        const fill = (n.sex==="女")? "var(--nodeWoman)" : "var(--nodeMan)";
        r.setAttribute("fill", fill);
        r.setAttribute("stroke","var(--stroke)");
        r.setAttribute("stroke-width","2");
        r.classList.add("node");
        g.appendChild(r);

        const t=document.createElementNS("http://www.w3.org/2000/svg","text");
        t.setAttribute("x", n.x + W/2);
        t.setAttribute("y", n.y + H/2 + 5);
        t.setAttribute("text-anchor","middle");
        t.setAttribute("fill","var(--text)");
        t.setAttribute("font-size", String(FONT));
        t.textContent = n.name;
        g.appendChild(t);
      }else if(n.type==="hub"){
        const dot=document.createElementNS("http://www.w3.org/2000/svg","rect");
        dot.setAttribute("x", n.x-3);
        dot.setAttribute("y", n.y-3);
        dot.setAttribute("width", 6); dot.setAttribute("height", 6);
        dot.setAttribute("fill","var(--stroke)");
        g.appendChild(dot);
      }
    });

    host.innerHTML=""; host.appendChild(svg);

    // 互動：pan / zoom
    const applyVB = ()=>svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
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
    document.getElementById("zoom100").onclick= ()=>{ vb={x:0,y:0,w:content.w,h:content.h}; applyVB(); };

    document.getElementById("btnSVG").onclick= ()=>{
      const out = svg.cloneNode(true);
      out.setAttribute("viewBox", `0 0 ${content.w} ${content.h}`);
      out.setAttribute("width", content.w);
      out.setAttribute("height", content.h);
      const s = new XMLSerializer().serializeToString(out);
      const blob = new Blob([s], {type:"image/svg+xml;charset=utf-8"});
      const url = URL.createObjectURL(blob);
      const a=document.createElement("a"); a.href=url; a.download="family-tree.svg"; a.click();
      URL.revokeObjectURL(url);
    };
  }

  // 事件
  document.getElementById("btnDemo").onclick = loadDemo;
  document.getElementById("btnClear").onclick= clearAll;

  document.getElementById("btnAddPerson").onclick = ()=>{
    const name = document.getElementById("namePerson").value.trim();
    const sex  = document.getElementById("sexPerson").value;
    if(!name) return;
    const id = uid("P");
    doc.persons[id]={id,name,sex,alive:true};
    document.getElementById("namePerson").value="";
    render();
  };

  document.getElementById("btnAddUnion").onclick = ()=>{
    const a = document.getElementById("selA").value;
    const b = document.getElementById("selB").value;
    const div = document.getElementById("setDiv").checked;
    if(!a||!b||a===b) return;
    // 若已存在這一對，更新離婚狀態
    let mid = Object.values(doc.marriages).find(m => (m.a===a && m.b===b) || (m.a===b && m.b===a))?.id;
    if(!mid){ mid = uid("M"); doc.marriages[mid]={id:mid,a,b,divorced:div}; }
    else { doc.marriages[mid].divorced = div; }
    render();
  };

  document.getElementById("btnAddChild").onclick = ()=>{
    const mid = document.getElementById("selUnion").value;
    const name = document.getElementById("nameChild").value.trim();
    const sex  = document.getElementById("sexChild").value;
    if(!mid || !name) return;
    const cid = uid("P"); doc.persons[cid]={id:cid,name,sex,alive:true};
    doc.children.push({mid, child:cid});
    document.getElementById("nameChild").value="";
    render();
  };

  document.getElementById("btnExport").onclick = ()=>{
    const s = JSON.stringify(doc, null, 2);
    document.getElementById("exportBox").textContent = s;
  };
  document.getElementById("fileImport").addEventListener("change", (e)=>{
    const f = e.target.files[0]; if(!f) return;
    const r = new FileReader();
    r.onload = ()=>{ try{ doc=JSON.parse(r.result); render(true); }catch(err){ alert("JSON 解析失敗"); } };
    r.readAsText(f, "utf-8");
  });

  // 初始
  render(true);
})();
</script>
</body>
</html>
"""

components.html(HTML, height=900, scrolling=True)

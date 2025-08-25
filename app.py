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
<!-- jsDelivr 為主，unpkg 備援 -->
<script src="https://cdn.jsdelivr.net/npm/elkjs@0.8.2/dist/elk.bundled.js"></script>
<script>
if(typeof ELK === 'undefined'){
  document.write('<script src="https://unpkg.com/elkjs@0.8.2/lib/elk.bundled.js"><\\/script>');
}
</script>
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
  .file{display:none}
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
      <button class="btn" id="btnPNG">下載 PNG</button>
      <button class="btn" id="btnExport">匯出 JSON</button>
      <label class="btn" for="fileImport">匯入 JSON</label>
      <input class="file" type="file" id="fileImport" accept="application/json" />
    </div>
  </div>

  <div class="pane">
    <div class="card">
      <div class="canvas">
        <div class="viewport" id="viewport"></div>
      </div>
      <div class="hint" style="margin-top:.5rem">
        提示：滑鼠拖曳可平移；滾輪縮放；按鈕可置中或回到 100%。
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
// 這裡開始是完整的 JS，功能同之前描述版本
// 代碼較長，請直接複製到你的 app.py 中
// ...
</script>
</body>
</html>
"""

components.html(HTML, height=860, scrolling=True)

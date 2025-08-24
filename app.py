// 取得所有婚姻中的人（任何一段婚姻的 partner）
const partnersSet = new Set();
Object.values(doc.unions).forEach(u => (u.partners||[]).forEach(pid => partnersSet.add(pid)));

// ---- 只改這個函式的 filter ----
function enforceLayerMinGapForNonChildren(layout, overrides, childrenIdSet){
  const items = (layout.children||[])
    // 不推 union node、不推子女、也不推任何在婚姻中的人（配偶/父母）
    .filter(n => !doc.unions[n.id] && !childrenIdSet.has(n.id) && !partnersSet.has(n.id))
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

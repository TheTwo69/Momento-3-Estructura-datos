// avl_visualizer.js — VERSIÓN DIAGNÓSTICO + RENDER ROBUSTO
'use strict';

const AVL_C = {
  bg:'#0a0f1a', surface:'#0e1520', border:'#1a2a40',
  root:'#00d4ff', left:'#4a90e2', leftLeaf:'#00b4ff',
  right:'#a855f7', rightLeaf:'#c084fc', leaf:'#00e87a',
  internal:'#94b8d4', muted:'#4a6a8a', text:'#e2e8f0',
  feOk:'#22d3ee', feWarn:'#f59e0b', feBad:'#ef4444',
};

const avlState = {
  scale:1, tx:0, ty:0,
  dragging:false, lastMx:0, lastMy:0,
  selectedId:null, nodes:[], _bound:false,
};

// ── helpers ──────────────────────────────────────────────────────────────
function feColor(fe){ return Math.abs(fe)>=2?AVL_C.feBad:Math.abs(fe)===1?AVL_C.feWarn:AVL_C.feOk; }
function feBg(fe){   return Math.abs(fe)>=2?'rgba(239,68,68,.18)':Math.abs(fe)===1?'rgba(245,158,11,.18)':'rgba(34,211,238,.12)'; }

function nodeColor(n){
  if(n.padre===null||n.padre===undefined) return AVL_C.root;
  const leaf=!avlState.nodes.some(c=>c.padre===n.id);
  if(n._side==='left')  return leaf?AVL_C.leftLeaf:AVL_C.left;
  if(n._side==='right') return leaf?AVL_C.rightLeaf:AVL_C.right;
  return leaf?AVL_C.leaf:AVL_C.internal;
}

function annotateSides(){
  const ns=avlState.nodes;
  ns.forEach(n=>{n._side=null;});
  const root=ns.find(n=>n.padre===null||n.padre===undefined);
  if(!root)return;
  function mark(id,side){ const n=ns.find(x=>x.id===id); if(n)n._side=side; ns.filter(c=>c.padre===id).forEach(c=>mark(c.id,side)); }
  ns.filter(c=>c.padre===root.id).forEach(c=>mark(c.id, c.pos%2===0?'left':'right'));
}

function computeLayout(){
  const ns=avlState.nodes;
  if(!ns.length)return{positions:{},W:600,H:200};
  const byLvl={};let maxLvl=0;
  ns.forEach(n=>{(byLvl[n.nivel]||(byLvl[n.nivel]=[])).push(n);if(n.nivel>maxLvl)maxLvl=n.nivel;});
  const maxCount=Math.max(...Object.values(byLvl).map(l=>l.length));
  const W=Math.max(640,maxCount*110+80), H=(maxLvl+1)*110+80;
  const pos={};
  Object.entries(byLvl).forEach(([lvl,list])=>{
    list.forEach((n,i)=>{pos[n.id]={x:W*(i+1)/(list.length+1),y:parseInt(lvl)*110+60};});
  });
  return{positions:pos,W,H};
}

function mk(tag,attrs={}){
  const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
  return el;
}
function mkt(txt,attrs={}){ const el=mk('text',attrs); el.textContent=txt; return el; }

// ── render ────────────────────────────────────────────────────────────────
function avlRender(){
  const cont=document.getElementById('avl-svg-container');
  if(!cont){console.error('[AVL] contenedor no existe');return;}
  cont.innerHTML='';

  const ns=avlState.nodes;
  if(!ns.length){
    cont.innerHTML=`<svg width="100%" height="120" xmlns="http://www.w3.org/2000/svg">
      <text x="50%" y="60" text-anchor="middle" fill="${AVL_C.muted}" font-family="monospace" font-size="13">
        Árbol vacío — inserta el primer producto</text></svg>`;
    return;
  }

  annotateSides();
  const {positions:pos,W,H}=computeLayout();

  /* SVG con viewBox dinámico para que SIEMPRE sea visible */
  const svg=mk('svg',{
    width:'100%', height:H,
    viewBox:`0 0 ${W} ${H}`,
    preserveAspectRatio:'xMidYMid meet',
    xmlns:'http://www.w3.org/2000/svg',
    style:'display:block;cursor:grab;user-select:none',
  });

  svg.innerHTML+=`<defs>
    <filter id="gr" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="gn" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>`;

  const g=mk('g',{id:'avl-g'}); svg.appendChild(g);
  const root=ns.find(n=>n.padre===null||n.padre===undefined);

  // zonas subárbol
  ['left','right'].forEach(side=>{
    const ids=ns.filter(n=>n._side===side).map(n=>n.id);
    if(!ids.length)return;
    const color=side==='left'?AVL_C.left:AVL_C.right;
    const xs=ids.map(id=>pos[id]?.x).filter(v=>v!=null);
    const ys=ids.map(id=>pos[id]?.y).filter(v=>v!=null);
    if(!xs.length)return;
    const pad=42,xm=Math.min(...xs),ym=Math.min(...ys);
    g.appendChild(mk('rect',{x:xm-pad,y:ym-pad,width:Math.max(...xs)-xm+pad*2,height:Math.max(...ys)-ym+pad*2,
      rx:14,fill:color,'fill-opacity':'0.04',stroke:color,'stroke-width':'0.6','stroke-dasharray':'7 5',opacity:'0.5'}));
    g.appendChild(mkt(side==='left'?'LEFT SUBTREE':'RIGHT SUBTREE',
      {x:xm-pad+8,y:ym-pad-5,fill:color,'font-size':'9','font-family':'monospace','letter-spacing':'0.12em',opacity:'0.7'}));
  });

  // aristas
  ns.forEach(n=>{
    if(n.padre===null||n.padre===undefined)return;
    const p1=pos[n.id],p2=pos[n.padre];
    if(!p1||!p2)return;
    const col=nodeColor(n),isDir=n.padre===root?.id,r1=isDir?28:24;
    const my=(p1.y+p2.y)/2;
    g.appendChild(mk('path',{d:`M${p2.x},${p2.y+r1} C${p2.x},${my} ${p1.x},${my} ${p1.x},${p1.y-24}`,
      fill:'none',stroke:col,'stroke-width':isDir?'1.5':'1',opacity:'0.45'}));
  });

  // nodos
  ns.forEach(n=>{
    const p=pos[n.id]; if(!p)return;
    const isRoot=n.padre===null||n.padre===undefined;
    const isLeaf=!ns.some(c=>c.padre===n.id);
    const col=nodeColor(n),fe=n.fe,r=isRoot?28:isLeaf?21:24;
    const isSel=n.id===avlState.selectedId;
    const ng=mk('g',{style:'cursor:pointer'}); ng.dataset.nodeId=String(n.id);

    if(isRoot){
      ng.appendChild(mk('circle',{cx:p.x,cy:p.y,r:r+14,fill:col,opacity:'0.07'}));
      ng.appendChild(mk('circle',{cx:p.x,cy:p.y,r:r+6,fill:'none',stroke:col,'stroke-width':'1',opacity:'0.25'}));
    }
    if(isSel) ng.appendChild(mk('circle',{cx:p.x,cy:p.y,r:r+8,fill:'none',stroke:col,'stroke-width':'1.5','stroke-dasharray':'5 3',opacity:'0.85'}));

    const circ=mk('circle',{cx:p.x,cy:p.y,r,fill:AVL_C.surface,stroke:col,'stroke-width':isRoot?'2.2':'1.5',filter:isRoot?'url(#gr)':'url(#gn)'});
    ng.appendChild(circ);
    ng.appendChild(mkt(String(n.id),{x:p.x,y:isLeaf?p.y-4:p.y-7,'text-anchor':'middle','dominant-baseline':'central',
      fill:col,'font-size':isRoot?'14':'11','font-weight':'bold','font-family':'monospace'}));
    if(!isLeaf&&n.nombre) ng.appendChild(mkt((n.nombre||'').slice(0,7).toUpperCase(),
      {x:p.x,y:p.y+7,'text-anchor':'middle','dominant-baseline':'central',fill:AVL_C.muted,'font-size':'7.5','font-family':'monospace'}));
    if(isLeaf) ng.appendChild(mkt('◆',{x:p.x,y:p.y+8,'text-anchor':'middle','dominant-baseline':'central',fill:col,'font-size':'7','font-family':'monospace'}));

    // badge FE
    const fs=`FE:${fe>0?'+':''}${fe}`,fw=fs.length*5.8+8,fx=p.x+r-2,fy=p.y-r-16;
    ng.appendChild(mk('rect',{x:fx,y:fy,width:fw,height:14,rx:7,fill:feBg(fe),stroke:feColor(fe),'stroke-width':'0.5'}));
    ng.appendChild(mkt(fs,{x:fx+fw/2,y:fy+7,'text-anchor':'middle','dominant-baseline':'central',fill:feColor(fe),'font-size':'7.5','font-family':'monospace'}));

    ng.addEventListener('mouseenter',()=>{circ.setAttribute('fill','rgba(255,255,255,.06)');circ.setAttribute('stroke-width',isRoot?'3':'2.2');});
    ng.addEventListener('mouseleave',()=>{circ.setAttribute('fill',AVL_C.surface);circ.setAttribute('stroke-width',isRoot?'2.2':'1.5');});
    ng.addEventListener('click',()=>avlSelect(n.id));
    g.appendChild(ng);
  });

  cont.appendChild(svg);
  avlApplyT();

  if(!avlState._bound){
    avlState._bound=true;
    window.addEventListener('mouseup',()=>{avlState.dragging=false;});
    window.addEventListener('mousemove',e=>{
      if(!avlState.dragging)return;
      avlState.tx+=e.clientX-avlState.lastMx; avlState.ty+=e.clientY-avlState.lastMy;
      avlState.lastMx=e.clientX; avlState.lastMy=e.clientY; avlApplyT();
    });
  }
  svg.addEventListener('mousedown',e=>{
    if(e.target.closest('[data-node-id]'))return;
    avlState.dragging=true; avlState.lastMx=e.clientX; avlState.lastMy=e.clientY;
  });
  svg.addEventListener('wheel',e=>{e.preventDefault();avlZoom(e.deltaY<0?.1:-.1);},{passive:false});
}

// ── inspector ─────────────────────────────────────────────────────────────
function avlSelect(id){
  avlState.selectedId=id; avlRender();
  const n=avlState.nodes.find(x=>x.id===id); if(!n)return;
  const panel=document.getElementById('avl-node-info'); if(!panel)return;
  const isRoot=n.padre===null||n.padre===undefined;
  const isLeaf=!avlState.nodes.some(c=>c.padre===id);
  const col=nodeColor(n),fe=n.fe;
  const type=isRoot?'Raíz':isLeaf?'Hoja':n._side==='left'?'Interno izquierdo':n._side==='right'?'Interno derecho':'Interno';
  const kids=avlState.nodes.filter(c=>c.padre===id);
  const ks=kids.length?kids.map(c=>`<span style="color:${nodeColor(c)}">${c.id}</span>`).join(', '):`<span style="color:${AVL_C.muted}">ninguno</span>`;
  const row=(l,v)=>`<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid ${AVL_C.border};padding:5px 0;font-size:11px"><span style="color:${AVL_C.muted};text-transform:uppercase;letter-spacing:.06em;font-size:10px">${l}</span><span style="font-weight:500">${v}</span></div>`;
  panel.innerHTML=`<div style="border-left:3px solid ${col};padding-left:10px;margin-bottom:12px">
    <div style="font-size:26px;font-weight:bold;color:${col};line-height:1">${n.id}</div>
    <div style="font-size:11px;color:${AVL_C.muted};margin-top:2px">${n.nombre||''}</div></div>
    ${row('Tipo',`<span style="color:${col}">${type}</span>`)}
    ${row('Nivel',n.nivel)}
    ${row('FE',`<span style="background:${feBg(fe)};color:${feColor(fe)};padding:1px 8px;border-radius:20px;font-size:11px">${fe>0?'+':''}${fe}</span>`)}
    ${row('Hijos',ks)}
    <div style="margin-top:10px;font-size:10px;color:${AVL_C.muted}">
      ${isLeaf?'Nodo hoja — sin descendientes.':''}
      ${Math.abs(fe)>=2?`<span style="color:${AVL_C.feBad}">⚠ Desbalanceado</span>`:''}</div>`;
}

// ── zoom / pan ────────────────────────────────────────────────────────────
function avlApplyT(){
  const g=document.getElementById('avl-g');
  if(g)g.setAttribute('transform',`translate(${avlState.tx},${avlState.ty}) scale(${avlState.scale})`);
  const l=document.getElementById('avl-zoom-lbl');
  if(l)l.textContent=Math.round(avlState.scale*100)+'%';
}
function avlZoom(d){ avlState.scale=Math.max(.25,Math.min(3,avlState.scale+d)); avlApplyT(); }
function avlResetView(){ avlState.scale=1;avlState.tx=0;avlState.ty=0;avlApplyT(); }

// ── fetch + render ────────────────────────────────────────────────────────
function avlFetch(){
  const cont=document.getElementById('avl-svg-container');
  if(cont) cont.innerHTML=`<div style="color:${AVL_C.muted};font-family:monospace;font-size:12px;padding:20px;text-align:center">Cargando…</div>`;
  fetch('/api/inventario/arbol')
    .then(r=>{ if(!r.ok)throw new Error('HTTP '+r.status); return r.json(); })
    .then(data=>{
      console.log('[AVL] nodos recibidos:', data.nodos?.length, data.nodos);
      avlState.nodes=data.nodos||[];
      avlState.selectedId=null;
      const p=document.getElementById('avl-node-info');
      if(p)p.innerHTML=`<span style="color:${AVL_C.muted};font-size:11px">Haz clic en un nodo para inspeccionarlo.</span>`;
      avlResetView();
      avlRender();
    })
    .catch(err=>{
      console.error('[AVL]',err);
      if(cont)cont.innerHTML=`<div style="color:${AVL_C.feBad};font-family:monospace;font-size:13px;padding:24px;text-align:center">
        ⚠ Error al cargar árbol AVL<br><small style="color:${AVL_C.muted}">${err.message}</small><br><br>
        <button onclick="avlFetch()" style="background:transparent;border:1px solid ${AVL_C.feBad};color:${AVL_C.feBad};padding:6px 16px;cursor:pointer;font-family:monospace;border-radius:4px">Reintentar</button></div>`;
    });
}

// ── actualizarPantallaInventario (override de map.js) ─────────────────────
function actualizarPantallaInventario(){
  fetch('/api/inventario/lista')
    .then(r=>r.json())
    .then(data=>{
      const t=document.getElementById('tabla-productos'); if(!t)return;
      t.innerHTML='<tr><th>ID</th><th>Nombre</th><th>Stock</th><th>Peso (Kg)</th></tr>';
      (data.productos||[]).forEach(p=>{
        const c=p.stock<5?AVL_C.feBad:p.stock<15?AVL_C.feWarn:AVL_C.feOk;
        t.innerHTML+=`<tr><td>${p.id}</td><td>${p.nombre}</td><td><span style="color:${c};font-weight:bold">${p.stock}</span> uds</td><td>${p.peso}</td></tr>`;
      });
    })
    .catch(e=>console.error('[AVL] lista:',e));

  // delay para que el contenedor tenga dimensiones reales
  setTimeout(avlFetch, 120);
}

// override del form de inserción
window.agregarInventario=function(e){
  e.preventDefault();
  fetch('/api/inventario',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      id:document.getElementById('inv-id').value,
      nombre:document.getElementById('inv-nom').value,
      tipo:document.getElementById('inv-tipo').value,
      stock:document.getElementById('inv-stock').value,
      peso:document.getElementById('inv-peso').value,
    }),
  }).then(()=>{ document.getElementById('form-inventario')?.reset(); actualizarPantallaInventario(); })
    .catch(e=>console.error('[AVL] insertar:',e));
};

window.avlZoom=avlZoom;
window.avlResetView=avlResetView;

// auto-init si la ventana ya está activa
document.addEventListener('DOMContentLoaded',()=>{
  if(document.getElementById('ventana-inventario')?.classList.contains('active-ventana'))
    actualizarPantallaInventario();
});
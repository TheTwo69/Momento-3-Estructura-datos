// ============================================================
// avl_visualizer.js  —  LogiDrone-UCC  AVL Visualizer
// Reemplaza la función actualizarPantallaInventario() que
// dibujaba el árbol como texto <pre> en el index.html original.
//
// USO:
//   1. Incluir este archivo DESPUÉS de map.js en index.html
//   2. El archivo index.html ya llama actualizarPantallaInventario()
//      en cambiarVentana('inventario') — esta versión la sobreescribe.
//   3. El contenedor #avl-visualizer debe existir en el HTML
//      (ver plantilla avl_panel.html o el parche en index.html).
// ============================================================

'use strict';

// ── Paleta táctica (igual que el resto de la app) ─────────────────────────
const AVL_C = {
  bg:        '#0a0f1a',
  surface:   '#0e1520',
  border:    '#1a2a40',
  root:      '#00d4ff',
  left:      '#4a90e2',
  leftLeaf:  '#00b4ff',
  right:     '#a855f7',
  rightLeaf: '#c084fc',
  leaf:      '#00e87a',
  internal:  '#94b8d4',
  muted:     '#4a6a8a',
  text:      '#e2e8f0',
  feOk:      '#22d3ee',
  feWarn:    '#f59e0b',
  feBad:     '#ef4444',
};

// ── Estado del visualizador ───────────────────────────────────────────────
const avlState = {
  scale:      1,
  tx:         0,
  ty:         0,
  dragging:   false,
  lastMx:     0,
  lastMy:     0,
  selectedId: null,
  nodes:      [],      // último snapshot de /api/inventario/arbol
};

// ── Helpers de color ──────────────────────────────────────────────────────
function avlFeColor(fe) {
  if (Math.abs(fe) >= 2) return AVL_C.feBad;
  if (Math.abs(fe) === 1) return AVL_C.feWarn;
  return AVL_C.feOk;
}
function avlFeBg(fe) {
  if (Math.abs(fe) >= 2) return 'rgba(239,68,68,0.18)';
  if (Math.abs(fe) === 1) return 'rgba(245,158,11,0.18)';
  return 'rgba(34,211,238,0.12)';
}
function avlNodeColor(node) {
  if (node.padre === null) return AVL_C.root;
  const leaf = !avlHasChildren(node);
  if (node._side === 'left')  return leaf ? AVL_C.leftLeaf  : AVL_C.left;
  if (node._side === 'right') return leaf ? AVL_C.rightLeaf : AVL_C.right;
  return leaf ? AVL_C.leaf : AVL_C.internal;
}
function avlHasChildren(node) {
  // Revisamos en el array global si algún nodo tiene a este como padre
  return avlState.nodes.some(n => n.padre === node.id);
}

// ── Layout: calcula posición x,y de cada nodo ────────────────────────────
function avlLayout(nodes) {
  if (!nodes.length) return {};

  // Agrupar por nivel
  const byLevel = {};
  let maxLevel = 0;
  nodes.forEach(n => {
    if (!byLevel[n.nivel]) byLevel[n.nivel] = [];
    byLevel[n.nivel].push(n);
    if (n.nivel > maxLevel) maxLevel = n.nivel;
  });

  const leafCount = Math.pow(2, maxLevel);
  const W = Math.max(700, leafCount * 88 + 60);
  const H = (maxLevel + 1) * 100 + 80;

  const positions = {};
  Object.entries(byLevel).forEach(([lvl, list]) => {
    const count = list.length;
    list.forEach((n, i) => {
      positions[n.id] = {
        x: W * (i + 1) / (count + 1),
        y: parseInt(lvl) * 100 + 55,
      };
    });
  });

  // Anotar qué lado del árbol ocupa cada nodo
  const root = nodes.find(n => n.padre === null);
  if (root) {
    const rootChildren = nodes.filter(n => n.padre === root.id);
    const rootX = positions[root.id]?.x || W / 2;
    rootChildren.forEach(child => {
      const side = positions[child.id]?.x < rootX ? 'left' : 'right';
      propagateSide(child.id, side, nodes, positions, rootX);
    });
  }

  return { positions, W, H };
}

function propagateSide(id, side, nodes, positions, rootX) {
  const node = nodes.find(n => n.id === id);
  if (!node) return;
  node._side = side;
  nodes.filter(n => n.padre === id).forEach(child => {
    propagateSide(child.id, side, nodes, positions, rootX);
  });
}

// ── SVG helpers ───────────────────────────────────────────────────────────
function svgEl(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}
function svgText(content, attrs = {}) {
  const el = svgEl('text', attrs);
  el.textContent = content;
  return el;
}

// ── Dibuja el árbol en el SVG ─────────────────────────────────────────────
function avlRender() {
  const container = document.getElementById('avl-svg-container');
  if (!container) return;

  const nodes = avlState.nodes;
  container.innerHTML = '';

  if (!nodes.length) {
    container.innerHTML = `<svg width="100%" height="120" xmlns="http://www.w3.org/2000/svg">
      <text x="50%" y="60" text-anchor="middle" fill="${AVL_C.muted}"
            font-family="monospace" font-size="13">Árbol vacío — inserta productos</text></svg>`;
    return;
  }

  const { positions, W, H } = avlLayout(nodes);

  const svg = svgEl('svg', {
    width: '100%', viewBox: `0 0 ${W} ${H}`,
    xmlns: 'http://www.w3.org/2000/svg',
    style: 'display:block;cursor:grab;user-select:none',
  });

  // Defs (filtros glow)
  const defs = svgEl('defs');
  defs.innerHTML = `
    <filter id="avl-glow-root" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="avl-glow-node" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>`;
  svg.appendChild(defs);

  const group = svgEl('g', { id: 'avl-g' });
  svg.appendChild(group);

  // Identificar lado raíz → children
  const root = nodes.find(n => n.padre === null);
  const leftIds  = new Set();
  const rightIds = new Set();
  if (root) {
    nodes.forEach(n => {
      if (n._side === 'left')  leftIds.add(n.id);
      if (n._side === 'right') rightIds.add(n.id);
    });
  }

  // Rectángulos de subárbol sombreados
  if (root && leftIds.size && rightIds.size) {
    ['left', 'right'].forEach(side => {
      const ids = side === 'left' ? leftIds : rightIds;
      const color = side === 'left' ? AVL_C.left : AVL_C.right;
      const xs = [...ids].map(id => positions[id]?.x).filter(Boolean);
      const ys = [...ids].map(id => positions[id]?.y).filter(Boolean);
      const xMin = Math.min(...xs) - 40, xMax = Math.max(...xs) + 40;
      const yMin = Math.min(...ys) - 38, yMax = Math.max(...ys) + 38;
      const rect = svgEl('rect', {
        x: xMin, y: yMin, width: xMax - xMin, height: yMax - yMin,
        rx: 16, fill: color, 'fill-opacity': '0.04',
        stroke: color, 'stroke-width': '0.6',
        'stroke-dasharray': '7 5', opacity: '0.55',
      });
      group.appendChild(rect);
      const lbl = svgText(side === 'left' ? 'LEFT SUBTREE' : 'RIGHT SUBTREE', {
        x: xMin + 10, y: yMin - 6,
        fill: color, 'font-size': '9',
        'font-family': 'monospace',
        'letter-spacing': '0.12em', opacity: '0.7',
      });
      group.appendChild(lbl);
    });
  }

  // Aristas (curvas cúbicas de Bézier)
  nodes.forEach(node => {
    if (node.padre === null) return;
    const p1 = positions[node.id];
    const p2 = positions[node.padre];
    if (!p1 || !p2) return;
    const color = avlNodeColor(node);
    const midY = (p1.y + p2.y) / 2;
    const path = svgEl('path', {
      d: `M${p2.x},${p2.y+26} C${p2.x},${midY} ${p1.x},${midY} ${p1.x},${p1.y-26}`,
      fill: 'none', stroke: color,
      'stroke-width': node.padre === root?.id ? '1.5' : '1',
      opacity: '0.45',
    });
    group.appendChild(path);
  });

  // Nodos
  nodes.forEach(node => {
    const pos = positions[node.id];
    if (!pos) return;

    const isRoot  = node.padre === null;
    const isLeaf  = !avlHasChildren(node);
    const color   = avlNodeColor(node);
    const fe      = node.fe;
    const r       = isRoot ? 28 : isLeaf ? 21 : 24;
    const isSelected = node.id === avlState.selectedId;

    const g = svgEl('g', { style: 'cursor:pointer' });
    g.dataset.nodeId = node.id;

    // Halo de raíz
    if (isRoot) {
      g.appendChild(svgEl('circle', {
        cx: pos.x, cy: pos.y, r: r + 14,
        fill: color, opacity: '0.06',
      }));
      g.appendChild(svgEl('circle', {
        cx: pos.x, cy: pos.y, r: r + 6,
        fill: 'none', stroke: color, 'stroke-width': '1', opacity: '0.22',
      }));
    }

    // Anillo de selección
    if (isSelected) {
      g.appendChild(svgEl('circle', {
        cx: pos.x, cy: pos.y, r: r + 8,
        fill: 'none', stroke: color,
        'stroke-width': '1.5', 'stroke-dasharray': '5 3', opacity: '0.75',
      }));
    }

    // Cuerpo
    const circle = svgEl('circle', {
      cx: pos.x, cy: pos.y, r,
      fill: AVL_C.surface, stroke: color,
      'stroke-width': isRoot ? '2.2' : '1.5',
      filter: isRoot ? 'url(#avl-glow-root)' : 'url(#avl-glow-node)',
    });
    g.appendChild(circle);

    // ID
    g.appendChild(svgText(node.id, {
      x: pos.x, y: isLeaf ? pos.y - 4 : pos.y - 7,
      'text-anchor': 'middle', 'dominant-baseline': 'central',
      fill: color,
      'font-size': isRoot ? '14' : '12',
      'font-weight': '500',
      'font-family': 'monospace',
    }));

    // Nombre corto (solo nodos internos)
    if (!isLeaf) {
      g.appendChild(svgText(node.nombre.slice(0, 7).toUpperCase(), {
        x: pos.x, y: pos.y + 7,
        'text-anchor': 'middle', 'dominant-baseline': 'central',
        fill: AVL_C.muted, 'font-size': '7.5', 'font-family': 'monospace',
      }));
    }

    // Icono hoja
    if (isLeaf) {
      g.appendChild(svgText('◆', {
        x: pos.x, y: pos.y + 7,
        'text-anchor': 'middle', 'dominant-baseline': 'central',
        fill: color, 'font-size': '7', opacity: '0.7', 'font-family': 'monospace',
      }));
    }

    // Badge FE
    const feStr = `FE:${fe > 0 ? '+' : ''}${fe}`;
    const feW   = feStr.length * 5.8 + 8;
    const feX   = pos.x + r - 2;
    const feY   = pos.y - r - 15;
    g.appendChild(svgEl('rect', {
      x: feX, y: feY, width: feW, height: 14, rx: 7,
      fill: avlFeBg(fe), stroke: avlFeColor(fe), 'stroke-width': '0.5',
    }));
    g.appendChild(svgText(feStr, {
      x: feX + feW / 2, y: feY + 7,
      'text-anchor': 'middle', 'dominant-baseline': 'central',
      fill: avlFeColor(fe), 'font-size': '7.5', 'font-family': 'monospace',
    }));

    // Hover
    g.addEventListener('mouseenter', () => {
      circle.setAttribute('fill', 'rgba(255,255,255,0.05)');
      circle.setAttribute('stroke-width', isRoot ? '3' : '2.5');
    });
    g.addEventListener('mouseleave', () => {
      circle.setAttribute('fill', AVL_C.surface);
      circle.setAttribute('stroke-width', isRoot ? '2.2' : '1.5');
    });
    g.addEventListener('click', () => avlSelectNode(node.id));

    group.appendChild(g);
  });

  container.appendChild(svg);
  avlApplyTransform();
  avlBindDrag(svg, group);
}

// ── Panel de información del nodo seleccionado ────────────────────────────
function avlSelectNode(id) {
  avlState.selectedId = id;
  avlRender();

  const node = avlState.nodes.find(n => n.id === id);
  if (!node) return;

  const panel = document.getElementById('avl-node-info');
  if (!panel) return;

  const isRoot = node.padre === null;
  const isLeaf = !avlHasChildren(node);
  const color  = avlNodeColor(node);
  const fe     = node.fe;

  let typeLabel;
  if (isRoot)             typeLabel = 'Raíz';
  else if (isLeaf)        typeLabel = 'Hoja';
  else if (node._side === 'left')  typeLabel = 'Interno izquierdo';
  else if (node._side === 'right') typeLabel = 'Interno derecho';
  else                    typeLabel = 'Interno';

  const children = avlState.nodes.filter(n => n.padre === id);
  const childStr = children.length
    ? children.map(c => `<span style="color:${avlNodeColor(c)}">${c.id}</span>`).join(', ')
    : '<span style="color:' + AVL_C.muted + '">ninguno</span>';

  panel.innerHTML = `
    <div style="border-left:3px solid ${color};padding-left:10px;margin-bottom:12px">
      <div style="font-size:26px;font-weight:500;color:${color};line-height:1">${node.id}</div>
      <div style="font-size:11px;color:${AVL_C.muted};margin-top:2px">${node.nombre}</div>
    </div>
    ${avlInfoRow('Tipo',     `<span style="color:${color}">${typeLabel}</span>`)}
    ${avlInfoRow('Nivel',    node.nivel)}
    ${avlInfoRow('Factor&nbsp;FE',
      `<span style="background:${avlFeBg(fe)};color:${avlFeColor(fe)};
        padding:1px 8px;border-radius:20px;font-size:11px">${fe > 0 ? '+' : ''}${fe}</span>`)}
    ${avlInfoRow('Hijos', childStr)}
    <div style="margin-top:10px;font-size:10px;color:${AVL_C.muted};line-height:1.6">
      ${isLeaf ? 'Nodo hoja — sin descendientes.' : ''}
      ${Math.abs(fe) >= 2 ? '<span style="color:' + AVL_C.feBad + '">⚠ Desbalanceado</span>' : ''}
    </div>`;
}

function avlInfoRow(label, value) {
  return `<div style="display:flex;justify-content:space-between;align-items:center;
    border-bottom:1px solid ${AVL_C.border};padding:5px 0;font-size:11px">
    <span style="color:${AVL_C.muted};text-transform:uppercase;letter-spacing:.06em;font-size:10px">${label}</span>
    <span style="font-weight:500">${value}</span>
  </div>`;
}

// ── Pan y zoom ────────────────────────────────────────────────────────────
function avlApplyTransform() {
  const g = document.getElementById('avl-g');
  if (g) g.setAttribute('transform',
    `translate(${avlState.tx},${avlState.ty}) scale(${avlState.scale})`);
  const lbl = document.getElementById('avl-zoom-lbl');
  if (lbl) lbl.textContent = Math.round(avlState.scale * 100) + '%';
}

function avlZoom(delta) {
  avlState.scale = Math.max(0.25, Math.min(3, avlState.scale + delta));
  avlApplyTransform();
}

function avlResetView() {
  avlState.scale = 1; avlState.tx = 0; avlState.ty = 0;
  avlApplyTransform();
}

function avlBindDrag(svg, group) {
  svg.addEventListener('mousedown', e => {
    if (e.target.closest('[data-node-id]')) return;
    avlState.dragging = true;
    avlState.lastMx = e.clientX;
    avlState.lastMy = e.clientY;
    svg.style.cursor = 'grabbing';
  });
  window.addEventListener('mouseup', () => {
    avlState.dragging = false;
    if (svg) svg.style.cursor = 'grab';
  });
  window.addEventListener('mousemove', e => {
    if (!avlState.dragging) return;
    avlState.tx += e.clientX - avlState.lastMx;
    avlState.ty += e.clientY - avlState.lastMy;
    avlState.lastMx = e.clientX;
    avlState.lastMy = e.clientY;
    avlApplyTransform();
  });
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    avlZoom(e.deltaY < 0 ? 0.1 : -0.1);
  }, { passive: false });
}

// ── Fetch y actualización ─────────────────────────────────────────────────

/**
 * actualizarPantallaInventario()
 * Sobreescribe la función original de map.js.
 * Llama a los dos endpoints y refresca tabla + árbol visual.
 */
function actualizarPantallaInventario() {
  // Tabla de productos (igual que antes)
  fetch('/api/inventario/lista').then(r => r.json()).then(data => {
    const tabla = document.getElementById('tabla-productos');
    if (!tabla) return;
    tabla.innerHTML = `<tr>
      <th>ID</th><th>Nombre</th><th>Stock</th><th>Peso (Kg)</th>
    </tr>`;
    data.productos.forEach(p => {
      const stockColor = p.stock < 5 ? AVL_C.feBad : p.stock < 15 ? AVL_C.feWarn : AVL_C.feOk;
      tabla.innerHTML += `<tr>
        <td>${p.id}</td>
        <td>${p.nombre}</td>
        <td><span style="color:${stockColor};font-weight:bold">${p.stock}</span> uds</td>
        <td>${p.peso}</td>
      </tr>`;
    });
  });

  // Árbol AVL visual
  fetch('/api/inventario/arbol').then(r => r.json()).then(data => {
    avlState.nodes = data.nodos || [];
    avlState.selectedId = null;
    const panel = document.getElementById('avl-node-info');
    if (panel) panel.innerHTML = `<span style="color:${AVL_C.muted};font-size:11px">
      Haz clic en un nodo para inspeccionarlo.</span>`;
    avlRender();
  });
}

// Exponer funciones de zoom al HTML (botones del toolbar)
window.avlZoom       = avlZoom;
window.avlResetView  = avlResetView;

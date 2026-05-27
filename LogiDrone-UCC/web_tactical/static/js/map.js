const map = L.map('tactical-map', { zoomControl: false }).setView([11.2408, -74.2110], 13);
L.tileLayer('http://mt0.google.com/vt/lyrs=m&hl=es&x={x}&y={y}&z={z}', { maxZoom: 20 }).addTo(map);

window.onload = function() {
    cargarGrafoZonas();
    actualizarPantallasDrones();
    actualizarPantallaInventario();
    actualizarPantallaPedidos();
};

function cambiarVentana(idVentana) {
    document.querySelectorAll('.ventana').forEach(v => v.classList.remove('active-ventana'));
    document.querySelectorAll('.menu-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('ventana-' + idVentana).classList.add('active-ventana');
    document.getElementById('btn-' + idVentana).classList.add('active');

    if (idVentana === 'principal') setTimeout(() => { map.invalidateSize(); }, 200);
    if (idVentana === 'drones') actualizarPantallasDrones();
    if (idVentana === 'inventario') actualizarPantallaInventario();
    if (idVentana === 'pedidos') actualizarPantallaPedidos();
}

function cargarGrafoZonas() {
    fetch('/api/grafo').then(res => res.json()).then(data => {

        // 1. ZONA EXCLUIDA: CERRO ZIRUMA
        const zCentro = data.ziruma.centro;
        const zRadio  = data.ziruma.radio_km * 1000;

        L.circle(zCentro, { radius: zRadio + 150, color: '#FF2040', weight: 1.5, opacity: 0.5, fillColor: '#FF0030', fillOpacity: 0.06, dashArray: '6 6', interactive: false }).addTo(map);
        L.circle(zCentro, { radius: zRadio, color: '#FF2040', weight: 2.5, opacity: 1, fillColor: '#CC0020', fillOpacity: 0.45, dashArray: '8 5' }).addTo(map).bindPopup(`<b style="color:#FF2040">⛔ ZONA EXCLUIDA — CERRO ZIRUMA</b>`);
        L.marker(zCentro, { icon: L.divIcon({ className: '', html: `<div style="background:rgba(15,0,5,0.88); border:2px solid #FF2040; border-radius:4px; color:#FF5070; font-family:monospace; font-size:10px; font-weight:bold; padding:4px 8px; white-space:nowrap; box-shadow:0 0 14px rgba(255,0,48,0.6);">⛔ ZIRUMA</div>`, iconAnchor: [34, -8] }), interactive: false }).addTo(map);

        // 2. ZONA EXCLUIDA: TAGANGA
        if (data.taganga_zona) {
            const tCentro = data.taganga_zona.centro;
            const tRadio  = data.taganga_zona.radio_km * 1000;
            L.circle(tCentro, { radius: tRadio + 100, color: '#FF8C00', weight: 1.5, opacity: 0.5, fillColor: '#FF8C00', fillOpacity: 0.06, dashArray: '6 6', interactive: false }).addTo(map);
            L.circle(tCentro, { radius: tRadio, color: '#FF8C00', weight: 2.5, opacity: 1, fillColor: '#E65C00', fillOpacity: 0.45, dashArray: '8 5' }).addTo(map).bindPopup(`<b style="color:#FF8C00">⛔ ZONA RESTRINGIDA TAGANGA</b>`);
            L.marker(tCentro, { icon: L.divIcon({ className: '', html: `<div style="background:rgba(15,0,5,0.88); border:2px solid #FF8C00; border-radius:4px; color:#FFB050; font-family:monospace; font-size:10px; font-weight:bold; padding:4px 8px; white-space:nowrap; box-shadow:0 0 14px rgba(255,140,0,0.6);">⛔ RESTRINGIDO</div>`, iconAnchor: [45, -8] }), interactive: false }).addTo(map);
        }

        data.aristas.forEach(a => L.polyline([a.origen, a.destino], { color: '#86868B', weight: 2, opacity: 0.6, dashArray: '4, 6' }).addTo(map));

        data.nodos.forEach(n => {
            let fillColor = '#1561F0';
            let radius = 6;
            if (n.tipo === 'almacen') { fillColor = '#FF9900'; radius = 9; }
            else if (n.tipo === 'recarga') { fillColor = '#00FF9C'; radius = 7; }
            else if (n.tipo === 'logistica') { fillColor = '#FFC857'; radius = 7; }
            else if (n.tipo === 'excluido') return;
            L.circleMarker([n.lat, n.lon], { radius, color: '#131313', fillColor, fillOpacity: 1, weight: 2 }).addTo(map).bindPopup(`<b>${n.nombre}</b>`);
        });
    });
}

function _opcionesPartida(dronesDisponibles) {
    const posicionesVistas = new Set();
    let opciones = '';
    dronesDisponibles.forEach(d => {
        const pos = d.posicion || 'ALMACEN';
        if (!posicionesVistas.has(pos)) posicionesVistas.add(pos);
    });

    const nodosSalida = [
        { id: 'ALMACEN',     nombre: 'Almacén Central'           },
        { id: 'RECARGA_N',   nombre: 'Recarga Norte'             },
        { id: 'PLAYA_AMOR',  nombre: 'Playa del Amor'            }, 
        { id: 'TAGANGA',     nombre: 'Taganga'                   },
        { id: 'CENTRO',      nombre: 'Centro Histórico'          },
        { id: 'RODADERO',    nombre: 'El Rodadero'               },
        { id: 'BELLO',       nombre: 'Bello Horizonte'           },
        { id: 'MINCA',       nombre: 'Minca'                     },
        { id: 'LOGISTICA_R', nombre: 'Punto Logístico Rodadero'  },
    ];

    nodosSalida.forEach(n => {
        const esPosActual = posicionesVistas.has(n.id);
        opciones += `<option value="${n.id}" ${n.id === 'ALMACEN' ? 'selected' : ''}>${n.nombre}${esPosActual ? ' ★' : ''}</option>`;
    });
    return opciones;
}

function actualizarPantallaPedidos() {
    fetch('/api/pedidos/frente').then(res => res.json()).then(data => {
        const panel = document.getElementById('pedido-frente');
        if (data.pedido) { panel.innerHTML = `<span style="color:#1561F0; font-weight:bold; font-size:16px;">[ ID: ${data.pedido.id} ]</span><br><br><b style="color:#86868B;">Destino:</b> ${data.pedido.destino}<br><b style="color:#86868B;">Suministro:</b> ${data.pedido.tipo} (${data.pedido.peso} Kg)<br><b style="color:#1561F0;">Prioridad: ${data.pedido.prioridad}</b>`; } 
        else { panel.innerHTML = `<span style="color:#86868B;">No hay pedidos en la cola.</span>`; }
    });

    fetch('/api/drones').then(res => res.json()).then(data => {
        const disponibles = (data.drones || []).filter(d => d.estado === 'en_espera' && !d.necesita_mant);
        const selectDron = document.getElementById('select-dron-viaje');
        selectDron.innerHTML = '<option value="">-- Seleccione un Dron --</option>';
        disponibles.forEach(d => { selectDron.innerHTML += `<option value="${d.id}">${d.id} · ${d.bateria}% · Ubicación: ${d.posicion || 'ALMACEN'}</option>`; });

        const selectPartida = document.getElementById('select-partida-viaje');
        if (selectPartida) selectPartida.innerHTML = _opcionesPartida(disponibles);

        selectDron.onchange = function () {
            const dron = disponibles.find(d => d.id === this.value);
            if (dron && selectPartida) selectPartida.value = dron.posicion || 'ALMACEN';
        };
    });
}

function crearPedido(e) {
    e.preventDefault();
    fetch('/api/pedidos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ destino: document.getElementById('ped-destino').value, tipo: document.getElementById('ped-tipo').value, prioridad: document.getElementById('ped-prioridad').value, peso: document.getElementById('ped-peso').value }) })
    .then(res => res.json()).then(data => { mostrarToast('✔ ' + data.message, 'success'); document.getElementById('form-pedidos').reset(); actualizarPantallaPedidos(); });
}

function despacharViaje() {
    const dronId = document.getElementById('select-dron-viaje').value;
    const partidaEl = document.getElementById('select-partida-viaje');
    if (!dronId) return mostrarToast('⚠ Seleccione un dron', 'error');

    fetch('/api/pedidos/despachar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id_dron: dronId, partida: partidaEl ? partidaEl.value : 'ALMACEN' }) })
    .then(res => res.json()).then(data => {
        if (data.status === 'success') { mostrarToast('✔ ' + data.message, 'success'); actualizarPantallaPedidos(); actualizarPantallasDrones(); }
        else { mostrarToast('⚠ ' + data.message, 'error'); }
    });
}

function actualizarPantallaInventario() {
    fetch('/api/inventario/lista').then(res => res.json()).then(data => {
        const tabla = document.getElementById('tabla-productos');
        if (!tabla) return;
        tabla.innerHTML = `<thead><tr><th>ID</th><th>Nombre</th><th>Stock</th><th>Acción</th></tr></thead><tbody></tbody>`;
        const tbody = tabla.querySelector('tbody');
        (data.productos || []).forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${p.id}</td><td>${p.nombre}</td><td>${p.stock}</td><td><button onclick="eliminarProducto(${p.id})">✖</button></td>`;
            tbody.appendChild(tr);
        });
    });
    if (typeof avlFetch === 'function') setTimeout(avlFetch, 120);
}

function eliminarProducto(idProducto) {
    if (!confirm('¿Eliminar producto del AVL?')) return;
    fetch(`/api/inventario/${idProducto}`, { method: 'DELETE' }).then(() => { actualizarPantallaInventario(); mostrarToast(`✔ Eliminado`, 'success'); });
}

function agregarInventario(e) {
    e.preventDefault();
    fetch('/api/inventario', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: document.getElementById('inv-id').value, nombre: document.getElementById('inv-nom').value, tipo: document.getElementById('inv-tipo').value, stock: document.getElementById('inv-stock').value, peso: document.getElementById('inv-peso').value }) })
    .then(() => { actualizarPantallaInventario(); document.getElementById('form-inventario').reset(); mostrarToast('✔ Insertado en AVL', 'success'); });
}

function actualizarPantallasDrones() {
    fetch('/api/drones').then(res => res.json()).then(data => {
        const tabla = document.getElementById('tabla-drones-full');
        if(tabla) tabla.innerHTML = `<tr><th>ID</th><th>Estado</th><th>Batería</th></tr>`;
        const select = document.getElementById('ctrl-dron-id');
        if(select) select.innerHTML = '';
        data.drones.forEach(d => {
            if(tabla) tabla.innerHTML += `<tr><td>${d.id}</td><td style="color:#1561F0; font-weight:bold;">${d.estado.toUpperCase()}</td><td>${d.bateria}%</td></tr>`;
            if(select) select.innerHTML += `<option value="${d.id}">${d.id} - ${d.estado}</option>`;
        });
    });
}

function mostrarToast(msg, tipo = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) { container = document.createElement('div'); container.id = 'toast-container'; container.style.cssText = `position:fixed; bottom:28px; right:28px; z-index:99999; display:flex; flex-direction:column; gap:8px; pointer-events:none;`; document.body.appendChild(container); }
    const color = tipo === 'success' ? '#00FF9C' : '#FF4D6D';
    const toast = document.createElement('div');
    toast.style.cssText = `background:#0B1929; color:${color}; border:1px solid ${color}; padding:10px 18px; font-family:monospace; border-radius:4px; opacity:0; transform:translateY(10px); transition:opacity .25s, transform .25s;`;
    toast.textContent = msg; container.appendChild(toast);
    requestAnimationFrame(() => { toast.style.opacity = '1'; toast.style.transform = 'translateY(0)'; });
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(10px)'; setTimeout(() => toast.remove(), 300); }, 3000);
}

const ws = new WebSocket(`ws://${window.location.host}/ws/telemetry`);
const droneIcon = L.divIcon({ className: 'drone-marker', html: `<div style="background-color:#1561F0;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 10px rgba(21,97,240,0.8);"></div>`, iconSize: [14, 14] });
let dronesMarkers = {}, dronesRoutes = {};

ws.onmessage = function(event) {
    const dronesEnVuelo = JSON.parse(event.data);
    const idsEnVuelo = dronesEnVuelo.map(d => d.id);
    Object.keys(dronesMarkers).forEach(id => {
        if (!idsEnVuelo.includes(id)) { map.removeLayer(dronesMarkers[id]); if (dronesRoutes[id]) map.removeLayer(dronesRoutes[id]); delete dronesMarkers[id]; delete dronesRoutes[id]; }
    });
    dronesEnVuelo.forEach(data => {
        const latLng = [data.lat, data.lng];
        if (!dronesMarkers[data.id]) {
            dronesMarkers[data.id] = L.marker(latLng, { icon: droneIcon }).addTo(map).bindTooltip(data.id, { permanent: true, className: "transparent-tooltip", offset: [10, 0] });
            dronesRoutes[data.id] = L.polyline([latLng], { color: '#86868B', dashArray: '6, 6', weight: 3 }).addTo(map);
        } else {
            dronesMarkers[data.id].setLatLng(latLng);
            dronesMarkers[data.id].setTooltipContent(`<b>${data.id}</b><br><span style="font-size:10px;">${data.status}</span>`);
            if (data.status !== 'ESPERANDO RETORNO') dronesRoutes[data.id].addLatLng(latLng);
        }
    });
};

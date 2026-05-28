// map.js — LogiDrone-UCC v3.1
// Correccion: panel pedido-frente siempre actualizado, sin colision con avl_visualizer.js
'use strict';

const map = L.map('tactical-map', { zoomControl: false }).setView([11.2408, -74.2110], 13);
L.tileLayer('http://mt0.google.com/vt/lyrs=m&hl=es&x={x}&y={y}&z={z}', { maxZoom: 20 }).addTo(map);

window.onload = function () {
    cargarGrafoZonas();
    actualizarPantallasDrones();
    // La pantalla de inventario la maneja avl_visualizer.js — no llamar aqui
    // para evitar la doble definicion / colision
    actualizarPantallaPedidos();
};

// ── Grafo y zonas ──────────────────────────────────────────────────────────

function cargarGrafoZonas() {
    fetch('/api/grafo').then(res => res.json()).then(data => {
        const zCentro = data.ziruma.centro;
        const zRadio  = data.ziruma.radio_km * 1000;
        L.circle(zCentro, { radius: zRadio + 150, color: '#FF2040', weight: 1.5, opacity: 0.5, fillColor: '#FF0030', fillOpacity: 0.06, dashArray: '6 6', interactive: false }).addTo(map);
        L.circle(zCentro, { radius: zRadio, color: '#FF2040', weight: 2.5, opacity: 1, fillColor: '#CC0020', fillOpacity: 0.45, dashArray: '8 5' }).addTo(map).bindPopup('<b style="color:#FF2040">⛔ ZONA EXCLUIDA — CERRO ZIRUMA</b>');
        L.marker(zCentro, { icon: L.divIcon({ className: '', html: '<div style="background:rgba(15,0,5,0.88);border:2px solid #FF2040;border-radius:4px;color:#FF5070;font-family:monospace;font-size:10px;font-weight:bold;padding:4px 8px;white-space:nowrap;box-shadow:0 0 14px rgba(255,0,48,0.6);">⛔ ZIRUMA</div>', iconAnchor: [34, -8] }), interactive: false }).addTo(map);

        if (data.taganga_zona) {
            const tCentro = data.taganga_zona.centro;
            const tRadio  = data.taganga_zona.radio_km * 1000;
            L.circle(tCentro, { radius: tRadio + 100, color: '#FF8C00', weight: 1.5, opacity: 0.5, fillColor: '#FF8C00', fillOpacity: 0.06, dashArray: '6 6', interactive: false }).addTo(map);
            L.circle(tCentro, { radius: tRadio, color: '#FF8C00', weight: 2.5, opacity: 1, fillColor: '#E65C00', fillOpacity: 0.45, dashArray: '8 5' }).addTo(map).bindPopup('<b style="color:#FF8C00">⛔ ZONA RESTRINGIDA TAGANGA</b>');
            L.marker(tCentro, { icon: L.divIcon({ className: '', html: '<div style="background:rgba(15,0,5,0.88);border:2px solid #FF8C00;border-radius:4px;color:#FFB050;font-family:monospace;font-size:10px;font-weight:bold;padding:4px 8px;white-space:nowrap;box-shadow:0 0 14px rgba(255,140,0,0.6);">⛔ RESTRINGIDO</div>', iconAnchor: [45, -8] }), interactive: false }).addTo(map);
        }

        data.aristas.forEach(a => L.polyline([a.origen, a.destino], { color: '#86868B', weight: 2, opacity: 0.6, dashArray: '4, 6' }).addTo(map));

        data.nodos.forEach(n => {
            let fillColor = '#1561F0', radius = 6;
            if (n.tipo === 'almacen')   { fillColor = '#FF9900'; radius = 9; }
            else if (n.tipo === 'recarga')   { fillColor = '#00FF9C'; radius = 7; }
            else if (n.tipo === 'logistica') { fillColor = '#FFC857'; radius = 7; }
            else if (n.tipo === 'excluido')  return;
            L.circleMarker([n.lat, n.lon], { radius, color: '#131313', fillColor, fillOpacity: 1, weight: 2 }).addTo(map).bindPopup('<b>' + n.nombre + '</b>');
        });
    });
}

// ── Selector de partida ────────────────────────────────────────────────────

function _opcionesPartida(dronesDisponibles) {
    const posicionesVistas = new Set();
    dronesDisponibles.forEach(d => posicionesVistas.add(d.posicion || 'ALMACEN'));
    const nodos = [
        { id: 'ALMACEN',     nombre: 'Almacén Central'          },
        { id: 'RECARGA_N',   nombre: 'Recarga Norte'            },
        { id: 'PLAYA_AMOR',  nombre: 'Playa del Amor'           },
        { id: 'TAGANGA',     nombre: 'Taganga'                  },
        { id: 'CENTRO',      nombre: 'Centro Histórico'         },
        { id: 'RODADERO',    nombre: 'El Rodadero'              },
        { id: 'BELLO',       nombre: 'Bello Horizonte'          },
        { id: 'MINCA',       nombre: 'Minca'                    },
        { id: 'LOGISTICA_R', nombre: 'Punto Logístico Rodadero' },
    ];
    return nodos.map(n =>
        '<option value="' + n.id + '"' + (n.id === 'ALMACEN' ? ' selected' : '') + '>' +
        n.nombre + (posicionesVistas.has(n.id) ? ' ★' : '') + '</option>'
    ).join('');
}

// ── Inventario dentro del formulario de pedidos ────────────────────────────

function cargarInventarioEnPedido() {
    const sel = document.getElementById('ped-producto');
    if (!sel) return;

    sel.innerHTML = '<option value="" disabled selected>— Cargando inventario… —</option>';

    fetch('/api/inventario/lista')
        .then(r => r.json())
        .then(data => {
            const productos = (data.productos || []).filter(p => p.stock > 0);

            if (!productos.length) {
                sel.innerHTML = '<option value="" disabled selected>— Sin stock disponible —</option>';
                _limpiarInfoProducto();
                return;
            }

            sel.innerHTML = '<option value="" disabled selected>— Seleccione un suministro —</option>';
            productos.forEach(function (p) {
                const opt = document.createElement('option');
                opt.value            = p.id;
                opt.dataset.peso     = p.peso;
                opt.dataset.stock    = p.stock;
                opt.dataset.nombre   = p.nombre;
                opt.textContent      = '[' + p.id + '] ' + p.nombre + ' · Stock: ' + p.stock + ' · ' + p.peso + ' kg/u';
                sel.appendChild(opt);
            });

            sel.onchange = function () {
                const o = sel.options[sel.selectedIndex];
                if (!o || !o.value) { _limpiarInfoProducto(); return; }
                _mostrarInfoProducto({
                    nombre: o.dataset.nombre,
                    stock:  parseInt(o.dataset.stock),
                    peso:   parseFloat(o.dataset.peso),
                });
                const cantInput = document.getElementById('ped-cantidad');
                if (cantInput) {
                    cantInput.max   = o.dataset.stock;
                    cantInput.value = 1;
                }
                if (typeof pedidoRecalcularPeso === 'function') pedidoRecalcularPeso();
            };
        })
        .catch(function (err) {
            console.error('[INVENTARIO PEDIDO]', err);
            sel.innerHTML = '<option value="" disabled selected>— Error al cargar inventario —</option>';
        });
}

function _mostrarInfoProducto(prod) {
    const box = document.getElementById('ped-producto-info');
    if (!box) return;
    box.style.display  = 'flex';
    box.innerHTML =
        '<span style="color:#00FF9C">📦 ' + prod.nombre + '</span>' +
        '<span style="color:#4A6A8A;font-size:10px">Stock disponible: ' +
        '<strong style="color:#FFC857">' + prod.stock + '</strong> uds · ' + prod.peso + ' kg/u</span>';
}

function _limpiarInfoProducto() {
    const box = document.getElementById('ped-producto-info');
    if (box) { box.style.display = 'none'; box.innerHTML = ''; }
    const disp = document.getElementById('ped-peso-display');
    if (disp) disp.textContent = '— selecciona un producto —';
    const hid = document.getElementById('ped-peso');
    if (hid) hid.value = '0';
}

// ── Panel "pedido al frente de la cola" ───────────────────────────────────

function _refrescarFrenteCola() {
    fetch('/api/pedidos/frente')
        .then(res => res.json())
        .then(data => {
            const panel = document.getElementById('pedido-frente');
            if (!panel) return;

            if (data.pedido) {
                const prioColor = {
                    'Alta':  '#FF4D6D',
                    'Media': '#FFC857',
                    'Baja':  '#00FF9C',
                }[data.pedido.prioridad] || '#1561F0';

                panel.innerHTML =
                    '<span style="color:#1561F0;font-weight:bold;font-size:16px;">[ ID: ' + data.pedido.id + ' ]</span><br><br>' +
                    '<b style="color:#86868B;">Destino:</b> ' + data.pedido.destino + '<br>' +
                    '<b style="color:#86868B;">Suministro:</b> ' + data.pedido.tipo + ' (' + data.pedido.peso + ' Kg)<br>' +
                    '<b style="color:' + prioColor + ';">Prioridad: ' + data.pedido.prioridad + '</b>';
            } else {
                panel.innerHTML =
                    '<span style="color:#86868B;font-family:monospace;font-size:12px;">' +
                    '✔ Cola vacía — no hay pedidos pendientes.</span>';
            }
        })
        .catch(function () {
            const panel = document.getElementById('pedido-frente');
            if (panel) panel.innerHTML = '<span style="color:#FF4D6D;font-size:12px;">⚠ Error al consultar la cola.</span>';
        });
}

// ── Pantalla de pedidos completa ───────────────────────────────────────────

function actualizarPantallaPedidos() {
    // 1. Frente de la cola  (siempre se refresca)
    _refrescarFrenteCola();

    // 2. Inventario en el selector
    cargarInventarioEnPedido();

    // 3. Drones disponibles
    fetch('/api/drones').then(res => res.json()).then(data => {
        const disponibles   = (data.drones || []).filter(d => d.estado === 'en_espera' && !d.necesita_mant);
        const selectDron    = document.getElementById('select-dron-viaje');
        const selectPartida = document.getElementById('select-partida-viaje');

        if (selectDron) {
            selectDron.innerHTML = '<option value="">-- Seleccione un Dron --</option>';
            disponibles.forEach(d => {
                selectDron.innerHTML += '<option value="' + d.id + '">' + d.id + ' · ' + d.bateria + '% · ' + (d.posicion || 'ALMACEN') + '</option>';
            });
        }
        if (selectPartida) selectPartida.innerHTML = _opcionesPartida(disponibles);

        if (selectDron && selectPartida) {
            selectDron.onchange = function () {
                const dron = disponibles.find(d => d.id === this.value);
                if (dron) selectPartida.value = dron.posicion || 'ALMACEN';
            };
        }
    });
}

// ── Crear pedido ───────────────────────────────────────────────────────────

function crearPedido(e) {
    e.preventDefault();

    const sel    = document.getElementById('ped-producto');
    const opt    = sel ? sel.options[sel.selectedIndex] : null;
    const cantEl = document.getElementById('ped-cantidad');
    const pesoEl = document.getElementById('ped-peso');

    if (!opt || !opt.value) {
        mostrarToast('⚠ Selecciona un suministro del inventario', 'error');
        return;
    }

    const cantidad = parseInt(cantEl ? cantEl.value : 1) || 1;
    const maxStock = parseInt(opt.dataset.stock) || 0;

    if (cantidad < 1 || cantidad > maxStock) {
        mostrarToast('⚠ Cantidad inválida. Disponible: ' + maxStock + ' uds', 'error');
        return;
    }

    const payload = {
        destino:     document.getElementById('ped-destino').value,
        producto_id: opt.value,
        tipo:        opt.dataset.nombre,
        cantidad:    cantidad,
        prioridad:   document.getElementById('ped-prioridad').value,
        peso:        parseFloat(pesoEl ? pesoEl.value : 0) || (parseFloat(opt.dataset.peso) * cantidad),
    };

    fetch('/api/pedidos', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            mostrarToast('✔ ' + data.message, 'success');
            if (data.stock_restante !== null && data.stock_restante !== undefined) {
                mostrarToast('📦 Stock restante: ' + data.stock_restante + ' uds', 'success');
            }
            // Resetear form y refrescar todo
            if (typeof resetFormPedido === 'function') resetFormPedido();
            else {
                document.getElementById('form-pedidos').reset();
                actualizarPantallaPedidos();
            }
            // Refrescar cola inmediatamente tras encolar
            _refrescarFrenteCola();
            // Refrescar inventario en la pantalla de inventario si está activa
            if (typeof actualizarPantallaInventario === 'function') actualizarPantallaInventario();
        } else {
            mostrarToast('⚠ ' + data.message, 'error');
        }
    })
    .catch(function () { mostrarToast('Error de red', 'error'); });
}

// ── Despachar viaje ────────────────────────────────────────────────────────

function despacharViaje() {
    const dronId    = document.getElementById('select-dron-viaje').value;
    const partidaEl = document.getElementById('select-partida-viaje');
    if (!dronId) return mostrarToast('⚠ Seleccione un dron', 'error');

    fetch('/api/pedidos/despachar', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ id_dron: dronId, partida: partidaEl ? partidaEl.value : 'ALMACEN' }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            mostrarToast('✔ ' + data.message, 'success');
            // Refrescar frente de cola, drones y selector
            _refrescarFrenteCola();
            actualizarPantallaPedidos();
            actualizarPantallasDrones();
        } else {
            mostrarToast('⚠ ' + data.message, 'error');
        }
    });
}

// ── Inventario: sólo definimos eliminarProducto y agregarInventario ────────
// actualizarPantallaInventario viene de avl_visualizer.js (evita conflicto)

function eliminarProducto(idProducto, nombre) {
    if (!confirm('¿Eliminar "' + (nombre || idProducto) + '" del inventario AVL?')) return;
    fetch('/api/inventario/' + idProducto, { method: 'DELETE' })
        .then(function () {
            if (typeof actualizarPantallaInventario === 'function') actualizarPantallaInventario();
            mostrarToast('✔ Eliminado del AVL', 'success');
        });
}

function agregarInventario(e) {
    e.preventDefault();
    fetch('/api/inventario', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            id:    document.getElementById('inv-id').value,
            nombre: document.getElementById('inv-nom').value,
            tipo:  document.getElementById('inv-tipo').value,
            stock: document.getElementById('inv-stock').value,
            peso:  document.getElementById('inv-peso').value,
        }),
    }).then(function () {
        if (typeof actualizarPantallaInventario === 'function') actualizarPantallaInventario();
        document.getElementById('form-inventario').reset();
        mostrarToast('✔ Insertado en AVL', 'success');
    });
}

// ── Drones (tabla simple — el detalle lo gestiona drones_panel.js) ─────────

function actualizarPantallasDrones() {
    // Si drones_panel.js ya está cargado, delegar a su versión completa
    if (typeof window.actualizarPantallasDronesCompleto === 'function') {
        window.actualizarPantallasDronesCompleto();
        return;
    }
    fetch('/api/drones').then(res => res.json()).then(data => {
        const tabla  = document.getElementById('tabla-drones-full');
        const select = document.getElementById('ctrl-dron-id');
        if (tabla)  tabla.innerHTML  = '<tr><th>ID</th><th>Estado</th><th>Batería</th></tr>';
        if (select) select.innerHTML = '';
        (data.drones || []).forEach(function (d) {
            if (tabla)  tabla.innerHTML  += '<tr><td>' + d.id + '</td><td style="color:#1561F0;font-weight:bold">' + d.estado.toUpperCase() + '</td><td>' + d.bateria + '%</td></tr>';
            if (select) select.innerHTML += '<option value="' + d.id + '">' + d.id + ' - ' + d.estado + '</option>';
        });
    });
}

// ── Toast ──────────────────────────────────────────────────────────────────

function mostrarToast(msg, tipo) {
    tipo = tipo || 'success';
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:28px;right:28px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
        document.body.appendChild(container);
    }
    var color = tipo === 'success' ? '#00FF9C' : tipo === 'warning' ? '#FFC857' : '#FF4D6D';
    var toast = document.createElement('div');
    toast.style.cssText = 'background:#0B1929;color:' + color + ';border:1px solid ' + color + ';padding:10px 18px;font-family:monospace;border-radius:4px;opacity:0;transform:translateY(10px);transition:opacity .25s,transform .25s;max-width:340px;';
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(function () { toast.style.opacity = '1'; toast.style.transform = 'translateY(0)'; });
    setTimeout(function () {
        toast.style.opacity = '0'; toast.style.transform = 'translateY(10px)';
        setTimeout(function () { toast.remove(); }, 300);
    }, 3500);
}

// ── WebSocket telemetría ───────────────────────────────────────────────────

const ws = new WebSocket('ws://' + window.location.host + '/ws/telemetry');
const droneIcon = L.divIcon({
    className: 'drone-marker',
    html: '<div style="background-color:#1561F0;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 10px rgba(21,97,240,0.8);"></div>',
    iconSize: [14, 14],
});
var dronesMarkers = {}, dronesRoutes = {};

ws.onmessage = function (event) {
    var dronesEnVuelo = JSON.parse(event.data);
    var idsEnVuelo    = dronesEnVuelo.map(function (d) { return d.id; });
    Object.keys(dronesMarkers).forEach(function (id) {
        if (!idsEnVuelo.includes(id)) {
            map.removeLayer(dronesMarkers[id]);
            if (dronesRoutes[id]) map.removeLayer(dronesRoutes[id]);
            delete dronesMarkers[id];
            delete dronesRoutes[id];
        }
    });
    dronesEnVuelo.forEach(function (data) {
        var latLng = [data.lat, data.lng];
        if (!dronesMarkers[data.id]) {
            dronesMarkers[data.id] = L.marker(latLng, { icon: droneIcon }).addTo(map)
                .bindTooltip(data.id, { permanent: true, className: 'transparent-tooltip', offset: [10, 0] });
            dronesRoutes[data.id] = L.polyline([latLng], { color: '#86868B', dashArray: '6, 6', weight: 3 }).addTo(map);
        } else {
            dronesMarkers[data.id].setLatLng(latLng);
            dronesMarkers[data.id].setTooltipContent('<b>' + data.id + '</b><br><span style="font-size:10px;">' + data.status + '</span>');
            if (data.status !== 'ESPERANDO RETORNO') dronesRoutes[data.id].addLatLng(latLng);
        }
    });

    // Cuando un dron completa la entrega, refrescar el frente de la cola
    if (dronesEnVuelo.length === 0 && Object.keys(dronesMarkers).length === 0) return;
    _refrescarFrenteCola();
};

// Exponer para que drones_panel.js pueda llamar a actualizarPantallaPedidos
window.actualizarPantallaPedidos = actualizarPantallaPedidos;
window._refrescarFrenteCola      = _refrescarFrenteCola;

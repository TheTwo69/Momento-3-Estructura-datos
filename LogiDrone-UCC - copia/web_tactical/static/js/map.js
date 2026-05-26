// ==========================================
// 1. MAPA BASE (Google Maps)
// ==========================================
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

    if(idVentana === 'principal') setTimeout(() => { map.invalidateSize(); }, 200);
    if(idVentana === 'drones') actualizarPantallasDrones();
    if(idVentana === 'inventario') actualizarPantallaInventario();
    if(idVentana === 'pedidos') actualizarPantallaPedidos();
}

// ==========================================
// 1. ZONAS Y GRAFO
// ==========================================
function cargarGrafoZonas() {
    fetch('/api/grafo').then(res => res.json()).then(data => {
        L.circle([data.ziruma.centro[0], data.ziruma.centro[1]], {
            color: '#86868B', fillColor: '#131313', fillOpacity: 0.2,
            radius: data.ziruma.radio_km * 1000
        }).addTo(map);

        data.aristas.forEach(a => L.polyline([a.origen, a.destino], {
            color: '#86868B', weight: 2, opacity: 0.6, dashArray: '4, 6'
        }).addTo(map));

        data.nodos.forEach(n => L.circleMarker([n.lat, n.lon], {
            radius: 6, color: '#131313', fillColor: '#1561F0', fillOpacity: 1, weight: 2
        }).addTo(map).bindPopup(`<b>${n.nombre}</b>`));
    });
}

// ==========================================
// 2. PEDIDOS Y DESPACHO
// ==========================================
function actualizarPantallaPedidos() {
    fetch('/api/pedidos/frente').then(res => res.json()).then(data => {
        const panel = document.getElementById('pedido-frente');
        if (data.pedido) {
            panel.innerHTML = `
                <span style="color:#1561F0; font-weight:bold; font-size:16px;">[ ID Operación: ${data.pedido.id} ]</span><br><br>
                <b style="color:#86868B;">Destino:</b> ${data.pedido.destino}<br>
                <b style="color:#86868B;">Suministro:</b> ${data.pedido.tipo} (${data.pedido.peso} Kg)<br>
                <b style="color:#1561F0; font-size:15px;">Prioridad: ${data.pedido.prioridad}</b>
            `;
        } else {
            panel.innerHTML = `<span style="color:#86868B;">No hay pedidos en la cola. Ingrese uno nuevo.</span>`;
        }
    });

    fetch('/api/drones').then(res => res.json()).then(data => {
        const select = document.getElementById('select-dron-viaje');
        select.innerHTML = '<option value="">-- Seleccione un Dron Operativo --</option>';
        data.drones.forEach(d => {
            if (d.estado === 'en_espera')
                select.innerHTML += `<option value="${d.id}">${d.id} (Batería: ${d.bateria}%)</option>`;
        });
    });
}

function crearPedido(e) {
    e.preventDefault();
    fetch('/api/pedidos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            destino: document.getElementById('ped-destino').value,
            tipo: document.getElementById('ped-tipo').value,
            prioridad: document.getElementById('ped-prioridad').value,
            peso: document.getElementById('ped-peso').value
        })
    }).then(res => res.json()).then(data => {
        alert("CENTRO DE MANDO: " + data.message);
        document.getElementById('form-pedidos').reset();
        actualizarPantallaPedidos();
    });
}

function despacharViaje() {
    const dronId = document.getElementById('select-dron-viaje').value;
    if (!dronId) return alert("Error: Seleccione un dron para el viaje.");
    fetch('/api/pedidos/despachar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_dron: dronId })
    }).then(res => res.json()).then(data => {
        if (data.status === 'success') {
            alert("ALGORITMO A* COMPLETADO:\n\n" + data.message);
            actualizarPantallaPedidos();
            actualizarPantallasDrones();
        } else {
            alert("ERROR TÁCTICO:\n" + data.message);
        }
    });
}

// ==========================================
// 3. INVENTARIO AVL — con eliminación
// ==========================================
function actualizarPantallaInventario() {
    fetch('/api/inventario/lista').then(res => res.json()).then(data => {
        const tabla = document.getElementById('tabla-productos');
        if (!tabla) return;

        tabla.innerHTML = `
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Stock</th>
                <th>Peso (Kg)</th>
                <th style="text-align:center">Acción</th>
              </tr>
            </thead>
            <tbody></tbody>
        `;
        const tbody = tabla.querySelector('tbody');

        (data.productos || []).forEach(p => {
            const stockColor = p.stock < 5 ? '#FF4D6D' : p.stock < 15 ? '#FFC857' : '#00FF9C';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${p.id}</td>
                <td>${p.nombre}</td>
                <td><span style="color:${stockColor};font-weight:bold">${p.stock}</span> uds</td>
                <td>${p.peso}</td>
                <td style="text-align:center">
                  <button
                    onclick="eliminarProducto(${p.id}, '${p.nombre.replace(/'/g, "\\'")}')"
                    class="btn-eliminar-inv"
                    title="Eliminar del árbol AVL"
                  >✖ Eliminar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    });

    // Actualizar árbol visual (delegado a avl_visualizer.js si está cargado)
    if (typeof avlFetch === 'function') {
        setTimeout(avlFetch, 120);
    }
}

/**
 * Elimina un producto del árbol AVL con confirmación.
 * Llama a DELETE /api/inventario/{id} y refresca la tabla y el árbol.
 */
function eliminarProducto(idProducto, nombre) {
    if (!confirm(`⚠ CONFIRMAR ELIMINACIÓN\n\n¿Eliminar "${nombre}" (ID: ${idProducto}) del árbol AVL?\n\nEsta acción no se puede deshacer.`)) {
        return;
    }

    fetch(`/api/inventario/${idProducto}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                // Feedback visual breve en el botón ya desaparecido — usamos alert mínimo
                actualizarPantallaInventario();
                // Notificación no bloqueante si hay soporte
                mostrarToast(`✔ Producto "${nombre}" eliminado del AVL`, 'success');
            } else {
                alert('ERROR AL ELIMINAR:\n' + (data.message || 'Producto no encontrado.'));
            }
        })
        .catch(err => {
            console.error('[INVENTARIO] eliminar:', err);
            alert('Error de red al eliminar el producto.');
        });
}

function agregarInventario(e) {
    e.preventDefault();
    fetch('/api/inventario', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            id: document.getElementById('inv-id').value,
            nombre: document.getElementById('inv-nom').value,
            tipo: document.getElementById('inv-tipo').value,
            stock: document.getElementById('inv-stock').value,
            peso: document.getElementById('inv-peso').value
        })
    }).then(() => {
        actualizarPantallaInventario();
        document.getElementById('form-inventario').reset();
        mostrarToast('✔ Producto insertado en el AVL', 'success');
    });
}

// ==========================================
// 4. GESTIÓN DRONES Y MANTENIMIENTO
// ==========================================
function actualizarPantallasDrones() {
    fetch('/api/drones').then(res => res.json()).then(data => {
        const tabla = document.getElementById('tabla-drones-full');
        tabla.innerHTML = `<tr><th>ID Dron</th><th>Modelo</th><th>Estado</th><th>Batería</th></tr>`;
        const select = document.getElementById('ctrl-dron-id');
        select.innerHTML = '';

        data.drones.forEach(d => {
            let colorBat = d.bateria > 20 ? '#1561F0' : '#86868B';
            tabla.innerHTML += `<tr>
                <td>${d.id}</td>
                <td><span style="color:#86868B;">${d.modelo}</span></td>
                <td style="color:#1561F0; font-weight:bold;">${d.estado.toUpperCase()}</td>
                <td style="color:${colorBat}; font-weight:bold;">${d.bateria}%</td>
            </tr>`;
            select.innerHTML += `<option value="${d.id}">${d.id} - ${d.estado}</option>`;
        });
    });
}

function recargarBateria() {
    const id = document.getElementById('ctrl-dron-id').value;
    fetch(`/api/drones/${id}/recargar`, { method: 'POST' })
        .then(() => { mostrarToast('⚡ Batería al 100%', 'success'); actualizarPantallasDrones(); });
}

function completarEntrega() {
    const id = document.getElementById('ctrl-dron-id').value;
    fetch(`/api/drones/${id}/completar`, { method: 'POST' })
        .then(res => res.json())
        .then(data => { alert("ORDEN EMITIDA:\n" + data.message); actualizarPantallasDrones(); });
}

function registrarMantenimiento() {
    const id  = document.getElementById('ctrl-dron-id').value;
    const tec = document.getElementById('ctrl-tecnico').value;
    const obs = document.getElementById('ctrl-obs').value;
    if (!tec || !obs) return alert("Requerido: Técnico y Observación.");

    fetch(`/api/drones/${id}/mantenimiento`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tecnico: tec, observacion: obs })
    }).then(res => res.json()).then(data => {
        mostrarToast(data.message, 'success');
        document.getElementById('ctrl-tecnico').value = '';
        document.getElementById('ctrl-obs').value = '';
    });
}

function verHistorialPila() {
    const id = document.getElementById('ctrl-dron-id').value;
    fetch(`/api/drones/${id}/pila`)
        .then(res => res.json())
        .then(data => { alert(`CIMA DE LA PILA (Último Mantenimiento):\n\n${data.ultimo_registro}`); });
}

// ==========================================
// TOAST — notificación no bloqueante
// ==========================================
function mostrarToast(msg, tipo = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position:fixed; bottom:28px; right:28px; z-index:99999;
            display:flex; flex-direction:column; gap:8px; pointer-events:none;
        `;
        document.body.appendChild(container);
    }

    const color = tipo === 'success' ? '#00FF9C' : tipo === 'error' ? '#FF4D6D' : '#FFC857';
    const toast = document.createElement('div');
    toast.style.cssText = `
        background:#0B1929; color:${color}; border:1px solid ${color};
        padding:10px 18px; font-family:monospace; font-size:13px;
        border-radius:4px; box-shadow:0 4px 20px rgba(0,0,0,.5);
        opacity:0; transform:translateY(10px);
        transition:opacity .25s, transform .25s; pointer-events:none;
    `;
    toast.textContent = msg;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==========================================
// 5. TELEMETRÍA DINÁMICA
// ==========================================
const ws = new WebSocket(`ws://${window.location.host}/ws/telemetry`);

const droneIcon = L.divIcon({
    className: 'drone-marker',
    html: `<div style="background-color:#1561F0;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 10px rgba(21,97,240,0.8);"></div>`,
    iconSize: [14, 14]
});
let dronesMarkers = {}, dronesRoutes = {};

ws.onmessage = function(event) {
    const dronesEnVuelo = JSON.parse(event.data);
    const idsEnVuelo = dronesEnVuelo.map(d => d.id);

    Object.keys(dronesMarkers).forEach(id => {
        if (!idsEnVuelo.includes(id)) {
            map.removeLayer(dronesMarkers[id]);
            if (dronesRoutes[id]) map.removeLayer(dronesRoutes[id]);
            delete dronesMarkers[id];
            delete dronesRoutes[id];
        }
    });

    dronesEnVuelo.forEach(data => {
        const latLng = [data.lat, data.lng];
        if (!dronesMarkers[data.id]) {
            dronesMarkers[data.id] = L.marker(latLng, { icon: droneIcon }).addTo(map)
                .bindTooltip(data.id + " | " + data.status, { permanent: true, className: "transparent-tooltip", offset: [10, 0] });
            dronesRoutes[data.id] = L.polyline([latLng], { color: '#86868B', dashArray: '6, 6', weight: 3 }).addTo(map);
        } else {
            dronesMarkers[data.id].setLatLng(latLng);
            dronesMarkers[data.id].setTooltipContent(`<b>${data.id}</b><br><span style="font-size:10px;">${data.status}</span>`);
            if (data.status !== 'ESPERANDO RETORNO') dronesRoutes[data.id].addLatLng(latLng);
        }
    });
};
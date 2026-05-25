// ==========================================
// 1. INICIALIZACIÓN DEL MAPA TÁCTICO
// ==========================================
const map = L.map('tactical-map', { zoomControl: false }).setView([11.2408, -74.2110], 13);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: 'LogiDrone-UCC Tactical Net',
    maxZoom: 19
}).addTo(map);

L.control.zoom({ position: 'bottomright' }).addTo(map);

const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);
const drawControl = new L.Control.Draw({ edit: { featureGroup: drawnItems } });
map.addControl(drawControl);

// Cargar Grafo (Nodos y Aristas de Santa Marta)
fetch('/api/grafo')
    .then(response => response.json())
    .then(data => {
        // Ziruma
        L.circle([data.ziruma.centro[0], data.ziruma.centro[1]], {
            color: 'red', fillColor: '#ff0000', fillOpacity: 0.3, radius: data.ziruma.radio_km * 1000
        }).addTo(map).bindPopup("<b>ZONA ZIRUMA</b>");

        // Rutas
        data.aristas.forEach(arista => {
            L.polyline([arista.origen, arista.destino], { color: '#00ffcc', weight: 1, opacity: 0.3, dashArray: '4' }).addTo(map);
        });

        // Nodos
        data.nodos.forEach(nodo => {
            let color = '#fff';
            if(nodo.tipo === 'almacen') color = '#33ff33';
            if(nodo.tipo === 'recarga') color = '#ffff33';
            L.circleMarker([nodo.lat, nodo.lon], { radius: 6, color: color, weight: 2, fillOpacity: 0.8 })
             .addTo(map).bindPopup(`<b>${nodo.nombre}</b>`);
        });
    }).catch(e => console.log("Aún no hay backend de grafo conectado, ignorando..."));

// ==========================================
// 2. TELEMETRÍA WEBSOCKET
// ==========================================
const ws = new WebSocket(`ws://${window.location.host}/ws/telemetry`);
const droneIcon = L.divIcon({
    className: 'drone-marker',
    html: `<div style="background-color: #00ffcc; width: 15px; height: 15px; border-radius: 50%; box-shadow: 0 0 15px #00ffcc;"></div>`,
    iconSize: [15, 15]
});

let droneMarker = null;

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    // UI Telemetría
    document.getElementById('telemetry-data').innerHTML = `
        ID: ${data.id} <br>ESTADO: ${data.status}<br>
        LAT: ${data.lat.toFixed(5)} <br>LNG: ${data.lng.toFixed(5)} <br>
        BAT: <span style="color:#33ff33;">${data.battery}%</span>
    `;

    // Alerta Batería
    const alertBox = document.getElementById('alert-box');
    if (data.battery <= 20) {
        alertBox.style.display = 'block';
    } else {
        alertBox.style.display = 'none';
    }

    // Mover dron en el mapa
    const latLng = [data.lat, data.lng];
    if (!droneMarker) {
        droneMarker = L.marker(latLng, {icon: droneIcon}).addTo(map);
    } else {
        droneMarker.setLatLng(latLng);
    }
};

// ==========================================
// 3. LÓGICA DE NAVEGACIÓN SPA (VENTANAS)
// ==========================================
function cambiarVentana(idVentana) {
    // Ocultar todas las ventanas
    document.querySelectorAll('.ventana').forEach(v => v.classList.remove('active-ventana'));
    // Quitar active de los botones
    document.querySelectorAll('.menu-btn').forEach(b => b.classList.remove('active'));

    // Mostrar seleccionada
    document.getElementById('ventana-' + idVentana).classList.add('active-ventana');
    document.getElementById('btn-' + idVentana).classList.add('active');

    // ¡VITAL! Recalcular el tamaño del mapa cuando se vuelve a mostrar
    if(idVentana === 'principal') {
        setTimeout(() => { map.invalidateSize(); }, 200);
    }
}

// ==========================================
// 4. FUNCIONES DE FORMULARIOS (AVL, COLA, PILA)
// ==========================================
let estructuraVisualAVL = "RAÍZ_AVL\n │"; 

function agregarInventario(e) {
    e.preventDefault();
    const id = document.getElementById('prod-id').value;
    const nombre = document.getElementById('prod-nombre').value;

    fetch('/api/inventario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, nombre: nombre })
    })
    .then(res => res.json())
    .then(data => {
        estructuraVisualAVL += `\n ├── Nodo [ID: ${id}] -> ${nombre}`;
        document.getElementById('avl-visualizer').innerText = estructuraVisualAVL;
        document.getElementById('prod-id').value = '';
        document.getElementById('prod-nombre').value = '';
    }).catch(e => {
        // En caso de que el backend no esté listo, simular visualmente de todos modos
        estructuraVisualAVL += `\n ├── Nodo [ID: ${id}] -> ${nombre} (Modo Local)`;
        document.getElementById('avl-visualizer').innerText = estructuraVisualAVL;
    });
}

function crearPedido(e) {
    e.preventDefault();
    const destino = document.getElementById('ped-destino').value;
    const prod = document.getElementById('ped-prod').value;
    const dron = document.getElementById('ped-dron').value;

    alert(`CENTRO DE DESPACHO:\nEl dron ${dron} fue encolado para llevar el producto [${prod}] a la zona de ${destino}.`);
    document.getElementById('ped-prod').value = '';
    document.getElementById('ped-dron').value = '';
}

function agregarDron(e) {
    e.preventDefault();
    const id = document.getElementById('dron-id').value;
    const mod = document.getElementById('dron-mod').value;
    document.getElementById('lista-drones').innerHTML += `<li>[EN ESPERA] ${id} - Modelo: ${mod}</li>`;
    document.getElementById('dron-id').value = '';
    document.getElementById('dron-mod').value = '';
}

function verMantenimiento() {
    alert("ÚLTIMO MANTENIMIENTO (CIMA DE LA PILA LIFO):\n15-MAY-2026 | Limpieza de salitre | Ing. Torres");
}
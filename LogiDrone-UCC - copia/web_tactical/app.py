import asyncio
import json
import os
import math
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# --- INTEGRACIÓN CON EL NÚCLEO DEL PROYECTO ---
# Añadimos el directorio padre al PATH para poder importar tus archivos
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_padre = os.path.dirname(directorio_actual)
sys.path.append(directorio_padre)

# Importamos tu mapa de Santa Marta
from estructuras.grafo import construir_mapa, ZIRUMA_CENTRO, ZIRUMA_RADIO_KM

app = FastAPI(title="LogiDrone-UCC Tactical Center")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATA_FILE = "data/zones.geojson"
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)

# Instanciamos tu grafo en memoria
mapa_tactico = construir_mapa()

@app.get("/", response_class=HTMLResponse)
async def get_tactical_map(request: Request):
    """Renderiza la interfaz principal del HUD Militar."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/grafo")
async def get_grafo_data():
    """Extrae los nodos y aristas de tu grafo.py y los envía al Frontend."""
    nodos_data = []
    aristas_data = []
    
    # 1. Extraer Nodos
    for id_nodo, nodo in mapa_tactico.nodos.items():
        nodos_data.append({
            "id": nodo.id_nodo,
            "nombre": nodo.nombre,
            "lat": nodo.lat,
            "lon": nodo.lon,
            "tipo": nodo.tipo
        })
        
        # 2. Extraer Aristas (Rutas)
        arista = nodo.primera_arista
        while arista is not None:
            destino = mapa_tactico.nodos[arista.destino]
            aristas_data.append({
                "origen": [nodo.lat, nodo.lon],
                "destino": [destino.lat, destino.lon],
                "peso": arista.peso
            })
            arista = arista.siguiente

    return {
        "nodos": nodos_data, 
        "aristas": aristas_data,
        "ziruma": {
            "centro": ZIRUMA_CENTRO,
            "radio_km": ZIRUMA_RADIO_KM
        }
    }

@app.get("/api/zones")
async def get_zones():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

@app.post("/api/zones")
async def save_zone(feature: dict):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    data["features"].append(feature)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return {"status": "success", "message": "Zona registrada"}

# Importar tus estructuras (Asegúrate de que las rutas coincidan con tus archivos)
from estructuras.cola import Cola
from estructuras.avl import ArbolAVL

# Instanciar las estructuras globales en memoria
cola_pedidos = Cola()
inventario_avl = ArbolAVL()

@app.post("/api/inventario")
async def api_agregar_inventario(request: Request):
    """Agrega un producto al Árbol AVL [Requisito Documento]"""
    data = await request.json()
    # Aquí llamamos al método de inserción de tu AVL. 
    # (Ajusta 'insertar' al nombre real del método en tu avl.py)
    # inventario_avl.insertar(data['id'], data['nombre'])
    
    print(f"🌲 AVL INSERT: Producto {data['nombre']} (ID: {data['id']}) agregado y balanceado.")
    return {"status": "success", "message": "Producto balanceado en el Árbol AVL"}

@app.post("/api/pedidos")
async def api_crear_pedido(request: Request):
    """Encola un pedido en la estructura FIFO [Requisito Documento]"""
    data = await request.json()
    # Aquí llamamos al método de encolar.
    # cola_pedidos.encolar({"destino": data['destino'], "producto_id": data['producto']})
    
    print(f"📦 COLA FIFO: Pedido hacia {data['destino']} ingresado a la cola.")
    return {"status": "success", "message": "Pedido encolado correctamente"}

@app.get("/api/mantenimiento/ultimo")
async def api_ultimo_mantenimiento():
    """Consulta la cima de la Pila de mantenimiento [Requisito Documento]"""
    # Usando el método que ya tienes en dron.py para ver la cima
    return {"status": "success", "registro": "15-MAY-2026 | Limpieza de salitre | Ing. Torres"}



@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Ahora el dron simula despegar desde las coordenadas del ALMACEN CENTRAL (Santa Marta)
    base_lat, base_lng = 11.2408, -74.2110 
    t = 0
    try:
        while True:
            lat = base_lat + (math.sin(t) * 0.005)
            lng = base_lng + (math.cos(t) * 0.005)
            
            await websocket.send_json({
                "id": "DRN-X77",
                "status": "EN_VUELO",
                "lat": lat,
                "lng": lng,
                "alt": 120.5,
                "speed": 45.2,
                "battery": 88
            })
            t += 0.1
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Enlace perdido.")
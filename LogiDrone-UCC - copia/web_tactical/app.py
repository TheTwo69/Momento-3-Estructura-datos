import asyncio
import math
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_padre = os.path.dirname(directorio_actual)
if directorio_padre not in sys.path:
    sys.path.insert(0, directorio_padre)

from logica.sistema import Sistema
from logica.dron import Dron
from estructuras.grafo import ZIRUMA_CENTRO, ZIRUMA_RADIO_KM, ZONAS_EXCLUIDAS

app = FastAPI(title="LogiDrone HUD")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sis = Sistema()

@app.get("/", response_class=HTMLResponse)
async def get_tactical_map(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# --- GRAFO Y ZONAS ---
@app.get("/api/grafo")
async def api_grafo():
    nodos_data, aristas_data = [], []
    for id_nodo, nodo in sis.mapa.nodos.items():
        nodos_data.append({"id": nodo.id_nodo, "nombre": nodo.nombre, "lat": nodo.lat, "lon": nodo.lon, "tipo": nodo.tipo})
        arista = nodo.primera_arista
        while arista is not None:
            destino = sis.mapa.nodos[arista.destino]
            aristas_data.append({"origen": [nodo.lat, nodo.lon], "destino": [destino.lat, destino.lon], "peso": arista.peso})
            arista = arista.siguiente
            
    # REDUCCIÓN DEL 50% DE LA ZONA ROJA SOLICITADA
    radio_reducido = ZIRUMA_RADIO_KM * 0.5 
    
    return {"nodos": nodos_data, "aristas": aristas_data, "ziruma": {"centro": ZIRUMA_CENTRO, "radio_km": radio_reducido}}

# --- DRONES Y MANTENIMIENTO ---
@app.get("/api/drones")
async def api_listar_drones():
    lista = [{"id": d.id_dron, "modelo": d.modelo, "estado": getattr(d, 'status_ui', d.estado), "bateria": int(d.bateria)} for d in sis.lista_drones()]
    return {"drones": lista}

@app.post("/api/drones/{id_dron}/volar")
async def api_volar(id_dron: str):
    if id_dron in sis.drones:
        d = sis.drones[id_dron]
        d.estado = 'en_vuelo'
        d.lat, d.lng = 11.2408, -74.2110
        d.status_ui = 'VUELO LIBRE'
        return {"status": "success"}
    return {"status": "error"}

@app.post("/api/drones/{id_dron}/recargar")
async def api_recargar(id_dron: str):
    sis.recargar_dron(id_dron)
    return {"status": "success"}

@app.post("/api/drones/{id_dron}/mantenimiento")
async def api_registrar_mantenimiento(id_dron: str, request: Request):
    data = await request.json()
    sis.registrar_mantenimiento(id_dron, "Taller Técnico", data['tecnico'], "Hoy", data['observacion'])
    return {"status": "success", "message": f"Mantenimiento apilado para {id_dron}"}

@app.post("/api/drones/{id_dron}/completar")
async def api_completar_entrega(id_dron: str):
    dron = sis.drones.get(id_dron)
    if dron and getattr(dron, 'esperando_retorno', False):
        # 1. Calcula ruta A* de retorno
        ruta, dist = sis.mapa.a_estrella(dron.posicion_actual, 'ALMACEN', ZONAS_EXCLUIDAS)
        if ruta:
            dron.ruta_nodos_latlng = [(sis.mapa.nodos[n].lat, sis.mapa.nodos[n].lon, n) for n in ruta]
            
            # 2. MANIOBRA DE EVASIÓN DE RETORNO (Si viene de Taganga, rodea por el mar)
            if dron.posicion_actual == 'TAGANGA':
                punto_mar_retorno = (11.2650, -74.2250, 'DESVÍO_MARITIMO_RETORNO')
                dron.ruta_nodos_latlng.insert(1, punto_mar_retorno)

            dron.target_idx = 1
            dron.estado = 'retornando'
            dron.status_ui = 'RETORNANDO'
            dron.esperando_retorno = False
            return {"status": "success", "message": f"Dron {id_dron} iniciando vuelo de retorno a la base."}
    
    sis.completar_entrega(id_dron)
    if dron: dron.status_ui = 'en_espera'
    return {"status": "success", "message": "Viaje completado. Dron en base."}

@app.get("/api/drones/{id_dron}/pila")
async def api_pila(id_dron: str):
    if id_dron in sis.drones:
        return {"ultimo_registro": sis.drones[id_dron].ultimo_mantenimiento()}
    return {"ultimo_registro": "Sin registros"}

# --- INVENTARIO (AVL) ---
@app.get("/api/inventario/lista")
async def api_inventario_lista():
    productos = [{"id": p.id_producto, "nombre": p.nombre, "stock": p.stock, "peso": p.peso} for p in sis.lista_productos()]
    return {"productos": productos}

@app.get("/api/inventario/arbol")
async def api_arbol():
    return {"nodos": sis.inventario.obtener_nodos_visualizacion()}

@app.post("/api/inventario")
async def api_agregar_inv(request: Request):
    data = await request.json()
    sis.agregar_producto(int(data['id']), data['nombre'], data['tipo'], int(data['stock']), float(data['peso']))
    return {"status": "success"}

# --- PEDIDOS (COLA FIFO Y ALGORITMO A*) ---
@app.post("/api/pedidos")
async def api_crear_pedido(request: Request):
    data = await request.json()
    destino_id = data['destino']
    destino_nombre = sis.mapa.nodos[destino_id].nombre if destino_id in sis.mapa.nodos else "Desconocido"
    sis.crear_pedido(destino_id, destino_nombre, data['tipo'], data['prioridad'], float(data['peso']))
    return {"status": "success", "message": "Pedido encolado exitosamente."}

@app.get("/api/pedidos/frente")
async def api_pedido_frente():
    frente = sis.cola_pedidos.ver_frente()
    if frente:
        return {"pedido": {"id": frente.id_pedido, "destino": frente.destino_nombre, "tipo": frente.tipo_producto, "prioridad": frente.prioridad, "peso": frente.peso_kg}}
    return {"pedido": None}

@app.post("/api/pedidos/despachar")
async def api_despachar_pedido(request: Request):
    data = await request.json()
    id_dron = data['id_dron']

    if sis.cola_pedidos.esta_vacia(): return {"status": "error", "message": "La cola de pedidos está vacía."}
    
    dron = sis.drones.get(id_dron)
    if not dron: return {"status": "error", "message": "Dron no encontrado."}
    if dron.bateria <= 20: return {"status": "error", "message": "Batería insuficiente."}

    pedido = sis.cola_pedidos.desencolar()
    
    # 1. Calculamos la ruta con tu algoritmo A*
    ruta, distancia = sis.mapa.a_estrella(dron.posicion_actual, pedido.destino_id, ZONAS_EXCLUIDAS)
    
    if ruta is None:
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error", "message": f"No se encontró ruta a {pedido.destino_nombre}."}

    dron.asignar_pedido(pedido, ruta)
    dron.lat, dron.lng = sis.mapa.nodos[dron.posicion_actual].lat, sis.mapa.nodos[dron.posicion_actual].lon
    
    # Preparamos las coordenadas reales
    dron.ruta_nodos_latlng = [(sis.mapa.nodos[n].lat, sis.mapa.nodos[n].lon, n) for n in ruta]

    # 2. MANIOBRA TÁCTICA DE IDA: Rodear el Cerro hacia Taganga
    if pedido.destino_id == 'TAGANGA':
        # Punto sobre el mar Caribe para evadir visualmente Ziruma
        punto_mar = (11.2650, -74.2250, 'DESVÍO_MARITIMO_IDA')
        # Insertamos el waypoint en la ruta, justo después de salir del Almacén
        dron.ruta_nodos_latlng.insert(1, punto_mar)

    dron.target_idx = 1
    dron.esperando_retorno = False
    dron.status_ui = 'EN VIAJE (IDA)'

    ruta_str = " ➔ ".join(ruta)
    if pedido.destino_id == 'TAGANGA':
        ruta_str = f"ALMACEN ➔ (Desvío Marítimo) ➔ {ruta_str.replace('ALMACEN ➔ ', '')}"

    return {"status": "success", "message": f"Despacho exitoso a {pedido.destino_nombre}.\nRuta Táctica: [ {ruta_str} ]"}

# --- MOTOR DE TELEMETRÍA AVANZADO ---
@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await websocket.accept()
    t = 0
    try:
        while True:
            activos = []
            for dron in sis.lista_drones():
                if dron.estado in ['en_vuelo', 'retornando']:
                    if not hasattr(dron, 'lat'): dron.lat, dron.lng = 11.2408, -74.2110
                    
                    if not getattr(dron, 'esperando_retorno', False):
                        dron.consumir_bateria(0.2) 

                    # Movimiento Vectorial
                    if hasattr(dron, 'ruta_nodos_latlng') and hasattr(dron, 'target_idx') and not getattr(dron, 'esperando_retorno', False):
                        if dron.target_idx < len(dron.ruta_nodos_latlng):
                            t_lat, t_lng, t_nodo = dron.ruta_nodos_latlng[dron.target_idx]
                            
                            dlat = t_lat - dron.lat
                            dlng = t_lng - dron.lng
                            dist = math.hypot(dlat, dlng)
                            step = 0.002 
                            
                            if dist < step:
                                dron.lat, dron.lng = t_lat, t_lng
                                dron.posicion_actual = t_nodo
                                dron.target_idx += 1
                            else:
                                dron.lat += (dlat/dist) * step
                                dron.lng += (dlng/dist) * step
                        else:
                            if dron.estado == 'en_vuelo':
                                dron.esperando_retorno = True
                                dron.status_ui = 'ESPERANDO RETORNO'
                            elif dron.estado == 'retornando':
                                sis.completar_entrega(dron.id_dron)
                                dron.status_ui = 'en_espera'
                                if hasattr(dron, 'ruta_nodos_latlng'): del dron.ruta_nodos_latlng

                    elif dron.estado == 'en_vuelo' and not hasattr(dron, 'ruta_nodos_latlng'):
                        dron.lat += (math.sin(t + hash(dron.id_dron)) * 0.002)
                        dron.lng += (math.cos(t + hash(dron.id_dron)) * 0.002)

                    if dron.estado in ['en_vuelo', 'retornando']:
                        activos.append({
                            "id": dron.id_dron, "lat": dron.lat, "lng": dron.lng, 
                            "battery": int(dron.bateria), "status": dron.status_ui
                        })
                        
            await websocket.send_json(activos)
            t += 0.2
            await asyncio.sleep(0.5) 
    except WebSocketDisconnect:
        pass
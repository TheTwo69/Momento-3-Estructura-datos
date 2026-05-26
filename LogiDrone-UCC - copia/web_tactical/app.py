import asyncio
import math
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

directorio_actual  = os.path.dirname(os.path.abspath(__file__))
directorio_padre   = os.path.dirname(directorio_actual)
if directorio_padre not in sys.path:
    sys.path.insert(0, directorio_padre)

from logica.sistema import Sistema, MODELOS_DISPONIBLES
from logica.dron import Dron
from estructuras.grafo import ZIRUMA_CENTRO, ZIRUMA_RADIO_KM, ZONAS_EXCLUIDAS

app = FastAPI(title="LogiDrone HUD")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sis = Sistema()


# ── RAÍZ ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_tactical_map(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ── GRAFO Y ZONAS ─────────────────────────────────────────────────────────────

@app.get("/api/grafo")
async def api_grafo():
    nodos_data, aristas_data = [], []
    for id_nodo, nodo in sis.mapa.nodos.items():
        nodos_data.append({
            "id": nodo.id_nodo, "nombre": nodo.nombre,
            "lat": nodo.lat, "lon": nodo.lon, "tipo": nodo.tipo
        })
        arista = nodo.primera_arista
        while arista is not None:
            destino = sis.mapa.nodos[arista.destino]
            aristas_data.append({
                "origen":  [nodo.lat, nodo.lon],
                "destino": [destino.lat, destino.lon],
                "peso":    arista.peso
            })
            arista = arista.siguiente

    radio_reducido = ZIRUMA_RADIO_KM * 0.5
    return {
        "nodos":   nodos_data,
        "aristas": aristas_data,
        "ziruma":  {"centro": ZIRUMA_CENTRO, "radio_km": radio_reducido}
    }


# ── DRONES ────────────────────────────────────────────────────────────────────

def _serializar_dron(d: Dron) -> dict:
    """Serializa un dron incluyendo los nuevos campos y la alerta de mantenimiento."""
    necesita_mant = d.necesita_mantenimiento()
    return {
        "id":               d.id_dron,
        "modelo":           d.modelo,
        "estado":           getattr(d, 'status_ui', d.estado),
        "bateria":          int(d.bateria),
        "capacidad_kg":     d.capacidad_kg,
        "velocidad_kmh":    d.velocidad_kmh,
        "posicion":         d.posicion_actual,
        "necesita_mant":    necesita_mant,
        "ultimo_mant":      d.ultimo_mantenimiento(),
        # Para la vista: razón del mantenimiento
        "razon_mant": (
            f"Batería crítica ({d.bateria}% ≤ 20%)" if d.bateria <= Dron.UMBRAL_BATERIA_CRITICA
            else "Mantenimiento programado"
        ) if necesita_mant else None,
    }


@app.get("/api/drones")
async def api_listar_drones():
    return {"drones": [_serializar_dron(d) for d in sis.lista_drones()]}


@app.get("/api/drones/mantenimiento")
async def api_drones_mantenimiento():
    """Devuelve solo los drones que requieren atención."""
    return {
        "drones": [_serializar_dron(d) for d in sis.drones_en_mantenimiento()],
        "total":  len(sis.drones_en_mantenimiento()),
    }


@app.get("/api/drones/modelos")
async def api_modelos():
    """Lista de modelos disponibles para nuevos drones."""
    return {"modelos": MODELOS_DISPONIBLES}


@app.post("/api/drones")
async def api_agregar_dron(request: Request):
    """
    Crea un nuevo dron en la flota.
    Body JSON:
      { "modelo": "DJI Pro X", "capacidad_kg": 5.0, "velocidad_kmh": 80.0 }
    """
    data = await request.json()
    modelo       = data.get("modelo", "DJI Pro X")
    capacidad_kg = float(data.get("capacidad_kg", 5.0))
    velocidad_kmh = float(data.get("velocidad_kmh", 80.0))

    dron, msg = sis.agregar_dron(modelo, capacidad_kg, velocidad_kmh)
    if dron:
        return {"status": "success", "message": msg, "dron": _serializar_dron(dron)}
    return {"status": "error", "message": msg}


@app.delete("/api/drones/{id_dron}")
async def api_eliminar_dron(id_dron: str):
    ok, msg = sis.eliminar_dron(id_dron)
    return {"status": "success" if ok else "error", "message": msg}


@app.post("/api/drones/{id_dron}/volar")
async def api_volar(id_dron: str):
    if id_dron in sis.drones:
        d = sis.drones[id_dron]
        if d.necesita_mantenimiento():
            return {
                "status": "error",
                "message": f"{id_dron} no puede volar: {d.razon_mant if hasattr(d,'razon_mant') else 'requiere mantenimiento'}"
            }
        d.estado = 'en_vuelo'
        d.lat, d.lng = 11.2408, -74.2110
        d.status_ui = 'VUELO LIBRE'
        return {"status": "success"}
    return {"status": "error", "message": "Dron no encontrado"}


@app.post("/api/drones/{id_dron}/recargar")
async def api_recargar(id_dron: str):
    sis.recargar_dron(id_dron)
    return {"status": "success", "message": f"{id_dron} recargado al 100%"}


@app.post("/api/drones/{id_dron}/mantenimiento")
async def api_registrar_mantenimiento(id_dron: str, request: Request):
    data = await request.json()
    sis.registrar_mantenimiento(
        id_dron,
        data.get("operacion", "Mantenimiento general"),
        data['tecnico'],
        data.get("fecha", "Hoy"),
        data['observacion']
    )
    dron = sis.drones.get(id_dron)
    necesita = dron.necesita_mantenimiento() if dron else False
    return {
        "status":        "success",
        "message":       f"Mantenimiento apilado para {id_dron}",
        "estado_actual": dron.estado if dron else "?",
        "necesita_mant": necesita,
    }


@app.post("/api/drones/{id_dron}/completar")
async def api_completar_entrega(id_dron: str):
    dron = sis.drones.get(id_dron)
    if dron and getattr(dron, 'esperando_retorno', False):
        ruta, dist = sis.mapa.a_estrella(dron.posicion_actual, 'ALMACEN', ZONAS_EXCLUIDAS)
        if ruta:
            dron.ruta_nodos_latlng = [
                (sis.mapa.nodos[n].lat, sis.mapa.nodos[n].lon, n) for n in ruta
            ]
            if dron.posicion_actual == 'TAGANGA':
                dron.ruta_nodos_latlng.insert(1, (11.2650, -74.2250, 'DESVÍO_MARITIMO_RETORNO'))
            dron.target_idx = 1
            dron.estado = 'retornando'
            dron.status_ui = 'RETORNANDO'
            dron.esperando_retorno = False
            return {"status": "success", "message": f"{id_dron} iniciando retorno a la base."}

    sis.completar_entrega(id_dron)
    if dron:
        dron.status_ui = dron.estado
    msg = "Viaje completado. Dron en base."
    if dron and dron.necesita_mantenimiento():
        msg += f" ⚠ Batería al {dron.bateria}% — requiere mantenimiento."
    return {"status": "success", "message": msg, "necesita_mant": dron.necesita_mantenimiento() if dron else False}


@app.get("/api/drones/{id_dron}/pila")
async def api_pila(id_dron: str):
    if id_dron in sis.drones:
        d = sis.drones[id_dron]
        historial = d.historial_mantenimiento.a_lista()
        return {
            "ultimo_registro": d.ultimo_mantenimiento(),
            "total_registros": len(historial),
            "historial": [
                {"operacion": r.operacion, "tecnico": r.tecnico,
                 "fecha": r.fecha, "observacion": r.observacion}
                for r in historial
            ],
        }
    return {"ultimo_registro": "Sin registros", "total_registros": 0, "historial": []}


# ── INVENTARIO (AVL) ──────────────────────────────────────────────────────────

@app.get("/api/inventario/lista")
async def api_inventario_lista():
    productos = []
    for p in sis.lista_productos():
        peso = getattr(p, 'peso_kg', getattr(p, 'peso', 0))
        productos.append({"id": p.id_producto, "nombre": p.nombre, "stock": p.stock, "peso": peso})
    return {"productos": productos}


@app.get("/api/inventario/arbol")
async def api_arbol():
    nodos_raw = sis.inventario.obtener_nodos_visualizacion()
    nodos = [{
        "id":     n.get("id"),
        "padre":  n.get("padre"),
        "nivel":  n.get("nivel", 0),
        "pos":    n.get("pos", 0),
        "fe":     n.get("fe", 0),
        "nombre": n.get("nombre", ""),
    } for n in nodos_raw]
    return {"nodos": nodos}


@app.post("/api/inventario")
async def api_agregar_inv(request: Request):
    data = await request.json()
    sis.agregar_producto(int(data['id']), data['nombre'], data['tipo'],
                         int(data['stock']), float(data['peso']))
    return {"status": "success"}


@app.delete("/api/inventario/{id_producto}")
async def api_eliminar_producto(id_producto: int):
    try:
        producto = sis.buscar_producto(id_producto)
        if producto is None:
            return {"status": "error", "message": f"Producto {id_producto} no encontrado"}
        sis.eliminar_producto(id_producto)
        return {"status": "success", "message": f"Producto {id_producto} eliminado del AVL"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── PEDIDOS (COLA FIFO Y ALGORITMO A*) ────────────────────────────────────────

@app.post("/api/pedidos")
async def api_crear_pedido(request: Request):
    data = await request.json()
    destino_id     = data['destino']
    destino_nombre = sis.mapa.nodos[destino_id].nombre if destino_id in sis.mapa.nodos else "Desconocido"
    sis.crear_pedido(destino_id, destino_nombre, data['tipo'], data['prioridad'], float(data['peso']))
    return {"status": "success", "message": "Pedido encolado exitosamente."}


@app.get("/api/pedidos/frente")
async def api_pedido_frente():
    frente = sis.cola_pedidos.ver_frente()
    if frente:
        return {"pedido": {
            "id":        frente.id_pedido,
            "destino":   frente.destino_nombre,
            "tipo":      frente.tipo,
            "prioridad": frente.prioridad,
            "peso":      frente.peso_kg,
        }}
    return {"pedido": None}


@app.post("/api/pedidos/despachar")
async def api_despachar_pedido(request: Request):
    data   = await request.json()
    id_dron = data['id_dron']

    if sis.cola_pedidos.esta_vacia():
        return {"status": "error", "message": "La cola de pedidos está vacía."}

    dron = sis.drones.get(id_dron)
    if not dron:
        return {"status": "error", "message": "Dron no encontrado."}
    if dron.necesita_mantenimiento():
        razon = f"Batería al {dron.bateria}% (≤ 20%)" if dron.bateria <= 20 else "en mantenimiento"
        return {"status": "error", "message": f"{id_dron} no puede despacharse: {razon}."}
    if dron.bateria <= Dron.UMBRAL_BATERIA_CRITICA:
        return {"status": "error", "message": f"Batería insuficiente ({dron.bateria}%)."}

    pedido = sis.cola_pedidos.desencolar()
    ruta, distancia = sis.mapa.a_estrella(dron.posicion_actual, pedido.destino_id, ZONAS_EXCLUIDAS)

    if ruta is None:
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error", "message": f"No se encontró ruta a {pedido.destino_nombre}."}

    ok = dron.asignar_pedido(pedido, ruta)
    if not ok:
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error", "message": f"{id_dron} no puede volar (requiere mantenimiento)."}

    dron.lat = sis.mapa.nodos[dron.posicion_actual].lat
    dron.lng = sis.mapa.nodos[dron.posicion_actual].lon
    dron.ruta_nodos_latlng = [
        (sis.mapa.nodos[n].lat, sis.mapa.nodos[n].lon, n) for n in ruta
    ]
    if pedido.destino_id == 'TAGANGA':
        dron.ruta_nodos_latlng.insert(1, (11.2650, -74.2250, 'DESVÍO_MARITIMO_IDA'))
    dron.target_idx = 1
    dron.esperando_retorno = False
    dron.status_ui = 'EN VIAJE (IDA)'

    ruta_str = " ➔ ".join(ruta)
    return {
        "status":  "success",
        "message": f"Despacho exitoso a {pedido.destino_nombre}.\nRuta: [ {ruta_str} ]"
    }


# ── TELEMETRÍA WebSocket ──────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await websocket.accept()
    t = 0
    try:
        while True:
            activos = []
            for dron in sis.lista_drones():
                if dron.estado in ['en_vuelo', 'retornando']:
                    if not hasattr(dron, 'lat'):
                        dron.lat, dron.lng = 11.2408, -74.2110

                    if not getattr(dron, 'esperando_retorno', False):
                        dron.consumir_bateria(0.2)

                    if (hasattr(dron, 'ruta_nodos_latlng')
                            and hasattr(dron, 'target_idx')
                            and not getattr(dron, 'esperando_retorno', False)):
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
                                dron.lat += (dlat / dist) * step
                                dron.lng += (dlng / dist) * step
                        else:
                            if dron.estado == 'en_vuelo':
                                dron.esperando_retorno = True
                                dron.status_ui = 'ESPERANDO RETORNO'
                            elif dron.estado == 'retornando':
                                sis.completar_entrega(dron.id_dron)
                                dron.status_ui = dron.estado
                                if hasattr(dron, 'ruta_nodos_latlng'):
                                    del dron.ruta_nodos_latlng

                    elif dron.estado == 'en_vuelo' and not hasattr(dron, 'ruta_nodos_latlng'):
                        dron.lat += math.sin(t + hash(dron.id_dron)) * 0.002
                        dron.lng += math.cos(t + hash(dron.id_dron)) * 0.002

                    if dron.estado in ['en_vuelo', 'retornando']:
                        activos.append({
                            "id":           dron.id_dron,
                            "lat":          dron.lat,
                            "lng":          dron.lng,
                            "battery":      int(dron.bateria),
                            "status":       getattr(dron, 'status_ui', dron.estado),
                            "necesita_mant": dron.necesita_mantenimiento(),
                        })

            await websocket.send_json(activos)
            t += 0.2
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
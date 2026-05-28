# app.py — LogiDrone-UCC  web_tactical
# v7: POST /api/pedidos descuenta stock del inventario AVL

import asyncio
import math
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_padre  = os.path.dirname(directorio_actual)
if directorio_padre not in sys.path:
    sys.path.insert(0, directorio_padre)

from logica.sistema import Sistema, MODELOS_DISPONIBLES
from logica.dron import Dron
from estructuras.grafo import (
    ZIRUMA_CENTRO, ZIRUMA_RADIO_KM,
    TAGANGA_CENTRO, TAGANGA_RADIO_KM,
    ZONAS_EXCLUIDAS
)

app = FastAPI(title="LogiDrone HUD")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sis = Sistema()

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS VISUALES SEGURAS
# ─────────────────────────────────────────────────────────────────────────────

WP_TAGANGA_OESTE = (11.2640, -74.2210, "WP_TAG_O")
WP_ZIRUMA_NO = (11.2350, -74.2400, "WP_ZIR_NO")
WP_ZIRUMA_SO = (11.2100, -74.2500, "WP_ZIR_SO")

_C = {
    "ALMACEN":     (11.2408, -74.2110),
    "CENTRO":      (11.2421, -74.2018),
    "TAGANGA":     (11.2672, -74.1901),
    "BELLO":       (11.2100, -74.2300),
    "RODADERO":    (11.1986, -74.2340),
    "MINCA":       (11.1420, -74.1140),
    "RECARGA_N":   (11.2730, -74.1800),
    "LOGISTICA_R": (11.1920, -74.2380),
    "PLAYA_AMOR":  (11.1547, -74.2260),
}

def _wp(nodo):
    return (_C[nodo][0], _C[nodo][1], nodo)

def _build_rutas_visuales():
    rutas = {}
    rutas[("ALMACEN",   "RECARGA_N")] = [_wp("ALMACEN"),   WP_TAGANGA_OESTE, _wp("RECARGA_N")]
    rutas[("RECARGA_N", "ALMACEN")]   = [_wp("RECARGA_N"), WP_TAGANGA_OESTE, _wp("ALMACEN")]
    rutas[("CENTRO",    "RECARGA_N")] = [_wp("CENTRO"),    WP_TAGANGA_OESTE, _wp("RECARGA_N")]
    rutas[("RECARGA_N", "CENTRO")]    = [_wp("RECARGA_N"), WP_TAGANGA_OESTE, _wp("CENTRO")]
    rutas[("ALMACEN", "BELLO")] = [_wp("ALMACEN"), WP_ZIRUMA_NO, WP_ZIRUMA_SO, _wp("BELLO")]
    rutas[("BELLO", "ALMACEN")] = [_wp("BELLO"), WP_ZIRUMA_SO, WP_ZIRUMA_NO, _wp("ALMACEN")]
    for par in [
        ("ALMACEN",     "CENTRO"),      ("CENTRO",      "ALMACEN"),
        ("ALMACEN",     "PLAYA_AMOR"),  ("PLAYA_AMOR",  "ALMACEN"),
        ("RECARGA_N",   "TAGANGA"),     ("TAGANGA",     "RECARGA_N"),
        ("PLAYA_AMOR",  "RODADERO"),    ("RODADERO",    "PLAYA_AMOR"),
        ("PLAYA_AMOR",  "BELLO"),       ("BELLO",       "PLAYA_AMOR"),
        ("BELLO",       "RODADERO"),    ("RODADERO",    "BELLO"),
        ("RODADERO",    "MINCA"),       ("MINCA",       "RODADERO"),
        ("LOGISTICA_R", "RODADERO"),    ("RODADERO",    "LOGISTICA_R"),
        ("LOGISTICA_R", "PLAYA_AMOR"),  ("PLAYA_AMOR",  "LOGISTICA_R"),
        ("LOGISTICA_R", "BELLO"),       ("BELLO",       "LOGISTICA_R"),
    ]:
        rutas[par] = [_wp(par[0]), _wp(par[1])]
    return rutas

RUTAS_VISUALES = _build_rutas_visuales()

def construir_ruta_visual(ruta_nodos: list) -> list:
    resultado = []
    for i in range(len(ruta_nodos) - 1):
        origen  = ruta_nodos[i]
        destino = ruta_nodos[i + 1]
        segmento = RUTAS_VISUALES.get((origen, destino))
        if segmento is None:
            if origen in _C and destino in _C:
                segmento = [_wp(origen), _wp(destino)]
            else:
                continue
        for wp in segmento:
            if not resultado or resultado[-1] != wp:
                resultado.append(wp)
    return resultado

def _serializar_dron(d: Dron) -> dict:
    necesita_mant = d.necesita_mantenimiento()
    return {
        "id": d.id_dron, "modelo": d.modelo,
        "estado": getattr(d, "status_ui", d.estado),
        "bateria": int(d.bateria), "capacidad_kg": d.capacidad_kg,
        "velocidad_kmh": d.velocidad_kmh, "posicion": d.posicion_actual,
        "necesita_mant": necesita_mant, "ultimo_mant": d.ultimo_mantenimiento(),
        "razon_mant": (f"Batería crítica ({d.bateria}% ≤ 20%)" if d.bateria <= Dron.UMBRAL_BATERIA_CRITICA else "Mant. programado") if necesita_mant else None,
    }

@app.get("/", response_class=HTMLResponse)
async def get_tactical_map(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

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
    return {
        "nodos": nodos_data, "aristas": aristas_data,
        "ziruma": {"centro": ZIRUMA_CENTRO, "radio_km": ZIRUMA_RADIO_KM},
        "taganga_zona": {"centro": TAGANGA_CENTRO, "radio_km": TAGANGA_RADIO_KM}
    }

@app.get("/api/drones")
async def api_listar_drones():
    return {"drones": [_serializar_dron(d) for d in sis.lista_drones()]}

@app.get("/api/drones/mantenimiento")
async def api_drones_mantenimiento():
    return {"drones": [_serializar_dron(d) for d in sis.drones_en_mantenimiento()]}

@app.get("/api/drones/modelos")
async def api_modelos():
    return {"modelos": MODELOS_DISPONIBLES}

@app.post("/api/drones")
async def api_agregar_dron(request: Request):
    data = await request.json()
    dron, msg = sis.agregar_dron(data.get("modelo", "DJI Pro X"), float(data.get("capacidad_kg", 5.0)), float(data.get("velocidad_kmh", 80.0)))
    return {"status": "success", "message": msg, "dron": _serializar_dron(dron)} if dron else {"status": "error", "message": msg}

@app.delete("/api/drones/{id_dron}")
async def api_eliminar_dron(id_dron: str):
    ok, msg = sis.eliminar_dron(id_dron)
    return {"status": "success" if ok else "error", "message": msg}

@app.post("/api/drones/{id_dron}/volar")
async def api_volar(id_dron: str):
    pass

@app.post("/api/drones/{id_dron}/recargar")
async def api_recargar(id_dron: str):
    sis.recargar_dron(id_dron)
    return {"status": "success", "message": f"{id_dron} recargado"}

@app.post("/api/drones/{id_dron}/mantenimiento")
async def api_registrar_mantenimiento(id_dron: str, request: Request):
    data = await request.json()
    sis.registrar_mantenimiento(id_dron, data.get("operacion", "Mant. general"), data["tecnico"], data.get("fecha", "Hoy"), data["observacion"])
    dron = sis.drones.get(id_dron)
    return {
        "status": "success", "message": "Mantenimiento apilado",
        "estado_actual": dron.estado if dron else "?",
        "necesita_mant": dron.necesita_mantenimiento() if dron else False
    }

@app.post("/api/drones/{id_dron}/completar")
async def api_completar_entrega(id_dron: str):
    dron = sis.drones.get(id_dron)
    if dron and getattr(dron, "esperando_retorno", False):
        ruta, _ = sis.mapa.a_estrella(dron.posicion_actual, "ALMACEN", ZONAS_EXCLUIDAS)
        if ruta:
            dron.ruta_visual, dron.target_idx, dron.estado, dron.status_ui, dron.esperando_retorno = construir_ruta_visual(ruta), 1, "retornando", "RETORNANDO", False
            return {"status": "success", "message": f"{id_dron} retornando a la base."}
    sis.completar_entrega(id_dron)
    if dron:
        dron.status_ui = dron.estado
    return {"status": "success", "message": "Viaje completado.", "necesita_mant": dron.necesita_mantenimiento() if dron else False}

@app.get("/api/drones/{id_dron}/pila")
async def api_pila(id_dron: str):
    if id_dron in sis.drones:
        d = sis.drones[id_dron]
        return {"ultimo_registro": d.ultimo_mantenimiento(), "total_registros": len(d.historial_mantenimiento.a_lista()), "historial": []}
    return {"ultimo_registro": "Sin registros", "total_registros": 0, "historial": []}

# ─────────────────────────────────────────────────────────────────────────────
# INVENTARIO
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/inventario/lista")
async def api_inventario_lista():
    return {
        "productos": [
            {
                "id": p.id_producto,
                "nombre": p.nombre,
                "categoria": p.categoria,
                "stock": p.stock,
                "peso": getattr(p, "peso_kg", getattr(p, "peso", 0))
            }
            for p in sis.lista_productos()
        ]
    }

@app.get("/api/inventario/arbol")
async def api_arbol():
    return {
        "nodos": [
            {
                "id": n.get("id"), "padre": n.get("padre"),
                "nivel": n.get("nivel", 0), "pos": n.get("pos", 0),
                "fe": n.get("fe", 0), "nombre": n.get("nombre", "")
            }
            for n in sis.inventario.obtener_nodos_visualizacion()
        ]
    }

@app.post("/api/inventario")
async def api_agregar_inv(request: Request):
    data = await request.json()
    sis.agregar_producto(int(data["id"]), data["nombre"], data["tipo"], int(data["stock"]), float(data["peso"]))
    return {"status": "success"}

@app.delete("/api/inventario/{id_producto}")
async def api_eliminar_producto(id_producto: int):
    sis.eliminar_producto(id_producto)
    return {"status": "success"}

# ─────────────────────────────────────────────────────────────────────────────
# PEDIDOS — v7: descuenta stock del AVL al encolar
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/pedidos")
async def api_crear_pedido(request: Request):
    data = await request.json()

    producto_id = data.get("producto_id")
    cantidad    = int(data.get("cantidad", 1))

    nombre_producto = data.get("tipo", "Suministro")
    stock_restante  = None
    producto        = None

    # ── Verificar stock y descontar ────────────────────────────────────────
    if producto_id:
        producto = sis.buscar_producto(int(producto_id))
        if not producto:
            return {
                "status": "error",
                "message": f"Producto ID {producto_id} no encontrado en inventario."
            }
        if producto.stock < cantidad:
            return {
                "status": "error",
                "message": f"Stock insuficiente: '{producto.nombre}' tiene solo {producto.stock} unidad(es)."
            }
        producto.stock  -= cantidad
        nombre_producto  = f"{producto.nombre} (x{cantidad})"
        stock_restante   = producto.stock

    destino_id     = data["destino"]
    destino_nombre = (
        sis.mapa.nodos[destino_id].nombre
        if destino_id in sis.mapa.nodos
        else "Desconocido"
    )

    sis.crear_pedido(
        destino_id,
        destino_nombre,
        nombre_producto,
        data.get("prioridad", "Media"),
        float(data.get("peso", producto.peso_kg * cantidad if producto else 1.0)),
    )

    return {
        "status": "success",
        "message": f"Pedido encolado: {nombre_producto} → {destino_nombre}",
        "stock_restante": stock_restante,
    }

@app.get("/api/pedidos/frente")
async def api_pedido_frente():
    f = sis.cola_pedidos.ver_frente()
    return {
        "pedido": {
            "id": f.id_pedido, "destino": f.destino_nombre,
            "tipo": f.tipo, "prioridad": f.prioridad, "peso": f.peso_kg
        } if f else None
    }

@app.post("/api/pedidos/despachar")
async def api_despachar_pedido(request: Request):
    data    = await request.json()
    id_dron = data["id_dron"]
    partida = data.get("partida", None)

    if sis.cola_pedidos.esta_vacia():
        return {"status": "error", "message": "Cola vacía."}
    dron = sis.drones.get(id_dron)
    if not dron:
        return {"status": "error", "message": "Dron no encontrado."}
    if dron.necesita_mantenimiento():
        return {"status": "error", "message": f"{id_dron} requiere mant."}

    if partida and partida in sis.mapa.nodos:
        if sis.mapa.nodos[partida].tipo == 'excluido':
            return {"status": "error", "message": "Punto excluido."}
        dron.posicion_actual = partida
        if partida in _C:
            dron.lat, dron.lng = _C[partida]
    else:
        partida = dron.posicion_actual

    pedido = sis.cola_pedidos.desencolar()
    ruta, dist = sis.mapa.a_estrella(partida, pedido.destino_id, ZONAS_EXCLUIDAS)

    if not ruta:
        sis.cola_pedidos.encolar(pedido)
        dron.posicion_actual = "ALMACEN"
        return {"status": "error", "message": f"Sin ruta a {pedido.destino_nombre}."}

    if not dron.asignar_pedido(pedido, ruta):
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error", "message": f"{id_dron} no puede volar."}

    ruta_visual = construir_ruta_visual(ruta)
    dron.lat, dron.lng = ruta_visual[0][0], ruta_visual[0][1]
    dron.ruta_visual, dron.target_idx, dron.esperando_retorno, dron.status_ui = ruta_visual, 1, False, "EN VIAJE"

    return {
        "status": "success",
        "message": f"Despacho exitoso: {id_dron}\nRuta: [ {' ➔ '.join(ruta)} ]"
    }

@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await websocket.accept()
    t = 0
    try:
        while True:
            activos = []
            for dron in sis.lista_drones():
                if dron.estado not in ("en_vuelo", "retornando"):
                    continue
                if not getattr(dron, "esperando_retorno", False):
                    dron.consumir_bateria(0.2)
                ruta_visual = getattr(dron, "ruta_visual", None)
                target_idx  = getattr(dron, "target_idx", 1)

                if ruta_visual and not getattr(dron, "esperando_retorno", False):
                    if target_idx < len(ruta_visual):
                        t_lat, t_lng, t_etiq = ruta_visual[target_idx]
                        dist = math.hypot(t_lat - dron.lat, t_lng - dron.lng)
                        if dist < 0.002:
                            dron.lat, dron.lng, dron.target_idx = t_lat, t_lng, target_idx + 1
                            if t_etiq in sis.mapa.nodos:
                                dron.posicion_actual = t_etiq
                        else:
                            dron.lat += ((t_lat - dron.lat) / dist) * 0.002
                            dron.lng += ((t_lng - dron.lng) / dist) * 0.002
                    else:
                        if dron.estado == "en_vuelo":
                            dron.esperando_retorno, dron.status_ui = True, "ESPERANDO RETORNO"
                        elif dron.estado == "retornando":
                            sis.completar_entrega(dron.id_dron)
                            dron.status_ui = dron.estado
                            if hasattr(dron, "ruta_visual"):
                                del dron.ruta_visual

                if dron.estado in ("en_vuelo", "retornando"):
                    activos.append({
                        "id": dron.id_dron, "lat": dron.lat, "lng": dron.lng,
                        "battery": int(dron.bateria),
                        "status": getattr(dron, "status_ui", dron.estado),
                        "necesita_mant": dron.necesita_mantenimiento()
                    })

            await websocket.send_json(activos)
            t += 0.2
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

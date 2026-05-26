# app.py — LogiDrone-UCC  web_tactical
# Corrección: rutas visuales con waypoints que evitan cruzar Ziruma

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
from estructuras.grafo import ZIRUMA_CENTRO, ZIRUMA_RADIO_KM, ZONAS_EXCLUIDAS

app = FastAPI(title="LogiDrone HUD")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sis = Sistema()

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS VISUALES SEGURAS
# ─────────────────────────────────────────────────────────────────────────────
# Problema: la línea recta entre ciertos pares de nodos cruza el círculo
# visual de Ziruma (radio 0.9 km en el mapa web).
# Segmentos conflictivos (distancia al centro de Ziruma < radio visual):
#   • RECARGA_N ↔ ALMACEN  : 0.26 km
#   • CENTRO    → RECARGA_N: 0.17 km
#
# Solución: waypoint intermedio WP_N_ZIRUMA (11.2680, -74.2050)
#   que está a 1.94 km de Ziruma, bordeando por el norte.
#
# Este diccionario mapea (origen, destino) → lista ordenada de
# coordenadas (lat, lon, etiqueta) que el dron debe seguir visualmente.
# Todos los pares del grafo están cubiertos.

WP_N = (11.2680, -74.2050, "WP_NORTE_ZIRUMA")   # waypoint norte de Ziruma

# Coordenadas reales de cada nodo del grafo
_C = {
    "ALMACEN":   (11.2408, -74.2110),
    "CENTRO":    (11.2421, -74.2018),
    "TAGANGA":   (11.2672, -74.1901),
    "RECARGA_N": (11.2730, -74.1800),
    "RECARGA_S": (11.2150, -74.2200),
    "BELLO":     (11.2300, -74.2210),
    "RODADERO":  (11.1986, -74.2340),
    "MINCA":     (11.1420, -74.1140),
}

def _wp(nodo):
    """Retorna tupla (lat, lon, id) para un nodo del grafo."""
    lat, lon = _C[nodo]
    return (lat, lon, nodo)


def _build_rutas_visuales():
    """
    Construye el diccionario de rutas visuales para cada arista del grafo.
    Las rutas conflictivas incluyen WP_N para rodear Ziruma por el norte.
    """
    rutas = {}

    # ── Rutas que pasan por WP_N (evitan cruzar Ziruma) ──────────────────
    # ALMACEN ↔ RECARGA_N  (0.26 km del centro de Ziruma sin waypoint)
    rutas[("ALMACEN",   "RECARGA_N")] = [_wp("ALMACEN"),   WP_N, _wp("RECARGA_N")]
    rutas[("RECARGA_N", "ALMACEN")]   = [_wp("RECARGA_N"), WP_N, _wp("ALMACEN")]

    # CENTRO ↔ RECARGA_N   (0.17 km del centro de Ziruma sin waypoint)
    rutas[("CENTRO",    "RECARGA_N")] = [_wp("CENTRO"),    WP_N, _wp("RECARGA_N")]
    rutas[("RECARGA_N", "CENTRO")]    = [_wp("RECARGA_N"), WP_N, _wp("CENTRO")]

    # ── Rutas directas (ya están fuera del radio visual) ─────────────────
    for par in [
        ("ALMACEN",   "CENTRO"),   ("CENTRO",    "ALMACEN"),
        ("ALMACEN",   "BELLO"),    ("BELLO",     "ALMACEN"),
        ("ALMACEN",   "RECARGA_S"),("RECARGA_S", "ALMACEN"),
        ("RECARGA_N", "TAGANGA"),  ("TAGANGA",   "RECARGA_N"),
        ("RECARGA_S", "RODADERO"), ("RODADERO",  "RECARGA_S"),
        ("RECARGA_S", "BELLO"),    ("BELLO",     "RECARGA_S"),
        ("BELLO",     "RODADERO"), ("RODADERO",  "BELLO"),
        ("RODADERO",  "MINCA"),    ("MINCA",     "RODADERO"),
    ]:
        o, d = par
        rutas[par] = [_wp(o), _wp(d)]

    return rutas


RUTAS_VISUALES = _build_rutas_visuales()


def construir_ruta_visual(ruta_nodos: list) -> list:
    """
    Dado el path A* (lista de IDs de nodos), devuelve la lista completa
    de waypoints visuales (lat, lon, etiqueta) expandiendo cada segmento
    con los puntos intermedios de RUTAS_VISUALES cuando sean necesarios.
    Elimina duplicados consecutivos.
    """
    resultado = []
    for i in range(len(ruta_nodos) - 1):
        origen  = ruta_nodos[i]
        destino = ruta_nodos[i + 1]
        segmento = RUTAS_VISUALES.get((origen, destino))
        if segmento is None:
            # Segmento no catalogado: ruta directa como fallback
            if origen in _C and destino in _C:
                segmento = [_wp(origen), _wp(destino)]
            else:
                continue

        for wp in segmento:
            # Evitar duplicados consecutivos
            if not resultado or resultado[-1] != wp:
                resultado.append(wp)

    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _serializar_dron(d: Dron) -> dict:
    necesita_mant = d.necesita_mantenimiento()
    return {
        "id":            d.id_dron,
        "modelo":        d.modelo,
        "estado":        getattr(d, "status_ui", d.estado),
        "bateria":       int(d.bateria),
        "capacidad_kg":  d.capacidad_kg,
        "velocidad_kmh": d.velocidad_kmh,
        "posicion":      d.posicion_actual,
        "necesita_mant": necesita_mant,
        "ultimo_mant":   d.ultimo_mantenimiento(),
        "razon_mant": (
            f"Batería crítica ({d.bateria}% ≤ 20%)"
            if d.bateria <= Dron.UMBRAL_BATERIA_CRITICA
            else "Mantenimiento programado"
        ) if necesita_mant else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_tactical_map(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/grafo")
async def api_grafo():
    nodos_data, aristas_data = [], []
    for id_nodo, nodo in sis.mapa.nodos.items():
        nodos_data.append({
            "id": nodo.id_nodo, "nombre": nodo.nombre,
            "lat": nodo.lat,    "lon": nodo.lon, "tipo": nodo.tipo,
        })
        arista = nodo.primera_arista
        while arista is not None:
            destino = sis.mapa.nodos[arista.destino]
            aristas_data.append({
                "origen":  [nodo.lat, nodo.lon],
                "destino": [destino.lat, destino.lon],
                "peso":    arista.peso,
            })
            arista = arista.siguiente

    # El radio visual se reduce a la mitad para que sea coherente
    # con las rutas reales (evita que el círculo cubra nodos destino)
    return {
        "nodos":   nodos_data,
        "aristas": aristas_data,
        "ziruma":  {"centro": ZIRUMA_CENTRO, "radio_km": ZIRUMA_RADIO_KM * 0.5},
    }


# ── DRONES ────────────────────────────────────────────────────────────────────

@app.get("/api/drones")
async def api_listar_drones():
    return {"drones": [_serializar_dron(d) for d in sis.lista_drones()]}


@app.get("/api/drones/mantenimiento")
async def api_drones_mantenimiento():
    criticos = sis.drones_en_mantenimiento()
    return {"drones": [_serializar_dron(d) for d in criticos], "total": len(criticos)}


@app.get("/api/drones/modelos")
async def api_modelos():
    return {"modelos": MODELOS_DISPONIBLES}


@app.post("/api/drones")
async def api_agregar_dron(request: Request):
    data          = await request.json()
    modelo        = data.get("modelo", "DJI Pro X")
    capacidad_kg  = float(data.get("capacidad_kg", 5.0))
    velocidad_kmh = float(data.get("velocidad_kmh", 80.0))
    dron, msg     = sis.agregar_dron(modelo, capacidad_kg, velocidad_kmh)
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
            return {"status": "error",
                    "message": f"{id_dron} no puede volar: requiere mantenimiento"}
        d.estado    = "en_vuelo"
        d.lat, d.lng = 11.2408, -74.2110
        d.status_ui  = "VUELO LIBRE"
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
        data["tecnico"],
        data.get("fecha", "Hoy"),
        data["observacion"],
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
    if dron and getattr(dron, "esperando_retorno", False):
        ruta, _ = sis.mapa.a_estrella(dron.posicion_actual, "ALMACEN", ZONAS_EXCLUIDAS)
        if ruta:
            # ── USAR RUTAS VISUALES SEGURAS para el retorno ──────────────
            dron.ruta_visual       = construir_ruta_visual(ruta)
            dron.target_idx        = 1
            dron.estado            = "retornando"
            dron.status_ui         = "RETORNANDO"
            dron.esperando_retorno = False
            return {"status": "success",
                    "message": f"{id_dron} iniciando retorno a la base."}

    sis.completar_entrega(id_dron)
    if dron:
        dron.status_ui = dron.estado
    msg = "Viaje completado. Dron en base."
    if dron and dron.necesita_mantenimiento():
        msg += f" ⚠ Batería al {dron.bateria}% — requiere mantenimiento."
    return {
        "status":        "success",
        "message":       msg,
        "necesita_mant": dron.necesita_mantenimiento() if dron else False,
    }


@app.get("/api/drones/{id_dron}/pila")
async def api_pila(id_dron: str):
    if id_dron in sis.drones:
        d        = sis.drones[id_dron]
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


# ── INVENTARIO ────────────────────────────────────────────────────────────────

@app.get("/api/inventario/lista")
async def api_inventario_lista():
    productos = []
    for p in sis.lista_productos():
        peso = getattr(p, "peso_kg", getattr(p, "peso", 0))
        productos.append({"id": p.id_producto, "nombre": p.nombre,
                          "stock": p.stock, "peso": peso})
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
    sis.agregar_producto(int(data["id"]), data["nombre"], data["tipo"],
                         int(data["stock"]), float(data["peso"]))
    return {"status": "success"}


@app.delete("/api/inventario/{id_producto}")
async def api_eliminar_producto(id_producto: int):
    try:
        producto = sis.buscar_producto(id_producto)
        if producto is None:
            return {"status": "error",
                    "message": f"Producto {id_producto} no encontrado"}
        sis.eliminar_producto(id_producto)
        return {"status": "success",
                "message": f"Producto {id_producto} eliminado del AVL"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── PEDIDOS ───────────────────────────────────────────────────────────────────

@app.post("/api/pedidos")
async def api_crear_pedido(request: Request):
    data           = await request.json()
    destino_id     = data["destino"]
    destino_nombre = (sis.mapa.nodos[destino_id].nombre
                      if destino_id in sis.mapa.nodos else "Desconocido")
    sis.crear_pedido(destino_id, destino_nombre,
                     data["tipo"], data["prioridad"], float(data["peso"]))
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
    data    = await request.json()
    id_dron = data["id_dron"]

    if sis.cola_pedidos.esta_vacia():
        return {"status": "error", "message": "La cola de pedidos está vacía."}

    dron = sis.drones.get(id_dron)
    if not dron:
        return {"status": "error", "message": "Dron no encontrado."}
    if dron.necesita_mantenimiento():
        razon = (f"Batería al {dron.bateria}% (≤ 20%)"
                 if dron.bateria <= Dron.UMBRAL_BATERIA_CRITICA
                 else "en mantenimiento")
        return {"status": "error",
                "message": f"{id_dron} no puede despacharse: {razon}."}

    pedido        = sis.cola_pedidos.desencolar()
    ruta, distancia = sis.mapa.a_estrella(
        dron.posicion_actual, pedido.destino_id, ZONAS_EXCLUIDAS)

    if ruta is None:
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error",
                "message": f"No se encontró ruta a {pedido.destino_nombre}."}

    ok = dron.asignar_pedido(pedido, ruta)
    if not ok:
        sis.cola_pedidos.encolar(pedido)
        return {"status": "error",
                "message": f"{id_dron} no puede volar (requiere mantenimiento)."}

    # ── RUTA VISUAL SEGURA (con waypoints que evitan cruzar Ziruma) ──────
    ruta_visual = construir_ruta_visual(ruta)
    dron.lat     = ruta_visual[0][0]
    dron.lng     = ruta_visual[0][1]
    dron.ruta_visual       = ruta_visual   # ← lista de (lat, lon, etiqueta)
    dron.target_idx        = 1
    dron.esperando_retorno = False
    dron.status_ui         = "EN VIAJE (IDA)"

    ruta_str = " ➔ ".join(ruta)
    return {
        "status":  "success",
        "message": (f"Despacho exitoso a {pedido.destino_nombre}.\n"
                    f"Ruta: [ {ruta_str} ]"),
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
                if dron.estado not in ("en_vuelo", "retornando"):
                    continue

                if not hasattr(dron, "lat"):
                    dron.lat, dron.lng = 11.2408, -74.2110

                # Consumir batería solo si está moviéndose
                if not getattr(dron, "esperando_retorno", False):
                    dron.consumir_bateria(0.2)

                # ── Movimiento por ruta visual segura ────────────────────
                ruta_visual = getattr(dron, "ruta_visual", None)
                target_idx  = getattr(dron, "target_idx", 1)

                if ruta_visual and not getattr(dron, "esperando_retorno", False):
                    if target_idx < len(ruta_visual):
                        t_lat, t_lng, t_etiqueta = ruta_visual[target_idx]
                        dlat = t_lat - dron.lat
                        dlng = t_lng - dron.lng
                        dist = math.hypot(dlat, dlng)
                        step = 0.002

                        if dist < step:
                            # Llegó al waypoint actual
                            dron.lat, dron.lng = t_lat, t_lng
                            # Actualizar posición lógica solo en nodos reales
                            if t_etiqueta in sis.mapa.nodos:
                                dron.posicion_actual = t_etiqueta
                            dron.target_idx = target_idx + 1
                        else:
                            dron.lat += (dlat / dist) * step
                            dron.lng += (dlng / dist) * step
                    else:
                        # Llegó al final de la ruta visual
                        if dron.estado == "en_vuelo":
                            dron.esperando_retorno = True
                            dron.status_ui         = "ESPERANDO RETORNO"
                        elif dron.estado == "retornando":
                            sis.completar_entrega(dron.id_dron)
                            dron.status_ui = dron.estado
                            if hasattr(dron, "ruta_visual"):
                                del dron.ruta_visual

                elif dron.estado == "en_vuelo" and not ruta_visual:
                    # Fallback: movimiento libre si no tiene ruta asignada
                    dron.lat += math.sin(t + hash(dron.id_dron)) * 0.002
                    dron.lng += math.cos(t + hash(dron.id_dron)) * 0.002

                if dron.estado in ("en_vuelo", "retornando"):
                    activos.append({
                        "id":            dron.id_dron,
                        "lat":           dron.lat,
                        "lng":           dron.lng,
                        "battery":       int(dron.bateria),
                        "status":        getattr(dron, "status_ui", dron.estado),
                        "necesita_mant": dron.necesita_mantenimiento(),
                    })

            await websocket.send_json(activos)
            t += 0.2
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
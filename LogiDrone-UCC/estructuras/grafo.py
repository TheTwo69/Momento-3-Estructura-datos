# Implementacion de Grafo con lista de adyacencia y algoritmo A*
# Modela el mapa aereo de Santa Marta
# Los nodos son puntos clave (almacen, destinos, recargas)
# Las aristas son rutas aereas con peso (distancia aproximada en km)
#
# ZONA ZIRUMA: Obstáculo aéreo ubicado en el centro del triángulo
# formado por Centro Histórico, Taganga y Recarga Norte.
# Los drones NO pueden sobrevolar esta zona.
# Recarga Norte fue reubicada al NORTE-ESTE, fuera del radio de Ziruma.
#
# LOGISTICA_R: Punto de logística secundario en El Rodadero (sur-oeste).
# Actúa como hub de distribución para la zona costera sur.
# Sus rutas (Rodadero, Recarga_S, Bello) están todas al sur-oeste,
# muy alejadas de Ziruma, por lo que A* nunca pasa por allí.

import math


class Arista:
    def __init__(self, destino, peso):
        self.destino = destino   # ID del nodo destino
        self.peso = peso         # distancia en km
        self.siguiente = None    # apuntador a la siguiente arista del nodo


class NodoGrafo:
    def __init__(self, id_nodo, nombre, lat, lon, tipo='destino'):
        self.id_nodo = id_nodo
        self.nombre = nombre
        self.lat = lat           # latitud real de Santa Marta
        self.lon = lon           # longitud real
        self.tipo = tipo         # 'almacen', 'destino', 'recarga', 'logistica', 'excluido'
        self.primera_arista = None  # cabeza de la lista de aristas


class Grafo:
    def __init__(self):
        self.nodos = {}   # diccionario id -> NodoGrafo

    def agregar_nodo(self, id_nodo, nombre, lat, lon, tipo='destino'):
        nodo = NodoGrafo(id_nodo, nombre, lat, lon, tipo)
        self.nodos[id_nodo] = nodo

    # Agrega arista bidireccional entre dos nodos
    def agregar_arista(self, id_origen, id_destino, peso=None):
        if id_origen not in self.nodos or id_destino not in self.nodos:
            return

        # Si no se da peso, se calcula con distancia haversine
        if peso is None:
            peso = self._distancia(id_origen, id_destino)

        self._agregar_arista_simple(id_origen, id_destino, peso)
        self._agregar_arista_simple(id_destino, id_origen, peso)

    def _agregar_arista_simple(self, origen, destino, peso):
        nueva = Arista(destino, peso)
        nodo = self.nodos[origen]
        nueva.siguiente = nodo.primera_arista
        nodo.primera_arista = nueva

    # Distancia real entre dos nodos usando formula haversine
    def _distancia(self, id_a, id_b):
        na = self.nodos[id_a]
        nb = self.nodos[id_b]
        r = 6371  # radio de la tierra en km
        dlat = math.radians(nb.lat - na.lat)
        dlon = math.radians(nb.lon - na.lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(na.lat)) * math.cos(math.radians(nb.lat)) * math.sin(dlon/2)**2
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Heuristica para A*: distancia en linea recta al destino
    def _heuristica(self, id_actual, id_destino):
        return self._distancia(id_actual, id_destino)

    def obtener_vecinos(self, id_nodo):
        vecinos = []
        if id_nodo not in self.nodos:
            return vecinos
        arista = self.nodos[id_nodo].primera_arista
        while arista is not None:
            vecinos.append((arista.destino, arista.peso))
            arista = arista.siguiente
        return vecinos

    # Algoritmo A* para encontrar la ruta mas corta
    # zonas_excluidas: lista de IDs de nodos que no se pueden usar
    def a_estrella(self, id_inicio, id_fin, zonas_excluidas=None):
        if zonas_excluidas is None:
            zonas_excluidas = []

        if id_inicio not in self.nodos or id_fin not in self.nodos:
            return None, float('inf')

        g_score = {id_inicio: 0}
        f_score = {id_inicio: self._heuristica(id_inicio, id_fin)}

        came_from = {}

        abiertos = [(f_score[id_inicio], id_inicio)]
        cerrados = set()

        while abiertos:
            menor_idx = 0
            for i in range(1, len(abiertos)):
                if abiertos[i][0] < abiertos[menor_idx][0]:
                    menor_idx = i
            _, actual = abiertos.pop(menor_idx)

            if actual == id_fin:
                return self._reconstruir_ruta(came_from, actual), g_score[actual]

            cerrados.add(actual)

            for vecino, peso in self.obtener_vecinos(actual):
                if vecino in cerrados:
                    continue
                if vecino in zonas_excluidas:
                    continue

                g_tentativo = g_score[actual] + peso

                if vecino not in g_score or g_tentativo < g_score[vecino]:
                    came_from[vecino] = actual
                    g_score[vecino] = g_tentativo
                    f_score[vecino] = g_tentativo + self._heuristica(vecino, id_fin)
                    abiertos.append((f_score[vecino], vecino))

        return None, float('inf')  # no se encontro ruta

    def _reconstruir_ruta(self, came_from, actual):
        ruta = [actual]
        while actual in came_from:
            actual = came_from[actual]
            ruta.append(actual)
        ruta.reverse()
        return ruta


# Construye el mapa de Santa Marta con coordenadas reales
# CAMBIOS v3:
#   - LOGISTICA_R: nuevo punto de logística en El Rodadero
#                  (lat 11.1920, lon -74.2380), tipo 'logistica'.
#                  Conectado a RODADERO, RECARGA_S y BELLO.
#                  Todas sus rutas discurren por el sur-oeste,
#                  lejos de Ziruma → A* nunca necesita pasar por allí.
#   - Para ir de LOGISTICA_R a TAGANGA, A* sigue:
#       LOGISTICA_R → RECARGA_S → ALMACEN → RECARGA_N → TAGANGA
#       (rodeando Ziruma por el este, igual que antes)
def construir_mapa():
    g = Grafo()

    # ── Nodos principales ──────────────────────────────────────────────────────
    g.agregar_nodo('ALMACEN',     'Almacen Central',          11.2408, -74.2110, 'almacen')
    g.agregar_nodo('RODADERO',    'El Rodadero',              11.1986, -74.2340, 'destino')
    g.agregar_nodo('TAGANGA',     'Taganga',                  11.2672, -74.1901, 'destino')
    g.agregar_nodo('CENTRO',      'Centro Historico',         11.2421, -74.2018, 'destino')
    g.agregar_nodo('BELLO',       'Bello Horizonte',          11.2300, -74.2210, 'destino')
    g.agregar_nodo('MINCA',       'Minca',                    11.1420, -74.1140, 'destino')

    # Punto de logística secundario — sur-oeste, zona Rodadero
    g.agregar_nodo('LOGISTICA_R', 'Punto Logistico Rodadero', 11.1920, -74.2380, 'logistica')

    # RECARGA NORTE → reubicada al NOR-ESTE, bien alejada de Ziruma
    g.agregar_nodo('RECARGA_N',   'Recarga Norte',            11.2730, -74.1800, 'recarga')
    g.agregar_nodo('RECARGA_S',   'Recarga Sur',              11.2150, -74.2200, 'recarga')

    # ── Zonas excluidas (obstáculos aéreos) ────────────────────────────────────
    # ZIRUMA: en el centro del triángulo Centro-Taganga-Recarga Norte
    g.agregar_nodo('ZIRUMA',      'Cerro Ziruma',             11.2530, -74.1960, 'excluido')
    g.agregar_nodo('AEROPUERTO',  'Aeropuerto Simon Bolivar', 11.1196, -74.2260, 'excluido')

    # ── Aristas existentes ─────────────────────────────────────────────────────
    # El dron rodea Ziruma usando RECARGA_N como punto de paso seguro.
    # No existe conexión directa Centro<->Taganga porque esa ruta
    # cruzaría la zona excluida de Ziruma.

    # Desde Almacen
    g.agregar_arista('ALMACEN',   'CENTRO')        # directo, no toca Ziruma
    g.agregar_arista('ALMACEN',   'BELLO')
    g.agregar_arista('ALMACEN',   'RECARGA_S')
    g.agregar_arista('ALMACEN',   'RECARGA_N')     # ruta larga pero segura (con WP_N visual)

    # Recarga Norte (NE) conecta Taganga y Centro bordeando Ziruma
    g.agregar_arista('RECARGA_N', 'TAGANGA')
    g.agregar_arista('RECARGA_N', 'CENTRO')

    # Recarga Sur conecta sur
    g.agregar_arista('RECARGA_S', 'RODADERO')
    g.agregar_arista('RECARGA_S', 'BELLO')

    # Otras conexiones sur
    g.agregar_arista('BELLO',     'RODADERO')
    g.agregar_arista('RODADERO',  'MINCA')

    # ── Aristas del punto logístico en Rodadero ────────────────────────────────
    # Todas en el sur-oeste, sin ninguna proximidad a Ziruma.
    # LOGISTICA_R → RODADERO : vecino inmediato al norte  (~0.75 km)
    # LOGISTICA_R → RECARGA_S: acceso al corredor central (~2.70 km)
    # LOGISTICA_R → BELLO    : conexión directa           (~1.60 km)
    g.agregar_arista('LOGISTICA_R', 'RODADERO')
    g.agregar_arista('LOGISTICA_R', 'RECARGA_S')
    g.agregar_arista('LOGISTICA_R', 'BELLO')

    # NOTA: La ruta LOGISTICA_R → TAGANGA calculada por A* será:
    #   LOGISTICA_R → RECARGA_S → ALMACEN → RECARGA_N → TAGANGA
    # Esto evita Ziruma automáticamente, igual que el resto del grafo.

    return g


# Zonas que los drones NO pueden sobrevolar
ZONAS_EXCLUIDAS = ['AEROPUERTO', 'ZIRUMA']

# Posicion del centro y radio (en grados aprox) de la zona Ziruma para el mapa visual
ZIRUMA_CENTRO = (11.2530, -74.1960)
ZIRUMA_RADIO_KM = 1.8   # radio de la zona de exclusión en km

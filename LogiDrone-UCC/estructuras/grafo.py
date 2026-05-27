import math

class Arista:
    def __init__(self, destino, peso):
        self.destino = destino
        self.peso = peso
        self.siguiente = None

class NodoGrafo:
    def __init__(self, id_nodo, nombre, lat, lon, tipo='destino'):
        self.id_nodo = id_nodo
        self.nombre = nombre
        self.lat = lat
        self.lon = lon
        self.tipo = tipo
        self.primera_arista = None

class Grafo:
    def __init__(self):
        self.nodos = {}

    def agregar_nodo(self, id_nodo, nombre, lat, lon, tipo='destino'):
        self.nodos[id_nodo] = NodoGrafo(id_nodo, nombre, lat, lon, tipo)

    def agregar_arista(self, id_origen, id_destino, peso=None):
        if id_origen not in self.nodos or id_destino not in self.nodos: return
        if peso is None: peso = self._distancia(id_origen, id_destino)
        self._agregar_arista_simple(id_origen, id_destino, peso)
        self._agregar_arista_simple(id_destino, id_origen, peso)

    def _agregar_arista_simple(self, origen, destino, peso):
        nueva = Arista(destino, peso)
        nodo = self.nodos[origen]
        nueva.siguiente = nodo.primera_arista
        nodo.primera_arista = nueva

    def _distancia(self, id_a, id_b):
        na, nb = self.nodos[id_a], self.nodos[id_b]
        dlat, dlon = math.radians(nb.lat - na.lat), math.radians(nb.lon - na.lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(na.lat)) * math.cos(math.radians(nb.lat)) * math.sin(dlon/2)**2
        return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _heuristica(self, id_actual, id_destino):
        return self._distancia(id_actual, id_destino)

    def obtener_vecinos(self, id_nodo):
        vecinos = []
        if id_nodo not in self.nodos: return vecinos
        arista = self.nodos[id_nodo].primera_arista
        while arista:
            vecinos.append((arista.destino, arista.peso))
            arista = arista.siguiente
        return vecinos

    def a_estrella(self, id_inicio, id_fin, zonas_excluidas=None):
        zonas_excluidas = zonas_excluidas or []
        if id_inicio not in self.nodos or id_fin not in self.nodos: return None, float('inf')

        g_score = {id_inicio: 0}
        f_score = {id_inicio: self._heuristica(id_inicio, id_fin)}
        came_from, abiertos, cerrados = {}, [(f_score[id_inicio], id_inicio)], set()

        while abiertos:
            menor_idx = min(range(len(abiertos)), key=lambda i: abiertos[i][0])
            _, actual = abiertos.pop(menor_idx)

            if actual == id_fin: return self._reconstruir_ruta(came_from, actual), g_score[actual]
            cerrados.add(actual)

            for vecino, peso in self.obtener_vecinos(actual):
                if vecino in cerrados or vecino in zonas_excluidas: continue
                g_tentativo = g_score[actual] + peso
                if vecino not in g_score or g_tentativo < g_score[vecino]:
                    came_from[vecino] = actual
                    g_score[vecino] = g_tentativo
                    f_score[vecino] = g_tentativo + self._heuristica(vecino, id_fin)
                    abiertos.append((f_score[vecino], vecino))
        return None, float('inf')

    def _reconstruir_ruta(self, came_from, actual):
        ruta = [actual]
        while actual in came_from:
            actual = came_from[actual]
            ruta.append(actual)
        return ruta[::-1]

def construir_mapa():
    g = Grafo()
    g.agregar_nodo('ALMACEN',     'Almacen Central',          11.2408, -74.2110, 'almacen')
    g.agregar_nodo('CENTRO',      'Centro Historico',         11.2421, -74.2018, 'destino')
    g.agregar_nodo('TAGANGA',     'Taganga',                  11.2672, -74.1901, 'destino')
    # BELLO movido al suroeste real para NO cruzar Ziruma
    g.agregar_nodo('BELLO',       'Bello Horizonte',          11.2100, -74.2300, 'destino')
    g.agregar_nodo('RODADERO',    'El Rodadero',              11.1986, -74.2340, 'destino')
    g.agregar_nodo('MINCA',       'Minca',                    11.1420, -74.1140, 'destino')
    g.agregar_nodo('RECARGA_N',   'Recarga Norte',            11.2730, -74.1800, 'recarga')
    g.agregar_nodo('LOGISTICA_R', 'Punto Logistico Rodadero', 11.1920, -74.2380, 'logistica')
    # NUEVO NODO OFICIAL (Reemplaza a Recarga Sur y Trupillos)
    g.agregar_nodo('PLAYA_AMOR',  'Playa del Amor',           11.1547, -74.2260, 'recarga')

    # Zonas excluidas
    g.agregar_nodo('ZIRUMA',      'Cerro Ziruma',             11.2190, -74.2270, 'excluido')
    g.agregar_nodo('Z_TAGANGA',   'Zona Restringida Taganga', 11.2580, -74.1950, 'excluido')
    g.agregar_nodo('AEROPUERTO',  'Aeropuerto Simon Bolivar', 11.1196, -74.2260, 'excluido')

    g.agregar_arista('ALMACEN',   'CENTRO')
    g.agregar_arista('ALMACEN',   'BELLO')
    g.agregar_arista('ALMACEN',   'PLAYA_AMOR')
    g.agregar_arista('ALMACEN',   'RECARGA_N')
    g.agregar_arista('RECARGA_N', 'TAGANGA')
    g.agregar_arista('RECARGA_N', 'CENTRO')
    g.agregar_arista('PLAYA_AMOR', 'RODADERO')
    g.agregar_arista('PLAYA_AMOR', 'BELLO')
    g.agregar_arista('BELLO',     'RODADERO')
    g.agregar_arista('RODADERO',  'MINCA')
    g.agregar_arista('LOGISTICA_R', 'RODADERO')
    g.agregar_arista('LOGISTICA_R', 'PLAYA_AMOR')
    g.agregar_arista('LOGISTICA_R', 'BELLO')

    return g

ZONAS_EXCLUIDAS = ['AEROPUERTO', 'ZIRUMA', 'Z_TAGANGA']
ZIRUMA_CENTRO = (11.2190, -74.2270)
ZIRUMA_RADIO_KM = 0.6  
TAGANGA_CENTRO = (11.2580, -74.1950)
TAGANGA_RADIO_KM = 0.6

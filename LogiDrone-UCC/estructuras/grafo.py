# Implementacion de Grafo con lista de adyacencia y algoritmo A*
# Modela el mapa aereo de Santa Marta
# Los nodos son puntos clave (almacen, destinos, recargas)
# Las aristas son rutas aereas con peso (distancia aproximada en km)

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
        self.tipo = tipo         # 'almacen', 'destino', 'recarga', 'excluido'
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

        # g_score: costo real desde el inicio
        # f_score: g_score + heuristica (estimado total)
        g_score = {id_inicio: 0}
        f_score = {id_inicio: self._heuristica(id_inicio, id_fin)}

        # Registro de por donde llegamos a cada nodo
        came_from = {}

        # Lista abierta: nodos por explorar [(f_score, id_nodo)]
        # Se implementa manualmente sin usar heapq
        abiertos = [(f_score[id_inicio], id_inicio)]
        cerrados = set()

        while abiertos:
            # Sacamos el nodo con menor f_score manualmente
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
def construir_mapa():
    g = Grafo()

    # Nodos: (id, nombre, lat, lon, tipo)
    g.agregar_nodo('ALMACEN',    'Almacen Central',    11.2408, -74.2110, 'almacen')
    g.agregar_nodo('RODADERO',   'El Rodadero',         11.1986, -74.2340, 'destino')
    g.agregar_nodo('TAGANGA',    'Taganga',              11.2672, -74.1901, 'destino')
    g.agregar_nodo('CENTRO',     'Centro Historico',    11.2421, -74.2018, 'destino')
    g.agregar_nodo('BELLO',      'Bello Horizonte',     11.2300, -74.2210, 'destino')
    g.agregar_nodo('MINCA',      'Minca',               11.1420, -74.1140, 'destino')
    g.agregar_nodo('RECARGA_N',  'Recarga Norte',       11.2550, -74.1980, 'recarga')
    g.agregar_nodo('RECARGA_S',  'Recarga Sur',         11.2150, -74.2200, 'recarga')
    g.agregar_nodo('AEROPUERTO', 'Aeropuerto Simon Bolivar', 11.1196, -74.2260, 'excluido')

    # Aristas (rutas aereas)
    g.agregar_arista('ALMACEN',   'CENTRO')
    g.agregar_arista('ALMACEN',   'BELLO')
    g.agregar_arista('ALMACEN',   'RECARGA_N')
    g.agregar_arista('ALMACEN',   'RECARGA_S')
    g.agregar_arista('RECARGA_N', 'TAGANGA')
    g.agregar_arista('RECARGA_N', 'CENTRO')
    g.agregar_arista('RECARGA_S', 'RODADERO')
    g.agregar_arista('RECARGA_S', 'BELLO')
    g.agregar_arista('BELLO',     'RODADERO')
    g.agregar_arista('CENTRO',    'TAGANGA')
    g.agregar_arista('RODADERO',  'MINCA')

    return g


# Zonas que los drones no pueden sobrevolar
ZONAS_EXCLUIDAS = ['AEROPUERTO']

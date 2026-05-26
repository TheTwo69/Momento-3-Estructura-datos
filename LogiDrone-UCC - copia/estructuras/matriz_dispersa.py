# Implementacion de Matriz Dispersa con lista de nodos enlazados
# Representa la grilla de monitoreo del espacio aereo sobre la bahia
# Solo almacena las celdas ocupadas (donde hay un dron), ahorrando memoria

class NodoMatriz:
    def __init__(self, fila, columna, valor):
        self.fila = fila
        self.columna = columna
        self.valor = valor       # ID del dron que ocupa esta coordenada
        self.siguiente = None    # apuntador al siguiente nodo ocupado


class MatrizDispersa:
    def __init__(self, filas, columnas):
        self.filas = filas
        self.columnas = columnas
        self.cabeza = None   # primer nodo de la lista de celdas ocupadas
        self.total_ocupados = 0

    def _coordenadas_validas(self, fila, columna):
        return 0 <= fila < self.filas and 0 <= columna < self.columnas

    # Asigna un dron a una coordenada del espacio aereo
    def insertar(self, fila, columna, valor):
        if not self._coordenadas_validas(fila, columna):
            return False

        # Si ya existe ese nodo, actualiza el valor
        actual = self.cabeza
        while actual is not None:
            if actual.fila == fila and actual.columna == columna:
                actual.valor = valor
                return True
            actual = actual.siguiente

        # Si no existe, crea un nuevo nodo
        nuevo = NodoMatriz(fila, columna, valor)
        nuevo.siguiente = self.cabeza
        self.cabeza = nuevo
        self.total_ocupados += 1
        return True

    # Elimina un dron de una coordenada (cuando se mueve)
    def eliminar(self, fila, columna):
        actual = self.cabeza
        anterior = None
        while actual is not None:
            if actual.fila == fila and actual.columna == columna:
                if anterior is None:
                    self.cabeza = actual.siguiente
                else:
                    anterior.siguiente = actual.siguiente
                self.total_ocupados -= 1
                return True
            anterior = actual
            actual = actual.siguiente
        return False

    # Obtiene el ID del dron en una coordenada (None si esta vacia)
    def obtener(self, fila, columna):
        actual = self.cabeza
        while actual is not None:
            if actual.fila == fila and actual.columna == columna:
                return actual.valor
            actual = actual.siguiente
        return None

    # Verifica si una coordenada esta ocupada (para evitar colisiones)
    def esta_ocupada(self, fila, columna):
        return self.obtener(fila, columna) is not None

    # Retorna lista de todas las celdas ocupadas (para la GUI)
    def a_lista(self):
        resultado = []
        actual = self.cabeza
        while actual is not None:
            resultado.append({
                'fila': actual.fila,
                'columna': actual.columna,
                'dron': actual.valor
            })
            actual = actual.siguiente
        return resultado

    # Mueve un dron de una coordenada a otra
    def mover_dron(self, fila_origen, col_origen, fila_destino, col_destino):
        dron_id = self.obtener(fila_origen, col_origen)
        if dron_id is None:
            return False
        if self.esta_ocupada(fila_destino, col_destino):
            return False  # colision detectada
        self.eliminar(fila_origen, col_origen)
        self.insertar(fila_destino, col_destino, dron_id)
        return True

# Implementacion de Cola FIFO usando nodos enlazados
# Se usa para gestionar las solicitudes de envio en orden de llegada

class NodoCola:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None  # apuntador al siguiente nodo


class Cola:
    def __init__(self):
        self.frente = None   # primer elemento (el que se despacha primero)
        self.final = None    # ultimo elemento (el ultimo en llegar)
        self.tamano = 0

    def esta_vacia(self):
        return self.frente is None

    # Agrega un pedido al final de la cola
    def encolar(self, dato):
        nuevo = NodoCola(dato)
        if self.esta_vacia():
            self.frente = nuevo
            self.final = nuevo
        else:
            self.final.siguiente = nuevo
            self.final = nuevo
        self.tamano += 1

    # Saca y retorna el primer pedido (FIFO)
    def desencolar(self):
        if self.esta_vacia():
            return None
        dato = self.frente.dato
        self.frente = self.frente.siguiente
        if self.frente is None:
            self.final = None
        self.tamano -= 1
        return dato

    # Muestra el primer pedido sin sacarlo
    def ver_frente(self):
        if self.esta_vacia():
            return None
        return self.frente.dato

    # Retorna todos los elementos como lista (para mostrar en GUI)
    def a_lista(self):
        resultado = []
        actual = self.frente
        while actual is not None:
            resultado.append(actual.dato)
            actual = actual.siguiente
        return resultado

    def __len__(self):
        return self.tamano

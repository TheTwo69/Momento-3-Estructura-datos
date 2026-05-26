# Implementacion de Pila LIFO usando nodos enlazados
# Cada dron tiene su propia pila para registrar su historial de mantenimiento
# La operacion mas reciente siempre queda en la cima

class NodoPila:
    def __init__(self, dato):
        self.dato = dato
        self.anterior = None  # apuntador al nodo debajo en la pila


class Pila:
    def __init__(self):
        self.cima = None   # nodo en la parte superior (el mas reciente)
        self.tamano = 0

    def esta_vacia(self):
        return self.cima is None

    # Agrega un registro de mantenimiento encima de la pila
    def apilar(self, dato):
        nuevo = NodoPila(dato)
        nuevo.anterior = self.cima
        self.cima = nuevo
        self.tamano += 1

    # Saca y retorna el ultimo mantenimiento registrado
    def desapilar(self):
        if self.esta_vacia():
            return None
        dato = self.cima.dato
        self.cima = self.cima.anterior
        self.tamano -= 1
        return dato

    # Muestra el ultimo mantenimiento sin sacarlo
    def ver_cima(self):
        if self.esta_vacia():
            return None
        return self.cima.dato

    # Retorna todos los registros como lista (para mostrar en GUI)
    def a_lista(self):
        resultado = []
        actual = self.cima
        while actual is not None:
            resultado.append(actual.dato)
            actual = actual.anterior
        return resultado

    def __len__(self):
        return self.tamano

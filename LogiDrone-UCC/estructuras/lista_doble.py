# Implementacion de Lista Doblemente Enlazada
# Gestiona la secuencia de entregas asignada a un dron en un viaje
# Permite recorrer hacia adelante y hacia atras, e insertar/eliminar paradas

class NodoLista:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None   # apuntador al nodo de adelante
        self.anterior = None    # apuntador al nodo de atras


class ListaDoble:
    def __init__(self):
        self.cabeza = None   # primera parada del viaje
        self.cola = None     # ultima parada del viaje
        self.tamano = 0

    def esta_vacia(self):
        return self.cabeza is None

    # Agrega una parada al final del viaje
    def agregar_al_final(self, dato):
        nuevo = NodoLista(dato)
        if self.esta_vacia():
            self.cabeza = nuevo
            self.cola = nuevo
        else:
            nuevo.anterior = self.cola
            self.cola.siguiente = nuevo
            self.cola = nuevo
        self.tamano += 1

    # Agrega una parada al inicio del viaje
    def agregar_al_inicio(self, dato):
        nuevo = NodoLista(dato)
        if self.esta_vacia():
            self.cabeza = nuevo
            self.cola = nuevo
        else:
            nuevo.siguiente = self.cabeza
            self.cabeza.anterior = nuevo
            self.cabeza = nuevo
        self.tamano += 1

    # Elimina una parada especifica buscando por dato
    def eliminar(self, dato):
        actual = self.cabeza
        while actual is not None:
            if actual.dato == dato:
                if actual.anterior:
                    actual.anterior.siguiente = actual.siguiente
                else:
                    self.cabeza = actual.siguiente
                if actual.siguiente:
                    actual.siguiente.anterior = actual.anterior
                else:
                    self.cola = actual.anterior
                self.tamano -= 1
                return True
            actual = actual.siguiente
        return False

    # Recorre hacia adelante y retorna lista
    def a_lista_adelante(self):
        resultado = []
        actual = self.cabeza
        while actual is not None:
            resultado.append(actual.dato)
            actual = actual.siguiente
        return resultado

    # Recorre hacia atras y retorna lista
    def a_lista_atras(self):
        resultado = []
        actual = self.cola
        while actual is not None:
            resultado.append(actual.dato)
            actual = actual.anterior
        return resultado

    def __len__(self):
        return self.tamano

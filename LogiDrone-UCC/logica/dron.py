# Clase que representa un dron de la flota
# Usa la Pila para su historial de mantenimiento
# y la Lista Doble para la secuencia de entregas del viaje actual

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estructuras.pila import Pila
from estructuras.lista_doble import ListaDoble


class RegistroMantenimiento:
    def __init__(self, operacion, tecnico, fecha, observacion):
        self.operacion = operacion
        self.tecnico = tecnico
        self.fecha = fecha
        self.observacion = observacion

    def __str__(self):
        return f"{self.fecha} | {self.operacion} | {self.tecnico}"


class Dron:
    ESTADOS = ['en_espera', 'en_vuelo', 'bateria_baja', 'mantenimiento']

    def __init__(self, id_dron, modelo):
        self.id_dron = id_dron
        self.modelo = modelo
        self.bateria = 100           # porcentaje de bateria
        self.estado = 'en_espera'
        self.posicion_actual = 'ALMACEN'  # ID del nodo donde esta

        # Coordenadas en la matriz dispersa
        self.coord_fila = 0
        self.coord_col = 0

        # Pila LIFO para historial de mantenimiento
        self.historial_mantenimiento = Pila()

        # Lista doble para la ruta de entregas del viaje actual
        self.ruta_viaje = ListaDoble()

        # Ruta calculada por A* (lista de IDs de nodos)
        self.ruta_astar = []
        self.pedido_actual = None

    def registrar_mantenimiento(self, operacion, tecnico, fecha, observacion):
        registro = RegistroMantenimiento(operacion, tecnico, fecha, observacion)
        self.historial_mantenimiento.apilar(registro)
        if self.estado == 'mantenimiento':
            self.estado = 'en_espera'

    def ultimo_mantenimiento(self):
        reg = self.historial_mantenimiento.ver_cima()
        if reg:
            return str(reg)
        return 'Sin registros'

    def asignar_pedido(self, pedido, ruta_nodos):
        self.pedido_actual = pedido
        self.ruta_astar = ruta_nodos
        self.estado = 'en_vuelo'
        pedido.estado = 'en_camino'
        # Carga la ruta en la lista doble
        self.ruta_viaje = ListaDoble()
        for nodo_id in ruta_nodos:
            self.ruta_viaje.agregar_al_final(nodo_id)

    def consumir_bateria(self, cantidad):
        self.bateria -= cantidad
        if self.bateria < 0:
            self.bateria = 0
        if self.bateria <= 20:
            self.estado = 'bateria_baja'

    def recargar(self):
        self.bateria = 100
        if self.estado == 'bateria_baja':
            self.estado = 'en_espera'

    def completar_entrega(self):
        if self.pedido_actual:
            self.pedido_actual.estado = 'entregado'
            self.pedido_actual = None
        self.ruta_astar = []
        self.ruta_viaje = ListaDoble()
        self.estado = 'en_espera'
        self.posicion_actual = 'ALMACEN'
        self.consumir_bateria(15)  # el viaje consume bateria

    def necesita_mantenimiento(self):
        return self.estado == 'mantenimiento'

    def __str__(self):
        return f"{self.id_dron} ({self.modelo}) - {self.estado} - Bateria: {self.bateria}%"

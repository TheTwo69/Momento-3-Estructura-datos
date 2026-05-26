# logica/dron.py — LogiDrone-UCC
# Clase que representa un dron de la flota.
# Usa la Pila para historial de mantenimiento
# y la Lista Doble para la secuencia de entregas del viaje actual.

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estructuras.pila import Pila
from estructuras.lista_doble import ListaDoble


class RegistroMantenimiento:
    def __init__(self, operacion, tecnico, fecha, observacion):
        self.operacion  = operacion
        self.tecnico    = tecnico
        self.fecha      = fecha
        self.observacion = observacion

    def __str__(self):
        return f"{self.fecha} | {self.operacion} | {self.tecnico}"


class Dron:
    ESTADOS = ['en_espera', 'en_vuelo', 'bateria_baja', 'mantenimiento']

    # Umbral a partir del cual el dron requiere mantenimiento automático
    UMBRAL_BATERIA_CRITICA = 20

    def __init__(self, id_dron, modelo, capacidad_kg=5.0, velocidad_kmh=80.0):
        self.id_dron       = id_dron
        self.modelo        = modelo
        self.capacidad_kg  = float(capacidad_kg)
        self.velocidad_kmh = float(velocidad_kmh)
        self.bateria       = 100        # porcentaje
        self.estado        = 'en_espera'
        self.posicion_actual = 'ALMACEN'

        # Coordenadas en la matriz dispersa
        self.coord_fila = 0
        self.coord_col  = 0

        # Pila LIFO — historial de mantenimiento
        self.historial_mantenimiento = Pila()

        # Lista doble — ruta de entregas del viaje actual
        self.ruta_viaje = ListaDoble()

        # Ruta calculada por A* (lista de IDs de nodos)
        self.ruta_astar   = []
        self.pedido_actual = None

    # ── BATERÍA ───────────────────────────────────────────────────────────────

    def consumir_bateria(self, cantidad):
        self.bateria -= cantidad
        if self.bateria < 0:
            self.bateria = 0
        self._evaluar_estado_bateria()

    def _evaluar_estado_bateria(self):
        """
        Regla central:
          · bateria <= UMBRAL_BATERIA_CRITICA
              - En tierra  → estado = 'mantenimiento'
              - En vuelo   → estado = 'bateria_baja' (aterriza y luego pasa a mant.)
        """
        if self.bateria <= self.UMBRAL_BATERIA_CRITICA:
            if self.estado == 'en_vuelo':
                self.estado = 'bateria_baja'
            else:
                self.estado = 'mantenimiento'

    def recargar(self):
        self.bateria = 100
        if self.estado in ('bateria_baja', 'mantenimiento'):
            self.estado = 'en_espera'

    # ── MANTENIMIENTO ─────────────────────────────────────────────────────────

    def registrar_mantenimiento(self, operacion, tecnico, fecha, observacion):
        registro = RegistroMantenimiento(operacion, tecnico, fecha, observacion)
        self.historial_mantenimiento.apilar(registro)
        # Sale de mantenimiento solo si la batería también está bien
        if self.estado == 'mantenimiento' and self.bateria > self.UMBRAL_BATERIA_CRITICA:
            self.estado = 'en_espera'

    def ultimo_mantenimiento(self):
        reg = self.historial_mantenimiento.ver_cima()
        return str(reg) if reg else 'Sin registros'

    def necesita_mantenimiento(self):
        return self.estado == 'mantenimiento' or self.bateria <= self.UMBRAL_BATERIA_CRITICA

    # ── PEDIDOS / VUELO ───────────────────────────────────────────────────────

    def asignar_pedido(self, pedido, ruta_nodos):
        if self.necesita_mantenimiento():
            return False   # no puede volar
        self.pedido_actual = pedido
        self.ruta_astar    = ruta_nodos
        self.estado        = 'en_vuelo'
        pedido.estado      = 'en_camino'
        self.ruta_viaje    = ListaDoble()
        for nodo_id in ruta_nodos:
            self.ruta_viaje.agregar_al_final(nodo_id)
        return True

    def completar_entrega(self):
        if self.pedido_actual:
            self.pedido_actual.estado = 'entregado'
            self.pedido_actual = None
        self.ruta_astar  = []
        self.ruta_viaje  = ListaDoble()
        self.consumir_bateria(15)   # el viaje consume batería
        self.posicion_actual = 'ALMACEN'
        if self.estado not in ('mantenimiento', 'bateria_baja'):
            self.estado = 'en_espera'

    # ── REPR ──────────────────────────────────────────────────────────────────

    def __str__(self):
        alerta = ' ⚠ MANTENIMIENTO REQUERIDO' if self.necesita_mantenimiento() else ''
        return (f"{self.id_dron} ({self.modelo}) — {self.estado} "
                f"— Batería: {self.bateria}%{alerta}")
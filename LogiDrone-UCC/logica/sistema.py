# Sistema central de LogiDrone-UCC
# Orquesta el mapa, los drones, los pedidos y el inventario
# Es el unico punto de contacto entre la GUI y la logica

import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estructuras.cola import Cola
from estructuras.avl import ArbolAVL
from estructuras.matriz_dispersa import MatrizDispersa
from estructuras.grafo import construir_mapa, ZONAS_EXCLUIDAS
from logica.dron import Dron
from logica.pedido import Pedido
from logica.producto import Producto


class Sistema:
    def __init__(self):
        # Mapa aereo de Santa Marta
        self.mapa = construir_mapa()

        # Cola de pedidos pendientes
        self.cola_pedidos = Cola()

        # Inventario de productos
        self.inventario = ArbolAVL()

        # Grilla de monitoreo: 20 filas x 20 columnas
        self.espacio_aereo = MatrizDispersa(20, 20)

        # Flota de drones
        self.drones = {}
        self._inicializar_flota()

        # Inventario inicial de muestra
        self._cargar_inventario_inicial()

        # Contador para IDs de pedidos
        self._contador_pedidos = 1

        # Historial de entregas completadas
        self.entregas_completadas = []

    def _inicializar_flota(self):
        flota_inicial = [
            ('D-01', 'DJI Pro X'),
            ('D-02', 'DJI Pro X'),
            ('D-03', 'Phantom 4'),
            ('D-04', 'Phantom 4'),
        ]
        posiciones = [(2, 2), (2, 4), (2, 6), (2, 8)]
        for (id_d, modelo), (f, c) in zip(flota_inicial, posiciones):
            d = Dron(id_d, modelo)
            d.coord_fila = f
            d.coord_col = c
            self.drones[id_d] = d
            self.espacio_aereo.insertar(f, c, id_d)

        # Mantenimientos iniciales de muestra
        self.drones['D-01'].registrar_mantenimiento('Limpieza de salitre', 'Carlos M.', '2026-05-20', 'Exposicion brisa marina')
        self.drones['D-01'].registrar_mantenimiento('Cambio de bateria',   'Luis R.',   '2026-05-15', 'Bateria al 10% en vuelo')
        self.drones['D-02'].registrar_mantenimiento('Calibracion GPS',     'Ana G.',    '2026-05-18', 'Desvio detectado')
        self.drones['D-03'].bateria = 18
        self.drones['D-03'].estado = 'bateria_baja'
        self.drones['D-04'].estado = 'mantenimiento'
        self.drones['D-04'].bateria = 60

    def _cargar_inventario_inicial(self):
        productos = [
            Producto(20,  'Adrenalina 1mg',    'Medicamento', 12,  0.1),
            Producto(30,  'Ibuprofeno 400mg',  'Medicamento', 50,  0.2),
            Producto(40,  'Tornillo M6',        'Repuesto',   200,  0.05),
            Producto(50,  'Suero oral 500ml',   'Medicamento', 30,  0.5),
            Producto(60,  'Cable HDMI 1m',      'Repuesto',     8,  0.3),
            Producto(70,  'Amoxicilina 500mg',  'Medicamento', 45,  0.15),
            Producto(80,  'Bateria DJI Pro',    'Repuesto',     5,  0.4),
        ]
        for p in productos:
            self.inventario.insertar(p)

    # ── PEDIDOS ────────────────────────────────────────────────

    def crear_pedido(self, destino_id, destino_nombre, tipo, prioridad, peso_kg):
        id_pedido = f'#{self._contador_pedidos:03d}'
        self._contador_pedidos += 1
        pedido = Pedido(id_pedido, destino_id, destino_nombre, tipo, prioridad, peso_kg)
        pedido.hora_ingreso = datetime.datetime.now().strftime('%H:%M')
        self.cola_pedidos.encolar(pedido)
        return pedido

    def despachar_siguiente(self):
        if self.cola_pedidos.esta_vacia():
            return None, 'No hay pedidos en cola'

        dron_libre = self._buscar_dron_disponible()
        if dron_libre is None:
            return None, 'No hay drones disponibles'

        pedido = self.cola_pedidos.desencolar()

        # Calcula ruta con A*
        ruta, distancia = self.mapa.a_estrella(
            dron_libre.posicion_actual,
            pedido.destino_id,
            ZONAS_EXCLUIDAS
        )

        if ruta is None:
            # Devuelve el pedido a la cola si no hay ruta
            self.cola_pedidos.encolar(pedido)
            return None, f'No se encontro ruta hacia {pedido.destino_nombre}'

        dron_libre.asignar_pedido(pedido, ruta)
        return dron_libre, f'Dron {dron_libre.id_dron} despachado hacia {pedido.destino_nombre}'

    def completar_entrega(self, id_dron):
        if id_dron not in self.drones:
            return False
        dron = self.drones[id_dron]
        if dron.pedido_actual:
            self.entregas_completadas.append(str(dron.pedido_actual))
        dron.completar_entrega()
        return True

    def _buscar_dron_disponible(self):
        for dron in self.drones.values():
            if dron.estado == 'en_espera' and dron.bateria > 20:
                return dron
        return None

    # ── INVENTARIO ─────────────────────────────────────────────

    def agregar_producto(self, id_p, nombre, categoria, stock, peso):
        producto = Producto(id_p, nombre, categoria, stock, peso)
        self.inventario.insertar(producto)
        return producto

    def buscar_producto(self, id_p):
        return self.inventario.buscar(int(id_p))

    def eliminar_producto(self, id_p):
        self.inventario.eliminar(int(id_p))

    def lista_productos(self):
        return self.inventario.a_lista()

    # ── DRONES ─────────────────────────────────────────────────

    def registrar_mantenimiento(self, id_dron, operacion, tecnico, fecha, observacion):
        if id_dron not in self.drones:
            return False
        self.drones[id_dron].registrar_mantenimiento(operacion, tecnico, fecha, observacion)
        return True

    def recargar_dron(self, id_dron):
        if id_dron in self.drones:
            self.drones[id_dron].recargar()

    def lista_drones(self):
        return list(self.drones.values())

    # ── ESPACIO AEREO ───────────────────────────────────────────

    def mover_dron_matriz(self, id_dron, nueva_fila, nueva_col):
        if id_dron not in self.drones:
            return False, 'Dron no encontrado'
        dron = self.drones[id_dron]
        resultado = self.espacio_aereo.mover_dron(
            dron.coord_fila, dron.coord_col,
            nueva_fila, nueva_col
        )
        if resultado:
            dron.coord_fila = nueva_fila
            dron.coord_col = nueva_col
            return True, 'Movimiento exitoso'
        return False, 'Colision detectada o coordenadas invalidas'

    # ── INFO DEL MAPA ───────────────────────────────────────────

    def info_nodo(self, id_nodo):
        if id_nodo not in self.mapa.nodos:
            return None
        nodo = self.mapa.nodos[id_nodo]
        drones_ahi = [d for d in self.drones.values() if d.posicion_actual == id_nodo]
        return {
            'id': nodo.id_nodo,
            'nombre': nodo.nombre,
            'tipo': nodo.tipo,
            'lat': nodo.lat,
            'lon': nodo.lon,
            'drones': [d.id_dron for d in drones_ahi],
            'conexiones': len(self.mapa.obtener_vecinos(id_nodo))
        }

    def calcular_ruta(self, origen, destino):
        return self.mapa.a_estrella(origen, destino, ZONAS_EXCLUIDAS)

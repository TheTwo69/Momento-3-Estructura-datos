# Ventana principal: Panel de Control — LogiDrone-UCC v2
# Mapa aereo mejorado con:
#   - Zona Ziruma visible como obstáculo central (entre Centro, Taganga y Recarga Norte)
#   - Recarga Norte reubicada fuera del radio de Ziruma
#   - Animacion del recorrido del dron en tiempo real (pulso animado sobre la ruta)
#   - Mapa mas claro, geografico, con etiquetas mejoradas

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import math

BG       = '#0f1415'
PANEL    = '#13191a'
CARD     = '#192021'
BORDER   = '#283435'
TEAL     = '#04c7b5'
GREEN    = '#48d86e'
RED      = '#ef4444'
AMBER    = '#f59e0b'
WHITE    = '#edf1f0'
GRAY     = '#809190'
PURPLE   = '#a855f7'

# ── Posiciones de nodos en el canvas (640x580 base) ──────────────────────────
# Reorganizadas para reflejar la nueva ubicación de Ziruma y Recarga Norte
NODO_POS = {
    'ALMACEN':   (310, 330),   # centro del mapa
    'RODADERO':  (140, 470),   # sur-oeste (playa)
    'TAGANGA':   (530, 120),   # nor-este (bahía)
    'CENTRO':    (430, 310),   # este-centro
    'BELLO':     (175, 330),   # oeste
    'MINCA':     (210, 510),   # sur-este (sierra)
    'RECARGA_N': (580, 200),   # nor-este, FUERA de Ziruma (nueva posición)
    'RECARGA_S': (260, 420),   # sur-centro
    # Ziruma: centro del triángulo Centro-Taganga-Recarga Norte vieja
    'ZIRUMA':    (490, 195),   # zona excluida visual
    'AEROPUERTO': (155, 560),  # sur (fuera del mapa operativo)
}

# Centro y radio visual de la zona Ziruma en el canvas
ZIRUMA_CANVAS = (490, 195)
ZIRUMA_RADIO  = 52   # radio en pixeles del canvas (580 base)

NODO_COLOR = {
    'almacen':  TEAL,
    'destino':  GREEN,
    'recarga':  AMBER,
    'excluido': RED,
}

COLOR_ESTADO = {
    'en_vuelo':    GREEN,
    'en_espera':   TEAL,
    'bateria_baja': RED,
    'mantenimiento': AMBER,
}


class VentanaPrincipal(tk.Tk):
    def __init__(self, sistema):
        super().__init__()
        self.sistema = sistema
        self.title('LogiDrone-UCC — Operacion Bahia Santa Marta')
        self.geometry('1350x780')
        self.configure(bg=BG)
        self.resizable(True, True)

        self.nodo_seleccionado = None
        self.ruta_activa = []          # ruta A* activa para dibujar
        self.ruta_dron_activo = None   # dron cuya ruta se anima

        # Animación de la ruta del dron
        self._anim_paso = 0            # posicion del "pulso" animado
        self._anim_activa = False

        # Referencias a widgets dinámicos
        self._widgets_drones = {}
        self._widgets_cola   = []

        self._construir_ui()
        self._inicializar_widgets_dinamicos()
        self._tick()

    # ── CONSTRUCCION ──────────────────────────────────────────────────────────

    def _construir_ui(self):
        topbar = tk.Frame(self, bg=PANEL, height=48)
        topbar.pack(fill=tk.X, side=tk.TOP)
        topbar.pack_propagate(False)

        tk.Label(topbar, text='  LogiDrone-UCC', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(topbar, text=' | Bahia Santa Marta', bg=PANEL,
                 fg=GRAY, font=('Segoe UI', 10)).pack(side=tk.LEFT)

        from gui.ventana_pedido import VentanaPedido
        from gui.ventana_dron import VentanaDron
        from gui.ventana_inventario import VentanaInventario

        for txt, cmd in [
            ('Pedidos',     lambda: VentanaPedido(self, self.sistema, self.actualizar)),
            ('Drones',      lambda: VentanaDron(self, self.sistema, self.actualizar)),
            ('Inventario',  lambda: VentanaInventario(self, self.sistema)),
        ]:
            tk.Button(topbar, text=txt, bg=PANEL, fg=GRAY, relief=tk.FLAT,
                      font=('Segoe UI', 10), cursor='hand2',
                      command=cmd).pack(side=tk.LEFT, padx=8)

        self.lbl_hora = tk.Label(topbar, text='', bg=PANEL, fg=GRAY,
                                  font=('Segoe UI', 10))
        self.lbl_hora.pack(side=tk.RIGHT, padx=12)

        tk.Frame(self, bg=TEAL, height=2).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=BG)
        contenido.pack(fill=tk.BOTH, expand=True)

        self.panel_izq = tk.Frame(contenido, bg=PANEL, width=250)
        self.panel_izq.pack(side=tk.LEFT, fill=tk.Y)
        self.panel_izq.pack_propagate(False)
        self._construir_panel_izq()

        self.frame_mapa = tk.Frame(contenido, bg=BG)
        self.frame_mapa.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._construir_mapa()

        self.panel_der = tk.Frame(contenido, bg=PANEL, width=270)
        self.panel_der.pack(side=tk.RIGHT, fill=tk.Y)
        self.panel_der.pack_propagate(False)
        self._construir_panel_der()

    def _construir_panel_izq(self):
        tk.Label(self.panel_izq, text='FLOTA DE DRONES', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))

        self.frame_drones = tk.Frame(self.panel_izq, bg=PANEL)
        self.frame_drones.pack(fill=tk.X, padx=6)

        tk.Frame(self.panel_izq, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=8)

        cola_hdr = tk.Frame(self.panel_izq, bg=PANEL)
        cola_hdr.pack(fill=tk.X, padx=10)
        tk.Label(cola_hdr, text='COLA DE PEDIDOS', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
        self.lbl_cola_count = tk.Label(cola_hdr, text='0', bg=TEAL, fg=BG,
                                        font=('Segoe UI', 8, 'bold'), padx=5)
        self.lbl_cola_count.pack(side=tk.RIGHT)

        self.frame_cola = tk.Frame(self.panel_izq, bg=PANEL)
        self.frame_cola.pack(fill=tk.X, padx=6, pady=(4, 0))

        tk.Frame(self.panel_izq, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=8)

        tk.Button(self.panel_izq, text='⚡  Despachar siguiente', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._despachar).pack(fill=tk.X, padx=8, pady=2)

        from gui.ventana_pedido import VentanaPedido
        tk.Button(self.panel_izq, text='+ Nuevo pedido', bg=CARD, fg=TEAL,
                  font=('Segoe UI', 10), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=TEAL,
                  command=lambda: VentanaPedido(self, self.sistema, self.actualizar)
                  ).pack(fill=tk.X, padx=8, pady=2)

    def _construir_mapa(self):
        lbl_frame = tk.Frame(self.frame_mapa, bg=BG)
        lbl_frame.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(lbl_frame, text='Mapa aereo — Santa Marta',
                 bg=BG, fg=WHITE, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        tk.Label(lbl_frame, text='Clic en un nodo para ver detalles y calcular ruta A*',
                 bg=BG, fg=GRAY, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)

        self.canvas = tk.Canvas(self.frame_mapa, bg='#07131a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.canvas.bind('<Configure>', lambda e: self._redibujar_mapa())
        self.canvas.bind('<Button-1>', self._click_canvas)

    def _construir_panel_der(self):
        tk.Label(self.panel_der, text='DETALLE DEL NODO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 4))

        self.frame_detalle = tk.Frame(self.panel_der, bg=CARD, padx=8, pady=8)
        self.frame_detalle.pack(fill=tk.X, padx=8)
        self.lbl_detalle = tk.Label(self.frame_detalle,
                                     text='Selecciona un nodo\nen el mapa',
                                     bg=CARD, fg=GRAY,
                                     font=('Segoe UI', 10), justify=tk.LEFT)
        self.lbl_detalle.pack(anchor='w')

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        # Panel de ruta activa
        tk.Label(self.panel_der, text='RUTA A* ACTIVA', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        self.frame_ruta = tk.Frame(self.panel_der, bg=CARD, padx=8, pady=6)
        self.frame_ruta.pack(fill=tk.X, padx=8, pady=(2, 0))
        self.lbl_ruta = tk.Label(self.frame_ruta, text='Sin ruta activa',
                                  bg=CARD, fg=GRAY, font=('Segoe UI', 9),
                                  justify=tk.LEFT, wraplength=220)
        self.lbl_ruta.pack(anchor='w')

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        tk.Label(self.panel_der, text='ESPACIO AEREO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        tk.Label(self.panel_der, text='Matriz de monitoreo de drones',
                 bg=PANEL, fg=GRAY, font=('Segoe UI', 8)).pack(anchor='w', padx=10)

        self.canvas_matriz = tk.Canvas(self.panel_der, bg=CARD,
                                        width=240, height=110, highlightthickness=0)
        self.canvas_matriz.pack(padx=8, pady=4)

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        tk.Label(self.panel_der, text='ALERTAS', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        self.frame_alertas = tk.Frame(self.panel_der, bg=PANEL)
        self.frame_alertas.pack(fill=tk.X, padx=8, pady=2)

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=6)

        tk.Label(self.panel_der, text='RESUMEN', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        self.frame_resumen = tk.Frame(self.panel_der, bg=PANEL)
        self.frame_resumen.pack(fill=tk.X, padx=10)

    # ── WIDGETS DINAMICOS ─────────────────────────────────────────────────────

    def _inicializar_widgets_dinamicos(self):
        for dron in self.sistema.drones.values():
            card = tk.Frame(self.frame_drones, bg=CARD, pady=4)
            card.pack(fill=tk.X, pady=2)
            barra = tk.Frame(card, bg=TEAL, width=3)
            barra.pack(side=tk.LEFT, fill=tk.Y)
            info = tk.Frame(card, bg=CARD, padx=6)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fila1 = tk.Frame(info, bg=CARD)
            fila1.pack(fill=tk.X)
            lbl_id  = tk.Label(fila1, text=dron.id_dron, bg=CARD, fg=WHITE,
                                font=('Segoe UI', 11, 'bold'))
            lbl_id.pack(side=tk.LEFT)
            lbl_bat = tk.Label(fila1, text='', bg=CARD, fg=GRAY,
                                font=('Segoe UI', 9))
            lbl_bat.pack(side=tk.RIGHT)
            lbl_est = tk.Label(info, text='', bg=CARD, fg=TEAL,
                                font=('Segoe UI', 9))
            lbl_est.pack(anchor='w')
            self._widgets_drones[dron.id_dron] = {
                'barra': barra, 'lbl_bat': lbl_bat, 'lbl_est': lbl_est
            }

        for _ in range(5):
            card = tk.Frame(self.frame_cola, bg=CARD, pady=3, padx=6)
            card.pack(fill=tk.X, pady=1)
            fila = tk.Frame(card, bg=CARD)
            fila.pack(fill=tk.X)
            lbl_id   = tk.Label(fila, text='', bg=CARD, fg=TEAL,
                                 font=('Segoe UI', 10, 'bold'))
            lbl_id.pack(side=tk.LEFT)
            lbl_dest = tk.Label(fila, text='', bg=CARD, fg=WHITE,
                                 font=('Segoe UI', 10))
            lbl_dest.pack(side=tk.LEFT, padx=4)
            lbl_pri  = tk.Label(fila, text='', bg=CARD, fg=GRAY,
                                 font=('Segoe UI', 8, 'bold'))
            lbl_pri.pack(side=tk.RIGHT)
            self._widgets_cola.append({
                'card': card, 'lbl_id': lbl_id,
                'lbl_dest': lbl_dest, 'lbl_pri': lbl_pri
            })

        self._widgets_alertas = []
        for _ in range(4):
            f = tk.Frame(self.frame_alertas, bg=CARD, pady=4, padx=6)
            f.pack(fill=tk.X, pady=1)
            barra = tk.Frame(f, bg=RED, width=3)
            barra.pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(f, text='', bg=CARD, fg=RED, font=('Segoe UI', 9))
            lbl.pack(side=tk.LEFT)
            self._widgets_alertas.append({'frame': f, 'barra': barra, 'lbl': lbl})
            f.pack_forget()

        stats_labels = ['Entregas completadas', 'Pedidos en cola', 'Drones activos']
        self._widgets_resumen = []
        for label in stats_labels:
            f = tk.Frame(self.frame_resumen, bg=PANEL)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=label, bg=PANEL, fg=GRAY,
                     font=('Segoe UI', 9)).pack(side=tk.LEFT)
            lbl_val = tk.Label(f, text='0', bg=PANEL, fg=WHITE,
                                font=('Segoe UI', 11, 'bold'))
            lbl_val.pack(side=tk.RIGHT)
            self._widgets_resumen.append(lbl_val)

    # ── CICLO DE ACTUALIZACION ─────────────────────────────────────────────────

    def _tick(self):
        self._actualizar_drones()
        self._actualizar_cola()
        self._actualizar_alertas()
        self._actualizar_resumen()
        self._actualizar_matriz()
        self.lbl_hora.config(text=datetime.datetime.now().strftime('%H:%M:%S'))

        # Anima el pulso sobre la ruta activa
        if self._anim_activa and self.ruta_activa:
            self._anim_paso = (self._anim_paso + 1) % max(1, len(self.ruta_activa))
            self._redibujar_mapa()

        self.after(800, self._tick)

    def actualizar(self):
        self._actualizar_drones()
        self._actualizar_cola()
        self._actualizar_alertas()
        self._actualizar_resumen()
        self._actualizar_matriz()
        self._redibujar_mapa()

    def _actualizar_drones(self):
        for dron in self.sistema.drones.values():
            w = self._widgets_drones.get(dron.id_dron)
            if not w:
                continue
            color = COLOR_ESTADO.get(dron.estado, GRAY)
            w['barra'].config(bg=color)
            w['lbl_bat'].config(text=f'{dron.bateria}%',
                                 fg=RED if dron.bateria <= 20 else GRAY)
            w['lbl_est'].config(
                text=dron.estado.replace('_', ' ').title(), fg=color)

    def _actualizar_cola(self):
        pedidos = self.sistema.cola_pedidos.a_lista()
        self.lbl_cola_count.config(text=str(len(pedidos)))
        COLOR_PRI = {'ALTA': RED, 'MEDIA': AMBER, 'BAJA': GREEN}
        for i, w in enumerate(self._widgets_cola):
            if i < len(pedidos):
                p = pedidos[i]
                w['lbl_id'].config(text=p.id_pedido)
                w['lbl_dest'].config(text=p.destino_nombre[:14])
                w['lbl_pri'].config(text=p.prioridad,
                                    fg=COLOR_PRI.get(p.prioridad, GRAY))
                w['card'].pack(fill=tk.X, pady=1)
            else:
                w['card'].pack_forget()

    def _actualizar_alertas(self):
        alertas = []
        for dron in self.sistema.drones.values():
            if dron.bateria <= 20:
                alertas.append((f'{dron.id_dron}: Bateria baja ({dron.bateria}%)', RED))
            if dron.estado == 'mantenimiento':
                alertas.append((f'{dron.id_dron}: En mantenimiento', AMBER))

        for i, w in enumerate(self._widgets_alertas):
            if i < len(alertas):
                msg, color = alertas[i]
                w['barra'].config(bg=color)
                w['lbl'].config(text='  ' + msg, fg=color, bg=CARD)
                w['frame'].config(bg=CARD)
                w['frame'].pack(fill=tk.X, pady=1)
            else:
                w['frame'].pack_forget()

        if not alertas:
            if not hasattr(self, '_lbl_sin_alertas'):
                self._lbl_sin_alertas = tk.Label(
                    self.frame_alertas, text='Sin alertas activas',
                    bg=PANEL, fg=GRAY, font=('Segoe UI', 9))
            self._lbl_sin_alertas.pack(anchor='w')
        else:
            if hasattr(self, '_lbl_sin_alertas'):
                self._lbl_sin_alertas.pack_forget()

    def _actualizar_resumen(self):
        valores = [
            str(len(self.sistema.entregas_completadas)),
            str(len(self.sistema.cola_pedidos)),
            str(sum(1 for d in self.sistema.drones.values()
                    if d.estado == 'en_vuelo')) + ' / 4',
        ]
        for lbl, val in zip(self._widgets_resumen, valores):
            lbl.config(text=val)

    # ── MAPA ──────────────────────────────────────────────────────────────────

    def _escalar(self, w, h):
        """Devuelve funciones sx(x) sy(y) que mapean coords base a canvas."""
        sx = w / 640.0
        sy = h / 580.0
        return sx, sy

    def _redibujar_mapa(self):
        self.canvas.delete('all')
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        sx, sy = self._escalar(w, h)

        self._dibujar_fondo(w, h, sx, sy)
        self._dibujar_zona_ziruma(sx, sy)
        self._dibujar_aristas(sx, sy)
        self._dibujar_ruta_animada(sx, sy)
        self._dibujar_nodos(sx, sy)
        self._dibujar_drones_en_vuelo(sx, sy)
        self._dibujar_leyenda(w, h)

    def _dibujar_fondo(self, w, h, sx, sy):
        # Fondo oceano
        self.canvas.create_rectangle(0, 0, w, h * 0.40,
                                      fill='#07131a', outline='')
        # Zona costera
        self.canvas.create_rectangle(0, h * 0.38, w, h * 0.44,
                                      fill='#0d1f18', outline='')
        # Tierra
        self.canvas.create_rectangle(0, h * 0.42, w, h,
                                      fill='#0a1610', outline='')

        # Bahia (elipse)
        bx = int(w * 0.42)
        by = int(h * 0.18)
        self.canvas.create_oval(bx, by, bx+200, by+100,
                                 fill='#081926', outline='#0f2d40', width=1)
        self.canvas.create_text(bx+100, by+50,
                                 text='Bahia de Santa Marta',
                                 fill='#1e4a6a', font=('Segoe UI', 8), justify=tk.CENTER)

        # Sierra Nevada (sur-este)
        mx = int(w * 0.62)
        my = int(h * 0.68)
        self.canvas.create_oval(mx, my, mx+120, my+80,
                                 fill='#0d1e0a', outline='#1a3a12', width=1)
        self.canvas.create_text(mx+60, my+40,
                                 text='Sierra Nevada',
                                 fill='#2a5020', font=('Segoe UI', 7))

        # Mar Caribe label
        self.canvas.create_text(w*0.75, h*0.10,
                                 text='MAR CARIBE',
                                 fill='#1e4a6a', font=('Segoe UI', 9, 'bold'))

        # Líneas de cuadrícula sutiles sobre tierra
        for gx in range(0, w, 60):
            self.canvas.create_line(gx, h*0.42, gx, h,
                                     fill='#111f14', width=1)
        for gy in range(int(h*0.42), h, 60):
            self.canvas.create_line(0, gy, w, gy,
                                     fill='#111f14', width=1)

    def _dibujar_zona_ziruma(self, sx, sy):
        """Dibuja la zona de exclusión Ziruma con múltiples capas visuales."""
        cx = int(ZIRUMA_CANVAS[0] * sx)
        cy = int(ZIRUMA_CANVAS[1] * sy)
        r  = int(ZIRUMA_RADIO * min(sx, sy))

        # Círculo exterior difuso (zona de peligro)
        self.canvas.create_oval(cx-r-12, cy-r-12, cx+r+12, cy+r+12,
                                 fill='', outline='#3d0a0a', width=2, dash=(4, 6))

        # Relleno semi-transparente rojo (interior)
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                 fill='#1a0505', outline='#ef4444', width=2)

        # Patrón de rayas interiores (X) para indicar zona prohibida
        for offset in range(-r+8, r-8, 14):
            # Diagonales \
            x1 = cx - r + max(0, offset)
            y1 = cy - r + max(0, -offset)
            x2 = cx + min(r, r + offset)
            y2 = cy + min(r, r - offset)
            self.canvas.create_line(x1, y1, x2, y2,
                                     fill='#3a0808', width=1)

        # Borde de alerta parpadeante (simulado con anillo doble)
        self.canvas.create_oval(cx-r-4, cy-r-4, cx+r+4, cy+r+4,
                                 fill='', outline='#7f1010', width=1)

        # Icono "prohibido" central (círculo con línea)
        ri = 14
        self.canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                                 fill='#2a0808', outline=RED, width=2)
        self.canvas.create_line(cx-ri+4, cy+ri-4, cx+ri-4, cy-ri+4,
                                 fill=RED, width=2)

        # Etiqueta
        self.canvas.create_text(cx, cy+r+18,
                                 text='⛔ Cerro Ziruma',
                                 fill=RED, font=('Segoe UI', 8, 'bold'))
        self.canvas.create_text(cx, cy+r+30,
                                 text='Zona de exclusión aérea',
                                 fill='#7f3333', font=('Segoe UI', 7))

    def _dibujar_aristas(self, sx, sy):
        """Dibuja todas las aristas del grafo."""
        dibujadas = set()
        from estructuras.grafo import ZONAS_EXCLUIDAS

        for id_nodo, nodo in self.sistema.mapa.nodos.items():
            if id_nodo not in NODO_POS or nodo.tipo == 'excluido':
                continue
            for vecino_id, dist in self.sistema.mapa.obtener_vecinos(id_nodo):
                if vecino_id not in NODO_POS:
                    continue
                par = tuple(sorted([id_nodo, vecino_id]))
                if par in dibujadas:
                    continue
                dibujadas.add(par)

                x1 = int(NODO_POS[id_nodo][0] * sx)
                y1 = int(NODO_POS[id_nodo][1] * sy)
                x2 = int(NODO_POS[vecino_id][0] * sx)
                y2 = int(NODO_POS[vecino_id][1] * sy)

                # Color según si involucra recarga
                nodo_v = self.sistema.mapa.nodos.get(vecino_id)
                if (nodo.tipo == 'recarga' or
                        (nodo_v and nodo_v.tipo == 'recarga')):
                    color = '#1a3825'
                else:
                    color = '#1a2e25'

                self.canvas.create_line(x1, y1, x2, y2,
                                         fill=color, width=1.5, dash=(5, 3))

                # Distancia en la arista
                mx, my = (x1+x2)//2, (y1+y2)//2
                self.canvas.create_text(mx, my-7,
                                         text=f'{dist:.1f}km',
                                         fill='#304035',
                                         font=('Segoe UI', 7))

    def _dibujar_ruta_animada(self, sx, sy):
        """Dibuja la ruta A* activa con animación de pulso."""
        if len(self.ruta_activa) < 2:
            return

        # Dibuja segmentos de la ruta con color brillante
        for i in range(len(self.ruta_activa) - 1):
            n1 = self.ruta_activa[i]
            n2 = self.ruta_activa[i + 1]
            if n1 not in NODO_POS or n2 not in NODO_POS:
                continue

            x1 = int(NODO_POS[n1][0] * sx)
            y1 = int(NODO_POS[n1][1] * sy)
            x2 = int(NODO_POS[n2][0] * sx)
            y2 = int(NODO_POS[n2][1] * sy)

            # Línea base de la ruta (brillante)
            self.canvas.create_line(x1, y1, x2, y2,
                                     fill=TEAL, width=3,
                                     capstyle=tk.ROUND)

            # Flechas de dirección sobre la ruta
            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)
            if dist > 0:
                # Flecha a 60% del segmento
                fx = x1 + dx * 0.60
                fy = y1 + dy * 0.60
                angulo = math.atan2(dy, dx)
                tam = 7
                # Triángulo de flecha
                pts = [
                    fx + tam * math.cos(angulo),
                    fy + tam * math.sin(angulo),
                    fx + tam * math.cos(angulo + 2.4),
                    fy + tam * math.sin(angulo + 2.4),
                    fx + tam * math.cos(angulo - 2.4),
                    fy + tam * math.sin(angulo - 2.4),
                ]
                self.canvas.create_polygon(pts, fill=TEAL, outline='')

        # Pulso animado (círculo que avanza sobre la ruta)
        if self._anim_activa and len(self.ruta_activa) >= 2:
            idx = self._anim_paso % (len(self.ruta_activa) - 1)
            n1 = self.ruta_activa[idx]
            n2 = self.ruta_activa[idx + 1]
            if n1 in NODO_POS and n2 in NODO_POS:
                frac = (self._anim_paso % 6) / 6.0
                px = NODO_POS[n1][0] + (NODO_POS[n2][0] - NODO_POS[n1][0]) * frac
                py = NODO_POS[n1][1] + (NODO_POS[n2][1] - NODO_POS[n1][1]) * frac
                px, py = int(px * sx), int(py * sy)

                # Halo exterior
                self.canvas.create_oval(px-14, py-14, px+14, py+14,
                                         fill='', outline=TEAL, width=1)
                # Círculo del dron animado
                self.canvas.create_oval(px-8, py-8, px+8, py+8,
                                         fill=TEAL, outline=WHITE, width=2)
                # Label del dron
                if self.ruta_dron_activo:
                    self.canvas.create_text(px+14, py-10,
                                             text=self.ruta_dron_activo,
                                             fill=WHITE,
                                             font=('Segoe UI', 8, 'bold'),
                                             anchor='w')

    def _dibujar_nodos(self, sx, sy):
        """Dibuja cada nodo del grafo con su etiqueta."""
        for id_nodo, nodo in self.sistema.mapa.nodos.items():
            if id_nodo not in NODO_POS:
                continue

            x = int(NODO_POS[id_nodo][0] * sx)
            y = int(NODO_POS[id_nodo][1] * sy)
            color = NODO_COLOR.get(nodo.tipo, GRAY)

            # Nodos excluidos se dibujan pequeños y sin interacción
            if nodo.tipo == 'excluido':
                # Solo Ziruma se dibuja como zona, Aeropuerto como punto
                if id_nodo == 'AEROPUERTO':
                    self.canvas.create_rectangle(x-8, y-4, x+8, y+4,
                                                  fill='#1a0505', outline=RED, width=1)
                    self.canvas.create_text(x, y+12, text='Aeropuerto',
                                             fill='#7f3333',
                                             font=('Segoe UI', 7))
                continue

            # ¿Está en la ruta activa?
            en_ruta = id_nodo in self.ruta_activa

            # Radio según tipo
            r = 14 if nodo.tipo == 'almacen' else 11 if nodo.tipo == 'recarga' else 10

            # Halo si está seleccionado
            if id_nodo == self.nodo_seleccionado:
                self.canvas.create_oval(x-r-8, y-r-8, x+r+8, y+r+8,
                                         fill='', outline=color, width=1,
                                         dash=(4, 4))

            # Halo de ruta
            if en_ruta:
                self.canvas.create_oval(x-r-5, y-r-5, x+r+5, y+r+5,
                                         fill='', outline=TEAL, width=2)

            # Nodo principal
            fill_color = '#0f1e1c' if nodo.tipo != 'almacen' else '#0d2520'
            self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                     fill=fill_color, outline=color, width=2)

            # Ícono según tipo
            if nodo.tipo == 'almacen':
                self.canvas.create_text(x, y, text='🏭',
                                         font=('Segoe UI', 9))
            elif nodo.tipo == 'recarga':
                self.canvas.create_text(x, y, text='⚡',
                                         font=('Segoe UI', 8))
            else:
                # Punto destino
                self.canvas.create_oval(x-4, y-4, x+4, y+4,
                                         fill=color, outline='')

            # Etiqueta con fondo
            lbl = nodo.nombre
            lbl_x = x + r + 6
            lbl_y = y
            # Fondo de etiqueta
            self.canvas.create_rectangle(
                lbl_x - 2, lbl_y - 8, lbl_x + len(lbl)*6 + 2, lbl_y + 9,
                fill='#0a1210', outline='', stipple='gray12')
            self.canvas.create_text(lbl_x, lbl_y,
                                     text=lbl, fill=color,
                                     font=('Segoe UI', 8, 'bold'),
                                     anchor='w')

            # Número de conexiones
            n_conexiones = len(self.sistema.mapa.obtener_vecinos(id_nodo))
            self.canvas.create_text(x, y + r + 11,
                                     text=f'{n_conexiones} rutas',
                                     fill='#304030',
                                     font=('Segoe UI', 6))

    def _dibujar_drones_en_vuelo(self, sx, sy):
        """Dibuja ícono de dron en vuelo sobre su nodo actual."""
        for dron in self.sistema.drones.values():
            if dron.estado == 'en_vuelo' and dron.posicion_actual in NODO_POS:
                dx = int(NODO_POS[dron.posicion_actual][0] * sx) + 18
                dy = int(NODO_POS[dron.posicion_actual][1] * sy) - 18
                self.canvas.create_oval(dx-9, dy-9, dx+9, dy+9,
                                         fill=GREEN, outline=WHITE, width=1.5)
                self.canvas.create_text(dx+14, dy,
                                         text=dron.id_dron,
                                         fill=WHITE,
                                         font=('Segoe UI', 8, 'bold'),
                                         anchor='w')

    def _dibujar_leyenda(self, w, h):
        """Leyenda en la esquina inferior izquierda."""
        items = [
            ('■ Almacen',    TEAL),
            ('● Destino',    GREEN),
            ('⚡ Recarga',   AMBER),
            ('⛔ Excluido',  RED),
            ('—  Ruta A*',  TEAL),
        ]
        lx, ly = 10, h - 22
        # Fondo de leyenda
        self.canvas.create_rectangle(lx-4, ly-14,
                                      lx + 380, ly + 16,
                                      fill='#07131a', outline='#1a2e25')
        for i, (txt, color) in enumerate(items):
            self.canvas.create_text(lx + i*78, ly,
                                     text=txt, fill=color,
                                     font=('Segoe UI', 7, 'bold'),
                                     anchor='w')

    # ── INTERACCION ───────────────────────────────────────────────────────────

    def _click_canvas(self, event):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        sx, sy = self._escalar(w, h)
        for id_nodo in NODO_POS:
            if self.sistema.mapa.nodos.get(id_nodo, None) is None:
                continue
            if self.sistema.mapa.nodos[id_nodo].tipo == 'excluido':
                continue
            x = int(NODO_POS[id_nodo][0] * sx)
            y = int(NODO_POS[id_nodo][1] * sy)
            if abs(event.x - x) < 20 and abs(event.y - y) < 20:
                self._mostrar_detalle_nodo(id_nodo)
                return

    def _mostrar_detalle_nodo(self, id_nodo):
        self.nodo_seleccionado = id_nodo
        info = self.sistema.info_nodo(id_nodo)
        if not info:
            return

        # Limpiar panel
        for widget in self.frame_detalle.winfo_children():
            widget.destroy()

        color = NODO_COLOR.get(info['tipo'], GRAY)
        tk.Label(self.frame_detalle, text=info['nombre'],
                 bg=CARD, fg=color,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        for k, v in [
            ('Tipo',       info['tipo'].capitalize()),
            ('Coords',     f"{info['lat']:.4f}°N  {abs(info['lon']):.4f}°W"),
            ('Drones',     ', '.join(info['drones']) if info['drones'] else 'Ninguno'),
            ('Rutas',      str(info['conexiones'])),
        ]:
            f = tk.Frame(self.frame_detalle, bg=CARD)
            f.pack(fill=tk.X)
            tk.Label(f, text=k, bg=CARD, fg=GRAY,
                     font=('Segoe UI', 9), width=8, anchor='w').pack(side=tk.LEFT)
            tk.Label(f, text=v, bg=CARD, fg=WHITE,
                     font=('Segoe UI', 9)).pack(side=tk.LEFT)

        if id_nodo != 'ALMACEN':
            tk.Button(self.frame_detalle,
                      text='Calcular ruta A* desde almacen',
                      bg=TEAL, fg=BG,
                      font=('Segoe UI', 9, 'bold'), relief=tk.FLAT,
                      cursor='hand2',
                      command=lambda: self._mostrar_ruta(id_nodo)
                      ).pack(fill=tk.X, pady=(8, 0))

        self._redibujar_mapa()

    def _mostrar_ruta(self, destino):
        ruta, dist = self.sistema.calcular_ruta('ALMACEN', destino)
        if ruta:
            self.ruta_activa = ruta
            self.ruta_dron_activo = 'Dron'
            self._anim_activa = True
            self._anim_paso = 0
            self._redibujar_mapa()

            # Actualizar panel de ruta
            for w in self.frame_ruta.winfo_children():
                w.destroy()
            nombres = [self.sistema.mapa.nodos[n].nombre
                       for n in ruta if n in self.sistema.mapa.nodos]
            ruta_txt = ' → '.join(nombres)
            tk.Label(self.frame_ruta, text=ruta_txt,
                     bg=CARD, fg=TEAL,
                     font=('Segoe UI', 8, 'bold'),
                     justify=tk.LEFT, wraplength=230).pack(anchor='w')
            tk.Label(self.frame_ruta, text=f'Distancia total: {dist:.2f} km',
                     bg=CARD, fg=WHITE,
                     font=('Segoe UI', 9)).pack(anchor='w', pady=(2, 0))
            tk.Label(self.frame_ruta, text=f'{len(ruta)} nodos · Evita Ziruma y Aeropuerto',
                     bg=CARD, fg=GRAY,
                     font=('Segoe UI', 8)).pack(anchor='w')

            messagebox.showinfo(
                'Ruta A* calculada',
                f'Ruta: {" → ".join(nombres)}\n'
                f'Distancia: {dist:.2f} km\n'
                f'Nodos: {len(ruta)}\n\n'
                f'La ruta evita la zona Ziruma y el Aeropuerto.',
                parent=self
            )
        else:
            messagebox.showwarning('Sin ruta',
                                    'No se encontró ruta disponible.\n'
                                    'Todas las rutas pueden estar bloqueadas.',
                                    parent=self)

    def _despachar(self):
        dron, mensaje = self.sistema.despachar_siguiente()
        if dron:
            self.ruta_activa = dron.ruta_astar
            self.ruta_dron_activo = dron.id_dron
            self._anim_activa = True
            self._anim_paso = 0

            # Actualizar panel de ruta
            for w in self.frame_ruta.winfo_children():
                w.destroy()
            nombres = [self.sistema.mapa.nodos[n].nombre
                       for n in dron.ruta_astar
                       if n in self.sistema.mapa.nodos]
            tk.Label(self.frame_ruta, text=' → '.join(nombres),
                     bg=CARD, fg=GREEN,
                     font=('Segoe UI', 8, 'bold'),
                     justify=tk.LEFT, wraplength=230).pack(anchor='w')
            tk.Label(self.frame_ruta, text=f'Dron: {dron.id_dron} en vuelo',
                     bg=CARD, fg=WHITE,
                     font=('Segoe UI', 9)).pack(anchor='w', pady=(2, 0))

            messagebox.showinfo('Despacho exitoso', mensaje, parent=self)
        else:
            messagebox.showwarning('No se pudo despachar', mensaje, parent=self)
        self.actualizar()

    def _actualizar_matriz(self):
        self.canvas_matriz.delete('all')
        ocupadas = {(c['fila'], c['columna']): c['dron']
                    for c in self.sistema.espacio_aereo.a_lista()}
        cols, rows = 13, 5
        cw, ch = 16, 18
        for r in range(rows):
            for c in range(cols):
                x1 = 5 + c * cw
                y1 = 5 + r * ch
                x2, y2 = x1 + cw - 1, y1 + ch - 1
                occ = ocupadas.get((r, c))
                self.canvas_matriz.create_rectangle(
                    x1, y1, x2, y2,
                    fill='#0d2520' if occ else CARD,
                    outline=BORDER, width=1
                )
                if occ:
                    self.canvas_matriz.create_text(
                        (x1+x2)//2, (y1+y2)//2,
                        text=occ.replace('D-', ''),
                        fill=TEAL, font=('Segoe UI', 6, 'bold')
                    )
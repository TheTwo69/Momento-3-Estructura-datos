# Ventana principal: Panel de Control
# Muestra el mapa aereo, el estado de los drones y la cola de pedidos

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

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

NODO_POS = {
    'ALMACEN':   (430, 340),
    'RODADERO':  (280, 500),
    'TAGANGA':   (560, 140),
    'CENTRO':    (570, 370),
    'BELLO':     (220, 360),
    'MINCA':     (340, 560),
    'RECARGA_N': (500, 230),
    'RECARGA_S': (350, 450),
}

NODO_COLOR = {
    'almacen':  TEAL,
    'destino':  GREEN,
    'recarga':  AMBER,
    'excluido': RED,
}

COLOR_ESTADO = {
    'en_vuelo': GREEN, 'en_espera': TEAL,
    'bateria_baja': RED, 'mantenimiento': AMBER
}


class VentanaPrincipal(tk.Tk):
    def __init__(self, sistema):
        super().__init__()
        self.sistema = sistema
        self.title('LogiDrone-UCC — Operacion Bahia Santa Marta')
        self.geometry('1280x760')
        self.configure(bg=BG)
        self.resizable(True, True)

        self.nodo_seleccionado = None
        self.ruta_activa = []

        # Referencias a widgets de drones y cola para actualizar sin recrear
        self._widgets_drones = {}   # id_dron -> dict de labels
        self._widgets_cola   = []   # lista de dicts de labels por fila

        self._construir_ui()
        self._inicializar_widgets_dinamicos()
        self._tick()  # primer ciclo de actualizacion

    # ── CONSTRUCCION INICIAL ──────────────────────────────────

    def _construir_ui(self):
        # Topbar
        topbar = tk.Frame(self, bg=PANEL, height=46)
        topbar.pack(fill=tk.X, side=tk.TOP)
        topbar.pack_propagate(False)

        tk.Label(topbar, text='  LogiDrone-UCC', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(topbar, text=' | Operacion Bahia Santa Marta', bg=PANEL,
                 fg=GRAY, font=('Segoe UI', 10)).pack(side=tk.LEFT)

        from gui.ventana_pedido import VentanaPedido
        from gui.ventana_dron import VentanaDron
        from gui.ventana_inventario import VentanaInventario

        tk.Button(topbar, text='Pedidos', bg=PANEL, fg=GRAY, relief=tk.FLAT,
                  font=('Segoe UI', 10), cursor='hand2',
                  command=lambda: VentanaPedido(self, self.sistema, self.actualizar)
                  ).pack(side=tk.LEFT, padx=8)
        tk.Button(topbar, text='Drones', bg=PANEL, fg=GRAY, relief=tk.FLAT,
                  font=('Segoe UI', 10), cursor='hand2',
                  command=lambda: VentanaDron(self, self.sistema, self.actualizar)
                  ).pack(side=tk.LEFT, padx=8)
        tk.Button(topbar, text='Inventario', bg=PANEL, fg=GRAY, relief=tk.FLAT,
                  font=('Segoe UI', 10), cursor='hand2',
                  command=lambda: VentanaInventario(self, self.sistema)
                  ).pack(side=tk.LEFT, padx=8)

        self.lbl_hora = tk.Label(topbar, text='', bg=PANEL, fg=GRAY, font=('Segoe UI', 10))
        self.lbl_hora.pack(side=tk.RIGHT, padx=12)

        tk.Frame(self, bg=TEAL, height=2).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=BG)
        contenido.pack(fill=tk.BOTH, expand=True)

        self.panel_izq = tk.Frame(contenido, bg=PANEL, width=240)
        self.panel_izq.pack(side=tk.LEFT, fill=tk.Y)
        self.panel_izq.pack_propagate(False)
        self._construir_panel_izq()

        self.frame_mapa = tk.Frame(contenido, bg=BG)
        self.frame_mapa.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._construir_mapa()

        self.panel_der = tk.Frame(contenido, bg=PANEL, width=260)
        self.panel_der.pack(side=tk.RIGHT, fill=tk.Y)
        self.panel_der.pack_propagate(False)
        self._construir_panel_der()

    def _construir_panel_izq(self):
        tk.Label(self.panel_izq, text='DRONES', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10, pady=(8, 2))

        self.frame_drones = tk.Frame(self.panel_izq, bg=PANEL)
        self.frame_drones.pack(fill=tk.X, padx=6)

        tk.Frame(self.panel_izq, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=6)

        cola_header = tk.Frame(self.panel_izq, bg=PANEL)
        cola_header.pack(fill=tk.X, padx=10)
        tk.Label(cola_header, text='COLA DE PEDIDOS', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
        self.lbl_cola_count = tk.Label(cola_header, text='0', bg=TEAL, fg=BG,
                                        font=('Segoe UI', 8, 'bold'), padx=5)
        self.lbl_cola_count.pack(side=tk.RIGHT)

        self.frame_cola = tk.Frame(self.panel_izq, bg=PANEL)
        self.frame_cola.pack(fill=tk.X, padx=6, pady=(4, 0))

        tk.Frame(self.panel_izq, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=6)

        tk.Button(self.panel_izq, text='Despachar siguiente', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._despachar).pack(fill=tk.X, padx=8, pady=2)

        from gui.ventana_pedido import VentanaPedido
        tk.Button(self.panel_izq, text='Nuevo pedido', bg=CARD, fg=TEAL,
                  font=('Segoe UI', 10), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=TEAL,
                  command=lambda: VentanaPedido(self, self.sistema, self.actualizar)
                  ).pack(fill=tk.X, padx=8, pady=2)

    def _construir_mapa(self):
        tk.Label(self.frame_mapa, text='Mapa aereo — Santa Marta  |  Clic en un nodo para ver detalles',
                 bg=BG, fg=GRAY, font=('Segoe UI', 9)).pack(anchor='w', padx=10, pady=4)

        self.canvas = tk.Canvas(self.frame_mapa, bg='#0a1015', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.canvas.bind('<Configure>', lambda e: self._redibujar_mapa())
        self.canvas.bind('<Button-1>', self._click_canvas)

    def _construir_panel_der(self):
        tk.Label(self.panel_der, text='DETALLE DEL NODO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10, pady=(8, 4))

        self.frame_detalle = tk.Frame(self.panel_der, bg=CARD, padx=8, pady=8)
        self.frame_detalle.pack(fill=tk.X, padx=8)
        self.lbl_detalle = tk.Label(self.frame_detalle, text='Selecciona un nodo\nen el mapa',
                                     bg=CARD, fg=GRAY, font=('Segoe UI', 10), justify=tk.LEFT)
        self.lbl_detalle.pack(anchor='w')

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        tk.Label(self.panel_der, text='ESPACIO AEREO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        tk.Label(self.panel_der, text='Matriz de monitoreo', bg=PANEL, fg=GRAY,
                 font=('Segoe UI', 8)).pack(anchor='w', padx=10, pady=(0, 4))

        self.canvas_matriz = tk.Canvas(self.panel_der, bg=CARD,
                                        width=230, height=130, highlightthickness=0)
        self.canvas_matriz.pack(padx=8, pady=2)

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        tk.Label(self.panel_der, text='ALERTAS', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        self.frame_alertas = tk.Frame(self.panel_der, bg=PANEL)
        self.frame_alertas.pack(fill=tk.X, padx=8, pady=4)

        tk.Frame(self.panel_der, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=6)

        tk.Label(self.panel_der, text='RESUMEN', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=10)
        self.frame_resumen = tk.Frame(self.panel_der, bg=PANEL)
        self.frame_resumen.pack(fill=tk.X, padx=10)

    # ── WIDGETS DINAMICOS: se crean UNA SOLA VEZ ─────────────
    # Despues solo se actualiza el texto/color con .config()

    def _inicializar_widgets_dinamicos(self):
        # Cards de drones (una por dron, fijas)
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
            lbl_bat = tk.Label(fila1, text='', bg=CARD, fg=GRAY, font=('Segoe UI', 9))
            lbl_bat.pack(side=tk.RIGHT)
            lbl_est = tk.Label(info, text='', bg=CARD, fg=TEAL, font=('Segoe UI', 9))
            lbl_est.pack(anchor='w')
            self._widgets_drones[dron.id_dron] = {
                'barra': barra, 'lbl_bat': lbl_bat, 'lbl_est': lbl_est
            }

        # Filas de la cola (maximo 5, fijas)
        for _ in range(5):
            card = tk.Frame(self.frame_cola, bg=CARD, pady=3, padx=6)
            card.pack(fill=tk.X, pady=1)
            fila = tk.Frame(card, bg=CARD)
            fila.pack(fill=tk.X)
            lbl_id   = tk.Label(fila, text='', bg=CARD, fg=TEAL, font=('Segoe UI', 10, 'bold'))
            lbl_id.pack(side=tk.LEFT)
            lbl_dest = tk.Label(fila, text='', bg=CARD, fg=WHITE, font=('Segoe UI', 10))
            lbl_dest.pack(side=tk.LEFT, padx=4)
            lbl_pri  = tk.Label(fila, text='', bg=CARD, fg=GRAY, font=('Segoe UI', 8, 'bold'))
            lbl_pri.pack(side=tk.RIGHT)
            self._widgets_cola.append({'card': card, 'lbl_id': lbl_id,
                                        'lbl_dest': lbl_dest, 'lbl_pri': lbl_pri})

        # Alertas: hasta 4 filas fijas
        self._widgets_alertas = []
        for _ in range(4):
            f = tk.Frame(self.frame_alertas, bg=CARD, pady=4, padx=6)
            f.pack(fill=tk.X, pady=1)
            barra = tk.Frame(f, bg=RED, width=3)
            barra.pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(f, text='', bg=CARD, fg=RED, font=('Segoe UI', 9))
            lbl.pack(side=tk.LEFT)
            self._widgets_alertas.append({'frame': f, 'barra': barra, 'lbl': lbl})
            f.pack_forget()  # oculto hasta que haya alerta

        # Resumen: 3 filas fijas
        stats_labels = ['Entregas completadas', 'Pedidos en cola', 'Drones activos']
        self._widgets_resumen = []
        for label in stats_labels:
            f = tk.Frame(self.frame_resumen, bg=PANEL)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=label, bg=PANEL, fg=GRAY, font=('Segoe UI', 9)).pack(side=tk.LEFT)
            lbl_val = tk.Label(f, text='0', bg=PANEL, fg=WHITE, font=('Segoe UI', 11, 'bold'))
            lbl_val.pack(side=tk.RIGHT)
            self._widgets_resumen.append(lbl_val)

    # ── CICLO DE ACTUALIZACION ────────────────────────────────
    # Solo actualiza texto/color, NO destruye ni crea widgets

    def _tick(self):
        # Solo actualiza labels y widgets pequenos — NO redibuja el mapa
        # Asi se elimina el parpadeo del canvas principal
        self._actualizar_drones()
        self._actualizar_cola()
        self._actualizar_alertas()
        self._actualizar_resumen()
        self._actualizar_matriz()
        self.lbl_hora.config(text=datetime.datetime.now().strftime('%H:%M:%S'))
        self.after(4000, self._tick)

    def actualizar(self):
        # Llamado desde ventanas secundarias cuando cambia algo real
        # Solo aqui se redibuja el mapa porque el estado cambio de verdad
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
            w['lbl_est'].config(text=dron.estado.replace('_', ' ').title(), fg=color)

    def _actualizar_cola(self):
        pedidos = self.sistema.cola_pedidos.a_lista()
        self.lbl_cola_count.config(text=str(len(pedidos)))
        COLOR_PRI = {'ALTA': RED, 'MEDIA': AMBER, 'BAJA': GREEN}
        for i, w in enumerate(self._widgets_cola):
            if i < len(pedidos):
                p = pedidos[i]
                w['lbl_id'].config(text=p.id_pedido)
                w['lbl_dest'].config(text=p.destino_nombre)
                w['lbl_pri'].config(text=p.prioridad, fg=COLOR_PRI.get(p.prioridad, GRAY))
                w['card'].pack(fill=tk.X, pady=1)
            else:
                # Oculta filas que no tienen pedido
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
                w['lbl'].config(text='  ' + msg, fg=color,
                                 bg=CARD)
                w['frame'].config(bg=CARD)
                w['frame'].pack(fill=tk.X, pady=1)
            else:
                w['frame'].pack_forget()

        # Si no hay alertas muestra mensaje
        if not alertas:
            if not hasattr(self, '_lbl_sin_alertas'):
                self._lbl_sin_alertas = tk.Label(self.frame_alertas, text='Sin alertas activas',
                                                   bg=PANEL, fg=GRAY, font=('Segoe UI', 9))
            self._lbl_sin_alertas.pack(anchor='w')
        else:
            if hasattr(self, '_lbl_sin_alertas'):
                self._lbl_sin_alertas.pack_forget()

    def _actualizar_resumen(self):
        valores = [
            str(len(self.sistema.entregas_completadas)),
            str(len(self.sistema.cola_pedidos)),
            str(sum(1 for d in self.sistema.drones.values() if d.estado == 'en_vuelo')) + ' / 4',
        ]
        for lbl, val in zip(self._widgets_resumen, valores):
            lbl.config(text=val)

    # ── MAPA (canvas, se redibuja completo pero es rapido) ────

    def _redibujar_mapa(self):
        self.canvas.delete('all')
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        # Fondos geograficos
        self.canvas.create_rectangle(0, 0, w, h * 0.45, fill='#0a1928', outline='')
        self.canvas.create_rectangle(0, h * 0.43, w, h * 0.48, fill='#1a2f28', outline='')
        self.canvas.create_rectangle(0, h * 0.46, w, h, fill='#151c1a', outline='')

        bx = int(w * 0.38)
        by = int(h * 0.30)
        self.canvas.create_oval(bx, by, bx + 160, by + 90, fill='#091e30', outline='')
        self.canvas.create_text(bx + 80, by + 45, text='Bahia de\nSanta Marta',
                                 fill='#3a5878', font=('Segoe UI', 7), justify=tk.CENTER)

        zx, zy = int(w * 0.13), int(h * 0.50)
        self.canvas.create_oval(zx, zy, zx + 100, zy + 70, fill='#1a3015', outline='#2a5020', width=1)
        self.canvas.create_text(zx + 50, zy + 35, text='Cerro\nZiruma',
                                 fill='#3a6030', font=('Segoe UI', 7), justify=tk.CENTER)

        self.canvas.create_text(w * 0.65, h * 0.15, text='MAR CARIBE',
                                 fill='#2a4560', font=('Segoe UI', 9, 'bold'))

        for gx in range(0, w, 55):
            self.canvas.create_line(gx, h * 0.46, gx, h, fill='#1a2825', width=1)
        for gy in range(int(h * 0.46), h, 55):
            self.canvas.create_line(0, gy, w, gy, fill='#1a2825', width=1)

        sx = w / 640
        sy = h / 620

        # Aristas
        dibujadas = set()
        for id_nodo, nodo in self.sistema.mapa.nodos.items():
            if nodo.tipo == 'excluido' or id_nodo not in NODO_POS:
                continue
            for vecino_id, _ in self.sistema.mapa.obtener_vecinos(id_nodo):
                if vecino_id not in NODO_POS:
                    continue
                par = tuple(sorted([id_nodo, vecino_id]))
                if par in dibujadas:
                    continue
                dibujadas.add(par)
                x1, y1 = NODO_POS[id_nodo]
                x2, y2 = NODO_POS[vecino_id]
                en_ruta = False
                if len(self.ruta_activa) > 1:
                    for i in range(len(self.ruta_activa) - 1):
                        if {self.ruta_activa[i], self.ruta_activa[i+1]} == {id_nodo, vecino_id}:
                            en_ruta = True
                            break
                self.canvas.create_line(
                    x1*sx, y1*sy, x2*sx, y2*sy,
                    fill=TEAL if en_ruta else '#283835',
                    width=3 if en_ruta else 1
                )

        # Nodos
        for id_nodo, nodo in self.sistema.mapa.nodos.items():
            if id_nodo not in NODO_POS:
                continue
            x, y = int(NODO_POS[id_nodo][0] * sx), int(NODO_POS[id_nodo][1] * sy)
            color = NODO_COLOR.get(nodo.tipo, GRAY)
            r = 10 if nodo.tipo == 'almacen' else 8 if nodo.tipo == 'destino' else 6
            self.canvas.create_oval(x-r-5, y-r-5, x+r+5, y+r+5,
                                     fill='', outline=color, width=1, stipple='gray25')
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=BG, outline=color, width=2)
            self.canvas.create_text(x + r + 7, y, text=nodo.nombre,
                                     fill=color, font=('Segoe UI', 8, 'bold'), anchor='w')

        # Drones en vuelo
        for dron in self.sistema.drones.values():
            if dron.estado == 'en_vuelo' and dron.posicion_actual in NODO_POS:
                dx = int(NODO_POS[dron.posicion_actual][0] * sx) + 14
                dy = int(NODO_POS[dron.posicion_actual][1] * sy) - 14
                self.canvas.create_oval(dx-7, dy-7, dx+7, dy+7, fill=TEAL, outline=WHITE, width=1)
                self.canvas.create_text(dx + 12, dy, text=dron.id_dron,
                                         fill=WHITE, font=('Segoe UI', 7, 'bold'), anchor='w')

        # Leyenda
        leyenda = [('Almacen/Ruta A*', TEAL), ('Destino', GREEN), ('Recarga', AMBER), ('Excluido', RED)]
        lx = 10
        for texto, color in leyenda:
            self.canvas.create_oval(lx, h-14, lx+8, h-6, fill=color, outline='')
            self.canvas.create_text(lx+12, h-10, text=texto, fill=color,
                                     font=('Segoe UI', 7), anchor='w')
            lx += 110

    def _click_canvas(self, event):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        sx = w / 640
        sy = h / 620
        for id_nodo in NODO_POS:
            x = int(NODO_POS[id_nodo][0] * sx)
            y = int(NODO_POS[id_nodo][1] * sy)
            if abs(event.x - x) < 18 and abs(event.y - y) < 18:
                self._mostrar_detalle_nodo(id_nodo)
                return

    def _mostrar_detalle_nodo(self, id_nodo):
        self.nodo_seleccionado = id_nodo
        info = self.sistema.info_nodo(id_nodo)
        if not info:
            return
        for widget in self.frame_detalle.winfo_children():
            widget.destroy()
        tk.Label(self.frame_detalle, text=info['nombre'], bg=CARD, fg=TEAL,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        for k, v in [
            ('Tipo',       info['tipo'].capitalize()),
            ('Coords',     f"{info['lat']:.4f} N  {abs(info['lon']):.4f} W"),
            ('Drones',     ', '.join(info['drones']) if info['drones'] else 'Ninguno'),
            ('Conexiones', str(info['conexiones']) + ' rutas'),
        ]:
            f = tk.Frame(self.frame_detalle, bg=CARD)
            f.pack(fill=tk.X)
            tk.Label(f, text=k, bg=CARD, fg=GRAY, font=('Segoe UI', 9),
                     width=10, anchor='w').pack(side=tk.LEFT)
            tk.Label(f, text=v, bg=CARD, fg=WHITE, font=('Segoe UI', 9)).pack(side=tk.LEFT)
        if id_nodo != 'ALMACEN':
            tk.Button(self.frame_detalle, text='Ver ruta A* desde almacen',
                      bg=TEAL, fg=BG, font=('Segoe UI', 9, 'bold'), relief=tk.FLAT,
                      cursor='hand2',
                      command=lambda: self._mostrar_ruta(id_nodo)
                      ).pack(fill=tk.X, pady=(6, 0))

    def _mostrar_ruta(self, destino):
        ruta, dist = self.sistema.calcular_ruta('ALMACEN', destino)
        if ruta:
            self.ruta_activa = ruta
            self._redibujar_mapa()
            nombres = [self.sistema.mapa.nodos[n].nombre for n in ruta]
            messagebox.showinfo('Ruta A*', ' -> '.join(nombres) + f'\nDistancia: {dist:.2f} km')
        else:
            messagebox.showwarning('Sin ruta', 'No se encontro ruta disponible')

    def _actualizar_matriz(self):
        self.canvas_matriz.delete('all')
        ocupadas = {(c['fila'], c['columna']): c['dron']
                    for c in self.sistema.espacio_aereo.a_lista()}
        cols, rows = 12, 6
        cw, ch = 17, 17
        for r in range(rows):
            for c in range(cols):
                x1 = 6 + c * cw
                y1 = 6 + r * ch
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

    def _despachar(self):
        dron, mensaje = self.sistema.despachar_siguiente()
        if dron:
            self.ruta_activa = dron.ruta_astar
            messagebox.showinfo('Despacho exitoso', mensaje)
        else:
            messagebox.showwarning('No se pudo despachar', mensaje)
        self.actualizar()

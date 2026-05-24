# ventana_principal.py — LogiDrone-UCC v3
# Rediseño completo inspirado en el panel HTML de referencia:
#   · Topbar con tabs de navegación activos (Panel / Pedidos / Drones / Inventario)
#   · Stat-cards con franja de color superior
#   · Mapa canvas animado con drones en vuelo, estelas y pulsos
#   · Panel de Actividad reciente + Estado de flota
#   · Paleta oscura con fuente monospace y acentos azul/verde/ámbar/rojo

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import math
import random

# ── Paleta de colores (igual que el HTML de referencia) ──────────────────────
DARK   = '#0a0e1a'   # fondo principal (muy oscuro azulado)
SURF   = '#111827'   # superficies de paneles
SURF2  = '#1f2937'   # superficies secundarias
BORDER = '#2d3748'   # bordes sutiles
TEXT   = '#e0e6f0'   # texto principal
MUTED  = '#6b7280'   # texto secundario

BLUE   = '#3b82f6'   # acento principal (azul)
GREEN  = '#10b981'   # acento éxito (verde)
WARN   = '#f59e0b'   # advertencia (ámbar)
DANGER = '#ef4444'   # peligro (rojo)

# ── Posiciones de nodos en canvas base 800 × 460 ──────────────────────────────
NODO_POS = {
    'ALMACEN':   (400, 230),
    'RODADERO':  (200, 370),
    'TAGANGA':   (610, 100),
    'CENTRO':    (490, 280),
    'BELLO':     (240, 250),
    'MINCA':     (310, 410),
    'RECARGA_N': (660, 175),
    'RECARGA_S': (320, 330),
    'ZIRUMA':    (555, 175),
    'AEROPUERTO': (180, 430),
}

NODO_COLOR = {
    'almacen':  BLUE,
    'destino':  GREEN,
    'recarga':  WARN,
    'excluido': DANGER,
}

COLOR_ESTADO = {
    'en_vuelo':     GREEN,
    'en_espera':    BLUE,
    'bateria_baja': DANGER,
    'mantenimiento': WARN,
}

# ── Rutas del grafo para dibujar aristas ──────────────────────────────────────
ARISTAS = [
    ('ALMACEN', 'CENTRO'),
    ('ALMACEN', 'BELLO'),
    ('ALMACEN', 'RECARGA_S'),
    ('ALMACEN', 'RECARGA_N'),
    ('RECARGA_N', 'TAGANGA'),
    ('RECARGA_N', 'CENTRO'),
    ('RECARGA_S', 'RODADERO'),
    ('RECARGA_S', 'BELLO'),
    ('BELLO', 'RODADERO'),
    ('RODADERO', 'MINCA'),
]


def bat_color(pct):
    if pct < 25:
        return DANGER
    if pct < 60:
        return WARN
    return GREEN


class VentanaPrincipal(tk.Tk):
    def __init__(self, sistema):
        super().__init__()
        self.sistema = sistema
        self.title('LogiDrone-UCC — Operación Bahía Santa Marta')
        self.geometry('1280x760')
        self.minsize(1100, 680)
        self.configure(bg=DARK)

        # Estado de animación del mapa
        self._tick_count   = 0
        self._drone_states = {}   # id_dron -> {x, y, tx, ty, prog, trail, returning}
        self._anim_pulse   = 0.0  # phase para efecto pulse

        # Tab activa
        self._tab_actual = 'panel'
        self._tab_frames = {}

        # Widgets dinámicos
        self._stat_vars = {}
        self._activity_items = []

        self._init_drone_states()
        self._build_ui()
        self._tick()

    # ── INICIALIZACION ─────────────────────────────────────────────────────────

    def _init_drone_states(self):
        BASE_X, BASE_Y = 400, 230
        for dron in self.sistema.drones.values():
            if dron.estado == 'en_vuelo' and dron.pedido_actual:
                dest_id = dron.pedido_actual.destino_id
                tx, ty = NODO_POS.get(dest_id, (500, 300))
            else:
                tx, ty = BASE_X + random.randint(-60, 60), BASE_Y + random.randint(-40, 40)
            self._drone_states[dron.id_dron] = {
                'x': float(BASE_X), 'y': float(BASE_Y),
                'tx': float(tx),    'ty': float(ty),
                'prog': random.uniform(0, 0.5) if dron.estado == 'en_vuelo' else 0.0,
                'trail': [],
                'returning': False,
                'wait': 0,
            }

    # ── CONSTRUCCION DE UI ────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        self._build_tabs()
        # Activar tab inicial DESPUÉS de que _tab_frames ya existe
        self._switch_tab('panel')

    def _build_topbar(self):
        bar = tk.Frame(self, bg=SURF, height=52)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # Logo badge
        badge = tk.Canvas(bar, width=34, height=34, bg=SURF,
                          highlightthickness=0)
        badge.pack(side=tk.LEFT, padx=(14, 8), pady=9)
        badge.create_rectangle(0, 0, 34, 34, fill='#1d4ed8', outline='')
        badge.create_rectangle(0, 17, 34, 34, fill='#059669', outline='')
        badge.create_text(17, 17, text='LD', fill='white',
                          font=('Courier New', 10, 'bold'))

        # Logo text
        logo_f = tk.Frame(bar, bg=SURF)
        logo_f.pack(side=tk.LEFT, padx=(0, 24))
        tk.Label(logo_f, text='LogiDrone-UCC', bg=SURF, fg='white',
                 font=('Courier New', 11, 'bold')).pack(anchor='w')
        tk.Label(logo_f, text='Operación Bahía Santa Marta', bg=SURF, fg=MUTED,
                 font=('Courier New', 8)).pack(anchor='w')

        # Separador
        tk.Frame(bar, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8)

        # Nav tabs
        self._nav_buttons = {}
        tabs = [
            ('panel',      'Panel'),
            ('pedidos',    'Pedidos'),
            ('drones',     'Drones'),
            ('inventario', 'Inventario'),
        ]
        nav_f = tk.Frame(bar, bg=SURF)
        nav_f.pack(side=tk.LEFT, fill=tk.Y, padx=12)
        for key, label in tabs:
            btn = tk.Button(nav_f, text=label.upper(), bg=SURF, fg=MUTED,
                            relief=tk.FLAT, cursor='hand2',
                            font=('Courier New', 9),
                            activebackground=SURF, activeforeground=TEXT,
                            padx=14, pady=0,
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side=tk.LEFT, fill=tk.Y)
            self._nav_buttons[key] = btn

        # Botón despachar
        tk.Frame(bar, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8)
        tk.Button(bar, text='⚡ DESPACHAR', bg=BLUE, fg='white',
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'), padx=12,
                  command=self._despachar).pack(side=tk.LEFT, pady=12, padx=10)

        # Reloj
        self._lbl_clock = tk.Label(bar, text='', bg=SURF, fg=GREEN,
                                    font=('Courier New', 10))
        self._lbl_clock.pack(side=tk.RIGHT, padx=16)

        # Separador inferior
        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)
        # NOTA: _switch_tab('panel') se llama al final de _build_ui,
        # después de que _build_tabs() ya creó _tab_frames.

    def _build_tabs(self):
        self._container = tk.Frame(self, bg=DARK)
        self._container.pack(fill=tk.BOTH, expand=True)

        for key in ('panel', 'pedidos', 'drones', 'inventario'):
            f = tk.Frame(self._container, bg=DARK)
            self._tab_frames[key] = f

        self._build_panel_tab()
        self._build_pedidos_tab()
        self._build_drones_tab()
        self._build_inventario_tab()

    def _switch_tab(self, key):
        if key not in self._tab_frames:
            return  # frames aun no construidos
        self._tab_actual = key
        for k, f in self._tab_frames.items():
            f.pack_forget()
        self._tab_frames[key].pack(fill=tk.BOTH, expand=True)

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.config(fg=BLUE,
                           relief=tk.FLAT,
                           bg='#0f172a')
            else:
                btn.config(fg=MUTED, bg=SURF)

        if key == 'panel':
            self.after(50, self._redraw_map)
        if key == 'inventario':
            self.after(50, self._draw_avl)

    # ── TAB PANEL ─────────────────────────────────────────────────────────────

    def _build_panel_tab(self):
        tab = self._tab_frames['panel']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=0)

        # Stat cards (fila superior)
        cards_row = tk.Frame(tab, bg=DARK)
        cards_row.grid(row=0, column=0, sticky='ew', padx=14, pady=(14, 8))
        for i in range(4):
            cards_row.columnconfigure(i, weight=1)

        stats = [
            ('stat_pedidos',    'PEDIDOS ACTIVOS',  '0', 'en operación',   BLUE),
            ('stat_vuelo',      'DRONES EN VUELO',  '0', 'de 4 totales',   GREEN),
            ('stat_batbaja',    'BATERÍA BAJA',      '0', '< 30%',          WARN),
            ('stat_stock',      'STOCK CRÍTICO',     '0', '< 5 unidades',   DANGER),
        ]
        self._stat_lbls = {}
        for col, (key, label, val, sub, color) in enumerate(stats):
            card = tk.Frame(cards_row, bg=SURF, bd=0, relief=tk.FLAT)
            card.grid(row=0, column=col, sticky='ew', padx=(0 if col == 0 else 8, 0))

            # franja de color superior
            tk.Frame(card, bg=color, height=3).pack(fill=tk.X)
            inner = tk.Frame(card, bg=SURF, padx=14, pady=10)
            inner.pack(fill=tk.BOTH)

            tk.Label(inner, text=label, bg=SURF, fg=MUTED,
                     font=('Courier New', 8), anchor='w').pack(anchor='w')
            lbl_val = tk.Label(inner, text=val, bg=SURF, fg='white',
                               font=('Courier New', 22, 'bold'), anchor='w')
            lbl_val.pack(anchor='w')
            tk.Label(inner, text=sub, bg=SURF, fg=MUTED,
                     font=('Courier New', 8), anchor='w').pack(anchor='w')
            self._stat_lbls[key] = lbl_val

        # Mapa canvas (zona central)
        map_card = tk.Frame(tab, bg=SURF, bd=0)
        map_card.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 8))
        map_card.rowconfigure(1, weight=1)
        map_card.columnconfigure(0, weight=1)

        # Header del mapa
        mhdr = tk.Frame(map_card, bg=SURF, height=36)
        mhdr.grid(row=0, column=0, sticky='ew')
        mhdr.pack_propagate(False)
        tk.Label(mhdr, text='MAPA DE VUELO — BAHÍA SANTA MARTA',
                 bg=SURF, fg=MUTED,
                 font=('Courier New', 8)).pack(side=tk.LEFT, padx=14, pady=10)

        badge_f = tk.Frame(mhdr, bg=SURF)
        badge_f.pack(side=tk.RIGHT, padx=14)
        self._pulse_canvas = tk.Canvas(badge_f, width=8, height=8,
                                        bg=SURF, highlightthickness=0)
        self._pulse_canvas.pack(side=tk.LEFT, pady=10)
        self._pulse_canvas.create_oval(1, 1, 7, 7, fill=GREEN, outline='')
        tk.Label(badge_f, text='EN VIVO', bg=SURF, fg=GREEN,
                 font=('Courier New', 8)).pack(side=tk.LEFT, padx=4)
        self._lbl_map_ts = tk.Label(badge_f, text='', bg=SURF, fg=MUTED,
                                     font=('Courier New', 8))
        self._lbl_map_ts.pack(side=tk.LEFT, padx=(12, 0))

        tk.Frame(map_card, bg=BORDER, height=1).grid(row=0, column=0,
                                                      sticky='ew', pady=(36, 0))

        self._map_canvas = tk.Canvas(map_card, bg='#0d1b2e',
                                      highlightthickness=0)
        self._map_canvas.grid(row=1, column=0, sticky='nsew')
        self._map_canvas.bind('<Configure>', lambda e: self._redraw_map())
        self._map_canvas.bind('<Button-1>', self._click_mapa)

        # Panel inferior: Actividad + Flota
        bottom = tk.Frame(tab, bg=DARK)
        bottom.grid(row=2, column=0, sticky='ew', padx=14, pady=(0, 14))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)

        # Actividad reciente
        act_card = tk.Frame(bottom, bg=SURF, padx=14, pady=12)
        act_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        tk.Label(act_card, text='ACTIVIDAD RECIENTE', bg=SURF, fg=MUTED,
                 font=('Courier New', 8)).pack(anchor='w', pady=(0, 8))
        self._act_frame = tk.Frame(act_card, bg=SURF)
        self._act_frame.pack(fill=tk.X)

        # Estado de flota
        fleet_card = tk.Frame(bottom, bg=SURF, padx=14, pady=12)
        fleet_card.grid(row=0, column=1, sticky='nsew')
        tk.Label(fleet_card, text='ESTADO DE FLOTA', bg=SURF, fg=MUTED,
                 font=('Courier New', 8)).pack(anchor='w', pady=(0, 8))
        self._fleet_frame = tk.Frame(fleet_card, bg=SURF)
        self._fleet_frame.pack(fill=tk.X)

        self._build_fleet_widgets()
        self._build_activity_log()

    def _build_fleet_widgets(self):
        for w in self._fleet_frame.winfo_children():
            w.destroy()
        self._fleet_rows = {}
        for dron in self.sistema.drones.values():
            row = tk.Frame(self._fleet_frame, bg=SURF)
            row.pack(fill=tk.X, pady=3)

            # separador izquierdo de color
            col = COLOR_ESTADO.get(dron.estado, MUTED)
            tk.Frame(row, bg=col, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

            info = tk.Frame(row, bg=SURF)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True)

            top_f = tk.Frame(info, bg=SURF)
            top_f.pack(fill=tk.X)
            lbl_id = tk.Label(top_f, text=dron.id_dron, bg=SURF, fg='white',
                              font=('Courier New', 10, 'bold'))
            lbl_id.pack(side=tk.LEFT)
            lbl_bat = tk.Label(top_f, text=f'{dron.bateria}%',
                               bg=SURF, fg=bat_color(dron.bateria),
                               font=('Courier New', 9))
            lbl_bat.pack(side=tk.RIGHT)

            # mini bat bar
            bat_track = tk.Frame(info, bg=BORDER, height=4)
            bat_track.pack(fill=tk.X, pady=(2, 0))
            bat_fill = tk.Frame(bat_track, bg=bat_color(dron.bateria), height=4)
            bat_fill.place(x=0, y=0, relwidth=dron.bateria / 100)

            self._fleet_rows[dron.id_dron] = {
                'row': row, 'lbl_bat': lbl_bat,
                'bat_fill': bat_fill, 'lbl_id': lbl_id,
            }

    def _build_activity_log(self):
        for w in self._act_frame.winfo_children():
            w.destroy()
        eventos = [
            (GREEN,  'Sistema iniciado. Flota en espera.'),
            (BLUE,   'Mapa aereo cargado con 8 nodos.'),
            (WARN,   'D-03 batería baja detectada.'),
            (DANGER, 'D-04 en mantenimiento programado.'),
        ]
        self._activity_widgets = []
        for color, msg in eventos:
            f = tk.Frame(self._act_frame, bg=SURF, pady=4)
            f.pack(fill=tk.X)
            dot = tk.Canvas(f, width=7, height=7, bg=SURF, highlightthickness=0)
            dot.pack(side=tk.LEFT, pady=3)
            dot.create_oval(1, 1, 6, 6, fill=color, outline='')
            tk.Label(f, text=msg, bg=SURF, fg=TEXT,
                     font=('Courier New', 9)).pack(side=tk.LEFT, padx=6)
            # separador
            tk.Frame(self._act_frame, bg=BORDER, height=1).pack(fill=tk.X)
            self._activity_widgets.append(f)

    def add_activity(self, msg, color=GREEN):
        """Agrega un evento al log de actividad."""
        if not hasattr(self, '_act_frame'):
            return
        for w in self._act_frame.winfo_children():
            w.destroy()
        self._activity_log = getattr(self, '_activity_log', [])
        self._activity_log.insert(0, (color, msg))
        self._activity_log = self._activity_log[:6]

        for color_i, msg_i in self._activity_log:
            f = tk.Frame(self._act_frame, bg=SURF, pady=4)
            f.pack(fill=tk.X)
            dot = tk.Canvas(f, width=7, height=7, bg=SURF, highlightthickness=0)
            dot.pack(side=tk.LEFT, pady=3)
            dot.create_oval(1, 1, 6, 6, fill=color_i, outline='')
            tk.Label(f, text=msg_i[:55], bg=SURF, fg=TEXT,
                     font=('Courier New', 9)).pack(side=tk.LEFT, padx=6)
            tk.Frame(self._act_frame, bg=BORDER, height=1).pack(fill=tk.X)

    # ── MAPA CANVAS ───────────────────────────────────────────────────────────

    def _sc(self, px, py, W, H):
        """Escala coordenadas de espacio base (800×460) a canvas real."""
        sx = W / 800.0
        sy = H / 460.0
        return int(px * sx), int(py * sy)

    def _redraw_map(self):
        c = self._map_canvas
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10 or H < 10:
            # Canvas aún no tiene tamaño — reintentar en 100ms
            self.after(100, self._redraw_map)
            return
        c.delete('all')

        self._draw_map_bg(c, W, H)
        self._draw_map_edges(c, W, H)
        self._draw_map_ziruma(c, W, H)
        self._draw_map_nodes(c, W, H)
        self._draw_map_drones(c, W, H)
        self._draw_map_legend(c, W, H)

    def _draw_map_bg(self, c, W, H):
        # fondo océano oscuro
        c.create_rectangle(0, 0, W, H, fill='#0d1b2e', outline='')

        # grid sutil
        for x in range(0, W, 40):
            c.create_line(x, 0, x, H, fill='#0d1f3a', width=1)
        for y in range(0, H, 40):
            c.create_line(0, y, W, y, fill='#0d1f3a', width=1)

        # Bahía
        bx, by = self._sc(430, 60, W, H)
        c.create_oval(bx - 90, by - 30, bx + 90, by + 50,
                      fill='#081926', outline='#0f2d40', width=1)
        c.create_text(bx, by + 10, text='Bahía de Santa Marta',
                      fill='#1e4a6a', font=('Courier New', 7))

        # Mar Caribe
        cx2, cy2 = self._sc(680, 50, W, H)
        c.create_text(cx2, cy2, text='MAR CARIBE',
                      fill='#1e4a6a', font=('Courier New', 8, 'bold'))

        # Sierra Nevada
        sx2, sy2 = self._sc(620, 390, W, H)
        c.create_oval(sx2 - 55, sy2 - 30, sx2 + 55, sy2 + 30,
                      fill='#0d1e0a', outline='#1a3a12')
        c.create_text(sx2, sy2 + 5, text='Sierra Nevada',
                      fill='#2a5020', font=('Courier New', 6))

    def _draw_map_edges(self, c, W, H):
        for n1, n2 in ARISTAS:
            if n1 not in NODO_POS or n2 not in NODO_POS:
                continue
            x1, y1 = self._sc(*NODO_POS[n1], W, H)
            x2, y2 = self._sc(*NODO_POS[n2], W, H)
            c.create_line(x1, y1, x2, y2,
                          fill='#2a5070', width=1.5,
                          dash=(5, 4))
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            dx = NODO_POS[n2][0] - NODO_POS[n1][0]
            dy = NODO_POS[n2][1] - NODO_POS[n1][1]
            dist = math.hypot(dx, dy) * 0.01
            c.create_text(mx, my - 7, text=f'{dist:.1f}km',
                          fill='#3a6080', font=('Courier New', 6))

    def _draw_map_ziruma(self, c, W, H):
        zx, zy = self._sc(*NODO_POS['ZIRUMA'], W, H)
        r = int(42 * min(W / 800, H / 460))

        c.create_oval(zx - r - 8, zy - r - 8, zx + r + 8, zy + r + 8,
                      outline='#3d0a0a', width=1, dash=(4, 6))
        c.create_oval(zx - r, zy - r, zx + r, zy + r,
                      fill='#1a0505', outline=DANGER, width=2)

        ri = 12
        c.create_oval(zx - ri, zy - ri, zx + ri, zy + ri,
                      fill='#2a0808', outline=DANGER, width=2)
        c.create_line(zx - ri + 3, zy + ri - 3, zx + ri - 3, zy - ri + 3,
                      fill=DANGER, width=2)
        c.create_text(zx, zy + r + 12, text='⛔ Ziruma',
                      fill=DANGER, font=('Courier New', 7, 'bold'))

    def _draw_map_nodes(self, c, W, H):
        from estructuras.grafo import ZONAS_EXCLUIDAS
        for nid, nodo in self.sistema.mapa.nodos.items():
            if nid not in NODO_POS or nid == 'ZIRUMA':
                continue
            x, y = self._sc(*NODO_POS[nid], W, H)
            color = NODO_COLOR.get(nodo.tipo, MUTED)

            if nodo.tipo == 'excluido':
                c.create_rectangle(x - 7, y - 4, x + 7, y + 4,
                                   fill='#1a0505', outline=DANGER)
                c.create_text(x, y + 12, text=nodo.nombre[:10],
                              fill='#7f3333', font=('Courier New', 6))
                continue

            r = 13 if nodo.tipo == 'almacen' else 10 if nodo.tipo == 'recarga' else 9

            # Halo sutil
            _halo_dash = (3, 5) if nodo.tipo != 'almacen' else ()
            halo_kw = {'dash': _halo_dash} if _halo_dash else {}
            c.create_oval(x - r - 5, y - r - 5, x + r + 5, y + r + 5,
                          fill='', outline=color, width=1, **halo_kw)

            fill_c = '#0f1e2e' if nodo.tipo != 'almacen' else '#0d1e30'
            c.create_oval(x - r, y - r, x + r, y + r,
                          fill=fill_c, outline=color, width=2)

            if nodo.tipo == 'almacen':
                c.create_text(x, y, text='◈', fill=color,
                              font=('Courier New', 11, 'bold'))
            elif nodo.tipo == 'recarga':
                c.create_text(x, y, text='⚡', fill=color,
                              font=('Courier New', 8))
            else:
                c.create_oval(x - 3, y - 3, x + 3, y + 3,
                              fill=color, outline='')

            # Etiqueta
            lbl = nodo.nombre
            lx = x + r + 5
            c.create_text(lx, y, text=lbl, fill=color,
                          font=('Courier New', 7, 'bold'), anchor='w')

    def _draw_map_drones(self, c, W, H):
        tick = self._tick_count / 10.0
        yi = 10  # posición Y de las barras de progreso

        for dron in self.sistema.drones.values():
            if dron.estado not in ('en_vuelo', 'bateria_baja'):
                continue
            if dron.id_dron not in self._drone_states:
                continue
            s = self._drone_states[dron.id_dron]

            # Coordenadas canvas
            px, py = self._sc(s['x'], s['y'], W, H)
            tx, ty = self._sc(s['tx'], s['ty'], W, H)

            # Ruta punteada
            c.create_line(px, py, tx, ty,
                          fill='#1e4a8a',
                          dash=(4, 6), width=1.5,
                          stipple='gray50')

            # Estela
            if len(s['trail']) > 1:
                pts = []
                for pt in s['trail'][-12:]:
                    px2, py2 = self._sc(pt[0], pt[1], W, H)
                    pts.extend([px2, py2])
                if len(pts) >= 4:
                    c.create_line(pts, fill='#0d6b4a', width=1.5)

            # Pulse ring animado
            pr = 7 + int(3 * math.sin(tick * 3))
            is_low = dron.bateria < 30
            # ring color handled by outline below
            c.create_oval(px - pr - 4, py - pr - 4,
                          px + pr + 4, py + pr + 4,
                          fill='', outline=DANGER if is_low else GREEN,
                          width=1)

            # Cuerpo del dron (triángulo orientado)
            dx = s['tx'] - s['x']
            dy = s['ty'] - s['y']
            ang = math.atan2(dy, dx)
            sz = 8
            pts = [
                px + sz * math.cos(ang),       py + sz * math.sin(ang),
                px + sz * math.cos(ang + 2.4), py + sz * math.sin(ang + 2.4),
                px + sz * math.cos(ang - 2.4), py + sz * math.sin(ang - 2.4),
            ]
            c.create_polygon(pts, fill=DANGER if is_low else GREEN, outline='')

            # Propelas (4 puntos)
            for ox, oy in [(-3, -4), (3, -4), (3, 4), (-3, 4)]:
                rx = px + ox * math.cos(ang) - oy * math.sin(ang)
                ry = py + ox * math.sin(ang) + oy * math.cos(ang)
                c.create_oval(rx - 2, ry - 2, rx + 2, ry + 2,
                              outline='#7f7f7f', width=1)

            # Etiqueta del dron
            prog = int(s['prog'] * 100)
            label = f'{dron.id_dron} {prog}%'
            lw = len(label) * 7 + 10
            c.create_rectangle(px - lw // 2, py - 26,
                                px + lw // 2, py - 13,
                                fill='#0a0e1a', outline='')
            c.create_text(px, py - 19, text=label,
                          fill='white', font=('Courier New', 8, 'bold'))

            # Barra de progreso en esquina superior-izquierda
            bw = 120
            c.create_rectangle(10, yi, 10 + bw + 40, yi + 20,
                                fill='#0a0e1a', outline='')
            c.create_text(14, yi + 10,
                          text=dron.id_dron, fill=DANGER if is_low else GREEN,
                          font=('Courier New', 8, 'bold'), anchor='w')
            c.create_rectangle(48, yi + 6, 48 + bw, yi + 14,
                               fill=BORDER, outline='')
            fill_w = int(bw * s['prog'])
            bar_col = (DANGER if prog < 25 else WARN if prog < 60 else GREEN)
            if fill_w > 0:
                c.create_rectangle(48, yi + 6, 48 + fill_w, yi + 14,
                                   fill=bar_col, outline='')
            c.create_text(172, yi + 10, text=f'{prog}%',
                          fill='#aabbcc',
                          font=('Courier New', 7), anchor='w')
            yi += 26

    def _draw_map_legend(self, c, W, H):
        items = [
            ('◈ Almacén', BLUE),
            ('● Destino',  GREEN),
            ('⚡ Recarga',  WARN),
            ('⛔ Excluido', DANGER),
        ]
        lx, ly = 10, H - 20
        total_w = len(items) * 90
        c.create_rectangle(lx - 4, ly - 12, lx + total_w, ly + 12,
                           fill='#07131a', outline=BORDER)
        for i, (txt, col) in enumerate(items):
            c.create_text(lx + i * 90, ly, text=txt, fill=col,
                          font=('Courier New', 7, 'bold'), anchor='w')

    def _click_mapa(self, event):
        W = self._map_canvas.winfo_width()
        H = self._map_canvas.winfo_height()
        for nid, (nx, ny) in NODO_POS.items():
            cx, cy = self._sc(nx, ny, W, H)
            if abs(event.x - cx) < 18 and abs(event.y - cy) < 18:
                nodo = self.sistema.mapa.nodos.get(nid)
                if nodo and nodo.tipo != 'excluido':
                    self._mostrar_info_nodo(nid)
                return

    def _mostrar_info_nodo(self, nid):
        info = self.sistema.info_nodo(nid)
        if not info:
            return
        color = NODO_COLOR.get(info['tipo'], MUTED)
        nombre = info['nombre']
        tipo   = info['tipo'].capitalize()
        coords = f"{info['lat']:.4f}°N  {abs(info['lon']):.4f}°W"
        conex  = info['conexiones']
        drones_ahi = ', '.join(info['drones']) or 'Ninguno'

        msg = (f"📍 {nombre}\n"
               f"Tipo: {tipo}\n"
               f"Coords: {coords}\n"
               f"Rutas: {conex}\n"
               f"Drones: {drones_ahi}")

        if nid != 'ALMACEN':
            if messagebox.askyesno('Nodo seleccionado',
                                    msg + '\n\n¿Calcular ruta A* desde Almacén?',
                                    parent=self):
                self._calc_ruta(nid)
        else:
            messagebox.showinfo('Almacén Central', msg, parent=self)

    def _calc_ruta(self, destino):
        ruta, dist = self.sistema.calcular_ruta('ALMACEN', destino)
        if ruta:
            nombres = [self.sistema.mapa.nodos[n].nombre
                       for n in ruta if n in self.sistema.mapa.nodos]
            messagebox.showinfo(
                'Ruta A* calculada',
                f"Ruta: {' → '.join(nombres)}\n"
                f"Distancia: {dist:.2f} km\n"
                f"Nodos: {len(ruta)}\n\n"
                f"Evita Ziruma y Aeropuerto.",
                parent=self)
            self.add_activity(f'Ruta calculada → {destino} ({dist:.1f}km)', BLUE)
        else:
            messagebox.showwarning('Sin ruta',
                                    'No se encontró ruta disponible.',
                                    parent=self)

    # ── TAB PEDIDOS ───────────────────────────────────────────────────────────

    def _build_pedidos_tab(self):
        tab = self._tab_frames['pedidos']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Toolbar
        tb = tk.Frame(tab, bg=DARK, pady=10)
        tb.grid(row=0, column=0, sticky='ew', padx=14)

        self._search_ped = tk.Entry(tb, bg=SURF, fg=TEXT, insertbackground=BLUE,
                                    relief=tk.FLAT, font=('Courier New', 10), width=40,
                                    highlightthickness=1, highlightbackground=BORDER)
        self._search_ped.insert(0, 'Buscar pedido, destino...')
        self._search_ped.bind('<FocusIn>', lambda e: (
            self._search_ped.delete(0, tk.END)
            if self._search_ped.get().startswith('Buscar') else None))
        self._search_ped.bind('<KeyRelease>', lambda e: self._refresh_pedidos_table())
        self._search_ped.pack(side=tk.LEFT, ipady=6, padx=(0, 8))

        from gui.ventana_pedido import VentanaPedido
        tk.Button(tb, text='+ Nuevo pedido', bg=BLUE, fg='white',
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'), padx=10,
                  command=lambda: VentanaPedido(self, self.sistema, self.actualizar)
                  ).pack(side=tk.LEFT)

        tk.Button(tb, text='⚡ Despachar', bg=GREEN, fg=DARK,
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'), padx=10,
                  command=self._despachar).pack(side=tk.LEFT, padx=8)

        # Tabla
        wrap = tk.Frame(tab, bg=SURF, bd=0)
        wrap.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 14))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Ped.Treeview', background=SURF2, foreground=TEXT,
                        fieldbackground=SURF2, font=('Courier New', 10),
                        rowheight=30, borderwidth=0)
        style.configure('Ped.Treeview.Heading', background=SURF,
                        foreground=MUTED, font=('Courier New', 8),
                        relief='flat')
        style.map('Ped.Treeview', background=[('selected', '#1e3040')])

        cols = ('ID', 'Destino', 'Tipo', 'Prioridad', 'Peso kg', 'Hora', 'Estado')
        self._tree_ped = ttk.Treeview(wrap, columns=cols, show='headings',
                                       style='Ped.Treeview')
        anchos = [65, 160, 110, 80, 65, 60, 80]
        for col, aw in zip(cols, anchos):
            self._tree_ped.heading(col, text=col.upper())
            self._tree_ped.column(col, width=aw, anchor='center')
        self._tree_ped.grid(row=0, column=0, sticky='nsew')

        sb = ttk.Scrollbar(wrap, orient='vertical',
                           command=self._tree_ped.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self._tree_ped.configure(yscrollcommand=sb.set)

        self._refresh_pedidos_table()

    def _refresh_pedidos_table(self):
        for row in self._tree_ped.get_children():
            self._tree_ped.delete(row)
        q = self._search_ped.get().lower()
        if q.startswith('buscar'):
            q = ''
        COLOR_PRI = {'ALTA': DANGER, 'MEDIA': WARN, 'BAJA': GREEN}
        for p in self.sistema.cola_pedidos.a_lista():
            if q and q not in p.destino_nombre.lower() and q not in p.id_pedido.lower():
                continue
            self._tree_ped.insert('', 'end', iid=p.id_pedido,
                                   values=(p.id_pedido, p.destino_nombre,
                                           p.tipo, p.prioridad,
                                           f'{p.peso_kg:.1f}',
                                           p.hora_ingreso or '--',
                                           p.estado.upper()))

    # ── TAB DRONES ────────────────────────────────────────────────────────────

    def _build_drones_tab(self):
        tab = self._tab_frames['drones']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        tb = tk.Frame(tab, bg=DARK, pady=10)
        tb.grid(row=0, column=0, sticky='ew', padx=14)
        from gui.ventana_dron import VentanaDron
        tk.Button(tb, text='+ Gestionar drones', bg=GREEN, fg=DARK,
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'), padx=10,
                  command=lambda: VentanaDron(self, self.sistema, self.actualizar)
                  ).pack(side=tk.LEFT)

        scroll_f = tk.Frame(tab, bg=DARK)
        scroll_f.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 14))
        self._drones_grid_frame = scroll_f
        self._refresh_drones_grid()

    def _refresh_drones_grid(self):
        for w in self._drones_grid_frame.winfo_children():
            w.destroy()

        drones = list(self.sistema.drones.values())
        cols = 3
        for i, dron in enumerate(drones):
            r, c = divmod(i, cols)
            self._drones_grid_frame.columnconfigure(c, weight=1)
            col = COLOR_ESTADO.get(dron.estado, MUTED)

            card = tk.Frame(self._drones_grid_frame, bg=SURF, bd=0, padx=14, pady=12)
            card.grid(row=r, column=c, sticky='nsew', padx=(0 if c == 0 else 8, 0),
                      pady=(0 if r == 0 else 8, 0))

            # Franja superior
            tk.Frame(card, bg=col, height=2).pack(fill=tk.X, pady=(0, 8))

            hdr = tk.Frame(card, bg=SURF)
            hdr.pack(fill=tk.X)
            tk.Label(hdr, text=dron.id_dron, bg=SURF, fg='white',
                     font=('Courier New', 14, 'bold')).pack(side=tk.LEFT)

            # Botones
            btn_f = tk.Frame(hdr, bg=SURF)
            btn_f.pack(side=tk.RIGHT)
            from gui.ventana_dron import VentanaDron
            tk.Button(btn_f, text='✎', bg=SURF, fg=MUTED, relief=tk.FLAT,
                      cursor='hand2', font=('Courier New', 9),
                      highlightthickness=1, highlightbackground=BORDER,
                      command=lambda: VentanaDron(self, self.sistema, self.actualizar)
                      ).pack(side=tk.LEFT, padx=2)

            tk.Label(card, text=dron.modelo, bg=SURF, fg=MUTED,
                     font=('Courier New', 8)).pack(anchor='w', pady=(2, 0))

            # Batería
            bat_track = tk.Frame(card, bg=BORDER, height=5)
            bat_track.pack(fill=tk.X, pady=(8, 4))
            fill_w = max(2, int(dron.bateria))
            bat_fill = tk.Frame(bat_track, bg=bat_color(dron.bateria), height=5)
            bat_fill.place(x=0, y=0, relwidth=dron.bateria / 100)

            tk.Label(card, text=f'Batería: {dron.bateria}%', bg=SURF, fg=MUTED,
                     font=('Courier New', 8)).pack(anchor='w')

            # Estado
            est_f = tk.Frame(card, bg=SURF)
            est_f.pack(anchor='w', pady=(6, 0))
            dot = tk.Canvas(est_f, width=7, height=7, bg=SURF, highlightthickness=0)
            dot.pack(side=tk.LEFT, pady=2)
            dot.create_oval(1, 1, 6, 6, fill=col, outline='')
            lbl = dron.estado.replace('_', ' ').title()
            tk.Label(est_f, text=lbl, bg=SURF, fg=col,
                     font=('Courier New', 9)).pack(side=tk.LEFT, padx=4)

    # ── TAB INVENTARIO ────────────────────────────────────────────────────────

    def _build_inventario_tab(self):
        tab = self._tab_frames['inventario']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        tb = tk.Frame(tab, bg=DARK, pady=10)
        tb.grid(row=0, column=0, sticky='ew', padx=14)
        from gui.ventana_inventario import VentanaInventario
        tk.Button(tb, text='+ Gestionar inventario', bg=GREEN, fg=DARK,
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'), padx=10,
                  command=lambda: VentanaInventario(self, self.sistema)
                  ).pack(side=tk.LEFT)

        # Grid de productos
        scroll_f = tk.Frame(tab, bg=DARK)
        scroll_f.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 14))
        self._inv_grid_frame = scroll_f
        self._refresh_inventario_grid()

        # Canvas AVL (parte inferior)
        avl_card = tk.Frame(tab, bg=SURF, bd=0)
        avl_card.grid(row=2, column=0, sticky='ew', padx=14, pady=(0, 14))
        tk.Label(avl_card, text='ÁRBOL AVL — INVENTARIO',
                 bg=SURF, fg=MUTED, font=('Courier New', 8)).pack(anchor='w',
                                                                    padx=14, pady=(8, 4))
        self._avl_canvas = tk.Canvas(avl_card, bg=SURF2, height=180,
                                      highlightthickness=0)
        self._avl_canvas.pack(fill=tk.X, padx=14, pady=(0, 10))
        self.after(120, self._draw_avl)

    def _refresh_inventario_grid(self):
        for w in self._inv_grid_frame.winfo_children():
            w.destroy()
        productos = self.sistema.lista_productos()
        cols = 3
        for i, p in enumerate(productos):
            r, c = divmod(i, cols)
            self._inv_grid_frame.columnconfigure(c, weight=1)
            stock_col = (DANGER if p.stock < 5 else
                         WARN   if p.stock < 10 else GREEN)

            card = tk.Frame(self._inv_grid_frame, bg=SURF, padx=12, pady=10)
            card.grid(row=r, column=c, sticky='nsew',
                      padx=(0 if c == 0 else 8, 0),
                      pady=(0 if r == 0 else 8, 0))

            # Barra lateral de stock
            tk.Frame(card, bg=stock_col, width=3).pack(side=tk.LEFT, fill=tk.Y,
                                                        padx=(0, 8))

            info = tk.Frame(card, bg=SURF)
            info.pack(fill=tk.X, expand=True)

            tk.Label(info, text=p.nombre, bg=SURF, fg='white',
                     font=('Courier New', 10, 'bold')).pack(anchor='w')
            tk.Label(info, text=p.categoria.upper(), bg=SURF, fg=MUTED,
                     font=('Courier New', 7)).pack(anchor='w', pady=(1, 6))

            for lbl, val in [('Stock', f'{p.stock} uds{"  ⚠" if p.stock < 5 else ""}'),
                              ('Peso',  f'{p.peso_kg} kg'),
                              ('ID',    str(p.id_producto))]:
                row_f = tk.Frame(info, bg=SURF)
                row_f.pack(fill=tk.X)
                tk.Label(row_f, text=lbl, bg=SURF, fg=MUTED,
                         font=('Courier New', 8)).pack(side=tk.LEFT)
                tk.Label(row_f, text=val, bg=SURF, fg=stock_col if lbl == 'Stock' else TEXT,
                         font=('Courier New', 8)).pack(side=tk.RIGHT)

    def _draw_avl(self):
        c = self._avl_canvas
        c.delete('all')
        W = c.winfo_width()
        H = c.winfo_height() or 180
        if W < 10:
            return

        nodos = self.sistema.inventario.obtener_nodos_visualizacion()
        if not nodos:
            c.create_text(W // 2, H // 2, text='Árbol vacío', fill=MUTED,
                          font=('Courier New', 10))
            return

        max_nivel = max(n['nivel'] for n in nodos)
        nivel_h = H / (max_nivel + 2)
        posiciones = {}

        by_level = {}
        for n in nodos:
            by_level.setdefault(n['nivel'], []).append(n)

        for nivel, lista in by_level.items():
            count = len(lista)
            for i, n in enumerate(lista):
                x = W * (i + 1) / (count + 1)
                y = nivel_h * (nivel + 1)
                posiciones[n['id']] = (x, y)

        # Aristas
        for n in nodos:
            if n['padre'] is not None and n['padre'] in posiciones and n['id'] in posiciones:
                x1, y1 = posiciones[n['padre']]
                x2, y2 = posiciones[n['id']]
                c.create_line(x1, y1, x2, y2, fill=BORDER, width=1.5)

        # Nodos
        r = 18
        for n in nodos:
            if n['id'] not in posiciones:
                continue
            x, y = posiciones[n['id']]
            col = BLUE if n['padre'] is None else TEXT
            c.create_oval(x - r, y - r, x + r, y + r,
                          fill=SURF2, outline=col, width=2)
            c.create_text(x, y, text=str(n['id']),
                          fill=col, font=('Courier New', 9, 'bold'))
            c.create_text(x + r + 2, y - r + 2,
                          text=f'FE:{n["fe"]}',
                          fill=MUTED, font=('Courier New', 6), anchor='w')

    # ── ACCIONES ──────────────────────────────────────────────────────────────

    def _despachar(self):
        dron, msg = self.sistema.despachar_siguiente()
        if dron:
            dest_id = (dron.pedido_actual.destino_id
                       if dron.pedido_actual else None)
            if dest_id and dest_id in NODO_POS:
                tx, ty = NODO_POS[dest_id]
                self._drone_states[dron.id_dron] = {
                    'x': 400.0, 'y': 230.0,
                    'tx': float(tx), 'ty': float(ty),
                    'prog': 0.0, 'trail': [],
                    'returning': False, 'wait': 0,
                }
            self.add_activity(f'{dron.id_dron} despachado → {dron.pedido_actual.destino_nombre if dron.pedido_actual else "?"}', GREEN)
            messagebox.showinfo('Despacho exitoso', msg, parent=self)
        else:
            messagebox.showwarning('No se pudo despachar', msg, parent=self)
        self.actualizar()

    def actualizar(self):
        self._update_stats()
        self._update_fleet_panel()
        self._refresh_pedidos_table()
        self._refresh_drones_grid()
        self._refresh_inventario_grid()
        self._redraw_map()

    # ── CICLO DE TICK ─────────────────────────────────────────────────────────

    def _tick(self):
        self._tick_count += 1
        now = datetime.datetime.now()
        self._lbl_clock.config(text=now.strftime('%H:%M:%S'))
        ts = now.strftime('%H:%M:%S')
        if hasattr(self, '_lbl_map_ts'):
            self._lbl_map_ts.config(text=f'Actualizado {ts}')

        self._step_drones()
        self._update_stats()
        self._update_fleet_panel()

        if self._tab_actual == 'panel':
            self._redraw_map()

        self.after(600, self._tick)

    def _step_drones(self):
        SPEED = 0.018
        BASE_X, BASE_Y = 400.0, 230.0
        for dron in self.sistema.drones.values():
            if dron.estado not in ('en_vuelo', 'bateria_baja'):
                self._drone_states.pop(dron.id_dron, None)
                continue
            if dron.id_dron not in self._drone_states:
                dest = NODO_POS.get(
                    dron.pedido_actual.destino_id if dron.pedido_actual else 'CENTRO',
                    (500, 280))
                self._drone_states[dron.id_dron] = {
                    'x': BASE_X, 'y': BASE_Y,
                    'tx': float(dest[0]), 'ty': float(dest[1]),
                    'prog': 0.0, 'trail': [], 'returning': False, 'wait': 0
                }

            s = self._drone_states[dron.id_dron]
            if s.get('wait', 0) > 0:
                s['wait'] -= 1
                continue

            s['trail'].append((s['x'], s['y']))
            if len(s['trail']) > 20:
                s['trail'].pop(0)

            if not s['returning']:
                s['prog'] = min(1.0, s['prog'] + SPEED)
                s['x'] += (s['tx'] - s['x']) * SPEED * 3
                s['y'] += (s['ty'] - s['y']) * SPEED * 3
                if s['prog'] >= 1.0:
                    s['returning'] = True
                    s['wait'] = 4
                    s['prog'] = 0.0
            else:
                s['prog'] = min(1.0, s['prog'] + SPEED)
                s['x'] += (BASE_X - s['x']) * SPEED * 3
                s['y'] += (BASE_Y - s['y']) * SPEED * 3
                if s['prog'] >= 1.0:
                    s['returning'] = False
                    s['prog'] = 0.0

    def _update_stats(self):
        if not hasattr(self, '_stat_lbls'):
            return
        pedidos_n = len(self.sistema.cola_pedidos)
        en_vuelo  = sum(1 for d in self.sistema.drones.values()
                        if d.estado == 'en_vuelo')
        bat_baja  = sum(1 for d in self.sistema.drones.values()
                        if d.bateria < 30)
        stock_crit = sum(1 for p in self.sistema.lista_productos()
                         if p.stock < 5)

        self._stat_lbls['stat_pedidos'].config(text=str(pedidos_n))
        self._stat_lbls['stat_vuelo'].config(text=str(en_vuelo))
        self._stat_lbls['stat_batbaja'].config(text=str(bat_baja))
        self._stat_lbls['stat_stock'].config(text=str(stock_crit))

    def _update_fleet_panel(self):
        if not hasattr(self, '_fleet_rows'):
            return
        for dron in self.sistema.drones.values():
            w = self._fleet_rows.get(dron.id_dron)
            if not w:
                continue
            col = bat_color(dron.bateria)
            w['lbl_bat'].config(text=f'{dron.bateria}%', fg=col)
            w['bat_fill'].place(relwidth=dron.bateria / 100)
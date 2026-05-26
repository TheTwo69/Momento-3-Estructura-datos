# ventana_principal.py — LogiDrone-UCC v4 TACTICAL
# Rediseño completo: HUD táctico futurista, mapa GIS avanzado, glow neón
# Inspirado en centros de comando militares y GIS dark mode
# Fuente: Courier New (monospace táctico) + efectos sci-fi

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import math
import random
import sys

# ── PALETA TÁCTICA ────────────────────────────────────────────────────────────
C_BG        = '#07111F'      # Fondo ultra oscuro
C_SURF      = '#0B1929'      # Superficie de card
C_SURF2     = '#0F2035'      # Superficie secundaria
C_BORDER    = '#1A3A5C'      # Borde estándar
C_BORDER2   = '#0E2844'      # Borde sutil

C_CYAN      = '#00E5FF'      # Cyan neón principal
C_CYAN_DIM  = '#007A8C'      # Cyan apagado
C_CYAN_GLOW = '#00CCEE'      # Cyan para glow
C_BLUE      = '#3B82F6'      # Azul eléctrico
C_BLUE_DIM  = '#1E4A9A'      # Azul atenuado
C_GREEN     = '#00FF9C'      # Verde operativo
C_GREEN_DIM = '#00805A'      # Verde atenuado
C_YELLOW    = '#FFC857'      # Amarillo alerta
C_RED       = '#FF4D6D'      # Rojo crítico
C_RED_DIM   = '#7A1E30'      # Rojo atenuado

C_TEXT      = '#C8D8E8'      # Texto principal
C_MUTED     = '#4A6A8A'      # Texto secundario
C_WHITE     = '#E8F4FF'      # Blanco frío

# ── POSICIONES NODOS (canvas 800x460 virtual) ─────────────────────────────────
NODO_POS = {
    'ALMACEN':    (400, 230),
    'RODADERO':   (200, 370),
    'TAGANGA':    (610, 100),
    'CENTRO':     (490, 280),
    'BELLO':      (240, 250),
    'MINCA':      (310, 410),
    'RECARGA_N':  (660, 175),
    'RECARGA_S':  (320, 330),
    'ZIRUMA':     (555, 175),
    'AEROPUERTO': (180, 430),
}

ARISTAS = [
    ('ALMACEN',   'CENTRO'),
    ('ALMACEN',   'BELLO'),
    ('ALMACEN',   'RECARGA_S'),
    ('ALMACEN',   'RECARGA_N'),
    ('RECARGA_N', 'TAGANGA'),
    ('RECARGA_N', 'CENTRO'),
    ('RECARGA_S', 'RODADERO'),
    ('RECARGA_S', 'BELLO'),
    ('BELLO',     'RODADERO'),
    ('RODADERO',  'MINCA'),
]

NODO_TIPO_COLOR = {
    'almacen':  C_BLUE,
    'destino':  C_GREEN,
    'recarga':  C_YELLOW,
    'excluido': C_RED,
}

ESTADO_COLOR = {
    'en_vuelo':      C_CYAN,
    'en_espera':     C_BLUE,
    'bateria_baja':  C_RED,
    'mantenimiento': C_YELLOW,
}

def bat_color(pct):
    if pct < 25: return C_RED
    if pct < 60: return C_YELLOW
    return C_GREEN


class VentanaPrincipal(tk.Tk):
    def __init__(self, sistema):
        super().__init__()
        self.sistema = sistema

        # ── CORRECCIÓN DE NITIDEZ (HiDPI / Retina) ───────────────────────────
        # tk.call con 'tk', 'scaling' ajusta el factor de escala interno de
        # tkinter para que los widgets, fuentes y canvas se rendericen nítidos.
        # En Windows con DPI 150% esto equivale a ~1.5; en Full HD normal es 1.0.
        try:
            # Detectar DPI real del monitor en Windows
            if sys.platform == 'win32':
                import ctypes
                hdc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                scale = dpi / 96.0          # 96 DPI = escala 1.0 (100%)
            else:
                scale = 1.0
            self.tk.call('tk', 'scaling', scale)
        except Exception:
            pass

        self.title('LogiDrone-UCC  ◈  CENTRO DE OPERACIONES TÁTICAS  ◈  BAHÍA SANTA MARTA')
        self.geometry('1400x820')
        self.minsize(1200, 700)
        self.configure(bg=C_BG)

        self._tick_count   = 0
        self._drone_states = {}
        self._anim_tick    = 0.0
        self._tab_actual   = 'panel'
        self._tab_frames   = {}
        self._stat_lbls    = {}
        self._activity_log = []
        self._particles    = []   # partículas de fondo del mapa
        self._scan_offset  = 0    # offset de scanline

        self._init_drone_states()
        self._init_particles()
        self._build_ui()
        self._tick()

    # ── INICIALIZACIÓN ────────────────────────────────────────────────────────
    def _init_drone_states(self):
        BASE_X, BASE_Y = 400.0, 230.0
        for dron in self.sistema.drones.values():
            if dron.estado == 'en_vuelo' and dron.pedido_actual:
                tx, ty = NODO_POS.get(dron.pedido_actual.destino_id, (500, 300))
            else:
                tx = BASE_X + random.uniform(-50, 50)
                ty = BASE_Y + random.uniform(-30, 30)
            self._drone_states[dron.id_dron] = {
                'x': BASE_X, 'y': BASE_Y,
                'tx': float(tx), 'ty': float(ty),
                'prog': random.uniform(0, 0.5) if dron.estado == 'en_vuelo' else 0.0,
                'trail': [],
                'returning': False,
                'wait': 0,
                'pulse': random.uniform(0, math.pi * 2),
            }

    def _init_particles(self):
        """Partículas flotantes de fondo para el mapa."""
        self._particles = []
        for _ in range(40):
            self._particles.append({
                'x': random.uniform(0, 800),
                'y': random.uniform(0, 460),
                'vx': random.uniform(-0.2, 0.2),
                'vy': random.uniform(-0.2, 0.2),
                'r': random.uniform(0.5, 1.5),
                'alpha': random.uniform(0.2, 0.8),
            })

    # ── CONSTRUCCIÓN DE UI ────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()
        self._build_statusbar()
        self._build_tabs()
        self._switch_tab('panel')

    def _build_topbar(self):
        bar = tk.Frame(self, bg=C_SURF, height=58)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # Logo táctico
        logo_frame = tk.Frame(bar, bg=C_SURF)
        logo_frame.pack(side=tk.LEFT, padx=(16, 0), pady=8)

        logo_canvas = tk.Canvas(logo_frame, width=40, height=40, bg=C_SURF, highlightthickness=0)
        logo_canvas.pack(side=tk.LEFT, padx=(0, 12))
        # Hexágono táctico
        cx, cy, r = 20, 20, 18
        pts = []
        for i in range(6):
            ang = math.pi / 6 + i * math.pi / 3
            pts += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
        logo_canvas.create_polygon(pts, fill=C_SURF2, outline=C_CYAN, width=1.5)
        logo_canvas.create_polygon(pts, fill='', outline=C_CYAN_GLOW, width=0.5)
        logo_canvas.create_text(cx, cy, text='LD', fill=C_CYAN, font=('Courier New', 10, 'bold'))

        text_frame = tk.Frame(logo_frame, bg=C_SURF)
        text_frame.pack(side=tk.LEFT)
        tk.Label(text_frame, text='LOGIDRONE-UCC', bg=C_SURF, fg=C_WHITE,
                 font=('Courier New', 13, 'bold')).pack(anchor='w')
        tk.Label(text_frame, text='CENTRO DE CONTROL TÁCTICO  ▸  OPERACIÓN BAHÍA SANTA MARTA',
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 7)).pack(anchor='w')

        # Separador vertical luminoso
        sep = tk.Frame(bar, bg=C_CYAN, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=16)

        # Navegación
        nav_frame = tk.Frame(bar, bg=C_SURF)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._nav_buttons = {}

        nav_tabs = [
            ('panel',      '◈  PANEL'),
            ('pedidos',    '▶  PEDIDOS'),
            ('drones',     '✦  DRONES'),
            ('inventario', '⊞  INVENTARIO'),
        ]
        for key, label in nav_tabs:
            btn = tk.Button(nav_frame, text=label, bg=C_SURF, fg=C_MUTED,
                            relief=tk.FLAT, cursor='hand2',
                            font=('Courier New', 9, 'bold'),
                            activebackground=C_SURF2, activeforeground=C_CYAN,
                            padx=18, pady=0, bd=0,
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side=tk.LEFT, fill=tk.Y)
            self._nav_buttons[key] = btn

        # Botón despachar (derecha)
        sep2 = tk.Frame(bar, bg=C_BORDER, width=1)
        sep2.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=4)

        tk.Button(bar, text='  ⚡  DESPACHAR  ', bg=C_CYAN, fg=C_BG,
                  relief=tk.FLAT, cursor='hand2',
                  font=('Courier New', 9, 'bold'),
                  activebackground=C_CYAN_GLOW, activeforeground=C_BG,
                  command=self._despachar).pack(side=tk.RIGHT, pady=14, padx=12)

        # Reloj
        self._lbl_clock = tk.Label(bar, text='', bg=C_SURF, fg=C_GREEN,
                                    font=('Courier New', 11, 'bold'))
        self._lbl_clock.pack(side=tk.RIGHT, padx=16)

        # Indicador en vivo
        live_f = tk.Frame(bar, bg=C_SURF)
        live_f.pack(side=tk.RIGHT, padx=8)
        self._pulse_dot = tk.Canvas(live_f, width=8, height=8, bg=C_SURF, highlightthickness=0)
        self._pulse_dot.pack(side=tk.LEFT, pady=20)
        self._pulse_dot.create_oval(1, 1, 7, 7, fill=C_GREEN, outline='', tags='dot')
        tk.Label(live_f, text='EN VIVO', bg=C_SURF, fg=C_GREEN, font=('Courier New', 7, 'bold')).pack(side=tk.LEFT, padx=4)

        # Línea inferior neón
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)
        tk.Frame(self, bg=C_BG, height=1).pack(fill=tk.X)

    def _build_statusbar(self):
        """Barra inferior de estado."""
        self._status_bar = tk.Frame(self, bg=C_SURF2, height=22)
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_bar.pack_propagate(False)

        self._lbl_status = tk.Label(self._status_bar,
                                     text='◈ SISTEMA OPERATIVO  |  TODOS LOS SUBSISTEMAS EN LÍNEA  |  A* PATHFINDING ACTIVO  |  COLA FIFO LISTA  |  AVL SINCRONIZADO',
                                     bg=C_SURF2, fg=C_MUTED, font=('Courier New', 7))
        self._lbl_status.pack(side=tk.LEFT, padx=12)

        tk.Label(self._status_bar, text='v4.0 TACTICAL', bg=C_SURF2, fg=C_BORDER,
                 font=('Courier New', 7)).pack(side=tk.RIGHT, padx=12)
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

    def _build_tabs(self):
        self._container = tk.Frame(self, bg=C_BG)
        self._container.pack(fill=tk.BOTH, expand=True)
        for key in ('panel', 'pedidos', 'drones', 'inventario'):
            f = tk.Frame(self._container, bg=C_BG)
            self._tab_frames[key] = f

        self._build_panel_tab()
        self._build_pedidos_tab()
        self._build_drones_tab()
        self._build_inventario_tab()

    def _switch_tab(self, key):
        if key not in self._tab_frames: return
        self._tab_actual = key
        for k, f in self._tab_frames.items(): f.pack_forget()
        self._tab_frames[key].pack(fill=tk.BOTH, expand=True)

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.config(fg=C_CYAN, bg=C_BG,
                           relief=tk.FLAT)
            else:
                btn.config(fg=C_MUTED, bg=C_SURF)

        if key == 'panel':      self.after(60, self._redraw_map)
        if key == 'inventario': self.after(60, self._draw_avl)

    # ── TAB PANEL ─────────────────────────────────────────────────────────────
    def _build_panel_tab(self):
        tab = self._tab_frames['panel']
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=0)

        # ── Fila KPI ──
        kpi_row = tk.Frame(tab, bg=C_BG)
        kpi_row.grid(row=0, column=0, columnspan=2, sticky='ew', padx=12, pady=(12, 6))
        for i in range(4): kpi_row.columnconfigure(i, weight=1)

        kpi_defs = [
            ('stat_pedidos',  'PEDIDOS EN COLA',   '0', 'solicitudes activas',  C_CYAN),
            ('stat_vuelo',    'DRONES EN VUELO',   '0', 'de 4 unidades',        C_GREEN),
            ('stat_batbaja',  'BATERÍA CRÍTICA',   '0', '< 30% carga',          C_YELLOW),
            ('stat_stock',    'STOCK CRÍTICO',      '0', '< 5 unidades',         C_RED),
        ]
        for col, (key, label, val, sub, color) in enumerate(kpi_defs):
            self._make_kpi_card(kpi_row, col, key, label, val, sub, color)

        # ── Mapa principal ──
        map_outer = tk.Frame(tab, bg=C_SURF, bd=0)
        map_outer.grid(row=1, column=0, sticky='nsew', padx=(12, 6), pady=(0, 6))
        map_outer.rowconfigure(1, weight=1)
        map_outer.columnconfigure(0, weight=1)

        # Header del mapa
        mhdr = tk.Frame(map_outer, bg=C_SURF, height=36)
        mhdr.grid(row=0, column=0, sticky='ew')
        mhdr.pack_propagate(False)

        tk.Label(mhdr, text='  ◈  MAPA TÁCTICO  ▸  BAHÍA SANTA MARTA  ▸  TIEMPO REAL',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT, pady=8)

        badge_f = tk.Frame(mhdr, bg=C_SURF)
        badge_f.pack(side=tk.RIGHT, padx=10)
        self._lbl_map_ts = tk.Label(badge_f, text='', bg=C_SURF, fg=C_MUTED, font=('Courier New', 7))
        self._lbl_map_ts.pack(side=tk.RIGHT, padx=8)
        tk.Label(badge_f, text='A* ACTIVO', bg=C_SURF, fg=C_GREEN, font=('Courier New', 7, 'bold')).pack(side=tk.RIGHT, padx=8)

        # Línea separadora cyan bajo el header
        tk.Frame(map_outer, bg=C_CYAN, height=1).grid(row=0, column=0, sticky='sew', pady=(35, 0))

        # Canvas del mapa
        self._map_canvas = tk.Canvas(map_outer, bg=C_BG, highlightthickness=0)
        self._map_canvas.grid(row=1, column=0, sticky='nsew')
        self._map_canvas.bind('<Configure>', lambda e: self._redraw_map())
        self._map_canvas.bind('<Button-1>', self._click_mapa)

        # ── Panel lateral derecho ──
        right = tk.Frame(tab, bg=C_BG)
        right.grid(row=1, column=1, sticky='nsew', padx=(0, 12), pady=(0, 6))
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # Fleet status
        fleet_card = tk.Frame(right, bg=C_SURF)
        fleet_card.grid(row=0, column=0, sticky='nsew', pady=(0, 6))
        fleet_card.columnconfigure(0, weight=1)
        self._make_card_header(fleet_card, '✦  ESTADO DE FLOTA')
        self._fleet_frame = tk.Frame(fleet_card, bg=C_SURF, padx=10, pady=8)
        self._fleet_frame.pack(fill=tk.BOTH, expand=True)
        self._build_fleet_widgets()

        # Activity log
        act_card = tk.Frame(right, bg=C_SURF)
        act_card.grid(row=1, column=0, sticky='nsew')
        act_card.columnconfigure(0, weight=1)
        self._make_card_header(act_card, '▶  ACTIVIDAD RECIENTE')
        self._act_frame = tk.Frame(act_card, bg=C_SURF, padx=10, pady=8)
        self._act_frame.pack(fill=tk.BOTH, expand=True)
        self._init_activity_log()

    def _make_kpi_card(self, parent, col, key, label, val, sub, color):
        card = tk.Frame(parent, bg=C_SURF)
        card.grid(row=0, column=col, sticky='ew', padx=(0 if col == 0 else 6, 0))

        # Barra superior de color
        tk.Frame(card, bg=color, height=2).pack(fill=tk.X)

        inner = tk.Frame(card, bg=C_SURF, padx=14, pady=10)
        inner.pack(fill=tk.BOTH)

        # Label pequeño
        tk.Label(inner, text=label, bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')

        # Número grande
        lbl_val = tk.Label(inner, text=val, bg=C_SURF, fg=color,
                           font=('Courier New', 26, 'bold'))
        lbl_val.pack(anchor='w')
        self._stat_lbls[key] = lbl_val

        # Sub-texto
        tk.Label(inner, text=sub, bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7)).pack(anchor='w')

        # Mini barra decorativa
        tk.Frame(inner, bg=color, height=1).pack(fill=tk.X, pady=(6, 0))

    def _make_card_header(self, parent, title):
        hdr = tk.Frame(parent, bg=C_SURF, height=30)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f'  {title}', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 8, 'bold')).pack(side=tk.LEFT, pady=6)
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X)

    def _build_fleet_widgets(self):
        for w in self._fleet_frame.winfo_children(): w.destroy()
        self._fleet_rows = {}

        for dron in self.sistema.drones.values():
            col = ESTADO_COLOR.get(dron.estado, C_MUTED)

            row_outer = tk.Frame(self._fleet_frame, bg=C_SURF2, pady=0)
            row_outer.pack(fill=tk.X, pady=3)

            # Borde izquierdo de estado
            tk.Frame(row_outer, bg=col, width=3).pack(side=tk.LEFT, fill=tk.Y)

            inner = tk.Frame(row_outer, bg=C_SURF2, padx=8, pady=6)
            inner.pack(fill=tk.X, expand=True)

            top_f = tk.Frame(inner, bg=C_SURF2)
            top_f.pack(fill=tk.X)

            tk.Label(top_f, text=dron.id_dron, bg=C_SURF2, fg=C_WHITE,
                     font=('Courier New', 10, 'bold')).pack(side=tk.LEFT)

            lbl_bat = tk.Label(top_f, text=f'{dron.bateria}%',
                               bg=C_SURF2, fg=bat_color(dron.bateria),
                               font=('Courier New', 9, 'bold'))
            lbl_bat.pack(side=tk.RIGHT)

            lbl_est = tk.Label(top_f, text=dron.estado.replace('_', ' ').upper(),
                               bg=C_SURF2, fg=col, font=('Courier New', 7))
            lbl_est.pack(side=tk.RIGHT, padx=6)

            # Barra de batería
            track = tk.Frame(inner, bg=C_BORDER2, height=4)
            track.pack(fill=tk.X, pady=(4, 0))
            fill_f = tk.Frame(track, bg=bat_color(dron.bateria), height=4)
            fill_f.place(x=0, y=0, relwidth=dron.bateria / 100)

            self._fleet_rows[dron.id_dron] = {
                'lbl_bat': lbl_bat, 'lbl_est': lbl_est,
                'fill_f': fill_f, 'col': col
            }

    def _init_activity_log(self):
        eventos = [
            (C_GREEN,  '◈ Sistema iniciado. Flota en espera.'),
            (C_BLUE,   '▶ Mapa cargado: 8 nodos, 10 rutas A*.'),
            (C_YELLOW, '⚠ D-03 batería crítica detectada.'),
            (C_RED,    '✖ D-04 en mantenimiento programado.'),
        ]
        self._activity_log = list(eventos)
        self._render_activity_log()

    def _render_activity_log(self):
        for w in self._act_frame.winfo_children(): w.destroy()
        for color, msg in self._activity_log[:7]:
            f = tk.Frame(self._act_frame, bg=C_SURF, pady=3)
            f.pack(fill=tk.X)
            dot = tk.Canvas(f, width=6, height=6, bg=C_SURF, highlightthickness=0)
            dot.pack(side=tk.LEFT, pady=4, padx=(0, 6))
            dot.create_oval(1, 1, 5, 5, fill=color, outline='')
            tk.Label(f, text=msg[:52], bg=C_SURF, fg=C_TEXT,
                     font=('Courier New', 8)).pack(side=tk.LEFT)
            tk.Frame(self._act_frame, bg=C_BORDER2, height=1).pack(fill=tk.X)

    def add_activity(self, msg, color=C_GREEN):
        self._activity_log.insert(0, (color, msg))
        self._activity_log = self._activity_log[:8]
        if hasattr(self, '_act_frame'):
            self._render_activity_log()

    # ── MAPA TÁCTICO ──────────────────────────────────────────────────────────
    def _sc(self, px, py, W, H):
        """Escala coordenadas virtuales al canvas real."""
        sx = W / 800.0
        sy = H / 460.0
        return int(px * sx), int(py * sy)

    def _redraw_map(self):
        c = self._map_canvas
        W, H = c.winfo_width(), c.winfo_height()
        if W < 10 or H < 10:
            self.after(100, self._redraw_map)
            return
        c.delete('all')
        self._draw_bg(c, W, H)
        self._draw_particles(c, W, H)
        self._draw_grid(c, W, H)
        self._draw_topology(c, W, H)
        self._draw_exclusion_zones(c, W, H)
        self._draw_edges(c, W, H)
        self._draw_nodes(c, W, H)
        self._draw_drones(c, W, H)
        self._draw_legend(c, W, H)
        self._draw_scanline(c, W, H)

    def _draw_bg(self, c, W, H):
        """Fondo oscuro con gradiente azul marino."""
        c.create_rectangle(0, 0, W, H, fill=C_BG, outline='')

        # Zona de bahía (agua) con gradiente simulado
        water_pts = []
        costa = [
            (800,0),(560,0),(590,50),(545,115),(590,160),
            (475,240),(370,210),(220,240),(180,350),(130,460),(800,460)
        ]
        for x, y in costa:
            water_pts.extend(self._sc(x, y, W, H))
        c.create_polygon(water_pts, fill='#040D1A', outline='')

        # Contorno de costa luminoso
        costa_line = []
        for x, y in costa:
            costa_line.extend(self._sc(x, y, W, H))
        c.create_line(costa_line, fill='#0E2E4A', width=2, smooth=True)
        c.create_line(costa_line, fill=C_CYAN_DIM, width=1, smooth=True, dash=(4, 6))

        # Sierra Nevada (montañas)
        sx, sy = self._sc(670, 395, W, H)
        for r, col in [(80,'#0A1F2F'),(58,'#0C2535'),(40,'#0F2D3C'),(24,'#133545'),(10,'#183D4E')]:
            rx, ry = int(r*(W/800)), int(r*0.7*(H/460))
            c.create_oval(sx-rx, sy-ry, sx+rx, sy+ry, fill=col, outline='#163040', width=1)
        c.create_text(sx, sy+3, text='▲ Sierra Nevada', fill='#2A6A58', font=('Courier New', 7, 'bold'))

        # Labels de agua
        bx, by = self._sc(380, 140, W, H)
        c.create_text(bx, by, text='BAHÍA DE SANTA MARTA', fill='#0E2844',
                      font=('Courier New', 8, 'bold', 'italic'))
        cx2, cy2 = self._sc(180, 70, W, H)
        c.create_text(cx2, cy2, text='M A R   C A R I B E', fill='#0C2238',
                      font=('Courier New', 11, 'bold'))

    def _draw_particles(self, c, W, H):
        """Partículas flotantes ambientales."""
        for p in self._particles:
            p['x'] = (p['x'] + p['vx']) % 800
            p['y'] = (p['y'] + p['vy']) % 460
            px, py = self._sc(p['x'], p['y'], W, H)
            r = max(1, int(p['r'] * min(W/800, H/460)))
            c.create_oval(px-r, py-r, px+r, py+r, fill=C_CYAN_DIM, outline='')

    def _draw_grid(self, c, W, H):
        """Grid táctico con cruces de coordenadas."""
        step_x = W // 8
        step_y = H // 6
        for x in range(0, W, step_x):
            c.create_line(x, 0, x, H, fill='#0A1E30', width=1)
        for y in range(0, H, step_y):
            c.create_line(0, y, W, y, fill='#0A1E30', width=1)

        # Cruces en intersecciones
        for gx in range(step_x, W, step_x):
            for gy in range(step_y, H, step_y):
                s = 3
                c.create_line(gx-s, gy, gx+s, gy, fill='#162B40', width=1)
                c.create_line(gx, gy-s, gx, gy+s, fill='#162B40', width=1)

    def _draw_topology(self, c, W, H):
        """Polígonos de zonas operativas translúcidas."""
        tick = self._anim_tick

        # Zona operativa norte (Taganga/Recarga)
        zona_norte = [(NODO_POS['TAGANGA']), (NODO_POS['RECARGA_N']), (610, 220), (490, 320), (400, 230)]
        pts = []
        for (x,y) in zona_norte:
            pts.extend(self._sc(x, y, W, H))
        c.create_polygon(pts, fill='#001A0F', outline='#003820', width=1, smooth=True)

        # Zona sur (Rodadero/Minca)
        zona_sur = [(NODO_POS['RODADERO']), (NODO_POS['MINCA']), (390, 430), (NODO_POS['RECARGA_S'])]
        pts2 = []
        for (x,y) in zona_sur:
            pts2.extend(self._sc(x, y, W, H))
        c.create_polygon(pts2, fill='#0A1200', outline='#1A2800', width=1, smooth=True)

        # Brillo pulsante en zona centro
        pulse = 0.3 + 0.1 * math.sin(tick * 0.8)
        cx_node, cy_node = self._sc(490, 280, W, H)
        for radius_mult, alpha_tag in [(3.0, '#021810'), (2.0, '#031F14'), (1.0, '#042A1A')]:
            rx = int(80 * radius_mult * W / 800)
            ry = int(60 * radius_mult * H / 460)
            c.create_oval(cx_node-rx, cy_node-ry, cx_node+rx, cy_node+ry,
                          fill=alpha_tag, outline='')

    def _draw_exclusion_zones(self, c, W, H):
        """Zonas de exclusión con efecto peligro pulsante."""
        tick = self._anim_tick

        # ZIRUMA
        zx, zy = self._sc(*NODO_POS['ZIRUMA'], W, H)
        base_r = int(44 * min(W/800, H/460))
        pulse_r = base_r + int(4 * math.sin(tick * 1.5))

        # Relleno rojo translúcido
        c.create_oval(zx-pulse_r, zy-pulse_r, zx+pulse_r, zy+pulse_r,
                      fill='#1A0308', outline=C_RED, width=1, dash=(3, 3))
        # Anillo exterior pulsante
        outer = pulse_r + 8
        c.create_oval(zx-outer, zy-outer, zx+outer, zy+outer,
                      fill='', outline='#6B0011', width=1, dash=(2, 6))

        # Ícono prohibición
        ri = 9
        c.create_oval(zx-ri, zy-ri, zx+ri, zy+ri, fill='#200509', outline=C_RED, width=2)
        c.create_line(zx-ri+3, zy+ri-3, zx+ri-3, zy-ri+3, fill=C_RED, width=2)

        c.create_rectangle(zx-28, zy+base_r+4, zx+28, zy+base_r+16,
                           fill=C_BG, outline='')
        c.create_text(zx, zy+base_r+10, text='⊘ ZIRUMA  ZONA EXCLUIDA',
                      fill=C_RED, font=('Courier New', 7, 'bold'))

        # AEROPUERTO
        ax, ay = self._sc(*NODO_POS['AEROPUERTO'], W, H)
        ar = int(22 * min(W/800, H/460))
        c.create_oval(ax-ar, ay-ar, ax+ar, ay+ar,
                      fill='#12090A', outline='#6B1020', width=1, dash=(2, 4))
        c.create_text(ax, ay, text='✈', fill='#6B1020', font=('Courier New', 9))
        c.create_text(ax, ay+ar+8, text='AEROP.', fill='#4A0815', font=('Courier New', 6))

    def _draw_edges(self, c, W, H):
        """Rutas de drones con curvas suaves y efecto neón."""
        tick = self._anim_tick

        for n1, n2 in ARISTAS:
            if n1 not in NODO_POS or n2 not in NODO_POS: continue
            x1, y1 = self._sc(*NODO_POS[n1], W, H)
            x2, y2 = self._sc(*NODO_POS[n2], W, H)

            # Calcular punto de control para curva suave
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            dx = x2 - x1
            dy = y2 - y1
            perp_x = -dy * 0.15
            perp_y = dx * 0.15
            cx_ctrl = mx + perp_x
            cy_ctrl = my + perp_y

            # Curva bezier simulada con puntos intermedios
            bezier_pts = []
            steps = 12
            for i in range(steps + 1):
                t = i / steps
                bx = (1-t)**2 * x1 + 2*(1-t)*t*cx_ctrl + t**2 * x2
                by = (1-t)**2 * y1 + 2*(1-t)*t*cy_ctrl + t**2 * y2
                bezier_pts.extend([bx, by])

            # Ruta base (oscura)
            if len(bezier_pts) >= 4:
                c.create_line(bezier_pts, fill='#0B2040', width=3, smooth=False)
                # Ruta neón sutil
                c.create_line(bezier_pts, fill=C_CYAN_DIM, width=1, smooth=False, dash=(5, 4))

            # Flecha de dirección animada
            anim_pos = (tick * 0.3) % 1.0
            t = anim_pos
            bx = (1-t)**2 * x1 + 2*(1-t)*t*cx_ctrl + t**2 * x2
            by = (1-t)**2 * y1 + 2*(1-t)*t*cy_ctrl + t**2 * y2
            t2 = min(1.0, t + 0.05)
            bx2 = (1-t2)**2 * x1 + 2*(1-t2)*t2*cx_ctrl + t2**2 * x2
            by2 = (1-t2)**2 * y1 + 2*(1-t2)*t2*cy_ctrl + t2**2 * y2
            ang = math.atan2(by2-by, bx2-bx)
            fs = 5
            c.create_polygon(
                bx + fs*math.cos(ang), by + fs*math.sin(ang),
                bx + fs*math.cos(ang+2.4), by + fs*math.sin(ang+2.4),
                bx + fs*math.cos(ang-2.4), by + fs*math.sin(ang-2.4),
                fill=C_CYAN_DIM, outline=''
            )

            # Etiqueta de distancia flotante
            dist_str = f'{math.hypot(NODO_POS[n2][0]-NODO_POS[n1][0], NODO_POS[n2][1]-NODO_POS[n1][1])*0.0085:.1f}km'
            lmx, lmy = int(cx_ctrl), int(cy_ctrl)
            c.create_rectangle(lmx-14, lmy-7, lmx+14, lmy+7, fill='#050F1A', outline=C_BORDER)
            c.create_text(lmx, lmy, text=dist_str, fill=C_MUTED, font=('Courier New', 6))

    def _draw_nodes(self, c, W, H):
        """Nodos del mapa con iconos tácticos y anillos de sonar."""
        tick = self._anim_tick

        for nid, nodo in self.sistema.mapa.nodos.items():
            if nid in ('ZIRUMA', 'AEROPUERTO') or nid not in NODO_POS: continue
            x, y = self._sc(*NODO_POS[nid], W, H)
            color = NODO_TIPO_COLOR.get(nodo.tipo, C_MUTED)

            # Radio según tipo
            r = 16 if nodo.tipo == 'almacen' else 13 if nodo.tipo == 'recarga' else 11

            # Anillo exterior pulsante (sonar)
            pulse_r = r + 6 + int(3 * math.sin(tick * 1.2 + hash(nid) % 6))
            c.create_oval(x-pulse_r, y-pulse_r, x+pulse_r, y+pulse_r,
                          fill='', outline=color, width=1,
                          dash=(2, 4) if nodo.tipo != 'almacen' else ())

            # Cuerpo del nodo
            c.create_oval(x-r, y-r, x+r, y+r, fill=C_BG, outline=color, width=2)

            # Ícono interior
            if nodo.tipo == 'almacen':
                c.create_text(x, y, text='◈', fill=color, font=('Courier New', 12, 'bold'))
            elif nodo.tipo == 'recarga':
                c.create_text(x, y, text='⚡', fill=color, font=('Courier New', 8))
            else:
                c.create_oval(x-4, y-4, x+4, y+4, fill=color, outline='')

            # Etiqueta del nodo
            nombre = nodo.nombre.upper()
            label_x = x + r + 6
            c.create_rectangle(label_x, y-8, label_x + len(nombre)*5.5 + 8, y+8,
                               fill='#050F1A', outline=C_BORDER2)
            c.create_text(label_x+4, y, text=nombre, fill=color,
                          font=('Courier New', 7, 'bold'), anchor='w')

    def _draw_drones(self, c, W, H):
        """Drones con diseño táctico avanzado quadcopter + HUD."""
        tick = self._anim_tick
        yi = 12

        for dron in self.sistema.drones.values():
            if dron.estado not in ('en_vuelo', 'bateria_baja'): continue
            if dron.id_dron not in self._drone_states: continue
            s = self._drone_states[dron.id_dron]

            px, py = self._sc(s['x'], s['y'], W, H)
            is_low = dron.bateria < 30
            main_col = C_RED if is_low else C_CYAN

            # Calcular ángulo de movimiento
            dx = s['tx'] - s['x']
            dy = s['ty'] - s['y']
            ang = math.atan2(dy, dx) if abs(dx)+abs(dy) > 5 else 0

            # ── ESTELA ──
            if len(s['trail']) > 2:
                trail_pts = []
                for pt in s['trail'][-18:]:
                    trail_pts.extend(self._sc(pt[0], pt[1], W, H))
                if len(trail_pts) >= 4:
                    c.create_line(trail_pts, fill='#020E1A', width=5, smooth=True)
                    c.create_line(trail_pts, fill=C_CYAN_DIM if not is_low else C_RED_DIM,
                                  width=2, smooth=True)
                    c.create_line(trail_pts, fill=main_col, width=1,
                                  smooth=True, dash=(3, 3))

            # ── PULSO DE RADAR ──
            pulse_r = 14 + int(6 * math.sin(tick * 3 + s['pulse']))
            c.create_oval(px-pulse_r, py-pulse_r, px+pulse_r, py+pulse_r,
                          fill='', outline=main_col, width=1, dash=(2, 3))

            # ── QUADCOPTER TÁCTICO ──
            sz = 11
            # Brazos
            for off_ang in [math.pi/4, 3*math.pi/4, -math.pi/4, -3*math.pi/4]:
                arm_ang = ang + off_ang
                ax = px + sz * math.cos(arm_ang)
                ay = py + sz * math.sin(arm_ang)
                c.create_line(px, py, ax, ay, fill='#2A4A6A', width=2)
                # Rotores
                r_rot = 4 + 1.5 * math.sin(tick * 10 + off_ang)
                c.create_oval(ax-r_rot, ay-r_rot, ax+r_rot, ay+r_rot,
                              fill='#080F1A', outline=main_col, width=1.5)

            # Cuerpo central hexagonal
            hex_pts = []
            for i in range(6):
                ha = math.pi/6 + i * math.pi/3
                hex_pts += [px + 5*math.cos(ha), py + 5*math.sin(ha)]
            c.create_polygon(hex_pts, fill=C_BG, outline=main_col, width=2)
            c.create_oval(px-2, py-2, px+2, py+2, fill=main_col, outline='')

            # Luz frontal
            fl_x = px + 8 * math.cos(ang)
            fl_y = py + 8 * math.sin(ang)
            c.create_oval(fl_x-1.5, fl_y-1.5, fl_x+1.5, fl_y+1.5, fill=C_WHITE, outline='')

            # ── HUD DEL DRON ──
            prog = int(s['prog'] * 100)
            hud_x = px + 18
            hud_y = py - 28

            # Línea conectora
            c.create_line(px, py, px+12, py-18, fill=main_col, width=1)
            c.create_line(px+12, py-18, hud_x+72, py-18, fill=main_col, width=1)

            # Caja HUD
            c.create_rectangle(hud_x, hud_y-10, hud_x+72, hud_y+10,
                               fill='#030A14', outline=main_col, width=1)

            c.create_text(hud_x+4, hud_y-4, text=f'{dron.id_dron}',
                          fill=C_WHITE, font=('Courier New', 7, 'bold'), anchor='w')
            c.create_text(hud_x+4, hud_y+4, text=f'▶{prog}%  B:{dron.bateria}%',
                          fill=main_col, font=('Courier New', 7), anchor='w')

            # ── BARRA MISIÓN (lateral izquierda) ──
            bw = 120
            bh = 20
            c.create_rectangle(10, yi, 10+bw+55, yi+bh,
                               fill='#040C18', outline=C_BORDER, width=1)
            c.create_text(16, yi+10, text=dron.id_dron, fill=main_col,
                          font=('Courier New', 8, 'bold'), anchor='w')
            # Riel
            c.create_rectangle(52, yi+7, 52+bw, yi+13, fill=C_BORDER2, outline='')
            fw = int(bw * s['prog'])
            if fw > 0:
                c.create_rectangle(52, yi+7, 52+fw, yi+13, fill=main_col, outline='')
            c.create_text(56+bw, yi+10, text=f'{prog}%', fill=C_MUTED,
                          font=('Courier New', 7), anchor='w')
            yi += 26

    def _draw_scanline(self, c, W, H):
        """Efecto scanline sutil moviéndose."""
        self._scan_offset = (self._scan_offset + 2) % H
        c.create_rectangle(0, self._scan_offset, W, self._scan_offset+2,
                           fill='#0D2233', outline='', stipple='gray12')

    def _draw_legend(self, c, W, H):
        """Leyenda táctica en esquina inferior derecha."""
        items = [
            ('◈ ALMACÉN', C_BLUE),
            ('● DESTINO',  C_GREEN),
            ('⚡ RECARGA', C_YELLOW),
            ('⊘ EXCLUIDO', C_RED),
        ]
        lx = W - 160
        ly = H - 14

        c.create_rectangle(lx-6, ly-12, W-4, ly+12, fill='#040C18', outline=C_BORDER)
        for i, (txt, col) in enumerate(items):
            c.create_text(lx + i*38, ly, text=txt[:4], fill=col,
                          font=('Courier New', 6, 'bold'), anchor='w')

        # Brújula
        cx_comp, cy_comp = 45, 45
        c.create_oval(cx_comp-22, cy_comp-22, cx_comp+22, cy_comp+22,
                      fill='#040C18', outline=C_BORDER, width=1)
        # N
        c.create_polygon(cx_comp, cy_comp-20, cx_comp+4, cy_comp,
                         cx_comp-4, cy_comp, fill=C_BLUE, outline='')
        # S
        c.create_polygon(cx_comp, cy_comp+20, cx_comp+4, cy_comp,
                         cx_comp-4, cy_comp, fill=C_MUTED, outline='')
        c.create_text(cx_comp, cy_comp-26, text='N', fill=C_BLUE, font=('Courier New', 7, 'bold'))

    def _click_mapa(self, event):
        W = self._map_canvas.winfo_width()
        H = self._map_canvas.winfo_height()
        for nid, (nx, ny) in NODO_POS.items():
            cx, cy = self._sc(nx, ny, W, H)
            if abs(event.x-cx) < 20 and abs(event.y-cy) < 20:
                nodo = self.sistema.mapa.nodos.get(nid)
                if nodo and nodo.tipo != 'excluido':
                    self._mostrar_info_nodo(nid)
                return

    def _mostrar_info_nodo(self, nid):
        info = self.sistema.info_nodo(nid)
        if not info: return
        nombre = info['nombre']
        tipo   = info['tipo'].upper()
        coords = f"{info['lat']:.4f}°N  {abs(info['lon']):.4f}°W"
        msg = f"◈ {nombre}\nTIPO: {tipo}\nCOORDS: {coords}\nCONEXIONES: {info['conexiones']}\nDRONES: {', '.join(info['drones']) or 'Ninguno'}"

        if nid != 'ALMACEN':
            if messagebox.askyesno('NODO SELECCIONADO', msg + '\n\n¿Calcular ruta A* desde Almacén?', parent=self):
                self._calc_ruta(nid)
        else:
            messagebox.showinfo('ALMACÉN CENTRAL', msg, parent=self)

    def _calc_ruta(self, destino):
        ruta, dist = self.sistema.calcular_ruta('ALMACEN', destino)
        if ruta:
            nombres = [self.sistema.mapa.nodos[n].nombre for n in ruta if n in self.sistema.mapa.nodos]
            msg = f"◈ RUTA CALCULADA\n\n{' → '.join(nombres)}\n\nDISTANCIA: {dist:.2f} km\nNODOS: {len(ruta)}\n\n✓ Evita Ziruma y Aeropuerto"
            messagebox.showinfo('A* PATHFINDING', msg, parent=self)
            self.add_activity(f'▶ Ruta A*: {destino} ({dist:.1f}km)', C_BLUE)
        else:
            messagebox.showwarning('SIN RUTA', 'No se encontró ruta disponible.', parent=self)

    # ── TAB PEDIDOS ───────────────────────────────────────────────────────────
    def _build_pedidos_tab(self):
        tab = self._tab_frames['pedidos']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        toolbar = tk.Frame(tab, bg=C_BG, pady=10)
        toolbar.grid(row=0, column=0, sticky='ew', padx=14)

        self._search_ped = tk.Entry(
            toolbar, bg=C_SURF, fg=C_TEXT, insertbackground=C_CYAN,
            relief=tk.FLAT, font=('Courier New', 10), width=38,
            highlightthickness=1, highlightbackground=C_BORDER
        )
        self._search_ped.insert(0, '  ⌕  Buscar pedido, destino...')
        self._search_ped.bind('<FocusIn>', lambda e: self._clear_search(self._search_ped, '  ⌕  Buscar pedido, destino...'))
        self._search_ped.bind('<KeyRelease>', lambda e: self._refresh_pedidos_table())
        self._search_ped.pack(side=tk.LEFT, ipady=7, padx=(0, 8))

        from gui.ventana_pedido import VentanaPedido
        self._make_btn(toolbar, '+ NUEVO PEDIDO', C_CYAN, C_BG,
                       lambda: VentanaPedido(self, self.sistema, self.actualizar)).pack(side=tk.LEFT, padx=(0, 6))
        self._make_btn(toolbar, '⚡ DESPACHAR', C_GREEN, C_BG,
                       self._despachar).pack(side=tk.LEFT)

        wrap = tk.Frame(tab, bg=C_SURF, bd=0)
        wrap.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 14))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Ped.Treeview',
                        background=C_SURF2, foreground=C_TEXT, fieldbackground=C_SURF2,
                        font=('Courier New', 10), rowheight=32, borderwidth=0)
        style.configure('Ped.Treeview.Heading',
                        background=C_SURF, foreground=C_CYAN,
                        font=('Courier New', 8, 'bold'), relief='flat')
        style.map('Ped.Treeview', background=[('selected', '#0D2A40')])

        cols = ('ID', 'Destino', 'Tipo', 'Prioridad', 'Peso', 'Hora', 'Estado')
        self._tree_ped = ttk.Treeview(wrap, columns=cols, show='headings', style='Ped.Treeview')
        anchos = [65, 180, 120, 90, 65, 65, 90]
        for col, aw in zip(cols, anchos):
            self._tree_ped.heading(col, text=col.upper())
            self._tree_ped.column(col, width=aw, anchor='center')
        self._tree_ped.grid(row=0, column=0, sticky='nsew')

        sb = ttk.Scrollbar(wrap, orient='vertical', command=self._tree_ped.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self._tree_ped.configure(yscrollcommand=sb.set)
        self._refresh_pedidos_table()

    def _clear_search(self, entry, placeholder):
        if entry.get().strip() == placeholder.strip():
            entry.delete(0, tk.END)

    def _refresh_pedidos_table(self):
        for row in self._tree_ped.get_children(): self._tree_ped.delete(row)
        q = self._search_ped.get().lower().strip()
        if '⌕' in q or 'buscar' in q: q = ''
        for p in self.sistema.cola_pedidos.a_lista():
            if q and q not in p.destino_nombre.lower() and q not in p.id_pedido.lower():
                continue
            self._tree_ped.insert('', 'end', iid=p.id_pedido,
                                   values=(p.id_pedido, p.destino_nombre, p.tipo,
                                           p.prioridad, f'{p.peso_kg:.1f}',
                                           p.hora_ingreso or '--', p.estado.upper()))

    # ── TAB DRONES ────────────────────────────────────────────────────────────
    def _build_drones_tab(self):
        tab = self._tab_frames['drones']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        toolbar = tk.Frame(tab, bg=C_BG, pady=10)
        toolbar.grid(row=0, column=0, sticky='ew', padx=14)

        from gui.ventana_dron import VentanaDron
        self._make_btn(toolbar, '+ GESTIONAR DRONES', C_GREEN, C_BG,
                       lambda: VentanaDron(self, self.sistema, self.actualizar)).pack(side=tk.LEFT)

        scroll_f = tk.Frame(tab, bg=C_BG)
        scroll_f.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 14))
        self._drones_grid_frame = scroll_f
        self._refresh_drones_grid()

    def _refresh_drones_grid(self):
        for w in self._drones_grid_frame.winfo_children(): w.destroy()
        from gui.ventana_dron import VentanaDron
        drones = list(self.sistema.drones.values())
        cols = 2
        for i, dron in enumerate(drones):
            r, ci = divmod(i, cols)
            self._drones_grid_frame.columnconfigure(ci, weight=1)
            col = ESTADO_COLOR.get(dron.estado, C_MUTED)

            card = tk.Frame(self._drones_grid_frame, bg=C_SURF, bd=0)
            card.grid(row=r, column=ci, sticky='nsew',
                      padx=(0 if ci == 0 else 8, 0),
                      pady=(0 if r == 0 else 8, 0))

            # Barra superior de color
            tk.Frame(card, bg=col, height=2).pack(fill=tk.X)

            hdr = tk.Frame(card, bg=C_SURF, padx=14, pady=10)
            hdr.pack(fill=tk.X)

            # ID y botón
            id_frame = tk.Frame(hdr, bg=C_SURF)
            id_frame.pack(fill=tk.X)
            tk.Label(id_frame, text=dron.id_dron, bg=C_SURF, fg=C_WHITE,
                     font=('Courier New', 18, 'bold')).pack(side=tk.LEFT)
            self._make_btn(id_frame, '✎ GESTIONAR', C_SURF, C_CYAN,
                           lambda: VentanaDron(self, self.sistema, self.actualizar),
                           border_color=C_BORDER).pack(side=tk.RIGHT)

            # Modelo
            tk.Label(hdr, text=dron.modelo.upper(), bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 8)).pack(anchor='w', pady=(2, 0))

            # Estado con punto de color
            est_f = tk.Frame(hdr, bg=C_SURF)
            est_f.pack(anchor='w', pady=(4, 0))
            dot = tk.Canvas(est_f, width=7, height=7, bg=C_SURF, highlightthickness=0)
            dot.pack(side=tk.LEFT, pady=3)
            dot.create_oval(1, 1, 6, 6, fill=col, outline='')
            tk.Label(est_f, text=dron.estado.replace('_', ' ').upper(),
                     bg=C_SURF, fg=col, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT, padx=4)

            # Separador
            tk.Frame(card, bg=C_BORDER2, height=1).pack(fill=tk.X, padx=14)

            # Batería
            bat_frame = tk.Frame(card, bg=C_SURF, padx=14, pady=8)
            bat_frame.pack(fill=tk.X)
            bat_row = tk.Frame(bat_frame, bg=C_SURF)
            bat_row.pack(fill=tk.X)
            tk.Label(bat_row, text='BATERÍA', bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(side=tk.LEFT)
            bc = bat_color(dron.bateria)
            tk.Label(bat_row, text=f'{dron.bateria}%', bg=C_SURF, fg=bc,
                     font=('Courier New', 9, 'bold')).pack(side=tk.RIGHT)
            track = tk.Frame(bat_frame, bg=C_BORDER2, height=6)
            track.pack(fill=tk.X, pady=(4, 0))
            tk.Frame(track, bg=bc, height=6).place(x=0, y=0, relwidth=dron.bateria/100)

            # Último mantenimiento
            tk.Label(card, text=f'  ◈  {dron.ultimo_mantenimiento()[:45]}',
                     bg=C_SURF, fg=C_MUTED, font=('Courier New', 8),
                     anchor='w').pack(fill=tk.X, padx=14, pady=(0, 10))

    # ── TAB INVENTARIO ────────────────────────────────────────────────────────
    def _build_inventario_tab(self):
        tab = self._tab_frames['inventario']
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=0)

        toolbar = tk.Frame(tab, bg=C_BG, pady=10)
        toolbar.grid(row=0, column=0, sticky='ew', padx=14)

        from gui.ventana_inventario import VentanaInventario
        self._make_btn(toolbar, '+ GESTIONAR INVENTARIO', C_GREEN, C_BG,
                       lambda: VentanaInventario(self, self.sistema)).pack(side=tk.LEFT)

        grid_f = tk.Frame(tab, bg=C_BG)
        grid_f.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 6))
        self._inv_grid_frame = grid_f
        self._refresh_inventario_grid()

        # AVL mini canvas
        avl_card = tk.Frame(tab, bg=C_SURF)
        avl_card.grid(row=2, column=0, sticky='ew', padx=14, pady=(0, 14))
        self._make_card_header(avl_card, '⊞  ÁRBOL AVL — INVENTARIO (AUTOBALANCEADO)')
        self._avl_canvas = tk.Canvas(avl_card, bg=C_SURF2, height=190, highlightthickness=0)
        self._avl_canvas.pack(fill=tk.X, padx=10, pady=(6, 10))
        self.after(120, self._draw_avl)

    def _refresh_inventario_grid(self):
        for w in self._inv_grid_frame.winfo_children(): w.destroy()
        productos = self.sistema.lista_productos()
        cols = 3
        for i, p in enumerate(productos):
            r, ci = divmod(i, cols)
            self._inv_grid_frame.columnconfigure(ci, weight=1)
            sc = C_RED if p.stock < 5 else C_YELLOW if p.stock < 10 else C_GREEN

            card = tk.Frame(self._inv_grid_frame, bg=C_SURF, padx=12, pady=8)
            card.grid(row=r, column=ci, sticky='nsew',
                      padx=(0 if ci == 0 else 6, 0),
                      pady=(0 if r == 0 else 6, 0))

            tk.Frame(card, bg=sc, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
            info = tk.Frame(card, bg=C_SURF)
            info.pack(fill=tk.X, expand=True)

            tk.Label(info, text=p.nombre, bg=C_SURF, fg=C_WHITE,
                     font=('Courier New', 10, 'bold')).pack(anchor='w')
            tk.Label(info, text=p.categoria.upper(), bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w', pady=(1, 4))

            for lbl, val, col in [
                ('STOCK', f'{p.stock} uds{"  ⚠" if p.stock < 5 else ""}', sc),
                ('PESO',  f'{p.peso_kg} kg', C_TEXT),
                ('ID',    f'#{p.id_producto}', C_MUTED),
            ]:
                rf = tk.Frame(info, bg=C_SURF)
                rf.pack(fill=tk.X)
                tk.Label(rf, text=lbl, bg=C_SURF, fg=C_MUTED, font=('Courier New', 7)).pack(side=tk.LEFT)
                tk.Label(rf, text=val, bg=C_SURF, fg=col, font=('Courier New', 8, 'bold')).pack(side=tk.RIGHT)

    def _draw_avl(self):
        c = self._avl_canvas
        c.delete('all')
        W = c.winfo_width()
        H = c.winfo_height() or 190
        if W < 10: return

        nodos = self.sistema.inventario.obtener_nodos_visualizacion()
        if not nodos:
            c.create_text(W//2, H//2, text='ÁRBOL VACÍO', fill=C_MUTED, font=('Courier New', 10))
            return

        c.create_rectangle(0, 0, W, H, fill=C_SURF2, outline='')

        max_nivel = max(n['nivel'] for n in nodos)
        nivel_h = H / (max_nivel + 2)
        posiciones = {}
        by_level = {}
        for n in nodos:
            by_level.setdefault(n['nivel'], []).append(n)

        for nivel, lista in by_level.items():
            count = len(lista)
            for j, n in enumerate(lista):
                x = W * (j+1) / (count+1)
                y = nivel_h * (nivel+1)
                posiciones[n['id']] = (x, y)

        # Aristas
        for n in nodos:
            if n['padre'] is not None and n['padre'] in posiciones and n['id'] in posiciones:
                x1, y1 = posiciones[n['padre']]
                x2, y2 = posiciones[n['id']]
                c.create_line(x1, y1, x2, y2, fill=C_BORDER, width=1.5)
                c.create_line(x1, y1, x2, y2, fill=C_CYAN_DIM, width=0.5, dash=(3, 4))

        # Nodos
        r = 18
        for n in nodos:
            if n['id'] not in posiciones: continue
            x, y = posiciones[n['id']]
            is_root = n['padre'] is None
            col = C_CYAN if is_root else C_TEXT

            # Anillo exterior sutil
            c.create_oval(x-r-3, y-r-3, x+r+3, y+r+3, fill='', outline=col, width=0.5, dash=(2, 4))
            c.create_oval(x-r, y-r, x+r, y+r, fill=C_SURF, outline=col, width=2)
            c.create_text(x, y, text=str(n['id']), fill=col, font=('Courier New', 9, 'bold'))
            c.create_text(x+r+2, y-r+2, text=f'FE:{n["fe"]}', fill=C_MUTED,
                          font=('Courier New', 6), anchor='w')

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _make_btn(self, parent, text, bg, fg, cmd, border_color=None):
        kwargs = dict(text=text, bg=bg, fg=fg, relief=tk.FLAT, cursor='hand2',
                      font=('Courier New', 8, 'bold'), padx=10, pady=4,
                      activebackground=bg, activeforeground=fg, command=cmd)
        if border_color:
            kwargs.update(highlightthickness=1, highlightbackground=border_color)
        return tk.Button(parent, **kwargs)

    # ── ACCIONES ──────────────────────────────────────────────────────────────
    def _despachar(self):
        dron, msg = self.sistema.despachar_siguiente()
        if dron:
            dest_id = dron.pedido_actual.destino_id if dron.pedido_actual else None
            if dest_id and dest_id in NODO_POS:
                tx, ty = NODO_POS[dest_id]
                self._drone_states[dron.id_dron] = {
                    'x': 400.0, 'y': 230.0,
                    'tx': float(tx), 'ty': float(ty),
                    'prog': 0.0, 'trail': [],
                    'returning': False, 'wait': 0,
                    'pulse': random.uniform(0, math.pi*2),
                }
            dest_nom = dron.pedido_actual.destino_nombre if dron.pedido_actual else '?'
            self.add_activity(f'⚡ {dron.id_dron} despachado → {dest_nom}', C_GREEN)
            messagebox.showinfo('DESPACHO EXITOSO', msg, parent=self)
        else:
            messagebox.showwarning('NO SE PUDO DESPACHAR', msg, parent=self)
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
        self._anim_tick += 0.15

        now = datetime.datetime.now()
        self._lbl_clock.config(text=now.strftime('%H:%M:%S'))
        if hasattr(self, '_lbl_map_ts'):
            self._lbl_map_ts.config(text=now.strftime('%H:%M:%S'))

        # Pulso del LED
        if self._tick_count % 4 == 0:
            col = C_GREEN if self._tick_count % 8 < 4 else C_GREEN_DIM
            self._pulse_dot.delete('all')
            self._pulse_dot.create_oval(1, 1, 7, 7, fill=col, outline='')

        self._step_drones()
        self._update_stats()
        self._update_fleet_panel()

        if self._tab_actual == 'panel':
            self._redraw_map()

        self.after(500, self._tick)

    def _step_drones(self):
        SPEED = 0.022
        BASE_X, BASE_Y = 400.0, 230.0

        for dron in self.sistema.drones.values():
            if dron.estado not in ('en_vuelo', 'bateria_baja'):
                self._drone_states.pop(dron.id_dron, None)
                continue

            if dron.id_dron not in self._drone_states:
                dest = NODO_POS.get(
                    dron.pedido_actual.destino_id if dron.pedido_actual else 'CENTRO',
                    (500, 280)
                )
                self._drone_states[dron.id_dron] = {
                    'x': BASE_X, 'y': BASE_Y,
                    'tx': float(dest[0]), 'ty': float(dest[1]),
                    'prog': 0.0, 'trail': [],
                    'returning': False, 'wait': 0,
                    'pulse': random.uniform(0, math.pi*2),
                }

            s = self._drone_states[dron.id_dron]
            if s.get('wait', 0) > 0:
                s['wait'] -= 1
                continue

            s['trail'].append((s['x'], s['y']))
            if len(s['trail']) > 22: s['trail'].pop(0)

            if not s['returning']:
                s['prog'] = min(1.0, s['prog'] + SPEED)
                s['x'] += (s['tx'] - s['x']) * SPEED * 3.5
                s['y'] += (s['ty'] - s['y']) * SPEED * 3.5
                if s['prog'] >= 1.0:
                    s['returning'] = True
                    s['wait'] = 5
                    s['prog'] = 0.0
            else:
                s['prog'] = min(1.0, s['prog'] + SPEED)
                s['x'] += (BASE_X - s['x']) * SPEED * 3.5
                s['y'] += (BASE_Y - s['y']) * SPEED * 3.5
                if s['prog'] >= 1.0:
                    s['returning'] = False
                    s['prog'] = 0.0

    def _update_stats(self):
        if not hasattr(self, '_stat_lbls'): return
        n_ped = len(self.sistema.cola_pedidos)
        n_vue = sum(1 for d in self.sistema.drones.values() if d.estado == 'en_vuelo')
        n_bat = sum(1 for d in self.sistema.drones.values() if d.bateria < 30)
        n_sto = sum(1 for p in self.sistema.lista_productos() if p.stock < 5)

        self._stat_lbls['stat_pedidos'].config(text=str(n_ped))
        self._stat_lbls['stat_vuelo'].config(text=str(n_vue))
        self._stat_lbls['stat_batbaja'].config(text=str(n_bat))
        self._stat_lbls['stat_stock'].config(text=str(n_sto))

    def _update_fleet_panel(self):
        if not hasattr(self, '_fleet_rows'): return
        for dron in self.sistema.drones.values():
            w = self._fleet_rows.get(dron.id_dron)
            if not w: continue
            bc = bat_color(dron.bateria)
            col = ESTADO_COLOR.get(dron.estado, C_MUTED)
            w['lbl_bat'].config(text=f'{dron.bateria}%', fg=bc)
            w['lbl_est'].config(text=dron.estado.replace('_', ' ').upper(), fg=col)
            w['fill_f'].place(relwidth=dron.bateria / 100)
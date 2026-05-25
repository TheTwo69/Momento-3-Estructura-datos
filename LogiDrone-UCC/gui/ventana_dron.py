# ventana_dron.py — LogiDrone-UCC v4 TACTICAL
# Gestión de flota de drones con HUD táctico y pila LIFO

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

C_BG     = '#07111F'
C_SURF   = '#0B1929'
C_SURF2  = '#0F2035'
C_BORDER = '#1A3A5C'
C_CYAN   = '#00E5FF'
C_BLUE   = '#3B82F6'
C_GREEN  = '#00FF9C'
C_YELLOW = '#FFC857'
C_RED    = '#FF4D6D'
C_TEXT   = '#C8D8E8'
C_MUTED  = '#4A6A8A'
C_WHITE  = '#E8F4FF'

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


class VentanaDron(tk.Toplevel):
    def __init__(self, parent, sistema, callback_actualizar):
        super().__init__(parent)
        self.sistema = sistema
        self.callback = callback_actualizar
        self.title('LogiDrone-UCC  ◈  GESTIÓN DE DRONES')
        self.geometry('1060x680')
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.dron_seleccionado = None
        self._construir_ui()

    def _construir_ui(self):
        # Header
        header = tk.Frame(self, bg=C_SURF, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  ✦  GESTIÓN DE DRONES  ◈  HISTORIAL PILA LIFO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=C_BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # ── Cards de drones ──
        self.frame_cards = tk.Frame(contenido, bg=C_BG)
        self.frame_cards.pack(fill=tk.X, pady=(0, 10))
        self._dibujar_cards()

        # ── Panel inferior ──
        inferior = tk.Frame(contenido, bg=C_BG)
        inferior.pack(fill=tk.BOTH, expand=True)

        # Historial (pila LIFO)
        hist_frame = tk.Frame(inferior, bg=C_SURF, padx=10, pady=10)
        hist_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        hdr_h = tk.Frame(hist_frame, bg=C_SURF)
        hdr_h.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr_h, text='◈  HISTORIAL DE MANTENIMIENTO  — PILA LIFO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT)
        tk.Label(hdr_h, text='TOPE = MÁS RECIENTE', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7)).pack(side=tk.RIGHT)

        self.lbl_dron_hist = tk.Label(hist_frame, text='Selecciona un dron arriba ↑',
                                       bg=C_SURF, fg=C_MUTED, font=('Courier New', 8))
        self.lbl_dron_hist.pack(anchor='w', pady=(0, 6))

        tk.Frame(hist_frame, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 6))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dron.Treeview',
                        background=C_SURF2, foreground=C_TEXT, fieldbackground=C_SURF2,
                        font=('Courier New', 10), rowheight=30, borderwidth=0)
        style.configure('Dron.Treeview.Heading',
                        background=C_SURF, foreground=C_CYAN,
                        font=('Courier New', 8, 'bold'), relief='flat')
        style.map('Dron.Treeview', background=[('selected', '#0D2A40')])

        cols = ('Pos', 'Operación', 'Técnico', 'Fecha', 'Observación')
        self.tree_hist = ttk.Treeview(hist_frame, columns=cols, show='headings',
                                       height=7, style='Dron.Treeview')
        anchos = [70, 190, 110, 90, 230]
        for col, ancho in zip(cols, anchos):
            self.tree_hist.heading(col, text=col.upper())
            self.tree_hist.column(col, width=ancho, anchor='w')
        self.tree_hist.pack(fill=tk.BOTH, expand=True)
        self.tree_hist.tag_configure('tope', foreground=C_CYAN)

        # ── Formulario nuevo mantenimiento ──
        form = tk.Frame(inferior, bg=C_SURF, padx=14, pady=14, width=270)
        form.pack(side=tk.RIGHT, fill=tk.Y)
        form.pack_propagate(False)

        tk.Label(form, text='◈  REGISTRAR MANTENIMIENTO', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 9, 'bold')).pack(anchor='w', pady=(0, 10))
        tk.Frame(form, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        # Selector de dron
        tk.Label(form, text='DRON', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.var_dron = tk.StringVar()
        self.combo_dron = ttk.Combobox(form, textvariable=self.var_dron,
                                        values=list(self.sistema.drones.keys()),
                                        width=22, state='readonly', font=('Courier New', 9))
        self.combo_dron.pack(pady=(3, 10), anchor='w')

        campos = [
            ('OPERACIÓN',   'entry_op',  'Ej: Limpieza de salitre'),
            ('TÉCNICO',     'entry_tec', 'Ej: Carlos M.'),
            ('OBSERVACIÓN', 'entry_obs', 'Ej: Desgaste por brisa'),
        ]
        for label, attr, ph in campos:
            tk.Label(form, text=label, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7, 'bold')).pack(anchor='w')
            e = tk.Entry(form, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
                         relief=tk.FLAT, font=('Courier New', 10), width=26,
                         highlightthickness=1, highlightbackground=C_BORDER)
            e.insert(0, ph)
            e.bind('<FocusIn>', lambda ev, w=e, p=ph: w.delete(0, tk.END) if w.get() == p else None)
            e.pack(pady=(3, 10), anchor='w', ipady=3)
            setattr(self, attr, e)

        tk.Frame(form, bg=C_BORDER, height=1).pack(fill=tk.X, pady=6)

        tk.Button(form, text='  ◈  REGISTRAR (APILAR)  ', bg=C_CYAN, fg=C_BG,
                  font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CCEE', activeforeground=C_BG,
                  command=self._registrar_mantenimiento).pack(fill=tk.X, pady=(4, 3), ipady=5)

        tk.Button(form, text='  ✔  COMPLETAR ENTREGA  ', bg=C_GREEN, fg=C_BG,
                  font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CC7A',
                  command=self._completar_entrega).pack(fill=tk.X, pady=3, ipady=5)

        tk.Button(form, text='  ⚡  RECARGAR BATERÍA  ', bg=C_SURF2, fg=C_YELLOW,
                  font=('Courier New', 9), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_YELLOW,
                  command=self._recargar).pack(fill=tk.X, pady=3, ipady=4)

    def _dibujar_cards(self):
        for w in self.frame_cards.winfo_children():
            w.destroy()

        for dron in self.sistema.drones.values():
            col = ESTADO_COLOR.get(dron.estado, C_MUTED)
            bc  = bat_color(dron.bateria)

            card = tk.Frame(self.frame_cards, bg=C_SURF, cursor='hand2',
                            padx=12, pady=8)
            card.pack(side=tk.LEFT, padx=(0, 8))

            # Barra superior de estado
            tk.Frame(card, bg=col, height=2).pack(fill=tk.X)
            tk.Frame(card, bg=C_SURF, height=4).pack(fill=tk.X)

            # Fila 1: ID + dot
            f1 = tk.Frame(card, bg=C_SURF)
            f1.pack(fill=tk.X)
            tk.Label(f1, text=dron.id_dron, bg=C_SURF, fg=C_WHITE,
                     font=('Courier New', 14, 'bold')).pack(side=tk.LEFT)
            dot_c = tk.Canvas(f1, width=10, height=10, bg=C_SURF, highlightthickness=0)
            dot_c.pack(side=tk.LEFT, padx=4, pady=4)
            dot_c.create_oval(2, 2, 8, 8, fill=col, outline='')

            tk.Label(card, text=dron.modelo.upper(), bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w')
            tk.Label(card, text=dron.estado.replace('_', ' ').upper(), bg=C_SURF, fg=col,
                     font=('Courier New', 8, 'bold')).pack(anchor='w', pady=(2, 6))

            # Barra de batería
            tk.Label(card, text=f'BATERÍA: {dron.bateria}%', bg=C_SURF, fg=bc,
                     font=('Courier New', 8)).pack(anchor='w')
            track = tk.Frame(card, bg=C_BORDER, height=5, width=150)
            track.pack(anchor='w')
            fw = max(1, int(150 * dron.bateria / 100))
            tk.Frame(track, bg=bc, height=5, width=fw).place(x=0, y=0)

            # Último mantenimiento
            tk.Frame(card, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(6, 4))
            last = dron.ultimo_mantenimiento()
            tk.Label(card, text=last[:32], bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w')

            # Clic para historial
            for w in [card] + list(card.winfo_children()):
                w.bind('<Button-1>', lambda e, d=dron.id_dron: self._ver_historial(d))

    def _ver_historial(self, id_dron):
        self.dron_seleccionado = id_dron
        self.var_dron.set(id_dron)
        self.lbl_dron_hist.config(
            text=f'▶ Dron: {id_dron}  —  TOPE = registro más reciente')
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)
        dron = self.sistema.drones[id_dron]
        for i, reg in enumerate(dron.historial_mantenimiento.a_lista()):
            pos = '▶ TOPE' if i == 0 else str(i+1)
            self.tree_hist.insert('', 'end', iid=f'reg_{i}',
                                   values=(pos, reg.operacion, reg.tecnico,
                                           reg.fecha, reg.observacion),
                                   tags=('tope',) if i == 0 else ())

    def _registrar_mantenimiento(self):
        id_dron = self.var_dron.get()
        op  = self.entry_op.get().strip()
        tec = self.entry_tec.get().strip()
        obs = self.entry_obs.get().strip()
        if not id_dron or not op or not tec:
            messagebox.showwarning('⚠ DATOS INCOMPLETOS',
                                   'Completa dron, operación y técnico.', parent=self)
            return
        fecha = datetime.date.today().strftime('%Y-%m-%d')
        self.sistema.registrar_mantenimiento(id_dron, op, tec, fecha, obs)
        self._dibujar_cards()
        self._ver_historial(id_dron)
        self.callback()
        messagebox.showinfo('◈ REGISTRADO', f'Mantenimiento apilado para {id_dron}', parent=self)

    def _completar_entrega(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('SELECCIONA', 'Selecciona un dron.', parent=self)
            return
        self.sistema.completar_entrega(id_dron)
        self._dibujar_cards()
        self.callback()
        messagebox.showinfo('✔ ENTREGA COMPLETADA', f'{id_dron} ha regresado al almacén.', parent=self)

    def _recargar(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('SELECCIONA', 'Selecciona un dron.', parent=self)
            return
        self.sistema.recargar_dron(id_dron)
        self._dibujar_cards()
        self.callback()
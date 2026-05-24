# Ventana de Gestion de Drones
# Muestra la flota, historial de mantenimiento (Pila LIFO) y permite registrar nuevos

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

BG    = '#0f1415'
PANEL = '#13191a'
CARD  = '#192021'
TEAL  = '#04c7b5'
GREEN = '#48d86e'
RED   = '#ef4444'
AMBER = '#f59e0b'
WHITE = '#edf1f0'
GRAY  = '#809190'
BORDER = '#283435'


class VentanaDron(tk.Toplevel):
    def __init__(self, parent, sistema, callback_actualizar):
        super().__init__(parent)
        self.sistema = sistema
        self.callback = callback_actualizar
        self.title('Gestion de Drones')
        self.geometry('1000x660')
        self.configure(bg=BG)
        self.resizable(False, False)
        self.dron_seleccionado = None
        self._construir_ui()

    def _construir_ui(self):
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  GESTION DE DRONES', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, pady=8)
        tk.Frame(self, bg=TEAL, height=2).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tarjetas de drones (fila superior)
        self.frame_cards = tk.Frame(contenido, bg=BG)
        self.frame_cards.pack(fill=tk.X, pady=(0, 10))
        self._dibujar_cards()

        # Panel inferior: historial + formulario
        inferior = tk.Frame(contenido, bg=BG)
        inferior.pack(fill=tk.BOTH, expand=True)

        # Historial (pila LIFO)
        hist_frame = tk.Frame(inferior, bg=PANEL, padx=10, pady=10)
        hist_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        tk.Label(hist_frame, text='HISTORIAL DE MANTENIMIENTO  (pila LIFO — tope = mas reciente)',
                 bg=PANEL, fg=TEAL, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.lbl_dron_hist = tk.Label(hist_frame, text='Selecciona un dron arriba',
                                       bg=PANEL, fg=GRAY, font=('Segoe UI', 8))
        self.lbl_dron_hist.pack(anchor='w', pady=(0, 6))

        cols = ('Posicion', 'Operacion', 'Tecnico', 'Fecha', 'Observacion')
        self.tree_hist = ttk.Treeview(hist_frame, columns=cols, show='headings', height=8)
        self._estilo_tree()
        anchos = [80, 180, 100, 90, 220]
        for col, ancho in zip(cols, anchos):
            self.tree_hist.heading(col, text=col)
            self.tree_hist.column(col, width=ancho, anchor='w')
        self.tree_hist.pack(fill=tk.BOTH, expand=True)

        # Formulario nuevo mantenimiento
        form = tk.Frame(inferior, bg=PANEL, padx=12, pady=12, width=260)
        form.pack(side=tk.RIGHT, fill=tk.Y)
        form.pack_propagate(False)

        tk.Label(form, text='REGISTRAR MANTENIMIENTO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, 8))

        # Selector de dron
        tk.Label(form, text='Dron', bg=PANEL, fg=GRAY, font=('Segoe UI', 9)).pack(anchor='w')
        self.var_dron = tk.StringVar()
        ids_drones = list(self.sistema.drones.keys())
        self.combo_dron = ttk.Combobox(form, textvariable=self.var_dron,
                                        values=ids_drones, width=22, state='readonly')
        self.combo_dron.pack(pady=(2, 8), anchor='w')

        campos = [
            ('Operacion',    'entry_op',   'Ej: Limpieza de salitre'),
            ('Tecnico',      'entry_tec',  'Ej: Carlos M.'),
            ('Observacion',  'entry_obs',  'Ej: Desgaste por brisa'),
        ]
        for label, attr, ph in campos:
            tk.Label(form, text=label, bg=PANEL, fg=GRAY, font=('Segoe UI', 9)).pack(anchor='w')
            e = tk.Entry(form, bg=CARD, fg=WHITE, insertbackground=TEAL, relief=tk.FLAT,
                         font=('Segoe UI', 10), width=24,
                         highlightthickness=1, highlightbackground=BORDER)
            e.insert(0, ph)
            e.bind('<FocusIn>', lambda ev, w=e, p=ph: w.delete(0, tk.END) if w.get() == p else None)
            e.pack(pady=(2, 8), anchor='w')
            setattr(self, attr, e)

        tk.Button(form, text='Registrar (apilar)', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._registrar_mantenimiento).pack(fill=tk.X, pady=(4, 2))

        tk.Frame(form, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        tk.Button(form, text='Completar entrega', bg=GREEN, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._completar_entrega).pack(fill=tk.X, pady=2)
        tk.Button(form, text='Recargar bateria', bg=CARD, fg=AMBER,
                  font=('Segoe UI', 10), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=AMBER,
                  command=self._recargar).pack(fill=tk.X, pady=2)

    def _dibujar_cards(self):
        for w in self.frame_cards.winfo_children():
            w.destroy()
        for dron in self.sistema.drones.values():
            color = {
                'en_vuelo': GREEN, 'en_espera': TEAL,
                'bateria_baja': RED, 'mantenimiento': AMBER
            }.get(dron.estado, GRAY)

            card = tk.Frame(self.frame_cards, bg=CARD, padx=10, pady=8, cursor='hand2')
            card.pack(side=tk.LEFT, padx=6, ipadx=4)
            # Barra superior de color
            tk.Frame(card, bg=color, height=3).pack(fill=tk.X)

            fila1 = tk.Frame(card, bg=CARD)
            fila1.pack(fill=tk.X, pady=(4, 0))
            tk.Label(fila1, text=dron.id_dron, bg=CARD, fg=WHITE,
                     font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT)
            dot = tk.Label(fila1, text='  ●', bg=CARD, fg=color, font=('Segoe UI', 12))
            dot.pack(side=tk.LEFT)

            tk.Label(card, text=dron.modelo, bg=CARD, fg=GRAY, font=('Segoe UI', 8)).pack(anchor='w')
            tk.Label(card, text=dron.estado.replace('_', ' ').title(), bg=CARD, fg=color,
                     font=('Segoe UI', 9, 'bold')).pack(anchor='w')

            # Barra de bateria
            bat_frame = tk.Frame(card, bg=CARD)
            bat_frame.pack(fill=tk.X, pady=(4, 0))
            tk.Label(bat_frame, text=f'Bat: {dron.bateria}%', bg=CARD,
                     fg=RED if dron.bateria <= 20 else GRAY, font=('Segoe UI', 8)).pack(anchor='w')
            track = tk.Frame(bat_frame, bg=BORDER, height=6, width=160)
            track.pack(anchor='w')
            fill_w = max(1, int(160 * dron.bateria / 100))
            bat_color = RED if dron.bateria < 25 else AMBER if dron.bateria < 60 else GREEN
            tk.Frame(track, bg=bat_color, height=6, width=fill_w).place(x=0, y=0)

            # Ultimo mantenimiento
            tk.Label(card, text='Ultimo mant:', bg=CARD, fg=GRAY, font=('Segoe UI', 8)).pack(anchor='w', pady=(4, 0))
            tk.Label(card, text=dron.ultimo_mantenimiento()[:30], bg=CARD, fg=WHITE,
                     font=('Segoe UI', 8, 'bold')).pack(anchor='w')

            # Clic para ver historial
            card.bind('<Button-1>', lambda e, d=dron.id_dron: self._ver_historial(d))
            for child in card.winfo_children():
                child.bind('<Button-1>', lambda e, d=dron.id_dron: self._ver_historial(d))

    def _ver_historial(self, id_dron):
        self.dron_seleccionado = id_dron
        self.var_dron.set(id_dron)
        self.lbl_dron_hist.config(text=f'Dron: {id_dron}  (tope de la pila = registro mas reciente)')
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)
        dron = self.sistema.drones[id_dron]
        registros = dron.historial_mantenimiento.a_lista()
        for i, reg in enumerate(registros):
            pos = 'TOPE' if i == 0 else str(i + 1)
            self.tree_hist.insert('', 'end', iid=f'reg_{i}',
                                   values=(pos, reg.operacion, reg.tecnico, reg.fecha, reg.observacion),
                                   tags=('tope',) if i == 0 else ())
        self.tree_hist.tag_configure('tope', foreground=TEAL)

    def _registrar_mantenimiento(self):
        id_dron = self.var_dron.get()
        op  = self.entry_op.get().strip()
        tec = self.entry_tec.get().strip()
        obs = self.entry_obs.get().strip()
        if not id_dron or not op or not tec:
            messagebox.showwarning('Datos incompletos', 'Completa dron, operacion y tecnico', parent=self)
            return
        fecha = datetime.date.today().strftime('%Y-%m-%d')
        self.sistema.registrar_mantenimiento(id_dron, op, tec, fecha, obs)
        self._dibujar_cards()
        self._ver_historial(id_dron)
        self.callback()
        messagebox.showinfo('Registrado', f'Mantenimiento apilado para {id_dron}', parent=self)

    def _completar_entrega(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('Selecciona', 'Selecciona un dron', parent=self)
            return
        self.sistema.completar_entrega(id_dron)
        self._dibujar_cards()
        self.callback()
        messagebox.showinfo('Entrega completada', f'{id_dron} volvio al almacen', parent=self)

    def _recargar(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('Selecciona', 'Selecciona un dron', parent=self)
            return
        self.sistema.recargar_dron(id_dron)
        self._dibujar_cards()
        self.callback()

    def _estilo_tree(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=CARD, foreground=WHITE,
                         fieldbackground=CARD, font=('Segoe UI', 10),
                         rowheight=28, borderwidth=0)
        style.configure('Treeview.Heading', background=PANEL, foreground=TEAL,
                         font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Treeview', background=[('selected', '#1e3530')])

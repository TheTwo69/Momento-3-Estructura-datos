# ventana_dron.py — LogiDrone-UCC v5 TACTICAL
# Gestión de flota: agregar drones, historial LIFO, alertas de mantenimiento por batería

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

C_BG      = '#07111F'
C_SURF    = '#0B1929'
C_SURF2   = '#0F2035'
C_BORDER  = '#1A3A5C'
C_CYAN    = '#00E5FF'
C_BLUE    = '#3B82F6'
C_GREEN   = '#00FF9C'
C_YELLOW  = '#FFC857'
C_RED     = '#FF4D6D'
C_RED2    = '#FF0040'        # rojo crítico para alerta mantenimiento
C_TEXT    = '#C8D8E8'
C_MUTED   = '#4A6A8A'
C_WHITE   = '#E8F4FF'
C_ORANGE  = '#FF8C00'        # naranja para "batería baja sin mantenimiento aún"

MODELOS = ['DJI Pro X', 'Phantom 4', 'Mavic 3', 'Agras T40', 'FlyCart 30']

ESTADO_COLOR = {
    'en_vuelo':      C_CYAN,
    'en_espera':     C_BLUE,
    'bateria_baja':  C_ORANGE,
    'mantenimiento': C_RED,
}


def bat_color(pct):
    if pct <= 20: return C_RED       # ≤20% → rojo crítico (necesita mantenimiento)
    if pct <= 40: return C_ORANGE    # ≤40% → naranja advertencia
    if pct <= 60: return C_YELLOW
    return C_GREEN


def necesita_mant(dron):
    """True si el dron está en estado que requiere mantenimiento."""
    return dron.estado == 'mantenimiento' or dron.bateria <= 20


class VentanaDron(tk.Toplevel):
    def __init__(self, parent, sistema, callback_actualizar):
        super().__init__(parent)
        self.sistema  = sistema
        self.callback = callback_actualizar
        self.title('LogiDrone-UCC  ◈  GESTIÓN DE DRONES')
        self.geometry('1120x740')
        self.configure(bg=C_BG)
        self.resizable(True, True)
        self.minsize(900, 600)
        self.dron_seleccionado = None
        self._construir_ui()

    # ── CONSTRUCCIÓN DE UI ────────────────────────────────────────────────────

    def _construir_ui(self):
        # Header
        header = tk.Frame(self, bg=C_SURF, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header,
                 text='  ✦  GESTIÓN DE DRONES  ◈  PILA LIFO DE MANTENIMIENTO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        # Botón "Agregar dron" en la cabecera
        tk.Button(header, text='  ＋  NUEVO DRON  ', bg=C_GREEN, fg=C_BG,
                  font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CC7A', activeforeground=C_BG,
                  command=self._abrir_dialogo_nuevo_dron).pack(side=tk.RIGHT, padx=14, pady=8)
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=C_BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # ── Panel de alertas ──
        self._frame_alertas = tk.Frame(contenido, bg=C_BG)
        self._frame_alertas.pack(fill=tk.X, pady=(0, 8))
        self._dibujar_alertas()

        # ── Cards de drones ──
        cards_outer = tk.Frame(contenido, bg=C_BG)
        cards_outer.pack(fill=tk.X, pady=(0, 10))
        self.frame_cards = cards_outer
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
        self.tree_hist.tag_configure('alerta', foreground=C_RED)

        # ── Formulario nuevo mantenimiento + acciones ──
        form = tk.Frame(inferior, bg=C_SURF, padx=14, pady=14, width=280)
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
                                        width=24, state='readonly', font=('Courier New', 9))
        self.combo_dron.pack(pady=(3, 10), anchor='w')
        self.combo_dron.bind('<<ComboboxSelected>>', self._on_combo_dron)

        # Campos del formulario
        campos = [
            ('OPERACIÓN',   'entry_op',  'Ej: Limpieza de salitre'),
            ('TÉCNICO',     'entry_tec', 'Ej: Carlos M.'),
            ('OBSERVACIÓN', 'entry_obs', 'Ej: Desgaste por brisa'),
        ]
        for label, attr, ph in campos:
            tk.Label(form, text=label, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7, 'bold')).pack(anchor='w')
            e = tk.Entry(form, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
                         relief=tk.FLAT, font=('Courier New', 10), width=28,
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

        tk.Frame(form, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(8, 4))

        tk.Button(form, text='  ✖  RETIRAR DRON  ', bg=C_SURF2, fg=C_RED,
                  font=('Courier New', 8), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_RED,
                  command=self._retirar_dron).pack(fill=tk.X, ipady=4)

    # ── ALERTAS DE MANTENIMIENTO ──────────────────────────────────────────────

    def _dibujar_alertas(self):
        for w in self._frame_alertas.winfo_children():
            w.destroy()

        criticos = [d for d in self.sistema.drones.values() if necesita_mant(d)]
        if not criticos:
            return

        banner = tk.Frame(self._frame_alertas, bg='#1A0008',
                          highlightthickness=1, highlightbackground=C_RED2)
        banner.pack(fill=tk.X)

        hdr_f = tk.Frame(banner, bg='#1A0008')
        hdr_f.pack(fill=tk.X, padx=12, pady=(8, 4))
        tk.Label(hdr_f,
                 text=f'⚠  {len(criticos)} DRON{"ES" if len(criticos)>1 else ""} REQUIERE{"N" if len(criticos)>1 else ""} MANTENIMIENTO',
                 bg='#1A0008', fg=C_RED2, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT)
        tk.Label(hdr_f, text='BATERÍA ≤ 20 %  →  MANTENIMIENTO OBLIGATORIO',
                 bg='#1A0008', fg=C_MUTED, font=('Courier New', 7)).pack(side=tk.RIGHT)

        filas = tk.Frame(banner, bg='#1A0008')
        filas.pack(fill=tk.X, padx=12, pady=(0, 8))

        for dron in criticos:
            fila = tk.Frame(filas, bg='#200510', pady=4, padx=8)
            fila.pack(fill=tk.X, pady=2)

            # Ícono de advertencia
            tk.Label(fila, text='⚠', bg='#200510', fg=C_RED2,
                     font=('Courier New', 12, 'bold')).pack(side=tk.LEFT, padx=(0, 8))

            info = tk.Frame(fila, bg='#200510')
            info.pack(side=tk.LEFT, fill=tk.X, expand=True)

            razon = f'Batería crítica: {dron.bateria}%' if dron.bateria <= 20 else 'En mantenimiento programado'
            tk.Label(info, text=f'{dron.id_dron}  ·  {dron.modelo}',
                     bg='#200510', fg=C_WHITE, font=('Courier New', 9, 'bold')).pack(anchor='w')
            tk.Label(info, text=razon,
                     bg='#200510', fg=C_RED, font=('Courier New', 8)).pack(anchor='w')

            # Botón rápido para registrar mantenimiento
            tk.Button(fila, text='ATENDER →', bg=C_RED2, fg=C_WHITE,
                      font=('Courier New', 7, 'bold'), relief=tk.FLAT, cursor='hand2',
                      command=lambda d=dron.id_dron: self._atender_rapido(d)
                      ).pack(side=tk.RIGHT, padx=(8, 0), ipady=2, ipadx=4)

    def _atender_rapido(self, id_dron):
        """Selecciona el dron en el combo y hace scroll al formulario."""
        self.var_dron.set(id_dron)
        self._ver_historial(id_dron)
        # Enfocar el campo operación
        self.entry_op.focus_set()

    # ── CARDS DE DRONES ───────────────────────────────────────────────────────

    def _dibujar_cards(self):
        for w in self.frame_cards.winfo_children():
            w.destroy()

        scroll_frame = tk.Frame(self.frame_cards, bg=C_BG)
        scroll_frame.pack(fill=tk.X)

        drones = list(self.sistema.drones.values())
        cols_por_fila = 4
        for idx, dron in enumerate(drones):
            fila = idx // cols_por_fila
            col  = idx %  cols_por_fila

            mant = necesita_mant(dron)
            col_estado = C_RED if mant else ESTADO_COLOR.get(dron.estado, C_MUTED)
            bc = bat_color(dron.bateria)

            card = tk.Frame(scroll_frame, bg=C_SURF, cursor='hand2',
                            padx=10, pady=8,
                            highlightthickness=1 if mant else 0,
                            highlightbackground=C_RED2 if mant else C_BORDER)
            card.grid(row=fila, column=col, padx=(0, 8), pady=(0, 8), sticky='nsew')
            scroll_frame.columnconfigure(col, weight=1)

            # Barra superior de estado
            tk.Frame(card, bg=col_estado, height=2).pack(fill=tk.X)

            # Ícono de mantenimiento requerido
            if mant:
                tk.Label(card, text='⚠ MANTENIMIENTO REQUERIDO',
                         bg=C_SURF, fg=C_RED2, font=('Courier New', 7, 'bold')).pack(anchor='w', pady=(4, 0))

            # ID del dron
            f1 = tk.Frame(card, bg=C_SURF)
            f1.pack(fill=tk.X, pady=(4, 0))
            tk.Label(f1, text=dron.id_dron, bg=C_SURF, fg=C_WHITE,
                     font=('Courier New', 13, 'bold')).pack(side=tk.LEFT)

            dot_c = tk.Canvas(f1, width=10, height=10, bg=C_SURF, highlightthickness=0)
            dot_c.pack(side=tk.LEFT, padx=4, pady=3)
            dot_c.create_oval(1, 1, 9, 9, fill=col_estado, outline='')

            tk.Label(card, text=dron.modelo.upper(), bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w')

            est_txt = 'MANTENIMIENTO' if mant else dron.estado.replace('_', ' ').upper()
            tk.Label(card, text=est_txt, bg=C_SURF, fg=col_estado,
                     font=('Courier New', 8, 'bold')).pack(anchor='w', pady=(2, 6))

            # Capacidad y velocidad
            cap_txt = f'Cap: {dron.capacidad_kg} kg  ·  Vel: {int(dron.velocidad_kmh)} km/h'
            tk.Label(card, text=cap_txt, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w', pady=(0, 4))

            # Barra de batería
            bat_lbl = f'BATERÍA: {dron.bateria}%'
            if dron.bateria <= 20:
                bat_lbl += '  ⚠ CRÍTICA'
            tk.Label(card, text=bat_lbl, bg=C_SURF, fg=bc,
                     font=('Courier New', 8, 'bold' if dron.bateria <= 20 else 'normal')).pack(anchor='w')
            track = tk.Frame(card, bg=C_BORDER, height=5, width=140)
            track.pack(anchor='w')
            fw = max(1, int(140 * dron.bateria / 100))
            tk.Frame(track, bg=bc, height=5, width=fw).place(x=0, y=0)

            # Último mantenimiento
            tk.Frame(card, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(6, 4))
            last = dron.ultimo_mantenimiento()
            tk.Label(card, text=last[:30], bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7)).pack(anchor='w')

            # Clic → ver historial
            for w in [card] + list(card.winfo_children()):
                w.bind('<Button-1>', lambda e, d=dron.id_dron: self._ver_historial(d))

    # ── HISTORIAL ─────────────────────────────────────────────────────────────

    def _on_combo_dron(self, event=None):
        id_dron = self.var_dron.get()
        if id_dron:
            self._ver_historial(id_dron)

    def _ver_historial(self, id_dron):
        self.dron_seleccionado = id_dron
        self.var_dron.set(id_dron)
        dron = self.sistema.drones.get(id_dron)
        if not dron:
            return

        sufijo = ''
        if necesita_mant(dron):
            sufijo = '  ⚠  REQUIERE MANTENIMIENTO'

        self.lbl_dron_hist.config(
            text=f'▶ Dron: {id_dron}  —  TOPE = registro más reciente{sufijo}',
            fg=C_RED if necesita_mant(dron) else C_MUTED)

        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)

        for i, reg in enumerate(dron.historial_mantenimiento.a_lista()):
            pos = '▶ TOPE' if i == 0 else str(i + 1)
            tag = 'tope' if i == 0 else ''
            self.tree_hist.insert('', 'end', iid=f'reg_{i}',
                                   values=(pos, reg.operacion, reg.tecnico,
                                           reg.fecha, reg.observacion),
                                   tags=(tag,))

    # ── ACCIONES ──────────────────────────────────────────────────────────────

    def _registrar_mantenimiento(self):
        id_dron = self.var_dron.get()
        op  = self.entry_op.get().strip()
        tec = self.entry_tec.get().strip()
        obs = self.entry_obs.get().strip()
        if not id_dron or not op or not tec:
            messagebox.showwarning('⚠ DATOS INCOMPLETOS',
                                   'Completa dron, operación y técnico.', parent=self)
            return

        dron = self.sistema.drones.get(id_dron)
        fecha = datetime.date.today().strftime('%Y-%m-%d')
        self.sistema.registrar_mantenimiento(id_dron, op, tec, fecha, obs)

        self._refresh_todo()
        messagebox.showinfo('◈ REGISTRADO',
                             f'Mantenimiento apilado para {id_dron}.\n'
                             f'Estado actual: {self.sistema.drones[id_dron].estado.upper()}',
                             parent=self)

    def _completar_entrega(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('SELECCIONA', 'Selecciona un dron.', parent=self)
            return
        self.sistema.completar_entrega(id_dron)
        self._refresh_todo()
        dron = self.sistema.drones.get(id_dron)
        msg = f'{id_dron} ha regresado al almacén.'
        if dron and necesita_mant(dron):
            msg += f'\n\n⚠ ATENCIÓN: Batería en {dron.bateria}%. Requiere mantenimiento antes del próximo vuelo.'
        messagebox.showinfo('✔ ENTREGA COMPLETADA', msg, parent=self)

    def _recargar(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('SELECCIONA', 'Selecciona un dron.', parent=self)
            return
        self.sistema.recargar_dron(id_dron)
        self._refresh_todo()
        messagebox.showinfo('⚡ RECARGA', f'{id_dron} cargado al 100%.', parent=self)

    def _retirar_dron(self):
        id_dron = self.var_dron.get()
        if not id_dron:
            messagebox.showwarning('SELECCIONA', 'Selecciona un dron.', parent=self)
            return
        ok, msg = self.sistema.eliminar_dron(id_dron)
        if ok:
            self.var_dron.set('')
            self._refresh_todo()
            messagebox.showinfo('✖ RETIRADO', msg, parent=self)
        else:
            messagebox.showwarning('⚠ NO SE PUEDE RETIRAR', msg, parent=self)

    # ── DIÁLOGO NUEVO DRON ────────────────────────────────────────────────────

    def _abrir_dialogo_nuevo_dron(self):
        dialogo = tk.Toplevel(self)
        dialogo.title('LogiDrone-UCC  ◈  NUEVO DRON')
        dialogo.geometry('400x360')
        dialogo.configure(bg=C_BG)
        dialogo.resizable(False, False)
        dialogo.grab_set()

        # Header
        hdr = tk.Frame(dialogo, bg=C_SURF, height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text='  ＋  INCORPORAR NUEVO DRON A LA FLOTA',
                 bg=C_SURF, fg=C_GREEN, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT, pady=10)
        tk.Frame(dialogo, bg=C_GREEN, height=1).pack(fill=tk.X)

        form = tk.Frame(dialogo, bg=C_BG, padx=20, pady=16)
        form.pack(fill=tk.BOTH, expand=True)

        def campo(parent, label, attr, valor_default, tipo='entry'):
            tk.Label(parent, text=label, bg=C_BG, fg=C_MUTED,
                     font=('Courier New', 7, 'bold')).pack(anchor='w')
            if tipo == 'combo':
                var = tk.StringVar(value=valor_default)
                w = ttk.Combobox(parent, textvariable=var, values=MODELOS,
                                 width=28, state='readonly', font=('Courier New', 10))
                w.pack(pady=(3, 10), anchor='w')
                setattr(dialogo, attr, var)
            else:
                e = tk.Entry(parent, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
                             relief=tk.FLAT, font=('Courier New', 10), width=30,
                             highlightthickness=1, highlightbackground=C_BORDER)
                e.insert(0, str(valor_default))
                e.pack(pady=(3, 10), anchor='w', ipady=4)
                setattr(dialogo, attr, e)

        campo(form, 'MODELO', 'var_modelo', 'DJI Pro X', 'combo')
        campo(form, 'CAPACIDAD DE CARGA (kg)', 'entry_cap', '5.0')
        campo(form, 'VELOCIDAD DE VUELO (km/h)', 'entry_vel', '80.0')

        # Info
        info = tk.Frame(form, bg=C_SURF2, padx=10, pady=8)
        info.pack(fill=tk.X, pady=(4, 12))
        tk.Label(info,
                 text='El dron recibirá un ID automático y quedará\n'
                      'en estado "en_espera" con batería al 100%.',
                 bg=C_SURF2, fg=C_MUTED, font=('Courier New', 8),
                 justify=tk.LEFT).pack(anchor='w')

        def confirmar():
            try:
                cap = float(dialogo.entry_cap.get())
                vel = float(dialogo.entry_vel.get())
                if cap <= 0 or vel <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning('⚠ DATOS INVÁLIDOS',
                                       'Capacidad y velocidad deben ser números positivos.',
                                       parent=dialogo)
                return

            modelo = dialogo.var_modelo.get()
            dron, msg = self.sistema.agregar_dron(modelo, cap, vel)
            if dron:
                # Actualizar combo
                self.combo_dron.config(values=list(self.sistema.drones.keys()))
                self._refresh_todo()
                dialogo.destroy()
                messagebox.showinfo('◈ DRON INCORPORADO', msg, parent=self)
            else:
                messagebox.showwarning('⚠ ERROR', msg, parent=dialogo)

        tk.Button(form, text='  ＋  INCORPORAR A LA FLOTA  ', bg=C_GREEN, fg=C_BG,
                  font=('Courier New', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CC7A', command=confirmar).pack(fill=tk.X, ipady=6)

        tk.Button(form, text='Cancelar', bg=C_SURF2, fg=C_MUTED,
                  font=('Courier New', 8), relief=tk.FLAT, cursor='hand2',
                  command=dialogo.destroy).pack(fill=tk.X, ipady=3, pady=(6, 0))

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _refresh_todo(self):
        """Actualiza alertas, cards, historial y callback de la ventana principal."""
        # Actualizar combo por si se agregaron / retiraron drones
        self.combo_dron.config(values=list(self.sistema.drones.keys()))
        self._dibujar_alertas()
        self._dibujar_cards()
        if self.dron_seleccionado and self.dron_seleccionado in self.sistema.drones:
            self._ver_historial(self.dron_seleccionado)
        self.callback()
# ventana_pedido.py — LogiDrone-UCC v4 TACTICAL
# Gestión de pedidos con estética HUD futurista

import tkinter as tk
from tkinter import ttk, messagebox

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


class VentanaPedido(tk.Toplevel):
    def __init__(self, parent, sistema, callback_actualizar):
        super().__init__(parent)
        self.sistema = sistema
        self.callback = callback_actualizar
        self.title('LogiDrone-UCC  ◈  GESTIÓN DE PEDIDOS')
        self.geometry('960x620')
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self._construir_ui()
        self._cargar_cola()

    def _construir_ui(self):
        # Header
        header = tk.Frame(self, bg=C_SURF, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  ▶  GESTIÓN DE PEDIDOS  ◈  COLA FIFO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        tk.Label(header, text='PRIMER EN ENTRAR = PRIMERO EN DESPACHARSE',
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 8)).pack(side=tk.RIGHT, padx=14, pady=14)
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=C_BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # ── Formulario izquierdo ──
        form_frame = tk.Frame(contenido, bg=C_SURF, padx=16, pady=14, width=270)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        form_frame.pack_propagate(False)

        tk.Label(form_frame, text='◈  NUEVO PEDIDO', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 10, 'bold')).pack(anchor='w', pady=(0, 12))

        # Destino
        tk.Label(form_frame, text='DESTINO', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        destinos = [(nid, n.nombre) for nid, n in self.sistema.mapa.nodos.items()
                    if n.tipo == 'destino']
        self.var_destino = tk.StringVar()
        self.combo_destino = ttk.Combobox(
            form_frame, textvariable=self.var_destino,
            values=[f"{nid} — {nombre}" for nid, nombre in destinos],
            width=28, state='readonly', font=('Courier New', 9)
        )
        self.combo_destino.pack(pady=(3, 10), fill=tk.X)
        self._estilo_combobox()

        # Tipo
        tk.Label(form_frame, text='TIPO DE SUMINISTRO', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.var_tipo = tk.StringVar(value='Medicamento')
        combo_tipo = ttk.Combobox(form_frame, textvariable=self.var_tipo,
                                   values=['Medicamento', 'Repuesto', 'Documento'],
                                   width=28, state='readonly', font=('Courier New', 9))
        combo_tipo.pack(pady=(3, 10), fill=tk.X)

        # Prioridad
        tk.Label(form_frame, text='PRIORIDAD', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.var_prioridad = tk.StringVar(value='MEDIA')
        pri_frame = tk.Frame(form_frame, bg=C_SURF)
        pri_frame.pack(anchor='w', pady=(3, 10))
        for val, col in [('ALTA', C_RED), ('MEDIA', C_YELLOW), ('BAJA', C_GREEN)]:
            tk.Radiobutton(
                pri_frame, text=val, variable=self.var_prioridad, value=val,
                bg=C_SURF, fg=col, selectcolor=C_SURF2, activebackground=C_SURF,
                font=('Courier New', 10, 'bold'), indicatoron=True
            ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Frame(form_frame, bg=C_BORDER, height=1).pack(fill=tk.X, pady=8)

        # Peso
        tk.Label(form_frame, text='PESO (kg)', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.entry_peso = tk.Entry(
            form_frame, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
            relief=tk.FLAT, font=('Courier New', 12), width=12,
            highlightthickness=1, highlightbackground=C_BORDER
        )
        self.entry_peso.insert(0, '0.5')
        self.entry_peso.pack(pady=(3, 14), anchor='w', ipady=4)

        # Botones
        tk.Button(
            form_frame, text='  ▶  AGREGAR A COLA  ', bg=C_CYAN, fg=C_BG,
            font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
            activebackground='#00CCEE', activeforeground=C_BG,
            command=self._agregar_pedido
        ).pack(fill=tk.X, pady=(0, 4), ipady=5)

        tk.Button(
            form_frame, text='  ✖  LIMPIAR  ', bg=C_SURF2, fg=C_MUTED,
            font=('Courier New', 9), relief=tk.FLAT, cursor='hand2',
            highlightthickness=1, highlightbackground=C_BORDER,
            command=self._limpiar
        ).pack(fill=tk.X, ipady=4)

        # ── Tabla cola derecha ──
        tabla_frame = tk.Frame(contenido, bg=C_SURF, padx=10, pady=10)
        tabla_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hdr_f = tk.Frame(tabla_frame, bg=C_SURF)
        hdr_f.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr_f, text='◈  COLA DE PEDIDOS — FIFO', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 10, 'bold')).pack(side=tk.LEFT)

        self._lbl_count = tk.Label(hdr_f, text='0 pedidos', bg=C_SURF, fg=C_MUTED,
                                    font=('Courier New', 8))
        self._lbl_count.pack(side=tk.RIGHT)

        tk.Frame(tabla_frame, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 6))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Ped.Treeview',
                        background=C_SURF2, foreground=C_TEXT, fieldbackground=C_SURF2,
                        font=('Courier New', 10), rowheight=30, borderwidth=0)
        style.configure('Ped.Treeview.Heading',
                        background=C_SURF, foreground=C_CYAN,
                        font=('Courier New', 8, 'bold'), relief='flat')
        style.map('Ped.Treeview', background=[('selected', '#0D2A40')])

        cols = ('Pos', 'ID', 'Destino', 'Tipo', 'Prioridad', 'Hora')
        self.tree = ttk.Treeview(tabla_frame, columns=cols, show='headings',
                                  height=10, style='Ped.Treeview')
        anchos = [45, 65, 160, 120, 90, 70]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=ancho, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Botones inferiores
        btn_f = tk.Frame(tabla_frame, bg=C_SURF)
        btn_f.pack(fill=tk.X, pady=(8, 0))

        tk.Button(btn_f, text='  ⚡  DESPACHAR SIGUIENTE  ', bg=C_GREEN, fg=C_BG,
                  font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CC7A', activeforeground=C_BG,
                  command=self._despachar).pack(side=tk.LEFT, padx=(0, 6), ipady=4)

        tk.Button(btn_f, text='  ✖  ELIMINAR SEL.  ', bg=C_SURF2, fg=C_RED,
                  font=('Courier New', 9), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_RED,
                  command=self._eliminar_seleccionado).pack(side=tk.LEFT, ipady=4)

    def _estilo_combobox(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox',
                        fieldbackground=C_SURF2, background=C_SURF,
                        foreground=C_WHITE, selectbackground=C_SURF2,
                        selectforeground=C_CYAN)

    def _cargar_cola(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        pedidos = self.sistema.cola_pedidos.a_lista()
        for i, p in enumerate(pedidos):
            self.tree.insert('', 'end', iid=p.id_pedido,
                             values=(i+1, p.id_pedido, p.destino_nombre,
                                     p.tipo, p.prioridad, p.hora_ingreso or '--'))
        self._lbl_count.config(text=f'{len(pedidos)} pedidos')

    def _agregar_pedido(self):
        dest_sel = self.var_destino.get()
        if not dest_sel:
            messagebox.showwarning('FALTA DESTINO', 'Selecciona un destino.', parent=self)
            return
        try:
            peso = float(self.entry_peso.get())
        except ValueError:
            messagebox.showwarning('PESO INVÁLIDO', 'Ingresa un número válido para el peso.', parent=self)
            return

        parts = dest_sel.split(' — ')
        dest_id = parts[0].strip()
        dest_nombre = parts[1].strip() if len(parts) > 1 else dest_id

        self.sistema.crear_pedido(dest_id, dest_nombre, self.var_tipo.get(),
                                   self.var_prioridad.get(), peso)
        self._cargar_cola()
        self.callback()
        messagebox.showinfo('◈ PEDIDO AGREGADO',
                             f'Pedido encolado exitosamente.\nDestino: {dest_nombre}',
                             parent=self)

    def _despachar(self):
        dron, msg = self.sistema.despachar_siguiente()
        self._cargar_cola()
        self.callback()
        if dron:
            messagebox.showinfo('⚡ DESPACHO EXITOSO', msg, parent=self)
        else:
            messagebox.showwarning('⚠ NO SE PUDO DESPACHAR', msg, parent=self)

    def _eliminar_seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('SELECCIONA', 'Selecciona un pedido de la tabla.', parent=self)
            return
        messagebox.showinfo('INFO', 'Usa Despachar para procesar pedidos en orden FIFO.', parent=self)

    def _limpiar(self):
        self.var_destino.set('')
        self.entry_peso.delete(0, tk.END)
        self.entry_peso.insert(0, '0.5')
        self.var_prioridad.set('MEDIA')
# Ventana de Gestion de Pedidos
# Formulario para crear nuevos pedidos y visualizar la cola FIFO

import tkinter as tk
from tkinter import ttk, messagebox

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


class VentanaPedido(tk.Toplevel):
    def __init__(self, parent, sistema, callback_actualizar):
        super().__init__(parent)
        self.sistema = sistema
        self.callback = callback_actualizar
        self.title('Gestion de Pedidos')
        self.geometry('900x600')
        self.configure(bg=BG)
        self.resizable(False, False)
        self._construir_ui()
        self._cargar_cola()

    def _construir_ui(self):
        # Header
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  GESTION DE PEDIDOS', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, pady=8)
        tk.Frame(self, bg=TEAL, height=2).pack(fill=tk.X)

        # Contenido
        contenido = tk.Frame(self, bg=BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Formulario izquierdo
        form_frame = tk.Frame(contenido, bg=PANEL, padx=14, pady=14)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(form_frame, text='NUEVO PEDIDO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, 8))

        # Destino
        tk.Label(form_frame, text='Destino', bg=PANEL, fg=GRAY,
                 font=('Segoe UI', 9)).pack(anchor='w')
        destinos = [(nid, n.nombre) for nid, n in self.sistema.mapa.nodos.items()
                    if n.tipo in ('destino',)]
        self.var_destino = tk.StringVar()
        self.combo_destino = ttk.Combobox(form_frame, textvariable=self.var_destino,
                                           values=[f"{nid} - {nombre}" for nid, nombre in destinos],
                                           width=26, state='readonly')
        self.combo_destino.pack(pady=(2, 8))
        self._estilo_combobox(self.combo_destino)

        # Tipo
        tk.Label(form_frame, text='Tipo de suministro', bg=PANEL, fg=GRAY,
                 font=('Segoe UI', 9)).pack(anchor='w')
        self.var_tipo = tk.StringVar(value='Medicamento')
        combo_tipo = ttk.Combobox(form_frame, textvariable=self.var_tipo,
                                   values=['Medicamento', 'Repuesto', 'Documento'],
                                   width=26, state='readonly')
        combo_tipo.pack(pady=(2, 8))
        self._estilo_combobox(combo_tipo)

        # Prioridad
        tk.Label(form_frame, text='Prioridad', bg=PANEL, fg=GRAY,
                 font=('Segoe UI', 9)).pack(anchor='w')
        self.var_prioridad = tk.StringVar(value='MEDIA')
        for val in ['ALTA', 'MEDIA', 'BAJA']:
            color = {'ALTA': RED, 'MEDIA': AMBER, 'BAJA': GREEN}[val]
            tk.Radiobutton(form_frame, text=val, variable=self.var_prioridad, value=val,
                           bg=PANEL, fg=color, selectcolor=CARD, activebackground=PANEL,
                           font=('Segoe UI', 10, 'bold')).pack(anchor='w')

        tk.Frame(form_frame, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        # Peso
        tk.Label(form_frame, text='Peso (kg)', bg=PANEL, fg=GRAY,
                 font=('Segoe UI', 9)).pack(anchor='w')
        self.entry_peso = tk.Entry(form_frame, bg=CARD, fg=WHITE, insertbackground=TEAL,
                                    relief=tk.FLAT, font=('Segoe UI', 11), width=10,
                                    highlightthickness=1, highlightbackground=BORDER)
        self.entry_peso.insert(0, '0.5')
        self.entry_peso.pack(pady=(2, 12), anchor='w')

        tk.Button(form_frame, text='Agregar a cola', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._agregar_pedido).pack(fill=tk.X, pady=2)
        tk.Button(form_frame, text='Limpiar', bg=CARD, fg=GRAY,
                  font=('Segoe UI', 10), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=BORDER,
                  command=self._limpiar).pack(fill=tk.X, pady=2)

        # Tabla cola derecha
        tabla_frame = tk.Frame(contenido, bg=PANEL, padx=10, pady=10)
        tabla_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(tabla_frame, text='COLA DE PEDIDOS — FIFO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Label(tabla_frame, text='Primer pedido en entrar = primero en despacharse',
                 bg=PANEL, fg=GRAY, font=('Segoe UI', 8)).pack(anchor='w', pady=(0, 6))

        cols_tabla = ('Pos', 'ID', 'Destino', 'Tipo', 'Prioridad', 'Hora')
        self.tree = ttk.Treeview(tabla_frame, columns=cols_tabla, show='headings', height=10)
        self._estilo_tree()

        anchos = [40, 60, 140, 110, 80, 70]
        for col, ancho in zip(cols_tabla, anchos):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Botones inferiores
        btn_frame = tk.Frame(tabla_frame, bg=PANEL)
        btn_frame.pack(fill=tk.X, pady=6)

        tk.Button(btn_frame, text='Despachar siguiente', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._despachar).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_frame, text='Eliminar seleccionado', bg=CARD, fg=RED,
                  font=('Segoe UI', 10), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=RED,
                  command=self._eliminar_seleccionado).pack(side=tk.LEFT)

    def _estilo_combobox(self, combo):
        combo.configure(font=('Segoe UI', 10))

    def _estilo_tree(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=CARD, foreground=WHITE,
                         fieldbackground=CARD, font=('Segoe UI', 10),
                         rowheight=28, borderwidth=0)
        style.configure('Treeview.Heading', background=PANEL, foreground=TEAL,
                         font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Treeview', background=[('selected', '#1e3530')])

    def _cargar_cola(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        pedidos = self.sistema.cola_pedidos.a_lista()
        colores_pri = {'ALTA': RED, 'MEDIA': AMBER, 'BAJA': GREEN}
        for i, p in enumerate(pedidos):
            self.tree.insert('', 'end', iid=p.id_pedido,
                             values=(i+1, p.id_pedido, p.destino_nombre,
                                     p.tipo, p.prioridad, p.hora_ingreso or '--'))

    def _agregar_pedido(self):
        dest_sel = self.var_destino.get()
        if not dest_sel:
            messagebox.showwarning('Falta destino', 'Selecciona un destino', parent=self)
            return
        try:
            peso = float(self.entry_peso.get())
        except ValueError:
            messagebox.showwarning('Peso invalido', 'Ingresa un numero valido para el peso', parent=self)
            return

        dest_id = dest_sel.split(' - ')[0]
        dest_nombre = dest_sel.split(' - ')[1]

        self.sistema.crear_pedido(dest_id, dest_nombre, self.var_tipo.get(),
                                   self.var_prioridad.get(), peso)
        self._cargar_cola()
        self.callback()
        messagebox.showinfo('Pedido agregado', f'Pedido agregado a la cola\nDestino: {dest_nombre}', parent=self)

    def _despachar(self):
        dron, msg = self.sistema.despachar_siguiente()
        self._cargar_cola()
        self.callback()
        if dron:
            messagebox.showinfo('Despacho exitoso', msg, parent=self)
        else:
            messagebox.showwarning('No se pudo despachar', msg, parent=self)

    def _eliminar_seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Selecciona', 'Selecciona un pedido de la tabla', parent=self)
            return
        messagebox.showinfo('Info', 'Para eliminar, usa el boton Despachar o agrega por encima.', parent=self)

    def _limpiar(self):
        self.var_destino.set('')
        self.entry_peso.delete(0, tk.END)
        self.entry_peso.insert(0, '0.5')
        self.var_prioridad.set('MEDIA')

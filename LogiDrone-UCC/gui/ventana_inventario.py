# Ventana de Gestion de Inventario
# Muestra el arbol AVL, permite insertar, buscar y eliminar productos

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


class VentanaInventario(tk.Toplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title('Inventario — Arbol AVL')
        self.geometry('1050x640')
        self.configure(bg=BG)
        self.resizable(False, False)
        self._construir_ui()
        self._cargar_tabla()

    def _construir_ui(self):
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  INVENTARIO — ARBOL AVL', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, pady=8)
        tk.Frame(self, bg=TEAL, height=2).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Formulario izquierdo
        form = tk.Frame(contenido, bg=PANEL, padx=12, pady=12, width=250)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        form.pack_propagate(False)

        tk.Label(form, text='GESTION DE PRODUCTO', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, 8))

        campos = [
            ('ID (clave AVL)',    'entry_id',    '1042'),
            ('Nombre',           'entry_nombre', 'Ej: Ibuprofeno 400mg'),
            ('Stock (unidades)', 'entry_stock',  '50'),
            ('Peso unitario (kg)','entry_peso',  '0.2'),
        ]
        for label, attr, ph in campos:
            tk.Label(form, text=label, bg=PANEL, fg=GRAY, font=('Segoe UI', 9)).pack(anchor='w')
            e = tk.Entry(form, bg=CARD, fg=WHITE, insertbackground=TEAL, relief=tk.FLAT,
                         font=('Segoe UI', 10), width=22,
                         highlightthickness=1, highlightbackground=BORDER)
            e.insert(0, ph)
            e.bind('<FocusIn>', lambda ev, w=e, p=ph: w.delete(0, tk.END) if w.get() == p else None)
            e.pack(pady=(2, 8), anchor='w')
            setattr(self, attr, e)

        tk.Label(form, text='Categoria', bg=PANEL, fg=GRAY, font=('Segoe UI', 9)).pack(anchor='w')
        self.var_cat = tk.StringVar(value='Medicamento')
        combo_cat = ttk.Combobox(form, textvariable=self.var_cat, width=20,
                                  values=['Medicamento', 'Repuesto', 'Documento', 'Herramienta'],
                                  state='readonly')
        combo_cat.pack(pady=(2, 12), anchor='w')

        tk.Button(form, text='Insertar en AVL', bg=TEAL, fg=BG,
                  font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._insertar).pack(fill=tk.X, pady=2)

        tk.Frame(form, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        btn_frame = tk.Frame(form, bg=PANEL)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text='Buscar ID', bg=CARD, fg=TEAL, relief=tk.FLAT,
                  cursor='hand2', font=('Segoe UI', 10),
                  highlightthickness=1, highlightbackground=TEAL,
                  command=self._buscar).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        tk.Button(btn_frame, text='Eliminar ID', bg=CARD, fg=RED, relief=tk.FLAT,
                  cursor='hand2', font=('Segoe UI', 10),
                  highlightthickness=1, highlightbackground=RED,
                  command=self._eliminar).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Panel central: visualizacion del arbol
        centro = tk.Frame(contenido, bg=BG)
        centro.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        tk.Label(centro, text='ARBOL AVL — Recorrido visual (autobalanceado)',
                 bg=BG, fg=TEAL, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Label(centro, text='FE = factor de equilibrio de cada nodo',
                 bg=BG, fg=GRAY, font=('Segoe UI', 8)).pack(anchor='w', pady=(0, 4))

        self.canvas_avl = tk.Canvas(centro, bg=CARD, highlightthickness=0)
        self.canvas_avl.pack(fill=tk.BOTH, expand=True)

        # Tabla derecha
        tabla_frame = tk.Frame(contenido, bg=PANEL, padx=8, pady=8, width=220)
        tabla_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tabla_frame.pack_propagate(False)

        tk.Label(tabla_frame, text='LISTA (inorden)', bg=PANEL, fg=TEAL,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, 4))

        cols = ('ID', 'Nombre', 'Stock', 'Cat.')
        self.tree = ttk.Treeview(tabla_frame, columns=cols, show='headings', height=18)
        self._estilo_tree()
        anchos = [40, 100, 46, 40]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)

        self._dibujar_arbol()

    def _cargar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.sistema.lista_productos():
            color_stock = 'bajo' if p.stock < 10 else ''
            self.tree.insert('', 'end', values=(p.id_producto, p.nombre, p.stock, p.categoria[:4]),
                              tags=(color_stock,))
        self.tree.tag_configure('bajo', foreground=RED)

    def _dibujar_arbol(self):
        self.canvas_avl.delete('all')
        self.canvas_avl.update_idletasks()
        w = self.canvas_avl.winfo_width()
        h = self.canvas_avl.winfo_height()
        if w < 10 or h < 10:
            self.after(100, self._dibujar_arbol)
            return

        nodos = self.sistema.inventario.obtener_nodos_visualizacion()
        if not nodos:
            self.canvas_avl.create_text(w//2, h//2, text='Arbol vacio', fill=GRAY,
                                         font=('Segoe UI', 12))
            return

        # Calcula posicion de cada nodo en el canvas
        max_nivel = max(n['nivel'] for n in nodos)
        nivel_h = h / (max_nivel + 2)
        posiciones = {}

        # Cuenta nodos por nivel para distribuirlos horizontalmente
        nodos_por_nivel = {}
        for n in nodos:
            nodos_por_nivel.setdefault(n['nivel'], []).append(n)

        for nivel, lista in nodos_por_nivel.items():
            count = len(lista)
            for i, n in enumerate(lista):
                x = w * (i + 1) / (count + 1)
                y = nivel_h * (nivel + 1)
                posiciones[n['id']] = (x, y)

        # Dibuja aristas primero
        for n in nodos:
            if n['padre'] is not None and n['padre'] in posiciones and n['id'] in posiciones:
                x1, y1 = posiciones[n['padre']]
                x2, y2 = posiciones[n['id']]
                self.canvas_avl.create_line(x1, y1, x2, y2, fill=BORDER, width=1.5)

        # Dibuja nodos
        r = 22
        for n in nodos:
            if n['id'] not in posiciones:
                continue
            x, y = posiciones[n['id']]
            color = TEAL if n['padre'] is None else WHITE
            # Circulo
            self.canvas_avl.create_oval(x-r, y-r, x+r, y+r,
                                         fill=CARD, outline=color, width=2)
            # ID
            self.canvas_avl.create_text(x, y, text=str(n['id']),
                                         fill=color, font=('Segoe UI', 10, 'bold'))
            # Factor de equilibrio
            self.canvas_avl.create_text(x + r + 4, y - r,
                                         text=f'FE:{n["fe"]}',
                                         fill=GRAY, font=('Segoe UI', 7), anchor='w')

    def _insertar(self):
        try:
            id_p = int(self.entry_id.get())
            nombre = self.entry_nombre.get().strip()
            stock = int(self.entry_stock.get())
            peso = float(self.entry_peso.get())
        except ValueError:
            messagebox.showwarning('Error', 'Verifica que ID, stock y peso sean numeros', parent=self)
            return
        if not nombre:
            messagebox.showwarning('Falta nombre', 'Ingresa el nombre del producto', parent=self)
            return
        self.sistema.agregar_producto(id_p, nombre, self.var_cat.get(), stock, peso)
        self._cargar_tabla()
        self._dibujar_arbol()
        messagebox.showinfo('Insertado', f'Producto {id_p} insertado en el AVL', parent=self)

    def _buscar(self):
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('ID invalido', 'Ingresa un numero como ID', parent=self)
            return
        p = self.sistema.buscar_producto(id_p)
        if p:
            messagebox.showinfo('Encontrado',
                                 f'ID: {p.id_producto}\nNombre: {p.nombre}\nStock: {p.stock}\nCategoria: {p.categoria}',
                                 parent=self)
        else:
            messagebox.showwarning('No encontrado', f'No existe producto con ID {id_p}', parent=self)

    def _eliminar(self):
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('ID invalido', 'Ingresa un numero como ID', parent=self)
            return
        if not messagebox.askyesno('Confirmar', f'Eliminar producto {id_p} del arbol?', parent=self):
            return
        self.sistema.eliminar_producto(id_p)
        self._cargar_tabla()
        self._dibujar_arbol()

    def _estilo_tree(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=CARD, foreground=WHITE,
                         fieldbackground=CARD, font=('Segoe UI', 10),
                         rowheight=26, borderwidth=0)
        style.configure('Treeview.Heading', background=PANEL, foreground=TEAL,
                         font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Treeview', background=[('selected', '#1e3530')])

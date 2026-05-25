# ventana_inventario.py — LogiDrone-UCC v4 TACTICAL
# Gestión de inventario con árbol AVL y estética HUD táctica

import tkinter as tk
from tkinter import ttk, messagebox
import math

C_BG     = '#07111F'
C_SURF   = '#0B1929'
C_SURF2  = '#0F2035'
C_BORDER = '#1A3A5C'
C_CYAN   = '#00E5FF'
C_CYAN_D = '#007A8C'
C_BLUE   = '#3B82F6'
C_GREEN  = '#00FF9C'
C_YELLOW = '#FFC857'
C_RED    = '#FF4D6D'
C_TEXT   = '#C8D8E8'
C_MUTED  = '#4A6A8A'
C_WHITE  = '#E8F4FF'


class VentanaInventario(tk.Toplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title('LogiDrone-UCC  ◈  INVENTARIO  ◈  ÁRBOL AVL')
        self.geometry('1100x660')
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self._construir_ui()
        self._cargar_tabla()

    def _construir_ui(self):
        # Header
        header = tk.Frame(self, bg=C_SURF, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  ⊞  INVENTARIO  ◈  ÁRBOL AVL AUTOBALANCEADO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        tk.Label(header, text='FE = FACTOR DE EQUILIBRIO  |  BÚSQUEDA O(log n)',
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 8)).pack(side=tk.RIGHT, padx=14, pady=14)
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)

        contenido = tk.Frame(self, bg=C_BG)
        contenido.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # ── Formulario izquierdo ──
        form = tk.Frame(contenido, bg=C_SURF, padx=14, pady=14, width=265)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        form.pack_propagate(False)

        tk.Label(form, text='◈  GESTIÓN DE PRODUCTO', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 9, 'bold')).pack(anchor='w', pady=(0, 10))
        tk.Frame(form, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        campos = [
            ('ID  (clave AVL)',       'entry_id',     '1042'),
            ('Nombre',               'entry_nombre',  'Ej: Ibuprofeno 400mg'),
            ('Stock  (unidades)',     'entry_stock',   '50'),
            ('Peso unitario  (kg)',   'entry_peso',    '0.2'),
        ]
        for label, attr, ph in campos:
            tk.Label(form, text=label, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7, 'bold')).pack(anchor='w')
            e = tk.Entry(form, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
                         relief=tk.FLAT, font=('Courier New', 10), width=24,
                         highlightthickness=1, highlightbackground=C_BORDER)
            e.insert(0, ph)
            e.bind('<FocusIn>', lambda ev, w=e, p=ph: w.delete(0, tk.END) if w.get() == p else None)
            e.pack(pady=(3, 10), anchor='w', ipady=3)
            setattr(self, attr, e)

        tk.Label(form, text='CATEGORÍA', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.var_cat = tk.StringVar(value='Medicamento')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox',
                        fieldbackground=C_SURF2, background=C_SURF,
                        foreground=C_WHITE, selectbackground=C_SURF2)
        combo_cat = ttk.Combobox(form, textvariable=self.var_cat, width=22,
                                  values=['Medicamento', 'Repuesto', 'Documento', 'Herramienta'],
                                  state='readonly', font=('Courier New', 9))
        combo_cat.pack(pady=(3, 12), anchor='w')

        tk.Button(form, text='  ▶  INSERTAR EN AVL  ', bg=C_CYAN, fg=C_BG,
                  font=('Courier New', 9, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground='#00CCEE', activeforeground=C_BG,
                  command=self._insertar).pack(fill=tk.X, pady=(0, 3), ipady=5)

        tk.Frame(form, bg=C_BORDER, height=1).pack(fill=tk.X, pady=8)

        btn_row = tk.Frame(form, bg=C_SURF)
        btn_row.pack(fill=tk.X)
        tk.Button(btn_row, text='  ⌕  BUSCAR ID  ', bg=C_SURF2, fg=C_CYAN,
                  font=('Courier New', 8), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_CYAN,
                  command=self._buscar).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4), ipady=4)
        tk.Button(btn_row, text='  ✖  ELIMINAR  ', bg=C_SURF2, fg=C_RED,
                  font=('Courier New', 8), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_RED,
                  command=self._eliminar).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        # ── Canvas AVL central ──
        centro = tk.Frame(contenido, bg=C_BG)
        centro.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        hdr_avl = tk.Frame(centro, bg=C_BG)
        hdr_avl.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr_avl, text='◈  ÁRBOL AVL — VISUALIZACIÓN ESTRUCTURAL',
                 bg=C_BG, fg=C_CYAN, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT)
        tk.Label(hdr_avl, text='INORDEN → IDs ORDENADOS', bg=C_BG, fg=C_MUTED,
                 font=('Courier New', 7)).pack(side=tk.RIGHT)

        self.canvas_avl = tk.Canvas(centro, bg=C_SURF, highlightthickness=0)
        self.canvas_avl.pack(fill=tk.BOTH, expand=True)
        self.canvas_avl.after(80, self._dibujar_arbol)

        # ── Tabla derecha (lista inorden) ──
        tabla_frame = tk.Frame(contenido, bg=C_SURF, padx=8, pady=8, width=230)
        tabla_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tabla_frame.pack_propagate(False)

        tk.Label(tabla_frame, text='LISTA INORDEN', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 8, 'bold')).pack(anchor='w', pady=(0, 6))
        tk.Frame(tabla_frame, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 6))

        style.configure('Inv.Treeview',
                        background=C_SURF2, foreground=C_TEXT, fieldbackground=C_SURF2,
                        font=('Courier New', 9), rowheight=26, borderwidth=0)
        style.configure('Inv.Treeview.Heading',
                        background=C_SURF, foreground=C_CYAN,
                        font=('Courier New', 8, 'bold'), relief='flat')
        style.map('Inv.Treeview', background=[('selected', '#0D2A40')])

        cols = ('ID', 'Nombre', 'Stock', 'Cat.')
        self.tree = ttk.Treeview(tabla_frame, columns=cols, show='headings',
                                  height=20, style='Inv.Treeview')
        anchos = [42, 100, 48, 40]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=ancho, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure('bajo', foreground=C_RED)
        self.tree.tag_configure('medio', foreground=C_YELLOW)

    def _cargar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.sistema.lista_productos():
            tag = 'bajo' if p.stock < 5 else 'medio' if p.stock < 10 else ''
            self.tree.insert('', 'end',
                              values=(p.id_producto, p.nombre[:12], p.stock, p.categoria[:4]),
                              tags=(tag,) if tag else ())

    def _dibujar_arbol(self):
        c = self.canvas_avl
        c.delete('all')
        c.update_idletasks()
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10 or H < 10:
            self.after(100, self._dibujar_arbol)
            return

        # Fondo con grid táctico sutil
        c.create_rectangle(0, 0, W, H, fill=C_SURF, outline='')
        for gx in range(0, W, 50):
            c.create_line(gx, 0, gx, H, fill='#0E2236', width=1)
        for gy in range(0, H, 50):
            c.create_line(0, gy, W, gy, fill='#0E2236', width=1)

        nodos = self.sistema.inventario.obtener_nodos_visualizacion()
        if not nodos:
            c.create_text(W//2, H//2, text='◈  ÁRBOL VACÍO', fill=C_MUTED,
                          font=('Courier New', 12))
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
                x = W * (i+1) / (count+1)
                y = nivel_h * (nivel+1)
                posiciones[n['id']] = (x, y)

        # Aristas con curva suave
        for n in nodos:
            if n['padre'] is not None and n['padre'] in posiciones and n['id'] in posiciones:
                x1, y1 = posiciones[n['padre']]
                x2, y2 = posiciones[n['id']]
                # Línea de fondo
                c.create_line(x1, y1, x2, y2, fill='#0A2030', width=2)
                # Línea neón sutil
                c.create_line(x1, y1, x2, y2, fill=C_CYAN_D, width=1, dash=(4, 4))

        # Nodos
        r = 22
        for n in nodos:
            if n['id'] not in posiciones: continue
            x, y = posiciones[n['id']]
            is_root = n['padre'] is None
            is_unbalanced = abs(n['fe']) > 1

            col = (C_RED if is_unbalanced else C_CYAN if is_root else C_BLUE)
            fill = C_SURF2

            # Anillo exterior pulsante para raíz
            if is_root:
                c.create_oval(x-r-5, y-r-5, x+r+5, y+r+5,
                              fill='', outline=C_CYAN_D, width=1, dash=(2, 4))

            # Cuerpo del nodo
            c.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline=col, width=2)

            # ID del producto
            c.create_text(x, y-5, text=str(n['id']), fill=col,
                          font=('Courier New', 10, 'bold'))

            # Nombre corto
            c.create_text(x, y+7, text=n['nombre'][:6].upper(), fill=C_MUTED,
                          font=('Courier New', 6))

            # Factor de equilibrio
            fe_col = C_RED if is_unbalanced else C_MUTED
            c.create_rectangle(x+r, y-r, x+r+30, y-r+14,
                               fill='#04090F', outline='')
            c.create_text(x+r+2, y-r+7, text=f'FE:{n["fe"]}', fill=fe_col,
                          font=('Courier New', 6), anchor='w')

        # Leyenda
        leyenda_items = [
            ('◈ RAÍZ', C_CYAN),
            ('● NODO', C_BLUE),
            ('⚠ DESBAL.', C_RED),
        ]
        lx, ly = W-10, H-10
        for i, (lbl, col) in enumerate(leyenda_items):
            c.create_text(lx - i*75, ly, text=lbl, fill=col,
                          font=('Courier New', 7, 'bold'), anchor='se')

    def _insertar(self):
        try:
            id_p  = int(self.entry_id.get())
            nombre = self.entry_nombre.get().strip()
            stock  = int(self.entry_stock.get())
            peso   = float(self.entry_peso.get())
        except ValueError:
            messagebox.showwarning('⚠ ERROR', 'Verifica que ID, stock y peso sean números.', parent=self)
            return
        if not nombre:
            messagebox.showwarning('⚠ FALTA NOMBRE', 'Ingresa el nombre del producto.', parent=self)
            return
        self.sistema.agregar_producto(id_p, nombre, self.var_cat.get(), stock, peso)
        self._cargar_tabla()
        self._dibujar_arbol()
        messagebox.showinfo('◈ INSERTADO', f'Producto {id_p} insertado en el AVL.', parent=self)

    def _buscar(self):
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('⚠ ID INVÁLIDO', 'Ingresa un número como ID.', parent=self)
            return
        p = self.sistema.buscar_producto(id_p)
        if p:
            messagebox.showinfo('◈ ENCONTRADO',
                                 f'ID: {p.id_producto}\nNOMBRE: {p.nombre}\n'
                                 f'STOCK: {p.stock}\nCATEGORÍA: {p.categoria}\nPESO: {p.peso_kg} kg',
                                 parent=self)
        else:
            messagebox.showwarning('✖ NO ENCONTRADO', f'No existe producto con ID {id_p}.', parent=self)

    def _eliminar(self):
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('⚠ ID INVÁLIDO', 'Ingresa un número como ID.', parent=self)
            return
        if not messagebox.askyesno('CONFIRMAR', f'¿Eliminar producto {id_p} del árbol AVL?', parent=self):
            return
        self.sistema.eliminar_producto(id_p)
        self._cargar_tabla()
        self._dibujar_arbol()
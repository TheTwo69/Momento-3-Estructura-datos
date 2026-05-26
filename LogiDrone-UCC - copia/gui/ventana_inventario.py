# ventana_inventario.py — LogiDrone-UCC  AVL Visualizer RENOVADO
# Mejoras v2:
#   · Eliminación desde la tabla inorden (clic en fila + botón)
#   · Eliminación desde el árbol (clic en nodo lo selecciona para eliminar)
#   · Botón "ELIMINAR SELECCIONADO" siempre visible con estado activo/inactivo
#   · Feedback visual: fila resaltada, nodo seleccionado en rojo antes de borrar
#   · El inspector muestra botón "Eliminar este nodo" al seleccionar uno

import tkinter as tk
from tkinter import ttk, messagebox
import math

# ── Paleta táctica ────────────────────────────────────────────────────────────
C_BG      = '#07111F'
C_SURF    = '#0B1929'
C_SURF2   = '#0F2035'
C_BORDER  = '#1A3A5C'
C_CYAN    = '#00E5FF'
C_BLUE    = '#4A90E2'
C_PURPLE  = '#A855F7'
C_GREEN   = '#00E87A'
C_YELLOW  = '#FFC857'
C_RED     = '#FF4D6D'
C_TEXT    = '#C8D8E8'
C_MUTED   = '#4A6A8A'
C_WHITE   = '#E8F4FF'

# Colores específicos del árbol
AVL_ROOT       = '#00D4FF'
AVL_LEFT       = '#4A90E2'
AVL_LEFT_LEAF  = '#00B4FF'
AVL_RIGHT      = '#A855F7'
AVL_RIGHT_LEAF = '#C084FC'
AVL_LEAF       = '#00E87A'
AVL_INTERNAL   = '#94B8D4'
AVL_FE_OK      = '#22D3EE'
AVL_FE_WARN    = '#F59E0B'
AVL_FE_BAD     = '#EF4444'
AVL_SELECTED   = '#FF4D6D'   # Rojo para nodo seleccionado para eliminar


def fe_color(fe):
    if abs(fe) >= 2: return AVL_FE_BAD
    if abs(fe) == 1: return AVL_FE_WARN
    return AVL_FE_OK


class VentanaInventario(tk.Toplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema  = sistema
        self.title('LogiDrone-UCC  ◈  INVENTARIO  ◈  ÁRBOL AVL')
        self.geometry('1240x720')
        self.configure(bg=C_BG)
        self.resizable(True, True)
        self.minsize(900, 580)

        # Estado del canvas (pan + zoom)
        self._scale     = 1.0
        self._offset_x  = 0.0
        self._offset_y  = 0.0
        self._drag_x    = 0
        self._drag_y    = 0
        self._selected  = None          # id del nodo seleccionado (int)
        self._node_meta = {}            # {id: {'color':…, 'cx':…, 'cy':…, …}}

        self._build_ui()
        self._load_table()
        self.after(80, self._draw_tree)

    # ── CONSTRUCCIÓN DE LA INTERFAZ ───────────────────────────────────────────
    def _build_ui(self):
        # Cabecera
        hdr = tk.Frame(self, bg=C_SURF, height=44)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text='  ⊞  INVENTARIO  ◈  ÁRBOL AVL AUTOBALANCEADO',
                 bg=C_SURF, fg=C_CYAN, font=('Courier New', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        tk.Label(hdr, text='FE = FACTOR DE EQUILIBRIO  |  O(log n)',
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 8)).pack(side=tk.RIGHT, padx=14)
        tk.Frame(self, bg=C_CYAN, height=1).pack(fill=tk.X)

        # Leyenda
        leg = tk.Frame(self, bg=C_SURF2, pady=5)
        leg.pack(fill=tk.X)
        for label, color in [
            ('● Raíz', AVL_ROOT), ('● Sub. izquierdo', AVL_LEFT),
            ('● Sub. derecho', AVL_RIGHT), ('◆ Hoja', AVL_LEAF),
            ('● Seleccionado', AVL_SELECTED),
        ]:
            tk.Label(leg, text=label, bg=C_SURF2, fg=color,
                     font=('Courier New', 8, 'bold')).pack(side=tk.LEFT, padx=12)
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill=tk.X)

        # Layout principal
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Panel izquierdo: formulario + tabla ──
        left = tk.Frame(body, bg=C_SURF, width=250, padx=12, pady=12)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)
        self._build_form(left)

        # ── Canvas central: árbol ──
        center = tk.Frame(body, bg=C_BG)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self._build_canvas(center)

        # ── Panel derecho: inspector ──
        right = tk.Frame(body, bg=C_SURF, width=200, padx=12, pady=12)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        self._build_inspector(right)

    def _build_form(self, parent):
        tk.Label(parent, text='◈  GESTIÓN DE PRODUCTO', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 9, 'bold')).pack(anchor='w', pady=(0, 8))
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 8))

        campos = [
            ('ID  (clave AVL)',     'entry_id',     '1042'),
            ('Nombre',              'entry_nombre',  'Ibuprofeno 400mg'),
            ('Stock  (unidades)',   'entry_stock',   '50'),
            ('Peso unitario  (kg)', 'entry_peso',    '0.2'),
        ]
        for label, attr, ph in campos:
            tk.Label(parent, text=label, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7, 'bold')).pack(anchor='w')
            e = tk.Entry(parent, bg=C_SURF2, fg=C_WHITE, insertbackground=C_CYAN,
                         relief=tk.FLAT, font=('Courier New', 9), width=24,
                         highlightthickness=1, highlightbackground=C_BORDER)
            e.insert(0, ph)
            e.bind('<FocusIn>', lambda ev, w=e, p=ph: w.delete(0, tk.END) if w.get()==p else None)
            e.pack(pady=(2, 8), anchor='w', ipady=3)
            setattr(self, attr, e)

        tk.Label(parent, text='CATEGORÍA', bg=C_SURF, fg=C_MUTED,
                 font=('Courier New', 7, 'bold')).pack(anchor='w')
        self.var_cat = tk.StringVar(value='Medicamento')
        ttk.Combobox(parent, textvariable=self.var_cat, width=22,
                     values=['Medicamento','Repuesto','Documento','Herramienta'],
                     state='readonly', font=('Courier New', 9)).pack(pady=(2, 10), anchor='w')

        tk.Button(parent, text='▶  INSERTAR EN AVL', bg=C_CYAN, fg=C_BG,
                  font=('Courier New', 8, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._insertar).pack(fill=tk.X, ipady=5, pady=(0, 4))

        row = tk.Frame(parent, bg=C_SURF)
        row.pack(fill=tk.X, pady=(0, 4))
        tk.Button(row, text='⌕ BUSCAR', bg=C_SURF2, fg=C_CYAN,
                  font=('Courier New', 7), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_CYAN,
                  command=self._buscar).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                             padx=(0,4), ipady=3)
        tk.Button(row, text='✖ ELIMINAR', bg=C_SURF2, fg=C_RED,
                  font=('Courier New', 7), relief=tk.FLAT, cursor='hand2',
                  highlightthickness=1, highlightbackground=C_RED,
                  command=self._eliminar_por_id).pack(side=tk.LEFT, fill=tk.X,
                                                      expand=True, ipady=3)

        # ── Botón eliminar seleccionado (desde árbol o tabla) ──
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(4, 8))
        self._btn_del_sel = tk.Button(
            parent, text='✖  ELIMINAR SELECCIONADO',
            bg=C_RED, fg=C_WHITE,
            font=('Courier New', 8, 'bold'), relief=tk.FLAT, cursor='hand2',
            state=tk.DISABLED, disabledforeground='#7A1E30',
            command=self._eliminar_seleccionado
        )
        self._btn_del_sel.pack(fill=tk.X, ipady=5, pady=(0, 8))
        self._lbl_sel = tk.Label(parent, text='Ningún nodo seleccionado',
                                  bg=C_SURF, fg=C_MUTED, font=('Courier New', 7),
                                  wraplength=220, justify=tk.LEFT)
        self._lbl_sel.pack(anchor='w')

        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X, pady=8)
        tk.Label(parent, text='LISTA INORDEN', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 8, 'bold')).pack(anchor='w', pady=(0, 4))

        style = ttk.Style(); style.theme_use('clam')
        style.configure('Inv.Treeview',
                        background=C_SURF2, foreground=C_TEXT,
                        fieldbackground=C_SURF2, font=('Courier New', 8),
                        rowheight=22, borderwidth=0)
        style.configure('Inv.Treeview.Heading',
                        background=C_SURF, foreground=C_CYAN,
                        font=('Courier New', 7, 'bold'), relief='flat')
        style.map('Inv.Treeview', background=[('selected','#1A0308')])

        cols = ('ID','Nombre','Stock')
        self.tree_tbl = ttk.Treeview(parent, columns=cols, show='headings',
                                      height=10, style='Inv.Treeview',
                                      selectmode='browse')
        for col, w in zip(cols, [40, 92, 44]):
            self.tree_tbl.heading(col, text=col)
            self.tree_tbl.column(col, width=w, anchor='center')
        self.tree_tbl.pack(fill=tk.BOTH, expand=True)
        self.tree_tbl.tag_configure('bajo',  foreground=C_RED)
        self.tree_tbl.tag_configure('medio', foreground=C_YELLOW)
        self.tree_tbl.tag_configure('sel',   foreground=C_WHITE, background='#1A0308')

        # Al seleccionar una fila, selecciona el nodo en el árbol
        self.tree_tbl.bind('<<TreeviewSelect>>', self._on_table_select)

    def _build_canvas(self, parent):
        hdr = tk.Frame(parent, bg=C_BG)
        hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr, text='◈  ÁRBOL AVL — VISUALIZACIÓN ESTRUCTURAL',
                 bg=C_BG, fg=C_CYAN, font=('Courier New', 9, 'bold')).pack(side=tk.LEFT)

        ctrl = tk.Frame(hdr, bg=C_BG)
        ctrl.pack(side=tk.RIGHT)
        for txt, delta in [('−', -0.15), ('+', 0.15)]:
            tk.Button(ctrl, text=txt, bg=C_SURF2, fg=C_TEXT,
                      font=('Courier New', 9), relief=tk.FLAT, cursor='hand2',
                      highlightthickness=1, highlightbackground=C_BORDER,
                      command=lambda d=delta: self._zoom(d)).pack(side=tk.LEFT, padx=2,
                                                                   ipady=1, ipadx=4)
        tk.Button(ctrl, text='⟳ Reset', bg=C_SURF2, fg=C_MUTED,
                  font=('Courier New', 7), relief=tk.FLAT, cursor='hand2',
                  command=self._reset_view).pack(side=tk.LEFT, padx=4, ipady=1, ipadx=4)
        self._lbl_zoom = tk.Label(ctrl, text='100%', bg=C_BG, fg=C_MUTED,
                                   font=('Courier New', 7))
        self._lbl_zoom.pack(side=tk.LEFT)

        self.canvas = tk.Canvas(parent, bg=C_SURF, highlightthickness=0, cursor='fleur')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind('<Configure>', lambda e: self._draw_tree())
        self.canvas.bind('<ButtonPress-1>',  self._on_press)
        self.canvas.bind('<B1-Motion>',       self._on_drag)
        self.canvas.bind('<MouseWheel>',      self._on_wheel)
        self.canvas.bind('<Button-4>',        lambda e: self._zoom(0.1))
        self.canvas.bind('<Button-5>',        lambda e: self._zoom(-0.1))

    def _build_inspector(self, parent):
        tk.Label(parent, text='◈  INSPECTOR', bg=C_SURF, fg=C_CYAN,
                 font=('Courier New', 8, 'bold')).pack(anchor='w', pady=(0, 6))
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(0, 8))
        self._inspector_frame = tk.Frame(parent, bg=C_SURF)
        self._inspector_frame.pack(fill=tk.BOTH, expand=True)
        self._show_inspector_empty()

    def _show_inspector_empty(self):
        for w in self._inspector_frame.winfo_children(): w.destroy()
        tk.Label(self._inspector_frame,
                 text='Haz clic en un\nnodo del árbol\no en la tabla\npara inspeccionar.',
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 8),
                 justify=tk.LEFT).pack(anchor='w')

    def _show_inspector(self, node_id):
        for w in self._inspector_frame.winfo_children(): w.destroy()
        meta = self._node_meta.get(node_id)
        if not meta: return
        color = meta['color']

        tk.Label(self._inspector_frame, text=str(node_id),
                 bg=C_SURF, fg=color, font=('Courier New', 22, 'bold')).pack(anchor='w')
        tk.Label(self._inspector_frame, text=meta.get('nombre',''),
                 bg=C_SURF, fg=C_MUTED, font=('Courier New', 8)).pack(anchor='w', pady=(0, 8))

        rows = [
            ('Tipo',  meta.get('tipo','')),
            ('Nivel', str(meta.get('nivel',0))),
            ('FE',    f"{'+' if meta['fe']>0 else ''}{meta['fe']}"),
        ]
        for lbl, val in rows:
            f = tk.Frame(self._inspector_frame, bg=C_SURF)
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=lbl, bg=C_SURF, fg=C_MUTED,
                     font=('Courier New', 7, 'bold'), width=6, anchor='w').pack(side=tk.LEFT)
            fe_col = color if lbl != 'FE' else fe_color(meta['fe'])
            tk.Label(f, text=val, bg=C_SURF, fg=fe_col,
                     font=('Courier New', 9, 'bold')).pack(side=tk.LEFT)
            tk.Frame(self._inspector_frame, bg=C_BORDER, height=1).pack(fill=tk.X)

        if meta.get('is_leaf'):
            tk.Label(self._inspector_frame, text='◆ Nodo hoja\nSin descendientes.',
                     bg=C_SURF, fg=AVL_LEAF, font=('Courier New', 7),
                     justify=tk.LEFT).pack(anchor='w', pady=(8, 0))

        # Botón de eliminación rápida desde el inspector
        tk.Frame(self._inspector_frame, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(12, 6))
        tk.Button(self._inspector_frame,
                  text=f'✖  ELIMINAR ID {node_id}',
                  bg=C_RED, fg=C_WHITE,
                  font=('Courier New', 8, 'bold'), relief=tk.FLAT, cursor='hand2',
                  command=lambda nid=node_id: self._eliminar_nodo(nid)
                  ).pack(fill=tk.X, ipady=5)

    # ── TABLA INORDEN ─────────────────────────────────────────────────────────
    def _load_table(self):
        for item in self.tree_tbl.get_children():
            self.tree_tbl.delete(item)
        for p in self.sistema.lista_productos():
            tag = 'bajo' if p.stock < 5 else 'medio' if p.stock < 10 else ''
            self.tree_tbl.insert('', 'end', iid=str(p.id_producto),
                                  values=(p.id_producto, p.nombre[:13], p.stock),
                                  tags=(tag,) if tag else ())

    def _on_table_select(self, event):
        sel = self.tree_tbl.selection()
        if not sel: return
        try:
            node_id = int(sel[0])
        except ValueError:
            return
        self._set_selected(node_id)
        self._draw_tree()
        # Sincronizar entry_id
        self.entry_id.delete(0, tk.END)
        self.entry_id.insert(0, str(node_id))

    # ── GESTIÓN DE SELECCIÓN ──────────────────────────────────────────────────
    def _set_selected(self, node_id):
        self._selected = node_id
        meta = self._node_meta.get(node_id, {})
        nombre = meta.get('nombre', '')
        self._lbl_sel.config(
            text=f'Seleccionado: ID {node_id}\n{nombre}',
            fg=C_RED
        )
        self._btn_del_sel.config(state=tk.NORMAL, bg=C_RED)
        self._show_inspector(node_id)
        # Resaltar fila en tabla
        try:
            self.tree_tbl.selection_set(str(node_id))
        except Exception:
            pass

    def _clear_selected(self):
        self._selected = None
        self._lbl_sel.config(text='Ningún nodo seleccionado', fg=C_MUTED)
        self._btn_del_sel.config(state=tk.DISABLED, bg='#3A0B14')
        self._show_inspector_empty()
        self.tree_tbl.selection_remove(*self.tree_tbl.selection())

    # ── DIBUJO DEL ÁRBOL ─────────────────────────────────────────────────────
    def _draw_tree(self):
        c = self.canvas
        c.delete('all')
        c.update_idletasks()
        W, H = c.winfo_width(), c.winfo_height()
        if W < 20 or H < 20:
            self.after(100, self._draw_tree)
            return

        # Fondo con grid táctica
        c.create_rectangle(0, 0, W, H, fill=C_SURF, outline='')
        for gx in range(0, W, 48):
            c.create_line(gx, 0, gx, H, fill='#0E2236', width=1)
        for gy in range(0, H, 48):
            c.create_line(0, gy, W, gy, fill='#0E2236', width=1)

        nodos = self.sistema.inventario.obtener_nodos_visualizacion()
        self._node_meta = {}

        if not nodos:
            c.create_text(W//2, H//2, text='◈  ÁRBOL VACÍO',
                          fill=C_MUTED, font=('Courier New', 12))
            return

        # ── Layout ──
        max_nivel = max(n['nivel'] for n in nodos)
        nivel_h   = (H * 0.85) / (max_nivel + 1)
        by_level  = {}
        for n in nodos:
            by_level.setdefault(n['nivel'], []).append(n)

        posiciones = {}
        for nivel, lista in by_level.items():
            count = len(lista)
            for i, n in enumerate(lista):
                x = W * (i + 1) / (count + 1)
                y = self._offset_y + nivel_h * (nivel + 1) * self._scale + 10
                posiciones[n['id']] = (
                    self._offset_x + (x - W/2) * (self._scale - 1) + x,
                    y,
                )

        # ── Identificar lados ──
        root_node = next((n for n in nodos if n['padre'] is None), None)
        left_ids, right_ids = set(), set()

        def marca_lado(nid, lado):
            if lado == 'left':  left_ids.add(nid)
            else:               right_ids.add(nid)
            for hijo in nodos:
                if hijo['padre'] == nid:
                    marca_lado(hijo['id'], lado)

        if root_node:
            root_x = posiciones[root_node['id']][0]
            for hijo in nodos:
                if hijo['padre'] == root_node['id']:
                    lado = 'left' if posiciones[hijo['id']][0] < root_x else 'right'
                    marca_lado(hijo['id'], lado)

        # ── Zonas de subárbol ──
        def zona_rect(ids, color):
            xs = [posiciones[i][0] for i in ids if i in posiciones]
            ys = [posiciones[i][1] for i in ids if i in posiciones]
            if not xs: return
            pad = 38
            c.create_rectangle(min(xs)-pad, min(ys)-pad,
                                max(xs)+pad, max(ys)+pad,
                                outline=color, width=1, dash=(8, 5),
                                fill=self._hex_alpha(color, 0.04))

        def zona_label(ids, color, txt):
            xs = [posiciones[i][0] for i in ids if i in posiciones]
            ys = [posiciones[i][1] for i in ids if i in posiciones]
            if not xs: return
            c.create_text(min(xs)-34, min(ys)-52, text=txt,
                          fill=color, font=('Courier New', 7, 'bold'), anchor='w')

        if left_ids:  zona_rect(left_ids, AVL_LEFT);  zona_label(left_ids,  AVL_LEFT,  'LEFT SUBTREE')
        if right_ids: zona_rect(right_ids, AVL_RIGHT); zona_label(right_ids, AVL_RIGHT, 'RIGHT SUBTREE')

        # ── Aristas ──
        for n in nodos:
            if n['padre'] is None or n['padre'] not in posiciones or n['id'] not in posiciones:
                continue
            x1, y1 = posiciones[n['padre']]
            x2, y2 = posiciones[n['id']]
            color = self._node_color(n['id'], root_node, left_ids, right_ids, nodos)
            r_src = 28 if n['padre'] == root_node['id'] else 24
            r_dst = 22 if not any(h['padre']==n['id'] for h in nodos) else 24
            mid_y = (y1 + y2) / 2
            c.create_line(x1, y1+r_src, x1, mid_y, x2, mid_y, x2, y2-r_dst,
                          fill=color, width=1.4 if n['padre']==root_node['id'] else 1,
                          smooth=True)

        # ── Nodos ──
        r_root = int(28 * self._scale)
        r_node = int(24 * self._scale)
        r_leaf = int(21 * self._scale)

        for n in nodos:
            if n['id'] not in posiciones: continue
            x, y = posiciones[n['id']]
            is_root = n['padre'] is None
            is_leaf = not any(h['padre'] == n['id'] for h in nodos)
            is_sel  = (n['id'] == self._selected)
            color   = AVL_SELECTED if is_sel else self._node_color(n['id'], root_node, left_ids, right_ids, nodos)
            fe      = n['fe']
            fc      = fe_color(fe)
            r       = r_root if is_root else r_leaf if is_leaf else r_node

            # Halo raíz
            if is_root:
                for halo_r, alpha in [(r+18, 0.05), (r+8, 0.12)]:
                    c.create_oval(x-halo_r, y-halo_r, x+halo_r, y+halo_r,
                                  fill=self._hex_alpha(color, alpha), outline='')

            # Anillo de selección (pulsante en rojo)
            if is_sel:
                c.create_oval(x-r-10, y-r-10, x+r+10, y+r+10,
                              fill='', outline=AVL_SELECTED, width=2, dash=(4, 3))
                c.create_oval(x-r-5, y-r-5, x+r+5, y+r+5,
                              fill=self._hex_alpha(AVL_SELECTED, 0.15), outline=AVL_SELECTED, width=1)

            # Cuerpo
            tag = f'node_{n["id"]}'
            body_fill = self._hex_alpha(AVL_SELECTED, 0.18) if is_sel else C_SURF2
            c.create_oval(x-r, y-r, x+r, y+r,
                          fill=body_fill, outline=color,
                          width=2.5 if is_sel else (2.2 if is_root else 1.5),
                          tags=(tag,))

            # ID
            font_sz = max(8, min(int(14 * self._scale) if is_root else int(11 * self._scale), 16))
            c.create_text(x, y - (6*self._scale), text=str(n['id']),
                          fill=color, font=('Courier New', font_sz, 'bold'), tags=(tag,))

            # Nombre corto
            if not is_leaf:
                ns = max(6, min(int(7 * self._scale), 9))
                c.create_text(x, y + (6*self._scale), text=n['nombre'][:7].upper(),
                               fill=C_MUTED, font=('Courier New', ns), tags=(tag,))

            # Rombo hoja
            if is_leaf:
                ds = max(5, min(int(7 * self._scale), 9))
                c.create_text(x, y + (6*self._scale), text='◆',
                               fill=color, font=('Courier New', ds), tags=(tag,))

            # Ícono de eliminar cuando seleccionado
            if is_sel:
                xi_sz = max(7, min(int(9 * self._scale), 12))
                c.create_text(x, y - r - 20, text='✖ ELIMINAR',
                               fill=AVL_SELECTED, font=('Courier New', xi_sz, 'bold'))

            # Badge FE
            fe_str = f'FE:{fe:+d}' if fe != 0 else 'FE:0'
            bw = len(fe_str)*5 + 8
            bx = x + r - 2; by = y - r - 15
            c.create_rectangle(bx, by, bx+bw, by+14, fill=C_BG, outline=fc, width=0.8)
            c.create_text(bx + bw//2, by+7, text=fe_str,
                          fill=fc, font=('Courier New', 7))

            # Guardar meta
            tipo_lbl = ('Raíz' if is_root else
                        'Hoja' if is_leaf else
                        'Interno izquierdo' if n['id'] in left_ids else
                        'Interno derecho'   if n['id'] in right_ids else 'Interno')
            self._node_meta[n['id']] = {
                'color': color if not is_sel else AVL_SELECTED,
                'cx': x, 'cy': y, 'r': r,
                'nombre': n['nombre'], 'tipo': tipo_lbl,
                'nivel': n['nivel'], 'fe': fe, 'is_leaf': is_leaf,
            }

            # Eventos hover + click
            c.tag_bind(tag, '<Enter>',
                       lambda e, t=tag: self.canvas.itemconfigure(t, fill='#12233A'))
            c.tag_bind(tag, '<Leave>',
                       lambda e, t=tag, nid=n['id']:
                           self.canvas.itemconfigure(
                               t, fill=self._hex_alpha(AVL_SELECTED, 0.18)
                               if nid == self._selected else C_SURF2))
            c.tag_bind(tag, '<Button-1>',
                       lambda e, nid=n['id']: self._on_node_click(nid))

    # ── Helpers de color ──────────────────────────────────────────────────────
    def _node_color(self, nid, root_node, left_ids, right_ids, nodos):
        if root_node and nid == root_node['id']: return AVL_ROOT
        is_leaf = not any(h['padre'] == nid for h in nodos)
        if nid in left_ids:  return AVL_LEFT_LEAF  if is_leaf else AVL_LEFT
        if nid in right_ids: return AVL_RIGHT_LEAF if is_leaf else AVL_RIGHT
        return AVL_LEAF if is_leaf else AVL_INTERNAL

    @staticmethod
    def _hex_alpha(hex_color, alpha):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        br, bg_, bb = 0x0F, 0x20, 0x35
        rr = int(br + (r - br) * alpha)
        gr = int(bg_ + (g - bg_) * alpha)
        bbl = int(bb + (b - bb) * alpha)
        return f'#{rr:02X}{gr:02X}{bbl:02X}'

    # ── Interacción ───────────────────────────────────────────────────────────
    def _on_node_click(self, nid):
        if self._selected == nid:
            # Segundo clic en el mismo nodo: preguntar si eliminar
            if messagebox.askyesno(
                '✖ ELIMINAR NODO',
                f'¿Eliminar ID {nid} — "{self._node_meta.get(nid, {}).get("nombre", "")}" del AVL?',
                parent=self
            ):
                self._eliminar_nodo(nid)
            return
        self._set_selected(nid)
        self._draw_tree()

    def _on_press(self, event):
        # Si no se hizo clic sobre un nodo → deseleccionar
        items = self.canvas.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
        is_on_node = any('node_' in (self.canvas.gettags(i) or ('',))[0]
                         for i in items if self.canvas.gettags(i))
        if not is_on_node:
            self._clear_selected()
            self._draw_tree()
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        self._offset_x += dx * 0.5
        self._offset_y += dy * 0.5
        self._drag_x = event.x
        self._drag_y = event.y
        self._draw_tree()

    def _on_wheel(self, event):
        delta = 0.12 if event.delta > 0 else -0.12
        self._zoom(delta)

    def _zoom(self, delta):
        self._scale = max(0.3, min(2.5, self._scale + delta))
        self._lbl_zoom.config(text=f'{int(self._scale*100)}%')
        self._draw_tree()

    def _reset_view(self):
        self._scale = 1.0; self._offset_x = 0; self._offset_y = 0
        self._lbl_zoom.config(text='100%')
        self._draw_tree()

    # ── Acciones CRUD ─────────────────────────────────────────────────────────
    def _insertar(self):
        try:
            id_p   = int(self.entry_id.get())
            nombre = self.entry_nombre.get().strip()
            stock  = int(self.entry_stock.get())
            peso   = float(self.entry_peso.get())
        except ValueError:
            messagebox.showwarning('⚠ ERROR', 'ID, stock y peso deben ser números.', parent=self)
            return
        if not nombre:
            messagebox.showwarning('⚠ FALTA NOMBRE', 'Ingresa el nombre.', parent=self)
            return
        self.sistema.agregar_producto(id_p, nombre, self.var_cat.get(), stock, peso)
        self._load_table()
        self._draw_tree()
        messagebox.showinfo('◈ INSERTADO', f'Producto ID {id_p} insertado en el AVL.', parent=self)

    def _buscar(self):
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('⚠ ID INVÁLIDO', 'Ingresa un número.', parent=self)
            return
        p = self.sistema.buscar_producto(id_p)
        if p:
            # Seleccionar en árbol
            self._set_selected(id_p)
            self._draw_tree()
            messagebox.showinfo('◈ ENCONTRADO',
                f'ID: {p.id_producto}\nNombre: {p.nombre}\n'
                f'Stock: {p.stock}\nCategoría: {p.categoria}\nPeso: {p.peso_kg} kg',
                parent=self)
        else:
            messagebox.showwarning('✖ NO ENCONTRADO',
                f'No existe producto con ID {id_p}.', parent=self)

    def _eliminar_por_id(self):
        """Elimina usando el ID escrito en el campo de texto."""
        try:
            id_p = int(self.entry_id.get())
        except ValueError:
            messagebox.showwarning('⚠ ID INVÁLIDO', 'Ingresa un número en el campo ID.', parent=self)
            return
        self._eliminar_nodo(id_p)

    def _eliminar_seleccionado(self):
        """Elimina el nodo actualmente seleccionado en el árbol o la tabla."""
        if self._selected is None:
            messagebox.showinfo('INFO', 'Selecciona un nodo en el árbol o en la tabla primero.', parent=self)
            return
        self._eliminar_nodo(self._selected)

    def _eliminar_nodo(self, id_p):
        """Lógica común de eliminación con confirmación."""
        p = self.sistema.buscar_producto(id_p)
        if not p:
            messagebox.showwarning('✖ NO ENCONTRADO',
                f'No existe producto con ID {id_p} en el árbol.', parent=self)
            return
        if not messagebox.askyesno(
            '✖ CONFIRMAR ELIMINACIÓN',
            f'¿Eliminar del árbol AVL?\n\n'
            f'  ID: {p.id_producto}\n'
            f'  Nombre: {p.nombre}\n'
            f'  Stock: {p.stock} uds\n\n'
            f'El árbol se rebalanceará automáticamente.',
            parent=self
        ):
            return
        self.sistema.eliminar_producto(id_p)
        # Limpiar selección si era el eliminado
        if self._selected == id_p:
            self._clear_selected()
        self._load_table()
        self._draw_tree()
        messagebox.showinfo('◈ ELIMINADO',
            f'Producto ID {id_p} eliminado.\nEl AVL se rebalanceó correctamente.',
            parent=self)
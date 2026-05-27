# Implementacion de Arbol AVL para el inventario de productos
# El ID de cada producto es la clave del arbol
# Al ser autobalanceado, las busquedas e inserciones son siempre rapidas

class NodoAVL:
    def __init__(self, producto):
        self.producto = producto          # objeto Producto
        self.clave = producto.id_producto # clave de busqueda
        self.izq = None
        self.der = None
        self.altura = 1  # altura del nodo para calcular el factor de equilibrio


class ArbolAVL:
    def __init__(self):
        self.raiz = None

    # Retorna la altura de un nodo (None = 0)
    def _altura(self, nodo):
        if nodo is None:
            return 0
        return nodo.altura

    # Factor de equilibrio: diferencia entre altura izquierda y derecha
    def _factor_equilibrio(self, nodo):
        if nodo is None:
            return 0
        return self._altura(nodo.izq) - self._altura(nodo.der)

    def _actualizar_altura(self, nodo):
        nodo.altura = 1 + max(self._altura(nodo.izq), self._altura(nodo.der))

    # Rotacion simple a la derecha
    def _rotar_derecha(self, y):
        x = y.izq
        t2 = x.der
        x.der = y
        y.izq = t2
        self._actualizar_altura(y)
        self._actualizar_altura(x)
        return x

    # Rotacion simple a la izquierda
    def _rotar_izquierda(self, x):
        y = x.der
        t2 = y.izq
        y.izq = x
        x.der = t2
        self._actualizar_altura(x)
        self._actualizar_altura(y)
        return y

    # Rebalancea el nodo si el factor de equilibrio esta fuera de [-1, 1]
    def _rebalancear(self, nodo):
        self._actualizar_altura(nodo)
        fe = self._factor_equilibrio(nodo)

        # Caso izquierda-izquierda
        if fe > 1 and self._factor_equilibrio(nodo.izq) >= 0:
            return self._rotar_derecha(nodo)

        # Caso izquierda-derecha
        if fe > 1 and self._factor_equilibrio(nodo.izq) < 0:
            nodo.izq = self._rotar_izquierda(nodo.izq)
            return self._rotar_derecha(nodo)

        # Caso derecha-derecha
        if fe < -1 and self._factor_equilibrio(nodo.der) <= 0:
            return self._rotar_izquierda(nodo)

        # Caso derecha-izquierda
        if fe < -1 and self._factor_equilibrio(nodo.der) > 0:
            nodo.der = self._rotar_derecha(nodo.der)
            return self._rotar_izquierda(nodo)

        return nodo

    def _insertar(self, nodo, producto):
        if nodo is None:
            return NodoAVL(producto)
        if producto.id_producto < nodo.clave:
            nodo.izq = self._insertar(nodo.izq, producto)
        elif producto.id_producto > nodo.clave:
            nodo.der = self._insertar(nodo.der, producto)
        else:
            # ID duplicado: actualiza el producto existente
            nodo.producto = producto
            return nodo
        return self._rebalancear(nodo)

    def insertar(self, producto):
        self.raiz = self._insertar(self.raiz, producto)

    def _buscar(self, nodo, id_producto):
        if nodo is None:
            return None
        if id_producto == nodo.clave:
            return nodo.producto
        elif id_producto < nodo.clave:
            return self._buscar(nodo.izq, id_producto)
        else:
            return self._buscar(nodo.der, id_producto)

    def buscar(self, id_producto):
        return self._buscar(self.raiz, id_producto)

    def _minimo(self, nodo):
        while nodo.izq is not None:
            nodo = nodo.izq
        return nodo

    def _eliminar(self, nodo, id_producto):
        if nodo is None:
            return None
        if id_producto < nodo.clave:
            nodo.izq = self._eliminar(nodo.izq, id_producto)
        elif id_producto > nodo.clave:
            nodo.der = self._eliminar(nodo.der, id_producto)
        else:
            # Nodo encontrado
            if nodo.izq is None:
                return nodo.der
            elif nodo.der is None:
                return nodo.izq
            # Tiene dos hijos: reemplaza con el sucesor inorden
            sucesor = self._minimo(nodo.der)
            nodo.producto = sucesor.producto
            nodo.clave = sucesor.clave
            nodo.der = self._eliminar(nodo.der, sucesor.clave)
        return self._rebalancear(nodo)

    def eliminar(self, id_producto):
        self.raiz = self._eliminar(self.raiz, id_producto)

    # Recorrido inorden: retorna productos ordenados por ID
    def _inorden(self, nodo, resultado):
        if nodo is None:
            return
        self._inorden(nodo.izq, resultado)
        resultado.append(nodo.producto)
        self._inorden(nodo.der, resultado)

    def a_lista(self):
        resultado = []
        self._inorden(self.raiz, resultado)
        return resultado

    # Retorna info del arbol para visualizarlo en la GUI (BFS)
    def obtener_nodos_visualizacion(self):
        if self.raiz is None:
            return []
        nodos = []
        cola = [(self.raiz, None, 0, 0)]  # (nodo, padre_id, nivel, posicion)
        while cola:
            nodo, padre_id, nivel, pos = cola.pop(0)
            nodos.append({
                'id': nodo.clave,
                'padre': padre_id,
                'nivel': nivel,
                'pos': pos,
                'fe': self._factor_equilibrio(nodo),
                'nombre': nodo.producto.nombre
            })
            if nodo.izq:
                cola.append((nodo.izq, nodo.clave, nivel + 1, pos * 2))
            if nodo.der:
                cola.append((nodo.der, nodo.clave, nivel + 1, pos * 2 + 1))
        return nodos

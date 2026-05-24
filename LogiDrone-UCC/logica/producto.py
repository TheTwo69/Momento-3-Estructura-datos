# Clase que representa un producto en el inventario
# Es el dato que se guarda en el Arbol AVL

class Producto:
    CATEGORIAS = ['Medicamento', 'Repuesto', 'Documento', 'Herramienta']

    def __init__(self, id_producto, nombre, categoria, stock, peso_kg):
        self.id_producto = int(id_producto)
        self.nombre = nombre
        self.categoria = categoria
        self.stock = int(stock)
        self.peso_kg = float(peso_kg)

    def reducir_stock(self, cantidad=1):
        if self.stock >= cantidad:
            self.stock -= cantidad
            return True
        return False

    def __str__(self):
        return f"[{self.id_producto}] {self.nombre} - Stock: {self.stock}"

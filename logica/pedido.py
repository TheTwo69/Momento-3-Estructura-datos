# Clase que representa un pedido de entrega
# Es el dato que viaja dentro de la Cola FIFO

class Pedido:
    PRIORIDADES = ['ALTA', 'MEDIA', 'BAJA']
    TIPOS = ['Medicamento', 'Repuesto', 'Documento']

    def __init__(self, id_pedido, destino_id, destino_nombre, tipo, prioridad, peso_kg):
        self.id_pedido = id_pedido
        self.destino_id = destino_id         # ID del nodo en el grafo
        self.destino_nombre = destino_nombre
        self.tipo = tipo
        self.prioridad = prioridad
        self.peso_kg = float(peso_kg)
        self.hora_ingreso = None             # se asigna al encolar
        self.estado = 'pendiente'            # pendiente / en_camino / entregado

    def __str__(self):
        return f"Pedido {self.id_pedido} -> {self.destino_nombre} ({self.tipo}, {self.prioridad})"

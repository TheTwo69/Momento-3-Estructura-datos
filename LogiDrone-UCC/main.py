# LogiDrone-UCC — Operacion Bahia Santa Marta
# Punto de entrada de la aplicacion
# Ejecutar: python main.py

import sys
import os

# Asegura que Python encuentre los modulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logica.sistema import Sistema
from gui.ventana_principal import VentanaPrincipal


def main():
    sistema = Sistema()
    app = VentanaPrincipal(sistema)
    app.mainloop()


if __name__ == '__main__':
    main()

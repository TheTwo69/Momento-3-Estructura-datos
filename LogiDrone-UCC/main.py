# LogiDrone-UCC — Operacion Bahia Santa Marta
# Punto de entrada de la aplicacion
# Ejecutar: python main.py

import sys
import os

# ── CORRECCIÓN DE NITIDEZ EN PANTALLAS HiDPI / RETINA ────────────────────────
# Esto debe ir ANTES de importar tkinter para que surta efecto.
# En Windows activa el modo "Per Monitor DPI Aware" que evita el escalado
# borroso del sistema operativo. En macOS y Linux no hace nada dañino.
if sys.platform == 'win32':
    try:
        import ctypes
        # Valores:  0 = DPI unaware  |  1 = System DPI  |  2 = Per-Monitor DPI
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

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
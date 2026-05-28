# main.py
import os
import sys
import uvicorn

def main():
    # 1. Configurar rutas para el ejecutable
    # Cuando PyInstaller crea el ejecutable, extrae los archivos en una carpeta 
    # temporal llamada sys._MEIPASS. Si estamos en modo desarrollo, usamos la ruta normal.
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # 2. Ajustar el directorio de trabajo
    # Tu app.py busca las carpetas "static" y "templates" asumiendo que estamos
    # dentro de la carpeta "web_tactical". Así que nos movemos allí:
    web_dir = os.path.join(application_path, 'web_tactical')
    os.chdir(web_dir)

    # 3. Asegurar que Python pueda encontrar tus módulos (logica, estructuras)
    sys.path.insert(0, application_path)

    # 4. Importar y arrancar la aplicación
    from web_tactical.app import app
    print("Iniciando LogiDrone-UCC Tactical HUD...")
    print("Por favor, abre tu navegador web en: http://127.0.0.1:8000")
    
    # Ejecutamos el servidor
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
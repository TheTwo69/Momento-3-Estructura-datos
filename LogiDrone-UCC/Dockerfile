# ─────────────────────────────────────────────────────────────────────────────
# LogiDrone-UCC — Dockerfile (app web: FastAPI + Uvicorn)
# ─────────────────────────────────────────────────────────────────────────────
# Imagen base: Python 3.11 slim (pequeña, sin GUI innecesaria)
FROM python:3.11-slim

# Metadatos
LABEL maintainer="LogiDrone-UCC"
LABEL description="Sistema táctico de gestión de drones — web_tactical"
LABEL version="4.0"

# ── Variables de entorno ──────────────────────────────────────────────────────
# Evita que Python cree archivos .pyc y que bufferice stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Puerto por defecto de Uvicorn (puede sobreescribirse con -e PORT=XXXX)
    PORT=8000

# ── Directorio de trabajo dentro del contenedor ───────────────────────────────
WORKDIR /app

# ── Copiar SOLO lo necesario para instalar dependencias primero ───────────────
# (aprovecha la caché de Docker: si requirements.txt no cambia, no reinstala)
COPY web_tactical/requirements.txt ./requirements.txt

# ── Instalar dependencias del sistema que algunas libs necesitan ──────────────
# build-essential → para compilar extensiones C de algunas librerías
# libgdal-dev     → necesario si geopandas quiere GDAL nativo
#  * Si no usas geopandas de verdad, la línea de gdal se puede eliminar
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Instalar dependencias Python ──────────────────────────────────────────────
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copiar el código fuente completo del proyecto ────────────────────────────
# Estructura dentro del contenedor:
#   /app/
#     web_tactical/   ← app FastAPI
#     logica/         ← lógica del sistema
#     estructuras/    ← estructuras de datos (AVL, Cola, etc.)
COPY web_tactical/ ./web_tactical/
COPY logica/       ./logica/
COPY estructuras/  ./estructuras/

# ── Exponer el puerto ─────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check: verifica que la API responda ────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# ── Comando de inicio ─────────────────────────────────────────────────────────
# --host 0.0.0.0   → escucha en todas las interfaces (obligatorio en Docker)
# --port $PORT     → usa la variable de entorno
# --reload         → recarga automática al cambiar código (quitar en producción)
CMD ["sh", "-c", "cd /app/web_tactical && uvicorn app:app --host 0.0.0.0 --port ${PORT} --reload"]

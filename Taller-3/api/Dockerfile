# Imagen base Python 3.11 slim
FROM python:3.11-slim

# Metadata
LABEL maintainer="DevOps Team - Taller 3"
LABEL description="API FastAPI para predicción de especies de pingüinos"
LABEL version="1.0"

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
# gcc y g++ son necesarios para compilar algunas librerías de Python
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requisitos primero (mejor caché de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar archivos de la API
COPY api.py .
COPY api_tf.py .
COPY __init__.py .

# Crear directorios para modelos (serán montados como volúmenes)
RUN mkdir -p /app/models /app/models_tf

# Variable de entorno para Python sin buffer (logs en tiempo real)
ENV PYTHONUNBUFFERED=1

# Configurar variables de entorno por defecto
ENV MODEL_PATH=/app/models
ENV MODEL_TF_PATH=/app/models_tf
ENV PORT=8000

# Usuario no root por seguridad
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser && \
    chown -R apiuser:apiuser /app

# Cambiar al usuario no root
USER apiuser

# Exponer puerto de la API
EXPOSE 8000

# Healthcheck para verificar que la API está funcionando
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Comando por defecto: ejecutar api.py con uvicorn
# Nota: Usar --host 0.0.0.0 es importante para que sea accesible desde fuera del contenedor
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Comando alternativo para ejecutar api_tf.py (comentado)
# CMD ["uvicorn", "api_tf:app", "--host", "0.0.0.0", "--port", "8889", "--reload"]
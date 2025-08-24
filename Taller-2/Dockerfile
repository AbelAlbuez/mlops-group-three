FROM python:3.9-slim

WORKDIR /app

# Instalar uv para gestionar dependencias más rápido
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copiar requirements e instalar dependencias con uv en el entorno del sistema
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear directorio para modelos
RUN mkdir -p /app/models

# Exponer puerto para la API
EXPOSE 8000

# Comando por defecto para la API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
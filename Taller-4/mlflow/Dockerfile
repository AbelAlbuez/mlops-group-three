FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Instalar MLflow y dependencias
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    mlflow>=2.8.0 \
    pymysql>=1.1.0 \
    cryptography>=41.0.0 \
    boto3>=1.28.0 \
    psutil

# Variable de entorno
ENV PYTHONUNBUFFERED=1

# Exponer puerto
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# El comando se especifica en docker-compose
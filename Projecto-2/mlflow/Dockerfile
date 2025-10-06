FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir \
    mlflow==2.9.0 \
    pymysql==1.1.0 \
    boto3==1.34.0 \
    requests==2.31.0

# Crear script de inicio
COPY start_mlflow.sh /start_mlflow.sh
RUN chmod +x /start_mlflow.sh

EXPOSE 5000

CMD ["/start_mlflow.sh"]

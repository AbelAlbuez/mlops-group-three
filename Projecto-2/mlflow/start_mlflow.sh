#!/bin/bash

# Configurar variables de entorno
export MLFLOW_BACKEND_STORE_URI=mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow
export MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow/
export MLFLOW_S3_ENDPOINT_URL=http://minio:9000
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin

# Esperar a que la base de datos esté lista
echo "Esperando a que la base de datos esté lista..."
sleep 10

# Iniciar MLflow con configuración específica
echo "Iniciando MLflow server..."
exec mlflow server \
  --backend-store-uri mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow \
  --default-artifact-root s3://mlflow/ \
  --host 0.0.0.0 \
  --port 5000 \
  --workers 1

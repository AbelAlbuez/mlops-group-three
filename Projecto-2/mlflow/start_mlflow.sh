#!/bin/bash

# Configurar variables de entorno
export MLFLOW_BACKEND_STORE_URI=mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow
export MLFLOW_DEFAULT_ARTIFACT_ROOT=/mlflow/artifacts

# Esperar a que la base de datos esté lista
echo "Esperando a que la base de datos esté lista..."
sleep 10

# Crear directorio de artefactos si no existe
mkdir -p /mlflow/artifacts

# Iniciar MLflow con configuración específica
echo "Iniciando MLflow server..."
exec mlflow server \
  --backend-store-uri mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow \
  --default-artifact-root /mlflow/artifacts \
  --host 0.0.0.0 \
  --port 5000

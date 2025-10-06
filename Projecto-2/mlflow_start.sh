#!/bin/bash

# Instalar dependencias
pip install mlflow==2.9.0 pymysql boto3

# Configurar variables de entorno
export MLFLOW_BACKEND_STORE_URI=mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow
export MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow/

# Iniciar MLflow con configuración específica
exec mlflow server \
  --backend-store-uri mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow \
  --default-artifact-root s3://mlflow/ \
  --host 0.0.0.0 \
  --port 5000

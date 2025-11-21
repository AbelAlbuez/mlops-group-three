#!/bin/bash

NAMESPACE="mlops"
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

echo "Deteniendo forwards anteriores relacionados con mlops-stack..."
pkill -f "kubectl port-forward.*mlops-stack" 2>/dev/null

echo "Iniciando nuevos port-forwards…"


#############################
# MINIO (API: 9000, Console: 9001)
# Local: 8015 -> 9000, 8016 -> 9001
#############################
nohup kubectl port-forward -n $NAMESPACE --address 0.0.0.0 \
  svc/mlops-stack-mlops-stack-minio 8015:9000 8016:9001 \
  > "$LOG_DIR/minio-forward.log" 2>&1 &

MINIO_PID=$!


#############################
# AIRFLOW WEBSERVER (8080)
# Local: 8017 -> 8080
#############################
nohup kubectl port-forward -n $NAMESPACE --address 0.0.0.0 \
  svc/mlops-stack-mlops-stack-airflow-webserver 8017:8080 \
  > "$LOG_DIR/airflow-web-forward.log" 2>&1 &

AIRFLOW_WEB_PID=$!


#############################
# MLFLOW (5000)
# Local: 8018 -> 5000
#############################
nohup kubectl port-forward -n $NAMESPACE --address 0.0.0.0 \
  svc/mlops-stack-mlops-stack-mlflow 8018:5000 \
  > "$LOG_DIR/mlflow-forward.log" 2>&1 &

MLFLOW_PID=$!


#############################
# Guardar PIDs
#############################
echo "$MINIO_PID" > "$LOG_DIR/minio.pid"
echo "$AIRFLOW_WEB_PID" > "$LOG_DIR/airflow-web.pid"
echo "$MLFLOW_PID" > "$LOG_DIR/mlflow.pid"


echo ""
echo "=============================================="
echo " Port-forward iniciado correctamente:"
echo "=============================================="
echo "  • MinIO API     → http://localhost:8015   (→ svc/minio:9000, PID: $MINIO_PID)"
echo "  • MinIO Console → http://localhost:8016   (→ svc/minio:9001)"
echo "  • Airflow Web   → http://localhost:8017   (→ svc/airflow-web:8080, PID: $AIRFLOW_WEB_PID)"
echo "  • MLflow        → http://localhost:8018   (→ svc/mlflow:5000, PID: $MLFLOW_PID)"
echo ""
echo "Logs disponibles en: $LOG_DIR/"
echo ""
echo "Para detener todos los forwards:"
echo "  pkill -f 'kubectl port-forward'"
echo ""
echo "O solo estos:"
echo "  kill \$(cat $LOG_DIR/minio.pid) \$(cat $LOG_DIR/airflow-web.pid) \$(cat $LOG_DIR/mlflow.pid)"
echo "=============================================="
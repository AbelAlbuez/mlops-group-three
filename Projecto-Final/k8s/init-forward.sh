#!/bin/bash

# Port forwarding para API, Locust y Streamlit
# Ejecutar en background para mantener los forwards activos

# Crear directorio de logs si no existe
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Detener forwards existentes si los hay
pkill -f 'kubectl port-forward.*api' 2>/dev/null
pkill -f 'kubectl port-forward.*locust' 2>/dev/null
pkill -f 'kubectl port-forward.*streamlit' 2>/dev/null

# Forward API (puerto 8000 -> 8001) en background
nohup kubectl port-forward -n apps --address 0.0.0.0 svc/api 8001:8000 > "$LOG_DIR/api-forward.log" 2>&1 &
API_PID=$!

# Forward Locust (puerto 8089 -> 8002) en background
nohup kubectl port-forward -n apps --address 0.0.0.0 svc/locust 8002:8089 > "$LOG_DIR/locust-forward.log" 2>&1 &
LOCUST_PID=$!

# Forward Streamlit (puerto 8501 -> 8003) en background
nohup kubectl port-forward -n apps --address 0.0.0.0 svc/streamlit 8003:8501 > "$LOG_DIR/streamlit-forward.log" 2>&1 &
STREAMLIT_PID=$!

# Guardar PIDs para referencia
echo "$API_PID" > "$LOG_DIR/api-forward.pid"
echo "$LOCUST_PID" > "$LOG_DIR/locust-forward.pid"
echo "$STREAMLIT_PID" > "$LOG_DIR/streamlit-forward.pid"

echo "Port forwarding iniciado en background:"
echo "  - API: http://localhost:8001 (PID: $API_PID)"
echo "  - Locust: http://localhost:8002 (PID: $LOCUST_PID)"
echo "  - Streamlit: http://localhost:8003 (PID: $STREAMLIT_PID)"
echo ""
echo "Logs guardados en: $LOG_DIR/"
echo ""
echo "Para detener los forwards, ejecuta:"
echo "  pkill -f 'kubectl port-forward'"
echo "  o"
echo "  kill \$(cat $LOG_DIR/api-forward.pid) \$(cat $LOG_DIR/locust-forward.pid) \$(cat $LOG_DIR/streamlit-forward.pid)"
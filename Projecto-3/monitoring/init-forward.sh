#!/bin/bash
# Crear directorio de logs si no existe
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Detener forwards existentes si los hay
pkill -f 'kubectl port-forward.*grafana' 2>/dev/null
pkill -f 'kubectl port-forward.*prometheus-server' 2>/dev/null

# Forward Grafana (puerto 80 -> 3010) en background
nohup kubectl port-forward -n monitoring  --address 0.0.0.0 svc/grafana 3010:80 > "$LOG_DIR/grafana-forward.log" 2>&1 &
GRAFANA_PID=$!

# Forward Prometheus (puerto 80 -> 3011) en background
nohup kubectl port-forward -n monitoring --address 0.0.0.0 svc/prometheus-server 3011:80 > "$LOG_DIR/prometheus-forward.log" 2>&1 &
PROMETHEUS_PID=$!

# Guardar PIDs para referencia
echo "$GRAFANA_PID" > "$LOG_DIR/grafana-forward.pid"
echo "$PROMETHEUS_PID" > "$LOG_DIR/prometheus-forward.pid"

echo "Port forwarding iniciado en background:"
echo "  - Grafana: http://localhost:3010 (PID: $GRAFANA_PID)"
echo "  - Prometheus: http://localhost:3011 (PID: $PROMETHEUS_PID)"
echo ""
echo "Logs guardados en: $LOG_DIR/"
echo ""
echo "Para detener los forwards, ejecuta:"
echo "  pkill -f 'kubectl port-forward'"
echo "  o"
echo "  kill \$(cat $LOG_DIR/grafana-forward.pid) \$(cat $LOG_DIR/prometheus-forward.pid)"
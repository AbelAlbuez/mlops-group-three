#!/bin/bash
# Ejecuta suite completa de pruebas con diferentes configuraciones

set -e

CONFIGS=(
    "0.25 256M 500"
    "0.5 512M 2000"
    "1.0 1G 5000"
    "2.0 2G 10000"
)

RESULTS_DIR="load_test_results"
mkdir -p "$RESULTS_DIR"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando suite completa de pruebas...${NC}"
echo "   Total de configuraciones: ${#CONFIGS[@]}"
echo ""

for config in "${CONFIGS[@]}"; do
    read -r cpu mem users <<< "$config"
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📊 Prueba: $cpu CPU, $mem RAM, $users usuarios${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Configurar recursos
    ./set_resources.sh $cpu $mem
    
    # Ejecutar prueba
    docker run --rm --network taller-5_locust-network \
        -v $(pwd)/locustfile.py:/locustfile.py:ro \
        locustio/locust:latest \
        -f /locustfile.py \
        --host=http://inference-api:8000 \
        --users=$users \
        --spawn-rate=100 \
        --run-time=5m \
        --headless \
        --csv="$RESULTS_DIR/test_${cpu}cpu_${mem}" \
        --html="$RESULTS_DIR/test_${cpu}cpu_${mem}.html"
    
    echo -e "${GREEN}✅ Prueba completada${NC}"
    echo ""
    sleep 30
done

# Generar reporte consolidado
cat > "$RESULTS_DIR/REPORTE.md" << EOF
# Reporte de Pruebas de Carga

**Fecha:** $(date)

## Configuraciones Probadas

| CPU | RAM | Usuarios | Archivo CSV | Archivo HTML |
|-----|-----|----------|-------------|--------------|
EOF

for config in "${CONFIGS[@]}"; do
    read -r cpu mem users <<< "$config"
    echo "| $cpu | $mem | $users | [test_${cpu}cpu_${mem}_stats.csv](test_${cpu}cpu_${mem}_stats.csv) | [test_${cpu}cpu_${mem}.html](test_${cpu}cpu_${mem}.html) |" >> "$RESULTS_DIR/REPORTE.md"
done

echo ""
echo -e "${GREEN}🎉 Suite completa de pruebas finalizada!${NC}"
echo -e "${BLUE}📁 Resultados en: $RESULTS_DIR/${NC}"
echo -e "${BLUE}📄 Reporte: $RESULTS_DIR/REPORTE.md${NC}"

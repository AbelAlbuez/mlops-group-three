#!/bin/bash
# Script simplificado para ejecutar pruebas de carga con Locust

set -e

# Configuraciones predefinidas: CPU MEM USERS RATE TIME
get_config() {
    case $1 in
        quick) echo "0.5 512M 500 50 5m" ;;
        medium) echo "1.0 1G 2000 100 10m" ;;
        load) echo "2.0 2G 5000 200 15m" ;;
        stress) echo "4.0 4G 10000 500 20m" ;;
        *) echo "" ;;
    esac
}

# Directorio de resultados
RESULTS_DIR="load_test_results"
mkdir -p "$RESULTS_DIR"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Función para ejecutar prueba
run_test() {
    local name=$1
    local config=$(get_config "$name")
    
    if [ -z "$config" ]; then
        error "Configuración '$name' no encontrada"
        return 1
    fi
    
    # Parsear valores: cpu mem users rate time
    read -r cpu mem users rate time <<< "$config"
    
    log "Iniciando prueba: $name"
    log "Configuración: $cpu CPU, $mem RAM, $users usuarios, $time"
    
    # Actualizar variables de entorno
    export API_CPU_LIMIT="$cpu"
    export API_MEMORY_LIMIT="$mem"
    
    # Levantar servicios
    log "Iniciando servicios..."
    docker compose -f docker-compose.locust-official.yml up -d
    
    # Esperar 30 segundos
    log "Esperando que los servicios estén listos..."
    sleep 30
    
    # Verificar que la API esté funcionando
    if ! curl -s http://localhost:8000/health >/dev/null; then
        error "API no está respondiendo"
        return 1
    fi
    
    # Ejecutar Locust headless
    log "Ejecutando Locust..."
    local test_name="test_${name}_${cpu}cpu_${mem}mem_${time}"
    
    docker compose -f docker-compose.locust-official.yml exec -T locust-master locust \
        --locustfile=/mnt/locust/locustfile.py \
        --host=http://inference-api:8000 \
        --users="$users" \
        --spawn-rate="$rate" \
        --run-time="$time" \
        --csv="$test_name" \
        --html="$test_name.html" \
        --headless
    
    # Copiar resultados
    log "Copiando resultados..."
    docker cp locust-master-minimal:/home/locust/${test_name}_stats.csv "${RESULTS_DIR}/" 2>/dev/null || true
    docker cp locust-master-minimal:/home/locust/${test_name}.html "${RESULTS_DIR}/" 2>/dev/null || true
    
    log "✅ Prueba '$name' completada"
    log "📁 Resultados en: ${RESULTS_DIR}/"
}

# Mostrar ayuda
show_help() {
    echo "Uso: $0 [quick|medium|load|stress]"
    echo ""
    echo "Configuraciones disponibles:"
    echo "  quick   - 0.5 CPU, 512M RAM, 500 usuarios, 5min"
    echo "  medium  - 1.0 CPU, 1G RAM, 2000 usuarios, 10min"
    echo "  load    - 2.0 CPU, 2G RAM, 5000 usuarios, 15min"
    echo "  stress  - 4.0 CPU, 4G RAM, 10000 usuarios, 20min"
    echo ""
    echo "Ejemplo: $0 quick"
}

# Main
case ${1:-quick} in
    quick|medium|load|stress)
        run_test $1
        ;;
    -h|--help|help)
        show_help
        ;;
    *)
        error "Opción inválida: $1"
        show_help
        exit 1
        ;;
esac
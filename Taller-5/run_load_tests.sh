#!/bin/bash

# Script para ejecutar pruebas de carga con Locust
# Configuraciones: 0.25/256M, 0.5/512M, 1.0/1G, 2.0/2G
# Usuarios: 500, 2000, 5000, 10000
# Resultados en: load_test_results/

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuraciones de prueba
CPU_CONFIGS=("0.25" "0.5" "1.0" "2.0")
MEMORY_CONFIGS=("256M" "512M" "1G" "2G")
USER_CONFIGS=(500 2000 5000 10000)
SPAWN_RATES=(50 100 200 500)
RUN_TIMES=("5m" "10m" "15m" "20m")

# Directorio base
BASE_DIR="/Users/abelalbuez/Documents/Maestria /Segundo Semestre/MLOPS/mlops-group-three/Taller-5"
RESULTS_DIR="${BASE_DIR}/load_test_results"
COMPOSE_FILE="${BASE_DIR}/docker-compose.locust.yml"

# Crear directorio de resultados si no existe
mkdir -p "${RESULTS_DIR}"

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}Script de Pruebas de Carga con Locust${NC}"
    echo ""
    echo "Uso: $0 [OPCIONES]"
    echo ""
    echo "Opciones:"
    echo "  -h, --help              Mostrar esta ayuda"
    echo "  -q, --quick             Ejecutar solo pruebas rápidas (500 usuarios)"
    echo "  -m, --medium            Ejecutar pruebas medias (2000 usuarios)"
    echo "  -f, --full              Ejecutar todas las pruebas (500, 2000, 5000, 10000)"
    echo "  -c, --config CONFIG     Ejecutar configuración específica (0.25/256M, 0.5/512M, 1.0/1G, 2.0/2G)"
    echo "  -u, --users USERS       Número de usuarios para la prueba"
    echo "  -t, --time TIME         Tiempo de ejecución (ej: 5m, 10m)"
    echo "  --clean                 Limpiar contenedores antes de empezar"
    echo "  --no-cleanup            No limpiar contenedores al finalizar"
    echo ""
    echo "Ejemplos:"
    echo "  $0 --quick                    # Pruebas rápidas con 500 usuarios"
    echo "  $0 --config 0.5/512M          # Configuración específica"
    echo "  $0 --users 1000 --time 10m    # 1000 usuarios por 10 minutos"
    echo ""
}

# Función para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Función para error
error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Función para warning
warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Función para limpiar contenedores
cleanup_containers() {
    log "Limpiando contenedores existentes..."
    docker compose -f "${COMPOSE_FILE}" down -v --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
}

# Función para verificar que los servicios estén listos
wait_for_services() {
    local max_attempts=60
    local attempt=0
    
    log "Esperando que los servicios estén listos..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log "Servicios listos!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 5
    done
    
    error "Los servicios no estuvieron listos a tiempo"
    return 1
}

# Función para ejecutar una prueba específica
run_test() {
    local cpu_limit="$1"
    local memory_limit="$2"
    local users="$3"
    local spawn_rate="$4"
    local run_time="$5"
    
    local test_name="test_${users}users_${cpu_limit}cpu_${memory_limit}mem_${run_time}"
    local results_file="${RESULTS_DIR}/${test_name}.csv"
    local html_file="${RESULTS_DIR}/${test_name}.html"
    
    log "Iniciando prueba: ${test_name}"
    log "Configuración: ${users} usuarios, ${cpu_limit} CPU, ${memory_limit} RAM, ${run_time}"
    
    # Configurar variables de entorno
    export API_CPU_LIMIT="${cpu_limit}"
    export API_MEMORY_LIMIT="${memory_limit}"
    export LOCUST_USERS="${users}"
    export LOCUST_SPAWN_RATE="${spawn_rate}"
    export LOCUST_RUN_TIME="${run_time}"
    
    # Iniciar servicios
    log "Iniciando servicios con configuración de recursos..."
    docker compose -f "${COMPOSE_FILE}" up -d
    
    # Esperar a que estén listos
    if ! wait_for_services; then
        error "No se pudieron iniciar los servicios"
        return 1
    fi
    
    # Ejecutar Locust
    log "Ejecutando Locust..."
    docker compose -f "${COMPOSE_FILE}" exec -T locust-master locust \
        --locustfile=/mnt/locust/locustfile.py \
        --host=http://inference-api:8000 \
        --users="${users}" \
        --spawn-rate="${spawn_rate}" \
        --run-time="${run_time}" \
        --csv="${test_name}" \
        --html="${test_name}.html" \
        --headless
    
    # Copiar resultados
    docker cp locust-master:/mnt/locust/${test_name}.csv "${results_file}" 2>/dev/null || true
    docker cp locust-master:/mnt/locust/${test_name}.html "${html_file}" 2>/dev/null || true
    
    log "Prueba completada: ${test_name}"
    log "Resultados guardados en: ${results_file}"
    
    # Mostrar resumen
    if [ -f "${results_file}" ]; then
        echo ""
        echo "=== RESUMEN DE LA PRUEBA ==="
        echo "Archivo: ${results_file}"
        echo "Usuarios: ${users}"
        echo "CPU: ${cpu_limit}"
        echo "RAM: ${memory_limit}"
        echo "Tiempo: ${run_time}"
        echo ""
    fi
}

# Función para generar reporte consolidado
generate_report() {
    local report_file="${RESULTS_DIR}/consolidated_report.md"
    
    log "Generando reporte consolidado..."
    
    cat > "${report_file}" << EOF
# Reporte Consolidado de Pruebas de Carga

**Fecha:** $(date)
**Directorio:** ${RESULTS_DIR}

## Configuraciones Probadas

| CPU | RAM | Usuarios | Tiempo | Archivo CSV | Archivo HTML |
|-----|-----|----------|--------|-------------|--------------|
EOF

    # Buscar archivos de resultados
    for csv_file in "${RESULTS_DIR}"/*.csv; do
        if [ -f "${csv_file}" ]; then
            local basename=$(basename "${csv_file}" .csv)
            local html_file="${RESULTS_DIR}/${basename}.html"
            local html_link=""
            
            if [ -f "${html_file}" ]; then
                html_link="[Ver HTML](${basename}.html)"
            fi
            
            echo "| - | - | - | - | [${basename}.csv](${basename}.csv) | ${html_link} |" >> "${report_file}"
        fi
    done
    
    cat >> "${report_file}" << EOF

## Instrucciones

1. **Ver resultados CSV:** Abre los archivos .csv en Excel o similar
2. **Ver reportes HTML:** Abre los archivos .html en un navegador
3. **Comparar configuraciones:** Usa el archivo consolidado para comparar

## Métricas Importantes

- **RPS (Requests Per Second):** Peticiones por segundo
- **Response Time:** Tiempo de respuesta promedio
- **95th Percentile:** 95% de las peticiones responden en este tiempo o menos
- **Error Rate:** Porcentaje de peticiones fallidas

## Recomendaciones

- **CPU 0.25-0.5:** Para desarrollo y pruebas básicas
- **CPU 1.0-2.0:** Para producción con carga media-alta
- **RAM 512M-1G:** Suficiente para la mayoría de casos
- **RAM 2G+:** Para cargas muy altas o modelos complejos

EOF

    log "Reporte consolidado generado: ${report_file}"
}

# Variables por defecto
QUICK_MODE=false
MEDIUM_MODE=false
FULL_MODE=false
CLEAN_BEFORE=false
CLEANUP_AFTER=true
SPECIFIC_CONFIG=""
SPECIFIC_USERS=""
SPECIFIC_TIME=""

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        -m|--medium)
            MEDIUM_MODE=true
            shift
            ;;
        -f|--full)
            FULL_MODE=true
            shift
            ;;
        -c|--config)
            SPECIFIC_CONFIG="$2"
            shift 2
            ;;
        -u|--users)
            SPECIFIC_USERS="$2"
            shift 2
            ;;
        -t|--time)
            SPECIFIC_TIME="$2"
            shift 2
            ;;
        --clean)
            CLEAN_BEFORE=true
            shift
            ;;
        --no-cleanup)
            CLEANUP_AFTER=false
            shift
            ;;
        *)
            error "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validar argumentos
if [ "$QUICK_MODE" = false ] && [ "$MEDIUM_MODE" = false ] && [ "$FULL_MODE" = false ] && [ -z "$SPECIFIC_CONFIG" ] && [ -z "$SPECIFIC_USERS" ]; then
    error "Debe especificar un modo de ejecución"
    show_help
    exit 1
fi

# Verificar que Docker esté disponible
if ! command -v docker &> /dev/null; then
    error "Docker no está instalado o no está en el PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose no está instalado o no está en el PATH"
    exit 1
fi

# Limpiar si se solicita
if [ "$CLEAN_BEFORE" = true ]; then
    cleanup_containers
fi

# Ejecutar pruebas según el modo seleccionado
if [ "$QUICK_MODE" = true ]; then
    log "Ejecutando pruebas rápidas..."
    run_test "0.5" "512M" "500" "50" "5m"
    
elif [ "$MEDIUM_MODE" = true ]; then
    log "Ejecutando pruebas medias..."
    run_test "0.5" "512M" "2000" "100" "10m"
    run_test "1.0" "1G" "2000" "100" "10m"
    
elif [ "$FULL_MODE" = true ]; then
    log "Ejecutando todas las pruebas..."
    
    # Pruebas con diferentes configuraciones de recursos
    for i in "${!CPU_CONFIGS[@]}"; do
        run_test "${CPU_CONFIGS[$i]}" "${MEMORY_CONFIGS[$i]}" "2000" "100" "10m"
    done
    
    # Pruebas con diferentes números de usuarios
    for users in "${USER_CONFIGS[@]}"; do
        run_test "1.0" "1G" "${users}" "200" "15m"
    done
    
elif [ -n "$SPECIFIC_CONFIG" ]; then
    # Parsear configuración específica (formato: CPU/RAM)
    IFS='/' read -r cpu ram <<< "$SPECIFIC_CONFIG"
    if [ -z "$cpu" ] || [ -z "$ram" ]; then
        error "Formato de configuración inválido. Use: CPU/RAM (ej: 0.5/512M)"
        exit 1
    fi
    
    local users="${SPECIFIC_USERS:-2000}"
    local time="${SPECIFIC_TIME:-10m}"
    
    run_test "$cpu" "$ram" "$users" "100" "$time"
    
elif [ -n "$SPECIFIC_USERS" ]; then
    local time="${SPECIFIC_TIME:-10m}"
    run_test "1.0" "1G" "$SPECIFIC_USERS" "200" "$time"
fi

# Generar reporte consolidado
generate_report

# Limpiar si se solicita
if [ "$CLEANUP_AFTER" = true ]; then
    log "Limpiando contenedores..."
    cleanup_containers
fi

log "¡Pruebas de carga completadas!"
log "Resultados disponibles en: ${RESULTS_DIR}"
log "Reporte consolidado: ${RESULTS_DIR}/consolidated_report.md"

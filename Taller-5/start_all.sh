#!/bin/bash
# Script para iniciar todos los servicios de Locust
# Uso: ./start_all.sh [quick|medium|load|stress]

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración por defecto
DEFAULT_CONFIG="medium"
COMPOSE_FILE="docker-compose.locust-official.yml"
RESULTS_DIR="load_test_results"

# Función para mostrar mensajes
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Función para mostrar banner
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      🚀 TALLER 5 - PRUEBAS DE CARGA CON LOCUST 🚀        ║
║                                                           ║
║           Inicializador Automático de Servicios          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Función para obtener configuración
get_config() {
    case $1 in
        quick)
            echo "0.5 512M 500 50 5m"
            ;;
        medium)
            echo "1.0 1G 2000 100 10m"
            ;;
        load)
            echo "2.0 2G 5000 200 15m"
            ;;
        stress)
            echo "4.0 4G 10000 500 20m"
            ;;
        *)
            echo "1.0 1G 2000 100 10m"  # Default medium
            ;;
    esac
}

# Función para mostrar ayuda
show_help() {
    cat << EOF
${BLUE}Uso:${NC} $0 [CONFIGURACION] [OPCIONES]

${BLUE}Configuraciones disponibles:${NC}
  quick      - 0.5 CPU, 512M RAM, 500 usuarios, 5 minutos
  medium     - 1.0 CPU, 1G RAM, 2000 usuarios, 10 minutos (default)
  load       - 2.0 CPU, 2G RAM, 5000 usuarios, 15 minutos
  stress     - 4.0 CPU, 4G RAM, 10000 usuarios, 20 minutos

${BLUE}Opciones:${NC}
  -h, --help          Mostrar esta ayuda
  -s, --status        Ver estado de los servicios
  -l, --logs          Ver logs en tiempo real
  -c, --clean         Limpiar contenedores antes de iniciar

${BLUE}Ejemplos:${NC}
  $0                  # Iniciar con configuración medium
  $0 quick            # Iniciar con configuración quick
  $0 load             # Iniciar con configuración load
  $0 --status         # Ver estado de servicios
  $0 --clean          # Limpiar y reiniciar

${BLUE}URLs de acceso:${NC}
  Locust UI:  http://localhost:8089  (👈 Configura tu prueba aquí)
  API:        http://localhost:8000
  API Docs:   http://localhost:8000/docs
  Health:     http://localhost:8000/health

${BLUE}Nota:${NC}
  Este script SOLO inicia los servicios.
  Configura y ejecuta las pruebas manualmente desde la UI de Locust.

EOF
}

# Función para verificar requisitos
check_requirements() {
    log "Verificando requisitos..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado"
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose no está instalado o no es la versión 2.x"
        exit 1
    fi
    
    # Verificar archivo compose
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Archivo $COMPOSE_FILE no encontrado"
        exit 1
    fi
    
    # Verificar locustfile
    if [ ! -f "locustfile.py" ]; then
        error "Archivo locustfile.py no encontrado"
        exit 1
    fi
    
    info "✅ Todos los requisitos cumplidos"
}

# Función para verificar puertos
check_ports() {
    log "Verificando puertos disponibles..."
    
    local ports=(8089 8000)
    local ports_in_use=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            ports_in_use+=($port)
        fi
    done
    
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        warning "Los siguientes puertos están en uso: ${ports_in_use[*]}"
        warning "Los servicios existentes serán detenidos"
        read -p "¿Continuar? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        info "✅ Puertos disponibles"
    fi
}

# Función para crear directorio de resultados
setup_results_dir() {
    mkdir -p "$RESULTS_DIR"
    log "Directorio de resultados: $RESULTS_DIR"
}

# Función para configurar recursos
setup_resources() {
    local config=${1:-$DEFAULT_CONFIG}
    local config_values=$(get_config "$config")
    read -r cpu mem users rate time <<< "$config_values"
    
    info "Configuración seleccionada: $config"
    echo "   CPU:        $cpu"
    echo "   RAM:        $mem"
    echo "   Usuarios:   $users"
    echo "   Spawn rate: $rate/s"
    echo "   Duración:   $time"
    echo ""
    
    # Exportar variables de entorno
    export API_CPU_LIMIT="$cpu"
    export API_MEMORY_LIMIT="$mem"
    export LOCUST_USERS="$users"
    export LOCUST_SPAWN_RATE="$rate"
    export LOCUST_RUN_TIME="$time"
    
    # Guardar configuración actual
    echo "$cpu $mem $users $rate $time" > .current_config
}

# Función para iniciar servicios
start_services() {
    log "Iniciando servicios Docker..."
    
    # Detener servicios existentes si existen
    docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    
    # Iniciar servicios
    docker compose -f "$COMPOSE_FILE" up -d
    
    info "✅ Servicios iniciados"
}

# Función para esperar que los servicios estén listos
wait_for_services() {
    log "Esperando que los servicios estén listos..."
    
    local max_attempts=60
    local attempt=0
    
    # Esperar API
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            info "✅ API lista"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    echo ""
    
    if [ $attempt -eq $max_attempts ]; then
        error "Timeout esperando API"
        exit 1
    fi
    
    # Esperar Locust
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8089 > /dev/null 2>&1; then
            info "✅ Locust listo"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    echo ""
    
    if [ $attempt -eq $max_attempts ]; then
        error "Timeout esperando Locust"
        exit 1
    fi
}

# Función para mostrar estado
show_status() {
    log "Estado de los servicios:"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    
    # Health checks
    info "Health checks:"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "   API:     ${GREEN}✅ OK${NC}"
    else
        echo -e "   API:     ${RED}❌ DOWN${NC}"
    fi
    
    if curl -s http://localhost:8089 > /dev/null 2>&1; then
        echo -e "   Locust:  ${GREEN}✅ OK${NC}"
    else
        echo -e "   Locust:  ${RED}❌ DOWN${NC}"
    fi
    echo ""
}

# Función para mostrar logs
show_logs() {
    log "Mostrando logs (Ctrl+C para salir)..."
    docker compose -f "$COMPOSE_FILE" logs -f
}

# Función para ejecutar prueba headless
run_headless_test() {
    if [ ! -f .current_config ]; then
        error "No hay configuración activa. Ejecuta start_all.sh primero."
        exit 1
    fi
    
    read -r cpu mem users rate time < .current_config
    
    log "Ejecutando prueba headless..."
    info "Configuración: $cpu CPU, $mem RAM, $users usuarios, $time"
    
    local test_name="test_${users}users_${cpu}cpu_${mem}mem_${time}"
    
    # Ejecutar Locust en modo headless
    docker compose -f "$COMPOSE_FILE" exec -T locust-master locust \
        --locustfile=/mnt/locust/locustfile.py \
        --host=http://inference-api:8000 \
        --users="$users" \
        --spawn-rate="$rate" \
        --run-time="$time" \
        --csv="/tmp/$test_name" \
        --html="/tmp/$test_name.html" \
        --headless
    
    # Copiar resultados
    log "Copiando resultados..."
    docker cp locust-master-official:/tmp/${test_name}_stats.csv "${RESULTS_DIR}/" 2>/dev/null || true
    docker cp locust-master-official:/tmp/${test_name}.html "${RESULTS_DIR}/" 2>/dev/null || true
    
    info "✅ Prueba completada"
    info "📁 Resultados en: $RESULTS_DIR/"
}

# Función para limpiar servicios
clean_services() {
    log "Limpiando servicios..."
    docker compose -f "$COMPOSE_FILE" down -v
    info "✅ Limpieza completada"
}

# Función principal
main() {
    local config="$DEFAULT_CONFIG"
    local show_status_only=false
    local show_logs_only=false
    local clean_first=false
    
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--status)
                show_status_only=true
                shift
                ;;
            -l|--logs)
                show_logs_only=true
                shift
                ;;
            -c|--clean)
                clean_first=true
                shift
                ;;
            quick|medium|load|stress)
                config="$1"
                shift
                ;;
            *)
                error "Opción desconocida: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Mostrar banner
    show_banner
    
    # Si solo quiere ver status
    if [ "$show_status_only" = true ]; then
        show_status
        exit 0
    fi
    
    # Si solo quiere ver logs
    if [ "$show_logs_only" = true ]; then
        show_logs
        exit 0
    fi
    
    # Verificar requisitos
    check_requirements
    
    # Verificar puertos
    check_ports
    
    # Limpiar si se solicita
    if [ "$clean_first" = true ]; then
        clean_services
    fi
    
    # Crear directorio de resultados
    setup_results_dir
    
    # Configurar recursos
    setup_resources "$config"
    
    # Iniciar servicios
    start_services
    
    # Esperar a que estén listos
    wait_for_services
    
    # Mostrar estado
    show_status
    
    # Mostrar URLs
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Servicios iniciados correctamente${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}URLs de acceso:${NC}"
    echo -e "   🌐 Locust UI:    ${GREEN}http://localhost:8089${NC}"
    echo -e "   🚀 API:          ${GREEN}http://localhost:8000${NC}"
    echo -e "   📚 API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "   ❤️  Health Check: ${GREEN}http://localhost:8000/health${NC}"
    echo ""
    
    # Siempre modo web - NO ejecutar pruebas automáticas
    echo -e "${YELLOW}✨ Servicios listos para usar${NC}"
    echo ""
    echo -e "${BLUE}Configura tu prueba en la UI de Locust:${NC}"
    echo -e "   ${GREEN}👉 http://localhost:8089${NC}"
    echo ""
    echo -e "${BLUE}Configuración sugerida:${NC}"
    if [ -f .current_config ]; then
        read -r cpu mem users rate time < .current_config
        echo -e "   Usuarios:    ${YELLOW}$users${NC}"
        echo -e "   Spawn rate:  ${YELLOW}$rate/s${NC}"
        echo -e "   Duración:    ${YELLOW}$time${NC}"
    fi
    echo ""
    echo -e "${BLUE}Comandos útiles:${NC}"
    echo -e "   Ver logs:    ${YELLOW}./start_all.sh --logs${NC}"
    echo -e "   Ver estado:  ${YELLOW}./start_all.sh --status${NC}"
    echo -e "   Detener:     ${YELLOW}./stop_all.sh${NC}"
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ¡Todo listo para pruebas de carga!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

# Ejecutar main
main "$@"
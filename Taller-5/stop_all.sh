#!/bin/bash
# Script para detener todos los servicios de Locust
# Uso: ./stop_all.sh [--clean] [--volumes] [--results]

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración
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
    echo -e "${RED}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🛑 DETENER SERVICIOS DE LOCUST 🛑                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Función para mostrar ayuda
show_help() {
    cat << EOF
${BLUE}Uso:${NC} $0 [OPCIONES]

${BLUE}Opciones:${NC}
  -h, --help          Mostrar esta ayuda
  -c, --clean         Detener y eliminar contenedores y redes
  -v, --volumes       También eliminar volúmenes de datos
  -r, --results       También eliminar resultados de pruebas
  -a, --all           Limpieza completa (contenedores + volúmenes + resultados)
  -s, --status        Solo mostrar estado actual
  -f, --force         No pedir confirmación

${BLUE}Ejemplos:${NC}
  $0                  # Solo detener servicios
  $0 --clean          # Detener y limpiar contenedores
  $0 --all            # Limpieza completa
  $0 --status         # Ver estado actual

${BLUE}Niveles de limpieza:${NC}
  Sin opciones        → Solo detener contenedores (se pueden reiniciar)
  --clean            → Eliminar contenedores y redes
  --volumes          → + Eliminar volúmenes de datos
  --results          → + Eliminar resultados de pruebas
  --all              → Limpieza completa de todo

EOF
}

# Función para mostrar estado
show_status() {
    log "Estado actual de los servicios:"
    echo ""
    
    if docker compose -f "$COMPOSE_FILE" ps 2>/dev/null | grep -q "Up"; then
        docker compose -f "$COMPOSE_FILE" ps
        echo ""
        info "Servicios activos detectados"
    else
        info "No hay servicios activos"
    fi
    
    echo ""
    info "Contenedores de Locust:"
    docker ps -a | grep -E "locust|inference" || echo "   Ninguno encontrado"
    
    echo ""
    info "Redes de Locust:"
    docker network ls | grep locust || echo "   Ninguna encontrada"
    
    echo ""
    info "Volúmenes de Locust:"
    docker volume ls | grep locust || echo "   Ninguno encontrado"
    
    if [ -d "$RESULTS_DIR" ]; then
        echo ""
        info "Resultados de pruebas:"
        ls -lh "$RESULTS_DIR" 2>/dev/null | tail -n +2 || echo "   Directorio vacío"
    fi
}

# Función para confirmar acción
confirm_action() {
    local message=$1
    local force=$2
    
    if [ "$force" = true ]; then
        return 0
    fi
    
    warning "$message"
    read -p "¿Estás seguro? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Operación cancelada"
        exit 0
    fi
}

# Función para detener servicios
stop_services() {
    log "Deteniendo servicios..."
    
    if docker compose -f "$COMPOSE_FILE" ps 2>/dev/null | grep -q "Up"; then
        docker compose -f "$COMPOSE_FILE" stop
        info "✅ Servicios detenidos"
    else
        info "No hay servicios en ejecución"
    fi
}

# Función para limpiar contenedores
clean_containers() {
    log "Eliminando contenedores y redes..."
    
    docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    
    # Limpiar contenedores huérfanos
    docker ps -a | grep -E "locust|inference" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
    
    info "✅ Contenedores eliminados"
}

# Función para limpiar volúmenes
clean_volumes() {
    log "Eliminando volúmenes..."
    
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    
    # Limpiar volúmenes huérfanos de locust
    docker volume ls | grep locust | awk '{print $2}' | xargs -r docker volume rm 2>/dev/null || true
    
    info "✅ Volúmenes eliminados"
}

# Función para limpiar resultados
clean_results() {
    log "Eliminando resultados de pruebas..."
    
    if [ -d "$RESULTS_DIR" ]; then
        local file_count=$(ls -1 "$RESULTS_DIR" 2>/dev/null | wc -l)
        if [ "$file_count" -gt 0 ]; then
            rm -rf "${RESULTS_DIR:?}"/*
            info "✅ $file_count archivos eliminados de $RESULTS_DIR"
        else
            info "Directorio de resultados ya está vacío"
        fi
    else
        info "Directorio de resultados no existe"
    fi
    
    # Limpiar archivo de configuración temporal
    [ -f .current_config ] && rm -f .current_config
}

# Función para limpiar redes huérfanas
clean_networks() {
    log "Limpiando redes huérfanas..."
    
    docker network ls | grep locust | awk '{print $1}' | xargs -r docker network rm 2>/dev/null || true
    
    info "✅ Redes limpiadas"
}

# Función para mostrar resumen final
show_summary() {
    local stopped=$1
    local cleaned=$2
    local volumes=$3
    local results=$4
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Resumen de operaciones completadas:${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    
    [ "$stopped" = true ] && echo -e "   ${GREEN}✅${NC} Servicios detenidos"
    [ "$cleaned" = true ] && echo -e "   ${GREEN}✅${NC} Contenedores eliminados"
    [ "$volumes" = true ] && echo -e "   ${GREEN}✅${NC} Volúmenes eliminados"
    [ "$results" = true ] && echo -e "   ${GREEN}✅${NC} Resultados eliminados"
    
    echo ""
    echo -e "${BLUE}Estado final:${NC}"
    
    # Verificar que todo está limpio
    local containers=$(docker ps -a | grep -c -E "locust|inference" || true)
    local networks=$(docker network ls | grep -c locust || true)
    local volumes=$(docker volume ls | grep -c locust || true)
    
    if [ "$containers" -eq 0 ] && [ "$networks" -eq 0 ] && [ "$volumes" -eq 0 ]; then
        echo -e "   ${GREEN}✅ Sistema completamente limpio${NC}"
    else
        [ "$containers" -gt 0 ] && echo -e "   ${YELLOW}⚠️  $containers contenedores restantes${NC}"
        [ "$networks" -gt 0 ] && echo -e "   ${YELLOW}⚠️  $networks redes restantes${NC}"
        [ "$volumes" -gt 0 ] && echo -e "   ${YELLOW}⚠️  $volumes volúmenes restantes${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Para reiniciar:${NC}"
    echo -e "   ${YELLOW}./start_all.sh${NC}"
    echo ""
}

# Función principal
main() {
    local clean=false
    local volumes=false
    local results=false
    local all=false
    local status_only=false
    local force=false
    
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--clean)
                clean=true
                shift
                ;;
            -v|--volumes)
                volumes=true
                clean=true
                shift
                ;;
            -r|--results)
                results=true
                shift
                ;;
            -a|--all)
                all=true
                clean=true
                volumes=true
                results=true
                shift
                ;;
            -s|--status)
                status_only=true
                shift
                ;;
            -f|--force)
                force=true
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
    if [ "$status_only" = true ]; then
        show_status
        exit 0
    fi
    
    # Variables para tracking
    local stopped=false
    local cleaned=false
    local volumes_cleaned=false
    local results_cleaned=false
    
    # Confirmar si es limpieza completa
    if [ "$all" = true ]; then
        confirm_action "Se eliminará TODO: contenedores, volúmenes y resultados" "$force"
    elif [ "$volumes" = true ]; then
        confirm_action "Se eliminarán contenedores Y volúmenes de datos" "$force"
    elif [ "$clean" = true ]; then
        confirm_action "Se eliminarán contenedores (los volúmenes se conservarán)" "$force"
    fi
    
    # Detener servicios
    stop_services
    stopped=true
    
    # Limpiar contenedores si se solicita
    if [ "$clean" = true ]; then
        clean_containers
        clean_networks
        cleaned=true
    fi
    
    # Limpiar volúmenes si se solicita
    if [ "$volumes" = true ]; then
        clean_volumes
        volumes_cleaned=true
    fi
    
    # Limpiar resultados si se solicita
    if [ "$results" = true ]; then
        clean_results
        results_cleaned=true
    fi
    
    # Mostrar resumen
    show_summary "$stopped" "$cleaned" "$volumes_cleaned" "$results_cleaned"
    
    echo -e "${GREEN}✅ Operación completada${NC}"
}

# Ejecutar main
main "$@"
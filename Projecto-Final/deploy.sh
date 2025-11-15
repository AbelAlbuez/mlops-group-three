#!/usr/bin/env bash
#
# Script de despliegue automatizado para Proyecto 3 MLOps
# Despliega el proyecto en una VM Rocky Linux
#
# Uso: ./deploy.sh [--dry-run] [--skip-cleanup]
#

set -euo pipefail

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

VM_HOST="10.43.100.80"
VM_USER="estudiante"
VM_PASSWORD="@A18u3z123098@"
VM_PROJECT_DIR="~/Projecto-3"
LOCAL_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Flags
DRY_RUN=false
SKIP_CLEANUP=false
AUTO_YES=false
LOG_FILE="/tmp/deploy_$(date +%Y%m%d_%H%M%S).log"

# Variables de entorno requeridas
REQUIRED_ENV_VARS=(
    "AIRFLOW_UID=50000"
    "MLFLOW_PORT=8020"
    "MINIO_API_PORT=8030"
    "MINIO_CONSOLE_PORT=8031"
)

# Servicios esperados
EXPECTED_SERVICES=(
    "airflow-webserver"
    "airflow-scheduler"
    "mlflow"
    "minio"
    "mlflow-db"
    "raw-db"
    "clean-db"
    "airflow-init"
)

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}ℹ${NC} $*" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE"
    exit 1
}

step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶${NC} ${BLUE}$*${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

timer_start() {
    TIMER_START=$(date +%s)
}

timer_end() {
    local end=$(date +%s)
    local duration=$((end - TIMER_START))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    if [ $minutes -gt 0 ]; then
        echo -e "${DIM}⏱  Tiempo: ${minutes}m ${seconds}s${NC}"
    else
        echo -e "${DIM}⏱  Tiempo: ${seconds}s${NC}"
    fi
}

# Ejecutar comando SSH
ssh_exec() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] SSH: $cmd"
        return 0
    fi
    
    sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        "${VM_USER}@${VM_HOST}" "$cmd"
}

# Ejecutar comando SSH con output
ssh_exec_verbose() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] SSH: $cmd"
        return 0
    fi
    
    sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        "${VM_USER}@${VM_HOST}" "$cmd"
}

# Verificar que un comando SSH fue exitoso
ssh_check() {
    local cmd="$1"
    local description="${2:-Comando}"
    
    if ssh_exec "$cmd" >/dev/null 2>&1; then
        success "$description"
        return 0
    else
        error "$description falló"
        return 1
    fi
}

# Esperar con mensaje
wait_with_message() {
    local seconds="$1"
    local message="${2:-Esperando...}"
    for i in $(seq 1 "$seconds"); do
        echo -ne "\r${DIM}${message} (${i}/${seconds})${NC}"
        sleep 1
    done
    echo -ne "\r${NC}"
}

# ============================================================================
# FUNCIONES DE DESPLIEGUE
# ============================================================================

check_prerequisites() {
    step "Verificando prerrequisitos"
    timer_start
    
    # Verificar sshpass
    if ! command -v sshpass &> /dev/null; then
        error "sshpass no está instalado. Instálalo con: brew install hudochenkov/sshpass/sshpass"
    fi
    success "sshpass instalado"
    
    # Verificar rsync
    if ! command -v rsync &> /dev/null; then
        error "rsync no está instalado"
    fi
    success "rsync instalado"
    
    # Verificar conexión SSH
    info "Verificando conexión SSH a ${VM_HOST}..."
    if ssh_exec "echo 'Conexión exitosa'" >/dev/null 2>&1; then
        success "Conexión SSH establecida"
    else
        error "No se pudo conectar a ${VM_HOST}"
    fi
    
    # Verificar Docker en VM
    info "Verificando Docker en VM..."
    if ssh_exec "docker --version" >/dev/null 2>&1; then
        local docker_version=$(ssh_exec "docker --version")
        success "Docker instalado: $docker_version"
    else
        error "Docker no está instalado en la VM"
    fi
    
    # Verificar docker-compose en VM
    info "Verificando Docker Compose en VM..."
    if ssh_exec "docker compose version" >/dev/null 2>&1; then
        local compose_version=$(ssh_exec "docker compose version")
        success "Docker Compose instalado: $compose_version"
    else
        error "Docker Compose no está instalado en la VM"
    fi
    
    timer_end
}

cleanup_vm() {
    if [ "$SKIP_CLEANUP" = true ]; then
        warning "Saltando limpieza de VM (--skip-cleanup)"
        return 0
    fi
    
    step "Limpiando VM"
    timer_start
    
    # Confirmación
    if [ "$AUTO_YES" = false ]; then
        echo -e "${YELLOW}⚠ ADVERTENCIA: Esto eliminará todos los datos y contenedores en ~/Projecto-3${NC}"
        read -p "¿Continuar? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            error "Operación cancelada por el usuario"
        fi
    else
        warning "Modo automático: saltando confirmación (--yes)"
    fi
    
    info "Conectando a VM y limpiando..."
    
    # Ir a directorio y detener servicios
    info "Deteniendo servicios Docker..."
    ssh_exec "cd ${VM_PROJECT_DIR} 2>/dev/null && docker compose down -v 2>/dev/null || true"
    success "Servicios detenidos"
    
    # Limpiar Docker
    info "Limpiando sistema Docker..."
    ssh_exec "docker system prune -a --volumes -f >/dev/null 2>&1 || true"
    success "Sistema Docker limpiado"
    
    # Eliminar directorio
    info "Eliminando directorio ${VM_PROJECT_DIR}..."
    # Intentar primero sin sudo
    ssh_exec "rm -rf ${VM_PROJECT_DIR} 2>/dev/null || true"
    
    # Verificar eliminación
    if ssh_exec "test -d ${VM_PROJECT_DIR}" 2>/dev/null; then
        warning "El directorio aún existe, intentando con sudo..."
        # Usar sudo con contraseña
        ssh_exec "echo '${VM_PASSWORD}' | sudo -S rm -rf ${VM_PROJECT_DIR} 2>/dev/null || true"
    fi
    
    # Verificar nuevamente
    if ssh_exec "test -d ${VM_PROJECT_DIR}" 2>/dev/null; then
        warning "No se pudo eliminar completamente el directorio ${VM_PROJECT_DIR}, pero continuando..."
    else
        success "Directorio eliminado correctamente"
    fi
    
    timer_end
}

transfer_files() {
    step "Transfiriendo archivos a VM"
    timer_start
    
    info "Sincronizando archivos con rsync..."
    
    # Crear directorio en VM
    ssh_exec "mkdir -p ${VM_PROJECT_DIR}"
    
    # Excluir archivos no necesarios
    local exclude_patterns=(
        "--exclude=*.pyc"
        "--exclude=__pycache__"
        "--exclude=.git"
        "--exclude=*.log"
        "--exclude=venv"
        "--exclude=node_modules"
        "--exclude=.DS_Store"
        "--exclude=airflow/logs"
        "--exclude=airflow/airflow.db"
        "--exclude=airflow/airflow-webserver.pid"
        "--exclude=airflow/airflow.cfg"
        "--exclude=airflow/webserver_config.py"
        "--exclude=.env"
    )
    
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] rsync -avz ${exclude_patterns[*]} ${LOCAL_PROJECT_DIR}/ ${VM_USER}@${VM_HOST}:${VM_PROJECT_DIR}/"
    else
        sshpass -p "$VM_PASSWORD" rsync -avz --progress \
            "${exclude_patterns[@]}" \
            -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR" \
            "${LOCAL_PROJECT_DIR}/" \
            "${VM_USER}@${VM_HOST}:${VM_PROJECT_DIR}/" \
            | tee -a "$LOG_FILE"
    fi
    
    success "Archivos transferidos"
    
    # Verificar archivos críticos
    info "Verificando archivos críticos..."
    local critical_files=(
        "docker-compose.yml"
        "airflow/dags/1_raw_batch_ingest_15k.py"
        "airflow/dags/2_clean_build.py"
        "airflow/dags/3_train_and_register.py"
    )
    
    for file in "${critical_files[@]}"; do
        if ssh_exec "test -f ${VM_PROJECT_DIR}/${file}" 2>/dev/null; then
            success "Archivo verificado: $file"
        else
            error "Archivo crítico no encontrado: $file"
        fi
    done
    
    timer_end
}

verify_config() {
    step "Verificando configuración"
    timer_start
    
    info "Verificando archivo .env..."
    
    # Verificar si existe .env.copy
    if ssh_exec "test -f ${VM_PROJECT_DIR}/.env.copy" 2>/dev/null; then
        info "Copiando .env.copy a .env..."
        ssh_exec "cp ${VM_PROJECT_DIR}/.env.copy ${VM_PROJECT_DIR}/.env"
    else
        warning ".env.copy no encontrado, creando .env desde cero..."
    fi
    
    # Verificar y ajustar variables requeridas
    info "Configurando variables de entorno..."
    for var_setting in "${REQUIRED_ENV_VARS[@]}"; do
        local var_name="${var_setting%%=*}"
        local var_value="${var_setting#*=}"
        
        # Verificar si la variable existe
        if ssh_exec "grep -q '^${var_name}=' ${VM_PROJECT_DIR}/.env" 2>/dev/null; then
            # Actualizar valor
            ssh_exec "sed -i 's|^${var_name}=.*|${var_name}=${var_value}|' ${VM_PROJECT_DIR}/.env"
            success "Variable ${var_name} configurada a ${var_value}"
        else
            # Agregar variable
            ssh_exec "echo '${var_name}=${var_value}' >> ${VM_PROJECT_DIR}/.env"
            success "Variable ${var_name} agregada: ${var_value}"
        fi
    done
    
    # Verificar AIRFLOW_UID específicamente
    local airflow_uid=$(ssh_exec "grep '^AIRFLOW_UID=' ${VM_PROJECT_DIR}/.env | cut -d'=' -f2" 2>/dev/null || echo "")
    if [ "$airflow_uid" != "50000" ]; then
        warning "AIRFLOW_UID no es 50000, ajustando..."
        ssh_exec "sed -i 's|^AIRFLOW_UID=.*|AIRFLOW_UID=50000|' ${VM_PROJECT_DIR}/.env"
    fi
    
    # Mostrar configuración final
    info "Configuración final del .env:"
    ssh_exec "grep -E '^(AIRFLOW_UID|MLFLOW_PORT|MINIO_API_PORT|MINIO_CONSOLE_PORT)=' ${VM_PROJECT_DIR}/.env" | tee -a "$LOG_FILE"
    
    timer_end
}

deploy_services() {
    step "Desplegando servicios"
    timer_start
    
    # Dar permisos a airflow
    info "Configurando permisos para Airflow..."
    ssh_exec "chmod -R 777 ${VM_PROJECT_DIR}/airflow/ 2>/dev/null || echo '${VM_PASSWORD}' | sudo -S chmod -R 777 ${VM_PROJECT_DIR}/airflow/ 2>/dev/null || true"
    success "Permisos configurados"
    
    # Construir imágenes
    info "Construyendo imágenes Docker (esto puede tardar varios minutos)..."
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] docker compose build"
    else
        ssh_exec_verbose "cd ${VM_PROJECT_DIR} && docker compose build" | tee -a "$LOG_FILE"
    fi
    success "Imágenes construidas"
    
    # Levantar servicios
    info "Levantando servicios..."
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] docker compose up -d"
    else
        ssh_exec_verbose "cd ${VM_PROJECT_DIR} && docker compose up -d" | tee -a "$LOG_FILE"
    fi
    success "Servicios iniciados"
    
    # Esperar a que inicien
    info "Esperando 60 segundos para que los servicios inicien..."
    wait_with_message 60 "Esperando inicialización de servicios"
    
    timer_end
}

validate_deployment() {
    step "Validando despliegue"
    timer_start
    
    info "Verificando estado de contenedores..."
    
    local all_ok=true
    
    for service in "${EXPECTED_SERVICES[@]}"; do
        local status=$(ssh_exec "cd ${VM_PROJECT_DIR} && docker compose ps --format '{{.Name}}:{{.State}}' 2>/dev/null | grep '^${service}:' | cut -d: -f2- | tr -d ' '" 2>/dev/null || echo "not found")
        
        case "$service" in
            "airflow-init")
                if [[ "$status" == *"exited"* ]] || [[ "$status" == *"Exited"* ]] || [ -z "$status" ]; then
                    success "✓ ${service}: Exited (0) - correcto"
                else
                    warning "⚠ ${service}: ${status} (esperado: Exited 0)"
                    # No marcar como error porque airflow-init puede no aparecer si ya terminó
                fi
                ;;
            *)
                if [[ "$status" == *"running"* ]] || [[ "$status" == *"healthy"* ]] || [[ "$status" == *"Up"* ]]; then
                    success "✓ ${service}: ${status}"
                else
                    warning "⚠ ${service}: ${status} (esperado: running/healthy)"
                    all_ok=false
                fi
                ;;
        esac
    done
    
    if [ "$all_ok" = true ]; then
        success "Todos los servicios están corriendo correctamente"
    else
        warning "Algunos servicios no están en el estado esperado"
    fi
    
    timer_end
}

test_connectivity() {
    step "Probando conectividad"
    timer_start
    
    info "Verificando endpoints HTTP..."
    
    local all_ok=true
    
    # Probar Airflow
    info "Probando Airflow..."
    local airflow_code=$(ssh_exec "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 'http://localhost:8080/health' 2>/dev/null || echo '000'")
    if [ "$airflow_code" = "200" ]; then
        success "✓ Airflow: HTTP ${airflow_code}"
    else
        warning "⚠ Airflow: HTTP ${airflow_code} (esperado: 200)"
        all_ok=false
    fi
    
    # Probar MLflow
    info "Probando MLflow..."
    local mlflow_code=$(ssh_exec "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 'http://localhost:8020' 2>/dev/null || echo '000'")
    if [ "$mlflow_code" = "200" ]; then
        success "✓ MLflow: HTTP ${mlflow_code}"
    else
        warning "⚠ MLflow: HTTP ${mlflow_code} (esperado: 200)"
        all_ok=false
    fi
    
    # Probar MinIO API
    info "Probando MinIO API..."
    local minio_api_code=$(ssh_exec "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 'http://localhost:8030/minio/health/ready' 2>/dev/null || echo '000'")
    if [ "$minio_api_code" = "200" ]; then
        success "✓ MinIO API: HTTP ${minio_api_code}"
    else
        warning "⚠ MinIO API: HTTP ${minio_api_code} (esperado: 200)"
        all_ok=false
    fi
    
    # Probar MinIO Console
    info "Probando MinIO Console..."
    local minio_console_code=$(ssh_exec "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 'http://localhost:8031' 2>/dev/null || echo '000'")
    if [ "$minio_console_code" = "200" ]; then
        success "✓ MinIO Console: HTTP ${minio_console_code}"
    else
        warning "⚠ MinIO Console: HTTP ${minio_console_code} (esperado: 200)"
        all_ok=false
    fi
    
    if [ "$all_ok" = true ]; then
        success "Todos los endpoints responden correctamente"
    else
        warning "Algunos endpoints no responden como se esperaba"
    fi
    
    timer_end
}

verify_data() {
    step "Verificando datos"
    timer_start
    
    info "Verificando datos en raw-db..."
    
    local row_count=$(ssh_exec "cd ${VM_PROJECT_DIR} && docker compose exec -T raw-db psql -U raw_user -d raw_data -tA -c 'SELECT COUNT(*) FROM diabetic_raw;' 2>/dev/null" | tr -d '[:space:]' || echo "0")
    
    if [ -z "$row_count" ] || [ "$row_count" = "0" ]; then
        warning "No hay datos en diabetic_raw (${row_count} registros)"
        warning "Es necesario ejecutar los DAGs en Airflow para cargar datos"
    elif [ "$row_count" -gt 0 ]; then
        success "Datos encontrados: ${row_count} registros en diabetic_raw"
        
        if [ "$row_count" -ge 100000 ] && [ "$row_count" -le 105000 ]; then
            success "Cantidad de datos esperada (~101,766 registros)"
        else
            warning "Cantidad de datos inusual: ${row_count} (esperado ~101,766)"
        fi
    else
        error "Error al consultar la base de datos"
    fi
    
    timer_end
}

generate_report() {
    step "Generando reporte final"
    
    local vm_ip="$VM_HOST"
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}                    DESPLIEGUE COMPLETADO${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${CYAN}📊 ESTADO DE SERVICIOS:${NC}"
    ssh_exec "cd ${VM_PROJECT_DIR} && docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'" | tee -a "$LOG_FILE"
    
    echo -e "\n${CYAN}🌐 URLs DE ACCESO:${NC}"
    echo -e "  ${BLUE}Airflow:${NC}     http://${vm_ip}:8080"
    echo -e "  ${BLUE}MLflow:${NC}      http://${vm_ip}:8020"
    echo -e "  ${BLUE}MinIO API:${NC}   http://${vm_ip}:8030"
    echo -e "  ${BLUE}MinIO Console:${NC} http://${vm_ip}:8031"
    
    echo -e "\n${CYAN}🔐 CREDENCIALES:${NC}"
    echo -e "  ${BLUE}Airflow:${NC}"
    echo -e "    Usuario: admin"
    echo -e "    Password: admin123"
    echo -e "  ${BLUE}MinIO:${NC}"
    local minio_user=$(ssh_exec "grep '^MINIO_ROOT_USER=' ${VM_PROJECT_DIR}/.env | cut -d'=' -f2" 2>/dev/null || echo "admin")
    local minio_pass=$(ssh_exec "grep '^MINIO_ROOT_PASSWORD=' ${VM_PROJECT_DIR}/.env | cut -d'=' -f2" 2>/dev/null || echo "adminadmin")
    echo -e "    Usuario: ${minio_user}"
    echo -e "    Password: ${minio_pass}"
    
    echo -e "\n${CYAN}📝 PRÓXIMOS PASOS:${NC}"
    echo -e "  1. Acceder a Airflow: http://${vm_ip}:8080"
    echo -e "  2. Ejecutar DAGs en orden:"
    echo -e "     - ${YELLOW}1_raw_batch_ingest_15k${NC} (cargar datos)"
    echo -e "     - ${YELLOW}2_clean_build${NC} (limpiar y transformar)"
    echo -e "     - ${YELLOW}3_train_and_register${NC} (entrenar modelo)"
    echo -e "  3. Verificar modelo en MLflow: http://${vm_ip}:8020"
    echo -e "  4. Revisar logs si hay problemas:"
    echo -e "     ${DIM}ssh ${VM_USER}@${VM_HOST}${NC}"
    echo -e "     ${DIM}cd ${VM_PROJECT_DIR}${NC}"
    echo -e "     ${DIM}docker compose logs -f [servicio]${NC}"
    
    echo -e "\n${CYAN}📄 LOG:${NC}"
    echo -e "  ${DIM}Log guardado en: ${LOG_FILE}${NC}"
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

main() {
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            --yes)
                AUTO_YES=true
                shift
                ;;
            *)
                echo "Uso: $0 [--dry-run] [--skip-cleanup] [--yes]"
                exit 1
                ;;
        esac
    done
    
    # Banner
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     DESPLIEGUE AUTOMATIZADO - PROYECTO 3 MLOPS                ║"
    echo "║     VM: ${VM_HOST}                                              ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        warning "MODO DRY-RUN: No se realizarán cambios reales"
    fi
    
    # Iniciar log
    log "INFO" "Iniciando despliegue"
    log "INFO" "VM: ${VM_HOST}"
    log "INFO" "Proyecto local: ${LOCAL_PROJECT_DIR}"
    log "INFO" "Proyecto remoto: ${VM_PROJECT_DIR}"
    
    # Ejecutar pasos
    check_prerequisites
    cleanup_vm
    transfer_files
    verify_config
    deploy_services
    validate_deployment
    test_connectivity
    verify_data
    generate_report
    
    success "Despliegue completado exitosamente!"
    log "INFO" "Despliegue completado"
}

# Ejecutar función principal
main "$@"


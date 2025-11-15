#!/usr/bin/env bash
"""
Script Automatizado de Pruebas de Rendimiento
Ejecuta las 5 pruebas, anota resultados, escala pods y genera reporte

Uso:
    ./run_performance_tests.sh
"""

set -euo pipefail

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

API_HOST="http://10.43.100.87:8001"
LOCUST_FILE="simple_load_test.py"
NAMESPACE="apps"
DEPLOYMENT_NAME="api"

# Resultados
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="results_${TIMESTAMP}"
REPORT_FILE="${RESULTS_DIR}/PERFORMANCE_REPORT.md"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# FUNCIONES
# ============================================================================

log() {
    echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"
}

success() {
    echo -e "${GREEN}✓${NC} $*"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

error() {
    echo -e "${RED}✗${NC} $*"
}

section() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$*${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ============================================================================
# PREPARACIÓN
# ============================================================================

section "🚀 PREPARACIÓN"

# Crear directorio de resultados
mkdir -p "$RESULTS_DIR"
log "Directorio de resultados: $RESULTS_DIR"

# Verificar que el script de Locust existe
if [[ ! -f "$LOCUST_FILE" ]]; then
    error "No se encuentra el archivo: $LOCUST_FILE"
    exit 1
fi
success "Script de Locust encontrado"

# Verificar conexión a la API
log "Verificando API en $API_HOST..."
if curl -s -f "${API_HOST}/health" > /dev/null 2>&1; then
    success "API disponible"
else
    error "API no disponible en $API_HOST"
    exit 1
fi

# Verificar kubectl
if ! kubectl get pods -n $NAMESPACE > /dev/null 2>&1; then
    error "No se puede conectar a Kubernetes"
    exit 1
fi
success "Kubernetes accesible"

# Verificar réplicas iniciales
INITIAL_REPLICAS=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")
log "Réplicas iniciales: $INITIAL_REPLICAS"

# ============================================================================
# FUNCIÓN PARA EJECUTAR PRUEBAS
# ============================================================================

run_locust_test() {
    local users=$1
    local spawn_rate=$2
    local duration=$3
    local test_name=$4
    local output_file="${RESULTS_DIR}/test_${test_name}_${users}users.html"
    local stats_file="${RESULTS_DIR}/test_${test_name}_${users}users_stats.csv"
    
    log "Ejecutando prueba: $test_name ($users usuarios, ${duration})"
    
    # Ejecutar Locust
    locust -f "$LOCUST_FILE" \
        --headless \
        --users "$users" \
        --spawn-rate "$spawn_rate" \
        --run-time "$duration" \
        --host "$API_HOST" \
        --html "$output_file" \
        --csv "${RESULTS_DIR}/test_${test_name}_${users}users" \
        2>&1 | tee "${RESULTS_DIR}/test_${test_name}_${users}users.log" | \
        grep -E "Type|Aggregated|failures" || true
    
    success "Prueba completada: $test_name"
    
    # Capturar métricas de K8s
    log "Capturando métricas de Kubernetes..."
    kubectl top pods -n $NAMESPACE > "${RESULTS_DIR}/k8s_metrics_${test_name}.txt" 2>&1 || echo "metrics-server no disponible"
    kubectl get pods -n $NAMESPACE > "${RESULTS_DIR}/k8s_pods_${test_name}.txt" 2>&1
    
    # Esperar un poco antes de la siguiente prueba
    log "Esperando 10 segundos antes de la siguiente prueba..."
    sleep 10
}

# ============================================================================
# FUNCIÓN PARA EXTRAER MÉTRICAS
# ============================================================================

extract_metrics() {
    local test_name=$1
    local users=$2
    local stats_file="${RESULTS_DIR}/test_${test_name}_${users}users_stats.csv"
    
    if [[ ! -f "$stats_file" ]]; then
        echo "N/A|N/A|N/A|N/A|N/A"
        return
    fi
    
    # Extraer línea "Aggregated"
    local aggregated_line=$(grep "Aggregated" "$stats_file" 2>/dev/null | head -1 || echo "")
    
    if [[ -z "$aggregated_line" ]]; then
        echo "N/A|N/A|N/A|N/A|N/A"
        return
    fi
    
    # CSV format: Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
    
    local request_count=$(echo "$aggregated_line" | cut -d',' -f3)
    local failure_count=$(echo "$aggregated_line" | cut -d',' -f4)
    local avg_response=$(echo "$aggregated_line" | cut -d',' -f6)
    local p95_response=$(echo "$aggregated_line" | cut -d',' -f16)
    local rps=$(echo "$aggregated_line" | cut -d',' -f10)
    
    # Calcular error rate
    local error_rate=0
    if [[ "$request_count" -gt 0 ]]; then
        error_rate=$(awk "BEGIN {printf \"%.2f\", ($failure_count / $request_count) * 100}")
    fi
    
    echo "${rps}|${avg_response}|${p95_response}|${error_rate}|${request_count}"
}

# ============================================================================
# FUNCIÓN PARA OBTENER MÉTRICAS DE K8S
# ============================================================================

get_k8s_metrics() {
    local test_name=$1
    local metrics_file="${RESULTS_DIR}/k8s_metrics_${test_name}.txt"
    
    if [[ ! -f "$metrics_file" ]]; then
        echo "N/A|N/A"
        return
    fi
    
    # Extraer CPU y memoria del pod API
    local api_metrics=$(grep "api-" "$metrics_file" | head -1 || echo "")
    
    if [[ -z "$api_metrics" ]]; then
        echo "N/A|N/A"
        return
    fi
    
    local cpu=$(echo "$api_metrics" | awk '{print $2}')
    local memory=$(echo "$api_metrics" | awk '{print $3}')
    
    echo "${cpu}|${memory}"
}

# ============================================================================
# PASO 2: EJECUTAR 5 PRUEBAS
# ============================================================================

section "📊 PASO 2: EJECUTANDO 5 PRUEBAS PROGRESIVAS"

log "Todas las pruebas usarán host: $API_HOST"
echo ""

# Prueba 1: Baseline
section "🔹 PRUEBA 1: BASELINE (10 usuarios)"
run_locust_test 10 2 "2m" "prueba1_baseline"

# Prueba 2: Carga ligera
section "🔹 PRUEBA 2: CARGA LIGERA (25 usuarios)"
run_locust_test 25 5 "3m" "prueba2_ligera"

# Prueba 3: Carga normal
section "🔹 PRUEBA 3: CARGA NORMAL (50 usuarios)"
run_locust_test 50 10 "5m" "prueba3_normal"

# Prueba 4: Carga alta
section "🔹 PRUEBA 4: CARGA ALTA (100 usuarios)"
run_locust_test 100 10 "5m" "prueba4_alta"

# Prueba 5: Estrés máximo
section "🔹 PRUEBA 5: ESTRÉS MÁXIMO (200 usuarios)"
run_locust_test 200 20 "3m" "prueba5_estres"

success "Todas las pruebas completadas con 1 réplica"

# ============================================================================
# PASO 3: RECOPILAR Y ANALIZAR RESULTADOS
# ============================================================================

section "📈 PASO 3: ANALIZANDO RESULTADOS"

log "Extrayendo métricas de todas las pruebas..."

# Extraer métricas de cada prueba
METRICS_P1=$(extract_metrics "prueba1_baseline" 10)
METRICS_P2=$(extract_metrics "prueba2_ligera" 25)
METRICS_P3=$(extract_metrics "prueba3_normal" 50)
METRICS_P4=$(extract_metrics "prueba4_alta" 100)
METRICS_P5=$(extract_metrics "prueba5_estres" 200)

# Extraer métricas de K8s
K8S_P1=$(get_k8s_metrics "prueba1_baseline")
K8S_P2=$(get_k8s_metrics "prueba2_ligera")
K8S_P3=$(get_k8s_metrics "prueba3_normal")
K8S_P4=$(get_k8s_metrics "prueba4_alta")
K8S_P5=$(get_k8s_metrics "prueba5_estres")

success "Métricas extraídas"

# ============================================================================
# PASO 4: ESCALAR PODS
# ============================================================================

section "🚀 PASO 4: ESCALANDO A 2 RÉPLICAS"

log "Escalando deployment '$DEPLOYMENT_NAME' de $INITIAL_REPLICAS a 2 réplicas..."

kubectl scale deployment $DEPLOYMENT_NAME --replicas=2 -n $NAMESPACE

log "Esperando a que los pods estén listos..."
kubectl wait --for=condition=ready pod -l app=api -n $NAMESPACE --timeout=120s || warning "Timeout esperando pods"

# Verificar réplicas
sleep 5
CURRENT_REPLICAS=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}')
READY_REPLICAS=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')

if [[ "$READY_REPLICAS" == "2" ]]; then
    success "2 réplicas listas y funcionando"
else
    warning "Solo $READY_REPLICAS de 2 réplicas están listas"
fi

kubectl get pods -n $NAMESPACE

# Repetir Prueba 4 con 2 réplicas
section "🔹 PRUEBA 4 (BIS): 100 USUARIOS CON 2 RÉPLICAS"

sleep 10  # Esperar estabilización

run_locust_test 100 10 "5m" "prueba4_bis_2replicas"

# Extraer métricas
METRICS_P4_BIS=$(extract_metrics "prueba4_bis_2replicas" 100)
K8S_P4_BIS=$(get_k8s_metrics "prueba4_bis_2replicas")

success "Prueba con 2 réplicas completada"

# Volver a réplica original
section "↩️ RESTAURANDO CONFIGURACIÓN ORIGINAL"

log "Volviendo a $INITIAL_REPLICAS réplica(s)..."
kubectl scale deployment $DEPLOYMENT_NAME --replicas=$INITIAL_REPLICAS -n $NAMESPACE

kubectl wait --for=condition=ready pod -l app=api -n $NAMESPACE --timeout=120s || true

success "Configuración restaurada"

# ============================================================================
# GENERAR REPORTE
# ============================================================================

section "📄 GENERANDO REPORTE"

cat > "$REPORT_FILE" << 'EOF'
# 📊 REPORTE DE ANÁLISIS DE RENDIMIENTO

**Fecha:** TIMESTAMP_PLACEHOLDER  
**Duración total:** DURATION_PLACEHOLDER  
**Sistema:** API de Predicción de Readmisión Diabética

---

## 📋 Resumen Ejecutivo

Este reporte presenta los resultados de 5 pruebas progresivas de carga realizadas sobre la API, más una prueba adicional con 2 réplicas para evaluar escalabilidad.

---

## 🧪 Pruebas Realizadas

### Configuración Inicial
- **API:** API_HOST_PLACEHOLDER
- **Namespace:** NAMESPACE_PLACEHOLDER
- **Deployment:** DEPLOYMENT_PLACEHOLDER
- **Réplicas iniciales:** INITIAL_REPLICAS_PLACEHOLDER

### Escenarios de Prueba

1. **Prueba 1: Baseline** - 10 usuarios, 2 minutos
2. **Prueba 2: Carga Ligera** - 25 usuarios, 3 minutos
3. **Prueba 3: Carga Normal** - 50 usuarios, 5 minutos
4. **Prueba 4: Carga Alta** - 100 usuarios, 5 minutos
5. **Prueba 5: Estrés Máximo** - 200 usuarios, 3 minutos
6. **Prueba 4 (bis): Carga Alta con 2 réplicas** - 100 usuarios, 5 minutos

---

## 📊 Resultados Detallados

### Tabla de Resultados - 1 Réplica

| Prueba | Usuarios | RPS | Response Time Avg | Response Time P95 | Error Rate % | CPU | Memoria | Estado |
|--------|----------|-----|-------------------|-------------------|--------------|-----|---------|--------|
| 1      | 10       | P1_RPS | P1_AVG ms | P1_P95 ms | P1_ERROR% | P1_CPU | P1_MEM | P1_STATUS |
| 2      | 25       | P2_RPS | P2_AVG ms | P2_P95 ms | P2_ERROR% | P2_CPU | P2_MEM | P2_STATUS |
| 3      | 50       | P3_RPS | P3_AVG ms | P3_P95 ms | P3_ERROR% | P3_CPU | P3_MEM | P3_STATUS |
| 4      | 100      | P4_RPS | P4_AVG ms | P4_P95 ms | P4_ERROR% | P4_CPU | P4_MEM | P4_STATUS |
| 5      | 200      | P5_RPS | P5_AVG ms | P5_P95 ms | P5_ERROR% | P5_CPU | P5_MEM | P5_STATUS |

### Comparación: 1 Réplica vs 2 Réplicas (100 usuarios)

| Configuración | RPS | Response Time P95 | Error Rate % | CPU por Pod | Memoria por Pod |
|---------------|-----|-------------------|--------------|-------------|-----------------|
| 1 Réplica     | P4_RPS | P4_P95 ms | P4_ERROR% | P4_CPU | P4_MEM |
| 2 Réplicas    | P4_BIS_RPS | P4_BIS_P95 ms | P4_BIS_ERROR% | P4_BIS_CPU | P4_BIS_MEM |
| **Mejora**    | IMPROVEMENT_RPS | IMPROVEMENT_P95 | IMPROVEMENT_ERROR | - | - |

---

## 🎯 Análisis y Conclusiones

### Capacidad del Sistema

**Con 1 Réplica:**
CONCLUSION_1_REPLICA

**Con 2 Réplicas:**
CONCLUSION_2_REPLICAS

### Cuello de Botella Identificado

BOTTLENECK_ANALYSIS

### Punto de Saturación

SATURATION_POINT

---

## 💡 Recomendaciones

### Prioridad Alta

RECOMMENDATIONS_HIGH

### Prioridad Media

RECOMMENDATIONS_MEDIUM

---

## 📁 Archivos Generados

Los siguientes archivos fueron generados durante las pruebas:

EOF

# Listar archivos generados
ls -lh "$RESULTS_DIR" | tail -n +2 | awk '{print "- " $9 " (" $5 ")"}' >> "$REPORT_FILE"

cat >> "$REPORT_FILE" << 'EOF'

---

## 📸 Screenshots Recomendados

Para completar el reporte, se recomienda tomar los siguientes screenshots:

- [ ] Dashboard de Grafana durante Prueba 1
- [ ] Dashboard de Grafana durante Prueba 4
- [ ] Terminal con `kubectl top pods` durante carga alta
- [ ] Locust UI mostrando estadísticas finales
- [ ] Gráfico de Response Time vs Usuarios

---

## 🎬 Guión para Video (2-3 minutos)

### Minuto 1: Demostración (30s)
- Mostrar las 3 ventanas: Grafana, Terminal con kubectl top
- "Realizamos 5 pruebas aumentando usuarios progresivamente"

### Minuto 2: Resultados (1m)
- Mostrar tabla de resultados
- "Con 10 usuarios todo funciona bien: X ms de latencia"
- "Con 100 usuarios aparecen errores: Y% error rate"
- "El cuello de botella es: Z (CPU/Memoria)"

### Minuto 3: Escalamiento (1m)
- "Escalamos de 1 a 2 réplicas"
- Mostrar comando kubectl scale
- "Con 2 réplicas, el error rate bajó de X% a Y%"
- "El sistema ahora soporta Z usuarios sin problemas"
- "Recomendamos usar W réplicas para producción"

### Frases Clave
- "Ejecutamos 5 escenarios de prueba con Locust"
- "El sistema con 1 réplica soporta hasta X usuarios"
- "Identificamos que el cuello de botella es el CPU/Memoria"
- "Al escalar a 2 réplicas mejoramos el throughput en X%"

---

**Análisis generado automáticamente**  
**Script:** run_performance_tests.sh
EOF

# Reemplazar placeholders
sed -i "s|TIMESTAMP_PLACEHOLDER|$(date '+%Y-%m-%d %H:%M:%S')|g" "$REPORT_FILE"
sed -i "s|API_HOST_PLACEHOLDER|$API_HOST|g" "$REPORT_FILE"
sed -i "s|NAMESPACE_PLACEHOLDER|$NAMESPACE|g" "$REPORT_FILE"
sed -i "s|DEPLOYMENT_PLACEHOLDER|$DEPLOYMENT_NAME|g" "$REPORT_FILE"
sed -i "s|INITIAL_REPLICAS_PLACEHOLDER|$INITIAL_REPLICAS|g" "$REPORT_FILE"

# Insertar métricas en la tabla
IFS='|' read -r P1_RPS P1_AVG P1_P95 P1_ERROR P1_REQUESTS <<< "$METRICS_P1"
IFS='|' read -r P1_CPU P1_MEM <<< "$K8S_P1"
P1_STATUS=$(awk "BEGIN {if ($P1_ERROR < 1) print \"✅ OK\"; else if ($P1_ERROR < 5) print \"⚠️\"; else print \"❌\"}")

IFS='|' read -r P2_RPS P2_AVG P2_P95 P2_ERROR P2_REQUESTS <<< "$METRICS_P2"
IFS='|' read -r P2_CPU P2_MEM <<< "$K8S_P2"
P2_STATUS=$(awk "BEGIN {if ($P2_ERROR < 1) print \"✅ OK\"; else if ($P2_ERROR < 5) print \"⚠️\"; else print \"❌\"}")

IFS='|' read -r P3_RPS P3_AVG P3_P95 P3_ERROR P3_REQUESTS <<< "$METRICS_P3"
IFS='|' read -r P3_CPU P3_MEM <<< "$K8S_P3"
P3_STATUS=$(awk "BEGIN {if ($P3_ERROR < 1) print \"✅ OK\"; else if ($P3_ERROR < 5) print \"⚠️\"; else print \"❌\"}")

IFS='|' read -r P4_RPS P4_AVG P4_P95 P4_ERROR P4_REQUESTS <<< "$METRICS_P4"
IFS='|' read -r P4_CPU P4_MEM <<< "$K8S_P4"
P4_STATUS=$(awk "BEGIN {if ($P4_ERROR < 1) print \"✅ OK\"; else if ($P4_ERROR < 5) print \"⚠️\"; else print \"❌\"}")

IFS='|' read -r P5_RPS P5_AVG P5_P95 P5_ERROR P5_REQUESTS <<< "$METRICS_P5"
IFS='|' read -r P5_CPU P5_MEM <<< "$K8S_P5"
P5_STATUS=$(awk "BEGIN {if ($P5_ERROR < 1) print \"✅ OK\"; else if ($P5_ERROR < 5) print \"⚠️\"; else print \"❌\"}")

IFS='|' read -r P4_BIS_RPS P4_BIS_AVG P4_BIS_P95 P4_BIS_ERROR P4_BIS_REQUESTS <<< "$METRICS_P4_BIS"
IFS='|' read -r P4_BIS_CPU P4_BIS_MEM <<< "$K8S_P4_BIS"

# Reemplazar en tabla
sed -i "s|P1_RPS|$P1_RPS|g; s|P1_AVG|$P1_AVG|g; s|P1_P95|$P1_P95|g; s|P1_ERROR%|$P1_ERROR%|g; s|P1_CPU|$P1_CPU|g; s|P1_MEM|$P1_MEM|g; s|P1_STATUS|$P1_STATUS|g" "$REPORT_FILE"
sed -i "s|P2_RPS|$P2_RPS|g; s|P2_AVG|$P2_AVG|g; s|P2_P95|$P2_P95|g; s|P2_ERROR%|$P2_ERROR%|g; s|P2_CPU|$P2_CPU|g; s|P2_MEM|$P2_MEM|g; s|P2_STATUS|$P2_STATUS|g" "$REPORT_FILE"
sed -i "s|P3_RPS|$P3_RPS|g; s|P3_AVG|$P3_AVG|g; s|P3_P95|$P3_P95|g; s|P3_ERROR%|$P3_ERROR%|g; s|P3_CPU|$P3_CPU|g; s|P3_MEM|$P3_MEM|g; s|P3_STATUS|$P3_STATUS|g" "$REPORT_FILE"
sed -i "s|P4_RPS|$P4_RPS|g; s|P4_AVG|$P4_AVG|g; s|P4_P95|$P4_P95|g; s|P4_ERROR%|$P4_ERROR%|g; s|P4_CPU|$P4_CPU|g; s|P4_MEM|$P4_MEM|g; s|P4_STATUS|$P4_STATUS|g" "$REPORT_FILE"
sed -i "s|P5_RPS|$P5_RPS|g; s|P5_AVG|$P5_AVG|g; s|P5_P95|$P5_P95|g; s|P5_ERROR%|$P5_ERROR%|g; s|P5_CPU|$P5_CPU|g; s|P5_MEM|$P5_MEM|g; s|P5_STATUS|$P5_STATUS|g" "$REPORT_FILE"
sed -i "s|P4_BIS_RPS|$P4_BIS_RPS|g; s|P4_BIS_P95|$P4_BIS_P95|g; s|P4_BIS_ERROR%|$P4_BIS_ERROR%|g; s|P4_BIS_CPU|$P4_BIS_CPU|g; s|P4_BIS_MEM|$P4_BIS_MEM|g" "$REPORT_FILE"

# Calcular mejoras
if [[ "$P4_ERROR" != "N/A" ]] && [[ "$P4_BIS_ERROR" != "N/A" ]]; then
    IMPROVEMENT_ERROR=$(awk "BEGIN {printf \"%.1f%%\", ($P4_ERROR - $P4_BIS_ERROR)}")
    sed -i "s|IMPROVEMENT_ERROR|$IMPROVEMENT_ERROR mejora|g" "$REPORT_FILE"
else
    sed -i "s|IMPROVEMENT_ERROR|N/A|g" "$REPORT_FILE"
fi

# Generar conclusiones automáticas
CONCLUSION_1=""
if (( $(echo "$P3_ERROR < 5" | bc -l 2>/dev/null || echo 0) )); then
    CONCLUSION_1="✅ El sistema funciona bien hasta **50 usuarios** (error rate < 5%)"
elif (( $(echo "$P2_ERROR < 5" | bc -l 2>/dev/null || echo 0) )); then
    CONCLUSION_1="✅ El sistema funciona bien hasta **25 usuarios** (error rate < 5%)"
else
    CONCLUSION_1="⚠️ El sistema muestra degradación desde pocos usuarios"
fi

sed -i "s|CONCLUSION_1_REPLICA|$CONCLUSION_1|g" "$REPORT_FILE"

if (( $(echo "$P4_BIS_ERROR < $P4_ERROR" | bc -l 2>/dev/null || echo 0) )); then
    CONCLUSION_2="✅ Con 2 réplicas mejora significativamente el rendimiento"
else
    CONCLUSION_2="⚠️ Escalar a 2 réplicas no mostró mejora significativa"
fi

sed -i "s|CONCLUSION_2_REPLICAS|$CONCLUSION_2|g" "$REPORT_FILE"

# Placeholder para análisis manual
sed -i "s|BOTTLENECK_ANALYSIS|⚠️ **Completar manualmente:** Revisar métricas de CPU/Memoria para identificar el cuello de botella|g" "$REPORT_FILE"
sed -i "s|SATURATION_POINT|⚠️ **Completar manualmente:** Identificar en qué prueba el sistema empezó a fallar|g" "$REPORT_FILE"
sed -i "s|RECOMMENDATIONS_HIGH|⚠️ **Completar manualmente:** Agregar recomendaciones específicas basadas en los resultados|g" "$REPORT_FILE"
sed -i "s|RECOMMENDATIONS_MEDIUM|⚠️ **Completar manualmente:** Agregar recomendaciones adicionales|g" "$REPORT_FILE"
sed -i "s|IMPROVEMENT_RPS|Calcular manualmente|g" "$REPORT_FILE"
sed -i "s|IMPROVEMENT_P95|Calcular manualmente|g" "$REPORT_FILE"

success "Reporte generado: $REPORT_FILE"

# ============================================================================
# RESUMEN FINAL
# ============================================================================

section "✅ ANÁLISIS COMPLETADO"

echo ""
echo -e "${GREEN}📊 RESUMEN DE RESULTADOS:${NC}"
echo ""
echo "Pruebas ejecutadas: 6 (5 con 1 réplica + 1 con 2 réplicas)"
echo ""
echo "Archivos generados en: ${CYAN}$RESULTS_DIR/${NC}"
echo ""
echo "Archivos importantes:"
echo "  📄 Reporte principal:    $REPORT_FILE"
echo "  📊 Reportes HTML:        test_*.html"
echo "  📈 Estadísticas CSV:     test_*_stats.csv"
echo "  📋 Métricas K8s:         k8s_*.txt"
echo ""
echo -e "${YELLOW}⚠️  Completar manualmente en el reporte:${NC}"
echo "  - Análisis de cuello de botella"
echo "  - Punto de saturación"
echo "  - Recomendaciones específicas"
echo ""
echo -e "${GREEN}🎬 Para el video:${NC}"
echo "  1. Abrir: $REPORT_FILE"
echo "  2. Usar sección 'Guión para Video'"
echo "  3. Mostrar reportes HTML de Locust"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Script completado exitosamente${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
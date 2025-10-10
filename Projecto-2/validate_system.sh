#!/bin/bash

echo "=== VALIDACIÓN COMPLETA DEL SISTEMA MLOPS ==="
echo "Proyecto 2 - Covertype Classification"
echo "Grupo 3: Abel Albuez, Omar Chalas, Mauricio Morales"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    elif [ "$status" = "ERROR" ]; then
        echo -e "${RED}❌ $message${NC}"
    else
        echo -e "${BLUE}ℹ️  $message${NC}"
    fi
}

# Función para verificar si un servicio está corriendo
check_service() {
    local service_name=$1
    local port=$2
    local path=${3:-""}
    
    if curl -s -f "http://localhost:$port$path" > /dev/null 2>&1; then
        print_status "OK" "$service_name: Online (puerto $port)"
        return 0
    else
        print_status "ERROR" "$service_name: Offline (puerto $port)"
        return 1
    fi
}

# Función para verificar contenedores Docker
check_container() {
    local container_name=$1
    local status=$(docker compose ps --format "{{.Name}} {{.Status}}" | grep "$container_name" | grep -c "Up")
    
    if [ "$status" -gt 0 ]; then
        print_status "OK" "Contenedor $container_name: Running"
        return 0
    else
        print_status "ERROR" "Contenedor $container_name: Not running"
        return 1
    fi
}

echo "1. VERIFICANDO CONTENEDORES DOCKER"
echo "=================================="

# Verificar que docker-compose está disponible
if ! docker compose version &> /dev/null; then
    print_status "ERROR" "docker compose no está disponible"
    exit 1
fi

# Verificar estado de contenedores
containers=("projecto-2-airflow-webserver-1" "projecto-2-airflow-scheduler-1" "projecto-2-mysql-db-1" "projecto-2-mlflow-db-1" "projecto-2-minio-1" "projecto-2-mlflow-1" "projecto-2-inference-1" "projecto-2-streamlit-1")
all_containers_ok=true

for container in "${containers[@]}"; do
    if ! check_container "$container"; then
        all_containers_ok=false
    fi
done

if [ "$all_containers_ok" = true ]; then
    print_status "OK" "Todos los contenedores están corriendo"
else
    print_status "WARNING" "Algunos contenedores no están corriendo. Ejecuta: docker compose up -d"
fi

echo ""
echo "2. VERIFICANDO SERVICIOS WEB"
echo "============================"

# Verificar servicios web
services=(
    "Airflow UI:8080:/health"
    "MLflow UI:5001:/health"
    "MinIO Console:9001:/minio/health/live"
    "Inference API:8000:/health"
    "Streamlit UI:8503"
)

all_services_ok=true

for service_info in "${services[@]}"; do
    IFS=':' read -r name port path <<< "$service_info"
    if ! check_service "$name" "$port" "$path"; then
        all_services_ok=false
    fi
done

echo ""
echo "3. VERIFICANDO CONECTIVIDAD DE BASE DE DATOS"
echo "============================================"

# Verificar MySQL (covertype)
if docker compose exec mysql-db mysql -u covertype_user -p covertype_pass123 -e "SELECT 1;" covertype_db > /dev/null 2>&1; then
    print_status "OK" "MySQL (covertype): Conectividad OK"
else
    print_status "ERROR" "MySQL (covertype): Error de conexión"
fi

# Verificar MySQL (mlflow)
if docker compose exec mlflow-db mysql -u mlflow -pmlflow -e "SELECT 1;" mlflow > /dev/null 2>&1; then
    print_status "OK" "MySQL (mlflow): Conectividad OK"
else
    print_status "ERROR" "MySQL (mlflow): Error de conexión"
fi

echo ""
echo "4. VERIFICANDO MLFLOW Y MODELOS"
echo "==============================="

# Verificar experimentos en MLflow
if curl -s http://localhost:5001/api/2.0/mlflow/experiments/search | grep -q "covertype_classification"; then
    print_status "OK" "Experimento 'covertype_classification' existe"
else
    print_status "WARNING" "Experimento 'covertype_classification' no encontrado"
fi

# Verificar modelos registrados
if curl -s http://localhost:5001/api/2.0/mlflow/registered-models/list | grep -q "covertype_classifier"; then
    print_status "OK" "Modelo 'covertype_classifier' registrado"
else
    print_status "WARNING" "Modelo 'covertype_classifier' no registrado"
fi

echo ""
echo "5. VERIFICANDO MINIO Y ARTIFACTS"
echo "==============================="

# Verificar bucket en MinIO
if docker compose exec projecto-2-minio-1 mc ls myminio/ | grep -q "mlflow"; then
    print_status "OK" "Bucket 'mlflow' existe en MinIO"
else
    print_status "WARNING" "Bucket 'mlflow' no encontrado"
fi

echo ""
echo "6. VERIFICANDO API DE INFERENCIA"
echo "================================"

# Test de predicción
test_payload='{
  "elevation": 2596,
  "aspect": 51,
  "slope": 3,
  "horizontal_distance_to_hydrology": 258,
  "vertical_distance_to_hydrology": 0,
  "horizontal_distance_to_roadways": 510,
  "hillshade_9am": 221,
  "hillshade_noon": 232,
  "hillshade_3pm": 148,
  "horizontal_distance_to_fire_points": 6279,
  "wilderness_area": 0,
  "soil_type": 7744
}'

if curl -s -X POST http://localhost:8000/predict \
   -H "Content-Type: application/json" \
   -d "$test_payload" | grep -q "cover_type"; then
    print_status "OK" "API de inferencia: Predicción exitosa"
else
    print_status "ERROR" "API de inferencia: Error en predicción"
fi

echo ""
echo "7. VERIFICANDO DATOS EN MYSQL"
echo "============================="

# Verificar datos en MySQL
total_samples=$(docker compose exec projecto-2-mysql-db-1 mysql -u covertype_user -pcovertype_pass123 -e "SELECT COUNT(*) as total FROM covertype_data;" covertype_db 2>/dev/null | grep -v "total" | tail -1)

if [ -n "$total_samples" ] && [ "$total_samples" -gt 0 ]; then
    print_status "OK" "Datos en MySQL: $total_samples muestras"
else
    print_status "WARNING" "No hay datos en MySQL. Ejecuta el DAG de Airflow"
fi

# Verificar métricas de modelo
model_metrics=$(docker compose exec projecto-2-mysql-db-1 mysql -u covertype_user -pcovertype_pass123 -e "SELECT COUNT(*) as total FROM model_metrics;" covertype_db 2>/dev/null | grep -v "total" | tail -1)

if [ -n "$model_metrics" ] && [ "$model_metrics" -gt 0 ]; then
    print_status "OK" "Métricas de modelo: $model_metrics registros"
else
    print_status "WARNING" "No hay métricas de modelo. Ejecuta el DAG de Airflow"
fi

echo ""
echo "8. RESUMEN FINAL"
echo "================"

if [ "$all_containers_ok" = true ] && [ "$all_services_ok" = true ]; then
    print_status "OK" "🎉 SISTEMA COMPLETAMENTE OPERATIVO"
    echo ""
    echo "Enlaces de acceso:"
    echo "• Airflow UI: http://localhost:8080 (admin/admin123)"
    echo "• MLflow UI: http://localhost:5001"
    echo "• MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
    echo "• Inference API: http://localhost:8000/docs"
    echo "• Streamlit UI: http://localhost:8503"
    echo ""
    print_status "OK" "¡Sistema listo para usar!"
else
    print_status "ERROR" "⚠️  SISTEMA PARCIALMENTE OPERATIVO"
    echo ""
    echo "Acciones recomendadas:"
    echo "1. Verificar que todos los contenedores estén corriendo: docker compose ps"
    echo "2. Revisar logs de servicios con problemas: docker compose logs [servicio]"
    echo "3. Reiniciar servicios si es necesario: docker compose restart [servicio]"
    echo "4. Ejecutar el DAG de Airflow para generar datos y modelos"
fi

echo ""
echo "=== FIN DE VALIDACIÓN ==="

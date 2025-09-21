#!/bin/bash
# Script para verificar que todos los servicios funcionan correctamente

echo "🔍 Verificando servicios del Taller MLflow..."
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para verificar servicio
check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    printf "%-20s" "$name:"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response)"
        return 1
    fi
}

# Función para verificar contenedor
check_container() {
    local name=$1
    
    printf "%-20s" "$name:"
    
    if docker ps --format '{{.Names}}' | grep -q "^$name$"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Verificar contenedores
echo "📦 Verificando contenedores Docker:"
check_container "mlflow-mysql"
check_container "mlflow-minio"
check_container "mlflow-server"
check_container "mlflow-jupyter"
check_container "mlflow-api"
echo ""

# Verificar servicios HTTP
echo "🌐 Verificando servicios HTTP:"
check_service "MinIO Console" "http://localhost:9001" 403
check_service "MinIO API" "http://localhost:9000" 403
check_service "MLflow UI" "http://localhost:5000"
check_service "JupyterLab" "http://localhost:8888"
check_service "API Health" "http://localhost:8000/health"
check_service "API Docs" "http://localhost:8000/docs"
echo ""

# Verificar conectividad MySQL
echo "🗄️ Verificando MySQL:"
printf "%-20s" "MySQL Connection:"
if docker exec mlflow-mysql mysql -u penguins -ppenguins123 -e "SELECT 1" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
    
    # Verificar bases de datos
    printf "%-20s" "Database penguins_db:"
    if docker exec mlflow-mysql mysql -u penguins -ppenguins123 -e "USE penguins_db" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Exists${NC}"
    else
        echo -e "${RED}✗ Not found${NC}"
    fi
    
    printf "%-20s" "Database mlflow_meta:"
    if docker exec mlflow-mysql mysql -u penguins -ppenguins123 -e "USE mlflow_meta" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Exists${NC}"
    else
        echo -e "${RED}✗ Not found${NC}"
    fi
else
    echo -e "${RED}✗ Connection failed${NC}"
fi
echo ""

# Verificar MinIO bucket
echo "🪣 Verificando MinIO:"
printf "%-20s" "Bucket mlflows3:"
if docker exec mlflow-minio mc ls myminio/mlflows3 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
fi
echo ""

# Test de API
echo "🧪 Test de API de predicción:"
printf "%-20s" "POST /predict:"

# Hacer request de prueba
response=$(curl -s -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200
  }' 2>/dev/null)

if echo "$response" | grep -q "predictions"; then
    echo -e "${GREEN}✓ Working${NC}"
    echo "   Response: $(echo $response | jq -r '.predictions[0].prediction' 2>/dev/null || echo 'Parse error')"
else
    echo -e "${RED}✗ Failed${NC}"
    echo "   Response: $response"
fi
echo ""

# Resumen
echo "📊 Resumen:"
total_checks=12
passed_checks=$(grep -c "✓" /tmp/mlflow_test_$$.log 2>/dev/null || echo 0)

if [ "$total_checks" -eq "$passed_checks" ]; then
    echo -e "${GREEN}✅ Todos los servicios están funcionando correctamente${NC}"
else
    echo -e "${RED}⚠️  Algunos servicios no están funcionando correctamente${NC}"
    echo "   Revisa los logs con: docker-compose -f docker-compose.mlflow.yml logs"
fi

# Limpiar archivo temporal
rm -f /tmp/mlflow_test_$$.log


# Agregar verificación específica del bucket
echo "🪣 Verificando MinIO y Bucket:"
printf "%-20s" "MinIO Health:"
if docker exec mlflow-minio curl -f http://localhost:9000/minio/health/ready &>/dev/null; then
    echo -e "${GREEN}✔ Healthy${NC}"
else
    echo -e "${RED}✗ Not healthy${NC}"
fi

printf "%-20s" "Bucket mlflows3:"
if docker exec mlflow-minio mc ls myminio/mlflows3 &>/dev/null; then
    echo -e "${GREEN}✔ Exists${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "   Intentando crear bucket..."
    docker exec mlflow-minio mc mb myminio/mlflows3 --ignore-existing
    docker exec mlflow-minio mc anonymous set download myminio/mlflows3
fi
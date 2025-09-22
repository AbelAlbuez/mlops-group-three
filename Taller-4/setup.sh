#!/bin/bash
# Script de instalación automática para Taller MLflow

echo "🚀 Configurando Taller MLflow..."

# Crear estructura de directorios
echo "📁 Creando directorios..."
mkdir -p jupyter notebooks mlflow mysql api data/{raw,processed}

# Copiar archivo de entorno si no existe
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env..."
    cp .env.example .env
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

# Detectar versión de Docker Compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo "✅ Usando docker-compose (versión standalone)"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo "✅ Usando docker compose (plugin integrado)"
else
    echo "❌ Docker Compose no está instalado."
    exit 1
fi

echo ""
echo "🐳 Levantando todos los servicios..."
echo "   Esto tomará 2-3 minutos la primera vez..."
echo ""

# Levantar todos los servicios de una vez
$DOCKER_COMPOSE -f docker-compose.mlflow.yml up -d

# Mostrar progreso
echo -n "⏳ Esperando a que los servicios se inicialicen"

# Esperar 30 segundos mostrando progreso
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""

# Verificar MySQL específicamente
echo -n "🔍 Verificando MySQL"
for i in {1..30}; do
    if docker exec mlflow-mysql mysql -u root -proot123 -e "SELECT 1" >/dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 2
done

# Esperar a que MinIO esté listo
echo -n "🔍 Verificando MinIO"
for i in {1..30}; do
    if docker exec mlflow-minio curl -f http://localhost:9000/minio/health/ready &>/dev/null; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 2
done

# Verificar y crear bucket si es necesario
echo -n "🪣 Verificando bucket mlflows3"
sleep 5  # Dar tiempo extra para que MinIO esté completamente listo

# Intentar crear el bucket varias veces
for i in {1..5}; do
    if docker exec mlflow-minio mc config host add myminio http://localhost:9000 admin supersecret &>/dev/null; then
        if docker exec mlflow-minio mc mb myminio/mlflows3 --ignore-existing &>/dev/null; then
            docker exec mlflow-minio mc anonymous set download myminio/mlflows3 &>/dev/null
            echo " ✅"
            break
        fi
    fi
    echo -n "."
    sleep 3
done

# Verificar que el bucket existe
if ! docker exec mlflow-minio mc ls myminio/mlflows3 &>/dev/null; then
    echo ""
    echo "⚠️  Advertencia: El bucket mlflows3 no se pudo crear automáticamente."
    echo "   Intenta crearlo manualmente con:"
    echo "   docker exec mlflow-minio mc mb myminio/mlflows3"
    echo "   docker exec mlflow-minio mc anonymous set download myminio/mlflows3"
fi

# Reiniciar MLflow server para asegurar que ve el bucket
echo -n "🔄 Reiniciando MLflow server"
docker restart mlflow-server &>/dev/null
echo " ✅"

# Esperar un poco más para que todos los servicios estén listos
echo -n "⏳ Finalizando inicialización"
for i in {1..20}; do
    echo -n "."
    sleep 1
done
echo " ✅"

# Mostrar estado de servicios
echo ""
echo "📊 Estado de los servicios:"
$DOCKER_COMPOSE -f docker-compose.mlflow.yml ps

# Función simple para verificar servicios
check_service() {
    local name=$1
    local port=$2
    
    if nc -z localhost $port 2>/dev/null; then
        echo "✅ $name está funcionando en puerto $port"
        return 0
    else
        echo "⏳ $name iniciándose en puerto $port..."
        return 1
    fi
}

# Verificar servicios principales - PUERTOS ACTUALIZADOS
echo ""
echo "🔍 Verificando servicios..."
check_service "MySQL" 3306
check_service "MinIO API" 8006
check_service "MinIO Console" 8003
check_service "MLflow" 8001
check_service "JupyterLab" 8004
check_service "API" 8005

# Mostrar URLs de acceso - PUERTOS ACTUALIZADOS
echo ""
echo "✅ Instalación completada!"
echo ""
echo "🌐 URLs de acceso:"
echo "   - MinIO Console: http://localhost:8003 (admin/supersecret)"
echo "   - MLflow UI: http://localhost:8001"
echo "   - JupyterLab: http://localhost:8004 (token: mlflow2024)"
echo "   - API Docs: http://localhost:8005/docs"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Verifica que el bucket mlflows3 existe en MinIO Console"
echo "   2. Abre JupyterLab en http://localhost:8004"
echo "   3. Ejecuta el notebook experiments.ipynb"
echo "   4. Verifica los experimentos en MLflow UI"
echo ""
echo "💡 Comandos útiles:"
echo "   Ver logs: $DOCKER_COMPOSE -f docker-compose.mlflow.yml logs -f"
echo "   Ver logs de un servicio: docker logs -f <nombre-contenedor>"
echo "   Verificar servicios: ./test_services.sh"
echo "   Crear bucket manualmente: docker exec mlflow-minio mc mb myminio/mlflows3"
echo ""
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

# Esperar un poco más para que todos los servicios estén listos
echo -n "⏳ Finalizando inicialización"
for i in {1..30}; do
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

# Verificar servicios principales
echo ""
echo "🔍 Verificando servicios..."
check_service "MySQL" 3306
check_service "MinIO API" 9000
check_service "MinIO Console" 9001
check_service "MLflow" 5001
check_service "JupyterLab" 8888
check_service "API" 8000

# Mostrar URLs de acceso
echo ""
echo "✅ Instalación completada!"
echo ""
echo "🌐 URLs de acceso:"
echo "   - MinIO Console: http://localhost:9001 (admin/supersecret)"
echo "   - MLflow UI: http://localhost:5001"
echo "   - JupyterLab: http://localhost:8888 (token: mlflow2024)"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Espera 1-2 minutos adicionales si algún servicio muestra 'iniciándose'"
echo "   2. Abre JupyterLab en http://localhost:8888"
echo "   3. Ejecuta el notebook experiments.ipynb"
echo "   4. Verifica los experimentos en MLflow UI"
echo ""
echo "💡 Comandos útiles:"
echo "   Ver logs: $DOCKER_COMPOSE -f docker-compose.mlflow.yml logs -f"
echo "   Ver logs de un servicio: docker logs -f <nombre-contenedor>"
echo "   Verificar servicios: ./test_services.sh"
echo ""
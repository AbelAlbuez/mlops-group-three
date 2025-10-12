#!/bin/bash
# Script para cambiar recursos de la API sin editar archivos manualmente

set -e

CPU=${1:-0.5}
MEM=${2:-512M}

echo "🔧 Configurando recursos..."
echo "   CPU: $CPU"
echo "   RAM: $MEM"

# Actualizar env.locust
if [ -f "env.locust" ]; then
    sed -i.bak "s/API_CPU_LIMIT=.*/API_CPU_LIMIT=$CPU/" env.locust
    sed -i.bak "s/API_MEMORY_LIMIT=.*/API_MEMORY_LIMIT=$MEM/" env.locust
    echo "✅ Archivo env.locust actualizado"
fi

# Exportar variables de entorno
export API_CPU_LIMIT=$CPU
export API_MEMORY_LIMIT=$MEM

# Reiniciar API con nuevos recursos
echo "🔄 Reiniciando API con nuevos recursos..."
docker compose -f docker-compose.locust-minimal.yml up -d --force-recreate inference-api

echo "✅ Recursos actualizados"
echo "   Esperando que la API reinicie..."
sleep 10

# Verificar health
if curl -s http://localhost:8000/health >/dev/null; then
    echo "✅ API funcionando correctamente"
else
    echo "⚠️  API puede estar iniciándose, espera 20s más"
fi

echo ""
echo "Uso: ./set_resources.sh <CPU> <MEMORY>"
echo "Ejemplo: ./set_resources.sh 1.0 1G"

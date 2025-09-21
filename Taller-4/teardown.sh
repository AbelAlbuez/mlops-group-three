#!/bin/bash
# Script para limpiar el ambiente del Taller MLflow

echo "🧹 Limpiando ambiente del Taller MLflow..."
echo ""

# Preguntar confirmación
read -p "⚠️  ¿Estás seguro? Esto detendrá todos los servicios. [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado."
    exit 1
fi

# Detener servicios
echo "🛑 Deteniendo servicios..."
docker-compose -f docker-compose.mlflow.yml down

# Preguntar si eliminar volúmenes
echo ""
read -p "🗑️  ¿Eliminar también los volúmenes (datos)? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Eliminando volúmenes..."
    docker-compose -f docker-compose.mlflow.yml down -v
fi

# Preguntar si eliminar archivos locales
echo ""
read -p "📁 ¿Eliminar directorios locales (notebooks, data)? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Eliminando directorios locales..."
    rm -rf notebooks/*.ipynb data/raw/* data/processed/*
    echo "Directorios limpiados (estructura preservada)"
fi

echo ""
echo "✅ Limpieza completada"
echo ""

# Mostrar estado
echo "📊 Contenedores Docker restantes:"
docker ps -a | grep mlflow || echo "No hay contenedores del proyecto"

echo ""
echo "📊 Volúmenes Docker restantes:"
docker volume ls | grep mlflow || echo "No hay volúmenes del proyecto"

echo ""
echo "💡 Para reinstalar, ejecuta: ./setup.sh"
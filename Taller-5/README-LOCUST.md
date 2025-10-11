# Pruebas de Carga con Locust - Modelo Covertype

Este directorio contiene la configuración completa para realizar pruebas de carga del modelo de covertype utilizando Locust, Docker y Docker Compose.

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Arquitectura](#arquitectura)
- [Archivos del Proyecto](#archivos-del-proyecto)
- [Instalación y Configuración](#instalación-y-configuración)
- [Uso Rápido](#uso-rápido)
- [Configuraciones de Pruebas](#configuraciones-de-pruebas)
- [Resultados Esperados](#resultados-esperados)
- [Troubleshooting](#troubleshooting)
- [Comandos Avanzados](#comandos-avanzados)

## 🎯 Descripción General

Este sistema permite realizar pruebas de carga del modelo de covertype con diferentes configuraciones de recursos (CPU/RAM) y números de usuarios concurrentes. El modelo utiliza 12 features para predecir el tipo de cobertura forestal.

### Features del Modelo Covertype

1. **elevation** (int: 1800-3800) - Elevación en metros
2. **aspect** (int: 0-360) - Orientación en grados
3. **slope** (int: 0-65) - Pendiente en grados
4. **horizontal_distance_to_hydrology** (int: 0-1400) - Distancia horizontal a hidrología
5. **vertical_distance_to_hydrology** (int: -170-600) - Distancia vertical a hidrología
6. **horizontal_distance_to_roadways** (int: 0-7000) - Distancia horizontal a carreteras
7. **hillshade_9am** (int: 0-255) - Sombra a las 9am
8. **hillshade_noon** (int: 0-255) - Sombra al mediodía
9. **hillshade_3pm** (int: 0-255) - Sombra a las 3pm
10. **horizontal_distance_to_fire_points** (int: 0-7000) - Distancia horizontal a puntos de fuego
11. **wilderness_area** (int: 0-3) - Área silvestre
12. **soil_type** (int: 0-40) - Tipo de suelo

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Locust Master │    │  Locust Worker  │    │  Locust Worker  │
│   (Web UI:8089) │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Nginx Load Balancer  │
                    │         (Puerto 80)       │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    API de Inferencia      │
                    │   (ogaston/inference-g3)  │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │        MLflow             │
                    │      (Puerto 5002)        │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │        MySQL              │
                    │       (Puerto 3306)       │
                    └───────────────────────────┘
```

## 📁 Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `locustfile.py` | Configuración de Locust con tareas de usuario |
| `docker-compose.locust.yml` | Servicios completos para pruebas de carga |
| `docker-compose.inference-simple.yml` | Servicios básicos sin Locust |
| `run_load_tests.sh` | Script automatizado para ejecutar pruebas |
| `Makefile.locust` | Comandos Make para gestión de servicios |
| `env.locust` | Variables de entorno específicas para Locust |
| `nginx.conf` | Configuración de load balancer |
| `README-LOCUST.md` | Esta documentación |
| `INICIO-RAPIDO-LOCUST.md` | Guía de inicio rápido |

## 🚀 Instalación y Configuración

### Prerrequisitos

- Docker 20.10+
- Docker Compose 2.0+
- curl
- make (opcional)

### Verificar Dependencias

```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar curl
curl --version

# Verificar make (opcional)
make --version
```

### Instalación en macOS

```bash
# Instalar con Homebrew
brew install docker docker-compose curl make

# O usar el Makefile
make -f Makefile.locust install-deps
```

## ⚡ Uso Rápido

### 1. Inicio Rápido con Make

```bash
# Verificar dependencias
make -f Makefile.locust check-deps

# Iniciar servicios
make -f Makefile.locust up

# Ejecutar prueba rápida
make -f Makefile.locust test-quick

# Ver logs
make -f Makefile.locust logs

# Detener servicios
make -f Makefile.locust down
```

### 2. Inicio Rápido con Script

```bash
# Hacer ejecutable
chmod +x run_load_tests.sh

# Prueba rápida (500 usuarios, 5 minutos)
./run_load_tests.sh --quick

# Prueba media (2000 usuarios, 10 minutos)
./run_load_tests.sh --medium

# Todas las pruebas
./run_load_tests.sh --full
```

### 3. Inicio Manual

```bash
# Iniciar servicios
docker-compose -f docker-compose.locust.yml up -d

# Verificar estado
docker-compose -f docker-compose.locust.yml ps

# Acceder a la Web UI
open http://localhost:8089
```

## 🔧 Configuraciones de Pruebas

### Configuraciones de Recursos

| CPU | RAM | Descripción | Uso Recomendado |
|-----|-----|-------------|-----------------|
| 0.25 | 256M | Desarrollo | Pruebas básicas |
| 0.5 | 512M | Testing | Pruebas regulares |
| 1.0 | 1G | Producción | Carga media |
| 2.0 | 2G | Producción | Carga alta |

### Configuraciones de Usuarios

| Usuarios | Spawn Rate | Tiempo | Descripción |
|----------|------------|--------|-------------|
| 500 | 50/s | 5m | Prueba rápida |
| 2000 | 100/s | 10m | Prueba media |
| 5000 | 200/s | 15m | Prueba de carga |
| 10000 | 500/s | 20m | Prueba de estrés |

### Ejemplos de Uso

```bash
# Prueba específica con configuración personalizada
./run_load_tests.sh --config 0.5/512M

# Prueba con número específico de usuarios
./run_load_tests.sh --users 1000 --time 10m

# Prueba con configuración específica
make -f Makefile.locust test-05  # 0.5 CPU, 512M RAM
make -f Makefile.locust test-1   # 1.0 CPU, 1G RAM
```

## 📊 Resultados Esperados

### Métricas Importantes

- **RPS (Requests Per Second)**: Peticiones por segundo
- **Response Time**: Tiempo de respuesta promedio
- **95th Percentile**: 95% de las peticiones responden en este tiempo o menos
- **Error Rate**: Porcentaje de peticiones fallidas

### Resultados Típicos por Configuración

| Configuración | Usuarios | RPS Esperado | Response Time | Error Rate |
|---------------|----------|--------------|---------------|------------|
| 0.25/256M | 500 | 50-100 | 200-500ms | <1% |
| 0.5/512M | 2000 | 100-200 | 100-300ms | <1% |
| 1.0/1G | 5000 | 200-400 | 50-200ms | <1% |
| 2.0/2G | 10000 | 400-800 | 25-100ms | <1% |

### Archivos de Resultados

Los resultados se guardan en `load_test_results/`:

- `test_*_users_*_cpu_*_mem_*.csv` - Datos detallados en CSV
- `test_*_users_*_cpu_*_mem_*.html` - Reporte visual en HTML
- `consolidated_report.md` - Reporte consolidado

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Servicios no inician

```bash
# Verificar logs
docker-compose -f docker-compose.locust.yml logs

# Verificar puertos
netstat -an | grep -E "(3306|5002|8000|8089)"

# Limpiar y reiniciar
make -f Makefile.locust clean
make -f Makefile.locust up
```

#### 2. API no responde

```bash
# Verificar health check
curl http://localhost:8000/health

# Verificar logs de la API
docker-compose -f docker-compose.locust.yml logs inference-api

# Verificar recursos
docker stats
```

#### 3. Locust no conecta

```bash
# Verificar conectividad
docker-compose -f docker-compose.locust.yml exec locust-master ping inference-api

# Verificar configuración de red
docker network ls
docker network inspect locust-network
```

#### 4. Errores de memoria

```bash
# Verificar uso de memoria
docker stats

# Aumentar límites de memoria
export API_MEMORY_LIMIT=1G
docker-compose -f docker-compose.locust.yml up -d
```

### Comandos de Diagnóstico

```bash
# Estado general
make -f Makefile.locust status

# Información del sistema
make -f Makefile.locust info

# Logs específicos
make -f Makefile.locust logs-api
make -f Makefile.locust logs-locust
```

## 🚀 Comandos Avanzados

### Escalado de Workers

```bash
# Escalar a 2 workers
make -f Makefile.locust scale-2

# Escalar a 3 workers
make -f Makefile.locust scale-3

# Escalar a 5 workers
make -f Makefile.locust scale-5
```

### Pruebas Personalizadas

```bash
# Prueba con configuración específica
make -f Makefile.locust test-custom USERS=1500 TIME=15m

# Prueba con configuración de recursos específica
./run_load_tests.sh --config 1.5/1.5G --users 3000 --time 12m
```

### Monitoreo en Tiempo Real

```bash
# Ver estadísticas en tiempo real
make -f Makefile.locust stats

# Ver logs en tiempo real
make -f Makefile.locust logs

# Ver logs específicos
make -f Makefile.locust logs-api
```

### Limpieza

```bash
# Limpiar contenedores y volúmenes
make -f Makefile.locust clean

# Limpiar solo resultados
make -f Makefile.locust clean-results

# Limpiar todo incluyendo imágenes
docker system prune -a
```

## 📈 Interpretación de Resultados

### Archivos CSV

Los archivos CSV contienen las siguientes columnas:

- `Timestamp`: Marca de tiempo
- `Name`: Nombre de la tarea
- `Request Count`: Número de peticiones
- `Failure Count`: Número de fallos
- `Median Response Time`: Tiempo de respuesta mediano
- `Average Response Time`: Tiempo de respuesta promedio
- `Min Response Time`: Tiempo de respuesta mínimo
- `Max Response Time`: Tiempo de respuesta máximo
- `Average Content Size`: Tamaño promedio del contenido
- `Requests/s`: Peticiones por segundo

### Archivos HTML

Los archivos HTML contienen:

- Gráficos de rendimiento
- Tablas de estadísticas
- Distribución de tiempos de respuesta
- Análisis de errores

## 🔒 Consideraciones de Seguridad

- Los contenedores se ejecutan en una red aislada
- No se exponen puertos innecesarios
- Se utilizan health checks para verificar el estado
- Los logs no contienen información sensible

## 📝 Notas Adicionales

- El modelo utiliza la imagen `ogaston/inference-g3:latest`
- MLflow se ejecuta en el puerto 5002 para evitar conflictos
- Los resultados se guardan automáticamente
- Se puede ejecutar en modo headless o con Web UI
- Soporte para múltiples workers de Locust

## 🤝 Soporte

Para problemas o preguntas:

1. Revisar la sección de Troubleshooting
2. Verificar los logs con `make -f Makefile.locust logs`
3. Consultar la documentación de Locust
4. Revisar la configuración de Docker

---

**Última actualización**: $(date)
**Versión**: 1.0.0
**Autor**: Equipo MLOPS

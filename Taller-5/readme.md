# 🚀 Taller 5 - Pruebas de Carga con Locust

## 📋 Descripción

Taller de MLOps enfocado en realizar **pruebas de carga** a una API de inferencia del modelo **Covertype Classification** utilizando Locust, Docker y herramientas de monitoreo.

**Objetivo principal**: Encontrar los recursos mínimos (CPU/RAM) que soporten **10,000 usuarios concurrentes** con incrementos de 500 usuarios.

---

## 🎯 Objetivos del Taller

1. ✅ **Imagen publicada**: `ogaston/inference-g3:latest` en DockerHub
2. ✅ **Sistema simplificado**: 2 scripts principales (start_all.sh + stop_all.sh)
3. ✅ **Pruebas desde UI**: Todo se configura desde Locust Web UI
4. ⭐ **Limitar recursos**: CPU y RAM ajustables
5. ⭐ **Escalar con réplicas**: Múltiples instancias de la API
6. ⭐ **Documentar resultados**: Tablas, gráficos y análisis

---

## 🐳 Imagen Docker

### Imagen Publicada en DockerHub

✅ **Imagen**: `ogaston/inference-g3:latest`  
🔗 **URL**: https://hub.docker.com/r/ogaston/inference-g3

**Características de la imagen:**
- **Modelo**: Covertype Classification (12 features)
- **Framework**: FastAPI + scikit-learn
- **Puerto**: 8000
- **Health Check**: `/health`
- **API Docs**: `/docs` (Swagger UI)
- **Arquitecturas**: AMD64, ARM64

**Uso:**

Para subir toda la infraestructura de la API:

```bash
docker compose up -d --buld
```

---

## 📁 Estructura del Proyecto

```
Taller-5/
├── start_all.sh                        # ⭐ Script principal de inicio
├── stop_all.sh                         # ⭐ Script de detención
├── docker-compose.yaml                 # Compose principal (Sistema base)
├── docker-compose.locust-official.yml  # Compose para Locust
├── .env                                # Variables de entorno
├── locustfile.py                       # Configuración de pruebas Locust
├── app/
│   └── train_standalone.py            # Script de entrenamiento
├── mysql/
│   └── init/
│       └── 01-create-schema.sql       # Schema de BD
└── README-SIMPLE.md                    # Guía rápida
```

**Archivos opcionales** (útiles pero no esenciales):
- `set_resources.sh` - Cambiar recursos dinámicamente
- `nginx.conf` - Load balancer para múltiples réplicas
- `.env.sample` - Ejemplo de configuración

---

## 🔧 Requisitos Previos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **curl** (para health checks)
- **8GB RAM** mínimo
- **10GB** espacio en disco

### Verificar instalación:
```bash
docker --version
docker compose version
curl --version
```

---

## ⚡ Inicio Rápido (3 pasos)

### 1️⃣ Iniciar servicios
```bash
# Dar permisos de ejecución (solo primera vez)
chmod +x start_all.sh stop_all.sh

# Iniciar servicios con configuración por defecto (medium)
./start_all.sh

# O con configuración específica
./start_all.sh quick    # 0.5 CPU, 512M RAM
./start_all.sh medium   # 1.0 CPU, 1G RAM (default)
./start_all.sh load     # 2.0 CPU, 2G RAM
./start_all.sh stress   # 4.0 CPU, 4G RAM
```

### 2️⃣ Acceder a Locust UI
Abre tu navegador en: **http://localhost:8089**

### 3️⃣ Configurar y ejecutar prueba
En la UI de Locust:
- **Number of users**: 2000 (según configuración elegida)
- **Spawn rate**: 100 usuarios/segundo
- **Host**: http://inference-api:8000 (ya configurado)
- Click en **"Start swarming"** 🚀

---

## 📊 Configuraciones Disponibles

| Configuración | CPU | RAM | Usuarios Recomendados | Uso |
|---------------|-----|-----|-----------------------|-----|
| **quick** | 0.5 | 512M | 500 | Desarrollo/Pruebas rápidas |
| **medium** | 1.0 | 1G | 2,000 | Testing (default) |
| **load** | 2.0 | 2G | 5,000 | Pre-producción |
| **stress** | 4.0 | 4G | 10,000 | Producción/Estrés |

---

## 🎯 Flujo de Trabajo del Taller

### Paso 1: Configuración Inicial

```bash
# 1. Iniciar con configuración base
./start_all.sh medium

# 2. Verificar que todo funciona
curl http://localhost:8000/health

# 3. Abrir Locust UI
open http://localhost:8089
```

### Paso 2: Ejecutar Pruebas Incrementales

```bash
# En la UI de Locust (http://localhost:8089):

# Prueba 1: 100 usuarios
Number of users: 100
Spawn rate: 10
Click "Start swarming"
→ Observar: RPS, latencia, errores

# Prueba 2: 500 usuarios
Click "Stop" → Cambiar a 500 users → "Start swarming"
→ Anotar resultados

# Prueba 3: 1000 usuarios
→ Continuar incrementando...

# Prueba 4: 2000 usuarios
→ Documentar cuando empiecen a aparecer errores
```

### Paso 3: Ajustar Recursos si es Necesario

```bash
# Si la API no soporta la carga actual:

# 1. Detener servicios
./stop_all.sh

# 2. Iniciar con más recursos
./start_all.sh load  # 2 CPU, 2GB RAM

# 3. Repetir pruebas
open http://localhost:8089
```

### Paso 4: Encontrar Configuración Óptima

Repetir hasta encontrar el mínimo de recursos que soporten 10,000 usuarios con:
- ✅ **Failures < 1%**
- ✅ **P95 Latency < 1s**
- ✅ **CPU < 90%**
- ✅ **RAM < 90%**

### Paso 5: Documentar Resultados

Crear tabla con tus hallazgos:

| CPU | RAM | Users | RPS | P95 (ms) | Failures | Resultado |
|-----|-----|-------|-----|----------|----------|-----------|

---

## 🛠️ Comandos Útiles

### Scripts Principales

```bash
# Iniciar servicios
./start_all.sh [quick|medium|load|stress]

# Ver estado actual
./start_all.sh --status

# Ver logs en tiempo real
./start_all.sh --logs

# Detener servicios
./stop_all.sh

# Detener y limpiar contenedores
./stop_all.sh --clean

# Limpieza completa
./stop_all.sh --all
```

### Comandos Docker Compose

```bash
# Ver estado de contenedores
docker compose -f docker-compose.locust-official.yml ps

# Ver logs
docker compose -f docker-compose.locust-official.yml logs -f

# Ver logs de un servicio específico
docker logs inference-api
docker logs locust-master-official

# Ver estadísticas de recursos
docker stats
```

### Health Checks

```bash
# Verificar API
curl http://localhost:8000/health

# Verificar Locust
curl http://localhost:8089

# Hacer predicción de prueba
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "elevation": 2500,
    "aspect": 180,
    "slope": 15,
    "horizontal_distance_to_hydrology": 200,
    "vertical_distance_to_hydrology": 50,
    "horizontal_distance_to_roadways": 1000,
    "hillshade_9am": 200,
    "hillshade_noon": 230,
    "hillshade_3pm": 150,
    "horizontal_distance_to_fire_points": 800,
    "wilderness_area": 1,
    "soil_type": 10
  }'
```

---

## 🔀 Escalamiento con Réplicas

Para probar con múltiples instancias de la API:

```bash
# Escalar a 3 réplicas
docker compose -f docker-compose.locust-official.yml up -d --scale inference-api=3

# Verificar réplicas
docker ps | grep inference-api

# Nota: Esto distribuye la carga automáticamente entre las réplicas
```

---

## 📈 Monitoreo en Tiempo Real

### Desde Locust UI (http://localhost:8089)

- **Statistics**: Tabla con RPS, latencias, errores
- **Charts**: Gráficos de RPS y tiempos de respuesta
- **Failures**: Detalle de errores
- **Exceptions**: Excepciones capturadas
- **Download Data**: Descargar reportes CSV/HTML

### Desde Docker Stats

```bash
# Ver uso de recursos de todos los contenedores
docker stats

# Solo la API
docker stats inference-api
```

---

## 📁 Guardar Resultados

### Desde Locust UI

1. Durante o después de la prueba, ir a http://localhost:8089
2. Click en **"Download Data"** en el menú superior
3. Seleccionar **"Download Report"** para HTML
4. O **"Download Request statistics CSV"** para datos

### Screenshots Importantes

Captura pantallas de:
- Tabla de Statistics con RPS y latencias
- Gráficos de Charts (Total RPS y Response Times)
- Docker stats mostrando uso de CPU/RAM
- Configuración de recursos usada

---

## 🐛 Troubleshooting

### Servicios no inician

```bash
# Ver logs completos
docker compose -f docker-compose.locust-official.yml logs

# Verificar puertos en uso
lsof -i :8000
lsof -i :8089

# Limpiar y reiniciar
./stop_all.sh --all
./start_all.sh
```

### API no responde

```bash
# Health check detallado
curl -v http://localhost:8000/health

# Ver logs de la API
docker logs inference-api

# Reiniciar solo la API
docker restart inference-api
```

### Puerto 8089 en uso

```bash
# Ver qué está usando el puerto
lsof -i :8089

# Matar proceso si es necesario
kill -9 <PID>

# O cambiar puerto en docker-compose.locust-official.yml
```

### Locust no conecta a la API

```bash
# Verificar que ambos están en la misma red
docker network inspect taller-5_default

# Si la red no existe, crearla
docker network create taller-5_default

# Reiniciar servicios
./stop_all.sh
./start_all.sh
```

---

## 🧹 Limpieza

### Detener servicios (mantiene contenedores)

```bash
./stop_all.sh
```

### Limpiar contenedores

```bash
./stop_all.sh --clean
```

### Limpieza completa (todo)

```bash
./stop_all.sh --all
```

### Limpiar sistema Docker

```bash
# Limpiar contenedores detenidos
docker container prune -f

# Limpiar imágenes no usadas
docker image prune -a -f

# Limpiar volúmenes
docker volume prune -f

# Limpieza completa del sistema
docker system prune -a --volumes -f
```

---

## 🔗 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Locust UI** | http://localhost:8089 | 🎯 Interfaz principal de pruebas |
| **API** | http://localhost:8000 | API de inferencia |
| **API Health** | http://localhost:8000/health | Health check |
| **API Docs** | http://localhost:8000/docs | Swagger UI |

---

## 📊 Ejemplo de Payload para Pruebas Manuales

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "elevation": 2500,
    "aspect": 180,
    "slope": 15,
    "horizontal_distance_to_hydrology": 200,
    "vertical_distance_to_hydrology": 50,
    "horizontal_distance_to_roadways": 1000,
    "hillshade_9am": 200,
    "hillshade_noon": 230,
    "hillshade_3pm": 150,
    "horizontal_distance_to_fire_points": 800,
    "wilderness_area": 1,
    "soil_type": 10
  }'
```

Respuesta esperada:
```json
{
  "prediction": 3,
  "confidence": 0.95,
  "model_version": "1.0.0"
}
```

---

## 👥 Equipo

- **Grupo 3**: Abel Albuez Sanchez, Omar Gaston Chalas, Mauricio Morales
- **Imagen Docker**: ogaston/inference-g3:latest
- **Modelo**: Covertype Classification (12 features)

---

## 📄 Licencia

Este proyecto es parte del curso de MLOps - 2024

---

## ✅ Checklist de Validación

Antes de entregar el taller, verifica:

- [ ] Imagen publicada en DockerHub
- [ ] Scripts funcionan correctamente (`start_all.sh`, `stop_all.sh`)
- [ ] Locust UI accesible en http://localhost:8089
- [ ] API responde en http://localhost:8000/health
- [ ] Pruebas ejecutadas con diferentes configuraciones
- [ ] Resultados documentados (screenshots + tabla)
- [ ] Tabla de resultados completa (CPU, RAM, Users, RPS, Latencia, Errores)
- [ ] Análisis de 1 vs múltiples instancias (opcional)
- [ ] Screenshots de evidencia
- [ ] Reporte final escrito

---

## 🆘 Soporte

Para problemas:

1. Revisar sección de **Troubleshooting**
2. Ver logs: `./start_all.sh --logs`
3. Verificar estado: `./start_all.sh --status`
4. Consultar **README-SIMPLE.md** para guía rápida

---

## 💡 Tips para el Éxito

1. **Empieza con `quick`**: Prueba con recursos mínimos primero
2. **Incrementa gradualmente**: 100 → 500 → 1000 → 2000 → 5000 → 10000 usuarios
3. **Documenta todo**: Toma screenshots en cada paso
4. **Observa las métricas**: RPS, latencia P95, % errores, uso CPU/RAM
5. **Descarga reportes**: Usa "Download Report" en Locust UI
6. **Limpia entre pruebas**: `./stop_all.sh --clean` antes de cambiar recursos

**¡Éxito en el taller! 🚀**
# 🚀 Taller 5 - Pruebas de Carga con Locust

## 📋 Descripción

Taller de MLOps enfocado en realizar **pruebas de carga** a una API de inferencia del modelo **Covertype Classification** utilizando Locust, Docker y herramientas de monitoreo.

**Objetivo principal**: Encontrar los recursos mínimos (CPU/RAM) que soporten **10,000 usuarios concurrentes** con incrementos de 500 usuarios.

---

## 🎯 Objetivos del Taller

1. ✅ **Imagen publicada**: `ogaston/inference-g3:latest` en DockerHub
2. ✅ **Docker Compose simple**: Para inferencia básica sin Locust
3. ✅ **Docker Compose con Locust**: Para pruebas de carga
4. ⭐ **Limitar recursos**: CPU y RAM ajustables
5. ⭐ **Escalar con réplicas**: Múltiples instancias de la API
6. ⭐ **Documentar resultados**: Tablas, gráficos y análisis

---

## 📁 Estructura del Proyecto

```
Taller-5/
├── docker-compose.yaml                  # Compose principal (NO modificar)
├── docker-compose.locust.yml            # ✨ Compose para Locust
├── docker-compose.inference-simple.yml  # ✨ Compose simple
├── .env                                 # Variables originales (NO modificar)
├── env.locust                          # ✨ Variables para Locust
├── locustfile.py                       # ✨ Configuración de pruebas
├── nginx.conf                          # ✨ Load balancer
├── run_load_tests.sh                   # ✨ Script automatizado
├── Makefile.locust                     # ✨ Comandos útiles
├── Dockerfile.inference                # Dockerfile de la API
├── README-LOCUST.md                    # Documentación detallada
├── INICIO-RAPIDO-LOCUST.md            # Guía rápida
├── app/
│   └── train_standalone.py            # Script de entrenamiento
├── api/
│   ├── main.py                        # API FastAPI
│   └── requirements.txt               # Dependencias
├── mysql/
│   └── init/
│       └── 01-create-schema.sql       # Schema de BD
└── load_test_results/                 # Resultados de pruebas
```

---

## 🔧 Requisitos Previos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **curl** (para health checks)
- **make** (opcional, para comandos simplificados)
- **8GB RAM** mínimo
- **10GB** espacio en disco

### Verificar instalación:
```bash
docker --version
docker compose version
curl --version
make --version  # opcional
```

---

## ⚡ Inicio Rápido (3 pasos)

### 1️⃣ Iniciar servicios con Locust
```bash
# Opción A: Con Make (recomendado)
make -f Makefile.locust up

# Opción B: Con Docker Compose
docker compose -f docker-compose.locust.yml up -d
```

### 2️⃣ Verificar que todo está funcionando
```bash
# Health check de la API
curl http://localhost:8000/health

# Ver estado de contenedores
docker compose -f docker-compose.locust.yml ps

# Ver logs en tiempo real
docker compose -f docker-compose.locust.yml logs -f
```

### 3️⃣ Acceder a Locust UI
Abre tu navegador en: **http://localhost:8089**

Configuración inicial:
- **Number of users**: 100
- **Spawn rate**: 10
- **Host**: http://inference-api:8000 (ya configurado)

Click en **"Start swarming"** 🚀

---

## 🎮 Uso con Make (Simplificado)

El `Makefile.locust` proporciona comandos simples:

```bash
# Ver todos los comandos disponibles
make -f Makefile.locust help

# Gestión básica
make -f Makefile.locust up          # Iniciar servicios
make -f Makefile.locust down        # Detener servicios
make -f Makefile.locust restart     # Reiniciar servicios
make -f Makefile.locust logs        # Ver logs
make -f Makefile.locust stats       # Ver estadísticas
make -f Makefile.locust status      # Verificar estado

# Pruebas rápidas
make -f Makefile.locust test-quick   # 500 usuarios, 5 min
make -f Makefile.locust test-medium  # 2000 usuarios, 10 min
make -f Makefile.locust test-load    # Todas las pruebas

# Pruebas con configuraciones específicas
make -f Makefile.locust test-025    # 0.25 CPU, 256M RAM
make -f Makefile.locust test-05     # 0.5 CPU, 512M RAM
make -f Makefile.locust test-1      # 1.0 CPU, 1G RAM
make -f Makefile.locust test-2      # 2.0 CPU, 2G RAM

# Escalado de workers
make -f Makefile.locust scale-2     # 2 workers
make -f Makefile.locust scale-3     # 3 workers
make -f Makefile.locust scale-5     # 5 workers

# Limpieza
make -f Makefile.locust clean       # Limpiar todo
```

---

## 🧪 Pruebas de Carga

### Método 1: UI Web de Locust

1. Iniciar servicios: `make -f Makefile.locust up`
2. Abrir: http://localhost:8089
3. Configurar usuarios y spawn rate
4. Click en "Start swarming"
5. Monitorear en tiempo real

### Método 2: Script Automatizado

```bash
# Dar permisos de ejecución
chmod +x run_load_tests.sh

# Prueba rápida
./run_load_tests.sh --quick

# Prueba media
./run_load_tests.sh --medium

# Todas las pruebas
./run_load_tests.sh --full

# Configuración específica
./run_load_tests.sh --config 0.5/512M

# Personalizada
./run_load_tests.sh --users 1000 --time 10m
```

### Método 3: Locust Headless

```bash
docker compose -f docker-compose.locust.yml exec locust-master locust \
  --locustfile=/mnt/locust/locustfile.py \
  --host=http://inference-api:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --headless
```

---

## 🔧 Configuración de Recursos

### Editar límites en `docker-compose.locust.yml`:

```yaml
inference-api:
  deploy:
    resources:
      limits:
        cpus: '0.5'      # Cambiar aquí
        memory: 512M     # Cambiar aquí
```

### O usar variables de entorno en `env.locust`:

```bash
# Editar archivo
nano env.locust

# Cambiar estos valores
API_CPU_LIMIT=0.5
API_MEMORY_LIMIT=512M
```

### Reiniciar con nueva configuración:

```bash
make -f Makefile.locust restart
```

---

## 📊 Configuraciones Recomendadas

| Escenario | CPU | RAM | Usuarios Max | Uso |
|-----------|-----|-----|--------------|-----|
| Desarrollo | 0.25 | 256M | 500 | Pruebas locales |
| Testing | 0.5 | 512M | 2,000 | CI/CD |
| Pre-producción | 1.0 | 1G | 5,000 | Staging |
| Producción | 2.0 | 2G | 10,000+ | Prod |

---

## 🎯 Flujo de Trabajo del Taller

### Paso 1: Configuración Base (0.5 CPU, 512M RAM)

```bash
# 1. Iniciar servicios
make -f Makefile.locust up

# 2. Verificar health
curl http://localhost:8000/health

# 3. Prueba con 100 usuarios (UI)
open http://localhost:8089
```

### Paso 2: Incrementar usuarios gradualmente

```
100 usuarios   → ✅ OK
500 usuarios   → ✅ OK
1000 usuarios  → ✅ OK
2000 usuarios  → ⚠️  Latencia alta
5000 usuarios  → ❌ Failures > 5%
```

### Paso 3: Ajustar recursos

```bash
# Editar docker-compose.locust.yml
cpus: '1.0'
memory: 1G

# Reiniciar
make -f Makefile.locust restart

# Probar de nuevo con 5000 usuarios
```

### Paso 4: Encontrar configuración óptima

Repetir hasta encontrar el mínimo de recursos que soporten 10,000 usuarios con:
- ✅ Failures < 1%
- ✅ P95 Latency < 1s
- ✅ CPU < 90%
- ✅ RAM < 90%

### Paso 5: Documentar resultados

Completar tabla en `REPORTE.md`:

| CPU | RAM | Users | RPS | P95 (ms) | Failures | Resultado |
|-----|-----|-------|-----|----------|----------|-----------|
| 0.5 | 512M | 2000 | 200 | 800 | 0.5% | ⚠️ Límite |
| 1.0 | 1G | 5000 | 500 | 600 | 0.8% | ✅ OK |
| 2.0 | 2G | 10000 | 1000 | 400 | 0.5% | ✅ OK |

---

## 🔀 Escalamiento con Réplicas

### Método 1: Docker Compose Scale

```bash
# Escalar a 3 instancias
docker compose -f docker-compose.locust.yml up -d --scale inference-api=3

# Verificar
docker ps | grep inference-api

# O con Make
make -f Makefile.locust scale-3
```

### Método 2: Con Nginx Load Balancer

El archivo `nginx.conf` ya está configurado para balancear entre 3 réplicas.

```bash
# Nginx ya está en docker-compose.locust.yml
# Automáticamente distribuye la carga

# Ver logs de Nginx
docker logs nginx-locust
```

---

## 📈 Monitoreo en Tiempo Real

### Ver estadísticas de Docker:

```bash
# Estadísticas generales
docker stats

# Solo API de inferencia
docker stats inference-api-locust

# O con Make
make -f Makefile.locust stats
```

### Ver logs:

```bash
# Todos los logs
make -f Makefile.locust logs

# Solo API
make -f Makefile.locust logs-api

# Solo Locust
make -f Makefile.locust logs-locust
```

### Métricas de Locust:

- **UI Web**: http://localhost:8089
- **Gráficos en tiempo real**: Total RPS, Response times, Failures
- **Tablas**: Requests, Failures, Statistics

---

## 📁 Resultados de Pruebas

Los resultados se guardan automáticamente en `load_test_results/`:

```bash
load_test_results/
├── test_500users_0.5cpu_512Mmem_5m_stats.csv    # Datos CSV
├── test_500users_0.5cpu_512Mmem_5m.html         # Reporte HTML
└── consolidated_report.md                        # Reporte consolidado
```

### Interpretar archivos CSV:

- **Request Count**: Total de peticiones
- **Failure Count**: Peticiones fallidas
- **Median Response Time**: Tiempo de respuesta mediano
- **95th Percentile**: 95% de respuestas en este tiempo
- **Requests/s**: RPS promedio

### Ver resultados:

```bash
# Listar archivos
ls -lh load_test_results/

# Ver reporte consolidado
cat load_test_results/consolidated_report.md

# Abrir HTML en navegador
open load_test_results/*.html
```

---

## 🐛 Troubleshooting

### Servicios no inician

```bash
# Ver logs completos
docker compose -f docker-compose.locust.yml logs

# Verificar puertos en uso
lsof -i :8000
lsof -i :8089
lsof -i :5002

# Limpiar y reiniciar
make -f Makefile.locust clean
make -f Makefile.locust up
```

### API no responde

```bash
# Health check
curl -v http://localhost:8000/health

# Logs de la API
docker logs inference-api-locust

# Reiniciar solo la API
docker restart inference-api-locust
```

### Locust no conecta a la API

```bash
# Verificar red
docker network inspect locust-network

# Verificar DNS interno
docker compose -f docker-compose.locust.yml exec locust-master ping inference-api

# Ver logs de Locust
docker logs locust-master
```

### Errores de memoria/CPU

```bash
# Ver uso actual
docker stats

# Aumentar límites
# Editar docker-compose.locust.yml:
cpus: '2.0'
memory: 2G

# Reiniciar
make -f Makefile.locust restart
```

### Puerto 8089 en uso

```bash
# Ver qué lo usa
lsof -i :8089

# Cambiar puerto en docker-compose.locust.yml:
ports:
  - "8090:8089"
```

---

## 📚 Archivos de Documentación

- **README.md** (este archivo): Guía completa del taller
- **README-LOCUST.md**: Documentación técnica detallada
- **INICIO-RAPIDO-LOCUST.md**: Comandos esenciales y guía rápida

---

## 🎓 Preguntas del Taller

### 1. ¿Es posible reducir más los recursos?

**Respuesta**: Depende del modelo:
- Modelo simple (sklearn): Hasta 0.25 CPU + 256MB
- Modelo complejo (deep learning): Mínimo 1 CPU + 1GB

### 2. ¿Cuál es la mayor cantidad de peticiones soportadas?

**Respuesta típica**:
- 1 instancia (2 CPU, 2GB): ~1,000 RPS
- 3 instancias (0.75 CPU, 768MB c/u): ~3,000 RPS
- Límite: Depende del hardware del host

### 3. ¿Qué diferencia hay entre 1 o múltiples instancias?

| Aspecto | 1 Instancia | 3 Instancias |
|---------|-------------|--------------|
| **Throughput** | Menor | Mayor |
| **Latencia** | Mayor bajo carga | Menor |
| **Disponibilidad** | Sin redundancia | Alta disponibilidad |
| **Escalabilidad** | Vertical (más recursos) | Horizontal (más instancias) |
| **Costo** | Más recursos por instancia | Recursos distribuidos |

---

## 🧹 Limpieza

### Detener servicios:

```bash
make -f Makefile.locust down
```

### Limpiar contenedores y volúmenes:

```bash
make -f Makefile.locust clean
```

### Limpiar solo resultados:

```bash
make -f Makefile.locust clean-results
```

### Limpieza completa del sistema:

```bash
docker system prune -a --volumes
```

---

## 🔗 URLs de Acceso

Una vez iniciados los servicios:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Locust UI** | http://localhost:8089 | Interfaz de pruebas |
| **API** | http://localhost:8000 | API de inferencia |
| **API Health** | http://localhost:8000/health | Health check |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **MLflow** | http://localhost:5002 | Tracking UI |
| **MySQL** | localhost:3306 | Base de datos |
| **Nginx** | http://localhost:80 | Load balancer |

---

## 📊 Ejemplo de Payload

Para hacer predicciones manuales:

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
- [ ] Docker Compose funciona correctamente
- [ ] Locust UI accesible en http://localhost:8089
- [ ] API responde en http://localhost:8000/health
- [ ] Pruebas ejecutadas con diferentes configuraciones
- [ ] Resultados documentados en `load_test_results/`
- [ ] Tabla de resultados completa
- [ ] Análisis de 1 vs múltiples instancias
- [ ] Screenshots de evidencia
- [ ] Reporte final escrito

---

## 🆘 Soporte

Para problemas:

1. Revisar sección de **Troubleshooting**
2. Ver logs: `make -f Makefile.locust logs`
3. Consultar **README-LOCUST.md** para detalles técnicos
4. Revisar **INICIO-RAPIDO-LOCUST.md** para comandos básicos

---
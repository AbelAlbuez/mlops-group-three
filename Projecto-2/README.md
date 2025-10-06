# 🌲 MLOps Proyecto 2 - Covertype Classification

**Pontificia Universidad Javeriana - MLOps**  
**Grupo 3**: Abel Albuez Sanchez, Omar Gaston Chalas, Mauricio Morales

## 📋 Descripción del Proyecto

Sistema completo de MLOps para clasificación de tipos de cobertura forestal que incluye:

- **Orquestación**: Apache Airflow para automatización de pipelines
- **Tracking**: MLflow para experimentos y modelos
- **Almacenamiento**: MySQL para datos y MinIO para artifacts
- **Inferencia**: FastAPI para servir predicciones
- **Visualización**: Streamlit para interfaz de usuario (BONO)

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Airflow       │    │   MLflow        │    │   MinIO         │
│   (Orquestación)│    │   (Tracking)    │    │   (Artifacts)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MySQL         │    │   FastAPI       │    │   Streamlit     │
│   (Datos)       │    │   (Inferencia)  │    │   (UI - BONO)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Docker y Docker Compose
- Git
- Navegador web

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd mlops-group-three/Projecto-2
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW_GID=0
FERNET_KEY=your-fernet-key-here
AIRFLOW_SECRET_KEY=your-secret-key-here
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin123
AIRFLOW_ADMIN_EMAIL=admin@example.com

# PostgreSQL Configuration
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

# MySQL Configuration (Covertype)
MYSQL_ROOT_PASSWORD=root_pass
MYSQL_DATABASE=covertype_db
MYSQL_USER=covertype_user
MYSQL_PASSWORD=covertype_pass123
MYSQL_HOST=mysql-db
MYSQL_PORT=3306

# Project Configuration
P2_API_BASE=http://api
P2_GROUP_ID=3
P2_API_PATH=/data
P2_TARGET_COL=cover_type
P2_SCHEDULE_CRON=*/5 * * * *
P2_DATA_DIR=/tmp/airflow_data
P2_RANDOM_STATE=42
P2_TEST_SIZE=0.2
P2_MIN_SAMPLE_INCREMENT=100

# MLflow Configuration
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MLFLOW_BACKEND_URI=mysql+pymysql://mlflow:mlflow@mlflow-db:3306/mlflow
```

### 3. Iniciar el Sistema

```bash
# Construir e iniciar todos los servicios
docker-compose up -d

# Verificar estado de servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f
```

### 4. Verificar Instalación

```bash
# Ejecutar script de validación
./validate_system.sh
```

## 🔧 Servicios del Sistema

### 1. Apache Airflow (Puerto 8080)
- **URL**: http://localhost:8080
- **Credenciales**: admin / admin123
- **Función**: Orquestación de pipelines ML
- **DAG**: `p2_covertype_pipeline` (ejecuta cada 5 minutos)

### 2. MLflow (Puerto 5000)
- **URL**: http://localhost:5000
- **Función**: Tracking de experimentos y modelos
- **Experimento**: `covertype_classification`
- **Modelo**: `covertype_classifier`

### 3. MinIO (Puerto 9001)
- **URL**: http://localhost:9001
- **Credenciales**: minioadmin / minioadmin
- **Función**: Almacenamiento de artifacts
- **Bucket**: `mlflow`

### 4. FastAPI Inference (Puerto 8000)
- **URL**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Función**: Servir predicciones del modelo

### 5. Streamlit UI (Puerto 8503) - BONO
- **URL**: http://localhost:8503
- **Función**: Interfaz gráfica para usuarios
- **Características**: Predicción, monitoreo, control

## 📊 Uso del Sistema

### 1. Ejecutar Pipeline ML

1. Acceder a Airflow UI: http://localhost:8080
2. Buscar DAG: `p2_covertype_pipeline`
3. Activar el DAG (toggle ON)
4. Ejecutar manualmente o esperar ejecución automática (cada 5 minutos)

### 2. Monitorear Experimentos

1. Acceder a MLflow UI: http://localhost:5000
2. Ver experimento: `covertype_classification`
3. Revisar runs, métricas y artifacts
4. Verificar modelo registrado: `covertype_classifier`

### 3. Realizar Predicciones

#### Via API REST:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
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
```

#### Via Streamlit UI:
1. Acceder a: http://localhost:8503
2. Tab "🔮 Predicción"
3. Ingresar características del terreno
4. Click en "🔮 Predecir"

### 4. Monitorear Sistema

#### Via Streamlit UI:
1. Tab "📊 Monitoreo": Ver gráficas de métricas
2. Tab "⚙️ Control": Verificar estado de servicios

#### Via Script de Validación:
```bash
./validate_system.sh
```

## 🔍 Estructura del Proyecto

```
Projecto-2/
├── airflow/
│   ├── dags/
│   │   └── p2_covertype_pipeline.py    # DAG principal
│   ├── requirements.txt                # Dependencias Airflow
│   └── Dockerfile                      # Imagen custom Airflow
├── inference/
│   ├── main.py                         # API FastAPI
│   ├── requirements.txt                # Dependencias API
│   └── Dockerfile                      # Imagen API
├── streamlit/
│   ├── app.py                          # App Streamlit
│   ├── requirements.txt                # Dependencias Streamlit
│   └── Dockerfile                      # Imagen Streamlit
├── api/
│   └── main.py                         # API de datos externa
├── mysql/
│   └── init/
│       └── 01-create-schema.sql        # Esquema MySQL
├── docker-compose.yml                  # Configuración servicios
├── validate_system.sh                  # Script de validación
└── README.md                           # Este archivo
```

## 🐛 Troubleshooting

### Problemas Comunes

#### 1. Servicios no inician
```bash
# Verificar logs
docker-compose logs [servicio]

# Reiniciar servicios
docker-compose restart [servicio]

# Reconstruir imágenes
docker-compose build [servicio]
```

#### 2. Error de conexión a base de datos
```bash
# Verificar que MySQL esté corriendo
docker-compose ps mysql-db

# Verificar conectividad
docker-compose exec mysql-db mysql -u covertype_user -pcovertype_pass123 covertype_db
```

#### 3. MLflow no puede conectar a MinIO
```bash
# Verificar que MinIO esté corriendo
docker-compose ps minio

# Verificar bucket
docker-compose exec minio mc ls myminio/
```

#### 4. API de inferencia no carga modelo
```bash
# Verificar que hay modelos en MLflow
curl http://localhost:5000/api/2.0/mlflow/registered-models/list

# Forzar recarga
curl -X POST http://localhost:8000/reload-model
```

#### 5. DAG de Airflow no ejecuta
```bash
# Verificar logs del scheduler
docker-compose logs airflow-scheduler

# Verificar que el DAG no tiene errores
docker-compose exec airflow-scheduler airflow dags list
```

### Comandos Útiles

```bash
# Ver estado de todos los servicios
docker-compose ps

# Ver logs de un servicio específico
docker-compose logs -f [servicio]

# Reiniciar un servicio
docker-compose restart [servicio]

# Reconstruir un servicio
docker-compose build [servicio]

# Detener todos los servicios
docker-compose down

# Limpiar volúmenes (¡CUIDADO! Borra datos)
docker-compose down -v
```

## 📈 Métricas y Monitoreo

### Métricas Disponibles

- **Accuracy**: Precisión del modelo
- **F1-Macro**: F1-score promedio
- **Tiempo de entrenamiento**: Duración del proceso
- **Número de muestras**: Datos utilizados
- **Número de features**: Características del modelo

### Dashboards

1. **Airflow UI**: Estado de tareas y ejecuciones
2. **MLflow UI**: Experimentos y métricas
3. **Streamlit UI**: Dashboard interactivo (BONO)

## 🎯 Criterios de Evaluación

| Componente | Peso | Estado |
|------------|------|--------|
| Código en repo público | 10% | ✅ |
| Docker Compose funcionando | 10% | ✅ |
| DAG en Airflow ejecutándose | 30% | ✅ |
| MLflow tracking y registry | 30% | ✅ |
| API de inferencia | 20% | ✅ |
| **Total Base** | **100%** | ✅ |
| **BONO: Streamlit** | +10% | ✅ |
| **Total Posible** | **110%** | ✅ |

## 📞 Contacto

**Grupo 3**:
- Abel Albuez Sanchez
- Omar Gaston Chalas
- Mauricio Morales

**Recursos**:
- [Documentación MLflow](https://mlflow.org/docs/)
- [Documentación Airflow](https://airflow.apache.org/)
- [Documentación FastAPI](https://fastapi.tiangolo.com/)
- [Documentación Streamlit](https://docs.streamlit.io/)

## 🎉 ¡Sistema Listo!

El sistema está completamente implementado y listo para usar. Todos los componentes están integrados y funcionando correctamente.

**¡Disfruta explorando el sistema MLOps! 🚀**
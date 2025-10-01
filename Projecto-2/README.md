# Proyecto 2 - ML Pipeline with MySQL Storage

Pipeline de Machine Learning con Apache Airflow que obtiene datos de API, los procesa en MySQL y entrena modelos con umbral de incremento.

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker y Docker Compose
- Puertos 8080 (Airflow), 3306 (MySQL), 80 (API)

### Ejecución
```bash
cd Projecto-2
cp .env.example .env  # Editar variables si es necesario
docker-compose up --build
```

**Acceso Airflow**: http://localhost:8080 (admin/admin123)

## 📊 Arquitectura del Pipeline

### DAG: `p2_covertype_pipeline`
**Programación**: Cada 5 minutos
**Flujo**: collect_data → preprocess_data → train_model

#### 1. collect_data
- Obtiene datos de API externa (`http://api:80/data`)
- Almacena como strings en tabla `covertype_raw`
- Detección de duplicados por hash

#### 2. preprocess_data
- Lee de `covertype_raw`, convierte tipos
- **Transformaciones**:
  - `wilderness_area`: mapeo dinámico string→numeric
  - `soil_type`: extracción de números con regex
- Guarda en `covertype_data` (tipos enteros)

#### 3. train_model
- Entrena solo si incremento ≥ `P2_MIN_SAMPLE_INCREMENT`
- Usa TODOS los datos disponibles
- Almacena métricas en `model_metrics`

## 🗄️ Base de Datos MySQL

### Tablas
- **`covertype_raw`**: datos originales (VARCHAR)
- **`covertype_data`**: datos procesados (INT)
- **`wilderness_area_mapping`**: mapeos string→numeric
- **`model_metrics`**: métricas de entrenamiento
- **`preprocessing_logs`**: logs de procesamiento

## ⚙️ Variables de Entorno Clave

```bash
# API Configuration
P2_API_BASE=http://api:80
P2_GROUP_ID=3
P2_MIN_SAMPLE_INCREMENT=100

# MySQL
MYSQL_HOST=mysql-db
MYSQL_DATABASE=covertype_db
MYSQL_USER=covertype_user
MYSQL_PASSWORD=covertype_pass123

# Airflow Security
FERNET_KEY=8hSZrOuU8yqV2Q5nGYKj2wCpkNQkRFxK9M-UYtJzYWE=
AIRFLOW_SECRET_KEY=o0SxIp4G3NI71Y41XXQhEW8cfv1M8HIx5vx4r6IylmA
```

## 🛠️ Estructura

```
Projecto-2/
├── airflow/
│   ├── dags/p2_covertype_pipeline.py  # DAG principal
│   ├── Dockerfile & requirements.txt
├── mysql/init/01-create-schema.sql          # Schema MySQL
├── api/                                     # API de datos
├── docker-compose.yml                       # Servicios
└── .env.example                            # Plantilla variables
```

## 🔧 Características

- **Almacenamiento persistente** en MySQL
- **Transformaciones inteligentes** (wilderness mapping, soil regex)
- **Entrenamiento condicional** por umbral de incremento
- **Detección de duplicados** por hash de datos
- **Manejo robusto de errores** y logging detallado

## 📈 Monitoreo

- **Logs Airflow**: `docker-compose logs airflow-scheduler`
- **MySQL**: puerto 3306 expuesto
- **Métricas**: tabla `model_metrics` en MySQL
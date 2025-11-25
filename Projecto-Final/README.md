# Operaciones de Machine Learning
## Proyecto 3 - Nivel 3
**Pontificia Universidad Javeriana**

## Descripción del Proyecto

Sistema MLOps para predecir readmisión hospitalaria de pacientes diabéticos. Incluye pipelines de datos, entrenamiento de modelos, API de inferencia y monitoreo.

## Arquitectura del Sistema

El proyecto se divide en tres partes principales:

### Infrastructure Stack (`docker-compose.yml`)

Aquí va todo lo relacionado con procesamiento de datos y entrenamiento:

- **AirFlow** (webserver + scheduler): Orquesta los pipelines de datos
- **MLflow**: Tracking de experimentos y registro de modelos
- **MinIO**: Almacenamiento de artifacts (compatible con S3)
- **PostgreSQL**: Tres bases de datos separadas para metadatos, datos raw y datos limpios

Acceso:
- Airflow: http://localhost:8080 (admin/admin123)
- MLflow: http://localhost:5001

### Applications Stack (`docker-compose.apps.yml`)

Para inferencia y testing:

- **API (FastAPI)**: Servicio de predicción
- **Streamlit**: Interfaz web para usuarios
- **Locust**: Pruebas de carga

Acceso:
- API Docs: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- Locust: http://localhost:8089

### Monitoring Stack (Kubernetes)

Monitoreo con Kubernetes usando MicroK8s:

- **Grafana**: http://10.43.100.87:3010/ (admin/admin123)
- **Prometheus**: http://10.43.100.87:3011/

Más detalles en [monitoring/README.md](./monitoring/README.md)

## Inicio Rápido

### Prerequisitos

Necesitas:
- Docker & Docker Compose
- Python 3.11+
- MicroK8s (solo si vas a usar el monitoreo)
- Al menos 8GB RAM y 20GB de disco

### Paso 1: Levantar Infrastructure Stack

```bash
cd ~/Projecto-3

# Copiar y editar variables de entorno
cp .env.copy .env

# Levantar servicios
docker-compose up -d

# Verificar que todo esté corriendo
docker-compose ps
```

Deberías ver corriendo: mlflow, minio, airflow-webserver, airflow-scheduler, y las tres bases de datos (raw-db, clean-db, mlflow-db).

### Paso 2: Ejecutar Pipeline de Datos

1. Abre Airflow en http://localhost:8080
2. Ejecuta los DAGs en este orden:
   - `1_raw_batch_ingest_15k` - Carga los datos en batches
   - `2_clean_build` - Limpia y transforma los datos
   - `3_train_and_register` - Entrena y registra el modelo

3. Verifica en MLflow (http://localhost:5001) que:
   - El experimiento "diabetic_risk" esté creado
   - El modelo "diabetic_risk_model" esté en stage "Production"

### Paso 3: Levantar Applications Stack

```bash
docker-compose -f docker-compose.apps.yml up -d api streamlit
docker-compose -f docker-compose.apps.yml logs -f
```

Verifica que:
- API responda en http://localhost:8000/health
- Streamlit esté disponible en http://localhost:8501

### Paso 4: Probar el Sistema

**Opción A: Usar Streamlit**

Abre http://localhost:8501, selecciona un ejemplo o ingresa datos manualmente, y haz click en "Realizar Predicción".

**Opción B: Usar API directamente**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "race": "Caucasian",
    "gender": "Female",
    "age_bucket": "[70-80)",
    "time_in_hospital": 3,
    "num_lab_procedures": 41,
    "num_procedures": 0,
    "num_medications": 11,
    "number_outpatient": 0,
    "number_emergency": 0,
    "number_inpatient": 0,
    "number_diagnoses": 6,
    "max_glu_serum": "None",
    "a1c_result": "None",
    "insulin": "Steady",
    "change_med": true,
    "diabetes_med": true,
    "diag_1": "428",
    "diag_2": "250.01",
    "diag_3": "401",
    "medical_specialty": "Cardiology",
    "admission_type_id": 1,
    "discharge_disposition_id": 1,
    "admission_source_id": 7
  }'
```

### Paso 5: Pruebas de Carga con Locust

```bash
docker-compose -f docker-compose.apps.yml up -d locust
```

Abre http://localhost:8089 y configura:
- Number of users: 10 para empezar (puedes aumentar después)
- Spawn rate: 2
- Host: http://api:8000

## Componentes del Proyecto

### AirFlow DAGs

**DAG 1: `1_raw_batch_ingest_15k`**
Carga los datos en lotes de 15,000 registros, cada uno con su batch_id, y los guarda en la base de datos RAW.

**DAG 2: `2_clean_build`**
Toma los datos de RAW, aplica transformaciones y limpieza, crea columnas derivadas, y divide en train/val/test (80/10/10). Todo se guarda en CLEAN.

**DAG 3: `3_train_and_register`**
Lee los datos de CLEAN (solo train y val), entrena un RandomForestClassifier, registra todo en MLflow, y promueve el mejor modelo a "Production".

### API FastAPI

Endpoints disponibles:
- `GET /health` - Health check
- `GET /model-info` - Info del modelo en Production
- `POST /predict` - Hacer predicción
- `POST /reload-model` - Recargar modelo desde MLflow
- `GET /metrics` - Métricas para Prometheus

La API carga modelos dinámicamente desde MLflow, así que no necesitas cambiar código cuando actualizas el modelo. También expone métricas para Prometheus y tiene documentación automática en `/docs`.

### Streamlit UI

Interfaz web con formulario para ingresar datos del paciente. Incluye 2 ejemplos pre-cargados (bajo y alto riesgo), muestra la probabilidad del resultado, la versión del modelo usado, y una interpretación del resultado.

### Locust Load Testing

Tareas configuradas:
- Health check (peso 1)
- Model info (peso 2)
- Predict (peso 10) - la principal

Resultados con 10 usuarios concurrentes: 0% errores, latencia promedio de 37ms, 5 RPS sostenido, P99 de 110ms.

## Estructura del Proyecto
```
Projecto-3/
├── docker-compose.yml              # Infrastructure stack
├── docker-compose.apps.yml         # Applications stack
├── .env                            # Variables de entorno
│
├── airflow/                        # Pipeline de datos
│   ├── dags/
│   │   ├── 1_raw_batch_ingest_15k.py
│   │   ├── 2_clean_build.py
│   │   └── 3_train_and_register.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── api/                            # API de inferencia
│   ├── main.py                     # Aplicación FastAPI
│   ├── schemas.py                  # Schemas Pydantic
│   ├── mlflow_client.py            # Cliente MLflow
│   ├── Dockerfile
│   └── requirements.txt
│
├── streamlit/                      # Interfaz de usuario
│   ├── app.py                      # Aplicación Streamlit
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
├── locust/                         # Pruebas de carga
│   ├── locustfile.py               # Definición de tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── monitoring/                     # Kubernetes monitoring
│   ├── README.md
│   ├── init-forward.sh
│   └── prometheus-datasource.yml
│
└── postgresql/                     # Inicialización de DBs
    ├── raw/init/
    └── clean/init/
```

## Configuración

### Variables de Entorno

El archivo `.env` debe contener:
```bash
# AirFlow
AIRFLOW_UID=50000
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin123

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_PORT=5001

# PostgreSQL
RAW_DB=raw_data
CLEAN_DB=clean_data
MLFLOW_DB_NAME=mlflow

# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=adminadmin
```

## Métricas y Monitoreo

La API expone métricas en `/metrics`:
- `predictions_total`: Total de predicciones por modelo y resultado
- `prediction_duration_seconds`: Tiempo de procesamiento
- `prediction_errors_total`: Total de errores

Grafana está disponible en http://10.43.100.87:3010 con dashboards para API Performance y ML Model Metrics.

## Testing

### Pruebas Manuales

```bash
cd api/
python test_api.py

./test_services.sh
```

### Pruebas de Carga

Los resultados están en Locust UI (http://localhost:8089). Con 10 usuarios concurrentes obtuvimos 0% errores, latencia promedio de 37ms y P99 de 110ms.

## Troubleshooting

### API no se conecta a MLflow

Verifica que MLflow esté corriendo:
```bash
docker-compose ps mlflow
docker-compose restart mlflow
docker-compose logs mlflow
```

### Modelo no cargado en la API

1. Verifica en MLflow que haya un modelo en "Production"
2. Si no hay, ejecuta el DAG 3
3. Luego llama a `POST /reload-model` en la API

### Streamlit no conecta con API

```bash
docker-compose -f docker-compose.apps.yml ps api
docker-compose -f docker-compose.apps.yml logs streamlit
```

## Notas Importantes

El modelo usa solo features numéricas y fue entrenado con datos de `clean_data.diabetic_clean`. Tiene un accuracy de ~89% y se actualiza automáticamente cuando cambias el modelo en MLflow.

Los datos vienen de 130 hospitales de EE.UU. (1999-2008), con ~101,000 registros de pacientes diabéticos. Se procesan en batches de 15,000 y se dividen en 80% train, 10% val, 10% test.

## Requisitos del Proyecto

- AirFlow para orquestación de pipelines (20%)
- MLflow con bucket y base de datos (20%)
- API que carga modelo dinámicamente (20%)
- Interfaz Streamlit funcional (incluido en 20%)
- Observabilidad con Prometheus/Grafana (10%)
- Pruebas de carga con Locust (incluido en 10%)

## Integrantes del Equipo

- Omar Gaston Chalas
- Abel Albuez Sanchez
- Mauricio Morales

## Referencias

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [AirFlow Documentation](https://airflow.apache.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Locust Documentation](https://docs.locust.io/)

---

Última actualización: Noviembre 2025
# Operaciones de Machine Learning
## Proyecto 3 - Nivel 3
**Pontificia Universidad Javeriana**

## 📋 Descripción del Proyecto

Este proyecto implementa un sistema completo de Machine Learning Operations (MLOps) para predecir la readmisión hospitalaria de pacientes diabéticos. El sistema utiliza tecnologías de contenedores, orquestación y monitoreo para el despliegue y gestión de modelos de machine learning en producción.

## 🏗️ Arquitectura del Sistema

El proyecto está dividido en dos docker-compose principales:

### 1. Infrastructure Stack (`docker-compose.yml`)
Sistema de procesamiento de datos y entrenamiento de modelos.

**Servicios:**
- **AirFlow** (webserver + scheduler): Orquestación de pipelines
- **MLflow**: Tracking de experimentos y registro de modelos
- **MinIO**: Almacenamiento de artifacts (S3-compatible)
- **PostgreSQL**: Bases de datos para metadatos, datos raw y datos limpios

**Acceso:**
- Airflow: http://localhost:8080 (admin/admin123)
- MLflow: http://localhost:5001

### 2. Applications Stack (`docker-compose.apps.yml`)
Sistema de inferencia y testing.

**Servicios:**
- **API (FastAPI)**: Servicio de predicción
- **Streamlit**: Interfaz de usuario web
- **Locust**: Pruebas de carga

**Acceso:**
- API Docs: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- Locust: http://localhost:8089

### 3. Monitoring Stack (Kubernetes)
Sistema de monitoreo implementado con Kubernetes para observabilidad.

**Tecnologías:**
- MicroK8s

**Servicios:**
- **Grafana**: http://10.43.100.87:3010/ (admin/admin123)
- **Prometheus**: http://10.43.100.87:3011/

> Para más detalles sobre la configuración de Kubernetes, consultar [monitoring/README.md](./monitoring/README.md)

---

## 🚀 Inicio Rápido

### Prerequisitos

- Docker & Docker Compose
- Python 3.11+
- MicroK8s (para monitoreo)
- 8GB RAM mínimo
- 20GB espacio en disco

### Paso 1: Levantar Infrastructure Stack
```bash
# Clonar repositorio
cd ~/Projecto-3

# Copiar variables de entorno
cp .env.copy .env
# Editar .env si es necesario

# Levantar servicios
docker-compose up -d

# Verificar que todo esté corriendo
docker-compose ps
```

**Servicios que deben estar UP:**
- mlflow
- minio
- airflow-webserver
- airflow-scheduler
- raw-db, clean-db, mlflow-db

### Paso 2: Ejecutar Pipeline de Datos

1. Acceder a Airflow: http://localhost:8080
2. Ejecutar DAGs en orden:
   - **DAG 1**: `1_raw_batch_ingest_15k` - Carga datos en batches
   - **DAG 2**: `2_clean_build` - Limpia y transforma datos
   - **DAG 3**: `3_train_and_register` - Entrena y registra modelo

3. Verificar en MLflow (http://localhost:5001):
   - Experimento "diabetic_risk" creado
   - Modelo "diabetic_risk_model" en stage "Production"

### Paso 3: Levantar Applications Stack
```bash
# Levantar API y Streamlit
docker-compose -f docker-compose.apps.yml up -d api streamlit

# Verificar logs
docker-compose -f docker-compose.apps.yml logs -f
```

**Verificar:**
- API: http://localhost:8000/health (debe retornar "healthy")
- Streamlit: http://localhost:8501 (debe mostrar interfaz)

### Paso 4: Probar el Sistema

**Opción A: Usar Streamlit (Recomendado)**

1. Abrir http://localhost:8501
2. Seleccionar un ejemplo pre-cargado o ingresar datos manualmente
3. Click "Realizar Predicción"
4. Ver resultados con versión del modelo usado

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
# Levantar Locust
docker-compose -f docker-compose.apps.yml up -d locust

# Abrir interfaz
# http://localhost:8089
```

**Configuración sugerida:**
- Number of users: 10 (inicial), incrementar gradualmente
- Spawn rate: 2
- Host: http://api:8000

---

## 📊 Componentes del Proyecto

### AirFlow DAGs

**DAG 1: `1_raw_batch_ingest_15k`**
- Ingesta datos en lotes de 15,000 registros
- Etiqueta cada lote con batch_id
- Almacena en base de datos RAW

**DAG 2: `2_clean_build`**
- Procesa datos de RAW
- Aplica transformaciones y limpieza
- Crea columnas derivadas
- Divide en train/val/test (80/10/10)
- Almacena en base de datos CLEAN

**DAG 3: `3_train_and_register`**
- Lee datos de CLEAN (solo train y val)
- Entrena modelo RandomForestClassifier
- Registra experimento en MLflow
- Promueve mejor modelo a "Production"

### API FastAPI

**Endpoints:**
- `GET /health`: Health check
- `GET /model-info`: Información del modelo en Production
- `POST /predict`: Realizar predicción
- `POST /reload-model`: Recargar modelo desde MLflow
- `GET /metrics`: Métricas de Prometheus

**Características:**
- Carga dinámica de modelos desde MLflow
- No requiere cambios de código al cambiar versión de modelo
- Expone métricas para Prometheus
- Documentación automática en `/docs`

### Streamlit UI

**Características:**
- Formulario interactivo para datos del paciente
- 2 ejemplos pre-cargados (bajo riesgo, alto riesgo)
- Visualización de resultados con probabilidad
- Muestra versión del modelo usado
- Interpretación del resultado

### Locust Load Testing

**Tasks implementadas:**
- Health check (peso 1)
- Model info (peso 2)
- Predict (peso 10) - tarea principal

**Resultados de pruebas:**
- 10 usuarios concurrentes: ✅ 0% errores, 37ms latencia promedio
- 5 RPS sostenido
- P99: 110ms

---

## 📁 Estructura del Proyecto
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

---

## 🔧 Configuración

### Variables de Entorno

Archivo `.env`:
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

---

## 📈 Métricas y Monitoreo

### Métricas de Prometheus

La API expone métricas en `/metrics`:

- `predictions_total`: Total de predicciones por modelo y resultado
- `prediction_duration_seconds`: Tiempo de procesamiento
- `prediction_errors_total`: Total de errores

### Dashboards Grafana

Acceder a Grafana: http://10.43.100.87:3010

**Dashboards disponibles:**
- API Performance
- ML Model Metrics

---

## 🧪 Testing

### Pruebas Manuales
```bash
# Test de la API
cd api/
python test_api.py

# Test de servicios
./test_services.sh
```

### Pruebas de Carga

Ver resultados en Locust UI: http://localhost:8089

**Capacidad determinada:**
- ✅ 10 usuarios concurrentes sin errores
- Latencia promedio: 37ms
- P99: 110ms

---

## 🐛 Troubleshooting

### API no se conecta a MLflow

**Solución:**
```bash
# Verificar que MLflow esté corriendo
docker-compose ps mlflow

# Reiniciar MLflow
docker-compose restart mlflow

# Verificar logs
docker-compose logs mlflow
```

### Modelo no cargado en la API

**Solución:**
1. Verificar en MLflow que hay un modelo en "Production"
2. Ejecutar DAG 3 si no hay modelo
3. Llamar a `POST /reload-model` en la API

### Streamlit no conecta con API

**Solución:**
```bash
# Verificar que API esté corriendo
docker-compose -f docker-compose.apps.yml ps api

# Ver logs de Streamlit
docker-compose -f docker-compose.apps.yml logs streamlit
```

---

## 📝 Notas Importantes

### Sobre el Modelo

- El modelo usa **solo features numéricas**
- Entrenado con datos de `clean_data.diabetic_clean`
- Métricas: Accuracy ~89%, F1 Score variable
- Se actualiza automáticamente al cambiar en MLflow

### Sobre los Datos

- Dataset: 130 hospitales de EE.UU. (1999-2008)
- ~101,000 registros de pacientes diabéticos
- Procesamiento en batches de 15,000 registros
- Split: 80% train, 10% val, 10% test

---

## 🎯 Requisitos del Proyecto Cumplidos

- ✅ AirFlow para orquestación de pipelines (20%)
- ✅ MLflow con bucket y base de datos (20%)
- ✅ API que carga modelo dinámicamente (20%)
- ✅ Interfaz Streamlit funcional (incluido en 20%)
- ✅ Observabilidad con Prometheus/Grafana (10%)
- ✅ Pruebas de carga con Locust (incluido en 10%)

---

## 👥 Integrantes del Equipo

- **Omar Gaston Chalas**
- **Abel Albuez Sanchez**
- **Mauricio Morales**

---

## 📚 Referencias

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [AirFlow Documentation](https://airflow.apache.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Locust Documentation](https://docs.locust.io/)

---

## 📄 Licencia

Este proyecto es parte del curso de Operaciones de Machine Learning de la Pontificia Universidad Javeriana.

---

**Última actualización:** Noviembre 2025
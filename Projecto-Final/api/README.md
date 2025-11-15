# API de Predicción de Readmisión - Pacientes Diabéticos

API FastAPI que carga modelos dinámicamente desde MLflow para predecir readmisión de pacientes diabéticos.

## 🎯 Características

- ✅ Carga dinámica de modelos desde MLflow (stage="Production")
- ✅ Sin hardcodeo de versiones de modelo
- ✅ Métricas de Prometheus en `/metrics`
- ✅ Documentación automática en `/docs`
- ✅ Health checks
- ✅ Recarga de modelos sin reiniciar

## 📋 Prerequisitos

1. **MLflow corriendo** en `http://localhost:5001`
2. **Modelo entrenado** y en stage "Production" (ejecutar DAG 3 de Airflow)
3. **MinIO** corriendo en `http://localhost:9000`

## 🚀 Instalación y Ejecución

### Opción 1: Ejecutar localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar API
uvicorn main:app --reload --port 8000
```

### Opción 2: Docker

```bash
# Construir imagen
docker build -t diabetic-api:latest .

# Ejecutar contenedor
docker run -p 8000:8000 \
  -e MLFLOW_TRACKING_URI=http://host.docker.internal:5001 \
  -e MLFLOW_S3_ENDPOINT_URL=http://host.docker.internal:9000 \
  diabetic-api:latest
```

## 📖 Endpoints

### 1. Root
```bash
GET /
```

### 2. Health Check
```bash
GET /health
```

Respuesta:
```json
{
  "status": "healthy",
  "mlflow_connected": true,
  "model_loaded": true,
  "model_info": {
    "model_name": "diabetic_risk_model",
    "model_version": "1",
    "model_stage": "Production",
    "run_id": "abc123...",
    "accuracy": 0.65,
    "f1_score": 0.38
  }
}
```

### 3. Model Info
```bash
GET /model-info
```

Respuesta:
```json
{
  "model_name": "diabetic_risk_model",
  "model_version": "1",
  "model_stage": "Production",
  "run_id": "abc123...",
  "accuracy": 0.65,
  "f1_score": 0.38
}
```

### 4. Predict
```bash
POST /predict
Content-Type: application/json

{
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
}
```

Respuesta:
```json
{
  "prediction": 0,
  "probability": 0.23,
  "risk_level": "Low Risk (>30 days or No)",
  "model_name": "diabetic_risk_model",
  "model_version": "1",
  "model_stage": "Production"
}
```

### 5. Reload Model
```bash
POST /reload-model
```

Útil cuando actualizas el modelo en MLflow sin querer reiniciar la API.

### 6. Metrics (Prometheus)
```bash
GET /metrics
```

Expone métricas para Prometheus:
- `predictions_total`: Total de predicciones
- `prediction_duration_seconds`: Tiempo de predicción
- `prediction_errors_total`: Total de errores

## 🧪 Probar la API

### Usando curl

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model-info

# Predicción
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

### Usando Python

```python
import requests

# Predicción
data = {
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
    "change_med": True,
    "diabetes_med": True,
    "diag_1": "428",
    "diag_2": "250.01",
    "diag_3": "401",
    "medical_specialty": "Cardiology",
    "admission_type_id": 1,
    "discharge_disposition_id": 1,
    "admission_source_id": 7
}

response = requests.post("http://localhost:8000/predict", json=data)
print(response.json())
```

## 📊 Documentación Interactiva

Una vez corriendo, visita:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Troubleshooting

### Error: "Modelo no cargado"

**Causa:** El DAG 3 de Airflow no se ha ejecutado o no hay modelo en "Production"

**Solución:**
1. Ve a Airflow (http://localhost:8080)
2. Ejecuta los DAGs en orden: 1 → 2 → 3
3. Verifica en MLflow (http://localhost:5001) que hay un modelo en stage "Production"

### Error: "Cannot connect to MLflow"

**Causa:** MLflow no está corriendo o la URL es incorrecta

**Solución:**
1. Verifica que MLflow esté corriendo: `curl http://localhost:5001/health`
2. Verifica la variable de entorno `MLFLOW_TRACKING_URI`

## 🎯 Puntos Clave del Proyecto

✅ **Carga dinámica**: El modelo se consulta desde MLflow cada vez, NO está hardcodeado

✅ **Sin cambios de código**: Si cambias el modelo en MLflow a otra versión en "Production", la API usa el nuevo automáticamente

✅ **Métricas**: Prometheus puede scrapear `/metrics` para observabilidad

✅ **Health checks**: Endpoint `/health` para verificar estado

## 📝 Notas

- La API usa solo features numéricas por simplicidad
- En producción, deberías aplicar el mismo preprocesamiento que en entrenamiento (one-hot encoding, etc.)
- El modelo fue entrenado con `.fillna(0)` para features numéricas

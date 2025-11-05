# 🚀 Guía de Inicio Rápido - API FastAPI

## ✅ Prerequisitos

Antes de ejecutar la API, asegúrate de tener:

1. ✅ Docker Compose corriendo con todos los servicios
2. ✅ Los 3 DAGs de Airflow ejecutados (especialmente el DAG 3)
3. ✅ Un modelo en stage "Production" en MLflow

---

## 📋 Paso 1: Verificar que todo esté listo

### 1.1 Verificar contenedores
```bash
cd ~/Projecto-3
docker-compose ps
```

Todos deben estar "Up".

### 1.2 Verificar MLflow
Abre http://localhost:5001 y verifica:
- Hay experimentos registrados
- Hay un modelo "diabetic_risk_model" 
- El modelo tiene una versión en stage "Production"

### 1.3 Verificar datos
```bash
docker exec -it clean-db psql -U clean_user -d clean_data -c "SELECT COUNT(*) FROM clean_data.diabetic_clean;"
```

Debe haber registros procesados.

---

## 🎯 Paso 2: Ejecutar los DAGs (si no lo hiciste)

1. Ve a Airflow: http://localhost:8080
   - User: `admin`
   - Pass: `admin123`

2. Ejecuta en orden:
   - DAG 1: `1_raw_batch_ingest_15k`
   - DAG 2: `2_clean_build`
   - DAG 3: `3_train_and_register` (ESTE CREA EL MODELO)

3. Espera a que se completen (círculos verdes)

4. Verifica en MLflow que el modelo aparece en "Production"

---

## 🚀 Paso 3: Ejecutar la API

### Opción A: Ejecución local (recomendado para desarrollo)

```bash
# 1. Ir al directorio de la API
cd ~/Projecto-3/api

# 2. Crear entorno virtual (opcional pero recomendado)
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la API
uvicorn main:app --reload --port 8000

# La API estará disponible en http://localhost:8000
```

### Opción B: Docker

```bash
cd ~/Projecto-3/api

# Construir imagen
docker build -t diabetic-api:latest .

# Ejecutar contenedor
docker run -p 8000:8000 \
  --name diabetic-api \
  --network projecto-3_default \
  -e MLFLOW_TRACKING_URI=http://mlflow:5000 \
  -e MLFLOW_S3_ENDPOINT_URL=http://minio:9000 \
  diabetic-api:latest
```

---

## 🧪 Paso 4: Probar la API

### 4.1 Abrir documentación interactiva

Abre en tu navegador:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4.2 Ejecutar script de prueba

```bash
cd ~/Projecto-3/api
python test_api.py
```

Esto probará todos los endpoints automáticamente.

### 4.3 Probar manualmente con curl

```bash
# Health check
curl http://localhost:8000/health

# Info del modelo
curl http://localhost:8000/model-info

# Hacer una predicción
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

---

## 📊 Paso 5: Verificar métricas de Prometheus

```bash
# Ver métricas
curl http://localhost:8000/metrics
```

Deberías ver métricas como:
- `predictions_total`
- `prediction_duration_seconds`
- `prediction_errors_total`

---

## ❓ Troubleshooting

### Error: "Modelo no cargado"

**Solución:**
1. Verifica que el DAG 3 se ejecutó correctamente
2. Ve a MLflow (http://localhost:5001)
3. Verifica que existe el modelo "diabetic_risk_model"
4. Verifica que tiene una versión en stage "Production"

### Error: "Cannot connect to MLflow"

**Solución:**
1. Verifica que MLflow está corriendo:
   ```bash
   docker-compose ps mlflow
   ```
2. Verifica que puedes acceder:
   ```bash
   curl http://localhost:5001/health
   ```
3. Si estás en Docker, usa `MLFLOW_TRACKING_URI=http://mlflow:5000`
4. Si estás en local, usa `MLFLOW_TRACKING_URI=http://localhost:5001`

### La API no inicia

**Solución:**
1. Verifica que el puerto 8000 esté libre:
   ```bash
   lsof -i :8000
   ```
2. Verifica que instalaste todas las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎯 Próximos pasos

Una vez que la API funcione:

1. ✅ Crear la interfaz Streamlit (consume esta API)
2. ✅ Configurar Prometheus para scrapear `/metrics`
3. ✅ Crear dashboard en Grafana
4. ✅ Hacer pruebas de carga con Locust

---

## 📝 Puntos clave cumplidos

✅ La API carga el modelo dinámicamente desde MLflow  
✅ NO hay versiones de modelo hardcodeadas en el código  
✅ Expone métricas en `/metrics` para Prometheus  
✅ Si cambias el modelo en MLflow, la API usa el nuevo automáticamente  
✅ Tiene health checks y documentación automática  

---

## 🎉 ¡Listo!

Si todo funciona, deberías ver:

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

**La API está lista para usarse! 🚀**

# 📊 Resumen Ejecutivo - API FastAPI

## ✅ Lo que cumple del proyecto (20% de la nota)

### Requisitos cumplidos:

1. ✅ **API con FastAPI creada**
   - Framework: FastAPI
   - Puerto: 8000
   - Documentación automática en `/docs`

2. ✅ **Consume el mejor modelo de MLflow**
   - Carga dinámica desde stage "Production"
   - Sin hardcodear versiones
   - Se actualiza automáticamente si cambias el modelo

3. ✅ **Endpoint de métricas para Prometheus**
   - Ruta: `/metrics`
   - Formato: Prometheus compatible
   - Métricas expuestas:
     - `predictions_total`: Total de predicciones por modelo y resultado
     - `prediction_duration_seconds`: Tiempo de respuesta
     - `prediction_errors_total`: Errores por tipo

4. ✅ **Sin cambios de código al cambiar modelo**
   - Usa `models:/{model_name}/Production`
   - Consulta MLflow en cada inicio
   - Endpoint `/reload-model` para actualizar sin reiniciar

---

## 📁 Archivos creados

```
api/
├── main.py                 # Aplicación FastAPI principal
├── schemas.py             # Modelos Pydantic para validación
├── mlflow_client.py       # Cliente para cargar modelos de MLflow
├── requirements.txt       # Dependencias
├── Dockerfile            # Imagen Docker
├── .env                  # Variables de entorno
├── README.md             # Documentación completa
├── QUICKSTART.md         # Guía de inicio rápido
└── test_api.py           # Script de pruebas
```

---

## 🔌 Endpoints implementados

### 1. `/` - Root
- Método: GET
- Info general de la API

### 2. `/health` - Health Check
- Método: GET
- Verifica estado de la API y conexión con MLflow
- Muestra si el modelo está cargado

### 3. `/model-info` - Información del modelo
- Método: GET
- Retorna: nombre, versión, stage, métricas (accuracy, f1)

### 4. `/predict` - Predicción
- Método: POST
- Input: Datos del paciente
- Output: 
  - prediction: 0 (bajo riesgo) o 1 (alto riesgo)
  - probability: probabilidad de alto riesgo
  - risk_level: descripción legible
  - model_name, model_version, model_stage

### 5. `/reload-model` - Recargar modelo
- Método: POST
- Recarga el modelo desde MLflow sin reiniciar

### 6. `/metrics` - Métricas Prometheus
- Método: GET
- Formato: Prometheus
- Para scraping automático

---

## 🎯 Características destacadas

### 1. Carga dinámica de modelos
```python
# NO hace esto (hardcodeado):
model = mlflow.sklearn.load_model("runs:/abc123/model")

# SÍ hace esto (dinámico):
model = mlflow.sklearn.load_model("models:/diabetic_risk_model/Production")
```

### 2. Métricas de Prometheus
```python
# Contador de predicciones
PREDICTIONS_COUNTER.labels(
    model_version="1",
    prediction="0"
).inc()

# Histograma de duración
PREDICTION_DURATION.labels(
    model_version="1"
).observe(0.123)
```

### 3. Validación con Pydantic
```python
class PatientInput(BaseModel):
    race: str
    gender: str
    time_in_hospital: int = Field(..., ge=1, le=14)
    # ... más validaciones
```

---

## 🧪 Cómo probar

### 1. Inicio rápido
```bash
cd ~/Projecto-3/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Probar con script
```bash
python test_api.py
```

### 3. Documentación interactiva
http://localhost:8000/docs

---

## 📊 Ejemplo de uso

### Request:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "race": "Caucasian",
    "gender": "Female",
    "age_bucket": "[70-80)",
    "time_in_hospital": 3,
    "num_lab_procedures": 41,
    ...
  }'
```

### Response:
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

---

## ✅ Checklist de cumplimiento

- [x] API con FastAPI creada
- [x] Carga modelo desde MLflow (Production)
- [x] Sin hardcodear versiones
- [x] Endpoint `/predict` funcional
- [x] Endpoint `/metrics` para Prometheus
- [x] Documentación automática
- [x] Health checks
- [x] Validación de entrada (Pydantic)
- [x] Manejo de errores
- [x] Logging
- [x] Dockerfile
- [x] README con instrucciones

---

## 🚀 Siguiente paso: Streamlit

Ahora que la API funciona, el siguiente paso es crear la interfaz con Streamlit que:
1. Consuma esta API
2. Permita ingresar datos del paciente
3. Tenga ejemplos pre-definidos
4. Muestre la versión del modelo usado

---

## 💡 Notas importantes

1. **La API debe ejecutarse DESPUÉS de que el DAG 3 haya creado el modelo**
2. **MLflow debe estar corriendo** en http://localhost:5001
3. **El modelo debe estar en stage "Production"** en MLflow
4. **Las métricas se acumulan** en memoria (se pierden al reiniciar)

---

## 📝 Para el video de sustentación

Puntos a explicar:
1. Mostrar código de `mlflow_client.py` - cómo carga dinámicamente
2. Hacer una predicción en `/docs`
3. Mostrar `/model-info` - versión actual
4. Cambiar modelo en MLflow a otra versión en Production
5. Llamar `/reload-model`
6. Hacer otra predicción - mostrar que usa el nuevo modelo
7. Mostrar `/metrics` - métricas de Prometheus

---

**Estado: ✅ COMPLETADO - Listo para integrar con Streamlit**

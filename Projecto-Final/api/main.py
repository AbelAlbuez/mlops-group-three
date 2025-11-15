"""
API FastAPI para inferencia de readmisión de pacientes diabéticos
Carga modelos dinámicamente desde MLflow (stage="Production")
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import pandas as pd
import logging
import time
import os
from typing import Dict, Any

from schemas import PatientInput, PredictionOutput, ModelInfo, HealthCheck
from mlflow_client import MLflowModelClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="Diabetic Readmission Prediction API",
    description="API para predecir readmisión de pacientes diabéticos usando MLflow",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Métricas de Prometheus
PREDICTIONS_COUNTER = Counter(
    'predictions_total',
    'Total number of predictions made',
    ['model_version', 'prediction']
)

PREDICTION_DURATION = Histogram(
    'prediction_duration_seconds',
    'Time spent processing prediction',
    ['model_version']
)

ERRORS_COUNTER = Counter(
    'prediction_errors_total',
    'Total number of prediction errors',
    ['error_type']
)

# Cliente de MLflow (global)
mlflow_client: MLflowModelClient = None


@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar la API"""
    global mlflow_client
    
    logger.info("🚀 Iniciando API de predicción...")
    
    # Configurar MLflow
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
    model_name = os.getenv("MODEL_NAME", "diabetic_risk_model")
    
    logger.info(f"Conectando a MLflow: {mlflow_uri}")
    logger.info(f"Buscando modelo: {model_name}")
    
    try:
        # Inicializar cliente de MLflow
        mlflow_client = MLflowModelClient(
            tracking_uri=mlflow_uri,
            model_name=model_name
        )
        
        # Intentar cargar modelo en Production
        try:
            mlflow_client.load_production_model()
            
            info = mlflow_client.model_info
            logger.info(
                f"✓ Modelo cargado: {info['model_name']} "
                f"v{info['model_version']} (Production)"
            )
            logger.info(f"  - Accuracy: {info.get('accuracy', 'N/A')}")
            logger.info(f"  - F1 Score: {info.get('f1_score', 'N/A')}")
            logger.info("✓ API lista para hacer predicciones")
            
        except ValueError as ve:
            # No hay modelo en Production - esto es OK
            logger.warning("⚠️  No hay modelo en stage 'Production'")
            logger.warning("⚠️  La API está funcionando pero no puede hacer predicciones")
            logger.info("💡 Para habilitar predicciones:")
            logger.info("   1. Ejecuta el DAG 3 en Airflow")
            logger.info("   2. O llama al endpoint POST /reload-model")
            mlflow_client.model = None
            mlflow_client.model_info = {}
            
        except Exception as e:
            # Otro error al cargar modelo
            logger.error(f"✗ Error al cargar modelo: {e}")
            logger.warning("⚠️  La API está funcionando pero no puede hacer predicciones")
            mlflow_client.model = None
            mlflow_client.model_info = {}
        
    except Exception as e:
        # Error conectando a MLflow
        logger.error(f"✗ Error conectando a MLflow: {e}")
        logger.error("⚠️  La API iniciará en modo degradado")
        logger.info("💡 Verifica que MLflow esté corriendo en: {mlflow_uri}")
        mlflow_client = None


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz"""
    return {
        "message": "Diabetic Readmission Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "model_info": "/model-info",
        "predict": "/predict",
        "metrics": "/metrics"
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Verifica que la API y MLflow estén funcionando
    """
    try:
        mlflow_connected = mlflow_client is not None and mlflow_client.is_connected()
        model_loaded = mlflow_client is not None and mlflow_client.is_model_loaded()
        
        model_info = None
        if model_loaded:
            info = mlflow_client.model_info
            model_info = ModelInfo(
                model_name=info["model_name"],
                model_version=info["model_version"],
                model_stage=info["model_stage"],
                run_id=info["run_id"],
                accuracy=info.get("accuracy"),
                f1_score=info.get("f1_score")
            )
        
        return HealthCheck(
            status="healthy" if (mlflow_connected and model_loaded) else "unhealthy",
            mlflow_connected=mlflow_connected,
            model_loaded=model_loaded,
            model_info=model_info
        )
    
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return HealthCheck(
            status="unhealthy",
            mlflow_connected=False,
            model_loaded=False,
            model_info=None
        )


@app.get("/model-info", response_model=ModelInfo, tags=["Model"])
async def get_model_info():
    """
    Obtiene información del modelo en Production
    """
    if mlflow_client is None or not mlflow_client.is_model_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no cargado. Ejecuta el DAG 3 en Airflow."
        )
    
    try:
        info = mlflow_client.model_info
        return ModelInfo(
            model_name=info["model_name"],
            model_version=info["model_version"],
            model_stage=info["model_stage"],
            run_id=info["run_id"],
            accuracy=info.get("accuracy"),
            f1_score=info.get("f1_score")
        )
    except Exception as e:
        logger.error(f"Error obteniendo info del modelo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/predict", response_model=PredictionOutput, tags=["Prediction"])
async def predict(patient: PatientInput):
    """
    Realiza predicción de readmisión para un paciente
    
    - **0**: Bajo riesgo (readmisión >30 días o sin readmisión)
    - **1**: Alto riesgo (readmisión <30 días)
    """
    if mlflow_client is None:
        ERRORS_COUNTER.labels(error_type="mlflow_not_connected").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MLflow no está conectado",
                "solution": "Verifica que MLflow esté corriendo y reinicia la API"
            }
        )
    
    if not mlflow_client.is_model_loaded():
        ERRORS_COUNTER.labels(error_type="model_not_loaded").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Modelo no cargado",
                "reason": "No hay modelo en stage 'Production' en MLflow",
                "solution": "Ejecuta el DAG 3 en Airflow o llama a POST /reload-model"
            }
        )
    
    start_time = time.time()
    model_version = mlflow_client.model_info.get("model_version", "unknown")
    
    try:
        # Convertir input a DataFrame
        patient_dict = patient.model_dump()
        
        # Crear DataFrame con las features que el modelo espera
        # El modelo fue entrenado con features numéricas
        # Debemos convertir los datos categóricos a numéricos como lo hizo el entrenamiento
        
        df = pd.DataFrame([{
            'encounter_id': 0,
            'patient_nbr': 0,
            'time_in_hospital': patient_dict['time_in_hospital'],
            'num_lab_procedures': patient_dict['num_lab_procedures'],
            'num_procedures': patient_dict['num_procedures'],
            'num_medications': patient_dict['num_medications'],
            'number_outpatient': patient_dict['number_outpatient'],
            'number_emergency': patient_dict['number_emergency'],
            'number_inpatient': patient_dict['number_inpatient'],
            'number_diagnoses': patient_dict['number_diagnoses'],
            'admission_type_id': patient_dict['admission_type_id'],
            'discharge_disposition_id': patient_dict['discharge_disposition_id'],
            'admission_source_id': patient_dict['admission_source_id'],
            'batch_id': 0
        }])
        
        # Realizar predicción
        prediction, probabilities = mlflow_client.predict(df)
        
        pred_value = int(prediction[0])
        
        # Obtener probabilidad de clase 1 (alto riesgo)
        if probabilities is not None:
            prob_high_risk = float(probabilities[0][1])
        else:
            prob_high_risk = 1.0 if pred_value == 1 else 0.0
        
        # Determinar nivel de riesgo
        risk_level = "High Risk (<30 days)" if pred_value == 1 else "Low Risk (>30 days or No)"
        
        # Métricas
        duration = time.time() - start_time
        PREDICTION_DURATION.labels(model_version=model_version).observe(duration)
        PREDICTIONS_COUNTER.labels(
            model_version=model_version,
            prediction=str(pred_value)
        ).inc()
        
        logger.info(
            f"Predicción exitosa: {pred_value} ({risk_level}) "
            f"[Prob: {prob_high_risk:.3f}] [Time: {duration:.3f}s]"
        )
        
        return PredictionOutput(
            prediction=pred_value,
            probability=prob_high_risk,
            risk_level=risk_level,
            model_name=mlflow_client.model_info["model_name"],
            model_version=model_version,
            model_stage=mlflow_client.model_info["model_stage"]
        )
    
    except Exception as e:
        ERRORS_COUNTER.labels(error_type="prediction_error").inc()
        logger.error(f"Error en predicción: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al realizar predicción: {str(e)}"
        )


@app.post("/reload-model", tags=["Model"])
async def reload_model():
    """
    Recarga el modelo desde MLflow
    
    Útil cuando se actualiza el modelo en Production sin reiniciar la API
    """
    if mlflow_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cliente MLflow no inicializado"
        )
    
    try:
        logger.info("Recargando modelo desde MLflow...")
        mlflow_client.reload_model()
        info = mlflow_client.model_info
        
        return {
            "message": "Modelo recargado exitosamente",
            "model_name": info["model_name"],
            "model_version": info["model_version"],
            "model_stage": info["model_stage"]
        }
    
    except Exception as e:
        logger.error(f"Error recargando modelo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Endpoint de métricas para Prometheus
    
    Expone métricas en formato Prometheus para scraping
    """
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

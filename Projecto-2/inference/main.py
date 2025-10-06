from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import mlflow
import mlflow.sklearn
import pandas as pd
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "covertype_classifier")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

app = FastAPI(
    title="Covertype Inference API",
    description="API para predicción de tipo de cobertura forestal",
    version="1.0.0"
)

# ==========================================
# Modelos Pydantic
# ==========================================

class CovertypeFeatures(BaseModel):
    """Features de entrada para predicción"""
    elevation: int = Field(..., description="Elevación en metros")
    aspect: int = Field(..., ge=0, le=360, description="Aspecto en grados azimuth")
    slope: int = Field(..., ge=0, le=90, description="Pendiente en grados")
    horizontal_distance_to_hydrology: int = Field(..., description="Distancia horizontal a fuentes de agua")
    vertical_distance_to_hydrology: int = Field(..., description="Distancia vertical a fuentes de agua")
    horizontal_distance_to_roadways: int = Field(..., description="Distancia horizontal a carreteras")
    hillshade_9am: int = Field(..., ge=0, le=255, description="Índice de sombra a las 9am")
    hillshade_noon: int = Field(..., ge=0, le=255, description="Índice de sombra al mediodía")
    hillshade_3pm: int = Field(..., ge=0, le=255, description="Índice de sombra a las 3pm")
    horizontal_distance_to_fire_points: int = Field(..., description="Distancia horizontal a puntos de fuego")
    wilderness_area: int = Field(..., description="Área silvestre (numérico)")
    soil_type: int = Field(..., description="Tipo de suelo (numérico)")

    class Config:
        schema_extra = {
            "example": {
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
            }
        }

class PredictionResponse(BaseModel):
    """Respuesta de predicción"""
    cover_type: int = Field(..., description="Tipo de cobertura predicho (0-6)")
    probabilities: Dict[int, float] = Field(..., description="Probabilidades por clase")
    model_version: str = Field(..., description="Versión del modelo usado")

class ModelInfo(BaseModel):
    """Información de modelo"""
    name: str
    version: str
    stage: str
    run_id: str

# ==========================================
# Global Model Cache
# ==========================================

_model_cache = {
    "model": None,
    "version": None,
    "run_id": None
}

def load_latest_model():
    """Carga el modelo más reciente desde MLflow"""
    try:
        # Obtener cliente de MLflow
        client = mlflow.MlflowClient()
        
        # Intentar obtener todas las versiones del modelo
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        if not versions:
            raise ValueError(f"No se encontraron versiones para el modelo {MODEL_NAME}")
        
        # Ordenar por versión (descendente) y tomar la más reciente
        latest = sorted(versions, key=lambda x: int(x.version), reverse=True)[0]
        version = latest.version
        run_id = latest.run_id
        
        logger.info(f"Cargando modelo {MODEL_NAME} versión {version}")
        
        # Cargar modelo
        model_uri = f"models:/{MODEL_NAME}/{version}"
        model = mlflow.sklearn.load_model(model_uri)
        
        # Actualizar caché
        _model_cache["model"] = model
        _model_cache["version"] = version
        _model_cache["run_id"] = run_id
        
        logger.info(f"✅ Modelo cargado: v{version}, run_id={run_id}")
        return model
        
    except Exception as e:
        logger.error(f"❌ Error al cargar modelo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cargando modelo: {str(e)}")

# ==========================================
# Endpoints
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Cargar modelo al iniciar"""
    logger.info("🚀 Iniciando servicio de inferencia...")
    try:
        load_latest_model()
    except Exception as e:
        logger.warning(f"⚠️ No se pudo cargar modelo al inicio: {e}")

@app.get("/")
async def root():
    """Health check básico"""
    return {
        "service": "Covertype Inference API",
        "status": "running",
        "mlflow_uri": MLFLOW_TRACKING_URI
    }

@app.get("/health")
async def health():
    """Health check detallado"""
    model_loaded = _model_cache["model"] is not None
    
    return {
        "status": "healthy" if model_loaded else "starting",
        "model_loaded": model_loaded,
        "model_version": _model_cache.get("version"),
        "mlflow_tracking_uri": MLFLOW_TRACKING_URI
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(features: CovertypeFeatures):
    """
    Realiza predicción de tipo de cobertura forestal
    
    Returns:
        Tipo de cobertura predicho (0-6) y probabilidades por clase
    """
    try:
        # Verificar que el modelo esté cargado
        if _model_cache["model"] is None:
            logger.warning("⚠️ Modelo no cargado, intentando cargar...")
            load_latest_model()
        
        model = _model_cache["model"]
        
        # Convertir features a DataFrame
        feature_dict = features.dict()
        df = pd.DataFrame([feature_dict])
        
        # Asegurar orden correcto de columnas
        expected_columns = [
            'elevation', 'aspect', 'slope', 'horizontal_distance_to_hydrology',
            'vertical_distance_to_hydrology', 'horizontal_distance_to_roadways',
            'hillshade_9am', 'hillshade_noon', 'hillshade_3pm',
            'horizontal_distance_to_fire_points', 'wilderness_area', 'soil_type'
        ]
        df = df[expected_columns]
        
        # Predicción
        prediction = model.predict(df)[0]
        probabilities = model.predict_proba(df)[0]
        
        # Formatear probabilidades
        prob_dict = {
            int(class_idx): float(prob) 
            for class_idx, prob in enumerate(probabilities)
        }
        
        logger.info(f"✅ Predicción exitosa: cover_type={prediction}")
        
        return PredictionResponse(
            cover_type=int(prediction),
            probabilities=prob_dict,
            model_version=str(_model_cache["version"])
        )
        
    except Exception as e:
        logger.error(f"❌ Error en predicción: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """
    Lista todos los modelos registrados en MLflow
    """
    try:
        client = mlflow.MlflowClient()
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        models_info = []
        for version in versions:
            models_info.append(ModelInfo(
                name=version.name,
                version=version.version,
                stage=version.current_stage,
                run_id=version.run_id
            ))
        
        return models_info
        
    except Exception as e:
        logger.error(f"❌ Error listando modelos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando modelos: {str(e)}")

@app.post("/reload-model")
async def reload_model():
    """
    Recarga el modelo más reciente desde MLflow
    """
    try:
        load_latest_model()
        return {
            "status": "success",
            "message": "Modelo recargado exitosamente",
            "version": _model_cache["version"],
            "run_id": _model_cache["run_id"]
        }
    except Exception as e:
        logger.error(f"❌ Error recargando modelo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error recargando modelo: {str(e)}")

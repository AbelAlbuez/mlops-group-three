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
    """Carga el modelo más reciente desde MySQL (fallback cuando MLflow no funciona)"""
    try:
        # Intentar cargar desde MLflow primero
        try:
            client = mlflow.MlflowClient()
            experiment = client.get_experiment_by_name("covertype_classification")
            if experiment:
                runs = client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    order_by=["start_time DESC"],
                    max_results=1
                )
                if runs:
                    latest_run = runs[0]
                    run_id = latest_run.info.run_id
                    model_uri = f"runs:/{run_id}/model"
                    model = mlflow.sklearn.load_model(model_uri)
                    
                    _model_cache["model"] = model
                    _model_cache["version"] = "latest"
                    _model_cache["run_id"] = run_id
                    
                    logger.info(f"✅ Modelo cargado desde MLflow run {run_id}")
                    return model
        except Exception as mlflow_error:
            logger.warning(f"⚠️ MLflow no disponible: {mlflow_error}")
        
        # Fallback: cargar modelo desde MySQL usando joblib
        import joblib
        import pymysql
        import os
        
        # Conectar a MySQL
        connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "mysql-db"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "covertype_user"),
            password=os.getenv("MYSQL_PASSWORD", "covertype_pass123"),
            database=os.getenv("MYSQL_DATABASE", "covertype_db")
        )
        
        try:
            with connection.cursor() as cursor:
                # Obtener la métrica más reciente para obtener el modelo
                cursor.execute("""
                    SELECT model_data, created_at 
                    FROM model_metrics 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if not result:
                    raise ValueError("No se encontraron modelos en la base de datos")
                
                # El modelo se guarda como pickle en la columna model_data
                model_data = result[0]
                model = joblib.loads(model_data)
                
                _model_cache["model"] = model
                _model_cache["version"] = "mysql_latest"
                _model_cache["run_id"] = "mysql_fallback"
                
                logger.info("✅ Modelo cargado desde MySQL (fallback)")
                return model
                
        finally:
            connection.close()
        
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

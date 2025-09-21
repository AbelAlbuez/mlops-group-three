from pathlib import Path
from typing import Dict, List, Optional, Any
import os
import json
import pandas as pd
from fastapi import FastAPI, HTTPException, Path as FastAPIPath
from pydantic import BaseModel, Field
import mlflow
import mlflow.pyfunc
from mlflow.tracking import MlflowClient

# Config
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Schemas (reutilizamos los existentes)
class PenguinInput(BaseModel):
    bill_length_mm: float = Field(..., example=44.5)
    bill_depth_mm: float = Field(..., example=17.1)
    flipper_length_mm: float = Field(..., example=200)
    body_mass_g: float = Field(..., example=4200)
    island: Optional[str] = Field("Biscoe", example="Biscoe")
    sex: Optional[str] = Field("male", example="male")
    year: Optional[int] = Field(2008, example=2008)

class HealthResponse(BaseModel):
    status: str
    mlflow_tracking_uri: str
    models_loaded: int

class ModelsResponse(BaseModel):
    available_models: List[Dict[str, Any]]
    total_count: int

class PredictionResult(BaseModel):
    model: str
    model_version: str
    prediction: str
    probabilities: Optional[Dict[str, float]] = None

class PredictResponse(BaseModel):
    predictions: List[PredictionResult]

# App setup
app = FastAPI(
    title="Palmer Penguins MLflow API", 
    version="2.0.0",
    description="API de inferencia que carga modelos desde MLflow Model Registry"
)

# MLflow client
client = MlflowClient()

# Cache de modelos cargados
_model_cache = {}

# Helper functions
def get_registered_models() -> List[Dict[str, Any]]:
    """Obtener todos los modelos registrados en MLflow"""
    try:
        models = []
        for rm in client.search_registered_models():
            model_info = {
                "name": rm.name,
                "description": rm.description,
                "versions": []
            }
            
            # Obtener versiones del modelo
            for mv in client.search_model_versions(f"name='{rm.name}'"):
                version_info = {
                    "version": mv.version,
                    "stage": mv.current_stage,
                    "status": mv.status,
                    "run_id": mv.run_id
                }
                model_info["versions"].append(version_info)
            
            models.append(model_info)
        
        return models
    except Exception as e:
        print(f"Error obteniendo modelos registrados: {e}")
        return []

def load_model_from_registry(model_name: str, stage: str = "Production") -> Any:
    """Cargar modelo desde MLflow Registry con caché"""
    cache_key = f"{model_name}/{stage}"
    
    if cache_key not in _model_cache:
        try:
            model_uri = f"models:/{model_name}/{stage}"
            _model_cache[cache_key] = mlflow.pyfunc.load_model(model_uri)
            print(f"Modelo cargado: {model_name} (stage: {stage})")
        except Exception as e:
            print(f"Error cargando modelo {model_name}: {e}")
            raise HTTPException(
                status_code=404, 
                detail=f"No se pudo cargar el modelo '{model_name}' en stage '{stage}'"
            )
    
    return _model_cache[cache_key]

def prepare_input(input_data: PenguinInput) -> pd.DataFrame:
    """Preparar datos de entrada para predicción"""
    # Crear DataFrame básico con features numéricas
    df = pd.DataFrame([{
        "bill_length_mm": input_data.bill_length_mm,
        "bill_depth_mm": input_data.bill_depth_mm,
        "flipper_length_mm": input_data.flipper_length_mm,
        "body_mass_g": input_data.body_mass_g
    }])
    
    # Añadir features opcionales si están presentes
    if input_data.island:
        df["island"] = input_data.island
    if input_data.sex:
        df["sex"] = input_data.sex
    if input_data.year:
        df["year"] = input_data.year
    
    return df

def make_prediction_mlflow(
    input_data: PenguinInput, 
    model_name: str, 
    model_version: str,
    model
) -> Dict:
    """Hacer predicción usando modelo de MLflow"""
    df = prepare_input(input_data)
    
    try:
        # Hacer predicción
        prediction = model.predict(df)
        
        # Si es un array numpy, tomar el primer elemento
        if hasattr(prediction, '__array__'):
            pred_value = prediction[0]
        else:
            pred_value = prediction
        
        # Mapear a nombre de especie si es numérico
        species_map = {0: "Adelie", 1: "Chinstrap", 2: "Gentoo"}
        if isinstance(pred_value, (int, float)) and int(pred_value) in species_map:
            pred_name = species_map[int(pred_value)]
        else:
            pred_name = str(pred_value)
        
        result = {
            "model": model_name,
            "model_version": model_version,
            "prediction": pred_name
        }
        
        # Intentar obtener probabilidades si el modelo las proporciona
        if hasattr(model._model_impl, "predict_proba"):
            try:
                probs = model._model_impl.predict_proba(df)[0]
                prob_dict = {species_map.get(i, str(i)): float(p) for i, p in enumerate(probs)}
                result["probabilities"] = prob_dict
            except:
                pass
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")

# API endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    return {
        "message": "Palmer Penguins MLflow API",
        "version": "2.0.0",
        "mlflow_uri": MLFLOW_TRACKING_URI
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    models = get_registered_models()
    model_count = sum(len(m["versions"]) for m in models)
    
    return HealthResponse(
        status="healthy",
        mlflow_tracking_uri=MLFLOW_TRACKING_URI,
        models_loaded=model_count
    )

@app.get("/models", response_model=ModelsResponse)
async def get_models():
    models = get_registered_models()
    
    # Filtrar solo modelos con versiones en Production o Staging
    available_models = []
    for model in models:
        prod_staging_versions = [
            v for v in model["versions"] 
            if v["stage"] in ["Production", "Staging"]
        ]
        if prod_staging_versions:
            model_copy = model.copy()
            model_copy["versions"] = prod_staging_versions
            available_models.append(model_copy)
    
    return ModelsResponse(
        available_models=available_models,
        total_count=len(available_models)
    )

@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: PenguinInput):
    """Predecir con todos los modelos en Production"""
    models = get_registered_models()
    predictions = []
    
    for model_info in models:
        # Buscar versión en Production
        prod_versions = [
            v for v in model_info["versions"] 
            if v["stage"] == "Production"
        ]
        
        if not prod_versions:
            continue
        
        # Usar la versión más reciente en Production
        latest_prod = max(prod_versions, key=lambda v: int(v["version"]))
        
        try:
            model = load_model_from_registry(model_info["name"], "Production")
            prediction = make_prediction_mlflow(
                input_data, 
                model_info["name"],
                latest_prod["version"],
                model
            )
            predictions.append(PredictionResult(**prediction))
        except Exception as e:
            print(f"Error con modelo {model_info['name']}: {e}")
            continue
    
    if not predictions:
        raise HTTPException(
            status_code=503, 
            detail="No hay modelos en Production disponibles para predicción"
        )
    
    return PredictResponse(predictions=predictions)

@app.post("/predict/{model_name}", response_model=PredictionResult)
async def predict_with_model(
    input_data: PenguinInput, 
    model_name: str = FastAPIPath(...)
):
    """Predecir con un modelo específico"""
    # Cargar modelo desde registry
    try:
        model = load_model_from_registry(model_name, "Production")
    except:
        # Si no hay en Production, intentar Staging
        try:
            model = load_model_from_registry(model_name, "Staging")
            stage = "Staging"
        except:
            raise HTTPException(
                status_code=404,
                detail=f"Modelo '{model_name}' no encontrado en Production o Staging"
            )
    else:
        stage = "Production"
    
    # Obtener versión del modelo
    versions = client.search_model_versions(f"name='{model_name}'")
    version_info = next(
        (v for v in versions if v.current_stage == stage),
        None
    )
    
    if not version_info:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró información de versión para {model_name}"
        )
    
    prediction = make_prediction_mlflow(
        input_data,
        model_name,
        version_info.version,
        model
    )
    
    return PredictionResult(**prediction)

@app.post("/predict/{model_name}/{version}", response_model=PredictionResult)
async def predict_with_model_version(
    input_data: PenguinInput,
    model_name: str = FastAPIPath(...),
    version: str = FastAPIPath(...)
):
    """Predecir con una versión específica de un modelo"""
    model_uri = f"models:/{model_name}/{version}"
    
    try:
        model = mlflow.pyfunc.load_model(model_uri)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo cargar {model_name} versión {version}: {str(e)}"
        )
    
    prediction = make_prediction_mlflow(
        input_data,
        model_name,
        version,
        model
    )
    
    return PredictionResult(**prediction)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
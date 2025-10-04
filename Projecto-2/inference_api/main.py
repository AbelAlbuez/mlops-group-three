from typing import List, Optional, Dict, Any
import os
import time
import pandas as pd
import numpy as np
import mlflow
from mlflow.tracking import MlflowClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

# -------- Config --------
MODEL_NAME = os.getenv("MODEL_NAME", "covertype_rf")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
# Para MinIO (S3 compatible):
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#   MLFLOW_S3_ENDPOINT_URL=http://minio:9000
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
client = MlflowClient()

app = FastAPI(title="Inference API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# -------- Carga de modelo desde el Registry --------
_model = None
_model_version_info: Dict[str, Any] = {}

def _load_production_or_latest(model_name: str):
    # 1) Intentar el último en "Production"
    versions = client.get_latest_versions(model_name, stages=["Production"])
    chosen = None
    if versions:
        chosen = versions[0]
    else:
        # 2) Fallback: última versión por número
        all_versions = client.search_model_versions(f"name='{model_name}'")
        if not all_versions:
            raise RuntimeError(f"No hay versiones registradas para el modelo '{model_name}'.")
        chosen = sorted(all_versions, key=lambda v: int(v.version))[-1]

    uri = f"models:/{model_name}/{chosen.current_stage or chosen.version}"
    start = time.time()
    model = mlflow.pyfunc.load_model(uri)
    elapsed = time.time() - start
    info = {
        "name": model_name,
        "version": chosen.version,
        "stage": chosen.current_stage,
        "run_id": chosen.run_id,
        "source": chosen.source,
        "load_time_s": round(elapsed, 3),
        "uri": uri
    }
    return model, info

def ensure_model_loaded():
    global _model, _model_version_info
    if _model is None:
        _model, _model_version_info = _load_production_or_latest(MODEL_NAME)

# -------- Esquemas de entrada/salida --------
# Usamos el esquema “compacto” del proyecto (13 + 4 columnas),
# NO los 54 dummies originales de Kaggle.
FEATURES = [
    "elevation","aspect","slope",
    "horizontal_distance_to_hydrology","vertical_distance_to_hydrology",
    "horizontal_distance_to_roadways",
    "hillshade_9am","hillshade_noon","hillshade_3pm",
    "horizontal_distance_to_fire_points",
    "wilderness_area","soil_type"
]

class PredictItem(BaseModel):
    elevation: int = Field(..., ge=0)
    aspect: int = Field(..., ge=0)
    slope: int = Field(..., ge=0)
    horizontal_distance_to_hydrology: int = Field(..., ge=0)
    vertical_distance_to_hydrology: int
    horizontal_distance_to_roadways: int = Field(..., ge=0)
    hillshade_9am: int = Field(..., ge=0, le=255)
    hillshade_noon: int = Field(..., ge=0, le=255)
    hillshade_3pm: int = Field(..., ge=0, le=255)
    horizontal_distance_to_fire_points: int = Field(..., ge=0)
    wilderness_area: int = Field(..., ge=0)  # ya codificado según tu pipeline
    soil_type: int = Field(..., ge=0)        # id numérico, no string

class PredictRequest(BaseModel):
    rows: List[PredictItem]

class PredictResponse(BaseModel):
    predictions: List[int]
    probabilities: Optional[List[List[float]]] = None
    model: Dict[str, Any]

# -------- Endpoints --------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"service": "Inference API", "model": MODEL_NAME}

@app.get("/model-info")
def model_info():
    ensure_model_loaded()
    return _model_version_info

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    ensure_model_loaded()
    if not req.rows:
        raise HTTPException(400, "rows vacío.")

    df = pd.DataFrame([r.model_dump() for r in req.rows])[FEATURES]
    try:
        preds = _model.predict(df)
        proba = None
        # Si el modelo soporta predict_proba
        if hasattr(_model._model_impl, "predict_proba"):
            proba = _model._model_impl.predict_proba(df).tolist()
        return PredictResponse(
            predictions=[int(p) for p in np.array(preds).ravel().tolist()],
            probabilities=proba,
            model=_model_version_info
        )
    except Exception as e:
        raise HTTPException(500, f"Error en inferencia: {e}")

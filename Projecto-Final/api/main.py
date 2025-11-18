import os
from typing import Dict, Any, List, Optional

import mlflow
from mlflow.tracking import MlflowClient
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "real_estate_rf")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow_client = MlflowClient()

app = FastAPI(
    title="Real Estate Inference API",
    description="API para servir el modelo de precios de vivienda en producción desde MLflow",
    version="1.0.0",
)

# Variables globales
current_model = None
current_model_info: Dict[str, Any] = {}


class PredictionRequest(BaseModel):

    features: Dict[str, float]


class PredictionResponse(BaseModel):
    predicted_price: float
    model_name: str
    model_version: str
    model_stage: str
    run_id: str


class ModelInfo(BaseModel):
    model_name: str
    model_version: str
    model_stage: str
    run_id: str
    metrics: Dict[str, float]

    model_config = {"protected_namespaces": ()}
    
class RealEstateFeatures(BaseModel):
    bed: float
    bath: float
    acre_lot: float
    house_size: float
    status: str
    city: str
    state: str
    zip_code: str


class ModelHistoryItem(BaseModel):
    model_name: str
    model_version: str
    model_stage: str
    run_id: str
    metrics: Dict[str, float]
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    creation_timestamp: Optional[int] = None  # ms desde epoch

    model_config = {"protected_namespaces": ()}


def _extract_feature_names_from_model(model) -> Optional[List[str]]:

    try:
        # Desempaquetar PyFuncModel -> python_model -> model (sklearn)
        sk_model = None
        if hasattr(model, "_model_impl") and hasattr(model._model_impl, "python_model"):
            py_model = model._model_impl.python_model
            if hasattr(py_model, "model"):
                sk_model = py_model.model
            else:
                sk_model = py_model
        else:
            sk_model = model

        if hasattr(sk_model, "feature_names_in_"):
            names = list(sk_model.feature_names_in_)
            print(f"[startup] feature_names_in_ detectadas ({len(names)}): {names[:10]} ...")
            return names

    except Exception as e:
        print(f"[startup] No se pudieron extraer feature_names_in_: {e}")

    return None


def load_production_model():

    global current_model, current_model_info

    latest_production = mlflow_client.get_latest_versions(
        name=MODEL_NAME,
        stages=["Production"],
    )

    if not latest_production:
        raise RuntimeError(
            f"No se encontró ningún modelo en stage 'Production' para MODEL_NAME={MODEL_NAME}"
        )

    mv = latest_production[0]

    model_uri = f"models:/{MODEL_NAME}/{mv.version}"
    loaded_model = mlflow.pyfunc.load_model(model_uri)

    run = mlflow_client.get_run(mv.run_id)
    metrics = dict(run.data.metrics)

    current_model = loaded_model
    current_model_info = {
        "model_name": MODEL_NAME,
        "model_version": mv.version,
        "model_stage": mv.current_stage,
        "run_id": mv.run_id,
        "metrics": metrics,
    }

    print(f"[startup] Modelo cargado: {current_model_info}")


def get_model_history() -> List[ModelHistoryItem]:
    versions = mlflow_client.search_model_versions(f"name='{MODEL_NAME}'")
    history: List[ModelHistoryItem] = []

    for mv in versions:
        run = mlflow_client.get_run(mv.run_id)
        metrics = dict(run.data.metrics)
        tags = run.data.tags

        item = ModelHistoryItem(
            model_name=mv.name,
            model_version=mv.version,
            model_stage=mv.current_stage,
            run_id=mv.run_id,
            metrics=metrics,
            status=tags.get("status"),
            rejection_reason=tags.get("rejection_reason"),
            creation_timestamp=mv.creation_timestamp,
        )
        history.append(item)

    history.sort(key=lambda x: int(x.model_version))
    return history

@app.on_event("startup")
def on_startup():
    try:
        load_production_model()
    except Exception as e:
        print(f"[startup] Error cargando modelo en Production: {e}")


@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {
        "status": "ok",
        "model_loaded": current_model is not None,
        "model_info": current_model_info or None,
    }


@app.get("/model-info", response_model=ModelInfo)
def get_current_model_info():
    if current_model is None or not current_model_info:
        raise HTTPException(
            status_code=503,
            detail="Modelo no cargado. Revisa MLflow o los logs del contenedor.",
        )

    return ModelInfo(
        model_name=current_model_info["model_name"],
        model_version=str(current_model_info["model_version"]),
        model_stage=current_model_info["model_stage"],
        run_id=current_model_info["run_id"],
        metrics=current_model_info["metrics"],
    )


@app.get("/models/history", response_model=List[ModelHistoryItem])
def models_history():
    try:
        history = get_model_history()
        return history
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial de modelos: {e}",
        )


@app.post("/predict", response_model=PredictionResponse)
def predict(request: RealEstateFeatures):

    if current_model is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo no cargado. Revisa MLflow o los logs del contenedor.",
        )

    try:
        data = request.model_dump()
        X = pd.DataFrame([data])

        y_pred = current_model.predict(X)
        pred_value = float(y_pred[0])

        return PredictionResponse(
            predicted_price=pred_value,
            model_name=current_model_info.get("model_name"),
            model_version=current_model_info.get("model_version"),
            model_stage=current_model_info.get("model_stage"),
            run_id=current_model_info.get("run_id"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error haciendo la predicción: {e}",
        )

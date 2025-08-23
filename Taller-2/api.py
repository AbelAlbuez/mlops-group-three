from pathlib import Path
from typing import Dict, List, Optional, Any
import os
import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Path as FastAPIPath
from pydantic import BaseModel, Field

# Config
ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models"

# Schemas
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
    models_loaded: int
    models_directory: str

class ModelsResponse(BaseModel):
    available_models: List[str]
    total_count: int

class PredictionResult(BaseModel):
    model: str
    prediction: str
    probabilities: Optional[Dict[str, float]] = None

class PredictResponse(BaseModel):
    predictions: List[PredictionResult]

# App setup
app = FastAPI(title="Palmer Penguins ML API", version="1.0.0")

# Helper functions
def load_models_from_directory() -> Dict[str, Any]:
    models = {}
    if not MODELS_DIR.exists():
        return models
    
    for pkl_file in MODELS_DIR.glob("*.pkl"):
        try:
            models[pkl_file.stem] = joblib.load(pkl_file)
        except Exception:
            continue
    return models

def expected_columns(pipe) -> List[str]:
    # Try to get feature names from pipeline steps
    if hasattr(pipe, 'named_steps'):
        for step_name in ("scaler", "identity", "preprocessor", "clf"):
            step = pipe.named_steps.get(step_name)
            if step and hasattr(step, "feature_names_in_"):
                return list(step.feature_names_in_)
    
    # Try direct model feature names
    if hasattr(pipe, "feature_names_in_"):
        return list(pipe.feature_names_in_)
    
    # Fallback
    return ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]

def expand_features(df: pd.DataFrame, expected_cols: List[str]) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # Numeric features
    for col in ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]:
        if col in expected_cols:
            out[col] = df.get(col, 0)

    # Year
    if "year" in expected_cols:
        out["year"] = df.get("year", 2008)

    # Sex encoding
    if any(col.startswith("sex_") for col in expected_cols):
        sex = df.get("sex", "male").astype(str).str.lower()
        if "sex_male" in expected_cols:
            out["sex_male"] = (sex == "male").astype(int)
        if "sex_female" in expected_cols:
            out["sex_female"] = (sex == "female").astype(int)

    # Island encoding
    if any(col.startswith("island_") for col in expected_cols):
        island = df.get("island", "Biscoe").astype(str)
        for col in expected_cols:
            if col.startswith("island_"):
                value = col.split("island_", 1)[1]
                out[col] = (island == value).astype(int)

    # Fill missing columns
    for col in expected_cols:
        if col not in out.columns:
            out[col] = 0

    return out[expected_cols]

def prepare_input(input_data: PenguinInput, model) -> pd.DataFrame:
    df = pd.DataFrame([input_data.dict()])
    exp_cols = expected_columns(model)
    return expand_features(df, exp_cols)

def make_prediction(input_data: PenguinInput, model_name: str, model) -> Dict:
    df = prepare_input(input_data, model)
    pred_idx = model.predict(df)[0]

    # Cargar nombres de clases reales desde model_metadata.json
    metadata_path = MODELS_DIR / "model_metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            meta = json.load(f)
            classes_names = meta.get("classes", None)
    else:
        classes_names = None

    # Mapear índice a nombre si hay metadata
    if classes_names:
        pred_name = classes_names[pred_idx]
    else:
        pred_name = str(pred_idx)  # fallback a número

    result = {
        "model": model_name,
        "prediction": pred_name
    }

    # Agregar probabilidades con nombres reales si existen
    if hasattr(model, "predict_proba"):
        try:
            probs = model.predict_proba(df)[0]
            if classes_names and len(classes_names) == len(probs):
                prob_dict = {classes_names[i]: float(probs[i]) for i in range(len(classes_names))}
            else:
                prob_dict = {str(i): float(probs[i]) for i in range(len(probs))}
            result["probabilities"] = prob_dict
        except Exception:
            pass

    return result

# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    models = load_models_from_directory()
    return HealthResponse(
        status="healthy",
        models_loaded=len(models),
        models_directory=str(MODELS_DIR)
    )

@app.get("/models", response_model=ModelsResponse)
async def get_models():
    models = load_models_from_directory()
    return ModelsResponse(
        available_models=list(models.keys()),
        total_count=len(models)
    )

@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: PenguinInput):
    models = load_models_from_directory()
    if not models:
        raise HTTPException(status_code=503, detail="No models are currently loaded")
    
    predictions = []
    for model_name, model in models.items():
        try:
            prediction = make_prediction(input_data, model_name, model)
            predictions.append(PredictionResult(**prediction))
        except Exception:
            continue
    
    if not predictions:
        raise HTTPException(status_code=500, detail="All models failed to make predictions")
    
    return PredictResponse(predictions=predictions)

@app.post("/predict/{model_name}", response_model=PredictionResult)
async def predict_with_model(input_data: PenguinInput, model_name: str = FastAPIPath(...)):
    models = load_models_from_directory()
    if model_name not in models:
        raise HTTPException(
            status_code=404, 
            detail=f"Model '{model_name}' not found. Available: {list(models.keys())}"
        )
    
    try:
        prediction = make_prediction(input_data, model_name, models[model_name])
        return PredictionResult(**prediction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8888))
    uvicorn.run(app, host="0.0.0.0", port=port)
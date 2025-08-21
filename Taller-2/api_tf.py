from pathlib import Path
from typing import Dict, List, Optional, Any
import os
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Path as FastAPIPath
from pydantic import BaseModel, Field

try:
    import tensorflow as tf
except ImportError:
    raise ImportError("TensorFlow is required. Install with: pip install tensorflow")

# Config
ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models_tf"

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
    tensorflow_version: str

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
app = FastAPI(title="Palmer Penguins TensorFlow API", version="1.0.0")

# Helper functions
def load_models_from_directory() -> Dict[str, Any]:
    models = {}
    if not MODELS_DIR.exists():
        return models
    
    # Load SavedModel format (.pb files in directories)
    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir():
            try:
                model = tf.keras.models.load_model(str(model_dir))
                models[model_dir.name] = model
            except Exception:
                continue
    
    # Load .h5 files
    for h5_file in MODELS_DIR.glob("*.h5"):
        try:
            model = tf.keras.models.load_model(str(h5_file))
            models[h5_file.stem] = model
        except Exception:
            continue
    
    return models

def prepare_input_tf(input_data: PenguinInput) -> np.ndarray:
    # Convert input to numpy array for TensorFlow
    data = input_data.dict()
    
    # Create feature vector with numeric features
    features = [
        data["bill_length_mm"],
        data["bill_depth_mm"], 
        data["flipper_length_mm"],
        data["body_mass_g"]
    ]
    
    # Add year if provided
    if data.get("year"):
        features.append(data["year"])
    
    # One-hot encode categorical features
    # Island encoding (Biscoe=0, Dream=1, Torgersen=2)
    island_map = {"Biscoe": 0, "Dream": 1, "Torgersen": 2}
    island_encoded = island_map.get(data.get("island", "Biscoe"), 0)
    
    # Sex encoding (male=0, female=1)
    sex_encoded = 1 if data.get("sex", "male").lower() == "female" else 0
    
    features.extend([island_encoded, sex_encoded])
    
    # Convert to numpy array and reshape for batch prediction
    return np.array(features).reshape(1, -1).astype(np.float32)

def make_prediction_tf(input_data: PenguinInput, model_name: str, model) -> Dict:
    # Prepare input
    X = prepare_input_tf(input_data)
    
    # Make prediction
    predictions = model.predict(X, verbose=0)
    
    # Handle different output formats
    if len(predictions.shape) == 2 and predictions.shape[1] > 1:
        # Multi-class classification with probabilities
        class_names = ["Adelie", "Chinstrap", "Gentoo"]  # Common penguin species
        predicted_class = np.argmax(predictions[0])
        prediction = class_names[predicted_class]
        
        # Get probabilities
        probabilities = {
            class_names[i]: float(predictions[0][i]) 
            for i in range(len(class_names)) 
            if i < predictions.shape[1]
        }
        
        return {
            "model": model_name,
            "prediction": prediction,
            "probabilities": probabilities
        }
    else:
        # Binary classification or regression
        pred_value = float(predictions[0][0])
        
        if pred_value > 0.5:  # Assuming binary classification threshold
            prediction = "Positive"
            probabilities = {"Positive": pred_value, "Negative": 1 - pred_value}
        else:
            prediction = "Negative" 
            probabilities = {"Positive": pred_value, "Negative": 1 - pred_value}
        
        return {
            "model": model_name,
            "prediction": prediction,
            "probabilities": probabilities
        }

# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    models = load_models_from_directory()
    return HealthResponse(
        status="healthy",
        models_loaded=len(models),
        models_directory=str(MODELS_DIR),
        tensorflow_version=tf.__version__
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
        raise HTTPException(status_code=503, detail="No TensorFlow models are currently loaded")
    
    predictions = []
    for model_name, model in models.items():
        try:
            prediction = make_prediction_tf(input_data, model_name, model)
            predictions.append(PredictionResult(**prediction))
        except Exception:
            continue
    
    if not predictions:
        raise HTTPException(status_code=500, detail="All TensorFlow models failed to make predictions")
    
    return PredictResponse(predictions=predictions)

@app.post("/predict/{model_name}", response_model=PredictionResult)
async def predict_with_model(input_data: PenguinInput, model_name: str = FastAPIPath(...)):
    models = load_models_from_directory()
    if model_name not in models:
        raise HTTPException(
            status_code=404, 
            detail=f"TensorFlow model '{model_name}' not found. Available: {list(models.keys())}"
        )
    
    try:
        prediction = make_prediction_tf(input_data, model_name, models[model_name])
        return PredictionResult(**prediction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TensorFlow prediction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8889)) 
    uvicorn.run(app, host="0.0.0.0", port=port)

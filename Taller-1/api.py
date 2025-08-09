from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, List, Dict, Any
from enum import Enum
import joblib
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Pydantic Models
class ModelType(str, Enum):
    RANDOM_FOREST = "random_forest"
    KNN = "knn"
    SVM = "svm"

class PenguinFeatures(BaseModel):
    bill_length_mm: float = Field(..., ge=0, le=100)
    bill_depth_mm: float = Field(..., ge=0, le=50)
    flipper_length_mm: float = Field(..., ge=0, le=300)
    body_mass_g: float = Field(..., ge=0, le=10000)
    island: Literal["Torgersen", "Biscoe", "Dream"]
    sex: Literal["male", "female"]
    
    class Config:
        schema_extra = {
            "example": {
                "bill_length_mm": 39.1,
                "bill_depth_mm": 18.7,
                "flipper_length_mm": 181.0,
                "body_mass_g": 3750.0,
                "island": "Torgersen",
                "sex": "male"
            }
        }

class PredictionResponse(BaseModel):
    model_used: str
    species: str
    confidence: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None

class MultiModelPredictionResponse(BaseModel):
    predictions: List[PredictionResponse]
    consensus: Optional[str] = None

# Model Manager Class
class ModelManager:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models = {}
        self.scalers = {}
        self.registry = {}
        self._load_registry()
        self._load_models()
    
    def _load_registry(self):
        """Load model registry"""
        registry_path = self.models_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path, "r") as f:
                self.registry = json.load(f)
        else:
            raise FileNotFoundError("registry.json not found in models directory")
    
    def _load_models(self):
        """Load all models and scalers"""
        for model_name, config in self.registry["models"].items():
            # Load model
            model_path = self.models_dir / config["model_file"]
            if model_path.exists():
                self.models[model_name] = joblib.load(model_path)
            else:
                print(f"Warning: Model {config['model_file']} not found")
            
            # Load scaler if needed
            if config["scaler_file"]:
                scaler_path = self.models_dir / config["scaler_file"]
                if scaler_path.exists():
                    self.scalers[model_name] = joblib.load(scaler_path)
    
    def preprocess_features(self, features: PenguinFeatures, model_name: str) -> np.ndarray:
        """Preprocess features for model"""
        # Create one-hot encoded features
        data = {
            'bill_length_mm': features.bill_length_mm,
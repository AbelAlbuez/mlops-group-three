#!/usr/bin/env python3
"""
API de inferencia simple para pruebas de carga con Locust.
Esta API simula el comportamiento de una API de inferencia de ML.
"""

import os
import json
import random
import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configuración
app = FastAPI(
    title="Covertype Inference API",
    description="API de inferencia para el modelo de covertype",
    version="1.0.0"
)

# Modelo de datos para la predicción
class CovertypePrediction(BaseModel):
    elevation: int
    aspect: int
    slope: int
    horizontal_distance_to_hydrology: int
    vertical_distance_to_hydrology: int
    horizontal_distance_to_roadways: int
    hillshade_9am: int
    hillshade_noon: int
    hillshade_3pm: int
    horizontal_distance_to_fire_points: int
    wilderness_area: int
    soil_type: int

class PredictionResponse(BaseModel):
    prediction: int
    confidence: float
    model_version: str

# Variables globales
MODEL_VERSION = "1.0.0"
MODEL_LOADED = False

def load_model():
    """Simular carga del modelo"""
    global MODEL_LOADED
    print("Cargando modelo de covertype...")
    time.sleep(2)  # Simular tiempo de carga
    MODEL_LOADED = True
    print("Modelo cargado exitosamente")

def predict_covertype(data: CovertypePrediction) -> PredictionResponse:
    """
    Realizar predicción de covertype.
    Esta es una simulación que genera predicciones aleatorias.
    """
    if not MODEL_LOADED:
        load_model()
    
    # Simular tiempo de procesamiento
    processing_time = random.uniform(0.01, 0.1)
    time.sleep(processing_time)
    
    # Generar predicción aleatoria (1-7 para covertype)
    prediction = random.randint(1, 7)
    confidence = random.uniform(0.7, 0.99)
    
    return PredictionResponse(
        prediction=prediction,
        confidence=confidence,
        model_version=MODEL_VERSION
    )

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("Iniciando API de inferencia de covertype...")
    load_model()
    print("API lista para recibir peticiones")

@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "model_loaded": MODEL_LOADED,
        "model_version": MODEL_VERSION,
        "timestamp": time.time()
    }

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Covertype Inference API",
        "version": MODEL_VERSION,
        "endpoints": ["/health", "/predict", "/docs"]
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(data: CovertypePrediction):
    """
    Endpoint principal para predicciones de covertype.
    
    Args:
        data: Datos de entrada con las 12 features del modelo
        
    Returns:
        Predicción del tipo de covertype (1-7)
    """
    try:
        # Validar datos de entrada
        if not all([
            1800 <= data.elevation <= 3800,
            0 <= data.aspect <= 360,
            0 <= data.slope <= 65,
            0 <= data.horizontal_distance_to_hydrology <= 1400,
            -170 <= data.vertical_distance_to_hydrology <= 600,
            0 <= data.horizontal_distance_to_roadways <= 7000,
            0 <= data.hillshade_9am <= 255,
            0 <= data.hillshade_noon <= 255,
            0 <= data.hillshade_3pm <= 255,
            0 <= data.horizontal_distance_to_fire_points <= 7000,
            0 <= data.wilderness_area <= 3,
            0 <= data.soil_type <= 40
        ]):
            raise HTTPException(
                status_code=422,
                detail="Datos de entrada fuera del rango válido"
            )
        
        # Realizar predicción
        result = predict_covertype(data)
        
        return result
        
    except Exception as e:
        print(f"Error en predicción: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@app.get("/model/info")
async def model_info():
    """Información del modelo"""
    return {
        "model_name": "covertype_classifier",
        "version": MODEL_VERSION,
        "features": [
            "elevation", "aspect", "slope",
            "horizontal_distance_to_hydrology", "vertical_distance_to_hydrology",
            "horizontal_distance_to_roadways", "hillshade_9am", "hillshade_noon",
            "hillshade_3pm", "horizontal_distance_to_fire_points",
            "wilderness_area", "soil_type"
        ],
        "feature_count": 12,
        "prediction_classes": 7,
        "model_loaded": MODEL_LOADED
    }

if __name__ == "__main__":
    # Configuración del servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Iniciando servidor en {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

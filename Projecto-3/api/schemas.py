"""
Pydantic schemas para validación de datos de entrada y salida
"""
from pydantic import BaseModel, Field
from typing import Optional


class PatientInput(BaseModel):
    """Schema para datos de entrada del paciente"""
    
    # Demographics
    race: str = Field(..., description="Race of the patient")
    gender: str = Field(..., description="Gender: Male, Female, Unknown/Invalid")
    age_bucket: str = Field(..., description="Age bucket, e.g., [70-80)")
    
    # Hospital stay info
    time_in_hospital: int = Field(..., ge=1, le=14, description="Days in hospital (1-14)")
    
    # Medical procedures and tests
    num_lab_procedures: int = Field(..., ge=0, description="Number of lab procedures")
    num_procedures: int = Field(..., ge=0, description="Number of procedures")
    num_medications: int = Field(..., ge=0, description="Number of medications")
    
    # Visit history
    number_outpatient: int = Field(..., ge=0, description="Number of outpatient visits")
    number_emergency: int = Field(..., ge=0, description="Number of emergency visits")
    number_inpatient: int = Field(..., ge=0, description="Number of inpatient visits")
    number_diagnoses: int = Field(..., ge=0, description="Number of diagnoses")
    
    # Test results
    max_glu_serum: Optional[str] = Field(None, description="Max glucose serum test result")
    a1c_result: Optional[str] = Field(None, description="A1C test result")
    
    # Medications
    insulin: str = Field(..., description="Insulin prescription status")
    change_med: bool = Field(..., description="Change in medication")
    diabetes_med: bool = Field(..., description="Diabetes medication prescribed")
    
    # Diagnoses codes
    diag_1: str = Field(..., description="Primary diagnosis")
    diag_2: Optional[str] = Field(None, description="Secondary diagnosis")
    diag_3: Optional[str] = Field(None, description="Tertiary diagnosis")
    
    # Medical specialty
    medical_specialty: Optional[str] = Field(None, description="Admitting physician specialty")
    
    # Administrative
    admission_type_id: int = Field(..., description="Admission type ID")
    discharge_disposition_id: int = Field(..., description="Discharge disposition ID")
    admission_source_id: int = Field(..., description="Admission source ID")

    class Config:
        json_schema_extra = {
            "example": {
                "race": "Caucasian",
                "gender": "Female",
                "age_bucket": "[70-80)",
                "time_in_hospital": 3,
                "num_lab_procedures": 41,
                "num_procedures": 0,
                "num_medications": 11,
                "number_outpatient": 0,
                "number_emergency": 0,
                "number_inpatient": 0,
                "number_diagnoses": 6,
                "max_glu_serum": "None",
                "a1c_result": "None",
                "insulin": "Steady",
                "change_med": True,
                "diabetes_med": True,
                "diag_1": "428",
                "diag_2": "250.01",
                "diag_3": "401",
                "medical_specialty": "Cardiology",
                "admission_type_id": 1,
                "discharge_disposition_id": 1,
                "admission_source_id": 7
            }
        }


class PredictionOutput(BaseModel):
    """Schema para respuesta de predicción"""
    model_config = {"protected_namespaces": ()}
    
    prediction: int = Field(..., description="0 = Low risk, 1 = High risk (<30 days)")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of high risk")
    risk_level: str = Field(..., description="Human readable risk level")
    model_name: str = Field(..., description="Name of the model used")
    model_version: str = Field(..., description="Version of the model used")
    model_stage: str = Field(..., description="Stage of the model (Production)")


class ModelInfo(BaseModel):
    """Schema para información del modelo"""
    model_config = {"protected_namespaces": ()}
    
    model_name: str
    model_version: str
    model_stage: str
    run_id: str
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    last_updated: Optional[str] = None


class HealthCheck(BaseModel):
    """Schema para health check"""
    model_config = {"protected_namespaces": ()}
    
    status: str
    mlflow_connected: bool
    model_loaded: bool
    model_info: Optional[ModelInfo] = None
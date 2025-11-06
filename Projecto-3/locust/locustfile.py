from locust import HttpUser, task, between
import random

class PredictionUser(HttpUser):
    """Usuario que realiza predicciones"""
    
    # Tiempo de espera entre requests (1-3 segundos)
    wait_time = between(1, 3)
    
    # Ejemplos de pacientes para probar
    patient_examples = [
        {
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
        },
        {
            "race": "AfricanAmerican",
            "gender": "Male",
            "age_bucket": "[80-90)",
            "time_in_hospital": 7,
            "num_lab_procedures": 65,
            "num_procedures": 3,
            "num_medications": 18,
            "number_outpatient": 2,
            "number_emergency": 1,
            "number_inpatient": 1,
            "number_diagnoses": 9,
            "max_glu_serum": ">300",
            "a1c_result": ">8",
            "insulin": "Up",
            "change_med": True,
            "diabetes_med": True,
            "diag_1": "250.01",
            "diag_2": "428",
            "diag_3": "401",
            "medical_specialty": "InternalMedicine",
            "admission_type_id": 1,
            "discharge_disposition_id": 1,
            "admission_source_id": 7
        },
        {
            "race": "Hispanic",
            "gender": "Female",
            "age_bucket": "[60-70)",
            "time_in_hospital": 5,
            "num_lab_procedures": 50,
            "num_procedures": 1,
            "num_medications": 14,
            "number_outpatient": 1,
            "number_emergency": 0,
            "number_inpatient": 0,
            "number_diagnoses": 7,
            "max_glu_serum": "None",
            "a1c_result": "Norm",
            "insulin": "No",
            "change_med": False,
            "diabetes_med": True,
            "diag_1": "414",
            "diag_2": "250",
            "diag_3": "401",
            "medical_specialty": "Cardiology",
            "admission_type_id": 1,
            "discharge_disposition_id": 1,
            "admission_source_id": 7
        }
    ]
    
    @task(1)
    def health_check(self):
        """Verificar que la API esté disponible"""
        self.client.get("/health", name="Health Check")
    
    @task(2)
    def get_model_info(self):
        """Obtener información del modelo"""
        self.client.get("/model-info", name="Model Info")
    
    @task(10)
    def predict(self):
        """Realizar una predicción (tarea principal)"""
        # Seleccionar paciente aleatorio
        patient = random.choice(self.patient_examples)
        
        # Hacer predicción
        self.client.post(
            "/predict",
            json=patient,
            name="Predict"
        )
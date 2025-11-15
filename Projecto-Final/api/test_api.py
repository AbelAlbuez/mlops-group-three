#!/usr/bin/env python3
"""
Script para probar la API de predicción
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"

def test_health():
    """Probar endpoint de health"""
    print("\n🔍 Probando /health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"✅ Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_model_info():
    """Probar endpoint de model info"""
    print("\n🔍 Probando /model-info...")
    try:
        response = requests.get(f"{API_URL}/model-info", timeout=5)
        print(f"✅ Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_prediction():
    """Probar endpoint de predicción"""
    print("\n🔍 Probando /predict...")
    
    # Paciente de ejemplo
    patient_data = {
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
    
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=patient_data,
            timeout=10
        )
        print(f"✅ Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))
        
        # Mostrar resultado de forma más amigable
        if response.status_code == 200:
            print(f"\n📊 RESULTADO:")
            print(f"   Predicción: {result['prediction']}")
            print(f"   Riesgo: {result['risk_level']}")
            print(f"   Probabilidad: {result['probability']:.2%}")
            print(f"   Modelo: {result['model_name']} v{result['model_version']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_metrics():
    """Probar endpoint de métricas"""
    print("\n🔍 Probando /metrics...")
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=5)
        print(f"✅ Status: {response.status_code}")
        # Solo mostrar las primeras líneas
        lines = response.text.split('\n')[:20]
        print('\n'.join(lines))
        print("...")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*60)
    print("🧪 PRUEBAS DE LA API DE PREDICCIÓN")
    print("="*60)
    
    results = []
    
    # Ejecutar pruebas
    results.append(("Health Check", test_health()))
    results.append(("Model Info", test_model_info()))
    results.append(("Prediction", test_prediction()))
    results.append(("Metrics", test_metrics()))
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron!")
        return 0
    else:
        print("\n⚠️  Algunas pruebas fallaron")
        print("\n💡 Asegúrate de:")
        print("   1. La API está corriendo (uvicorn main:app --reload)")
        print("   2. MLflow está accesible (http://localhost:5001)")
        print("   3. El DAG 3 se ejecutó y hay un modelo en Production")
        return 1

if __name__ == "__main__":
    sys.exit(main())

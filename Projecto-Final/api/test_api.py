#!/usr/bin/env python3
"""
Script para probar la API de predicción de precios de vivienda
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"


def test_health() -> bool:
    """Probar endpoint de health"""
    print("\nProbando /health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        return (
            response.status_code == 200
            and data.get("status") == "ok"
            and isinstance(data.get("model_loaded"), bool)
        )
    except Exception as e:
        print(f"Error en /health: {e}")
        return False


def test_model_info() -> bool:
    """Probar endpoint de información del modelo"""
    print("\nProbando /model-info...")
    try:
        response = requests.get(f"{API_URL}/model-info", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        required_keys = {"model_name", "model_version", "model_stage", "run_id", "metrics"}
        return response.status_code == 200 and required_keys.issubset(data.keys())
    except Exception as e:
        print(f"Error en /model-info: {e}")
        return False


def test_models_history() -> bool:
    """Probar endpoint de historial de modelos"""
    print("\nProbando /models/history...")
    try:
        response = requests.get(f"{API_URL}/models/history", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        # Lista con al menos un modelo registrado
        return response.status_code == 200 and isinstance(data, list) and len(data) >= 1
    except Exception as e:
        print(f"Error en /models/history: {e}")
        return False


def test_prediction() -> bool:
    """Probar endpoint de predicción"""
    print("\n🔍 Probando /predict...")

    house_data = {
        "bed": 3.0,
        "bath": 2.0,
        "acre_lot": 0.10,
        "house_size": 1500.0,
        "status": "for_sale",
        "city": "Baltimore",
        "state": "MD",
        "zip_code": "21201",
    }

    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=house_data,
            timeout=10,
        )
        print(f"✅ Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        if response.status_code != 200:
            return False

        required_keys = {"predicted_price", "model_name", "model_version", "model_stage", "run_id"}
        if not required_keys.issubset(data.keys()):
            print(" Faltan campos en la respuesta de /predict")
            return False

        print("\n RESULTADO:")
        print(f"   Precio estimado: {data['predicted_price']:.2f}")
        print(f"   Modelo: {data['model_name']} v{data['model_version']} ({data['model_stage']})")
        print(f"   Run ID: {data['run_id']}")

        return True

    except Exception as e:
        print(f" Error en /predict: {e}")
        return False


def main() -> int:
    print("=" * 60)
    print(" PRUEBAS DE LA API DE PREDICCIÓN - REAL ESTATE")
    print("=" * 60)

    results = []

    # Ejecutar pruebas
    results.append(("Health Check", test_health()))
    results.append(("Model Info", test_model_info()))
    results.append(("Model History", test_models_history()))
    results.append(("Prediction", test_prediction()))

    # Resumen
    print("\n" + "=" * 60)
    print(" RESUMEN DE PRUEBAS")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} pruebas exitosas")

    if passed == total:
        print("\n¡Todas las pruebas pasaron!")
        return 0
    else:
        print("\nAlgunas pruebas fallaron")
        print("\nAsegúrate de:")
        print("   1. La API está corriendo (contenedor final-api / puerto 8000)")
        print("   2. MLflow está accesible y hay un modelo en Production")
        print("   3. Se ejecutó el DAG de entrenamiento al menos una vez")
        return 1


if __name__ == "__main__":
    sys.exit(main())

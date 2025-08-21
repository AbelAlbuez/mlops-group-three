# API de Predicción de Pingüinos - Taller 2

Una aplicación FastAPI para predecir especies de pingüinos usando modelos de machine learning.

## Características

- **Carga dinámica de modelos**: Carga automáticamente todos los archivos `.pkl` de la carpeta `/models`
- **Múltiples endpoints**: Salud, listado de modelos y predicción
- **Predicciones flexibles**: Predice con todos los modelos o uno específico

## Endpoints

### GET /health
Estado de la API y modelos cargados.

### GET /models  
Lista de todos los modelos disponibles.

### POST /predict
Predicción usando **todos los modelos disponibles**.

**Datos de entrada:**
```json
{
  "bill_length_mm": 44.5,
  "bill_depth_mm": 17.1,
  "flipper_length_mm": 200,
  "body_mass_g": 4200,
  "island": "Biscoe",
  "sex": "male",
  "year": 2008
}
```

**Respuesta:**
```json
{
  "predictions": [
    {
      "model": "knn",
      "prediction": "Adelie",
      "probabilities": {
        "Adelie": 0.8,
        "Chinstrap": 0.1,
        "Gentoo": 0.1
      }
    },
    {
      "model": "svm",
      "prediction": "Adelie"
    }
  ]
}
```

### POST /predict/{model_name}
Predicción usando un modelo específico.

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Agregar modelos (archivos `.pkl`) a la carpeta `models/`

3. Ejecutar la aplicación:
```bash
python api.py
```

4. Documentación automática en: `http://localhost:8000/docs`

## Formato de datos

- `bill_length_mm` (requerido): Longitud del pico en mm
- `bill_depth_mm` (requerido): Profundidad del pico en mm  
- `flipper_length_mm` (requerido): Longitud de la aleta en mm
- `body_mass_g` (requerido): Masa corporal en gramos
- `island` (opcional): Isla (Biscoe, Dream, Torgersen)
- `sex` (opcional): Sexo (male, female)
- `year` (opcional): Año de observación

## Ejemplo de uso

```python
import requests

# Verificar estado
response = requests.get("http://localhost:8000/health")

# Obtener modelos disponibles
response = requests.get("http://localhost:8000/models")

# Hacer predicción con todos los modelos
data = {
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200
}

response = requests.post("http://localhost:8000/predict", json=data)
print(response.json())

# Predicción con modelo específico
response = requests.post("http://localhost:8000/predict/rf", json=data)
```
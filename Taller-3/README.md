# API de Predicción de Pingüinos - Taller 2

Una aplicación FastAPI que entrena y expone modelos de machine learning para predecir especies de pingüinos.

## 🚀 Flujo del Taller

1. **Entrenamiento**: El script `train_models.py` entrena modelos (KNN y RandomForest) usando datos de pingüinos o Iris como fallback, y guarda los archivos `.pkl` en la carpeta `models/` junto con un `model_metadata.json` con métricas y metadatos.
2. **API**: `api.py` carga automáticamente los modelos `.pkl` y expone endpoints REST para predicciones.
3. **Contenedores**: `docker-compose.yml` levanta dos servicios:

   * `trainer`: ejecuta `train_models.py` y guarda modelos en `/models`.
   * `api`: levanta la API FastAPI consumiendo los modelos desde la misma carpeta compartida por volumen.

## ⚙️ Características

* **Carga dinámica de modelos**: detecta automáticamente todos los `.pkl` en `/models`.
* **Múltiples endpoints**: salud, listado de modelos y predicción.
* **Predicciones flexibles**: se puede predecir con todos los modelos o con uno específico.

## 📡 Endpoints

### GET /health

Estado de la API y modelos cargados.

### GET /models

Lista de todos los modelos disponibles.

### POST /predict

Predicción usando **todos los modelos disponibles**.

**Ejemplo de entrada:**

```json
{
  "bill_length_mm": 44.5,
  "bill_depth_mm": 17.1,
  "flipper_length_mm": 200,
  "body_mass_g": 4200
}
```

### POST /predict/{model\_name}

Predicción usando un modelo específico (ej. `/predict/rf` o `/predict/knn`).

## 🛠️ Instalación local

1. Crear entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Entrenar modelos:

```bash
python train_models.py --out ./models
```

4. Ejecutar la API:

```bash
uvicorn api:app --reload --port 8000
```

5. Ver documentación en: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🐳 Uso con Docker Compose

1. Construir e iniciar servicios:

```bash
docker compose up --build
```

2. Entrenar modelos desde el contenedor `trainer`:

```bash
docker compose exec trainer python train_models.py --out /app/models
```

3. Probar API en: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📊 Ejemplo de uso con cURL

```bash
curl -X POST "http://localhost:8000/predict/knn" \
  -H "Content-Type: application/json" \
  -d '{"bill_length_mm":44.5, "bill_depth_mm":17.1, "flipper_length_mm":200, "body_mass_g":4200}'
```

## 📋 Formato de datos

* `bill_length_mm` (float, requerido)
* `bill_depth_mm` (float, requerido)
* `flipper_length_mm` (float, requerido)
* `body_mass_g` (float, requerido)
* `island` (opcional)
* `sex` (opcional)
* `year` (opcional)

---
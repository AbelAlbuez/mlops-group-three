# Taller 2 - Desarrollo en Contenedores

## Descripcion
Aplicación contenedorizada que entrena y sirve modelos de clasificación de pingüinos. Se despliega con Docker Compose en dos servicios: una API en FastAPI y un entorno JupyterLab. Cumple con el enunciado "Desarrollo en contenedores" del curso (ver [instrucciones](https://github.com/CristianDiazAlvarez/MLOPS_PUJ/blob/main/Niveles/1/Desarollo_en_contenedores/README.md)).

## Corriendo el proyecto
- Requisitos: Docker y Docker Compose.
- Construir e iniciar:
```bash
docker compose up --build
```
- URLs:
  - API: http://localhost:8000/docs
  - JupyterLab: http://localhost:8888

## Instruccion de uso 
- Para crear los modelos hay que correr el archivo `train_from_jupyter.ipynb` en JupyterLab. Ahora cada modelo (KNN, Random Forest, SVM) se guarda inmediatamente después de entrenarse, por lo que puedes reentrenar y sobrescribir solo el modelo que necesites. Los artefactos se guardan en `models/` y la API los carga automáticamente.
- Para predecir, usar la documentación interactiva de la API en `/docs` con los endpoints `/predict` o `/predict/{model}`.

## Servicios
- API: Servicio FastAPI que carga modelos desde `models/` y expone endpoints en el puerto 8000.
  - GET `/health`: estado de la API y número de modelos cargados.
  - GET `/models`: lista de modelos disponibles (según archivos `.pkl` en `models/`).
  - POST `/predict`: predice con todos los modelos disponibles.
  - POST `/predict/{model_name}`: predice con un modelo específico (por ejemplo, `knn`, `rf`, `svm`).
- JupyterLab: Entorno interactivo en el puerto 8888.
  - Ejecuta `train_from_jupyter.ipynb` para entrenar y guardar modelos individualmente.
  - La carpeta `models/` está montada como volumen compartido con la API.
  - Consejos: puedes duplicar celdas para experimentar con hiperparámetros y volver a guardar el modelo objetivo sin afectar a los demás.

 

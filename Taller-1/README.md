# Palmer Penguins Classifier API

API REST para clasificación de especies de pingüinos usando múltiples modelos de Machine Learning (Random Forest, KNN, SVM).

## 📋 Descripción

Esta API permite predecir la especie de pingüino (Adelie, Chinstrap o Gentoo) basándose en características físicas como el tamaño del pico, aletas y masa corporal. Incluye la funcionalidad de seleccionar entre diferentes modelos entrenados.

## 🚀 Inicio Rápido

### Prerequisitos
- Python 3.8+
- Docker (opcional)

### Instalación Local

1. **Clonar el repositorio**
```bash
git clone https://github.com/AbelAlbuez/mlops-group-three.git
cd mlops-group-three/Taller-1
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Ejecutar la API**
```bash
python api.py
```

La API estará disponible en `http://localhost:5000`

## 🐳 Instalación con Docker

1. **Construir la imagen**
```bash
docker build -t palmer-penguins-api .
```

2. **Ejecutar el contenedor**
```bash
docker run -p 5000:5000 palmer-penguins-api
```

## 📚 Estructura del Proyecto

```
Taller-1/
├── api.py                  # API Flask principal
├── Modelos/               # Directorio con modelos entrenados
│   ├── knn_model.pkl
│   ├── random_forest_model.pkl
│   └── svm_model.pkl
├── migrate_models.py      # Script para migración de modelos
├── requirements.txt       # Dependencias del proyecto
├── smoke_test.py         # Tests básicos de la API
├── Dockerfile            # Configuración Docker
├── .gitignore           # Archivos ignorados por Git
└── README.md            # Este archivo
```

## 🔧 Uso de la API

### Endpoints Disponibles

#### 1. Health Check
```bash
GET /health
```

Respuesta:
```json
{
  "status": "ok"
}
```

#### 2. Predicción de Especie
```bash
POST /predict
```

**Parámetros del body (JSON):**
```json
{
  "culmen_length_mm": 39.1,
  "culmen_depth_mm": 18.7,
  "flipper_length_mm": 181,
  "body_mass_g": 3750,
  "model_type": "random_forest"  // Opciones: "random_forest", "knn", "svm"
}
```

**Respuesta exitosa:**
```json
{
  "species": "Adelie",
  "model_used": "random_forest",
  "confidence": 0.95
}
```

### Ejemplos de Uso

#### Con cURL:
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "culmen_length_mm": 39.1,
    "culmen_depth_mm": 18.7,
    "flipper_length_mm": 181,
    "body_mass_g": 3750,
    "model_type": "random_forest"
  }'
```

#### Con Python:
```python
import requests

url = "http://localhost:5000/predict"
data = {
    "culmen_length_mm": 39.1,
    "culmen_depth_mm": 18.7,
    "flipper_length_mm": 181,
    "body_mass_g": 3750,
    "model_type": "knn"
}

response = requests.post(url, json=data)
print(response.json())
```

## 📊 Modelos Disponibles

1. **Random Forest** (por defecto)
   - Alta precisión
   - Robusto ante outliers
   - Mejor rendimiento general

2. **K-Nearest Neighbors (KNN)**
   - Simple y efectivo
   - Bueno para patrones locales
   - Sensible a la escala de datos

3. **Support Vector Machine (SVM)**
   - Excelente para separación no lineal
   - Eficiente en espacios de alta dimensión
   - Robusto ante overfitting

## 🧪 Testing

Ejecutar el test de smoke:
```bash
python smoke_test.py
```

Este script verifica:
- Conexión a la API
- Endpoint de health check
- Predicciones con cada modelo
- Manejo de errores

## 📈 Características de los Datos

Las características utilizadas para la predicción son:
- **culmen_length_mm**: Longitud del pico (mm)
- **culmen_depth_mm**: Profundidad del pico (mm)
- **flipper_length_mm**: Longitud de la aleta (mm)
- **body_mass_g**: Masa corporal (g)

Especies predichas:
- Adelie
- Chinstrap
- Gentoo

## 🔄 Migración de Modelos

Para actualizar o migrar modelos existentes:
```bash
python migrate_models.py
```

Este script permite:
- Cargar modelos antiguos
- Validar su funcionamiento
- Guardar en el nuevo formato
- Verificar compatibilidad

## 🛠️ Desarrollo

### Dependencias Principales
- Flask: Framework web
- scikit-learn: Modelos de ML
- pandas: Manipulación de datos
- numpy: Operaciones numéricas
- pickle: Serialización de modelos

### Agregar un Nuevo Modelo

1. Entrenar el modelo usando el dataset Palmer Penguins
2. Guardar el modelo en formato pickle en `Modelos/`
3. Actualizar `api.py` para incluir el nuevo modelo
4. Actualizar la documentación

## 📝 Notas Importantes

- Los modelos están pre-entrenados con el dataset Palmer Penguins
- Asegúrate de que todos los valores de entrada sean numéricos
- Los valores faltantes deben ser manejados antes de la predicción
- La API valida automáticamente los rangos de valores esperados

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## 👥 Autores

- **Abel Albuez** - [GitHub](https://github.com/AbelAlbuez)
- **Omar Gastón**
- **Mauricio Morales**

Grupo 3 - MLOps

## 🙏 Agradecimientos

- Dataset Palmer Penguins por Allison Horst
- Comunidad de scikit-learn
- Flask por su excelente framework
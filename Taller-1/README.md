# Palmer Penguins Classifier API

API REST con FastAPI para clasificación de especies de pingüinos usando múltiples modelos de Machine Learning (Random Forest, KNN, SVM). Incluye una interfaz web moderna y capacidades de contenedorización con Docker.

## 📋 Descripción

Esta API permite predecir la especie de pingüino (Adelie, Chinstrap o Gentoo) basándose en características físicas como el tamaño del pico, aletas y masa corporal. Incluye:

- 🤖 **Múltiples modelos ML**: Random Forest, KNN, SVM
- 🌐 **Interfaz web moderna**: UI responsiva con glassmorphism design
- 🐳 **Dockerizada**: Fácil despliegue con contenedores
- 🔄 **Selección dinámica de modelos**: Cambio de modelo en tiempo real
- 📊 **Probabilidades visuales**: Barras de confianza para cada especie

## 🚀 Inicio Rápido

### 🐳 Método Recomendado: Docker

1. **Construir la imagen**
```bash
git clone https://github.com/AbelAlbuez/mlops-group-three.git
cd mlops-group-three/Taller-1
docker build -t taller1 .
```

2. **Ejecutar el contenedor**
```bash
docker run -p 8989:8989 taller1
```

3. **Acceder a la aplicación**
- **Interfaz Web**: `http://localhost:8989`
- **API Docs**: `http://localhost:8989/docs`
- **Health Check**: `http://localhost:8989/health`

### 💻 Instalación Local

### Prerequisitos
- Python 3.11+
- Modelos pre-entrenados en `Modelos/migrated/`

### Pasos

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
uvicorn api:app --host 0.0.0.0 --port 8989
```

La aplicación estará disponible en `http://localhost:8989`

## 📚 Estructura del Proyecto

```
Taller-1/
├── api.py                  # API FastAPI principal
├── Dockerfile             # Configuración Docker
├── requirements.txt       # Dependencias del proyecto
├── Static/
│   └── index.html         # Interfaz web moderna
├── Modelos/
│   ├── migrated/          # Modelos migrados (pipelines completos)
│   │   ├── knn.pkl
│   │   ├── rf.pkl
│   │   └── svm.pkl
│   ├── KNN/              # Modelos KNN originales
│   ├── Random Forest/    # Modelos Random Forest originales
│   └── SVM/              # Modelos SVM originales
├── migrate_models.py      # Script para migración de modelos
├── smoke_test.py         # Tests básicos de la API
└── README.md             # Este archivo
```

## 🌐 Interfaz Web

### Características de la UI

- **🎨 Diseño Moderno**: Glassmorphism con gradientes y efectos de desenfoque
- **📱 Responsive**: Funciona perfectamente en desktop, tablet y móvil
- **🔄 Tiempo Real**: Cambio de modelos sin recargar la página
- **� Visualización**: Barras de probabilidad para cada especie
- **✨ Animaciones**: Transiciones suaves y efectos hover
- **📝 Validación**: Formularios con validación en tiempo real

### Campos de Entrada

- **Bill Length (mm)**: Longitud del pico
- **Bill Depth (mm)**: Profundidad del pico  
- **Flipper Length (mm)**: Longitud de la aleta
- **Body Mass (g)**: Masa corporal
- **Sex**: Masculino/Femenino
- **Island**: Biscoe/Dream/Torgersen

### Funcionalidades

1. **Selección de Modelo**: Dropdown para elegir entre RF, KNN, SVM
2. **Predicción Instantánea**: Resultados con probabilidades visuales
3. **Datos de Ejemplo**: Botón para llenar con datos de prueba
4. **Historial**: Muestra parámetros usados en cada predicción

## �🔧 Uso de la API

### Endpoints Disponibles

#### 1. Interfaz Web
```bash
GET /
```
Sirve la interfaz web principal

#### 2. Health Check
```bash
GET /health
```

Respuesta:
```json
{
  "status": "ok",
  "active_model": "rf",
  "available": ["rf", "knn", "svm"]
}
```

#### 3. Listar Modelos
```bash
GET /models
```

Respuesta:
```json
{
  "active": "rf",
  "available": ["rf", "knn", "svm"]
}
```

#### 4. Seleccionar Modelo
```bash
POST /models/select/{model_name}
```

Parámetros: `model_name` puede ser "rf", "knn", o "svm"

#### 5. Predicción Individual
```bash
POST /predict
```

**Parámetros del body (JSON):**
```json
{
  "bill_length_mm": 44.5,
  "bill_depth_mm": 17.1,
  "flipper_length_mm": 200,
  "body_mass_g": 4200,
  "sex": "male",
  "island": "Biscoe",
  "year": 2008
}
```

**Respuesta exitosa:**
```json
{
  "model": "rf",
  "prediction": "Adelie",
  "probs": {
    "Adelie": 0.85,
    "Chinstrap": 0.10,
    "Gentoo": 0.05
  }
}
```

#### 6. Predicción por Lotes
```bash
POST /predict/batch
```

**Parámetros del body (JSON):**
```json
{
  "items": [
    {
      "bill_length_mm": 44.5,
      "bill_depth_mm": 17.1,
      "flipper_length_mm": 200,
      "body_mass_g": 4200,
      "sex": "male",
      "island": "Biscoe"
    },
    {
      "bill_length_mm": 50.4,
      "bill_depth_mm": 15.2,
      "flipper_length_mm": 224,
      "body_mass_g": 5350,
      "sex": "female",
      "island": "Dream"
    }
  ]
}
```

### Ejemplos de Uso

#### Con cURL:
```bash
# Predicción individual
curl -X POST http://localhost:8989/predict \
  -H "Content-Type: application/json" \
  -d '{
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200,
    "sex": "male",
    "island": "Biscoe"
  }'

# Cambiar modelo
curl -X POST http://localhost:8989/models/select/knn
```

#### Con Python:
```python
import requests

# Cambiar a modelo KNN
requests.post("http://localhost:8989/models/select/knn")

# Hacer predicción
url = "http://localhost:8989/predict"
data = {
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200,
    "sex": "male",
    "island": "Biscoe",
    "year": 2008
}

response = requests.post(url, json=data)
result = response.json()
print(f"Predicción: {result['prediction']}")
print(f"Probabilidades: {result['probs']}")
```

#### Con JavaScript (Frontend):
```javascript
// La interfaz web ya incluye toda esta funcionalidad
// Visita http://localhost:8989 para usar la UI
```

## � Docker

### Configuración

El Dockerfile incluye:
- **Base**: Python 3.11-slim para un contenedor ligero
- **Puerto**: 8989 expuesto para la aplicación
- **Dependencias**: Instalación optimizada con cache de capas
- **Servidor**: Uvicorn con configuración de producción

### Comandos Docker

```bash
# Construir imagen
docker build -t taller1 .

# Ejecutar contenedor
docker run -p 8989:8989 taller1

# Ejecutar en background
docker run -d -p 8989:8989 --name penguin-classifier taller1

# Ver logs
docker logs penguin-classifier

# Parar contenedor
docker stop penguin-classifier

# Remover contenedor
docker rm penguin-classifier
```

### Docker Compose (Opcional)

Crear `docker-compose.yml`:
```yaml
version: '3.8'
services:
  palmer-penguins:
    build: .
    ports:
      - "8989:8989"
    restart: unless-stopped
    environment:
      - ENV=production
```

Ejecutar con:
```bash
docker-compose up -d
```

## 📊 Modelos Disponibles
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

### Test de Smoke
```bash
python smoke_test.py
```

Este script verifica:
- ✅ Carga correcta de modelos migrados
- ✅ Preprocesamiento de características
- ✅ Predicciones con cada modelo (RF, KNN, SVM)
- ✅ Probabilidades de clasificación
- ✅ Manejo de diferentes tipos de entrada

### Test Manual con la UI
1. Abrir `http://localhost:8989`
2. Hacer clic en "📝 Fill with example data"
3. Seleccionar diferentes modelos
4. Verificar predicciones y probabilidades

### Test de Endpoints
```bash
# Health check
curl http://localhost:8989/health

# Listar modelos
curl http://localhost:8989/models

# Predicción de prueba
curl -X POST http://localhost:8989/predict \
  -H "Content-Type: application/json" \
  -d '{
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200,
    "sex": "male",
    "island": "Biscoe"
  }'
```

## 📈 Características de los Datos

### Parámetros de Entrada
- **bill_length_mm**: Longitud del pico en milímetros (float)
- **bill_depth_mm**: Profundidad del pico en milímetros (float)
- **flipper_length_mm**: Longitud de la aleta en milímetros (int)
- **body_mass_g**: Masa corporal en gramos (int)
- **sex**: Sexo del pingüino ("male" o "female")
- **island**: Isla de origen ("Biscoe", "Dream", "Torgersen")
- **year**: Año (opcional, por defecto 2008)

### Especies Predichas
- **Adelie**: Especie más común, pico más corto y ancho
- **Chinstrap**: Marca negra distintiva bajo la cabeza
- **Gentoo**: La más grande de las tres especies

### Rangos Típicos
- Bill Length: 32-60 mm
- Bill Depth: 13-22 mm  
- Flipper Length: 170-230 mm
- Body Mass: 2700-6300 g

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

### Stack Tecnológico
- **Backend**: FastAPI 
- **Frontend**: HTML5, CSS3 (Tailwind), Vanilla JavaScript
- **ML**: scikit-learn, pandas, numpy
- **Contenedorización**: Docker
- **Servidor**: Uvicorn (ASGI)

### Dependencias Principales
```txt
fastapi
uvicorn[standard]
pandas
numpy
scikit-learn
joblib
```

### Estructura de Código
- **api.py**: Aplicación FastAPI principal con endpoints
- **Static/index.html**: SPA con interfaz moderna
- **Modelos/migrated/**: Pipelines ML completos (preprocesamiento + modelo)
- **migrate_models.py**: Utilidad para migrar modelos legacy

### Agregar un Nuevo Modelo

1. **Entrenar el modelo** usando el dataset Palmer Penguins
2. **Crear pipeline completo** con preprocesamiento incluido
3. **Guardar en formato pickle** en `Modelos/migrated/`
4. **Actualizar MODELS dict** en `api.py`
5. **Agregar al dropdown** en `Static/index.html`
6. **Actualizar documentación**

Ejemplo:
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier

# Crear pipeline
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', GradientBoostingClassifier())
])

# Entrenar
pipeline.fit(X_train, y_train)

# Guardar
joblib.dump(pipeline, 'Modelos/migrated/gb.pkl')
```

## 📝 Notas Importantes

### Modelos y Datos
- Los modelos están pre-entrenados con el dataset Palmer Penguins
- Todos los pipelines incluyen preprocesamiento automático (escalado, one-hot encoding)
- Los valores faltantes se manejan automáticamente con valores por defecto
- La API valida automáticamente tipos y rangos de entrada

### Arquitectura
- **FastAPI**: Framework ASGI para alta performance
- **Uvicorn**: Servidor ASGI con soporte para async/await
- **Pipelines sklearn**: Preprocesamiento + modelo en un solo objeto
- **Contenedorización**: Imagen Docker optimizada para producción

### Seguridad y Performance
- Validación automática de entrada con Pydantic
- Manejo robusto de errores con códigos HTTP apropiados
- Carga de modelos en memoria al startup para respuesta rápida
- Logs estructurados para debugging y monitoring

### Limitaciones
- Los modelos asumen distribución similar al dataset de entrenamiento
- Performance óptimo con valores dentro de rangos típicos
- Cambio de modelo afecta todas las solicitudes (no por sesión)

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
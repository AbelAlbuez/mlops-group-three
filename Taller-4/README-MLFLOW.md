# 🚀 Taller MLflow - Palmer Penguins

## 📌 Descripción
Este taller implementa un **pipeline completo de MLOps** usando MLflow para tracking de experimentos, registro de modelos y servicio de inferencia.

### Componentes principales:
- **MinIO**: Almacenamiento S3-compatible para artefactos
- **MySQL**: Base de datos para metadatos de MLflow y datos de pingüinos
- **MLflow**: Tracking de experimentos y Model Registry
- **JupyterLab**: Ambiente de desarrollo para experimentos
- **API FastAPI**: Servicio de inferencia que consume modelos desde MLflow

---

## 📋 Pre-requisitos
- Docker y Docker Compose
- 8GB RAM mínimo
- Puertos disponibles: 3306, 5000, 8000, 8888, 9000, 9001

---

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <tu-repositorio>
cd taller-mlflow
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

### 3. Crear estructura de directorios
```bash
mkdir -p jupyter notebooks mlflow mysql/init-mlflow.sql api data/{raw,processed}
```

### 4. Levantar servicios con Docker Compose
```bash
# Opción 1: Todo en un comando
docker-compose -f docker-compose.mlflow.yml up -d

# Opción 2: Por etapas
docker-compose -f docker-compose.mlflow.yml up -d mysql minio
# Esperar 30 segundos
docker-compose -f docker-compose.mlflow.yml up -d mlflow
docker-compose -f docker-compose.mlflow.yml up -d jupyterlab api-mlflow
```

---

## 🔍 Verificación de Servicios

### MinIO (S3)
- Consola: http://localhost:9001
- Usuario: `admin`
- Password: `supersecret`
- Verificar que existe el bucket `mlflows3`

### MLflow
- UI: http://localhost:5000
- Debe mostrar el experimento `penguins-classification` después de ejecutar el notebook

### JupyterLab
- URL: http://localhost:8888
- Token: `mlflow2024`
- El notebook `experiments.ipynb` debe estar en `/work`

### API
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### MySQL
```bash
# Verificar bases de datos
docker exec -it mlflow-mysql mysql -u penguins -ppenguins123 -e "SHOW DATABASES;"

# Debe mostrar:
# - penguins_db
# - mlflow_meta
```

---

## 📊 Flujo de Trabajo

### 1. Ejecutar experimentos en JupyterLab
1. Abrir http://localhost:8888 (token: mlflow2024)
2. Abrir `notebooks/experiments.ipynb`
3. Ejecutar todas las celdas (≥20 experimentos)
4. Verificar en MLflow UI que aparecen los runs

### 2. Verificar modelo en Production
```bash
# En MLflow UI (http://localhost:5000):
# - Click en "Models" → "penguins-classifier"
# - Debe haber una versión en stage "Production"
```

### 3. Probar API de inferencia
```bash
# Health check
curl http://localhost:8000/health

# Listar modelos disponibles
curl http://localhost:8000/models

# Hacer predicción
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "bill_length_mm": 44.5,
    "bill_depth_mm": 17.1,
    "flipper_length_mm": 200,
    "body_mass_g": 4200
  }'
```

---

## 🏗️ Estructura del Proyecto

```
taller-mlflow/
├── docker-compose.mlflow.yml    # Orquestación de servicios
├── .env                         # Variables de entorno
├── .env.example                 # Ejemplo de configuración
├── mysql/
│   ├── init.sql                # Schema de penguins_db
│   └── init-mlflow.sql         # Schema de mlflow_meta
├── jupyter/
│   ├── Dockerfile              # Imagen de JupyterLab
│   └── requirements.txt        # Dependencias Python
├── mlflow/
│   └── Dockerfile              # Imagen de MLflow server
├── api/
│   ├── api_mlflow.py           # API que consume desde MLflow
│   ├── Dockerfile.mlflow       # Imagen de la API
│   └── requirements_mlflow.txt # Dependencias de la API
├── notebooks/
│   └── experiments.ipynb       # Notebook con experimentos
└── data/
    ├── raw/                    # Datos crudos
    └── processed/              # Datos procesados
```

---

## 🐛 Troubleshooting

### MinIO no inicia
```bash
# Verificar logs
docker logs mlflow-minio

# Recrear contenedor
docker-compose -f docker-compose.mlflow.yml up -d --force-recreate minio
```

### MLflow no se conecta a MinIO
```bash
# Verificar variables de entorno
docker exec mlflow-server env | grep -E "AWS_|MLFLOW_S3"

# Verificar conectividad
docker exec mlflow-server curl -I http://minio:9000
```

### API no encuentra modelos
```bash
# Verificar que MLflow tiene modelos registrados
curl http://localhost:5000/api/2.0/mlflow/registered-models/list

# Verificar logs de la API
docker logs mlflow-api
```

### JupyterLab no puede conectar a MLflow
```bash
# Verificar desde dentro del contenedor
docker exec -it mlflow-jupyter python -c "import mlflow; print(mlflow.get_tracking_uri())"
```

---

## 🔄 Comandos Útiles

### Ver logs
```bash
# Todos los servicios
docker-compose -f docker-compose.mlflow.yml logs -f

# Servicio específico
docker logs -f mlflow-server
```

### Reiniciar servicios
```bash
# Reiniciar todo
docker-compose -f docker-compose.mlflow.yml restart

# Reiniciar servicio específico
docker-compose -f docker-compose.mlflow.yml restart mlflow
```

### Limpiar todo
```bash
# Detener y eliminar contenedores
docker-compose -f docker-compose.mlflow.yml down

# Eliminar volúmenes (⚠️ BORRA TODOS LOS DATOS)
docker-compose -f docker-compose.mlflow.yml down -v
```

---

## 🎯 Checklist de Validación

- [ ] MinIO corriendo en :9001 con bucket `mlflows3` creado
- [ ] MySQL con bases `penguins_db` y `mlflow_meta`
- [ ] MLflow UI accesible en :5000
- [ ] JupyterLab en :8888 con notebook ejecutado
- [ ] ≥20 experimentos visibles en MLflow
- [ ] Modelo `penguins-classifier` en Model Registry
- [ ] Versión del modelo en stage "Production"
- [ ] API en :8000 respondiendo predicciones
- [ ] Datos en tablas `penguins_raw` y `penguins_clean`

---

## 📝 Notas Adicionales

### Instalación sin Docker (Systemd)
Si prefieres usar systemd en lugar de Docker:

1. Instalar MLflow localmente:
```bash
python3 -m venv /opt/mlflow/venv
/opt/mlflow/venv/bin/pip install mlflow pymysql boto3
```

2. Copiar `mlflow_serv.service` a `/etc/systemd/system/`

3. Habilitar y arrancar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mlflow_serv
sudo systemctl start mlflow_serv
```

### Configuración de producción
Para ambientes de producción considera:
- Usar bases de datos externas (RDS, Cloud SQL)
- MinIO en cluster o usar S3 real
- MLflow detrás de un proxy reverso con SSL
- Autenticación en todos los servicios
- Monitoreo con Prometheus/Grafana

---

💡 **Tip**: Si algo no funciona, revisar primero los logs de Docker y las variables de entorno en `.env`
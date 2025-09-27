# Proyecto 2 - Airflow ML Pipeline

Este proyecto implementa un pipeline de Machine Learning usando Apache Airflow que obtiene datos de una API externa, los procesa y entrena un modelo de clasificación.

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker y Docker Compose instalados
- Puerto 8080 disponible

### Configuración

1. **Copia el archivo `.env.example` a `.env`** en el directorio raíz

2. **Ejecutar el pipeline**:
```bash
cd Projecto-2
docker-compose up --build
```

3. **Acceder a Airflow**:
- URL: http://localhost:8080
- Usuario: `admin`
- Contraseña: `admin123`

## 📊 Pipeline de ML

### DAG: `p2_covertype_single_request`

**Programación**: Cada 5 minutos
**Descripción**: Pipeline que procesa datos de cobertura forestal

#### Tareas:
1. **fetch_once**: Obtiene datos de la API externa
2. **validate_and_preprocess**: Valida y preprocesa los datos
3. **train_eval**: Entrena modelo RandomForest y calcula métricas

### Configuración del Pipeline

Las variables del pipeline se configuran automáticamente:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `P2_API_BASE` | `http://10.43.100.103:80` | URL base de la API |
| `P2_GROUP_ID` | `3` | ID del grupo |
| `P2_API_PATH` | `/data` | Endpoint de datos |
| `P2_TARGET_COL` | `Cover_Type` | Columna objetivo |
| `P2_SCHEDULE_CRON` | `*/5 * * * *` | Ejecutar cada 5 minutos |

## 🛠️ Estructura del Proyecto

```
Projecto-2/
├── airflow/
│   ├── dags/
│   │   └── p2_covertype_single_request.py  # DAG principal
│   ├── Dockerfile                          # Imagen custom de Airflow
│   └── requirements.txt                    # Dependencias Python
├── docker-compose.yml                      # Configuración de servicios
├── .env                                    # Variables de entorno
└── README.md                               # Este archivo
```

## 📈 Resultados

Los resultados del pipeline se guardan en `/opt/airflow/data/p2/` dentro del contenedor:

- **Datos raw**: `raw_{timestamp}.json`
- **Datos procesados**: `X_{timestamp}.parquet`, `y_{timestamp}.parquet`
- **Métricas**: `metrics_{timestamp}.json`
- **Modelo**: `model_{timestamp}.joblib`

## 🔧 Comandos Útiles

### Detener servicios
```bash
docker-compose down
```

### Ver logs
```bash
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler
```

### Reconstruir imágenes
```bash
docker-compose up --build --force-recreate
```

## 📝 Notas

- El DAG se activa automáticamente al iniciar
- Los datos se procesan y persisten localmente en el contenedor
- Las métricas del modelo se imprimen en los logs de Airflow
- El pipeline maneja errores básicos de validación de datos
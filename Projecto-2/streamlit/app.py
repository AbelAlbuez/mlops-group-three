import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import pymysql
import os
from datetime import datetime, timedelta
import json

# Configuración de la página
st.set_page_config(
    page_title="🌲 MLOps Proyecto 2 - Covertype Classification",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de servicios
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://inference:8000")
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql-db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "covertype_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "covertype_pass123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "covertype_db")

# ==========================================
# Funciones de utilidad
# ==========================================

def get_mysql_connection():
    """Crear conexión a MySQL"""
    try:
        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None

def check_service_health(service_name, url):
    """Verificar salud de un servicio"""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_model_info():
    """Obtener información del modelo desde la API de inferencia"""
    try:
        response = requests.get(f"{INFERENCE_API_URL}/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            if models:
                return models[0]  # Retornar el modelo más reciente
        return None
    except:
        return None

def make_prediction(features):
    """Realizar predicción usando la API de inferencia"""
    try:
        response = requests.post(
            f"{INFERENCE_API_URL}/predict",
            json=features,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error en predicción: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error conectando con API de inferencia: {e}")
        return None

def get_training_history():
    """Obtener historial de entrenamiento desde MySQL"""
    connection = get_mysql_connection()
    if not connection:
        return pd.DataFrame()
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    batch_id,
                    accuracy,
                    f1_macro,
                    n_samples_train,
                    n_samples_test,
                    training_time_seconds,
                    created_at
                FROM model_metrics
                ORDER BY created_at DESC
                LIMIT 20
            """)
            results = cursor.fetchall()
            return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Error obteniendo historial: {e}")
        return pd.DataFrame()
    finally:
        connection.close()

def get_data_stats():
    """Obtener estadísticas de datos desde MySQL"""
    connection = get_mysql_connection()
    if not connection:
        return {}
    
    try:
        with connection.cursor() as cursor:
            # Total de muestras
            cursor.execute("SELECT COUNT(*) as total FROM covertype_data")
            total_samples = cursor.fetchone()['total']
            
            # Batches procesados
            cursor.execute("SELECT COUNT(DISTINCT batch_id) as batches FROM covertype_data")
            batches = cursor.fetchone()['batches']
            
            # Última actualización
            cursor.execute("SELECT MAX(created_at) as last_update FROM model_metrics")
            last_update = cursor.fetchone()['last_update']
            
            return {
                'total_samples': total_samples,
                'batches': batches,
                'last_update': last_update
            }
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {e}")
        return {}
    finally:
        connection.close()

# ==========================================
# Interfaz principal
# ==========================================

# Título principal
st.title("🌲 MLOps Proyecto 2 - Covertype Classification")
st.markdown("**Sistema de clasificación de tipos de cobertura forestal con MLflow y Airflow**")

# Tabs principales
tab1, tab2, tab3 = st.tabs(["🔮 Predicción", "📊 Monitoreo", "⚙️ Control"])

# ==========================================
# Tab 1: Predicción
# ==========================================
with tab1:
    st.header("🔮 Predicción de Tipo de Cobertura")
    st.markdown("Ingresa las características del terreno para predecir el tipo de cobertura forestal.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Características del Terreno")
        
        # Formulario de entrada
        elevation = st.number_input("Elevación (metros)", min_value=0, max_value=5000, value=2596)
        aspect = st.number_input("Aspecto (grados)", min_value=0, max_value=360, value=51)
        slope = st.number_input("Pendiente (grados)", min_value=0, max_value=90, value=3)
        horizontal_distance_to_hydrology = st.number_input("Distancia horizontal a hidrología", min_value=0, value=258)
        vertical_distance_to_hydrology = st.number_input("Distancia vertical a hidrología", value=0)
        horizontal_distance_to_roadways = st.number_input("Distancia horizontal a carreteras", min_value=0, value=510)
        
    with col2:
        st.subheader("Características Ambientales")
        
        hillshade_9am = st.number_input("Índice de sombra 9am", min_value=0, max_value=255, value=221)
        hillshade_noon = st.number_input("Índice de sombra mediodía", min_value=0, max_value=255, value=232)
        hillshade_3pm = st.number_input("Índice de sombra 3pm", min_value=0, max_value=255, value=148)
        horizontal_distance_to_fire_points = st.number_input("Distancia horizontal a puntos de fuego", min_value=0, value=6279)
        wilderness_area = st.number_input("Área silvestre", min_value=0, value=0)
        soil_type = st.number_input("Tipo de suelo", min_value=0, value=7744)
    
    # Botón de predicción
    if st.button("🔮 Predecir", type="primary"):
        # Preparar datos
        features = {
            "elevation": elevation,
            "aspect": aspect,
            "slope": slope,
            "horizontal_distance_to_hydrology": horizontal_distance_to_hydrology,
            "vertical_distance_to_hydrology": vertical_distance_to_hydrology,
            "horizontal_distance_to_roadways": horizontal_distance_to_roadways,
            "hillshade_9am": hillshade_9am,
            "hillshade_noon": hillshade_noon,
            "hillshade_3pm": hillshade_3pm,
            "horizontal_distance_to_fire_points": horizontal_distance_to_fire_points,
            "wilderness_area": wilderness_area,
            "soil_type": soil_type
        }
        
        # Realizar predicción
        with st.spinner("Realizando predicción..."):
            result = make_prediction(features)
        
        if result:
            st.success("✅ Predicción exitosa!")
            
            # Mostrar resultado
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.metric(
                    label="Tipo de Cobertura Predicho",
                    value=f"Clase {result['cover_type']}",
                    help="0: Spruce/Fir, 1: Lodgepole Pine, 2: Ponderosa Pine, 3: Cottonwood/Willow, 4: Aspen, 5: Douglas-fir, 6: Krummholz"
                )
                st.metric(
                    label="Versión del Modelo",
                    value=f"v{result['model_version']}"
                )
            
            with col2:
                # Gráfica de probabilidades
                prob_df = pd.DataFrame([
                    {"Clase": f"Clase {k}", "Probabilidad": v}
                    for k, v in result['probabilities'].items()
                ])
                
                fig = px.bar(
                    prob_df, 
                    x="Clase", 
                    y="Probabilidad",
                    title="Probabilidades por Clase",
                    color="Probabilidad",
                    color_continuous_scale="viridis"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# Tab 2: Monitoreo
# ==========================================
with tab2:
    st.header("📊 Monitoreo del Sistema")
    
    # Estadísticas de datos
    st.subheader("Estadísticas de Datos")
    stats = get_data_stats()
    
    if stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Muestras", f"{stats['total_samples']:,}")
        
        with col2:
            st.metric("Batches Procesados", f"{stats['batches']:,}")
        
        with col3:
            if stats['last_update']:
                st.metric("Última Actualización", stats['last_update'].strftime("%Y-%m-%d %H:%M"))
            else:
                st.metric("Última Actualización", "N/A")
    
    # Histórico de entrenamiento
    st.subheader("Histórico de Entrenamiento")
    
    if st.button("🔄 Actualizar Datos"):
        st.rerun()
    
    history_df = get_training_history()
    
    if not history_df.empty:
        # Gráficas de evolución
        col1, col2 = st.columns(2)
        
        with col1:
            fig_accuracy = px.line(
                history_df, 
                x="created_at", 
                y="accuracy",
                title="Evolución de Accuracy",
                labels={"accuracy": "Accuracy", "created_at": "Fecha"}
            )
            st.plotly_chart(fig_accuracy, use_container_width=True)
        
        with col2:
            fig_f1 = px.line(
                history_df, 
                x="created_at", 
                y="f1_macro",
                title="Evolución de F1-Macro",
                labels={"f1_macro": "F1-Macro", "created_at": "Fecha"}
            )
            st.plotly_chart(fig_f1, use_container_width=True)
        
        # Tabla de métricas
        st.subheader("Métricas Detalladas")
        display_df = history_df.copy()
        display_df['created_at'] = display_df['created_at'].dt.strftime('%Y-%m-%d %H:%M')
        display_df = display_df.round(4)
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No hay datos de entrenamiento disponibles. Ejecuta el DAG de Airflow para generar datos.")

# ==========================================
# Tab 3: Control
# ==========================================
with tab3:
    st.header("⚙️ Control del Sistema")
    
    # Estado de servicios
    st.subheader("Estado de Servicios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Inference API
        inference_health = check_service_health("Inference API", f"{INFERENCE_API_URL}/health")
        if inference_health:
            st.success("✅ Inference API: Online")
            
            # Información del modelo
            model_info = get_model_info()
            if model_info:
                st.info(f"Modelo: {model_info['name']} v{model_info['version']}")
        else:
            st.error("❌ Inference API: Offline")
    
    with col2:
        # MLflow
        mlflow_health = check_service_health("MLflow", f"{MLFLOW_TRACKING_URI}/health")
        if mlflow_health:
            st.success("✅ MLflow: Online")
        else:
            st.error("❌ MLflow: Offline")
    
    # Acciones de control
    st.subheader("Acciones de Control")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Recargar Modelo"):
            try:
                response = requests.post(f"{INFERENCE_API_URL}/reload-model", timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {result['message']}")
                    st.info(f"Versión: {result['version']}")
                else:
                    st.error("Error recargando modelo")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with col2:
        if st.button("📊 Verificar Conectividad"):
            st.info("Verificando servicios...")
            
            services = {
                "Inference API": f"{INFERENCE_API_URL}/health",
                "MLflow": f"{MLFLOW_TRACKING_URI}/health",
                "MySQL": "mysql-db:3306"
            }
            
            for service, url in services.items():
                if check_service_health(service, url):
                    st.success(f"✅ {service}: Online")
                else:
                    st.error(f"❌ {service}: Offline")
    
    # Enlaces útiles
    st.subheader("Enlaces Útiles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔗 MLflow UI"):
            st.markdown(f"[Abrir MLflow UI]({MLFLOW_TRACKING_URI})")
    
    with col2:
        if st.button("🔗 Airflow UI"):
            st.markdown("[Abrir Airflow UI](http://localhost:8080)")
    
    with col3:
        if st.button("🔗 MinIO Console"):
            st.markdown("[Abrir MinIO Console](http://localhost:9001)")

# ==========================================
# Sidebar
# ==========================================
with st.sidebar:
    st.header("🌲 Sistema MLOps")
    st.markdown("**Proyecto 2 - Covertype Classification**")
    
    st.markdown("---")
    
    # Estado del sistema
    st.subheader("Estado del Sistema")
    
    # Verificar servicios
    inference_ok = check_service_health("Inference", f"{INFERENCE_API_URL}/health")
    mlflow_ok = check_service_health("MLflow", f"{MLFLOW_TRACKING_URI}/health")
    
    if inference_ok and mlflow_ok:
        st.success("🟢 Sistema Operativo")
    else:
        st.warning("🟡 Sistema Parcialmente Operativo")
    
    st.markdown("---")
    
    # Información del proyecto
    st.subheader("Información")
    st.markdown("""
    **Grupo 3:**
    - Abel Albuez Sanchez
    - Omar Gaston Chalas  
    - Mauricio Morales
    
    **Tecnologías:**
    - Airflow (Orquestación)
    - MLflow (Tracking)
    - FastAPI (Inferencia)
    - Streamlit (UI)
    - MySQL (Datos)
    - MinIO (Artifacts)
    """)
    
    st.markdown("---")
    
    # Métricas rápidas
    st.subheader("Métricas Rápidas")
    stats = get_data_stats()
    if stats:
        st.metric("Muestras Totales", f"{stats['total_samples']:,}")
        st.metric("Batches", f"{stats['batches']:,}")

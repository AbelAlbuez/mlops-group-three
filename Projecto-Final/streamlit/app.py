import os
import requests
import pandas as pd
import streamlit as st

def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000")


API_BASE_URL = get_api_base_url()

def get_health():
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e), "model_loaded": False}


def get_model_info():
    try:
        resp = requests.get(f"{API_BASE_URL}/model-info", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_models_history():
    try:
        resp = requests.get(f"{API_BASE_URL}/models/history", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def call_predict(features: dict):
    resp = requests.post(
        f"{API_BASE_URL}/predict",
        json=features,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


st.set_page_config(
    page_title="Predicción de Precios de Vivienda",
    layout="wide",
)


st.sidebar.title("Estado de la API")
health = get_health()
if health.get("status") == "ok":
    st.sidebar.success("API Conectada")
else:
    st.sidebar.error("API no disponible")
    st.sidebar.write(health.get("error", "Error desconocido"))

# Información del modelo actual
st.sidebar.subheader("Información del Modelo")
model_info = get_model_info()
if model_info:
    st.sidebar.markdown(f"**Modelo:** `{model_info['model_name']}`")
    st.sidebar.markdown(f"**Versión:** `v{model_info['model_version']}`")
    st.sidebar.markdown(f"**Stage:** `{model_info['model_stage']}`")
    st.sidebar.markdown("**Métricas:**")
    for k, v in model_info["metrics"].items():
        st.sidebar.markdown(f"- `{k}`: `{v:.4f}`")
else:
    st.sidebar.warning("No se pudo obtener información del modelo.")

st.sidebar.markdown("---")
st.sidebar.caption(f"API base: `{API_BASE_URL}`")

st.title("Predicción de Precios de Vivienda")

tab_pred, tab_history = st.tabs(["Inferencia", "Historial y Explicabilidad"])


with tab_pred:
    st.header("Ingresar características de la propiedad")

    st.markdown(
        "Completar los campos con la información de la vivienda. "
        "El sistema usará el **modelo en stage `Production`** registrado en MLflow."
    )

    # Ejemplos pre-cargados
    ejemplos = {
        "Ejemplo 1": {
            "longitude": -122.23,
            "latitude": 37.88,
            "housing_median_age": 20,
            "total_rooms": 1500,
            "total_bedrooms": 300,
            "population": 800,
            "households": 300,
            "median_income": 3.5,
        },
        "Ejemplo 2": {
            "longitude": -118.30,
            "latitude": 34.05,
            "housing_median_age": 35,
            "total_rooms": 800,
            "total_bedrooms": 200,
            "population": 1200,
            "households": 500,
            "median_income": 4.2,
        },
    }

    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.subheader("Ejemplos Pre-cargados")
        ej_nombre = st.selectbox(
            "Seleccionar ejemplo:",
            options=["-- Ninguno --"] + list(ejemplos.keys()),
        )
    # Valores por defecto
    if ej_nombre != "-- Ninguno --":
        default = ejemplos[ej_nombre]
    else:
        default = {
            "longitude": -122.23,
            "latitude": 37.88,
            "housing_median_age": 20,
            "total_rooms": 1500,
            "total_bedrooms": 300,
            "population": 800,
            "households": 300,
            "median_income": 3.5,
        }

    with st.form("prediction_form"):
        st.subheader("Características numéricas")

        c1, c2, c3 = st.columns(3)
        with c1:
            bed = st.number_input(
                "Número de habitaciones (bed)",
                value=3.0,
                min_value=0.0,
                step=1.0,
            )
        with c2:
            bath = st.number_input(
                "Número de baños (bath)",
                value=2.0,
                min_value=0.0,
                step=0.5,
            )
        with c3:
            acre_lot = st.number_input(
                "Tamaño del lote (acre_lot)",
                value=0.10,
                min_value=0.0,
                step=0.01,
            )

        c4, c5, c6 = st.columns(3)
        with c4:
            house_size = st.number_input(
                "Tamaño de la casa (house_size)",
                value=1500.0,
                min_value=0.0,
                step=10.0,
            )
        with c5:
            zip_code_num = st.number_input(
                "Código postal (zip_code)",
                value=21201.0,
                min_value=0.0,
                step=1.0,
            )
        with c6:
            year_built = st.number_input(  
                "Año de construcción (no usado por el modelo)",
                value=1990.0,
                min_value=1800.0,
                step=1.0,
            )

        st.subheader("Características categóricas")

        c7, c8 = st.columns(2)
        with c7:
            status = st.selectbox(
                "Estado de la vivienda (status)",
                options=[
                    "for_sale",
                    "sold",
                ],
                index=0,
            )
        with c8:
            state = st.text_input(
                "Estado (state)",
                value="MD",
            )

        st.subheader("Ubicación (ciudad)")

        city = st.selectbox(
            "Ciudad",
            options=[
                "Baltimore",
                "Buffalo",
                "Chicago",
                "Cleveland",
                "Columbus",
                "Detroit",
                "Houston",
                "Indianapolis",
                "Jacksonville",
                "Kansas",
            ],
            index=0,
        )

        submitted = st.form_submit_button("Calcular precio estimado")

        if submitted:
            # zip_code como string (como lo vio el modelo)
            zip_code_str = str(int(zip_code_num)) if zip_code_num > 0 else ""


            features = {
                "bed": bed,
                "bath": bath,
                "acre_lot": acre_lot,
                "house_size": house_size,
                "status": status,
                "city": city,
                "state": state,
                "zip_code": zip_code_str,
            }

            try:
                with st.spinner("Consultando modelo en producción..."):
                    pred = call_predict(features)

                st.success("Predicción realizada correctamente")

                col_pred, col_meta = st.columns([1, 1])

                with col_pred:
                    st.metric(
                        "Precio estimado de la vivienda",
                        f"{pred['predicted_price']:,.2f}",
                    )

                with col_meta:
                    st.markdown("**Modelo utilizado:**")
                    st.write(f"Nombre: `{pred['model_name']}`")
                    st.write(f"Versión: `v{pred['model_version']}`")
                    st.write(f"Stage: `{pred['model_stage']}`")
                    st.write(f"Run ID: `{pred['run_id']}`")
            except requests.exceptions.RequestException as e:
                st.error(f"Error de la API: {e}")
                try:
                    st.json(e.response.json())
                except Exception:
                    pass



with tab_history:
    st.header("Historial de modelos registrados en MLflow")

    st.markdown(
        "Aquí se muestra un registro de los modelos entrenados, "
        "su stage actual, métricas y (cuando aplique) el motivo de rechazo."
    )

    history = get_models_history()
    if not history:
        st.info("No se encontró historial de modelos para este nombre en MLflow.")
    else:
        df = pd.DataFrame(history)

        # (df['metrics'] es un dict por fila)
        metrics_df = df["metrics"].apply(pd.Series)
        df = pd.concat([df.drop(columns=["metrics"]), metrics_df], axis=1)
        
        if "creation_timestamp" in df.columns:
            df["created_at"] = pd.to_datetime(
                df["creation_timestamp"], unit="ms"
            ).dt.strftime("%Y-%m-%d %H:%M:%S")


        # Orden sugerida de columnas
        cols_order = [
            "model_name",
            "model_version",
            "model_stage",
            "run_id",
            "status",
            "rejection_reason",
            "rmse",
            "mae",
            "r2",
            "created_at",
        ]
        cols_order = [c for c in cols_order if c in df.columns]
        df = df[cols_order]

        # Marcar producción
        if "model_stage" in df.columns:
            df["is_production"] = df["model_stage"].eq("Production")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

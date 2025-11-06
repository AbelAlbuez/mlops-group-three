import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Configuración de la página
st.set_page_config(
    page_title="Predicción de Readmisión",
    page_icon="🏥",
    layout="wide"
)

# Título
st.title("🏥 Predicción de Readmisión - Pacientes Diabéticos")
st.markdown("---")

# Verificar conexión con API
try:
    health = requests.get(f"{API_URL}/health", timeout=5)
    if health.status_code == 200:
        st.sidebar.success("✅ API Conectada")
        
        # Obtener info del modelo
        model_info = requests.get(f"{API_URL}/model-info", timeout=5).json()
        st.sidebar.markdown("### 🤖 Información del Modelo")
        st.sidebar.metric("Modelo", model_info['model_name'])
        st.sidebar.metric("Versión", f"v{model_info['model_version']}")
        st.sidebar.metric("Stage", model_info['model_stage'])
        if model_info.get('accuracy'):
            st.sidebar.metric("Accuracy", f"{model_info['accuracy']:.2%}")
    else:
        st.sidebar.error("❌ API no disponible")
except:
    st.sidebar.error("❌ No se puede conectar a la API")
    st.error(f"No se puede conectar a la API en {API_URL}")
    st.stop()

# Ejemplos predefinidos
EJEMPLOS = {
    "-- Seleccionar ejemplo --": None,
    "Ejemplo 1: Bajo Riesgo": {
        "race": "Caucasian",
        "gender": "Female",
        "age_bucket": "[70-80)",
        "time_in_hospital": 3,
        "num_lab_procedures": 41,
        "num_procedures": 0,
        "num_medications": 11,
        "number_outpatient": 0,
        "number_emergency": 0,
        "number_inpatient": 0,
        "number_diagnoses": 6,
        "max_glu_serum": "None",
        "a1c_result": "None",
        "insulin": "Steady",
        "change_med": True,
        "diabetes_med": True,
        "diag_1": "428",
        "diag_2": "250.01",
        "diag_3": "401",
        "medical_specialty": "Cardiology",
        "admission_type_id": 1,
        "discharge_disposition_id": 1,
        "admission_source_id": 7
    },
    "Ejemplo 2: Alto Riesgo": {
        "race": "AfricanAmerican",
        "gender": "Male",
        "age_bucket": "[80-90)",
        "time_in_hospital": 7,
        "num_lab_procedures": 65,
        "num_procedures": 3,
        "num_medications": 18,
        "number_outpatient": 2,
        "number_emergency": 1,
        "number_inpatient": 1,
        "number_diagnoses": 9,
        "max_glu_serum": ">300",
        "a1c_result": ">8",
        "insulin": "Up",
        "change_med": True,
        "diabetes_med": True,
        "diag_1": "250.01",
        "diag_2": "428",
        "diag_3": "401",
        "medical_specialty": "InternalMedicine",
        "admission_type_id": 1,
        "discharge_disposition_id": 1,
        "admission_source_id": 7
    }
}

# Selector de ejemplos
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Ejemplos Pre-cargados")
ejemplo_seleccionado = st.sidebar.selectbox(
    "Seleccionar ejemplo:",
    list(EJEMPLOS.keys())
)

datos_ejemplo = EJEMPLOS[ejemplo_seleccionado]

# Formulario
with st.form("patient_form"):
    st.subheader("👤 Datos del Paciente")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        race = st.selectbox(
            "Raza",
            ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other"],
            index=0 if not datos_ejemplo else ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other"].index(datos_ejemplo.get("race", "Caucasian"))
        )
    
    with col2:
        gender = st.selectbox(
            "Género",
            ["Male", "Female", "Unknown/Invalid"],
            index=0 if not datos_ejemplo else ["Male", "Female", "Unknown/Invalid"].index(datos_ejemplo.get("gender", "Male"))
        )
    
    with col3:
        age_bucket = st.selectbox(
            "Rango de Edad",
            ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", 
             "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"],
            index=6 if not datos_ejemplo else ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", 
                                               "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"].index(datos_ejemplo.get("age_bucket", "[60-70)"))
        )
    
    st.markdown("### 🏥 Información de Hospitalización")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        time_in_hospital = st.number_input(
            "Días en hospital",
            min_value=1,
            max_value=14,
            value=datos_ejemplo.get("time_in_hospital", 3) if datos_ejemplo else 3
        )
    
    with col2:
        num_lab_procedures = st.number_input(
            "Procedimientos de laboratorio",
            min_value=0,
            value=datos_ejemplo.get("num_lab_procedures", 40) if datos_ejemplo else 40
        )
    
    with col3:
        num_procedures = st.number_input(
            "Procedimientos médicos",
            min_value=0,
            value=datos_ejemplo.get("num_procedures", 0) if datos_ejemplo else 0
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_medications = st.number_input(
            "Número de medicamentos",
            min_value=0,
            value=datos_ejemplo.get("num_medications", 10) if datos_ejemplo else 10
        )
    
    with col2:
        number_diagnoses = st.number_input(
            "Número de diagnósticos",
            min_value=0,
            value=datos_ejemplo.get("number_diagnoses", 6) if datos_ejemplo else 6
        )
    
    with col3:
        admission_type_id = st.number_input(
            "Tipo de admisión (ID)",
            min_value=1,
            value=datos_ejemplo.get("admission_type_id", 1) if datos_ejemplo else 1
        )
    
    st.markdown("### 📊 Historial de Visitas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        number_outpatient = st.number_input(
            "Visitas ambulatorias",
            min_value=0,
            value=datos_ejemplo.get("number_outpatient", 0) if datos_ejemplo else 0
        )
    
    with col2:
        number_emergency = st.number_input(
            "Visitas de emergencia",
            min_value=0,
            value=datos_ejemplo.get("number_emergency", 0) if datos_ejemplo else 0
        )
    
    with col3:
        number_inpatient = st.number_input(
            "Hospitalizaciones previas",
            min_value=0,
            value=datos_ejemplo.get("number_inpatient", 0) if datos_ejemplo else 0
        )
    
    st.markdown("### 🔬 Resultados de Pruebas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_glu_serum = st.selectbox(
            "Glucosa sérica máxima",
            ["None", "Norm", ">200", ">300"],
            index=0 if not datos_ejemplo else ["None", "Norm", ">200", ">300"].index(datos_ejemplo.get("max_glu_serum", "None"))
        )
    
    with col2:
        a1c_result = st.selectbox(
            "Resultado A1C",
            ["None", "Norm", ">7", ">8"],
            index=0 if not datos_ejemplo else ["None", "Norm", ">7", ">8"].index(datos_ejemplo.get("a1c_result", "None"))
        )
    
    st.markdown("### 💊 Medicamentos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        insulin = st.selectbox(
            "Insulina",
            ["No", "Steady", "Up", "Down"],
            index=0 if not datos_ejemplo else ["No", "Steady", "Up", "Down"].index(datos_ejemplo.get("insulin", "No"))
        )
    
    with col2:
        change_med = st.checkbox(
            "Cambio en medicación",
            value=datos_ejemplo.get("change_med", False) if datos_ejemplo else False
        )
    
    with col3:
        diabetes_med = st.checkbox(
            "Medicamento para diabetes",
            value=datos_ejemplo.get("diabetes_med", True) if datos_ejemplo else True
        )
    
    st.markdown("### 🩺 Diagnósticos (Códigos ICD)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        diag_1 = st.text_input(
            "Diagnóstico principal",
            value=datos_ejemplo.get("diag_1", "428") if datos_ejemplo else "428"
        )
    
    with col2:
        diag_2 = st.text_input(
            "Diagnóstico secundario",
            value=datos_ejemplo.get("diag_2", "250") if datos_ejemplo else "250"
        )
    
    with col3:
        diag_3 = st.text_input(
            "Diagnóstico terciario",
            value=datos_ejemplo.get("diag_3", "401") if datos_ejemplo else "401"
        )
    
    st.markdown("### 📋 Información Administrativa")
    
    col1, col2 = st.columns(2)
    
    with col1:
        medical_specialty = st.text_input(
            "Especialidad médica",
            value=datos_ejemplo.get("medical_specialty", "Cardiology") if datos_ejemplo else "Cardiology"
        )
        
        discharge_disposition_id = st.number_input(
            "Disposición de alta (ID)",
            min_value=1,
            value=datos_ejemplo.get("discharge_disposition_id", 1) if datos_ejemplo else 1
        )
    
    with col2:
        admission_source_id = st.number_input(
            "Fuente de admisión (ID)",
            min_value=1,
            value=datos_ejemplo.get("admission_source_id", 7) if datos_ejemplo else 7
        )
    
    # Botón de predicción
    submitted = st.form_submit_button("🔮 Realizar Predicción", type="primary", use_container_width=True)

# Procesar predicción
if submitted:
    with st.spinner("Realizando predicción..."):
        
        # Preparar datos
        patient_data = {
            "race": race,
            "gender": gender,
            "age_bucket": age_bucket,
            "time_in_hospital": time_in_hospital,
            "num_lab_procedures": num_lab_procedures,
            "num_procedures": num_procedures,
            "num_medications": num_medications,
            "number_outpatient": number_outpatient,
            "number_emergency": number_emergency,
            "number_inpatient": number_inpatient,
            "number_diagnoses": number_diagnoses,
            "max_glu_serum": max_glu_serum,
            "a1c_result": a1c_result,
            "insulin": insulin,
            "change_med": change_med,
            "diabetes_med": diabetes_med,
            "diag_1": diag_1,
            "diag_2": diag_2,
            "diag_3": diag_3,
            "medical_specialty": medical_specialty,
            "admission_type_id": admission_type_id,
            "discharge_disposition_id": discharge_disposition_id,
            "admission_source_id": admission_source_id
        }
        
        try:
            # Llamar a la API
            response = requests.post(
                f"{API_URL}/predict",
                json=patient_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                st.markdown("---")
                st.subheader("📊 Resultados de la Predicción")
                
                # Determinar color
                is_high_risk = result['prediction'] == 1
                color = "#FF4B4B" if is_high_risk else "#00CC00"
                icon = "🔴" if is_high_risk else "🟢"
                
                # Mostrar resultado principal
                st.markdown(f"""
                <div style='
                    padding: 20px;
                    border-radius: 10px;
                    background-color: {color}20;
                    border: 2px solid {color};
                    text-align: center;
                '>
                    <h1 style='color: {color}; margin: 0;'>{icon} {result['risk_level']}</h1>
                    <h2 style='margin: 10px 0;'>Probabilidad: {result['probability']:.1%}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("")
                
                # Métricas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Predicción", "Alto Riesgo" if is_high_risk else "Bajo Riesgo")
                
                with col2:
                    st.metric("Probabilidad", f"{result['probability']:.1%}")
                
                with col3:
                    st.metric("Modelo Usado", f"{result['model_name']} v{result['model_version']}")
                
                # Interpretación
                st.markdown("---")
                st.markdown("### 📖 Interpretación")
                
                if is_high_risk:
                    st.warning("""
                    ⚠️ **Alto Riesgo de Readmisión**
                    
                    El modelo predice que este paciente tiene alto riesgo de ser readmitido 
                    en menos de 30 días. Se recomienda seguimiento cercano.
                    """)
                else:
                    st.success("""
                    ✅ **Bajo Riesgo de Readmisión**
                    
                    El modelo predice que este paciente tiene bajo riesgo de readmisión 
                    en menos de 30 días.
                    """)
                
            else:
                st.error(f"Error en la predicción: {response.status_code}")
                st.json(response.json())
                
        except Exception as e:
            st.error(f"Error al conectar con la API: {str(e)}")
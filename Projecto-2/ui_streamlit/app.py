import os, requests, pandas as pd, streamlit as st

API_URL = os.getenv("INFERENCE_API_URL", "http://localhost:8504")

st.set_page_config(page_title="Predicción Forestal - Grupo 3", page_icon="🌲", layout="centered")
st.title("🌲 Predicción Forestal - Grupo 3")

with st.sidebar:
    st.header("⚙️ Config")
    api_base = st.text_input("Inference API URL", API_URL)
    if st.button("Check health"):
        try:
            r = requests.get(f"{api_base}/health", timeout=5)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

# --- ICONOS Y AYUDAS ---
ICON = {
    "elevation": "🗻",
    "aspect": "🧭",
    "slope": "⛰️",
    "horizontal_distance_to_hydrology": "💧↔️",
    "vertical_distance_to_hydrology": "💧↕️",
    "horizontal_distance_to_roadways": "🛣️↔️",
    "hillshade_9am": "🌅",
    "hillshade_noon": "☀️",
    "hillshade_3pm": "🌇",
    "horizontal_distance_to_fire_points": "🔥↔️",
    "wilderness_area": "🌲",
    "soil_type": "🧪",
}

HELP = {
    "elevation": "Altitud sobre el nivel del mar (m).",
    "aspect": "Orientación del terreno (0–360°, 0 = Norte).",
    "slope": "Inclinación del terreno en grados.",
    "horizontal_distance_to_hydrology": "Distancia horizontal a cuerpos de agua (m).",
    "vertical_distance_to_hydrology": "Diferencia de altura con respecto al agua (m).",
    "horizontal_distance_to_roadways": "Distancia horizontal a carreteras (m).",
    "hillshade_9am": "Iluminación (0–255) calculada a las 9am.",
    "hillshade_noon": "Iluminación (0–255) calculada al mediodía.",
    "hillshade_3pm": "Iluminación (0–255) calculada a las 3pm.",
    "horizontal_distance_to_fire_points": "Distancia horizontal a puntos de incendios (m).",
    "wilderness_area": "Área silvestre (ID entero según tu pipeline).",
    "soil_type": "Tipo de suelo (ID entero según tu pipeline).",
}

def L(name):
    return f"{ICON[name]}  {name}"

st.subheader("Input features")

basic = st.toggle("Modo avanzado", value=False)

defaults = dict(aspect=90, h9=180, h12=200, h15=160, vhyd=10, hfire=1000)

if not basic:
    # --- MODO BÁSICO (7 campos) ---
    elevation = st.number_input(L("elevation"), 0, 5000, 2500, 1, help=HELP["elevation"])
    slope = st.number_input(L("slope"), 0, 90, 10, 1, help=HELP["slope"])
    hhyd = st.number_input(L("horizontal_distance_to_hydrology"), 0, 10000, 100, 1,
                           help=HELP["horizontal_distance_to_hydrology"])
    hroad = st.number_input(L("horizontal_distance_to_roadways"), 0, 100000, 500, 1,
                            help=HELP["horizontal_distance_to_roadways"])
    h12 = st.number_input(L("hillshade_noon"), 0, 255, defaults["h12"], 1, help=HELP["hillshade_noon"])

    w_area = st.number_input(L("wilderness_area"), 0, 10, 1, 1, help=HELP["wilderness_area"])
    soil = st.number_input(L("soil_type"), 0, 100, 12, 1, help=HELP["soil_type"])

    payload = {
        "rows": [{
            "elevation": elevation,
            "aspect": defaults["aspect"],
            "slope": slope,
            "horizontal_distance_to_hydrology": hhyd,
            "vertical_distance_to_hydrology": defaults["vhyd"],
            "horizontal_distance_to_roadways": hroad,
            "hillshade_9am": defaults["h9"],
            "hillshade_noon": h12,
            "hillshade_3pm": defaults["h15"],
            "horizontal_distance_to_fire_points": defaults["hfire"],
            "wilderness_area": w_area,
            "soil_type": soil
        }]
    }

else:
    # --- MODO AVANZADO (12 campos) ---
    col1, col2 = st.columns(2)
    with col1:
        elevation = st.number_input(L("elevation"), 0, 5000, 2500, 1, help=HELP["elevation"])
        aspect = st.number_input(L("aspect"), 0, 360, defaults["aspect"], 1, help=HELP["aspect"])
        slope = st.number_input(L("slope"), 0, 90, 10, 1, help=HELP["slope"])
        hhyd = st.number_input(L("horizontal_distance_to_hydrology"), 0, 10000, 100, 1,
                               help=HELP["horizontal_distance_to_hydrology"])
        vhyd = st.number_input(L("vertical_distance_to_hydrology"), -1000, 1000, defaults["vhyd"], 1,
                               help=HELP["vertical_distance_to_hydrology"])
        hroad = st.number_input(L("horizontal_distance_to_roadways"), 0, 100000, 500, 1,
                                help=HELP["horizontal_distance_to_roadways"])
    with col2:
        h9 = st.number_input(L("hillshade_9am"), 0, 255, defaults["h9"], 1, help=HELP["hillshade_9am"])
        h12 = st.number_input(L("hillshade_noon"), 0, 255, defaults["h12"], 1, help=HELP["hillshade_noon"])
        h15 = st.number_input(L("hillshade_3pm"), 0, 255, defaults["h15"], 1, help=HELP["hillshade_3pm"])
        hfire = st.number_input(L("horizontal_distance_to_fire_points"), 0, 100000, defaults["hfire"], 1,
                                help=HELP["horizontal_distance_to_fire_points"])
        w_area = st.number_input(L("wilderness_area"), 0, 10, 1, 1, help=HELP["wilderness_area"])
        soil = st.number_input(L("soil_type"), 0, 100, 12, 1, help=HELP["soil_type"])

    payload = {
        "rows": [{
            "elevation": elevation,
            "aspect": aspect,
            "slope": slope,
            "horizontal_distance_to_hydrology": hhyd,
            "vertical_distance_to_hydrology": vhyd,
            "horizontal_distance_to_roadways": hroad,
            "hillshade_9am": h9,
            "hillshade_noon": h12,
            "hillshade_3pm": h15,
            "horizontal_distance_to_fire_points": hfire,
            "wilderness_area": w_area,
            "soil_type": soil
        }]
    }


if st.button("🔮 Inferir"):
    try:
        r = requests.post(f"{api_base}/predict", json=payload, timeout=15)
        if r.status_code != 200:
            st.error(f"HTTP {r.status_code}: {r.text}")
        else:
            out = r.json()
            st.success(f"Predicción: {out['predictions'][0]}")
            st.write("Modelo:")
            st.json(out.get("model", {}))
            probs = out.get("probabilities")
            if probs:
                dfp = pd.DataFrame(probs[0]).T
                dfp.index = ["proba"]
                st.write("Probabilidades:")
                st.dataframe(dfp)
    except Exception as e:
        st.error(str(e))

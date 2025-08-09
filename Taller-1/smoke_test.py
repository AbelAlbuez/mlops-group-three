from pathlib import Path
import joblib
import pandas as pd
from typing import List

MODELS_DIR = Path("Modelos/migrated")
MODELS = ["knn", "svm", "rf"]

# Muestras crudas (incluye island/sex/year por si tu preprocesamiento las usó)
RAW_SAMPLES = [
    {"bill_length_mm": 44.5, "bill_depth_mm": 17.1, "flipper_length_mm": 200, "body_mass_g": 4200,
     "island": "Biscoe", "sex": "male", "year": 2008},
    {"bill_length_mm": 50.4, "bill_depth_mm": 15.2, "flipper_length_mm": 224, "body_mass_g": 5350,
     "island": "Dream", "sex": "female", "year": 2009},
]

def expand_features(df: pd.DataFrame, expected_cols: List[str]) -> pd.DataFrame:
    """
    Construye un DataFrame con exactamente las columnas esperadas por el modelo.
    - Soporta numéricas base, 'year'
    - One-hot dinámico para island_* (p.ej. island_Dream, island_Torgersen)
    - Soporta sex_male / sex_female
    """
    out = pd.DataFrame(index=df.index)

    # numéricas base
    for c in ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]:
        if c in expected_cols:
            out[c] = df.get(c)

    # year
    if "year" in expected_cols:
        out["year"] = df.get("year", 2008)

    # sexo (male/female)
    sex_series = df.get("sex", "male").astype(str).str.lower()
    if "sex_male" in expected_cols:
        out["sex_male"] = (sex_series == "male").astype(int)
    if "sex_female" in expected_cols:
        out["sex_female"] = (sex_series == "female").astype(int)

    # island_* dinámico
    if any(c.startswith("island_") for c in expected_cols):
        isl = df.get("island", "Biscoe").astype(str)
        for c in expected_cols:
            if c.startswith("island_"):
                val = c.split("island_", 1)[1]
                out[c] = (isl == val).astype(int)

    # Si faltó alguna columna esperada, rellena con 0
    for c in expected_cols:
        if c not in out.columns:
            out[c] = 0

    # orden exacto
    return out[expected_cols]

def expected_columns(pipe) -> List[str]:
    """
    Intenta inferir las columnas de entrada esperadas:
    1) del 'scaler' si existe
    2) del 'identity' si hubiera
    3) del clasificador ('clf') – muchos estimadores tienen feature_names_in_
    Si no existe, cae a columnas numéricas básicas.
    """
    # 1 / 2
    for step_name in ("scaler", "identity"):
        step = pipe.named_steps.get(step_name)
        if step is not None:
            cols = getattr(step, "feature_names_in_", None)
            if cols is not None:
                return list(cols)

    # 3
    clf = pipe.named_steps.get("clf")
    cols = getattr(clf, "feature_names_in_", None)
    if cols is not None:
        return list(cols)

    # fallback
    return ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]

def main():
    raw_df = pd.DataFrame(RAW_SAMPLES)

    for name in MODELS:
        pkl = MODELS_DIR / f"{name}.pkl"
        print(f"\n=== {name.upper()} ===")
        if not pkl.exists():
            print(f"❌ Missing file: {pkl}")
            continue

        pipe = joblib.load(pkl)
        print("Steps:", list(pipe.named_steps.keys()))

        exp_cols = expected_columns(pipe)
        df = expand_features(raw_df, exp_cols)

        preds = pipe.predict(df).tolist()
        print("Predictions:", preds)

        if hasattr(pipe, "predict_proba"):
            try:
                probas = pipe.predict_proba(df)
                classes = getattr(pipe, "classes_", None)
                print("Proba shape:", getattr(probas, "shape", None))
                if classes is not None:
                    print("Classes:", [str(c) for c in classes])
            except Exception as e:
                print("predict_proba not available:", e)

if __name__ == "__main__":
    main()

import os, json, argparse, joblib, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import seaborn as sns  # <- agregado para dataset interno de pingüinos

# Features esperadas si usamos dataset de pingüinos
PENGUIN_FEATURES = [
    "bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"
]

# Carpeta de salida (fija en ./models dentro del repo)
MODELS_DIR = Path("./models")


def load_penguins_csv(csv_path: str, target_col: str = "species"):
    """Carga dataset CSV de pingüinos"""
    df = pd.read_csv(csv_path)
    missing = [c for c in PENGUIN_FEATURES + [target_col] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en CSV: {missing}")

    X = df[PENGUIN_FEATURES].astype(float)
    y = df[target_col].astype("category").cat.codes  # etiquetas numéricas
    classes = list(df[target_col].astype("category").cat.categories)
    return X, y, classes


def load_penguins_fallback():
    """Dataset interno de pingüinos si no se pasa CSV"""
    df = sns.load_dataset("penguins")
    df = df.dropna(subset=PENGUIN_FEATURES + ["species"])  # eliminar filas con NA
    X = df[PENGUIN_FEATURES].astype(float)
    y = df["species"].astype("category").cat.codes
    classes = list(df["species"].astype("category").cat.categories)
    return X, y, classes


def train_and_save(X, y, classes, out_dir: Path):
    """Entrena KNN y RF, guarda modelos y metadatos"""
    out_dir.mkdir(parents=True, exist_ok=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- KNN ---
    knn = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", KNeighborsClassifier(n_neighbors=5))
    ])
    knn.fit(X_tr, y_tr)
    y_pred = knn.predict(X_te)
    knn_metrics = {
        "accuracy": float(accuracy_score(y_te, y_pred)),
        "f1_macro": float(f1_score(y_te, y_pred, average="macro"))
    }
    joblib.dump(knn, out_dir / "knn.pkl")

    # --- Random Forest ---
    rf = Pipeline([
        ("clf", RandomForestClassifier(n_estimators=200, random_state=42))
    ])
    rf.fit(X_tr, y_tr)
    y_pred = rf.predict(X_te)
    rf_metrics = {
        "accuracy": float(accuracy_score(y_te, y_pred)),
        "f1_macro": float(f1_score(y_te, y_pred, average="macro"))
    }
    joblib.dump(rf, out_dir / "rf.pkl")

    # --- Metadatos ---
    meta = {
        "classes": classes,
        "feature_order": PENGUIN_FEATURES if X.shape[1] == 4 else list(X.columns),
        "models": {
            "knn.pkl": knn_metrics,
            "rf.pkl": rf_metrics
        }
    }
    with open(out_dir / "model_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print("✅ Modelos guardados en:", out_dir.resolve())
    print("   knn.pkl ", knn_metrics)
    print("   rf.pkl  ", rf_metrics)


def main():
    parser = argparse.ArgumentParser(description="Entrena KNN y RF y guarda .pkl en ./models")
    parser.add_argument("--csv", type=str, default=None,
                        help="Ruta a CSV de pingüinos (con species y 4 features)")
    parser.add_argument("--target", type=str, default="species",
                        help="Nombre de la columna objetivo (default: species)")
    args = parser.parse_args()

    if args.csv and Path(args.csv).exists():
        print("→ Usando dataset de pingüinos:", args.csv)
        X, y, classes = load_penguins_csv(args.csv, args.target)
    else:
        print("→ CSV no provisto o no existe. Usando dataset interno de pingüinos")
        X, y, classes = load_penguins_fallback()

    train_and_save(X, y, classes, MODELS_DIR)


if __name__ == "__main__":
    main()
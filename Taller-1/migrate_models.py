from pathlib import Path
import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

# Rutas base
ROOT = Path(__file__).parent
SRC = ROOT / "Modelos"
DST = SRC / "migrated"
DST.mkdir(exist_ok=True, parents=True)

def save_pipeline(model_pkl: Path, scaler_pkl: Path | None, out_name: str):
    clf = joblib.load(model_pkl)
    if scaler_pkl and scaler_pkl.exists():
        scaler = joblib.load(scaler_pkl)
        pipe = Pipeline([("scaler", scaler), ("clf", clf)])
    else:
        pipe = Pipeline([("identity", FunctionTransformer(lambda X: X)), ("clf", clf)])
    out_path = DST / out_name
    joblib.dump(pipe, out_path)
    print(f"✔ Saved pipeline: {out_path}")

# KNN
save_pipeline(
    SRC / "KNN" / "Palmer_penguins_KNN.pkl",
    SRC / "KNN" / "scaler_Palmer_penguins_KNN.pkl",
    "knn.pkl"
)

# SVM
save_pipeline(
    SRC / "SVM" / "Palmer_penguins_SVM.pkl",
    SRC / "SVM" / "scaler_palmer_penguins_SVM.pkl",
    "svm.pkl"
)

# Random Forest (sin scaler)
save_pipeline(
    SRC / "Random Forest" / "Palmer_penguins_Random_Forest.pkl",
    None,
    "rf.pkl"
)

print("✅ All migrated pipelines saved in:", DST)

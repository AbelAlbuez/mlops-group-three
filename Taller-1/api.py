# api.py
from pathlib import Path
from typing import Dict, List, Optional
import json

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
ROOT = Path(__file__).parent
# Use migrated pipelines (each is a full sklearn Pipeline ready to predict)
MODELS: Dict[str, Path] = {
    "knn": ROOT / "Modelos" / "migrated" / "knn.pkl",
    "svm": ROOT / "Modelos" / "migrated" / "svm.pkl",
    "rf":  ROOT / "Modelos" / "migrated" / "rf.pkl",
}
DEFAULT_MODEL = "rf"

# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------
class PenguinInput(BaseModel):
    # numeric required
    bill_length_mm: float = Field(..., example=44.5)
    bill_depth_mm: float = Field(..., example=17.1)
    flipper_length_mm: float = Field(..., example=200)
    body_mass_g: float = Field(..., example=4200)
    # optional raw fields (handled if your scaler expects them)
    island: Optional[str] = Field(None, example="Biscoe")      # Dream, Torgersen, Biscoe
    sex: Optional[str] = Field(None, example="male")           # male, female
    year: Optional[int] = Field(None, example=2008)

class BatchInput(BaseModel):
    items: List[PenguinInput]

# -------------------------------------------------------------------
# App + In-memory registry
# -------------------------------------------------------------------
app = FastAPI(title="Palmer Penguins API", version="1.0")

_loaded: Dict[str, object] = {}
_current: Optional[str] = None

# -------------------------------------------------------------------
# Helpers to handle expected columns (scaler/one-hot/year)
# -------------------------------------------------------------------
def expected_columns(pipe) -> List[str]:
    """Infer expected input columns from pipeline steps or fallback to numeric."""
    # Prefer preprocessor step (scaler or identity) if it exposes feature_names_in_
    for step_name in ("scaler", "identity"):
        step = pipe.named_steps.get(step_name)
        if step is not None:
            cols = getattr(step, "feature_names_in_", None)
            if cols is not None:
                return list(cols)
    # Some classifiers might have feature_names_in_
    clf = pipe.named_steps.get("clf")
    cols = getattr(clf, "feature_names_in_", None)
    if cols is not None:
        return list(cols)
    # Fallback to the basic numeric columns used across examples
    return ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]

def expand_features(df: pd.DataFrame, expected_cols: List[str]) -> pd.DataFrame:
    """
    Build a DataFrame with exactly the expected columns:
    - Numeric: bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g
    - Optional: year
    - One-hot for island_* and sex_* (sex_male/sex_female)
    Missing columns are created with zeros; unknown islands map to all-zeros.
    """
    out = pd.DataFrame(index=df.index)

    # numeric base
    for c in ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]:
        if c in expected_cols:
            out[c] = df.get(c)

    # year
    if "year" in expected_cols:
        out["year"] = df.get("year", 2008)

    # sex one-hot
    if any(c.startswith("sex_") for c in expected_cols):
        sex_series = df.get("sex", "male").astype(str).str.lower()
        if "sex_male" in expected_cols:
            out["sex_male"] = (sex_series == "male").astype(int)
        if "sex_female" in expected_cols:
            out["sex_female"] = (sex_series == "female").astype(int)

    # island one-hot (dynamic based on expected column names)
    if any(c.startswith("island_") for c in expected_cols):
        isl = df.get("island", "Biscoe").astype(str)
        for c in expected_cols:
            if c.startswith("island_"):
                val = c.split("island_", 1)[1]
                out[c] = (isl == val).astype(int)

    # Fill any missing expected columns with 0
    for c in expected_cols:
        if c not in out.columns:
            out[c] = 0

    # Keep exact order
    return out[expected_cols]

def to_dataframe(items: List[PenguinInput], pipe) -> pd.DataFrame:
    raw = pd.DataFrame([x.dict() for x in items])
    exp_cols = expected_columns(pipe)
    return expand_features(raw, exp_cols)

# -------------------------------------------------------------------
# Startup: load all pipelines
# -------------------------------------------------------------------
@app.on_event("startup")
def startup():
    global _current
    for name, path in MODELS.items():
        if not path.exists():
            raise RuntimeError(f"Missing model file: {path}")
        _loaded[name] = joblib.load(path)
    _current = DEFAULT_MODEL

# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serve the main HTML page."""
    html_file = ROOT / "Static" / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="HTML file not found")
    return html_file.read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok", "active_model": _current, "available": list(_loaded.keys())}

@app.get("/models")
def list_models():
    return {"active": _current, "available": list(_loaded.keys())}

@app.post("/models/select/{name}")
def select_model(name: str):
    """BONUS: switch the active model used for inference."""
    global _current
    if name not in _loaded:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found.")
    _current = name
    return {"message": f"active model set to '{name}'"}

@app.post("/predict")
def predict(item: PenguinInput):
    if _current is None:
        raise HTTPException(500, "No active model.")
    pipe = _loaded[_current]
    df = to_dataframe([item], pipe)
    pred = pipe.predict(df)[0]
    result = {"model": _current, "prediction": str(pred)}
    if hasattr(pipe, "predict_proba"):
        try:
            proba = pipe.predict_proba(df)[0].tolist()
            classes = [str(c) for c in getattr(pipe, "classes_", [])]
            result["probs"] = dict(zip(classes, proba))
        except Exception:
            result["probs"] = {}
    return result

@app.post("/predict/batch")
def predict_batch(payload: BatchInput):
    if _current is None:
        raise HTTPException(500, "No active model.")
    pipe = _loaded[_current]
    df = to_dataframe(payload.items, pipe)
    preds = [str(p) for p in pipe.predict(df).tolist()]
    out = {"model": _current, "predictions": preds}
    if hasattr(pipe, "predict_proba"):
        try:
            probas = pipe.predict_proba(df).tolist()
            classes = [str(c) for c in getattr(pipe, "classes_", [])]
            out["probs"] = [dict(zip(classes, row)) for row in probas]
        except Exception:
            pass
    return out

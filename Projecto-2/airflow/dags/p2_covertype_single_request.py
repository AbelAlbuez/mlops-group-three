from __future__ import annotations
from datetime import datetime, timedelta
import os
import json
import pathlib
import typing as t

import pandas as pd
import requests

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

# Config vía Variables de Airflow
API_BASE      = Variable.get("P2_API_BASE", default_var="http://10.43.100.103:80")
GROUP_ID      = Variable.get("P2_GROUP_ID", default_var="3")
API_PATH      = Variable.get("P2_API_PATH", default_var="/data")
TARGET_COL    = Variable.get("P2_TARGET_COL", default_var="Cover_Type")
SCHEDULE_CRON = Variable.get("P2_SCHEDULE_CRON", default_var="*/5 * * * *")  # 1 run cada 5 min (un batch)
DATA_DIR      = Variable.get("P2_DATA_DIR", default_var="/opt/airflow/data/p2")
RANDOM_STATE  = int(Variable.get("P2_RANDOM_STATE", default_var="42"))
TEST_SIZE     = float(Variable.get("P2_TEST_SIZE", default_var="0.2"))

# Crea carpeta para artefactos locales (persistencia simple)
pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="p2_covertype_single_request",
    description="Proyecto 2: una request por ejecución → preprocess → train/eval",
    schedule_interval=SCHEDULE_CRON, 
    start_date=datetime(2025, 9, 1),
    catchup=False,
    default_args=default_args,
    tags=["p2", "covertype"],
) as dag:

    def fetch_once(**context):
        """Hace EXACTAMENTE una request al endpoint por run y empuja el JSON crudo a XCom."""
        url = f"{API_BASE.rstrip('/')}{API_PATH}?group_id={GROUP_ID}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        # Guarda crudo (opcional) a disco con timestamp del run
        ts = context["ts"].replace(":", "-")
        raw_path = os.path.join(DATA_DIR, f"raw_{ts}.json")
        with open(raw_path, "w") as f:
            json.dump(payload, f)

        context["ti"].xcom_push(key="raw", value=payload)

    def validate_and_preprocess(**context):
        """Valida esquema básico y prepara X, y."""
        raw = context["ti"].xcom_pull(key="raw")
        # La API puede devolver {"rows": [...]} o una lista de dicts directa.
        if isinstance(raw, dict) and "rows" in raw:
            df = pd.DataFrame(raw["rows"])
        else:
            df = pd.DataFrame(raw)

        if df.empty:
            raise ValueError("Dataset vacío recibido desde la API externa.")

        if TARGET_COL not in df.columns:
            raise ValueError(
                f"No se encontró la columna objetivo '{TARGET_COL}'. "
                f"Columnas disponibles: {list(df.columns)}"
            )

        # Preprocesado mínimo: fillna(0), convertir target a int si aplica
        y = df[TARGET_COL]
        try:
            y = y.astype(int)
        except Exception:
            # si no es entero, déjalo como está
            pass

        X = df.drop(columns=[TARGET_COL]).fillna(0)

        # Persistir a disco (opcional)
        ts = context["ts"].replace(":", "-")
        X.to_parquet(os.path.join(DATA_DIR, f"X_{ts}.parquet"))
        y.to_frame(name=TARGET_COL).to_parquet(os.path.join(DATA_DIR, f"y_{ts}.parquet"))

        # Enviar por XCom
        context["ti"].xcom_push(key="X_json", value=X.to_json(orient="split"))
        context["ti"].xcom_push(key="y_json", value=y.to_json(orient="split"))

    def train_eval(**context):
        """Entrena un modelo sencillo y calcula métricas (sin MLflow)."""
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, f1_score

        X_json = context["ti"].xcom_pull(key="X_json")
        y_json = context["ti"].xcom_pull(key="y_json")
        X = pd.read_json(X_json, orient="split")
        y = pd.read_json(y_json, orient="split", typ="series")

        stratify = y if y.nunique() > 1 else None
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=stratify
        )

        clf = RandomForestClassifier(
            n_estimators=150,
            max_depth=None,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        clf.fit(X_tr, y_tr)
        preds = clf.predict(X_te)

        metrics = {
            "accuracy": float(accuracy_score(y_te, preds)),
            "f1_macro": float(f1_score(y_te, preds, average="macro")),
            "n_samples_train": int(len(X_tr)),
            "n_samples_test": int(len(X_te)),
            "n_features": int(X.shape[1]),
        }

        # Guarda métricas a un archivo .json por run (sencillo)
        ts = context["ts"].replace(":", "-")
        with open(os.path.join(DATA_DIR, f"metrics_{ts}.json"), "w") as f:
            json.dump(metrics, f, indent=2)

        # También imprime a logs para ver en la UI
        print("MÉTRICAS:", json.dumps(metrics, indent=2))

        # (Opcional) persistir el modelo a disco dentro del contenedor
        # Para demo guardamos como joblib local
        try:
            import joblib
            model_path = os.path.join(DATA_DIR, f"model_{ts}.joblib")
            joblib.dump(clf, model_path)
            print(f"Modelo guardado en: {model_path}")
        except Exception as e:
            print("No se pudo guardar el modelo (opcional):", e)

    fetch = PythonOperator(
        task_id="fetch_once",
        python_callable=fetch_once,
    )
    preprocess = PythonOperator(
        task_id="validate_and_preprocess",
        python_callable=validate_and_preprocess,
    )
    train = PythonOperator(
        task_id="train_eval",
        python_callable=train_eval,
    )

    fetch >> preprocess >> train

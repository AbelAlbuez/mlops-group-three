#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import json
import io
import time
import uuid
import re
import hashlib
from typing import Optional, List

import pandas as pd
import numpy as np

import requests
import pymysql
from pymysql.cursors import DictCursor

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import joblib

# MLflow es opcional: si no pones MLFLOW_TRACKING_URI, el script sigue
import mlflow
from mlflow.tracking import MlflowClient


# =========================
# Config desde variables de entorno
# =========================
# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql-db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "covertype_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "covertype_pass123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "covertype_db")

# Fuente de datos
P2_CSV_PATH = os.getenv("P2_CSV_PATH", "/app/covertype.csv").strip()
P2_API_BASE = os.getenv("P2_API_BASE", "").strip()
P2_API_PATH = os.getenv("P2_API_PATH", "/api/covertype").strip()
P2_GROUP_ID = os.getenv("P2_GROUP_ID", "3").strip()

# Entrenamiento
P2_RANDOM_STATE = int(os.getenv("P2_RANDOM_STATE", "42"))
P2_TEST_SIZE = float(os.getenv("P2_TEST_SIZE", "0.2"))
P2_MIN_SAMPLE_INCREMENT = int(os.getenv("P2_MIN_SAMPLE_INCREMENT", "0"))  # 0 = entrenar siempre

# MLflow opcional
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "").strip()
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "covertype_classification").strip()
MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "covertype_classifier").strip()
PROMOTE_TO_STAGE = os.getenv("PROMOTE_TO_STAGE", "Production").strip()  # "" para no promover

REQUIRED_COLS = [
    'elevation', 'aspect', 'slope',
    'horizontal_distance_to_hydrology', 'vertical_distance_to_hydrology',
    'horizontal_distance_to_roadways', 'hillshade_9am', 'hillshade_noon',
    'hillshade_3pm', 'horizontal_distance_to_fire_points',
    'wilderness_area', 'soil_type', 'cover_type'
]
FEATURE_COLS = [
    'elevation', 'aspect', 'slope',
    'horizontal_distance_to_hydrology', 'vertical_distance_to_hydrology',
    'horizontal_distance_to_roadways', 'hillshade_9am', 'hillshade_noon',
    'hillshade_3pm', 'horizontal_distance_to_fire_points',
    'wilderness_area', 'soil_type'
]


# =========================
# Utilidades
# =========================
def get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=True,
        cursorclass=DictCursor,
    )


def extract_soil_type_number(soil_type_text: str) -> int:
    """Extrae el número de algo tipo 'C7756' -> 7756; si no, intenta convertir a int; si falla, 0."""
    soil_type_text = str(soil_type_text).strip()
    m = re.search(r'C(\d+)', soil_type_text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    try:
        return int(float(soil_type_text))
    except Exception:
        return 0


def get_or_create_wilderness_area_mapping(cursor, wilderness_area_text: str) -> int:
    """Asigna entero incremental a cada string de wilderness_area en tabla mapping."""
    wilderness_area_text = str(wilderness_area_text).strip()
    cursor.execute(
        "SELECT wilderness_area_numeric FROM wilderness_area_mapping WHERE wilderness_area_text=%s",
        (wilderness_area_text,),
    )
    r = cursor.fetchone()
    if r:
        return int(r["wilderness_area_numeric"])
    cursor.execute("SELECT COALESCE(MAX(wilderness_area_numeric), -1) AS max_num FROM wilderness_area_mapping")
    next_num = int(cursor.fetchone()["max_num"]) + 1
    cursor.execute(
        "INSERT INTO wilderness_area_mapping (wilderness_area_text, wilderness_area_numeric) VALUES (%s,%s)",
        (wilderness_area_text, next_num),
    )
    return next_num


def generate_data_hash(row_like) -> str:
    """Hash estable de las 13 columnas para detectar duplicados en covertype_raw."""
    parts = [
        str(row_like.get('elevation', '')),
        str(row_like.get('aspect', '')),
        str(row_like.get('slope', '')),
        str(row_like.get('horizontal_distance_to_hydrology', '')),
        str(row_like.get('vertical_distance_to_hydrology', '')),
        str(row_like.get('horizontal_distance_to_roadways', '')),
        str(row_like.get('hillshade_9am', '')),
        str(row_like.get('hillshade_noon', '')),
        str(row_like.get('hillshade_3pm', '')),
        str(row_like.get('horizontal_distance_to_fire_points', '')),
        str(row_like.get('wilderness_area', '')),
        str(row_like.get('soil_type', '')),
        str(row_like.get('cover_type', '')),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# =========================
# 1) Ingesta (CSV primero; fallback a API)
# =========================
def collect_data() -> str:
    batch_id = f"{time.strftime('%Y-%m-%d')}_{str(uuid.uuid4())[:8]}"

    # Cargar dataframe
    df = None
    if P2_CSV_PATH and os.path.exists(P2_CSV_PATH):
        print(f"[collect] Leyendo CSV: {P2_CSV_PATH}")
        df = pd.read_csv(P2_CSV_PATH)
    else:
        if not P2_API_BASE:
            raise ValueError("P2_CSV_PATH no existe y P2_API_BASE está vacío. No hay fuente de datos.")
        url = f"{P2_API_BASE.rstrip('/')}{P2_API_PATH}?group_number={P2_GROUP_ID}"
        print(f"[collect] GET {url}")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if not (isinstance(payload, dict) and "data" in payload):
            raise ValueError("Formato de API no esperado (falta clave 'data').")
        df = pd.DataFrame(payload["data"], columns=REQUIRED_COLS)

    if df is None or df.empty:
        raise ValueError("Dataset vacío.")

    # Normaliza columnas
    df.columns = (
        df.columns.str.lower()
        .str.replace(' ', '_')
        .str.replace('-', '_', regex=False)
    )

    # Validación de columnas
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    # Insertar en covertype_raw con hash anti-duplicados
    ins = dup = fail = 0
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO covertype_raw
                (elevation, aspect, slope, horizontal_distance_to_hydrology,
                 vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                 hillshade_9am, hillshade_noon, hillshade_3pm,
                 horizontal_distance_to_fire_points, wilderness_area,
                 soil_type, cover_type, batch_id, processing_status, data_hash)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'raw',%s)
            """
            for _, row in df.iterrows():
                try:
                    data_hash = generate_data_hash(row)
                    vals = [
                        str(row.get('elevation','')), str(row.get('aspect','')), str(row.get('slope','')),
                        str(row.get('horizontal_distance_to_hydrology','')),
                        str(row.get('vertical_distance_to_hydrology','')),
                        str(row.get('horizontal_distance_to_roadways','')),
                        str(row.get('hillshade_9am','')), str(row.get('hillshade_noon','')),
                        str(row.get('hillshade_3pm','')),
                        str(row.get('horizontal_distance_to_fire_points','')),
                        str(row.get('wilderness_area','')), str(row.get('soil_type','')),
                        str(row.get('cover_type','')), batch_id, data_hash
                    ]
                    cur.execute(sql, vals)
                    ins += 1
                except Exception as e:
                    if "1062" in str(e):  # duplicate entry
                        dup += 1
                    else:
                        fail += 1
        print(f"[collect] batch={batch_id} inserted={ins} dup={dup} fail={fail}")
    finally:
        conn.close()

    return batch_id


# =========================
# 2) Preproceso (raw -> data)
# =========================
def preprocess_data(batch_id: str):
    """Convierte strings a ints, mapea wilderness_area y soil_type.
       Si no hay RAW (todo duplicado), inserta 1 fila 'link' con este batch_id (FK para model_metrics).
    """
    if not batch_id:
        raise ValueError("batch_id no recibido")

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            # RAWs del batch
            cur.execute("""
                SELECT * FROM covertype_raw
                WHERE batch_id=%s AND processing_status='raw'
                ORDER BY id
            """, (batch_id,))
            rows = cur.fetchall()

            # --- Caso: todo duplicado (no hay raws nuevos) ---
            if not rows:
                cur.execute("SELECT COUNT(*) AS n FROM covertype_data")
                n = int(cur.fetchone()["n"])
                if n == 0:
                    raise ValueError(f"No hay datos RAW para batch {batch_id} y tampoco hay datos históricos en covertype_data.")
                # Clona 1 fila existente para “marcar” el batch_id
                cur.execute("""
                    SELECT elevation, aspect, slope, horizontal_distance_to_hydrology,
                           vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                           hillshade_9am, hillshade_noon, hillshade_3pm,
                           horizontal_distance_to_fire_points, wilderness_area, soil_type, cover_type
                    FROM covertype_data
                    ORDER BY id DESC LIMIT 1
                """)
                base = cur.fetchone()
                cur.execute("""
                    INSERT INTO covertype_data
                    (elevation, aspect, slope, horizontal_distance_to_hydrology,
                     vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                     hillshade_9am, hillshade_noon, hillshade_3pm,
                     horizontal_distance_to_fire_points, wilderness_area,
                     soil_type, cover_type, batch_id, raw_id, processing_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,'preprocessed')
                """, (
                    base["elevation"], base["aspect"], base["slope"],
                    base["horizontal_distance_to_hydrology"], base["vertical_distance_to_hydrology"],
                    base["horizontal_distance_to_roadways"], base["hillshade_9am"],
                    base["hillshade_noon"], base["hillshade_3pm"],
                    base["horizontal_distance_to_fire_points"], base["wilderness_area"],
                    base["soil_type"], base["cover_type"], batch_id
                ))
                print(f"[preprocess] No había RAW nuevos. Inserté 1 fila 'link' para batch {batch_id}.")
                return

            # --- Hay raws: procesar normal ---
            df = pd.DataFrame(rows)
            processed = failed = 0

            for _, r in df.iterrows():
                try:
                    converted = {}
                    for col in REQUIRED_COLS:
                        raw_value = str(r.get(col, '')).strip()
                        if raw_value == '' or raw_value.lower() in ['nan','null','none']:
                            converted[col] = 0
                        elif col == 'wilderness_area':
                            converted[col] = get_or_create_wilderness_area_mapping(cur, raw_value)
                        elif col == 'soil_type':
                            converted[col] = extract_soil_type_number(raw_value)
                        else:
                            converted[col] = int(float(raw_value))

                    cur.execute("""
                        INSERT INTO covertype_data
                        (elevation, aspect, slope, horizontal_distance_to_hydrology,
                         vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                         hillshade_9am, hillshade_noon, hillshade_3pm,
                         horizontal_distance_to_fire_points, wilderness_area,
                         soil_type, cover_type, batch_id, raw_id, processing_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'preprocessed')
                    """, [
                        converted['elevation'], converted['aspect'], converted['slope'],
                        converted['horizontal_distance_to_hydrology'], converted['vertical_distance_to_hydrology'],
                        converted['horizontal_distance_to_roadways'], converted['hillshade_9am'],
                        converted['hillshade_noon'], converted['hillshade_3pm'],
                        converted['horizontal_distance_to_fire_points'], converted['wilderness_area'],
                        converted['soil_type'], converted['cover_type'],
                        batch_id, r['id']
                    ])
                    processed += 1
                except Exception as e:
                    print(f"[preprocess] Error en raw id={r['id']}: {e}")
                    failed += 1

            # Marcar raws como processed
            cur.execute("""
                UPDATE covertype_raw
                SET processing_status='processed'
                WHERE batch_id=%s AND processing_status='raw'
            """, (batch_id,))
            print(f"[preprocess] batch={batch_id} ok={processed} fail={failed}")
    finally:
        conn.close()


# =========================
# 3) Entrenamiento + Registro + Métricas
# =========================
def train_and_publish(batch_id: str):
    t0 = time.time()
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            # Total de muestras disponibles
            cur.execute("""
                SELECT COUNT(*) AS total
                FROM covertype_data
                WHERE processing_status IN ('preprocessed','completed')
            """)
            total_samples = int(cur.fetchone()["total"])

            # Último entrenamiento (para ver incremento)
            cur.execute("""
                SELECT (n_samples_train + n_samples_test) AS last_total
                FROM model_metrics
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            last_total = int(row["last_total"]) if row else 0

            inc = total_samples - last_total
            print(f"[train] total_samples={total_samples} last_total={last_total} increment={inc} threshold={P2_MIN_SAMPLE_INCREMENT}")
            if inc < P2_MIN_SAMPLE_INCREMENT:
                print(f"[train] Incremento insuficiente; omitiendo entrenamiento.")
                return

            # Traer TODAS las filas para entrenar
            cur.execute("""
                SELECT elevation, aspect, slope, horizontal_distance_to_hydrology,
                       vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                       hillshade_9am, hillshade_noon, hillshade_3pm,
                       horizontal_distance_to_fire_points, wilderness_area,
                       soil_type, cover_type
                FROM covertype_data
                WHERE processing_status IN ('preprocessed','completed')
                ORDER BY id
            """)
            rows = cur.fetchall()
            if not rows:
                raise ValueError("[train] No hay datos para entrenar.")

            df = pd.DataFrame(rows)
            X = df[FEATURE_COLS].astype(float)
            y = df['cover_type'].astype(int)

            if len(df) < 10:
                raise ValueError(f"[train] Insuficientes filas: {len(df)}")

            stratify = y if y.nunique() > 1 else None
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=P2_TEST_SIZE, random_state=P2_RANDOM_STATE, stratify=stratify
            )

            model = RandomForestClassifier(
                n_estimators=150, max_depth=None, random_state=P2_RANDOM_STATE,
                n_jobs=-1, class_weight='balanced'
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            accuracy = float(accuracy_score(y_test, y_pred))
            f1_macro = float(f1_score(y_test, y_pred, average='macro'))
            elapsed = float(time.time() - t0)

            print(f"[train] acc={accuracy:.4f} f1_macro={f1_macro:.4f} time={elapsed:.2f}s")

            # ------- MLflow (opcional) -------
            try:
                if MLFLOW_TRACKING_URI:
                    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
                    mlflow.set_experiment(MLFLOW_EXPERIMENT)
                    with mlflow.start_run(run_name=f"batch_{batch_id}"):
                        mlflow.log_params({
                            "n_estimators": 150,
                            "max_depth": "None",
                            "random_state": P2_RANDOM_STATE,
                            "test_size": P2_TEST_SIZE,
                            "class_weight": "balanced",
                            "min_sample_increment": P2_MIN_SAMPLE_INCREMENT,
                            "model_type": "RandomForestClassifier",
                        })
                        mlflow.log_metrics({
                            "accuracy": accuracy,
                            "f1_macro": f1_macro,
                            "n_samples_train": int(len(X_train)),
                            "n_samples_test": int(len(X_test)),
                            "n_features": int(X.shape[1]),
                            "n_classes": int(y.nunique()),
                            "training_time_seconds": elapsed,
                        })
                        # Log + Registry
                        mlflow.sklearn.log_model(
                            sk_model=model,
                            artifact_path="model",
                            registered_model_name=MLFLOW_MODEL_NAME
                        )
                        run_id = mlflow.active_run().info.run_id
                        print(f"[mlflow] run_id={run_id}")

                        # Promover última versión si se pide
                        if PROMOTE_TO_STAGE:
                            client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
                            vers = client.get_latest_versions(MLFLOW_MODEL_NAME, stages=["None", "Staging", "Production"])
                            if vers:
                                # Buscar la versión asociada a este run (si aplica)
                                all_vers = client.search_model_versions(f"name='{MLFLOW_MODEL_NAME}'")
                                v_for_run = None
                                for v in all_vers:
                                    if v.run_id == run_id:
                                        v_for_run = v
                                        break
                                if v_for_run:
                                    client.transition_model_version_stage(
                                        name=MLFLOW_MODEL_NAME,
                                        version=v_for_run.version,
                                        stage=PROMOTE_TO_STAGE,
                                        archive_existing_versions=True
                                    )
                                    print(f"[mlflow] Promovido {MLFLOW_MODEL_NAME} v{v_for_run.version} -> {PROMOTE_TO_STAGE}")
            except Exception as e:
                print(f"[mlflow] Aviso: fallo en logging/registry: {e}. Continúo sin MLflow.")

            # ------- Serializar y guardar en model_metrics -------
            buf = io.BytesIO()
            joblib.dump(model, buf, compress=3)
            model_bytes = buf.getvalue()
            print(f"[train] model_bytes={len(model_bytes)/1024:.1f} KB")

            hyperparams = {
                "n_estimators": 150,
                "max_depth": None,
                "random_state": P2_RANDOM_STATE,
                "test_size": P2_TEST_SIZE,
                "class_weight": "balanced",
            }

            cur.execute("""
                INSERT INTO model_metrics
                (batch_id, accuracy, f1_macro, n_samples_train, n_samples_test,
                 n_features, model_type, hyperparameters, training_time_seconds, model_data)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                batch_id, accuracy, f1_macro, int(len(X_train)), int(len(X_test)),
                int(X.shape[1]), "RandomForestClassifier", json.dumps(hyperparams),
                elapsed, model_bytes
            ))

            # Marcar preprocessed como completed
            cur.execute("""
                UPDATE covertype_data
                SET processing_status='completed'
                WHERE processing_status='preprocessed'
            """)
            print("[train] Entrenamiento + guardado en DB completados.")
    finally:
        conn.close()


# =========================
# main()
# =========================
def main():
    batch_id = collect_data()
    preprocess_data(batch_id)
    train_and_publish(batch_id)
    print(f"Listo. batch_id={batch_id}")


if __name__ == "__main__":
    main()

from datetime import datetime
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import get_current_context

import pandas as pd
import mlflow, mlflow.sklearn
from mlflow.tracking import MlflowClient

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.ensemble import RandomForestClassifier

RAW_CONN_ID = "postgres_raw"
CLEAN_CONN_ID = "postgres_clean"

RAW_TABLE = "public.diabetic_raw"

CLEAN_SCHEMA = "clean_data"
CLEAN_TABLE = f"{CLEAN_SCHEMA}.diabetic_clean"

BATCH_SIZE = 15000

MLFLOW_TRACKING_URI = "http://mlflow:5000"
EXPERIMENT_NAME = "diabetic_risk"
MODEL_NAME = "diabetic_risk_model"
PRIMARY_METRIC = "accuracy"

CREATE_CLEAN_DDL = f"""
CREATE SCHEMA IF NOT EXISTS {CLEAN_SCHEMA};

CREATE TABLE IF NOT EXISTS {CLEAN_TABLE} (
    encounter_id              BIGINT PRIMARY KEY,
    patient_nbr               BIGINT,
    race                      TEXT,
    gender                    TEXT,
    age_bucket                TEXT,
    time_in_hospital          INT,
    num_lab_procedures        INT,
    num_procedures            INT,
    num_medications           INT,
    number_outpatient         INT,
    number_emergency          INT,
    number_inpatient          INT,
    number_diagnoses          INT,
    max_glu_serum             TEXT,
    a1c_result                TEXT,
    insulin                   TEXT,
    change_med                BOOLEAN,
    diabetes_med              BOOLEAN,
    readmitted_label          TEXT,
    diag_1                    TEXT,
    diag_2                    TEXT,
    diag_3                    TEXT,
    medical_specialty         TEXT,
    admission_type_id         INT,
    discharge_disposition_id  INT,
    admission_source_id       INT,
    outcome                   INT,
    batch_id                  BIGINT,
    split                     TEXT CHECK (split IN ('train','val','test'))
);
"""

TRANSFORM_SELECT = f"""
    SELECT
        r.encounter_id,
        r.patient_nbr,
        COALESCE(NULLIF(TRIM(r.race), '?'), 'Unknown') AS race,
        CASE
            WHEN LOWER(r.gender) IN ('male','m') THEN 'Male'
            WHEN LOWER(r.gender) IN ('female','f') THEN 'Female'
            ELSE 'Unknown/Invalid'
        END AS gender,
        REPLACE(REPLACE(r.age, '[', ''), ')', '') AS age_bucket,
        r.time_in_hospital,
        r.num_lab_procedures,
        r.num_procedures,
        r.num_medications,
        r.number_outpatient,
        r.number_emergency,
        r.number_inpatient,
        r.number_diagnoses,
        NULLIF(r.max_glu_serum, 'None') AS max_glu_serum,
        NULLIF(r.a1cresult, 'None')     AS a1c_result,
        r.insulin,
        CASE WHEN LOWER(r."change") IN ('ch','yes','true','t','1') THEN TRUE ELSE FALSE END AS change_med,
        CASE WHEN LOWER(r.diabetesmed) IN ('yes','true','t','1') THEN TRUE ELSE FALSE END AS diabetes_med,
        r.readmitted AS readmitted_label,
        r.diag_1,
        r.diag_2,
        r.diag_3,
        COALESCE(NULLIF(r.medical_specialty, '?'), 'Unknown') AS medical_specialty,
        r.admission_type_id,
        r.discharge_disposition_id,
        r.admission_source_id,
        CASE 
          WHEN r.readmitted = '<30' THEN 1
          WHEN r.readmitted IN ('>30','NO') THEN 0
          ELSE NULL
        END                                                   AS outcome,
        r.batch_id,
        CASE 
          WHEN (abs(hashtext(r.encounter_id::text)) %% 100) < 80 THEN 'train'
          WHEN (abs(hashtext(r.encounter_id::text)) %% 100) < 90 THEN 'val'
          ELSE 'test'
        END AS split
    FROM {RAW_TABLE} r
    WHERE r.batch_id = %s
"""

@dag(
    dag_id="batch_ingestion_training",
    description="Ingesta 15k → Clean build → Train & Register & Promote",
    start_date=datetime(2025, 10, 27),
    schedule="*/3 * * * *",
    catchup=False,
    is_paused_upon_creation=False,
    tags=["raw", "clean", "ml"],
)
def all_in_one_pipeline():

    # INGESTA: toma 15k sin batch_id y les asigna un batch_id (incremental)
    @task
    def ingest_next_batch_15k() -> int:
        hook = PostgresHook(postgres_conn_id=RAW_CONN_ID)
        with hook.get_conn() as conn, conn.cursor() as cur:
            # Asegura la columna batch_id
            cur.execute("""
                ALTER TABLE public.diabetic_raw
                ADD COLUMN IF NOT EXISTS batch_id BIGINT;
            """)

            # Calcula el siguiente batch_id
            cur.execute(f"SELECT COALESCE(MAX(batch_id), 0) + 1 FROM {RAW_TABLE};")
            next_batch = int(cur.fetchone()[0])

            # Asigna batch_id a los próximos 15k con batch_id IS NULL (orden estable por encounter_id)
            cur.execute(f"""
                WITH to_tag AS (
                    SELECT ctid FROM {RAW_TABLE}
                    WHERE batch_id IS NULL
                    ORDER BY encounter_id
                    LIMIT %s
                )
                UPDATE {RAW_TABLE} r
                SET batch_id = %s
                WHERE r.ctid IN (SELECT ctid FROM to_tag);
            """, (BATCH_SIZE, next_batch))

            conn.commit()

            cur.execute(f"SELECT COUNT(*) FROM {RAW_TABLE} WHERE batch_id = %s;", (next_batch,))
            tagged = int(cur.fetchone()[0])

            print(f"[INGEST] batch_id={next_batch} tagged_rows={tagged}")
            return next_batch

    # CLEAN: crea objetos clean y carga el batch
    @task
    def ensure_clean_objects():
        hook = PostgresHook(postgres_conn_id=CLEAN_CONN_ID)
        with hook.get_conn() as conn, conn.cursor() as cur:
            cur.execute(CREATE_CLEAN_DDL)
            conn.commit()
        print("[CLEAN] Schema/tabla asegurados.")

    @task
    def load_clean_for_batch(batch_id: int) -> int:
        # Lee desde RAW y escribe en CLEAN (upsert por encounter_id)
        raw = PostgresHook(postgres_conn_id=RAW_CONN_ID)
        clean = PostgresHook(postgres_conn_id=CLEAN_CONN_ID)

        # Selecciona filas transformadas del batch
        with raw.get_conn() as rconn, rconn.cursor() as rcur:
            rcur.execute(TRANSFORM_SELECT, (batch_id,))
            rows = rcur.fetchall()

        if not rows:
            print(f"[CLEAN] batch_id={batch_id} no tiene filas para limpiar.")
            return 0

        with clean.get_conn() as cconn, cconn.cursor() as ccur:
            ccur.execute("CREATE TEMP TABLE tmp_encounters (encounter_id BIGINT PRIMARY KEY);")
            ccur.executemany(
                "INSERT INTO tmp_encounters(encounter_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                [(r[0],) for r in rows],
            )
            ccur.execute(f"""
                DELETE FROM {CLEAN_TABLE} c
                USING tmp_encounters t
                WHERE c.encounter_id = t.encounter_id;
            """)

            insert_sql = f"""
                INSERT INTO {CLEAN_TABLE} (
                    encounter_id, patient_nbr, race, gender, age_bucket,
                    time_in_hospital, num_lab_procedures, num_procedures, num_medications,
                    number_outpatient, number_emergency, number_inpatient, number_diagnoses,
                    max_glu_serum, a1c_result, insulin, change_med, diabetes_med,
                    readmitted_label, diag_1, diag_2, diag_3, medical_specialty,
                    admission_type_id, discharge_disposition_id, admission_source_id,
                    outcome, batch_id, split
                ) VALUES (
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s
                );
            """
            ccur.executemany(insert_sql, rows)
            inserted = ccur.rowcount
            cconn.commit()

        print(f"[CLEAN] batch_id={batch_id} inserted={inserted}")
        return inserted

    # TRAIN + REGISTER + PROMOTE
    @task
    def train_register_promote():
        # Leer TRAIN/VAL desde CLEAN
        hook = PostgresHook(postgres_conn_id=CLEAN_CONN_ID)

        # TRAIN
        sql_train = f"""
          SELECT * FROM {CLEAN_TABLE}
          WHERE outcome IS NOT NULL AND split = 'train';
        """
        # VALIDATION
        sql_val = f"""
          SELECT * FROM {CLEAN_TABLE}
          WHERE outcome IS NOT NULL AND split = 'val';
        """

        # pandas con hooks de Airflow (DBAPI); es suficiente para este caso
        df_train = hook.get_pandas_df(sql_train)
        df_val   = hook.get_pandas_df(sql_val)

        if df_train.empty or df_val.empty:
            raise RuntimeError("No hay datos en TRAIN o VAL para entrenar/evaluar.")

        y_train = df_train["outcome"].astype(int)
        X_train = df_train.drop(columns=["outcome"], errors="ignore").select_dtypes(include="number").fillna(0)

        y_val = df_val["outcome"].astype(int)
        X_val = df_val.drop(columns=["outcome"], errors="ignore").select_dtypes(include="number").fillna(0)

        # MLflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)

        with mlflow.start_run(run_name="rf_train_val"):
            model = RandomForestClassifier(n_estimators=200, random_state=42)
            model.fit(X_train, y_train)

            y_pred = model.predict(X_val)
            acc = accuracy_score(y_val, y_pred)
            f1  = f1_score(y_val, y_pred)

            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("f1", f1)

            # guarda y registra
            mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=MODEL_NAME)

        # Promoción del mejor a Production (por accuracy)
        client = MlflowClient()
        exp = client.get_experiment_by_name(EXPERIMENT_NAME)
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=[f"metrics.{PRIMARY_METRIC} DESC"],
            max_results=1,
        )
        if not runs:
            raise RuntimeError("No hay runs exitosos para promover.")
        best_run = runs[0]

        versions = client.search_model_versions(f"name='{MODEL_NAME}' and run_id='{best_run.info.run_id}'")
        if not versions:
            raise RuntimeError("El mejor run no tiene versión registrada en el Model Registry.")

        best_v = versions[0].version

        # archiva cualquier Production actual
        for mv in client.search_model_versions(f"name='{MODEL_NAME}'"):
            if mv.current_stage == "Production":
                client.transition_model_version_stage(name=MODEL_NAME, version=mv.version, stage="Archived")

        client.transition_model_version_stage(name=MODEL_NAME, version=best_v, stage="Production")
        client.set_model_version_tag(MODEL_NAME, best_v, "primary_metric", PRIMARY_METRIC)
        client.set_model_version_tag(MODEL_NAME, best_v, "primary_metric_value",
                                     str(best_run.data.metrics.get(PRIMARY_METRIC, "")))

        print(f"[TRAIN] Promovido a Production: {MODEL_NAME} v{best_v}")

    bid = ingest_next_batch_15k()
    ensure = ensure_clean_objects()
    inserted = load_clean_for_batch(bid)
    # Asegura que la tabla existe antes de cargar
    ensure >> inserted
    # Entrena solo si hubo inserciones (simplemente dependemos de 'inserted')
    inserted >> train_register_promote()

dag_obj = all_in_one_pipeline()

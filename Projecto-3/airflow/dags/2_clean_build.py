# 2_clean_build.py
from datetime import datetime
from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook

RAW_CONN_ID = "postgres_raw"
CLEAN_CONN_ID = "postgres_clean"
RAW_SCHEMA = "raw_data"
CLEAN_SCHEMA = "clean_data"
CLEAN_TABLE = f"{CLEAN_SCHEMA}.diabetic_clean"
RAW_TABLE = "public.diabetic_raw"
RAW_BATCH_CTRL = f"{RAW_SCHEMA}.batch_control"

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    dag_id="2_clean_build",
    description="Construye la tabla CLEAN a partir de RAW con transformaciones",
    start_date=datetime(2025, 10, 1),
    schedule_interval="@once",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "depends_on_past": False},
    tags=["clean", "transform"],
) as dag:

    # ----------------------
    # Helpers / SQL
    # ----------------------
    CREATE_CLEAN_DDL = f"""
    CREATE SCHEMA IF NOT EXISTS {CLEAN_SCHEMA};

    CREATE TABLE IF NOT EXISTS {CLEAN_TABLE} (
        encounter_id           BIGINT PRIMARY KEY,
        patient_nbr            BIGINT,
        race                   TEXT,
        gender                 TEXT,
        age_bucket             TEXT,
        time_in_hospital       INT,
        num_lab_procedures     INT,
        num_procedures         INT,
        num_medications        INT,
        number_outpatient      INT,
        number_emergency       INT,
        number_inpatient       INT,
        number_diagnoses       INT,
        max_glu_serum          TEXT,
        a1c_result             TEXT,
        insulin                TEXT,
        change_med             BOOLEAN,
        diabetes_med           BOOLEAN,
        readmitted_label       TEXT,
        diag_1                 TEXT,
        diag_2                 TEXT,
        diag_3                 TEXT,
        medical_specialty      TEXT,
        admission_type_id      INT,
        discharge_disposition_id INT,
        admission_source_id    INT,
        outcome    INT,
        batch_id INT
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
            r.batch_id
        FROM {RAW_TABLE} r
        WHERE r.batch_id = %s
    """
    
    @task
    def latest_batch_id() -> int:
        """Obtiene el último batch_id disponible en RAW, tolerando ausencia de batch_control."""
        hook = PostgresHook(postgres_conn_id=RAW_CONN_ID)
        with hook.get_conn() as conn, conn.cursor() as cur:
            try:
                cur.execute("SELECT to_regclass('raw_data.batch_control') IS NOT NULL;")
                exists = cur.fetchone()[0]
            except Exception:
                # si hasta to_regclass fallara por algo raro, consideramos que no existe
                conn.rollback()
                exists = False

            if exists:
                try:
                    cur.execute("SELECT COALESCE(MAX(batch_id), 0) FROM raw_data.batch_control;")
                    bid = cur.fetchone()[0] or 0
                    return int(bid)
                except Exception:
                    # falló la lectura de batch_control -> rollback -> fallback
                    conn.rollback()

            try:
                cur.execute(f"SELECT COALESCE(MAX(batch_id), 0) FROM {RAW_TABLE};")
                bid = cur.fetchone()[0] or 0
                return int(bid)
            except Exception:
                conn.rollback()
                # como último recurso, 0
                return 0

    @task
    def ensure_clean_objects():
        """Crea esquema y tabla CLEAN si no existen."""
        hook = PostgresHook(postgres_conn_id=CLEAN_CONN_ID)
        with hook.get_conn() as conn, conn.cursor() as cur:
            cur.execute(CREATE_CLEAN_DDL)
            conn.commit()

    @task
    def load_clean_for_batch(batch_id: int) -> int:
        """
        Inserta en CLEAN los registros del batch dado (con transformaciones).
        primero elimina posibles encounter_id del batch en CLEAN.
        Retorna cantidad insertada.
        """
        # Leemos desde RAW
        raw = PostgresHook(postgres_conn_id=RAW_CONN_ID)
        clean = PostgresHook(postgres_conn_id=CLEAN_CONN_ID)

        with raw.get_conn() as rconn, rconn.cursor() as rcur:
            rcur.execute(TRANSFORM_SELECT, (batch_id,))
            rows = rcur.fetchall()

        if not rows:
            return 0

        with clean.get_conn() as cconn, cconn.cursor() as ccur:
            # Borrar por encuentro usando una tabla temporal
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
                    encounter_id, patient_nbr, race, gender, age_bucket, time_in_hospital,
                    num_lab_procedures, num_procedures, num_medications,
                    number_outpatient, number_emergency, number_inpatient, number_diagnoses,
                    max_glu_serum, a1c_result, insulin, change_med, diabetes_med,
                    readmitted_label, diag_1, diag_2, diag_3, medical_specialty,
                    admission_type_id, discharge_disposition_id, admission_source_id, outcome, batch_id
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                );
            """
            ccur.executemany(insert_sql, rows)
            inserted = ccur.rowcount
            cconn.commit()

        return inserted

    @task
    def log_summary(batch_id: int, inserted: int):
        print(f"[clean_build] batch_id={batch_id} -> inserted={inserted} rows into {CLEAN_TABLE}")

    # Orquestación
    bid = latest_batch_id()
    ensure = ensure_clean_objects()
    inserted = load_clean_for_batch(bid)
    ensure >> inserted
    log_summary(bid, inserted)

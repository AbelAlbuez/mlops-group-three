from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook

DEFAULT_ARGS = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="1_raw_batch_ingest_15k",
    description="Etiqueta lotes de 15k en diabetic_raw",
    start_date=datetime(2025, 10, 1),
    schedule_interval="@once",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "depends_on_past": False},
    tags=["raw","ingest","batch"],
):

    @task
    def create_batch_id():
        hook = PostgresHook(postgres_conn_id="postgres_raw")
        with hook.get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS batch_control (
                  batch_id BIGSERIAL PRIMARY KEY,
                  created_at TIMESTAMP DEFAULT now()
                );
                INSERT INTO batch_control DEFAULT VALUES RETURNING batch_id;
            """)
            batch_id = cur.fetchone()[0]
            conn.commit()
        return batch_id

    @task
    def tag_next_15000_rows(batch_id: int):
        """
        Marca 15k filas “sin batch_id” en diabetic_raw.
        """
        hook = PostgresHook(postgres_conn_id="postgres_raw")
        with hook.get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE diabetic_raw
                ADD COLUMN IF NOT EXISTS batch_id BIGINT;
            """)
            cur.execute("""
                WITH cte AS (
                  SELECT ctid
                  FROM diabetic_raw
                  WHERE batch_id IS NULL
                  LIMIT 15000
                )
                UPDATE diabetic_raw t
                SET batch_id = %s
                FROM cte
                WHERE t.ctid = cte.ctid;
            """, (batch_id,))
            conn.commit()

    bid = create_batch_id()
    tag_next_15000_rows(bid)

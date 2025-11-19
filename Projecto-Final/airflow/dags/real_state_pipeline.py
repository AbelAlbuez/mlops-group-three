from datetime import datetime
from io import StringIO
import os

import pandas as pd
import numpy as np
import requests
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.exceptions import AirflowSkipException

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import mlflow
import mlflow.sklearn

log = LoggingMixin().log

@dag(
    dag_id="real_estate_batch_pipeline",
    description="Pipeline batch: API → Postgres raw → Postgres Clean → train → Staging",
    start_date=datetime(2025, 1, 1),
    schedule_interval="* * * * *",
    max_active_runs=1,
    catchup=False,
    tags=["real_estate_api", "batch", "train", "staging"],
)
def real_estate_batch_pipeline():

    @task
    def fetch_and_insert_real_estate():

        # --- Config desde .env ---
        base_url = os.environ.get("REAL_ESTATE_API_BASE_URL")
        if not base_url:
            raise ValueError("REAL_ESTATE_API_BASE_URL no está definida en el entorno")
        group_number = int(os.environ.get("REAL_ESTATE_GROUP_NUMBER"))
        if not group_number:
            raise ValueError("REAL_ESTATE_GROUP_NUMBER no está definida en el entorno")
        day = os.environ.get("REAL_ESTATE_DAY")
        if not day:
            raise ValueError("REAL_ESTATE_DAY no está definida en el entorno")

        # --- API call ---
        resp = requests.get(
            f"{base_url}/data",
            params={"group_number": group_number, "day": day},
            timeout=30,
        )
        
        if resp.status_code == 400:
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text
        
            log.warning(
                "Fin de datos para group_number=%s, day=%s. Mensaje de la API: %s", group_number, day, detail,
            )
            
            raise AirflowSkipException(
                f"No hay más datos disponibles para group_number={group_number}, day={day}. "
                f"Detalle API: {detail}"
            )
        
        resp.raise_for_status()
        payload = resp.json()

        records = payload["data"]
        if not records:
            # Nada que insertar
            return

        df = pd.DataFrame(records)

        # Metadatos del JSON
        df["group_number"] = payload["group_number"]
        df["day"] = payload["day"]
        df["batch_number"] = payload["batch_number"]

        # Convertir prev_sold_date a DATE
        if "prev_sold_date" in df.columns:
            df["prev_sold_date"] = pd.to_datetime(
                df["prev_sold_date"], errors="coerce"
            ).dt.date

        # --- Obtener batch_id secuencial desde Postgres ---
        hook = PostgresHook(postgres_conn_id="postgres_raw")
        with hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(batch_id), 0) FROM real_estate_raw;")
                max_batch_id = cur.fetchone()[0]
                new_batch_id = max_batch_id + 1

        df["batch_id"] = new_batch_id

        # Orden de columnas (sin id ni ingestion_ts)
        cols = [
            "batch_id",
            "group_number",
            "day",
            "batch_number",
            "brokered_by",
            "status",
            "price",
            "bed",
            "bath",
            "acre_lot",
            "street",
            "city",
            "state",
            "zip_code",
            "house_size",
            "prev_sold_date",
        ]
        df = df[cols]

        # --- COPY a Postgres ---
        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        copy_sql = """
            COPY real_estate_raw (
                batch_id,
                group_number,
                day,
                batch_number,
                brokered_by,
                status,
                price,
                bed,
                bath,
                acre_lot,
                street,
                city,
                state,
                zip_code,
                house_size,
                prev_sold_date
            )
            FROM STDIN WITH (FORMAT csv)
        """

        with hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.copy_expert(copy_sql, buffer)
            conn.commit()

        # Devolver new_batch_id para usarlo en otras tasks
        return new_batch_id
        
    @task
    def clean_real_estate_batch():
        raw_hook = PostgresHook(postgres_conn_id="postgres_raw")
        clean_hook = PostgresHook(postgres_conn_id="postgres_clean")

        # 1) Saber hasta qué batch se ha procesado en CLEAN
        with clean_hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(batch_id), 0) FROM real_estate_clean;")
                last_clean_batch = cur.fetchone()[0]

        # 2) Traer de RAW solo los batches nuevos
        with raw_hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        batch_id,
                        group_number,
                        day,
                        batch_number,
                        brokered_by,
                        status,
                        price,
                        bed,
                        bath,
                        acre_lot,
                        street,
                        city,
                        state,
                        zip_code,
                        house_size,
                        prev_sold_date,
                        ingestion_ts
                    FROM real_estate_raw
                    WHERE batch_id > %s
                    """,
                    (last_clean_batch,),
                )
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]

        if not rows:
            # Nada nuevo que procesar
            return

        df = pd.DataFrame(rows, columns=colnames)

        # ---- LIMPIEZA ----
        # Tipos
        df["bed"] = df["bed"].astype("Int64")
        df["bath"] = df["bath"].astype("Int64")
        df["batch_number"] = df["batch_number"].astype("Int64")
        df["group_number"] = df["group_number"].astype("Int64")
        df["house_size"] = df["house_size"].astype("Int64")
        
        df["brokered_by"] = df["brokered_by"].astype("Int64")
        df["street"] = df["street"].astype("Int64")

        # zip_code a texto
        df["zip_code"] = (
            df["zip_code"]
            .astype("Int64")
            .astype("string")
        )

        # Fecha
        df["prev_sold_date"] = pd.to_datetime(
            df["prev_sold_date"], errors="coerce"
        ).dt.date

        # Filtro de registros inválidos
        df = df[df["price"].notna() & (df["price"] > 0)]
        df = df[df["bed"].notna() & (df["bed"] > 0)]
        df = df[df["bath"].notna() & (df["bath"] >= 0)]
        df = df[df["house_size"].notna() & (df["house_size"] > 0)]

        # Duplicados
        df = df.drop_duplicates(
            subset=["street", "city", "state", "zip_code", "price", "bed", "bath", "house_size"]
        )

        # Features derivadas
        df["price_per_sqft"] = df["price"] / df["house_size"].replace({0: np.nan})
        df["price_per_bed"] = df["price"] / df["bed"].replace({0: np.nan})
        df["price_per_acre"] = np.where(
            (df["acre_lot"].notna()) & (df["acre_lot"] > 0),
            df["price"] / df["acre_lot"],
            np.nan,
        )
        
        max_val = 9.9999e7
        
        for col in ["price_per_sqft", "price_per_bed", "price_per_acre"]:
            df.loc[df[col].abs() > max_val, col] = np.nan

        if df.empty:
            return

        # Ordenar columnas como en la tabla clean (sin id ni processed_ts)
        cols = [
            "batch_id",
            "group_number",
            "day",
            "batch_number",
            "brokered_by",
            "status",
            "price",
            "bed",
            "bath",
            "acre_lot",
            "street",
            "city",
            "state",
            "zip_code",
            "house_size",
            "prev_sold_date",
            "price_per_sqft",
            "price_per_bed",
            "price_per_acre",
            "ingestion_ts",
        ]
        df = df[cols]

        # 3) COPY a CLEAN
        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        copy_sql = """
            COPY real_estate_clean (
                batch_id,
                group_number,
                day,
                batch_number,
                brokered_by,
                status,
                price,
                bed,
                bath,
                acre_lot,
                street,
                city,
                state,
                zip_code,
                house_size,
                prev_sold_date,
                price_per_sqft,
                price_per_bed,
                price_per_acre,
                ingestion_ts
            )
            FROM STDIN WITH (FORMAT csv)
        """

        with clean_hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.copy_expert(copy_sql, buffer)
            conn.commit()

        return int(df["batch_id"].nunique())

    @task
    def train_regression_model(min_rows: int = 5000):

        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        import mlflow
        import mlflow.sklearn
        import numpy as np

        clean_hook = PostgresHook(postgres_conn_id="postgres_clean")

        # 1) Obtener último batch_id y tamaño de ese batch
        with clean_hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        MAX(batch_id) AS max_batch_id,
                        COUNT(*)     AS total_rows
                    FROM real_estate_clean
                    WHERE batch_id = (SELECT MAX(batch_id) FROM real_estate_clean)
                    """
                )
                row = cur.fetchone()
                if row is None or row[0] is None:
                    log.warning("No hay datos en real_estate_clean aún.")
                    raise AirflowSkipException("CLEAN_DATA vacío, no se puede entrenar.")

                last_batch_id, last_batch_rows = row

        log.info(
            "Último batch_id=%s tiene %s filas en CLEAN.",
            last_batch_id,
            last_batch_rows,
        )

        # Si el último batch tiene muy pocas filas, saltar entrenamiento
        if last_batch_rows < min_rows:
            msg = (
                f"Batch_id={last_batch_id} tiene solo {last_batch_rows} filas "
                f"(mínimo requerido={min_rows}). Se hace SKIP de entrenamiento."
            )
            log.warning(msg)
            raise AirflowSkipException(msg)

        # 2) Cargar datos completos de CLEAN para entrenar
        with clean_hook.get_conn() as conn:
            df = pd.read_sql(
                """
                SELECT
                    price,
                    bed,
                    bath,
                    acre_lot,
                    house_size,
                    status,
                    city,
                    state,
                    zip_code
                FROM real_estate_clean
                """,
                conn,
            )

        if df.empty:
            raise AirflowSkipException("real_estate_clean está vacío al intentar entrenar.")

        # ---------- Ingeniería de features con Pipeline ----------
        numeric_cols = ["bed", "bath", "acre_lot", "house_size"]
        cat_cols = ["status", "city", "state", "zip_code"]

        # Asegurar tipos
        df[numeric_cols] = df[numeric_cols].astype(float)

        # Target
        y = df["price"].astype(float)

        # Eliminar filas con NaN en numéricas o target
        mask = df[numeric_cols].notna().all(axis=1) & y.notna()
        df = df[mask]
        y = y[mask]

        if len(df) < 100:
            raise AirflowSkipException(
                f"Tras limpieza quedan solo {len(df)} filas para entrenar. Muy pocas."
            )

        # Dataset de entrada para el modelo: SOLO columnas originales
        feature_cols = numeric_cols + cat_cols
        X = df[feature_cols].copy()

        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.pipeline import Pipeline

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", "passthrough", numeric_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ]
        )

        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )

        model = Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("rf", rf),
            ]
        )

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        log.info(
            "Shapes para entrenamiento: X_train=%s, X_test=%s",
            X_train.shape,
            X_test.shape,
        )

        # 3) Configurar MLflow
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("real_estate_rf")

        with mlflow.start_run(run_name=f"rf_batch_{last_batch_id}") as run:
            mlflow.set_tag("status", "candidate")
            mlflow.set_tag("rejection_reason", "")
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Log params
            mlflow.log_param("model_type", "RandomForestRegressor")
            mlflow.log_param("n_estimators", 400)
            mlflow.log_param("max_depth", 20)
            mlflow.log_param("min_samples_leaf", 5)
            mlflow.log_param("min_rows_threshold", min_rows)
            mlflow.log_param("last_batch_id", int(last_batch_id))
            mlflow.log_param("n_features", int(X.shape[1]))
            mlflow.log_param("numeric_features", ",".join(numeric_cols))
            mlflow.log_param("categorical_features", ",".join(cat_cols))

            # Log metrics
            mlflow.log_metric("rmse", float(rmse))
            mlflow.log_metric("mae", float(mae))
            mlflow.log_metric("r2", float(r2))
            mlflow.log_metric("train_size", int(len(X_train)))
            mlflow.log_metric("test_size", int(len(X_test)))

            # Log modelo
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name="real_estate_rf",
            )

            log.info(
                "Entrenamiento RF completado. run_id=%s, rmse=%.2f, mae=%.2f, r2=%.3f",
                run.info.run_id,
                rmse,
                mae,
                r2,
            )

        return run.info.run_id
            


    @task
    def promote_best_model(
        model_name: str = "real_estate_rf",
        metric_name: str = "rmse",
        min_improvement: float = 0.05,  # 5% mejor que el modelo actual
    ):

        from airflow.operators.python import get_current_context
        from mlflow.tracking import MlflowClient
        import mlflow

        # --- Obtener run_id desde XCom ---
        ctx = get_current_context()
        ti = ctx["ti"]  # TaskInstance
        run_id = ti.xcom_pull(task_ids="train_regression_model")

        if not run_id:
            raise AirflowSkipException(
                "No se encontró run_id en XCom desde train_regression_model. "
                "No se puede decidir promoción."
            )

        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)
        client = MlflowClient(tracking_uri=tracking_uri)

        # --- Métricas del run candidato ---
        run = client.get_run(run_id)
        cand_metrics = run.data.metrics

        if metric_name not in cand_metrics:
            raise AirflowSkipException(
                f"El run {run_id} no tiene la métrica '{metric_name}'. "
                "No se puede decidir promoción."
            )

        cand_rmse = cand_metrics[metric_name]
        cand_mae = cand_metrics.get("mae")

        log.info(
            "Candidato run_id=%s -> %s=%.4f, mae=%.4f",
            run_id,
            metric_name,
            cand_rmse,
            cand_mae if cand_mae is not None else float("nan"),
        )

        # --- Buscar versión del modelo asociada a este run ---
        candidate_versions = client.search_model_versions(
            f"name='{model_name}' and run_id='{run_id}'"
        )
        if not candidate_versions:
            raise AirflowSkipException(
                f"No se encontró ninguna versión registrada en MLflow "
                f"para el modelo '{model_name}' con run_id={run_id}."
            )

        cand_version = max(candidate_versions, key=lambda v: int(v.version))
        cand_ver_num = int(cand_version.version)

        log.info(
            "Versión candidata del modelo '%s' -> version=%s, current_stage=%s",
            model_name,
            cand_ver_num,
            cand_version.current_stage,
        )

        # --- Buscar modelo en Producción (si existe) ---
        all_versions = client.search_model_versions(f"name='{model_name}'")
        prod_versions = [v for v in all_versions if v.current_stage == "Production"]

        if not prod_versions:
        
            log.info(
                "No existe versión en Producción para '%s'. "
                "Promoviendo versión %s como Production.",
                model_name,
                cand_ver_num,
            )
            client.transition_model_version_stage(
                name=model_name,
                version=cand_ver_num,
                stage="Production",
            )
            
            client.set_tag(run_id, "status", "promoted")
            client.set_tag(run_id, "rejection_reason", "")
            
            return {
                "decision": "promoted_first_model",
                "new_prod_version": cand_ver_num,
                "rmse": float(cand_rmse),
                "mae": float(cand_mae) if cand_mae is not None else None,
            }

        current_prod = max(prod_versions, key=lambda v: int(v.version))
        prod_ver_num = int(current_prod.version)
        prod_run_id = current_prod.run_id

        prod_run = client.get_run(prod_run_id)
        prod_metrics = prod_run.data.metrics
        prod_rmse = prod_metrics.get(metric_name)
        prod_mae = prod_metrics.get("mae")

        log.info(
            "Modelo actual en Producción -> version=%s, run_id=%s, %s=%.4f, mae=%.4f",
            prod_ver_num,
            prod_run_id,
            metric_name,
            prod_rmse,
            prod_mae if prod_mae is not None else float("nan"),
        )

        if prod_rmse is None:
            log.warning(
                "El modelo en Producción no tiene la métrica '%s'. "
                "Se promoverá el nuevo modelo por defecto.",
                metric_name,
            )
            client.transition_model_version_stage(
                name=model_name,
                version=cand_ver_num,
                stage="Production",
            )
            client.transition_model_version_stage(
                name=model_name,
                version=prod_ver_num,
                stage="Archived",
            )
            
            client.set_tag(run_id, "status", "promoted")
            client.set_tag(run_id, "rejection_reason",
                           "Modelo anterior sin métrica; promovido por defecto")
            client.set_tag(prod_run_id, "status", "archived")
            client.set_tag(prod_run_id, "rejection_reason",
                           "Reemplazado por modelo sin métrica en producción")
                           
            return {
                "decision": "promoted_no_metric_in_prod",
                "old_prod_version": prod_ver_num,
                "new_prod_version": cand_ver_num,
            }

        # --- Comparar RMSE (menor es mejor) ---
        threshold = prod_rmse * (1 - min_improvement)

        log.info(
            "Comparando candidatos: nuevo %s=%.4f vs prod %s=%.4f (umbral mejora=%.4f)",
            metric_name,
            cand_rmse,
            metric_name,
            prod_rmse,
            threshold,
        )

        if cand_rmse < threshold:
            # Mejora suficiente -> promovemos
            log.info(
                "El nuevo modelo mejora el %s en al menos %.1f%%. "
                "Promoviendo versión %s a Production y archivando %s.",
                metric_name,
                min_improvement * 100,
                cand_ver_num,
                prod_ver_num,
            )

            client.transition_model_version_stage(
                name=model_name,
                version=cand_ver_num,
                stage="Production",
            )
            client.transition_model_version_stage(
                name=model_name,
                version=prod_ver_num,
                stage="Archived",
            )
            
            client.set_tag(run_id, "status", "promoted")
            client.set_tag(
                run_id,
                "rejection_reason",
                "",
            )
            client.set_tag(prod_run_id, "status", "archived")
            client.set_tag(
                prod_run_id,
                "rejection_reason",
                "Reemplazado por modelo con mejor desempeño",
            )

            return {
                "decision": "promoted",
                "old_prod_version": prod_ver_num,
                "new_prod_version": cand_ver_num,
                "rmse_new": float(cand_rmse),
                "rmse_old": float(prod_rmse),
                "mae_new": float(cand_mae) if cand_mae is not None else None,
                "mae_old": float(prod_mae) if prod_mae is not None else None,
            }
        else:
            # No mejora lo suficiente -> se archiva el candidato
            log.warning(
                "El nuevo modelo NO mejora el %s en al menos %.1f%%. "
                "Se mantiene la versión %s en Producción.",
                metric_name,
                min_improvement * 100,
                prod_ver_num,
            )

            client.transition_model_version_stage(
                name=model_name,
                version=cand_ver_num,
                stage="Archived",
            )
            
            client.set_tag(run_id, "status", "rejected")
            client.set_tag(
                run_id,
                "rejection_reason",
                (
                    f"El modelo no superó el umbral de mejora del {min_improvement*100:.1f}% "
                    f"en {metric_name}. rmse_nuevo={cand_rmse:.4f}, rmse_prod={prod_rmse:.4f}"
                ),
            )
            client.set_tag(prod_run_id, "status", "production")
            client.set_tag(prod_run_id, "rejection_reason", "")

            return {
                "decision": "not_promoted",
                "prod_version_kept": prod_ver_num,
                "candidate_version": cand_ver_num,
                "rmse_new": float(cand_rmse),
                "rmse_old": float(prod_rmse),
            }



    # Chaining TASK 
    raw_task = fetch_and_insert_real_estate()
    clean_task = clean_real_estate_batch()
    train_task = train_regression_model()
    promote_task = promote_best_model()
    
    raw_task >> clean_task >> train_task >> promote_task

dag = real_estate_batch_pipeline()

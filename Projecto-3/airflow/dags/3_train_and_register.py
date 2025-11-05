from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import mlflow, mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime
from mlflow.tracking import MlflowClient

MODEL_NAME = "diabetic_risk_model"
MLFLOW_TRACKING_URI = "http://mlflow:5000"
EXPERIMENT_NAME = "diabetic_risk"
PRIMARY_METRIC = "accuracy"

@dag(
    dag_id="3_train_and_register",
    start_date=datetime(2025, 10, 27),
    schedule_interval="@once",
    catchup=False,
    max_active_runs=1,
    tags=["mlflow", "production"]
)
def train_and_register():

    @task
    def train_and_log():
        hook = PostgresHook(postgres_conn_id="postgres_clean")
        
        df_train = hook.get_pandas_df("""
        SELECT * FROM clean_data.diabetic_clean
        WHERE outcome IS NOT NULL AND split = 'train'
        """)
        
        df_eval = hook.get_pandas_df("""
        SELECT *
        FROM clean_data.diabetic_clean
        WHERE outcome IS NOT NULL AND split = 'val'
        """)
        
        y_train = df_train["outcome"].astype(int)
        X_train = df_train.drop(columns=["outcome","split"], errors="ignore").select_dtypes(include="number").fillna(0)
        
        y_eval = df_eval["outcome"].astype(int)
        X_eval = df_eval.drop(columns=["outcome","split"], errors="ignore").select_dtypes(include="number").fillna(0)

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        with mlflow.start_run(run_name="rf_train_on_split"):
            model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train)

            y_pred = model.predict(X_eval)
            acc = accuracy_score(y_eval, y_pred)
            f1 = f1_score(y_eval, y_pred, pos_label=1)

            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("f1", f1)

            mlflow.sklearn.log_model(
                model, artifact_path="model", registered_model_name=MODEL_NAME
            )

    @task
    def promote_best_to_staging():
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
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
        versions = client.search_model_versions(
            f"name='{MODEL_NAME}' and run_id='{best_run.info.run_id}'"
        )
        if not versions:
            raise RuntimeError("El mejor run no tiene versión registrada en el Model Registry.")

        v = versions[0].version

        # Archiva Production actual
        for mv in client.search_model_versions(f"name='{MODEL_NAME}'"):
            if mv.current_stage == "Production":
                client.transition_model_version_stage(MODEL_NAME, mv.version, "Archived")

        client.transition_model_version_stage(MODEL_NAME, v, "Production")
        client.set_model_version_tag(MODEL_NAME, v, "primary_metric", PRIMARY_METRIC)
        client.set_model_version_tag(MODEL_NAME, v, "primary_metric_value",
                                     str(best_run.data.metrics.get(PRIMARY_METRIC, "")))

    t_train = train_and_log()
    t_promote = promote_best_to_staging()
    t_train >> t_promote

dag_obj = train_and_register()
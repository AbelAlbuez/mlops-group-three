from datetime import datetime
import os
import requests

from airflow.decorators import dag, task
from airflow.utils.log.logging_mixin import LoggingMixin

log = LoggingMixin().log


@dag(
    dag_id="00_restart_data_generation",
    description="Reinicia los batches de la API de real estate para un grupo/día",
    start_date=datetime(2025, 11, 17),
    schedule_interval=None,
    catchup=False,
    tags=["real_estate", "maintenance"],
)
def restart_data_generation_dag():
    @task
    def restart_data_generation(**context):

        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}

        # Config desde .env
        base_url = os.environ.get("REAL_ESTATE_API_BASE_URL")
        if not base_url:
            raise ValueError("REAL_ESTATE_API_BASE_URL no está definida en el entorno")

        default_group = os.environ.get("REAL_ESTATE_GROUP_NUMBER", "3")
        default_day = os.environ.get("REAL_ESTATE_DAY", "Tuesday")

        group_number_str = str(conf.get("group_number", default_group))
        day = conf.get("day", default_day)

        try:
            group_number = int(group_number_str)
        except ValueError:
            raise ValueError(
                f"REAL_ESTATE_GROUP_NUMBER / group_number debe ser entero, llegó: {group_number_str!r}"
            )

        log.info(
            "Reiniciando generación de datos para group_number=%s, day=%s",
            group_number,
            day,
        )

        resp = requests.get(
            f"{base_url}/restart_data_generation",
            params={"group_number": group_number, "day": day},
            timeout=30,
        )
        resp.raise_for_status()

        try:
            payload = resp.json()
        except Exception:
            payload = resp.text

        log.info("Respuesta de /restart_data_generation: %s", payload)

    restart_data_generation()

dag = restart_data_generation_dag()

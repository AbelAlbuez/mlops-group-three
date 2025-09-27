FROM apache/airflow:2.9.2-python3.12

# Instalar dependencias del DAG con constraints para 2.9.2 + py3.12
USER airflow

COPY requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt \
    --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.12.txt
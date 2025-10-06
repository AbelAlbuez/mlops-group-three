from __future__ import annotations
from datetime import datetime, timedelta
import os
import json
import pathlib
import typing as t
import uuid
import time
import pymysql
import re
import hashlib

import pandas as pd
import requests
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import mlflow
import mlflow.sklearn

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

# Config vía Variables de Airflow (configuradas desde .env via docker-compose)
# Las variables se inyectan automáticamente desde AIRFLOW_VAR_* en docker-compose.yml
API_BASE      = Variable.get("P2_API_BASE")
GROUP_ID      = Variable.get("P2_GROUP_ID")
API_PATH      = Variable.get("P2_API_PATH")
TARGET_COL    = Variable.get("P2_TARGET_COL")
SCHEDULE_CRON = Variable.get("P2_SCHEDULE_CRON")
DATA_DIR      = Variable.get("P2_DATA_DIR")
RANDOM_STATE  = int(Variable.get("P2_RANDOM_STATE"))
TEST_SIZE     = float(Variable.get("P2_TEST_SIZE"))
MIN_SAMPLE_INCREMENT = int(Variable.get("P2_MIN_SAMPLE_INCREMENT"))

# MySQL Configuration
MYSQL_HOST = Variable.get("MYSQL_HOST")
MYSQL_PORT = int(Variable.get("MYSQL_PORT"))
MYSQL_USER = Variable.get("MYSQL_USER")
MYSQL_PASSWORD = Variable.get("MYSQL_PASSWORD")
MYSQL_DATABASE = Variable.get("MYSQL_DATABASE")

# MLflow Configuration
MLFLOW_TRACKING_URI = Variable.get("MLFLOW_TRACKING_URI")

# Crea carpeta para artefactos locales (persistencia simple)
pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def get_mysql_connection():
    """Create MySQL connection"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_or_create_wilderness_area_mapping(cursor, wilderness_area_text):
    """Get numeric value for wilderness area, create new mapping if not exists"""
    wilderness_area_text = str(wilderness_area_text).strip()

    # Check if mapping already exists
    select_sql = "SELECT wilderness_area_numeric FROM wilderness_area_mapping WHERE wilderness_area_text = %s"
    cursor.execute(select_sql, (wilderness_area_text,))
    result = cursor.fetchone()

    if result:
        return result['wilderness_area_numeric']

    # Get the next available numeric value
    max_sql = "SELECT COALESCE(MAX(wilderness_area_numeric), -1) as max_num FROM wilderness_area_mapping"
    cursor.execute(max_sql)
    max_result = cursor.fetchone()
    next_numeric = max_result['max_num'] + 1

    # Insert new mapping
    insert_sql = "INSERT INTO wilderness_area_mapping (wilderness_area_text, wilderness_area_numeric) VALUES (%s, %s)"
    cursor.execute(insert_sql, (wilderness_area_text, next_numeric))

    print(f"Created new wilderness area mapping: '{wilderness_area_text}' -> {next_numeric}")
    return next_numeric

def extract_soil_type_number(soil_type_text):
    """Extract numeric value from soil type using regex"""
    soil_type_text = str(soil_type_text).strip()

    # Pattern to match C followed by numbers (e.g., "C7756", "C4758")
    pattern = r'C(\d+)'
    
    match = re.search(pattern, soil_type_text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # If no match found, try to convert the whole string to int as fallback
    try:
        return int(float(soil_type_text))
    except (ValueError, TypeError):
        print(f"Warning: Could not extract number from soil_type: '{soil_type_text}', defaulting to 0")
        return 0

def generate_data_hash(row_data):
    """Generate SHA-256 hash of all data columns for duplicate detection"""
    # Create a string representation of all data values
    data_string = '|'.join([
        str(row_data.get('elevation', '')),
        str(row_data.get('aspect', '')),
        str(row_data.get('slope', '')),
        str(row_data.get('horizontal_distance_to_hydrology', '')),
        str(row_data.get('vertical_distance_to_hydrology', '')),
        str(row_data.get('horizontal_distance_to_roadways', '')),
        str(row_data.get('hillshade_9am', '')),
        str(row_data.get('hillshade_noon', '')),
        str(row_data.get('hillshade_3pm', '')),
        str(row_data.get('horizontal_distance_to_fire_points', '')),
        str(row_data.get('wilderness_area', '')),
        str(row_data.get('soil_type', '')),
        str(row_data.get('cover_type', ''))
    ])
    
    # Generate SHA-256 hash
    return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="p2_covertype_pipeline",
    description="Proyecto 2: collect_data → preprocess_data → train_model",
    schedule_interval=SCHEDULE_CRON,
    start_date=datetime(2025, 9, 1),
    catchup=False,
    default_args=default_args,
    tags=["p2", "covertype"],
) as dag:

    def collect_data(**context):
        """Step 1: Fetch data from API and store in MySQL database"""
        # Generate unique batch ID for this execution
        batch_id = f"{context['ds']}_{str(uuid.uuid4())[:8]}"

        # Fetch data from API
        url = f"{API_BASE.rstrip('/')}{API_PATH}?group_number={GROUP_ID}"
        print(f"Fetching data from: {url}")

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        # Parse the response data
        if isinstance(payload, dict) and "data" in payload:
            # New format: data property contains list of arrays
            data_rows = payload["data"]
            if isinstance(data_rows, list) and len(data_rows) > 0:
                # Convert list of arrays to DataFrame
                # Assuming the columns are in the expected order for covertype dataset
                column_names = [
                    'elevation', 'aspect', 'slope', 'horizontal_distance_to_hydrology',
                    'vertical_distance_to_hydrology', 'horizontal_distance_to_roadways',
                    'hillshade_9am', 'hillshade_noon', 'hillshade_3pm',
                    'horizontal_distance_to_fire_points', 'wilderness_area',
                    'soil_type', 'cover_type'
                ]
                df = pd.DataFrame(data_rows, columns=column_names)
            else:
                df = pd.DataFrame()

        if df.empty:
            raise ValueError("Empty dataset received from API")

        print(f"Received {len(df)} rows with columns: {list(df.columns)}")

        # Map any column names to lowercase with underscores
        df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')

        # Store raw data in MySQL (all as varchar)
        connection = get_mysql_connection()

        try:
            with connection.cursor() as cursor:
                insert_sql = """
                INSERT INTO covertype_raw
                (elevation, aspect, slope, horizontal_distance_to_hydrology,
                 vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                 hillshade_9am, hillshade_noon, hillshade_3pm,
                 horizontal_distance_to_fire_points, wilderness_area,
                 soil_type, cover_type, batch_id, processing_status, data_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                rows_inserted = 0
                rows_duplicated = 0
                rows_failed = 0
                
                for row_idx, row in df.iterrows():
                    try:
                        # Generate hash for duplicate detection
                        data_hash = generate_data_hash(row)
                        
                        # Store all values as strings (no type conversion)
                        values = [
                            str(row.get('elevation', '')),
                            str(row.get('aspect', '')),
                            str(row.get('slope', '')),
                            str(row.get('horizontal_distance_to_hydrology', '')),
                            str(row.get('vertical_distance_to_hydrology', '')),
                            str(row.get('horizontal_distance_to_roadways', '')),
                            str(row.get('hillshade_9am', '')),
                            str(row.get('hillshade_noon', '')),
                            str(row.get('hillshade_3pm', '')),
                            str(row.get('horizontal_distance_to_fire_points', '')),
                            str(row.get('wilderness_area', '')),
                            str(row.get('soil_type', '')),
                            str(row.get('cover_type', '')),
                            batch_id,
                            'raw',
                            data_hash
                        ]
                        cursor.execute(insert_sql, values)
                        rows_inserted += 1
                    except Exception as e:
                        error_msg = str(e).lower()
                        if 'duplicate' in error_msg or 'unique constraint' in error_msg or '1062' in str(e):
                            # MySQL error 1062 is duplicate entry error
                            print(f"WARNING: Duplicate data detected for row {row_idx + 1} in batch {batch_id}")
                            print(f"  Data: elevation={values[0]}, aspect={values[1]}, slope={values[2]}, "
                                  f"wilderness_area={values[10]}, soil_type={values[11]}, cover_type={values[12]}")
                            print(f"  Hash: {data_hash}")
                            rows_duplicated += 1
                        else:
                            print(f"Error inserting row {row_idx + 1}: {e}")
                            print(f"Row data: {row.to_dict()}")
                            rows_failed += 1
                        continue

                # Summary logging
                total_rows = len(df)
                print(f"Data collection summary for batch {batch_id}:")
                print(f"  - Total rows received: {total_rows}")
                print(f"  - Successfully inserted: {rows_inserted}")
                print(f"  - Duplicates skipped: {rows_duplicated}")
                print(f"  - Failed insertions: {rows_failed}")
                
                if rows_duplicated > 0:
                    print(f"WARNING: {rows_duplicated} duplicate rows were detected and skipped!")
                
                context["ti"].xcom_push(key="batch_id", value=batch_id)
                context["ti"].xcom_push(key="rows_inserted", value=rows_inserted)
                context["ti"].xcom_push(key="rows_duplicated", value=rows_duplicated)
                context["ti"].xcom_push(key="rows_failed", value=rows_failed)

        finally:
            connection.close()

    def preprocess_data(**context):
        """Step 2: Read from covertype_raw, convert types, and store in covertype_data"""
        # Get batch_id from previous task
        batch_id = context["ti"].xcom_pull(task_ids="collect_data", key="batch_id")

        if not batch_id:
            raise ValueError("No batch_id received from collect_data task")

        connection = get_mysql_connection()

        try:
            with connection.cursor() as cursor:
                # Fetch raw string data for the batch
                select_sql = """
                SELECT * FROM covertype_raw
                WHERE batch_id = %s AND processing_status = 'raw'
                ORDER BY id
                """

                cursor.execute(select_sql, (batch_id,))
                rows = cursor.fetchall()

                if not rows:
                    raise ValueError(f"No raw data found for batch {batch_id}")

                # Convert to DataFrame for processing
                df = pd.DataFrame(rows)
                print(f"Processing {len(df)} raw rows for batch {batch_id}")

                # Data validation and type conversion
                required_columns = [
                    'elevation', 'aspect', 'slope', 'horizontal_distance_to_hydrology',
                    'vertical_distance_to_hydrology', 'horizontal_distance_to_roadways',
                    'hillshade_9am', 'hillshade_noon', 'hillshade_3pm',
                    'horizontal_distance_to_fire_points', 'wilderness_area',
                    'soil_type', 'cover_type'
                ]

                processed_rows = 0
                failed_rows = 0

                # Process each row individually for better error handling
                for _, row in df.iterrows():
                    try:
                        # Convert string values to integers with validation
                        converted_values = {}
                        conversion_errors = []

                        for col in required_columns:
                            raw_value = str(row.get(col, '')).strip()
                            if raw_value == '' or raw_value.lower() in ['nan', 'null', 'none']:
                                converted_values[col] = 0
                            else:
                                try:
                                    if col == 'wilderness_area':
                                        # Use mapping table for wilderness area
                                        converted_values[col] = get_or_create_wilderness_area_mapping(cursor, raw_value)
                                    elif col == 'soil_type':
                                        # Extract number from soil type using regex
                                        converted_values[col] = extract_soil_type_number(raw_value)
                                    else:
                                        # Standard integer conversion for other columns
                                        converted_values[col] = int(float(raw_value))
                                except (ValueError, TypeError):
                                    conversion_errors.append(f"{col}: '{raw_value}'")
                                    converted_values[col] = 0

                        if conversion_errors:
                            print(f"Warning: Type conversion errors for row {row['id']}: {conversion_errors}")

                        # Validate and fix cover_type range (should be 1-7)
                        if 'cover_type' in converted_values:
                            if converted_values['cover_type'] < 1 or converted_values['cover_type'] > 7:
                                print(f"Warning: Invalid cover_type value {converted_values['cover_type']} for row {row['id']}, setting to 1")
                                converted_values['cover_type'] = 1

                        # Insert into covertype_data table with proper types
                        insert_sql = """
                        INSERT INTO covertype_data
                        (elevation, aspect, slope, horizontal_distance_to_hydrology,
                         vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                         hillshade_9am, hillshade_noon, hillshade_3pm,
                         horizontal_distance_to_fire_points, wilderness_area,
                         soil_type, cover_type, batch_id, raw_id, processing_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

                        values = [
                            converted_values['elevation'],
                            converted_values['aspect'],
                            converted_values['slope'],
                            converted_values['horizontal_distance_to_hydrology'],
                            converted_values['vertical_distance_to_hydrology'],
                            converted_values['horizontal_distance_to_roadways'],
                            converted_values['hillshade_9am'],
                            converted_values['hillshade_noon'],
                            converted_values['hillshade_3pm'],
                            converted_values['horizontal_distance_to_fire_points'],
                            converted_values['wilderness_area'],
                            converted_values['soil_type'],
                            converted_values['cover_type'],
                            batch_id,
                            row['id'],  # Reference to raw data
                            'preprocessed'
                        ]

                        cursor.execute(insert_sql, values)
                        processed_rows += 1

                    except Exception as e:
                        print(f"Error processing row {row['id']}: {e}")
                        failed_rows += 1
                        continue

                # Update raw data status to processed
                update_raw_sql = """
                UPDATE covertype_raw
                SET processing_status = 'processed'
                WHERE batch_id = %s AND processing_status = 'raw'
                """
                cursor.execute(update_raw_sql, (batch_id,))

                print(f"Preprocessing completed for batch {batch_id}:")
                print(f"  - Successfully processed: {processed_rows} rows")
                print(f"  - Failed to process: {failed_rows} rows")
                print(f"  - Total rows in batch: {len(df)}")

                context["ti"].xcom_push(key="preprocessed_batch_id", value=batch_id)
                context["ti"].xcom_push(key="preprocessed_rows", value=processed_rows)
                context["ti"].xcom_push(key="failed_rows", value=failed_rows)

        finally:
            connection.close()

    # TODO: This task should implement MLFlow
    def train_model(**context):
        """Step 3: Train model on ALL preprocessed data if sample increment threshold is met"""
        start_time = time.time()

        # Get batch_id from previous task (for logging purposes)
        current_batch_id = context["ti"].xcom_pull(task_ids="preprocess_data", key="preprocessed_batch_id")

        if not current_batch_id:
            raise ValueError("No batch_id received from preprocess_data task")

        connection = get_mysql_connection()

        try:
            with connection.cursor() as cursor:
                # Check total number of preprocessed samples
                total_samples_sql = """
                SELECT COUNT(*) as total_samples
                FROM covertype_data
                WHERE processing_status IN ('preprocessed', 'completed')
                """
                cursor.execute(total_samples_sql)
                total_result = cursor.fetchone()
                total_samples = total_result['total_samples'] if total_result else 0

                # Check when was the last training (get the latest model_metrics entry)
                last_training_sql = """
                SELECT n_samples_train + n_samples_test as last_total_samples, created_at
                FROM model_metrics
                ORDER BY created_at DESC
                LIMIT 1
                """
                cursor.execute(last_training_sql)
                last_training_result = cursor.fetchone()
                last_total_samples = last_training_result['last_total_samples'] if last_training_result else 0

                print(f"Total samples available: {total_samples}")
                print(f"Samples used in last training: {last_total_samples}")
                print(f"Sample increment: {total_samples - last_total_samples}")
                print(f"Required increment threshold: {MIN_SAMPLE_INCREMENT}")

                # Check if we have enough new samples to trigger training
                sample_increment = total_samples - last_total_samples
                if sample_increment < MIN_SAMPLE_INCREMENT:
                    print(f"Sample increment ({sample_increment}) is below threshold ({MIN_SAMPLE_INCREMENT}). Skipping training.")
                    context["ti"].xcom_push(key="training_skipped", value=True)
                    context["ti"].xcom_push(key="reason", value=f"Insufficient sample increment: {sample_increment} < {MIN_SAMPLE_INCREMENT}")
                    return

                print(f"Sample increment threshold met. Proceeding with training on all {total_samples} samples.")

                # Fetch ALL preprocessed data for training
                select_all_sql = """
                SELECT elevation, aspect, slope, horizontal_distance_to_hydrology,
                       vertical_distance_to_hydrology, horizontal_distance_to_roadways,
                       hillshade_9am, hillshade_noon, hillshade_3pm,
                       horizontal_distance_to_fire_points, wilderness_area,
                       soil_type, cover_type
                FROM covertype_data
                WHERE processing_status IN ('preprocessed', 'completed')
                ORDER BY id
                """

                cursor.execute(select_all_sql)
                rows = cursor.fetchall()

                if not rows:
                    raise ValueError("No training data found")

                # Convert to DataFrame
                df = pd.DataFrame(rows)
                print(f"Training on ALL {len(df)} rows from entire dataset")

                # Prepare features and target
                feature_columns = [
                    'elevation', 'aspect', 'slope', 'horizontal_distance_to_hydrology',
                    'vertical_distance_to_hydrology', 'horizontal_distance_to_roadways',
                    'hillshade_9am', 'hillshade_noon', 'hillshade_3pm',
                    'horizontal_distance_to_fire_points', 'wilderness_area', 'soil_type'
                ]

                X = df[feature_columns]
                y = df['cover_type']

                print(f"Features shape: {X.shape}")
                print(f"Target distribution: {y.value_counts().to_dict()}")

                # Check if we have enough samples for training
                if len(df) < 10:
                    raise ValueError(f"Insufficient data for training: only {len(df)} rows")

                # Use stratification only if we have multiple classes
                stratify = y if y.nunique() > 1 else None

                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y,
                    test_size=TEST_SIZE,
                    random_state=RANDOM_STATE,
                    stratify=stratify
                )

                print(f"Training set: {len(X_train)} samples")
                print(f"Test set: {len(X_test)} samples")

                # Train RandomForest model
                model = RandomForestClassifier(
                    n_estimators=150,
                    max_depth=None,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    class_weight='balanced'
                )

                model.fit(X_train, y_train)

                # Make predictions
                y_pred = model.predict(X_test)

                # Calculate metrics
                accuracy = accuracy_score(y_test, y_pred)
                f1_macro = f1_score(y_test, y_pred, average='macro')
                training_time = time.time() - start_time

                # ========== INTEGRACIÓN MLFLOW ==========
                
                # Configurar tracking URI
                mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
                
                # Crear/seleccionar experimento
                experiment_name = "covertype_classification"
                mlflow.set_experiment(experiment_name)
                
                # Iniciar run de MLflow
                with mlflow.start_run(run_name=f"batch_{current_batch_id}"):
                    
                    # Log de parámetros
                    mlflow.log_params({
                        "n_estimators": 150,
                        "max_depth": "None",
                        "random_state": RANDOM_STATE,
                        "test_size": TEST_SIZE,
                        "class_weight": "balanced",
                        "min_sample_increment": MIN_SAMPLE_INCREMENT,
                        "model_type": "RandomForestClassifier"
                    })
                    
                    # Log de métricas
                    mlflow.log_metrics({
                        "accuracy": float(accuracy),
                        "f1_macro": float(f1_macro),
                        "n_samples_train": int(len(X_train)),
                        "n_samples_test": int(len(X_test)),
                        "n_features": int(X.shape[1]),
                        "n_classes": int(y.nunique()),
                        "training_time_seconds": float(training_time)
                    })
                    
                    # Log del modelo
                    signature = mlflow.models.infer_signature(X_train, y_train)
                    mlflow.sklearn.log_model(
                        sk_model=model,
                        artifact_path="model",
                        registered_model_name="covertype_classifier",
                        signature=signature
                    )
                    
                    # Log de tags
                    mlflow.set_tags({
                        "batch_id": current_batch_id,
                        "model_type": "RandomForestClassifier",
                        "framework": "scikit-learn",
                        "dataset": "covertype",
                        "training_mode": "incremental",
                        "team": "grupo_3"
                    })
                    
                    # Obtener run_id para referencia
                    run_id = mlflow.active_run().info.run_id
                    print(f"✅ MLflow run_id: {run_id}")
                    
                    # Guardar en XCom
                    context["ti"].xcom_push(key="mlflow_run_id", value=run_id)
                
                # ========== FIN INTEGRACIÓN MLFLOW ==========

                # Prepare hyperparameters
                hyperparams = {
                    "n_estimators": 150,
                    "max_depth": None,
                    "random_state": RANDOM_STATE,
                    "test_size": TEST_SIZE,
                    "class_weight": "balanced"
                }

                # Prepare metrics
                metrics = {
                    "accuracy": float(accuracy),
                    "f1_macro": float(f1_macro),
                    "n_samples_train": int(len(X_train)),
                    "n_samples_test": int(len(X_test)),
                    "n_features": int(X.shape[1]),
                    "n_classes": int(y.nunique())
                }

                print("TRAINING METRICS:")
                print(json.dumps(metrics, indent=2))

                # Store metrics in database (use current_batch_id as trigger batch)
                insert_metrics_sql = """
                INSERT INTO model_metrics
                (batch_id, accuracy, f1_macro, n_samples_train, n_samples_test,
                 n_features, model_type, hyperparameters, training_time_seconds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_metrics_sql, (
                    current_batch_id,  # The batch that triggered this training
                    accuracy,
                    f1_macro,
                    len(X_train),
                    len(X_test),
                    X.shape[1],
                    "RandomForestClassifier",
                    json.dumps(hyperparams),
                    training_time
                ))

                # Update ALL preprocessed data status to completed
                update_complete_sql = """
                UPDATE covertype_data
                SET processing_status = 'completed'
                WHERE processing_status = 'preprocessed'
                """
                cursor.execute(update_complete_sql)
                updated_rows = cursor.rowcount

                print(f"Training completed using ALL available data (triggered by batch {current_batch_id})")
                print(f"Updated {updated_rows} rows to 'completed' status")
                print(f"Accuracy: {accuracy:.4f}, F1-macro: {f1_macro:.4f}")
                print(f"Training time: {training_time:.2f} seconds")
                print(f"Total samples used: {len(df)} ({len(X_train)} train + {len(X_test)} test)")

                # Store results in XCom
                context["ti"].xcom_push(key="final_batch_id", value=current_batch_id)
                context["ti"].xcom_push(key="accuracy", value=accuracy)
                context["ti"].xcom_push(key="f1_macro", value=f1_macro)
                context["ti"].xcom_push(key="total_samples_used", value=len(df))
                context["ti"].xcom_push(key="training_completed", value=True)

        except Exception as e:
            # Update status to failed if training fails
            try:
                with connection.cursor() as cursor:
                    update_failed_sql = """
                    UPDATE covertype_data
                    SET processing_status = 'failed'
                    WHERE processing_status = 'preprocessed'
                    """
                    cursor.execute(update_failed_sql)
            except:
                pass

            print(f"Training failed: {str(e)}")
            context["ti"].xcom_push(key="training_failed", value=True)
            context["ti"].xcom_push(key="error_message", value=str(e))
            raise

        finally:
            connection.close()

    collect = PythonOperator(
        task_id="collect_data",
        python_callable=collect_data,
    )
    preprocess = PythonOperator(
        task_id="preprocess_data",
        python_callable=preprocess_data,
    )
    train = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    collect >> preprocess >> train

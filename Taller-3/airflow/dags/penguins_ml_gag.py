"""
DAG de Airflow para Pipeline ML de Clasificación de Pingüinos
=============================================================
Este DAG implementa el pipeline completo desde la ingesta de datos
hasta el entrenamiento de modelos de Machine Learning.

Autor: Persona 2 - Taller 3
Fecha: 2024
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowException

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
import logging
import os
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, classification_report

# Configuración de logging
logger = logging.getLogger(__name__)

# Configuración de rutas
MODELS_DIR = Path("/opt/airflow/models")
MODELS_TF_DIR = Path("/opt/airflow/models_tf")
DATA_DIR = Path("/opt/airflow/data")

# Asegurar que los directorios existan
MODELS_DIR.mkdir(exist_ok=True)
MODELS_TF_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True, parents=True)

# Configuración por defecto del DAG
default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email': ['mlops@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Definición del DAG
dag = DAG(
    'penguins_ml_pipeline',
    default_args=default_args,
    description='Pipeline ML completo para clasificación de pingüinos',
    schedule_interval='@daily',  # Ejecutar diariamente
    catchup=False,
    tags=['ml', 'penguins', 'training'],
    max_active_runs=1,  # Solo una ejecución a la vez
)


def load_penguins():
    """
    Carga el dataset de pingüinos de Palmer.
    Intenta múltiples fuentes en orden de preferencia.
    
    Returns:
        pd.DataFrame: Dataset de pingüinos con columnas estándar
    """
    logger.info("Intentando cargar dataset de pingüinos...")
    
    # Método 1: Intentar cargar desde palmerpenguins
    try:
        from palmerpenguins import load_penguins as load_palmer_penguins
        df = load_palmer_penguins()
        logger.info("✓ Dataset cargado exitosamente desde palmerpenguins")
        return df
    except ImportError:
        logger.warning("palmerpenguins no está instalado, intentando método alternativo...")
    except Exception as e:
        logger.warning(f"Error cargando desde palmerpenguins: {e}")
    
    # Método 2: Intentar cargar desde seaborn
    try:
        import seaborn as sns
        df = sns.load_dataset('penguins')
        logger.info("✓ Dataset cargado exitosamente desde seaborn")
        return df
    except Exception as e:
        logger.warning(f"No se pudo cargar desde seaborn: {e}")
    
    # Método 3: Intentar cargar desde archivo CSV local
    try:
        csv_paths = [
            DATA_DIR / "raw" / "penguins.csv",
            Path("/opt/airflow/data/penguins.csv"),
            Path("./data/penguins.csv"),
            Path("penguins.csv")
        ]
        
        for csv_path in csv_paths:
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                logger.info(f"✓ Dataset cargado desde archivo local: {csv_path}")
                return df
    except Exception as e:
        logger.warning(f"No se pudo cargar desde archivo CSV: {e}")
    
    # Método 4: Descargar desde URL si está permitido
    try:
        url = "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/master/inst/extdata/penguins.csv"
        df = pd.read_csv(url)
        logger.info("✓ Dataset descargado desde GitHub")
        
        # Guardar para futuras ejecuciones
        save_path = DATA_DIR / "raw" / "penguins.csv"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(save_path, index=False)
        logger.info(f"Dataset guardado localmente en: {save_path}")
        
        return df
    except Exception as e:
        logger.warning(f"No se pudo descargar desde URL: {e}")
    
    # Método 5: Crear dataset sintético como último recurso
    logger.warning("Creando dataset sintético de pingüinos como último recurso...")
    
    np.random.seed(42)
    n_samples = 344  # Tamaño similar al dataset original
    
    # Generar datos sintéticos basados en distribuciones reales
    species_choices = ['Adelie', 'Chinstrap', 'Gentoo']
    species_probs = [0.44, 0.20, 0.36]  # Proporciones aproximadas reales
    
    species = np.random.choice(species_choices, size=n_samples, p=species_probs)
    
    # Generar features basadas en la especie (valores aproximados reales)
    data = []
    for s in species:
        if s == 'Adelie':
            bill_length = np.random.normal(38.8, 2.7)
            bill_depth = np.random.normal(18.3, 1.2)
            flipper_length = np.random.normal(190, 6.5)
            body_mass = np.random.normal(3700, 459)
            island = np.random.choice(['Torgersen', 'Biscoe', 'Dream'], p=[0.47, 0.44, 0.09])
        elif s == 'Chinstrap':
            bill_length = np.random.normal(48.8, 3.3)
            bill_depth = np.random.normal(18.4, 1.1)
            flipper_length = np.random.normal(196, 7.1)
            body_mass = np.random.normal(3733, 384)
            island = 'Dream'  # Chinstrap solo en Dream
        else:  # Gentoo
            bill_length = np.random.normal(47.5, 3.1)
            bill_depth = np.random.normal(15.0, 1.0)
            flipper_length = np.random.normal(217, 6.6)
            body_mass = np.random.normal(5076, 504)
            island = 'Biscoe'  # Gentoo solo en Biscoe
        
        sex = np.random.choice(['male', 'female', None], p=[0.49, 0.49, 0.02])
        year = np.random.choice([2007, 2008, 2009])
        
        data.append({
            'species': s,
            'island': island,
            'bill_length_mm': round(max(30, min(60, bill_length)), 1),
            'bill_depth_mm': round(max(13, min(22, bill_depth)), 1),
            'flipper_length_mm': round(max(170, min(235, flipper_length))),
            'body_mass_g': round(max(2700, min(6300, body_mass))),
            'sex': sex,
            'year': year
        })
    
    df = pd.DataFrame(data)
    
    # Introducir algunos valores nulos de manera realista
    null_indices = np.random.choice(df.index, size=int(0.02 * len(df)), replace=False)
    df.loc[null_indices, 'sex'] = None
    
    null_indices = np.random.choice(df.index, size=int(0.01 * len(df)), replace=False)
    for col in ['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']:
        null_subset = np.random.choice(null_indices, size=max(1, len(null_indices)//4), replace=False)
        df.loc[null_subset, col] = None
    
    logger.info(f"✓ Dataset sintético creado con {len(df)} registros")
    logger.info(f"Distribución de especies: {df['species'].value_counts().to_dict()}")
    
    return df


def clear_database(**context):
    """
    Tarea 1: Limpiar las tablas de la base de datos
    """
    logger.info("Iniciando limpieza de base de datos...")
    
    try:
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id='mysql_penguins', schema='penguins_db')
        
        # Limpiar tablas en orden (por foreign keys si las hubiera)
        queries = [
            "TRUNCATE TABLE penguins_clean;",
            "TRUNCATE TABLE penguins_raw;",
        ]
        
        for query in queries:
            logger.info(f"Ejecutando: {query}")
            mysql_hook.run(query)
        
        # Verificar que las tablas estén vacías
        for table in ['penguins_raw', 'penguins_clean']:
            count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {table}")[0]
            logger.info(f"Tabla {table} tiene {count} registros después de limpieza")
            if count > 0:
                raise AirflowException(f"Error: La tabla {table} no se limpió correctamente")
        
        logger.info("Base de datos limpiada exitosamente")
        return {'status': 'success', 'message': 'Database cleared successfully'}
        
    except Exception as e:
        logger.error(f"Error limpiando base de datos: {str(e)}")
        raise AirflowException(f"Error en clear_database: {str(e)}")


def load_raw_data(**context):
    """
    Tarea 2: Cargar datos crudos de pingüinos a la base de datos
    """
    logger.info("Iniciando carga de datos crudos...")
    
    try:
        # Cargar dataset de penguins (puede ser de palmerpenguins o un CSV local)
        try:
            # Intentar cargar desde archivo local primero
            raw_data_path = DATA_DIR / "raw" / "penguins.csv"
            if raw_data_path.exists():
                logger.info(f"Cargando datos desde {raw_data_path}")
                df = pd.read_csv(raw_data_path)
            else:
                # Si no existe, usar palmerpenguins
                logger.info("Cargando datos desde palmerpenguins")
                df = load_penguins()
        except Exception as e:
            logger.warning(f"No se pudo cargar archivo local, usando palmerpenguins: {e}")
            df = load_penguins()
        
        logger.info(f"Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas")
        logger.info(f"Columnas: {df.columns.tolist()}")
        
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id='mysql_penguins', schema='penguins_db')
        connection = mysql_hook.get_conn()
        cursor = connection.cursor()
        
        # Preparar datos para inserción
        insert_query = """
            INSERT INTO penguins_raw 
            (species, island, bill_length_mm, bill_depth_mm, 
             flipper_length_mm, body_mass_g, sex, year)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Insertar datos fila por fila
        rows_inserted = 0
        rows_with_nulls = 0
        
        for _, row in df.iterrows():
            try:
                # Convertir NaN a None para MySQL
                values = tuple(None if pd.isna(val) else val for val in [
                    row['species'],
                    row['island'],
                    row['bill_length_mm'],
                    row['bill_depth_mm'],
                    row['flipper_length_mm'],
                    row['body_mass_g'],
                    row['sex'] if 'sex' in row else None,
                    row.get('year', 2024)  # Valor por defecto si no existe
                ])
                
                # Contar filas con valores nulos
                if any(v is None for v in values):
                    rows_with_nulls += 1
                
                cursor.execute(insert_query, values)
                rows_inserted += 1
                
            except Exception as e:
                logger.error(f"Error insertando fila: {e}")
                logger.error(f"Valores problemáticos: {values}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"Datos crudos cargados: {rows_inserted} filas insertadas")
        logger.info(f"Filas con valores nulos: {rows_with_nulls}")
        
        # Verificar carga
        count = mysql_hook.get_first("SELECT COUNT(*) FROM penguins_raw")[0]
        logger.info(f"Total de registros en penguins_raw: {count}")
        
        # Guardar estadísticas en XCom para siguiente tarea
        context['task_instance'].xcom_push(
            key='raw_data_stats',
            value={
                'total_rows': rows_inserted,
                'rows_with_nulls': rows_with_nulls,
                'columns': df.columns.tolist()
            }
        )
        
        return {'status': 'success', 'rows_loaded': rows_inserted}
        
    except Exception as e:
        logger.error(f"Error cargando datos crudos: {str(e)}")
        raise AirflowException(f"Error en load_raw_data: {str(e)}")


def preprocess_data(**context):
    """
    Tarea 3: Preprocesar datos para entrenamiento
    """
    logger.info("Iniciando preprocesamiento de datos...")
    
    try:
        # Obtener estadísticas de la tarea anterior
        raw_stats = context['task_instance'].xcom_pull(
            task_ids='load_raw_data',
            key='raw_data_stats'
        )
        logger.info(f"Estadísticas de datos crudos: {raw_stats}")
        
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id='mysql_penguins', schema='penguins_db')
        
        # Leer datos crudos
        query = """
            SELECT id, species, island, bill_length_mm, bill_depth_mm,
                   flipper_length_mm, body_mass_g, sex, year
            FROM penguins_raw
        """
        df_raw = pd.read_sql(query, mysql_hook.get_conn())
        logger.info(f"Datos crudos leídos: {df_raw.shape}")
        
        # Eliminar filas con valores nulos en features importantes
        features_numericas = ['bill_length_mm', 'bill_depth_mm', 
                            'flipper_length_mm', 'body_mass_g']
        
        df_clean = df_raw.dropna(subset=features_numericas + ['species'])
        logger.info(f"Datos después de eliminar nulos: {df_clean.shape}")
        
        # Codificar variable objetivo (species)
        label_encoder = LabelEncoder()
        df_clean['species_encoded'] = label_encoder.fit_transform(df_clean['species'])
        
        # Guardar mapeo de clases
        species_mapping = {i: species for i, species in enumerate(label_encoder.classes_)}
        logger.info(f"Mapeo de especies: {species_mapping}")
        
        # Rellenar valores faltantes en columnas opcionales
        df_clean['sex'] = df_clean['sex'].fillna('Unknown')
        df_clean['year'] = df_clean['year'].fillna(df_clean['year'].median())
        
        # Agregar timestamp de procesamiento
        df_clean['processed_at'] = datetime.now()
        
        # Insertar datos limpios en la tabla penguins_clean
        connection = mysql_hook.get_conn()
        cursor = connection.cursor()
        
        insert_query = """
            INSERT INTO penguins_clean
            (species, island, bill_length_mm, bill_depth_mm,
             flipper_length_mm, body_mass_g, sex, year, 
             species_encoded, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rows_processed = 0
        for _, row in df_clean.iterrows():
            values = (
                row['species'],
                row['island'],
                float(row['bill_length_mm']),
                float(row['bill_depth_mm']),
                float(row['flipper_length_mm']),
                float(row['body_mass_g']),
                row['sex'],
                int(row['year']),
                int(row['species_encoded']),
                row['processed_at']
            )
            cursor.execute(insert_query, values)
            rows_processed += 1
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"Datos procesados: {rows_processed} filas insertadas en penguins_clean")
        
        # Guardar metadata para entrenamiento
        preprocessing_metadata = {
            'rows_processed': rows_processed,
            'features': features_numericas,
            'species_mapping': species_mapping,
            'label_encoder_classes': label_encoder.classes_.tolist()
        }
        
        # Guardar label encoder
        joblib.dump(label_encoder, MODELS_DIR / 'label_encoder.pkl')
        
        # Guardar metadata
        with open(MODELS_DIR / 'preprocessing_metadata.json', 'w') as f:
            json.dump(preprocessing_metadata, f, indent=2)
        
        # Push metadata a XCom
        context['task_instance'].xcom_push(
            key='preprocessing_metadata',
            value=preprocessing_metadata
        )
        
        return {'status': 'success', 'rows_processed': rows_processed}
        
    except Exception as e:
        logger.error(f"Error en preprocesamiento: {str(e)}")
        raise AirflowException(f"Error en preprocess_data: {str(e)}")


def train_models(**context):
    """
    Tarea 4: Entrenar modelos de ML usando datos preprocesados
    """
    logger.info("Iniciando entrenamiento de modelos...")
    
    try:
        # Obtener metadata del preprocesamiento
        prep_metadata = context['task_instance'].xcom_pull(
            task_ids='preprocess_data',
            key='preprocessing_metadata'
        )
        logger.info(f"Metadata de preprocesamiento: {prep_metadata}")
        
        # Conectar a MySQL y leer datos limpios
        mysql_hook = MySqlHook(mysql_conn_id='mysql_penguins', schema='penguins_db')
        
        query = """
            SELECT bill_length_mm, bill_depth_mm, flipper_length_mm, 
                   body_mass_g, species_encoded
            FROM penguins_clean
        """
        df = pd.read_sql(query, mysql_hook.get_conn())
        logger.info(f"Datos para entrenamiento: {df.shape}")
        
        # Preparar features y target
        X = df[prep_metadata['features']].values
        y = df['species_encoded'].values
        
        # División train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        logger.info(f"Train: {X_train.shape}, Test: {X_test.shape}")
        
        # Diccionario para almacenar resultados
        results = {}
        
        # 1. Entrenar KNN con escalado
        logger.info("Entrenando modelo KNN...")
        knn_pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', KNeighborsClassifier(n_neighbors=5))
        ])
        knn_pipeline.fit(X_train, y_train)
        
        # Evaluar KNN
        y_pred_knn = knn_pipeline.predict(X_test)
        knn_accuracy = accuracy_score(y_test, y_pred_knn)
        knn_f1 = f1_score(y_test, y_pred_knn, average='macro')
        
        results['knn'] = {
            'accuracy': float(knn_accuracy),
            'f1_score': float(knn_f1),
            'model_path': 'knn.pkl'
        }
        logger.info(f"KNN - Accuracy: {knn_accuracy:.4f}, F1: {knn_f1:.4f}")
        
        # Guardar modelo KNN
        joblib.dump(knn_pipeline, MODELS_DIR / 'knn.pkl')
        
        # 2. Entrenar Random Forest
        logger.info("Entrenando modelo Random Forest...")
        rf_pipeline = Pipeline([
            ('clf', RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ))
        ])
        rf_pipeline.fit(X_train, y_train)
        
        # Evaluar RF
        y_pred_rf = rf_pipeline.predict(X_test)
        rf_accuracy = accuracy_score(y_test, y_pred_rf)
        rf_f1 = f1_score(y_test, y_pred_rf, average='macro')
        
        results['rf'] = {
            'accuracy': float(rf_accuracy),
            'f1_score': float(rf_f1),
            'model_path': 'rf.pkl'
        }
        logger.info(f"RF - Accuracy: {rf_accuracy:.4f}, F1: {rf_f1:.4f}")
        
        # Guardar modelo RF
        joblib.dump(rf_pipeline, MODELS_DIR / 'rf.pkl')
        
        # 3. Entrenar SVM
        logger.info("Entrenando modelo SVM...")
        svm_pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', SVC(kernel='rbf', probability=True, random_state=42))
        ])
        svm_pipeline.fit(X_train, y_train)
        
        # Evaluar SVM
        y_pred_svm = svm_pipeline.predict(X_test)
        svm_accuracy = accuracy_score(y_test, y_pred_svm)
        svm_f1 = f1_score(y_test, y_pred_svm, average='macro')
        
        results['svm'] = {
            'accuracy': float(svm_accuracy),
            'f1_score': float(svm_f1),
            'model_path': 'svm.pkl'
        }
        logger.info(f"SVM - Accuracy: {svm_accuracy:.4f}, F1: {svm_f1:.4f}")
        
        # Guardar modelo SVM
        joblib.dump(svm_pipeline, MODELS_DIR / 'svm.pkl')
        
        # Guardar el mejor modelo como model.pkl para compatibilidad
        best_model_name = max(results.keys(), key=lambda k: results[k]['f1_score'])
        best_model = joblib.load(MODELS_DIR / results[best_model_name]['model_path'])
        joblib.dump(best_model, MODELS_DIR / 'model.pkl')
        logger.info(f"Mejor modelo ({best_model_name}) guardado como model.pkl")
        
        # Crear metadata completa
        model_metadata = {
            'training_date': datetime.now().isoformat(),
            'features': prep_metadata['features'],
            'classes': prep_metadata['label_encoder_classes'],
            'species_mapping': prep_metadata['species_mapping'],
            'models': results,
            'best_model': best_model_name,
            'dataset_info': {
                'total_samples': len(df),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }
        }
        
        # Guardar metadata
        with open(MODELS_DIR / 'model_metadata.json', 'w') as f:
            json.dump(model_metadata, f, indent=2)
        
        logger.info("Entrenamiento completado exitosamente")
        logger.info(f"Modelos guardados en: {MODELS_DIR}")
        
        # Verificar que los archivos existan
        for model_file in ['knn.pkl', 'rf.pkl', 'svm.pkl', 'model.pkl', 'model_metadata.json']:
            file_path = MODELS_DIR / model_file
            if file_path.exists():
                size = file_path.stat().st_size
                logger.info(f"✓ {model_file}: {size:,} bytes")
            else:
                logger.error(f"✗ {model_file} no encontrado!")
        
        return {
            'status': 'success',
            'models_trained': list(results.keys()),
            'best_model': best_model_name,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error en entrenamiento: {str(e)}")
        raise AirflowException(f"Error en train_models: {str(e)}")


def validate_pipeline(**context):
    """
    Tarea opcional: Validar que el pipeline se ejecutó correctamente
    """
    logger.info("Validando pipeline completo...")
    
    try:
        # Verificar que existan los modelos
        required_files = ['model.pkl', 'knn.pkl', 'rf.pkl', 'svm.pkl', 
                         'label_encoder.pkl', 'model_metadata.json']
        
        missing_files = []
        for file in required_files:
            if not (MODELS_DIR / file).exists():
                missing_files.append(file)
        
        if missing_files:
            raise AirflowException(f"Archivos faltantes: {missing_files}")
        
        # Verificar base de datos
        mysql_hook = MySqlHook(mysql_conn_id='mysql_penguins', schema='penguins_db')
        
        raw_count = mysql_hook.get_first("SELECT COUNT(*) FROM penguins_raw")[0]
        clean_count = mysql_hook.get_first("SELECT COUNT(*) FROM penguins_clean")[0]
        
        logger.info(f"Registros en penguins_raw: {raw_count}")
        logger.info(f"Registros en penguins_clean: {clean_count}")
        
        if clean_count == 0:
            raise AirflowException("No hay datos en penguins_clean")
        
        # Cargar y verificar metadata
        with open(MODELS_DIR / 'model_metadata.json', 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Modelos entrenados: {metadata['models'].keys()}")
        logger.info(f"Mejor modelo: {metadata['best_model']}")
        
        logger.info("✅ Pipeline validado exitosamente")
        
        return {
            'status': 'success',
            'validation': {
                'models_ok': True,
                'database_ok': True,
                'raw_records': raw_count,
                'clean_records': clean_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error en validación: {str(e)}")
        raise AirflowException(f"Error en validate_pipeline: {str(e)}")


# Definir tareas del DAG
with dag:
    # Tarea 1: Limpiar base de datos
    task_clear_db = PythonOperator(
        task_id='clear_database',
        python_callable=clear_database,
        doc_md="""
        ### Limpiar Base de Datos
        Trunca las tablas penguins_raw y penguins_clean
        para iniciar con datos frescos.
        """
    )
    
    # Tarea 2: Cargar datos crudos
    task_load_raw = PythonOperator(
        task_id='load_raw_data',
        python_callable=load_raw_data,
        doc_md="""
        ### Cargar Datos Crudos
        Carga el dataset de pingüinos desde archivo CSV o seaborn
        a la tabla penguins_raw sin ningún preprocesamiento.
        """
    )
    
    # Tarea 3: Preprocesar datos
    task_preprocess = PythonOperator(
        task_id='preprocess_data',
        python_callable=preprocess_data,
        doc_md="""
        ### Preprocesar Datos
        - Elimina valores nulos
        - Codifica variables categóricas
        - Guarda datos limpios en penguins_clean
        """
    )
    
    # Tarea 4: Entrenar modelos
    task_train = PythonOperator(
        task_id='train_models',
        python_callable=train_models,
        doc_md="""
        ### Entrenar Modelos ML
        Entrena múltiples modelos:
        - KNN
        - Random Forest
        - SVM
        Guarda los modelos en /opt/airflow/models/
        """
    )
    
    # Tarea 5: Validar pipeline
    task_validate = PythonOperator(
        task_id='validate_pipeline',
        python_callable=validate_pipeline,
        doc_md="""
        ### Validar Pipeline
        Verifica que todos los componentes del pipeline
        se ejecutaron correctamente.
        """
    )
    
    # Definir dependencias
    task_clear_db >> task_load_raw >> task_preprocess >> task_train >> task_validate


# Configuración adicional del DAG
dag.doc_md = """
# Pipeline ML de Clasificación de Pingüinos 🐧

Este DAG implementa un pipeline completo de Machine Learning que:

1. **Limpia la base de datos** - Elimina datos anteriores
2. **Carga datos crudos** - Ingesta el dataset de pingüinos
3. **Preprocesa datos** - Limpieza y transformación
4. **Entrena modelos** - KNN, Random Forest y SVM
5. **Valida el pipeline** - Verifica la ejecución correcta

## Configuración

### Conexión MySQL
- **Connection ID**: `mysql_penguins`
- **Host**: mysql
- **Schema**: penguins_db
- **Login**: Configurar en Airflow UI

### Estructura de Datos
- **penguins_raw**: Datos sin procesar
- **penguins_clean**: Datos procesados listos para ML

### Modelos Generados
- `model.pkl`: Mejor modelo
- `knn.pkl`: K-Nearest Neighbors
- `rf.pkl`: Random Forest
- `svm.pkl`: Support Vector Machine

## Monitoreo
- Logs detallados en cada tarea
- Métricas en model_metadata.json
- Validación automática al final
"""
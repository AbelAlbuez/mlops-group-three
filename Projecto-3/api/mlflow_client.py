"""
Cliente de MLflow para cargar modelos dinámicamente desde el Model Registry
"""
import mlflow
from mlflow.tracking import MlflowClient
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class MLflowModelClient:
    """Cliente para interactuar con MLflow y cargar modelos"""
    
    def __init__(
        self,
        tracking_uri: str = "http://mlflow:5000",
        model_name: str = "diabetic_risk_model"
    ):
        """
        Inicializa el cliente de MLflow
        
        Args:
            tracking_uri: URI del servidor MLflow
            model_name: Nombre del modelo registrado
        """
        self.tracking_uri = tracking_uri
        self.model_name = model_name
        self.client = None
        self.model = None
        self.model_info = {}
        
        # Configurar variables de entorno para S3 (MinIO)
        os.environ['MLFLOW_S3_ENDPOINT_URL'] = os.getenv('MLFLOW_S3_ENDPOINT_URL', 'http://minio:9000')
        os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', 'minio')
        os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'minio123')
        
        self._connect()
    
    def _connect(self):
        """Conecta con MLflow"""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            self.client = MlflowClient(tracking_uri=self.tracking_uri)
            
            # Verificar conexión haciendo una consulta simple
            try:
                self.client.search_experiments(max_results=1)
                logger.info(f"✓ Conectado a MLflow en {self.tracking_uri}")
            except Exception as conn_error:
                logger.warning(f"⚠️  MLflow responde pero puede tener problemas: {conn_error}")
                # No hacemos raise, dejamos que continue
                
        except Exception as e:
            logger.error(f"✗ Error conectando a MLflow: {e}")
            raise ConnectionError(f"No se pudo conectar a MLflow en {self.tracking_uri}")
    
    def get_production_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo en stage 'Production'
        
        Returns:
            Dict con información del modelo
        """
        try:
            # Buscar versiones del modelo en Production
            versions = self.client.search_model_versions(
                f"name='{self.model_name}'"
            )
            
            production_versions = [
                v for v in versions 
                if v.current_stage == "Production"
            ]
            
            if not production_versions:
                raise ValueError(
                    f"No se encontró ninguna versión del modelo '{self.model_name}' "
                    f"en stage 'Production'. Por favor ejecuta el DAG 3 de Airflow."
                )
            
            # Tomar la primera versión en Production
            prod_version = production_versions[0]
            
            # Obtener métricas del run
            run = self.client.get_run(prod_version.run_id)
            metrics = run.data.metrics
            
            info = {
                "model_name": self.model_name,
                "model_version": prod_version.version,
                "model_stage": prod_version.current_stage,
                "run_id": prod_version.run_id,
                "accuracy": metrics.get("accuracy"),
                "f1_score": metrics.get("f1"),
                "model_uri": f"models:/{self.model_name}/Production",
                "last_updated": prod_version.last_updated_timestamp
            }
            
            self.model_info = info
            logger.info(
                f"✓ Modelo encontrado: {self.model_name} "
                f"v{prod_version.version} (Production)"
            )
            
            return info
            
        except Exception as e:
            logger.error(f"✗ Error obteniendo info del modelo: {e}")
            raise
    
    def load_production_model(self):
        """
        Carga el modelo desde MLflow que está en stage 'Production'
        
        IMPORTANTE: Carga dinámicamente, sin hardcodear la versión
        """
        try:
            # Obtener info del modelo en Production
            info = self.get_production_model_info()
            
            # Cargar modelo usando el alias 'Production'
            # Esto carga automáticamente la versión correcta sin hardcodear
            model_uri = f"models:/{self.model_name}/Production"
            
            logger.info(f"Cargando modelo desde: {model_uri}")
            self.model = mlflow.sklearn.load_model(model_uri)
            
            logger.info(
                f"✓ Modelo cargado exitosamente: {self.model_name} "
                f"v{info['model_version']}"
            )
            
            return self.model
            
        except Exception as e:
            logger.error(f"✗ Error cargando modelo: {e}")
            raise
    
    def predict(self, features: Any) -> Any:
        """
        Realiza predicción usando el modelo cargado
        
        Args:
            features: Features para predicción (DataFrame o array)
            
        Returns:
            Predicción del modelo
        """
        if self.model is None:
            raise ValueError(
                "Modelo no cargado. Llama a load_production_model() primero."
            )
        
        try:
            prediction = self.model.predict(features)
            
            # Si el modelo tiene predict_proba
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features)
                return prediction, probabilities
            
            return prediction, None
            
        except Exception as e:
            logger.error(f"✗ Error en predicción: {e}")
            raise
    
    def reload_model(self):
        """
        Recarga el modelo desde MLflow
        
        Útil para actualizar el modelo sin reiniciar la API
        """
        logger.info("Recargando modelo desde MLflow...")
        self.model = None
        self.model_info = {}
        return self.load_production_model()
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a MLflow"""
        try:
            self.client.search_experiments(max_results=1)
            return True
        except:
            return False
    
    def is_model_loaded(self) -> bool:
        """Verifica si el modelo está cargado"""
        return self.model is not None

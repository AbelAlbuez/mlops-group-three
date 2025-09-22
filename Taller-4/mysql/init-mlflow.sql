-- ============================================
-- Script de inicialización MySQL para MLFlow
-- Base de datos para metadatos de MLFlow
-- ============================================

-- Crear base de datos para metadatos de MLflow
CREATE DATABASE IF NOT EXISTS mlflow_meta CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario específico para MLFlow si no existe
CREATE USER IF NOT EXISTS 'mlflow_user'@'%' IDENTIFIED BY 'mlflow_pass123';

-- Otorgar permisos al usuario mlflow_user sobre mlflow_meta
GRANT ALL PRIVILEGES ON mlflow_meta.* TO 'mlflow_user'@'%';

-- También otorgar permisos al usuario penguins para compatibilidad
GRANT ALL PRIVILEGES ON mlflow_meta.* TO 'penguins'@'%';

FLUSH PRIVILEGES;

-- Usar la base de datos mlflow_meta
USE mlflow_meta;

-- ============================================
-- Tablas adicionales para tracking personalizado
-- ============================================

-- Tabla para tracking de experimentos personalizados
CREATE TABLE IF NOT EXISTS experiment_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id VARCHAR(255) NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    description TEXT,
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_experiment_id (experiment_id),
    INDEX idx_experiment_name (experiment_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Metadatos adicionales de experimentos MLFlow';

-- Tabla para tracking de modelos en producción
CREATE TABLE IF NOT EXISTS production_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    stage VARCHAR(50) NOT NULL DEFAULT 'Staging',
    deployment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    performance_metrics JSON,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_model_name (model_name),
    INDEX idx_run_id (run_id),
    INDEX idx_stage (stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tracking de modelos en producción';

-- ============================================
-- Vista para estadísticas de experimentos
-- ============================================
CREATE OR REPLACE VIEW v_experiment_stats AS
SELECT 
    experiment_name,
    COUNT(*) as total_runs,
    MIN(created_at) as first_run,
    MAX(updated_at) as last_run
FROM experiment_metadata
GROUP BY experiment_name
ORDER BY total_runs DESC;

-- Mensaje de confirmación
SELECT 'Base de datos mlflow_meta inicializada correctamente con tablas adicionales' AS mensaje;
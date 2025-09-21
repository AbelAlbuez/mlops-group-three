-- Crear base de datos para metadatos de MLflow
CREATE DATABASE IF NOT EXISTS mlflow_meta CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Otorgar permisos al usuario penguins sobre mlflow_meta
GRANT ALL PRIVILEGES ON mlflow_meta.* TO 'penguins'@'%';
FLUSH PRIVILEGES;

-- Mensaje de confirmación
SELECT 'Base de datos mlflow_meta creada correctamente' AS mensaje;
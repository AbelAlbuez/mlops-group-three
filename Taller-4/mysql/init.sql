-- ============================================
-- Script de inicialización MySQL
-- Base de datos para Pipeline ML de Pingüinos
-- ============================================

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS penguins_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE penguins_db;

-- ============================================
-- Tabla 1: penguins_raw (Datos crudos)
-- ============================================
DROP TABLE IF EXISTS penguins_raw;

CREATE TABLE penguins_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    species VARCHAR(50),
    island VARCHAR(50),
    bill_length_mm FLOAT,
    bill_depth_mm FLOAT,
    flipper_length_mm FLOAT,
    body_mass_g FLOAT,
    sex VARCHAR(10),
    year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_species_raw (species),
    INDEX idx_created_raw (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Datos crudos de pingüinos sin procesar';

-- ============================================
-- Tabla 2: penguins_clean (Datos procesados)
-- ============================================
DROP TABLE IF EXISTS penguins_clean;

CREATE TABLE penguins_clean (
    id INT AUTO_INCREMENT PRIMARY KEY,
    species VARCHAR(50) NOT NULL,
    island VARCHAR(50),
    bill_length_mm FLOAT NOT NULL,
    bill_depth_mm FLOAT NOT NULL,
    flipper_length_mm FLOAT NOT NULL,
    body_mass_g FLOAT NOT NULL,
    sex VARCHAR(10),
    year INT,
    species_encoded INT NOT NULL COMMENT 'Especie codificada numéricamente',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL DEFAULT NULL COMMENT 'Fecha de procesamiento',
    INDEX idx_species_clean (species),
    INDEX idx_species_encoded (species_encoded),
    INDEX idx_processed (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Datos limpios y procesados para ML';

-- ============================================
-- Tabla 3: model_metrics (Métricas de modelos)
-- ============================================
DROP TABLE IF EXISTS model_metrics;

CREATE TABLE model_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    accuracy FLOAT NOT NULL,
    f1_score FLOAT NOT NULL,
    training_date TIMESTAMP NOT NULL,
    training_samples INT NOT NULL,
    test_samples INT NOT NULL,
    parameters JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model_name (model_name),
    INDEX idx_training_date (training_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Métricas históricas de modelos entrenados';

-- ============================================
-- Tabla 4: predictions_log (Log de predicciones)
-- ============================================
DROP TABLE IF EXISTS predictions_log;

CREATE TABLE predictions_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    bill_length_mm FLOAT NOT NULL,
    bill_depth_mm FLOAT NOT NULL,
    flipper_length_mm FLOAT NOT NULL,
    body_mass_g FLOAT NOT NULL,
    predicted_species VARCHAR(50) NOT NULL,
    prediction_confidence FLOAT,
    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prediction_date (prediction_date),
    INDEX idx_predicted_species (predicted_species)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Registro de predicciones realizadas';

-- ============================================
-- Vistas útiles
-- ============================================

-- Vista de estadísticas de datos
CREATE OR REPLACE VIEW v_data_stats AS
SELECT 
    'raw' as data_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT species) as unique_species,
    COUNT(DISTINCT island) as unique_islands,
    AVG(bill_length_mm) as avg_bill_length,
    AVG(flipper_length_mm) as avg_flipper_length,
    MIN(created_at) as first_record,
    MAX(created_at) as last_record
FROM penguins_raw
UNION ALL
SELECT 
    'clean' as data_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT species) as unique_species,
    COUNT(DISTINCT island) as unique_islands,
    AVG(bill_length_mm) as avg_bill_length,
    AVG(flipper_length_mm) as avg_flipper_length,
    MIN(created_at) as first_record,
    MAX(created_at) as last_record
FROM penguins_clean;

-- Vista de distribución de especies
CREATE OR REPLACE VIEW v_species_distribution AS
SELECT 
    species,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM penguins_clean), 2) as percentage
FROM penguins_clean
GROUP BY species
ORDER BY count DESC;

-- ============================================
-- Procedimientos almacenados
-- ============================================

-- Procedimiento para limpiar datos antiguos
DELIMITER //

CREATE PROCEDURE sp_cleanup_old_data(IN days_to_keep INT)
BEGIN
    DELETE FROM predictions_log 
    WHERE prediction_date < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);
    
    DELETE FROM model_metrics 
    WHERE created_at < DATE_SUB(NOW(), INTERVAL days_to_keep * 2 DAY);
END//

DELIMITER ;

-- ============================================
-- Permisos (ajustar según necesidades)
-- ============================================

-- Crear usuario específico para la aplicación si no existe
-- CREATE USER IF NOT EXISTS 'penguins_app'@'%' IDENTIFIED BY 'app_password_123';

-- Otorgar permisos necesarios
-- GRANT SELECT, INSERT, UPDATE, DELETE ON penguins_db.* TO 'penguins_app'@'%';
-- FLUSH PRIVILEGES;

-- ============================================
-- Datos de prueba (opcional, comentar en producción)
-- ============================================

-- INSERT INTO penguins_raw (species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year)
-- VALUES 
-- ('Adelie', 'Torgersen', 39.1, 18.7, 181, 3750, 'male', 2007),
-- ('Adelie', 'Torgersen', 39.5, 17.4, 186, 3800, 'female', 2007),
-- ('Adelie', 'Torgersen', 40.3, 18.0, 195, 3250, 'female', 2007);

-- ============================================
-- Mensaje final
-- ============================================
SELECT 'Base de datos penguins_db inicializada correctamente' AS mensaje;
-- Initialize database schema for covertype data storage
USE covertype_db;

-- Table to store raw string data from API (all varchar)
CREATE TABLE covertype_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    elevation VARCHAR(90),
    aspect VARCHAR(90),
    slope VARCHAR(90),
    horizontal_distance_to_hydrology VARCHAR(90),
    vertical_distance_to_hydrology VARCHAR(90),
    horizontal_distance_to_roadways VARCHAR(90),
    hillshade_9am VARCHAR(90),
    hillshade_noon VARCHAR(90),
    hillshade_3pm VARCHAR(90),
    horizontal_distance_to_fire_points VARCHAR(90),
    wilderness_area VARCHAR(90),
    soil_type VARCHAR(90),
    cover_type VARCHAR(90),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50) NOT NULL,
    processing_status ENUM('raw', 'processed', 'failed') DEFAULT 'raw',
    -- Hash of all data columns for duplicate detection
    data_hash VARCHAR(64) NOT NULL,
    INDEX idx_batch_id (batch_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (processing_status),
    -- Unique constraint on the hash to prevent duplicate data rows
    UNIQUE KEY unique_data_hash (data_hash)
);

-- Table to store processed covertype data (converted to proper types)
CREATE TABLE covertype_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    elevation INT NOT NULL,
    aspect INT NOT NULL,
    slope INT NOT NULL,
    horizontal_distance_to_hydrology INT NOT NULL,
    vertical_distance_to_hydrology INT NOT NULL,
    horizontal_distance_to_roadways INT NOT NULL,
    hillshade_9am INT NOT NULL,
    hillshade_noon INT NOT NULL,
    hillshade_3pm INT NOT NULL,
    horizontal_distance_to_fire_points INT NOT NULL,
    wilderness_area INT NOT NULL,
    soil_type INT NOT NULL,
    cover_type INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50) NOT NULL,
    raw_id INT,
    processing_status ENUM('preprocessed', 'training', 'completed', 'failed') DEFAULT 'preprocessed',
    INDEX idx_batch_id (batch_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (processing_status),
    FOREIGN KEY (raw_id) REFERENCES covertype_raw(id) ON DELETE CASCADE
);

-- Table to store model training metrics
CREATE TABLE model_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    accuracy DECIMAL(10, 8) NOT NULL,
    f1_macro DECIMAL(10, 8) NOT NULL,
    n_samples_train INT NOT NULL,
    n_samples_test INT NOT NULL,
    n_features INT NOT NULL,
    model_type VARCHAR(100) DEFAULT 'RandomForestClassifier',
    hyperparameters JSON,
    training_time_seconds DECIMAL(10, 3),
    model_data LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (batch_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (batch_id) REFERENCES covertype_data(batch_id) ON DELETE CASCADE
);

-- Table to store preprocessing logs/metadata
CREATE TABLE preprocessing_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    status ENUM('started', 'completed', 'failed') NOT NULL,
    message TEXT,
    execution_time_seconds DECIMAL(10, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (batch_id),
    INDEX idx_step_name (step_name),
    FOREIGN KEY (batch_id) REFERENCES covertype_data(batch_id) ON DELETE CASCADE
);

-- Table to store wilderness area string-to-numeric mappings
CREATE TABLE wilderness_area_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wilderness_area_text VARCHAR(255) NOT NULL UNIQUE,
    wilderness_area_numeric INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_text (wilderness_area_text),
    INDEX idx_numeric (wilderness_area_numeric)
);
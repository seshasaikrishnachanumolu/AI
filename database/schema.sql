-- MySQL schema for the AI Smart Waste Management system.
-- The Flask app can also create these tables itself (python seed.py).
-- Run:  mysql -u root -p < database/schema.sql
-- Then set DATABASE_URL=mysql+pymysql://root:password@localhost:3306/smart_waste in .env

CREATE DATABASE IF NOT EXISTS smart_waste CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_waste;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(10) NOT NULL DEFAULT 'user',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS locations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS smart_bins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  location_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS bin_compartments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bin_id INT NOT NULL,
  category VARCHAR(20) NOT NULL,
  max_capacity DOUBLE NOT NULL DEFAULT 20,
  current_load DOUBLE NOT NULL DEFAULT 0,
  UNIQUE KEY uq_bin_category (bin_id, category),
  FOREIGN KEY (bin_id) REFERENCES smart_bins(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS waste_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  image_filename VARCHAR(255) NOT NULL,
  category VARCHAR(20) NOT NULL,
  confidence DOUBLE NOT NULL,
  recommendation TEXT NOT NULL,
  is_recyclable TINYINT(1) NOT NULL DEFAULT 0,
  bin_id INT NULL,
  compartment_id INT NULL,
  estimated_volume DOUBLE NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_waste_user (user_id),
  INDEX idx_waste_category (category),
  INDEX idx_waste_created (created_at),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (bin_id) REFERENCES smart_bins(id),
  FOREIGN KEY (compartment_id) REFERENCES bin_compartments(id)
);

CREATE TABLE IF NOT EXISTS collection_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bin_id INT NOT NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'pending',
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  collected_at DATETIME NULL,
  collected_by INT NULL,
  volume_collected DOUBLE NULL,
  FOREIGN KEY (bin_id) REFERENCES smart_bins(id),
  FOREIGN KEY (collected_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bin_id INT NOT NULL,
  compartment_id INT NULL,
  message VARCHAR(255) NOT NULL,
  resolved TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME NULL,
  FOREIGN KEY (bin_id) REFERENCES smart_bins(id),
  FOREIGN KEY (compartment_id) REFERENCES bin_compartments(id)
);

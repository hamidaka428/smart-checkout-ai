-- Smart Checkout – database schema and demo catalogue (MariaDB / MySQL)
--
-- Usage (as a MariaDB admin):
--   sudo mariadb < schema.sql
--   sudo mariadb -e "CREATE USER 'smart_checkout'@'localhost' IDENTIFIED BY 'CHANGE_ME';
--                    GRANT SELECT, INSERT ON smart_checkout.* TO 'smart_checkout'@'localhost';
--                    FLUSH PRIVILEGES;"

CREATE DATABASE IF NOT EXISTS smart_checkout
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_checkout;

-- One row per product the AI model can recognise.
-- `barcode` is the class label returned by the classifier (ai/model/labels.txt).
CREATE TABLE IF NOT EXISTS products (
  barcode VARCHAR(50)   NOT NULL PRIMARY KEY,
  name    VARCHAR(100)  NOT NULL,
  price   DECIMAL(10,2) NOT NULL CHECK (price >= 0)
) ENGINE=InnoDB;

-- One row per completed checkout session.
CREATE TABLE IF NOT EXISTS orders (
  id           INT UNSIGNED  NOT NULL AUTO_INCREMENT PRIMARY KEY,
  total_amount DECIMAL(10,2) NOT NULL,   -- gross total, VAT included
  vat_amount   DECIMAL(10,2) NOT NULL,
  items_count  INT UNSIGNED  NOT NULL,
  created_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_orders_created_at (created_at)
) ENGINE=InnoDB;

-- Demo catalogue (prices in EUR, VAT included).
-- NOTE: RPI_JOYSTICK uses a placeholder name/price – adjust to your own data.
INSERT INTO products (barcode, name, price) VALUES
  ('RPI_BATTERY_9V',  '9V Battery',                 1.79),
  ('RPI_BREADBOARD',  'Breadboard',                 2.56),
  ('RPI_CABLE',       'Jumper Cable',               1.02),
  ('RPI_EXTENSION',   'GPIO Extension Board',       6.14),
  ('RPI_FLASHLIGHT',  'LED Flashlight',             5.11),
  ('RPI_JOYSTICK',    'Joystick Module',            2.30),
  ('RPI_KBOARD',      'Mechanical Keyboard',       38.35),
  ('RPI_MOTOR',       'DC Motor 5V',                1.79),
  ('RPI_MOUSE',       'Wireless Computer Mouse',    9.20),
  ('RPI_MULTIMETER',  'Digital Multimeter DT-830B', 7.67),
  ('RPI_PHONE',       'Smartphone',              1278.23),
  ('RPI_RASPBERRY',   'Raspberry Pi',              92.03),
  ('RPI_SCISSORS',    'Office Scissors',            1.79),
  ('RPI_SERVO',       'Micro Servo SG90',           3.07),
  ('RPI_STEPPER',     'Stepper Motor',              4.09)
ON DUPLICATE KEY UPDATE name = VALUES(name), price = VALUES(price);

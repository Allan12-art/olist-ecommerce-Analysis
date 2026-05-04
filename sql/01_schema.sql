-- ============================================================
-- 01_schema.sql
-- Load all Olist CSV files into DuckDB tables
-- Run via: python src/01_setup_db.py  (which executes this)
-- ============================================================

-- Orders
CREATE OR REPLACE TABLE orders AS
    SELECT * FROM read_csv_auto('data/olist_orders_dataset.csv');

-- Order Items
CREATE OR REPLACE TABLE order_items AS
    SELECT * FROM read_csv_auto('data/olist_order_items_dataset.csv');

-- Order Payments
CREATE OR REPLACE TABLE order_payments AS
    SELECT * FROM read_csv_auto('data/olist_order_payments_dataset.csv');

-- Order Reviews
CREATE OR REPLACE TABLE order_reviews AS
    SELECT * FROM read_csv_auto('data/olist_order_reviews_dataset.csv');

-- Customers
CREATE OR REPLACE TABLE customers AS
    SELECT * FROM read_csv_auto('data/olist_customers_dataset.csv');

-- Products
CREATE OR REPLACE TABLE products AS
    SELECT * FROM read_csv_auto('data/olist_products_dataset.csv');

-- Sellers
CREATE OR REPLACE TABLE sellers AS
    SELECT * FROM read_csv_auto('data/olist_sellers_dataset.csv');

-- Product Category Name Translation (Portuguese → English)
CREATE OR REPLACE TABLE category_translation AS
    SELECT * FROM read_csv_auto('data/product_category_name_translation.csv');

-- Geolocation
CREATE OR REPLACE TABLE geolocation AS
    SELECT * FROM read_csv_auto('data/olist_geolocation_dataset.csv');

-- Verify row counts
SELECT 'orders'           AS tbl, COUNT(*) AS rows FROM orders
UNION ALL
SELECT 'order_items',     COUNT(*) FROM order_items
UNION ALL
SELECT 'order_payments',  COUNT(*) FROM order_payments
UNION ALL
SELECT 'order_reviews',   COUNT(*) FROM order_reviews
UNION ALL
SELECT 'customers',       COUNT(*) FROM customers
UNION ALL
SELECT 'products',        COUNT(*) FROM products
UNION ALL
SELECT 'sellers',         COUNT(*) FROM sellers;

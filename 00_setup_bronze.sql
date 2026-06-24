-- =====================================================================
-- 00_setup_bronze.sql  (EJECUTAR UNA SOLA VEZ)
-- Crea la capa BRONZE en workspace.on a partir de workspace.workshop3.
-- Estas tablas son append-only y sirven como fuente STREAM() para el
-- Lakeflow Declarative Pipeline. Conservan los datos "sucios" tal cual
-- (mojibake en categorias, tipos en STRING) para demostrar la limpieza.
--
-- Warehouse sugerido: Serverless BI (Medium) -> 16cb45a2bec93679
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS workspace.`on`;

-- ---------- BRONZE: orders (linea de venta, transaccional) ----------
CREATE TABLE IF NOT EXISTS workspace.`on`.orders
AS SELECT * FROM workspace.workshop3.evg_orders;

-- ---------- BRONZE: customers (dimension cliente) ----------
CREATE TABLE IF NOT EXISTS workspace.`on`.customers
AS SELECT * FROM workspace.workshop3.evg_customers;

-- ---------- BRONZE: products (dimension producto, con mojibake) ----------
CREATE TABLE IF NOT EXISTS workspace.`on`.products
AS SELECT * FROM workspace.workshop3.evg_products;

-- Las tablas SILVER/GOLD las crea y administra el Declarative Pipeline:
--   workspace.on.orders_silver, customers_silver, products_silver,
--   workspace.on.products_quarantine, workspace.on.fact_orders
-- NO se crean aqui para evitar conflicto de propiedad con el pipeline.

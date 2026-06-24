-- =====================================================================
-- 20_pipeline.sql  -- LAKEFLOW DECLARATIVE PIPELINE (SQL)
-- Lee la capa BRONZE de workspace.on como STREAM y produce SILVER/GOLD:
--   * customers_silver   - tipos + encoding corregido + expectations
--   * products_silver     - validos, encoding corregido, precio DECIMAL
--   * products_quarantine - filas que violan reglas de calidad
--   * orders_silver       - tipos, timestamp parseado, encoding, expectations
--   * fact_orders         - join denormalizado (GOLD)
--
-- Correccion de mojibake:  decode(encode(col,'ISO-8859-1'),'UTF-8')
-- Configurar el pipeline con default catalog = workspace, schema = on.
-- =====================================================================

-- ---------------------------------------------------------------------
-- CUSTOMERS SILVER
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE customers_silver
(
  CONSTRAINT valid_customer_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_email       EXPECT (email IS NULL OR email LIKE '%@%')
)
COMMENT 'Clientes limpios: tipos casteados y texto con encoding corregido'
AS SELECT
  internal_customer_id                                            AS customer_id,
  lower(email)                                                    AS email,
  CASE WHEN first_name RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(first_name,'windows-1252'),'UTF-8') ELSE first_name END AS first_name,
  CASE WHEN last_name  RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(last_name,'windows-1252'),'UTF-8')  ELSE last_name  END AS last_name,
  phone,
  try_to_timestamp(registration_date)                            AS registration_date,
  CASE upper(gender) WHEN 'F' THEN 'F' WHEN 'FEMALE' THEN 'F'
                     WHEN 'M' THEN 'M' WHEN 'MALE' THEN 'M' ELSE 'U' END AS gender,
  registration_channel,
  CASE WHEN city  RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(city,'windows-1252'),'UTF-8')  ELSE city  END AS city,
  CASE WHEN state RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(state,'windows-1252'),'UTF-8') ELSE state END AS state,
  zip,
  preferred_store,
  preferred_channel,
  brand_name,
  member_Type                                                     AS member_type,
  try_cast(member_Points AS int)                                  AS member_points
FROM STREAM(workspace.`on`.customers);

-- ---------------------------------------------------------------------
-- PRODUCTS SILVER  (solo filas validas)
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE products_silver
(
  CONSTRAINT valid_item  EXPECT (item IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_price EXPECT (price IS NOT NULL)
)
COMMENT 'Productos limpios: precio DECIMAL y texto con encoding corregido'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS SELECT
  item,
  CASE WHEN title    RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(title,'windows-1252'),'UTF-8')    ELSE title    END AS title,
  CASE WHEN category RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(category,'windows-1252'),'UTF-8') ELSE category END AS category,
  try_cast(price AS decimal(12,2))                  AS price,
  try_cast(msrp  AS decimal(12,2))                  AS msrp,
  brand,
  CASE WHEN c_size  RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(c_size,'windows-1252'),'UTF-8')  ELSE c_size  END AS size,
  CASE WHEN c_color RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(c_color,'windows-1252'),'UTF-8') ELSE c_color END AS color,
  CASE WHEN c_fit   RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(c_fit,'windows-1252'),'UTF-8')   ELSE c_fit   END AS fit,
  CASE WHEN c_style RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(c_style,'windows-1252'),'UTF-8') ELSE c_style END AS style,
  c_sales_channel                                   AS sales_channel
FROM STREAM(workspace.`on`.products)
WHERE title IS NOT NULL AND title <> '' AND try_cast(price AS decimal(12,2)) IS NOT NULL;

-- ---------------------------------------------------------------------
-- PRODUCTS QUARANTINE  (filas que NO pasan las reglas de calidad)
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE products_quarantine
COMMENT 'Productos en cuarentena: titulo vacio o precio no numerico'
AS SELECT
  item,
  CASE WHEN title    RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(title,'windows-1252'),'UTF-8')    ELSE title    END AS title,
  CASE WHEN category RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(category,'windows-1252'),'UTF-8') ELSE category END AS category,
  price                                             AS price_raw,
  brand,
  current_timestamp()                               AS quarantined_at,
  CASE WHEN title IS NULL OR title = '' THEN 'titulo_vacio'
       WHEN try_cast(price AS decimal(12,2)) IS NULL THEN 'precio_invalido'
       ELSE 'otro' END                              AS quarantine_reason
FROM STREAM(workspace.`on`.products)
WHERE title IS NULL OR title = '' OR try_cast(price AS decimal(12,2)) IS NULL;

-- ---------------------------------------------------------------------
-- ORDERS SILVER  (transaccional limpio)
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE orders_silver
(
  CONSTRAINT positive_quantity EXPECT (quantity > 0)          ON VIOLATION DROP ROW,
  CONSTRAINT valid_amount      EXPECT (order_amount >= 0)     ON VIOLATION DROP ROW,
  CONSTRAINT valid_order_id    EXPECT (order_id IS NOT NULL)  ON VIOLATION DROP ROW
)
COMMENT 'Ordenes limpias: tipos casteados, timestamp parseado, errores de caracteres corregidos'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS SELECT
  `order`                                                       AS order_id,
  lower(email)                                                  AS email,
  try_to_timestamp(`timestamp`, 'MMM d yyyy  h:mma')            AS order_ts,
  item,
  -- LIMPIEZA ROBUSTA DE TEXTO (cadena completa):
  --   1) decodifica entidades HTML  2) arregla mojibake SOLO si lo detecta
  --   (windows-1252 cubre acentos Y signos: em-dash, comillas tipograficas)
  --   3) quita caracter de reemplazo U+FFFD  4) normaliza espacios
  trim(regexp_replace(replace(
    CASE WHEN replace(replace(replace(s_item_name,'&amp;','&'),'&aacute;','á'),'&eacute;','é') RLIKE 'Ã|Â|â€|â‚'
         THEN decode(encode(replace(replace(replace(s_item_name,'&amp;','&'),'&aacute;','á'),'&eacute;','é'),'windows-1252'),'UTF-8')
         ELSE replace(replace(replace(s_item_name,'&amp;','&'),'&aacute;','á'),'&eacute;','é') END,
    decode(unhex('EFBFBD'),'UTF-8'),''), '\\s+',' ')) AS item_name,
  try_cast(quantity AS int)                                    AS quantity,
  try_cast(price AS decimal(12,2))                             AS unit_price,
  try_cast(f_order_amount AS decimal(14,2))                    AS order_amount,
  try_cast(f_order_discount AS decimal(14,2))                  AS order_discount,
  s_market                                                     AS market,
  s_sales_channel                                              AS sales_channel,
  s_store_id                                                   AS store_id,
  CASE WHEN s_store_name RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_store_name,'windows-1252'),'UTF-8') ELSE s_store_name END AS store_name,
  s_brand_name                                                 AS brand_name,
  s_payment_method                                             AS payment_method,
  s_payment_brand                                              AS payment_brand,
  s_order_status                                               AS order_status,
  CASE WHEN s_item_category RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_item_category,'windows-1252'),'UTF-8') ELSE s_item_category END AS item_category,
  CASE WHEN s_item_size RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_item_size,'windows-1252'),'UTF-8') ELSE s_item_size END AS item_size,
  CASE WHEN s_item_color RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_item_color,'windows-1252'),'UTF-8') ELSE s_item_color END AS item_color,
  CASE WHEN s_item_fit RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_item_fit,'windows-1252'),'UTF-8') ELSE s_item_fit END AS item_fit,
  CASE WHEN s_item_style RLIKE 'Ã|Â|â€|â‚' THEN decode(encode(s_item_style,'windows-1252'),'UTF-8') ELSE s_item_style END AS item_style,
  -- CALIDAD DE DATOS: clasifica el error de caracteres detectado en s_item_name
  CASE
    WHEN s_item_name LIKE concat('%', decode(unhex('EFBFBD'),'UTF-8'), '%') THEN 'caracter_reemplazo'
    WHEN s_item_name RLIKE 'Ã|Â|â€|â‚'                                       THEN 'mojibake'
    WHEN s_item_name RLIKE '&[a-zA-Z]+;'                                    THEN 'entidad_html'
    WHEN s_item_name RLIKE '^ | $|  '                                       THEN 'espacios'
    ELSE 'limpio'
  END                                                          AS text_issue_type,
  (s_item_name RLIKE 'Ã|Â|â€|â‚|&[a-zA-Z]+;|  '
   OR s_item_name LIKE concat('%', decode(unhex('EFBFBD'),'UTF-8'), '%')
   OR s_item_category RLIKE 'Ã|Â|â€|â‚')                        AS had_text_issue
FROM STREAM(workspace.`on`.orders);

-- ---------------------------------------------------------------------
-- FACT_ORDERS (GOLD)  -- join stream(orders_silver) con dimensiones silver
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE fact_orders
COMMENT 'Tabla de hechos denormalizada: orden + cliente + producto'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS SELECT
  o.order_id,
  o.order_ts                              AS order_timestamp,
  o.order_status,
  o.sales_channel,
  o.market,
  o.brand_name,
  o.store_name,
  o.payment_method,
  o.payment_brand,
  o.item                                  AS item_id,
  o.item_name,
  o.quantity,
  o.unit_price,
  o.order_amount,
  o.order_discount,
  o.item_category,
  o.item_size,
  o.item_color,
  o.item_fit,
  o.item_style,
  o.text_issue_type,
  o.had_text_issue,
  c.customer_id,
  c.first_name                            AS customer_first_name,
  c.last_name                             AS customer_last_name,
  c.city                                  AS customer_city,
  c.state                                 AS customer_state,
  c.member_type,
  c.member_points,
  p.title                                 AS product_title,
  p.category                              AS product_category,
  p.brand                                 AS product_brand,
  p.msrp                                  AS product_msrp,
  p.size                                  AS product_size,
  p.color                                 AS product_color
FROM STREAM(orders_silver) o
LEFT JOIN customers_silver c ON o.email = c.email
LEFT JOIN products_silver  p ON o.item  = p.item;

-- ---------------------------------------------------------------------
-- PREDICCIONES_DEVOLUCION  -- tabla de INFERENCE para Lakehouse Monitoring
-- Simula un modelo que predice si una orden será devuelta.
--   label            = ground truth real (order_status = 'Devolución')
--   prediction_score = probabilidad simulada (correlacionada con label + ruido
--                      determinístico por hash, para accuracy realista no perfecta)
--   prediction_label = clase predicha (score > 0.5)
-- Inference profile: timestamp_col=order_ts, model_id_col=model_id,
--   prediction_col=prediction_label, label_col=label, classification.
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE predicciones_devolucion
COMMENT 'Inference log: predicción de devolución con ground truth real'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS SELECT
  order_id,
  order_ts,
  model_id,
  label,
  prediction_score,
  CASE WHEN prediction_score > 0.5 THEN 1 ELSE 0 END AS prediction_label
FROM (
  SELECT
    order_id,
    order_ts,
    'modelo_devolucion_v1' AS model_id,
    CASE WHEN order_status = 'Devolución' THEN 1 ELSE 0 END AS label,
    round(least(1.0, greatest(0.0,
      0.08
      + CASE WHEN order_status = 'Devolución' THEN 0.55 ELSE 0.0 END
      + (pmod(hash(order_id), 1000) / 1000.0 - 0.5) * 0.4
    )), 4) AS prediction_score
  FROM STREAM(orders_silver)
);

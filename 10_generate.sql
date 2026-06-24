-- =====================================================================
-- 10_generate.sql  -- GENERADOR (corre cada 15 min en warehouse BI Medium)
-- Inserta datos sinteticos RAW en la capa BRONZE de workspace.on.
--   * ~5,000,000 lineas de venta nuevas -> orders   (transaccional)
--   * ~10,000 clientes nuevos           -> customers (dimension)
--   * ~2,000 productos nuevos           -> products  (dimension)
-- Referencia clientes/productos reales para mantener consistencia y
-- conserva el mojibake en categorias (lo arregla el pipeline en silver).
--
-- VOLUMEN: cambia el numero dentro de range(...) en el bloque ORDERS
--          (5000000) si quieres mas/menos filas por corrida.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) ORDERS  (~5,000,000 lineas de venta nuevas)
-- ---------------------------------------------------------------------
INSERT INTO workspace.`on`.orders BY NAME
WITH dc AS (
  SELECT email, internal_customer_id,
         (row_number() OVER (ORDER BY internal_customer_id)) - 1 AS idx
  FROM workspace.`on`.customers
),
dp AS (
  SELECT item, title, category, c_size, c_color, c_fit, c_style,
         (row_number() OVER (ORDER BY item)) - 1 AS idx
  FROM workspace.`on`.products
),
base AS (
  SELECT
    r.id,
    cast(floor(rand() * (SELECT count(*) FROM dc)) AS bigint) AS ci,
    cast(floor(rand() * (SELECT count(*) FROM dp)) AS bigint) AS pi,
    CASE WHEN rand() < 0.10 THEN 'online' ELSE 'offline' END AS channel,
    cast(1 + floor(pow(rand(), 3) * 6) AS int) AS qty,
    array(89.0,99.0,129.0,159.0,189.0,229.0,259.0,299.0,349.0,399.0,449.0,549.0,649.0)[cast(rand()*13 AS int)] AS unit_price,
    array(0.0,0.0,0.0,0.10,0.15,0.20,0.30)[cast(rand()*7 AS int)] AS disc_f,
    array('BATH&BODYWORKS GALERIAS MONTERREY','BATH&BODYWORKS MITIKAH','BATH&BODYWORKS ANTEA QUERETARO',
          'BATH&BODYWORKS PARQUE DELTA','BATH&BODYWORKS ANDARES','BATH&BODYWORKS LA ISLA MERIDA',
          'BATH&BODYWORKS PLAZA SATELITE','BATH&BODYWORKS ANTARA','BATH&BODYWORKS SANTA FE',
          'BATH&BODYWORKS PUNTO VALLE','BATH&BODYWORKS MIDTOWN','BATH&BODYWORKS ARTZ PEDREGAL',
          'BATHANDBODYWORKS GALERIAS GUADALAJARA','BATH&BODYWORKS THE PARK','BATH&BODYWORKS SANTA FE')[cast(rand()*15 AS int)] AS store,
    CASE WHEN rand() < 0.75 THEN 'TARJETA' WHEN rand() < 0.90 THEN 'EFECTIVO' ELSE 'OTRA' END AS pay_method,
    array('Visa','Mastercard','American Express','PayPalRT','OXXO','KUESKI')[cast(rand()*6 AS int)] AS pay_brand,
    CASE WHEN rand() < 0.97 THEN 'Venta' ELSE 'Devolución' END AS status,
    array('iOS','Android','Desktop')[cast(rand()*3 AS int)] AS device,
    array('STANDARD','EXPRESS','PICKUP')[cast(rand()*3 AS int)] AS delivery,
    date_format(current_timestamp() - make_interval(0,0,0,0,0,cast(rand()*15 AS int),0), 'MMM d yyyy  h:mma') AS ts,
    date_format(current_timestamp(), 'yyyyMMddHHmmss') AS stamp,
    cast(rand()*6 AS int) AS errklass     -- clase de error de caracteres a inyectar
  FROM range(5000000) r            -- <<< VOLUMEN POR CORRIDA
)
SELECT
  concat('SYN-', b.stamp, '-', lpad(cast(b.id AS string), 9, '0'))      AS `order`,
  c.email                                                               AS email,
  b.ts                                                                  AS `timestamp`,
  p.item                                                                AS item,
  -- Inyeccion de DISTINTOS errores de caracteres (byte-fieles) para que
  -- el pipeline los detecte y corrija. Cada clase es 100% reversible
  -- salvo la 2 (caracter de reemplazo = perdida real de informacion).
  CASE b.errklass
    WHEN 0 THEN decode(encode(p.title,'UTF-8'),'windows-1252')           -- mojibake (acentos + signos)
    WHEN 1 THEN concat(replace(replace(replace(p.title,'&','&amp;'),'á','&aacute;'),'é','&eacute;'), ' &amp; Co.') -- entidades HTML
    WHEN 2 THEN concat('Arom', decode(unhex('EFBFBD'),'UTF-8'), 'tico ', p.title)  -- caracter de reemplazo U+FFFD
    WHEN 3 THEN concat('   ', upper(p.title), '   ')                      -- espacios extra + MAYUSCULAS
    ELSE p.title                                                         -- limpio
  END                                                                   AS s_item_name,
  cast(b.qty AS string)                                                 AS quantity,
  cast(b.unit_price AS string)                                          AS price,
  cast(b.unit_price AS string)                                          AS f_original_price,
  'MX'                                                                  AS s_market,
  'MXN'                                                                 AS s_original_currency,
  cast(NULL AS string)                                                  AS s_coupon,
  b.channel                                                             AS s_sales_channel,
  cast((1000 + b.ci) AS string)                                         AS s_store_id,
  concat('SYN-', b.stamp, '-', lpad(cast(b.id AS string), 9, '0'))      AS s_order_id,
  b.channel                                                             AS s_channel,
  '1'                                                                   AS s_brand_id,
  CASE WHEN b.channel = 'online' THEN 'BATH AND BODY WORKS' ELSE 'BBW' END AS s_brand_name,
  CASE WHEN b.channel = 'online' THEN 'ECOMMERCE BBW' ELSE b.store END   AS s_store_name,
  cast(NULL AS string)                                                  AS s_area,
  cast(NULL AS string)                                                  AS s_department,
  cast(round(b.unit_price * b.qty, 2) AS string)                        AS f_order_amount,
  cast(round(b.unit_price * b.qty * b.disc_f, 2) AS string)             AS f_order_discount,
  b.pay_method                                                          AS s_payment_method,
  CASE WHEN b.pay_method = 'TARJETA' THEN b.pay_brand ELSE cast(NULL AS string) END AS s_payment_brand,
  b.status                                                              AS s_order_status,
  CASE WHEN b.channel = 'online' THEN 'Completado' ELSE cast(NULL AS string) END AS s_order_status_ecomm,
  CASE WHEN b.channel = 'online' THEN 'WEB' ELSE cast(NULL AS string) END AS s_channel_ecomm,
  CASE WHEN b.channel = 'online' THEN b.device ELSE cast(NULL AS string) END AS s_device_type_ecomm,
  CASE WHEN b.channel = 'online' THEN b.delivery ELSE cast(NULL AS string) END AS s_delivery_channel_ecomm,
  cast(NULL AS string)                                                  AS t_delivery_date_ecomm,
  cast(NULL AS string)                                                  AS s_pickup_store_id_ecomm,
  cast(NULL AS string)                                                  AS t_pickup_date_ecomm,
  cast(b.qty AS string)                                                 AS i_order_total_items,
  cast(NULL AS string)                                                  AS s_order_coupon,
  p.category                                                            AS s_item_category,
  p.c_size                                                              AS s_item_size,
  p.c_color                                                             AS s_item_color,
  cast(round(b.unit_price * b.qty * b.disc_f, 2) AS string)             AS f_item_discount,
  p.c_fit                                                               AS s_item_fit,
  p.c_style                                                             AS s_item_style,
  date_format(current_timestamp(), 'yyyy-MM-dd HH:mm:ss')               AS t_modified_date,
  concat('SYN-', b.stamp, '-', lpad(cast(b.id AS string), 9, '0'))      AS REF_DWH_uniqueId,
  cast(b.id AS string)                                                  AS Sheetrow,
  'I'                                                                   AS IUD,
  date_format(current_timestamp(), 'yyyy-MM-dd HH:mm:ss')               AS RegisterDate,
  date_format(current_timestamp(), 'yyyy-MM-dd HH:mm:ss')               AS UpdateDate,
  cast(NULL AS string)                                                  AS _rescued_data
FROM base b
JOIN dc c ON b.ci = c.idx
JOIN dp p ON b.pi = p.idx;

-- ---------------------------------------------------------------------
-- 2) CUSTOMERS  (~10,000 clientes nuevos; clona reales y muta identidad)
-- ---------------------------------------------------------------------
INSERT INTO workspace.`on`.customers BY NAME
WITH r AS (
  SELECT id, cast(floor(rand() * (SELECT count(*) FROM workspace.`on`.customers)) AS bigint) AS pick
  FROM range(10000)
),
c AS (
  SELECT *, (row_number() OVER (ORDER BY internal_customer_id)) - 1 AS idx
  FROM workspace.`on`.customers
)
SELECT
  c.* EXCEPT (idx, internal_customer_id, email, RowNum),
  concat('SYN-', date_format(current_timestamp(),'yyyyMMddHHmmss'), '-', cast(r.id AS string)) AS internal_customer_id,
  concat('syn', date_format(current_timestamp(),'yyyyMMddHHmmss'), '_', cast(r.id AS string), '@example.com') AS email,
  cast(1000000 + r.id AS string) AS RowNum
FROM r JOIN c ON c.idx = r.pick;

-- ---------------------------------------------------------------------
-- 3) PRODUCTS  (~2,000 productos nuevos; clona reales y muta el SKU)
-- ---------------------------------------------------------------------
INSERT INTO workspace.`on`.products BY NAME
WITH r AS (
  SELECT id, cast(floor(rand() * (SELECT count(*) FROM workspace.`on`.products)) AS bigint) AS pick
  FROM range(2000)
),
p AS (
  SELECT *, (row_number() OVER (ORDER BY item)) - 1 AS idx
  FROM workspace.`on`.products
)
SELECT
  p.* EXCEPT (idx, item),
  concat('SYN-', date_format(current_timestamp(),'yyyyMMddHHmmss'), '-', cast(r.id AS string)) AS item
FROM r JOIN p ON p.idx = r.pick;

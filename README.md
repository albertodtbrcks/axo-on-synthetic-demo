# Datos sintéticos de ventas — `workspace.on` (Grupo Axo / Bath & Body Works MX)

Genera millones de registros de ventas sintéticos y los limpia con un
Lakeflow Declarative Pipeline (arquitectura medallion).

- **Workspace:** https://dbc-2123a53c-916e.cloud.databricks.com  (perfil CLI `axo-on`)
- **Warehouse:** Serverless BI (Medium) — `16cb45a2bec93679`
- **Esquema:** `workspace.on`
- **Modelo base copiado de:** `workspace.workshop3` (tablas `evg_*`, sin el prefijo `evg_`)

## Arquitectura

```
JOB SQL (cada 15 min, warehouse BI Medium)        LAKEFLOW DECLARATIVE PIPELINE (serverless)
  10_generate.sql                                   20_pipeline.sql
  ~5,000,000 orders + 10k customers + 2k products   STREAM(bronze) -> silver/gold
        |                                                 |
        v   capa BRONZE (raw, "sucia")                    v   capa SILVER / GOLD (limpia)
  workspace.on.orders        ---STREAM--->          workspace.on.orders_silver
  workspace.on.customers     ---STREAM--->          workspace.on.customers_silver
  workspace.on.products      ---STREAM--->          workspace.on.products_silver + products_quarantine
                                                    workspace.on.fact_orders   (gold, join denormalizado)
```

La limpieza incluye: casteo de tipos (STRING→INT/DECIMAL/TIMESTAMP), parseo de
timestamp, **corrección de mojibake** `decode(encode(col,'ISO-8859-1'),'UTF-8')`
(`JabÃ³n`→`Jabón`), y **expectations** de calidad (qty>0, amount>=0, quarantine
de productos inválidos).

## Archivos

| Archivo | Qué hace |
|---|---|
| `00_setup_bronze.sql` | (1 vez) crea y siembra la capa bronze desde `workshop3` |
| `10_generate.sql` | generador ~5M filas/corrida (cambia `range(5000000)` para ajustar volumen) |
| `20_pipeline.sql` | definición del Declarative Pipeline (silver/gold) |
| `30_load_test.sql` | query pesada para la prueba de auto-scaling del warehouse |

## Recursos desplegados

| Recurso | ID | Estado |
|---|---|---|
| Job `axo_on_synthetic_generator` (4 tareas encadenadas) | `279322249080343` | schedule **ACTIVO cada 15 min** (MX) |
| Declarative Pipeline `axo_on_silver_pipeline` | `02a27d28-6981-41d0-a522-06dd308cda90` | encadenado tras el generador |
| Dashboard **AXO Ventas** | `01f16ff532031c0085d628c6f6dd6222` | publicado |
| Dashboard **AXO Calidad de Datos** | `01f16ff532851c629c48e87025a4e78a` | publicado |
| Job de carga `axo_warehouse_load_test` | `821492600817208` | on-demand (24 tareas paralelas) |

**Cadena del job (cada 15 min):** `generar_bronze` (SQL, warehouse) → `limpiar_pipeline` (Declarative Pipeline) → `refrescar_ventas` + `refrescar_calidad` (refresco de ambos dashboards, en paralelo).

URLs dashboards:
- AXO Ventas: https://dbc-2123a53c-916e.cloud.databricks.com/dashboardsv3/01f16ff532031c0085d628c6f6dd6222/published?o=7474658890723778
- AXO Calidad de Datos: https://dbc-2123a53c-916e.cloud.databricks.com/dashboardsv3/01f16ff532851c629c48e87025a4e78a/published?o=7474658890723778

Archivos en el workspace: `/Users/alberto.ramirez@databricks.com/axo_on_synthetic/`

## Change Data Feed + Lakehouse Monitoring (3 tipos de profiling)

CDF habilitado con `delta.enableChangeDataFeed = true`:
- Bronze (`orders`, `customers`, `products`): vía `ALTER TABLE` (Delta normal).
- Silver/Gold (`orders_silver`, `products_silver`, `fact_orders`, `predicciones_devolucion`): vía `TBLPROPERTIES` en `CREATE STREAMING TABLE` (administradas por el pipeline).

Monitores (Lakehouse Monitoring) — tablas de métricas en `workspace.on.*_profile_metrics` / `*_drift_metrics`, refresh **horario** (`0 5 * * * ?`):

| Profile | Tabla monitoreada | Por qué | Dashboard de monitoreo |
|---|---|---|---|
| **Time Series** | `fact_orders` (col `order_timestamp`, slices por canal/pago) | calidad/distribuciones por ventana de tiempo | `01f16ff7cb4c1cca825db9f74481ba2a` |
| **Snapshot** | `products_silver` | estado completo de la dimensión en cada refresh | `01f16ff7cbbe1de5a2427ac02bb7302b` |
| **Inference** | `predicciones_devolucion` (clasificación; label real + prediction) | drift + calidad del modelo (accuracy/F1) | `01f16ff7cc3a1fbb9c535e116ce9792a` |

Tabla de inference `predicciones_devolucion`: simula modelo de devolución; `label` = ground truth real (`order_status='Devolución'`), `prediction_score` correlacionado + ruido determinístico por hash. Creada por el pipeline (se actualiza cada 15 min).

Operar monitores:
```bash
databricks quality-monitors run-refresh workspace.on.fact_orders --profile axo-on   # refrescar
databricks quality-monitors get workspace.on.fact_orders --profile axo-on            # estado + dashboard_id
```

## Errores de caracteres (generados e inyectados, y corregidos por el pipeline)
- **mojibake** — UTF-8 leído como Latin-1/Windows-1252 (`JabÃ³n`→`Jabón`, `EdiciÃ³n â€"`→`Edición —`). Fix: `decode(encode(col,'windows-1252'),'UTF-8')` **condicional** (solo si `RLIKE 'Ã|Â|â€|â‚'`, para no romper texto ya limpio).
- **entidad_html** — `&amp;`,`&aacute;` → `&`,`á` (replace).
- **caracter_reemplazo** — `�` (U+FFFD): **pérdida real e irrecuperable**; el pipeline lo detecta y elimina.
- **espacios** — espacios extra / mayúsculas → trim + colapso.
- windows-1252 (no ISO-8859-1) cubre además signos tipográficos: em-dash, comillas curvas.

## Cómo operarlo

```bash
P=--profile=axo-on

# Activar la generación cada 15 min:
databricks jobs update --job-id 279322249080343 \
  --json '{"job_id":279322249080343,"new_settings":{"schedule":{"quartz_cron_expression":"0 0/15 * * * ?","timezone_id":"America/Mexico_City","pause_status":"UNPAUSED"}}}' $P

# Refrescar el pipeline (limpia el nuevo bronze):
databricks pipelines start-update 02a27d28-6981-41d0-a522-06dd308cda90 $P

# Prueba de auto-scaling (levanta el 2do cluster Medium):
databricks jobs run-now --job-id 821492600817208 $P
# Monitorear: databricks warehouses get 16cb45a2bec93679 $P  -> campo num_clusters (1->2)
```

## Notas

- **Volumen:** 5M/corrida ≈ 480M filas/día en `orders`. Ajusta `range(5000000)` en
  `10_generate.sql` (validado: 5M corre en ~30s en el Medium).
- **Pipeline en vivo:** para limpiar automáticamente cada 15 min, agrega un *pipeline
  task* downstream en el job generador (genera → refresca silver en la misma corrida),
  o pon el pipeline en modo `continuous`.
- **Auto-scaling validado:** la prueba de carga llevó el warehouse de `num_clusters=1`
  a `num_clusters=2` (queries encolados → 2do cluster Medium).

# AXO App (Databricks App · Streamlit)

Dos vistas:
- **📊 Analytics** — embebe los dashboards Lakeview *AXO Ventas* y *AXO Calidad de Datos*.
- **🧾 Órdenes** — captura órdenes (individual o batch) → escribe a **Lakebase (Postgres)**.
  Una **Synced Table** replica a Unity Catalog (`workspace.on`) → flujo Apps→Lakebase→Lakehouse.

## Pendiente para desplegar (requiere datos del Lakebase)
1. **Adjuntar el recurso Lakebase** a la app `axo-app` (UI Apps → Edit → Resources → Database,
   seleccionar la instancia). Esto inyecta `PGHOST/PGPORT/PGDATABASE/PGUSER` + credenciales OAuth.
2. Poner el **nombre real de la instancia** en `app.yaml` → `LAKEBASE_INSTANCE`.
3. Conceder al **Service Principal de la app** permisos de `CONNECT`/`CREATE`/`INSERT` en el
   database/schema de Lakebase.
4. Desplegar:
   ```bash
   databricks sync ./app /Workspace/Users/<you>/axo-app-src --profile axo-on
   databricks apps deploy axo-app --source-code-path /Workspace/Users/<you>/axo-app-src --profile axo-on
   ```
5. Crear la **Synced Table** Lakebase→UC sobre la tabla `ordenes_app`
   (`databricks database create-synced-database-table ...`) apuntando a `workspace.on.ordenes_app`.

## Local (opcional)
```bash
pip install -r requirements.txt
export LAKEBASE_INSTANCE=... PGHOST=... PGDATABASE=...
streamlit run Home.py
```

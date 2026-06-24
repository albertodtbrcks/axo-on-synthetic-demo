import streamlit as st

st.set_page_config(page_title="AXO · Bath & Body Works MX", page_icon="🛍️", layout="wide")

st.title("🛍️ AXO · Demo Lakehouse")
st.caption("Bath & Body Works México — Apps → Lakebase → Lakehouse")

st.markdown(
    """
Esta app tiene dos vistas (menú lateral):

### 📊 Analytics
Dashboards de **Ventas** y **Calidad de datos** (AI/BI Lakeview) embebidos,
alimentados por el medallion en `workspace.on` (generador cada 15 min →
Declarative Pipeline → dashboards + monitoring).

### 🧾 Órdenes (Lakebase)
Captura de **órdenes de venta** (individual o batch) que escribe a
**Lakebase (Postgres)**. Una **Synced Table** replica las órdenes a Unity
Catalog (`workspace.on`), demostrando el flujo **Apps → Lakebase → Lakehouse**.
    """
)

c1, c2, c3 = st.columns(3)
c1.metric("Esquema Lakehouse", "workspace.on")
c2.metric("Cadencia generador", "cada 15 min")
c3.metric("Monitores de calidad", "3 (TS · Snapshot · Inference)")

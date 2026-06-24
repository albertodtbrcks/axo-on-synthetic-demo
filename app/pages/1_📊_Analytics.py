import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="AXO · Analytics", page_icon="📊", layout="wide")
st.title("📊 Analytics")

HOST = os.getenv("WORKSPACE_HOST", "https://dbc-2123a53c-916e.cloud.databricks.com")
ORG = os.getenv("WORKSPACE_ORG", "7474658890723778")
DASH = {
    "Ventas": os.getenv("DASHBOARD_VENTAS_ID", "01f16ff532031c0085d628c6f6dd6222"),
    "Calidad de datos": os.getenv("DASHBOARD_CALIDAD_ID", "01f16ff532851c629c48e87025a4e78a"),
}

tab = st.radio("Dashboard", list(DASH.keys()), horizontal=True, label_visibility="collapsed")
dash_id = DASH[tab]
# URL embebible del dashboard publicado de Lakeview
embed_url = f"{HOST}/embed/dashboardsv3/{dash_id}?o={ORG}"
published_url = f"{HOST}/dashboardsv3/{dash_id}/published?o={ORG}"

components.iframe(embed_url, height=900, scrolling=True)

st.caption(
    "Si el dashboard no carga embebido, agrega el dominio de la app a la "
    "*allowlist de embedding* del dashboard (Lakeview → Share → Embedding), "
    f"o ábrelo directo: [{tab}]({published_url})"
)

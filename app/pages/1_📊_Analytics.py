import os
import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

st.set_page_config(page_title="Demo AXO APP · Analytics", page_icon="📊", layout="wide")
st.title("📊 Analytics — Ventas & Calidad")
st.caption("Gráficas nativas (sin embedding) sobre workspace.on, vía el warehouse BI.")

WID = os.getenv("DATABRICKS_WAREHOUSE_ID", "16cb45a2bec93679")
HOST = "https://" + os.getenv("WORKSPACE_HOST", "https://dbc-2123a53c-916e.cloud.databricks.com").replace("https://", "")


def _user_token():
    try:
        return st.context.headers.get("x-forwarded-access-token")
    except Exception:
        return None


token = _user_token()
if not token:
    st.warning("No se encontró el token de usuario (X-Forwarded-Access-Token). Abre la app autenticado.")
    st.stop()


@st.cache_resource
def _client(tok):
    # auth_type="pat" fuerza usar SOLO el token del usuario (OBO) e ignora el
    # OAuth del Service Principal que Apps inyecta como env (DATABRICKS_CLIENT_ID/SECRET).
    return WorkspaceClient(host=HOST, token=tok, auth_type="pat")


@st.cache_data(ttl=300)
def q(tok, query):
    w = _client(tok)
    r = w.statement_execution.execute_statement(statement=query, warehouse_id=WID, wait_timeout="50s")
    if r.status and r.status.state != StatementState.SUCCEEDED:
        msg = r.status.error.message if r.status.error else r.status.state
        raise RuntimeError(msg)
    cols = [c.name for c in r.manifest.schema.columns]
    rows = (r.result.data_array if r.result else None) or []
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if len(df) and s.notna().all():
            df[c] = s
    return df


T = "workspace.`on`"
try:
    kpi = q(token, f"SELECT count(*) ordenes, sum(order_amount) ventas, sum(quantity) unidades, avg(order_amount) ticket FROM {T}.fact_orders").iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Venta total (MXN)", f"${float(kpi.ventas):,.0f}")
    c2.metric("Órdenes (líneas)", f"{int(kpi.ordenes):,}")
    c3.metric("Unidades", f"{int(kpi.unidades):,}")
    c4.metric("Ticket promedio", f"${float(kpi.ticket):,.0f}")

    st.subheader("Ventas por hora")
    hora = q(token, f"SELECT date_trunc('HOUR', order_timestamp) hora, sum(order_amount) ventas FROM {T}.fact_orders WHERE order_timestamp IS NOT NULL GROUP BY 1 ORDER BY 1")
    hora["hora"] = pd.to_datetime(hora["hora"])
    st.line_chart(hora, x="hora", y="ventas", color="#E9D8B6")

    a, b = st.columns(2)
    with a:
        st.subheader("Top tiendas")
        ti = q(token, f"SELECT store_name, sum(order_amount) ventas FROM {T}.fact_orders WHERE store_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 12")
        st.bar_chart(ti, x="store_name", y="ventas", horizontal=True, color="#E9D8B6")
    with b:
        st.subheader("Top categorías")
        ca = q(token, f"SELECT split(item_category,' > ')[0] categoria, sum(order_amount) ventas FROM {T}.fact_orders WHERE item_category IS NOT NULL AND item_category<>'' GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
        st.bar_chart(ca, x="categoria", y="ventas", horizontal=True, color="#E9D8B6")

    a2, b2 = st.columns(2)
    with a2:
        st.subheader("Online vs Offline")
        cn = q(token, f"SELECT sales_channel canal, count(*) ordenes FROM {T}.fact_orders GROUP BY 1")
        st.bar_chart(cn, x="canal", y="ordenes", color="#E9D8B6")
    with b2:
        st.subheader("Método de pago")
        pa = q(token, f"SELECT payment_method metodo, count(*) ordenes FROM {T}.fact_orders WHERE payment_method IS NOT NULL GROUP BY 1 ORDER BY 2 DESC")
        st.bar_chart(pa, x="metodo", y="ordenes", color="#E9D8B6")

    st.divider()
    st.subheader("🧹 Calidad de datos — errores de caracteres corregidos")
    pct = q(token, f"SELECT round(100*avg(case when had_text_issue then 1 else 0 end),1) pct, count(*) total FROM {T}.orders_silver").iloc[0]
    k1, k2 = st.columns(2)
    k1.metric("% líneas con error de texto", f"{float(pct.pct)}%")
    k2.metric("Total líneas procesadas", f"{int(pct.total):,}")
    cal = q(token, f"SELECT text_issue_type, count(*) filas FROM {T}.orders_silver GROUP BY 1 ORDER BY 2 DESC")
    st.bar_chart(cal, x="text_issue_type", y="filas", color="#E9D8B6")

except Exception as e:
    st.error(f"Error consultando el warehouse: {type(e).__name__}: {e}")
    st.info("Si es permisos/scope: reabre la app y aprueba la autorización de SQL (on-behalf-of-user).")
    with st.expander("Debug"):
        st.write({"token_present": bool(token), "token_len": len(token or ""), "warehouse": WID, "host": HOST})

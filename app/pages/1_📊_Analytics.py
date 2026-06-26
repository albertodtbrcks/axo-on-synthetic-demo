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
CREAM = "#E9D8B6"

# ---- Datos de muestra (fallback si la query en vivo falla por scope/permiso) ----
SAMPLES = {
    "kpi": pd.DataFrame([{"ordenes": 426128237, "ventas": 270948392237.32, "unidades": 494125560, "ticket": 635.84}]),
    "hora": pd.DataFrame({
        "hora": pd.to_datetime(["2026-06-25 18:00", "2026-06-25 20:00", "2026-06-25 22:00",
                                 "2026-06-26 00:00", "2026-06-26 02:00", "2026-06-26 04:00"]),
        "ventas": [1.21e9, 1.55e9, 1.38e9, 0.92e9, 1.07e9, 1.44e9],
    }),
    "tiendas": pd.DataFrame({
        "store_name": ["BATH&BODYWORKS SANTA FE", "ECOMMERCE BBW", "BATH&BODYWORKS MITIKAH",
                        "BATH&BODYWORKS ANDARES", "BATH&BODYWORKS PARQUE DELTA", "BATH&BODYWORKS ANTARA"],
        "ventas": [1.18e9, 1.01e9, 0.59e9, 0.57e9, 0.55e9, 0.53e9],
    }),
    "categorias": pd.DataFrame({
        "categoria": ["Hogar", "Jabones", "Cuidado Corporal", "Regalos", "Hombres"],
        "ventas": [9.8e10, 7.1e10, 6.4e10, 1.9e10, 1.1e10],
    }),
    "canal": pd.DataFrame({"canal": ["offline", "online"], "ordenes": [383000000, 43000000]}),
    "pago": pd.DataFrame({"metodo": ["TARJETA", "EFECTIVO", "OTRA"], "ordenes": [319000000, 94000000, 13000000]}),
    "calidad_pct": pd.DataFrame([{"pct": 29.5, "total": 425162394}]),
    "calidad": pd.DataFrame({
        "text_issue_type": ["limpio", "espacios", "caracter_reemplazo", "entidad_html", "mojibake"],
        "filas": [299500000, 50300000, 47600000, 47300000, 760000],
    }),
}

st.session_state.setdefault("_sample", False)


def _token():
    try:
        return st.context.headers.get("x-forwarded-access-token")
    except Exception:
        return None


@st.cache_resource
def _client(tok):
    # auth_type="pat" fuerza usar solo el token OBO (ignora el OAuth del SP que Apps inyecta).
    return WorkspaceClient(host=HOST, token=tok, auth_type="pat")


@st.cache_data(ttl=300, show_spinner=False)
def _live(tok, query):
    w = _client(tok)
    r = w.statement_execution.execute_statement(statement=query, warehouse_id=WID, wait_timeout="50s")
    if r.status and r.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(r.status.error.message if r.status.error else str(r.status.state))
    cols = [c.name for c in r.manifest.schema.columns]
    df = pd.DataFrame((r.result.data_array if r.result else None) or [], columns=cols)
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if len(df) and s.notna().all():
            df[c] = s
    return df


def q(name, query):
    tok = _token()
    if tok:
        try:
            return _live(tok, query)
        except Exception:
            st.session_state["_sample"] = True
    else:
        st.session_state["_sample"] = True
    return SAMPLES[name].copy()


T = "workspace.`on`"
kpi = q("kpi", f"SELECT count(*) ordenes, sum(order_amount) ventas, sum(quantity) unidades, avg(order_amount) ticket FROM {T}.fact_orders").iloc[0]
hora = q("hora", f"SELECT date_trunc('HOUR', order_timestamp) hora, sum(order_amount) ventas FROM {T}.fact_orders WHERE order_timestamp IS NOT NULL GROUP BY 1 ORDER BY 1")
ti = q("tiendas", f"SELECT store_name, sum(order_amount) ventas FROM {T}.fact_orders WHERE store_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 12")
ca = q("categorias", f"SELECT split(item_category,' > ')[0] categoria, sum(order_amount) ventas FROM {T}.fact_orders WHERE item_category IS NOT NULL AND item_category<>'' GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
cn = q("canal", f"SELECT sales_channel canal, count(*) ordenes FROM {T}.fact_orders GROUP BY 1")
pa = q("pago", f"SELECT payment_method metodo, count(*) ordenes FROM {T}.fact_orders WHERE payment_method IS NOT NULL GROUP BY 1 ORDER BY 2 DESC")
pct = q("calidad_pct", f"SELECT round(100*avg(case when had_text_issue then 1 else 0 end),1) pct, count(*) total FROM {T}.orders_silver").iloc[0]
cal = q("calidad", f"SELECT text_issue_type, count(*) filas FROM {T}.orders_silver GROUP BY 1 ORDER BY 2 DESC")

if st.session_state["_sample"]:
    st.warning("⚠️ Mostrando **datos de muestra**. Para datos en vivo, reabre la app y **aprueba la autorización de SQL** "
               "(on-behalf-of-user) — falta el scope `sql` en tu token.")

try:
    hora["hora"] = pd.to_datetime(hora["hora"])
except Exception:
    pass

c1, c2, c3, c4 = st.columns(4)
c1.metric("Venta total (MXN)", f"${float(kpi.ventas):,.0f}")
c2.metric("Órdenes (líneas)", f"{int(kpi.ordenes):,}")
c3.metric("Unidades", f"{int(kpi.unidades):,}")
c4.metric("Ticket promedio", f"${float(kpi.ticket):,.0f}")

st.subheader("Ventas por hora")
st.line_chart(hora, x="hora", y="ventas", color=CREAM)

a, b = st.columns(2)
with a:
    st.subheader("Top tiendas")
    st.bar_chart(ti, x="store_name", y="ventas", horizontal=True, color=CREAM)
with b:
    st.subheader("Top categorías")
    st.bar_chart(ca, x="categoria", y="ventas", horizontal=True, color=CREAM)

a2, b2 = st.columns(2)
with a2:
    st.subheader("Online vs Offline")
    st.bar_chart(cn, x="canal", y="ordenes", color=CREAM)
with b2:
    st.subheader("Método de pago")
    st.bar_chart(pa, x="metodo", y="ordenes", color=CREAM)

st.divider()
st.subheader("🧹 Calidad de datos — errores de caracteres corregidos")
k1, k2 = st.columns(2)
k1.metric("% líneas con error de texto", f"{float(pct.pct)}%")
k2.metric("Total líneas procesadas", f"{int(pct.total):,}")
st.bar_chart(cal, x="text_issue_type", y="filas", color=CREAM)

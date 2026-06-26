import streamlit as st

st.set_page_config(page_title="Demo AXO APP", page_icon="🔷", layout="wide")

# Logo AXO (marca de diamantes apilados) recreada como SVG, color crema sobre taupe.
AXO_LOGO = """
<div style="display:flex;align-items:center;gap:22px;justify-content:center;margin:8px 0 4px 0;">
  <svg width="86" height="138" viewBox="0 0 120 190" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M60 8 L108 95 L60 120 L12 95 Z" stroke="#E9D8B6" stroke-width="11" stroke-linejoin="round"/>
    <path d="M60 120 L96 150 L60 182 L24 150 Z" stroke="#E9D8B6" stroke-width="11" stroke-linejoin="round"/>
  </svg>
  <span style="font-size:64px;letter-spacing:14px;color:#E9D8B6;font-weight:300;">AXO</span>
</div>
"""

st.markdown(AXO_LOGO, unsafe_allow_html=True)
st.markdown(
    "<h2 style='text-align:center;color:#F3EEE2;font-weight:300;letter-spacing:6px;margin-top:0;'>DEMO AXO APP</h2>"
    "<p style='text-align:center;color:#CFC8B6;letter-spacing:2px;margin-top:-6px;'>Grupo Axo · Lakehouse Demo</p>",
    unsafe_allow_html=True,
)

st.markdown("<hr style='border-color:#5E5A4E;'>", unsafe_allow_html=True)

st.markdown(
    """
<div style="max-width:820px;margin:0 auto;color:#E9E3D4;font-size:16px;line-height:1.7;">
<b style="color:#E9D8B6;">📊 Analytics</b> — Ventas y calidad de datos sobre <code>workspace.on</code>,
con gráficas nativas (generador cada 15&nbsp;min → pipeline declarativo → monitoring).
<br><br>
<b style="color:#E9D8B6;">🧾 Órdenes</b> — Captura de órdenes de venta (individual o batch) que escribe a
<b>Lakebase&nbsp;(Postgres)</b> y se integra al Lakehouse: <i>Apps → Lakebase → Lakehouse</i>.
</div>
""",
    unsafe_allow_html=True,
)

st.write("")
c1, c2, c3 = st.columns(3)
c1.metric("Esquema Lakehouse", "workspace.on")
c2.metric("Cadencia generador", "cada 15 min")
c3.metric("Monitores de calidad", "3 · TS · Snapshot · Inference")

st.caption("Usa el menú lateral para navegar entre vistas.")

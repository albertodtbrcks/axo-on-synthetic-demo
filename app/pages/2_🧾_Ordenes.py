import datetime as dt
import random
import uuid
import pandas as pd
import streamlit as st

import lakebase

st.set_page_config(page_title="AXO · Órdenes", page_icon="🧾", layout="wide")
st.title("🧾 Órdenes → Lakebase → Lakehouse")
st.caption("Captura órdenes que se escriben en Lakebase (Postgres) y se sincronizan a Unity Catalog.")

TIENDAS = ["BATH&BODYWORKS SANTA FE", "BATH&BODYWORKS MITIKAH", "BATH&BODYWORKS ANDARES",
           "BATH&BODYWORKS PARQUE DELTA", "ECOMMERCE BBW"]
CATEGORIAS = ["Hogar > Velas > Velas Grandes", "Jabones > Jabón de Manos > Espumosos",
              "Cuidado Corporal > Cremas > Crema Corporal", "Cuidado Corporal > Fragancias > Fragancias Corporales"]
PAGOS = ["TARJETA", "EFECTIVO", "OTRA"]


def _nuevo_order_id():
    return "APP-" + dt.datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]


# ---- asegurar tabla ----
with st.sidebar:
    st.subheader("Lakebase")
    if st.button("Crear/verificar tabla de órdenes"):
        try:
            lakebase.ensure_orders_table()
            st.success("Tabla lista en Lakebase ✅")
        except Exception as e:
            st.error(f"Error: {e}")

modo = st.radio("Modo de carga", ["Individual", "Batch (real-time simulado)"], horizontal=True)

if modo == "Individual":
    with st.form("orden"):
        c1, c2, c3 = st.columns(3)
        email = c1.text_input("Email cliente", "cliente@example.com")
        tienda = c2.selectbox("Tienda", TIENDAS)
        canal = c3.selectbox("Canal", ["offline", "online"])
        c4, c5, c6 = st.columns(3)
        item_name = c4.text_input("Producto", "Vela Grande Aroma Vainilla")
        categoria = c5.selectbox("Categoría", CATEGORIAS)
        pago = c6.selectbox("Método de pago", PAGOS)
        c7, c8 = st.columns(2)
        qty = c7.number_input("Cantidad", 1, 50, 1)
        precio = c8.number_input("Precio unitario (MXN)", 1.0, 9999.0, 299.0)
        enviar = st.form_submit_button("Registrar orden")
    if enviar:
        oid = _nuevo_order_id()
        row = dict(order_id=oid, email=email, store_name=tienda, sales_channel=canal,
                   item=oid, item_name=item_name, item_category=categoria, quantity=int(qty),
                   unit_price=float(precio), order_amount=round(float(precio) * qty, 2),
                   payment_method=pago, order_status="Venta", source="app")
        try:
            lakebase.insert_orders([row])
            st.success(f"Orden {oid} escrita en Lakebase ✅")
        except Exception as e:
            st.error(f"Error al escribir: {e}")

else:
    n = st.slider("¿Cuántas órdenes generar?", 10, 5000, 500, step=10)
    if st.button("Generar batch y escribir a Lakebase"):
        rows = []
        for _ in range(n):
            qty = random.randint(1, 5)
            precio = random.choice([89, 99, 159, 229, 299, 399, 549, 649])
            canal = "online" if random.random() < 0.1 else "offline"
            oid = _nuevo_order_id()
            rows.append(dict(order_id=oid, email=f"user{random.randint(1,99999)}@example.com",
                             store_name="ECOMMERCE BBW" if canal == "online" else random.choice(TIENDAS),
                             sales_channel=canal, item=oid, item_name=random.choice(["Vela Grande", "Jabón Espumoso", "Crema Corporal", "Gel de Ducha"]),
                             item_category=random.choice(CATEGORIAS), quantity=qty, unit_price=float(precio),
                             order_amount=round(precio * qty, 2), payment_method=random.choice(PAGOS),
                             order_status="Venta", source="app-batch"))
        try:
            lakebase.insert_orders(rows)
            st.success(f"{n} órdenes escritas en Lakebase ✅ (se sincronizarán a workspace.on vía Synced Table)")
        except Exception as e:
            st.error(f"Error al escribir batch: {e}")

st.divider()
st.subheader("Órdenes recientes en Lakebase")
try:
    cols, data = lakebase.recent_orders(50)
    st.dataframe(pd.DataFrame(data, columns=cols), use_container_width=True)
except Exception as e:
    st.info(f"Aún no hay conexión/tabla de Lakebase configurada. ({e})")

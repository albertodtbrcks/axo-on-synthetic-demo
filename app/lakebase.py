"""Helper de conexión a Lakebase (Postgres) desde una Databricks App.

Patrón nativo: la App tiene un Service Principal; generamos un token OAuth de
base de datos con el SDK y lo usamos como password de Postgres. El host/puerto/
database/usuario vienen de las env vars que inyecta el recurso Lakebase
(PGHOST, PGPORT, PGDATABASE, PGUSER) o de app.yaml.
"""
import os
import psycopg
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()


def _instance_name() -> str:
    return os.environ["LAKEBASE_INSTANCE"]


def get_connection():
    """Devuelve una conexión psycopg a Lakebase usando token OAuth fresco."""
    instance = _instance_name()
    inst = _w.database.get_database_instance(name=instance)
    host = os.getenv("PGHOST") or inst.read_write_dns
    port = int(os.getenv("PGPORT", "5432"))
    database = os.getenv("PGDATABASE", "databricks_postgres")
    user = os.getenv("PGUSER") or _w.current_user.me().user_name

    # token OAuth de corta vida que funciona como password de Postgres
    cred = _w.database.generate_database_credential(
        request_id=os.urandom(8).hex(), instance_names=[instance]
    )
    return psycopg.connect(
        host=host, port=port, dbname=database, user=user,
        password=cred.token, sslmode="require", autocommit=True,
    )


def ensure_orders_table():
    """Crea la tabla de órdenes en Lakebase si no existe."""
    schema = os.getenv("ORDERS_SCHEMA", "public")
    table = os.getenv("ORDERS_TABLE", "ordenes_app")
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {schema}.{table} (
        order_id        TEXT PRIMARY KEY,
        order_ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
        email           TEXT,
        store_name      TEXT,
        sales_channel   TEXT,
        item            TEXT,
        item_name       TEXT,
        item_category   TEXT,
        quantity        INT,
        unit_price      NUMERIC(12,2),
        order_amount    NUMERIC(14,2),
        payment_method  TEXT,
        order_status    TEXT,
        source          TEXT DEFAULT 'app'
    );
    """
    with get_connection() as conn:
        conn.execute(ddl)


def insert_orders(rows: list[dict]):
    """Inserta una lista de órdenes (batch o single) en Lakebase."""
    schema = os.getenv("ORDERS_SCHEMA", "public")
    table = os.getenv("ORDERS_TABLE", "ordenes_app")
    cols = ["order_id", "email", "store_name", "sales_channel", "item", "item_name",
            "item_category", "quantity", "unit_price", "order_amount",
            "payment_method", "order_status", "source"]
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {schema}.{table} ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT (order_id) DO NOTHING"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, [[r.get(c) for c in cols] for r in rows])


def recent_orders(limit: int = 50):
    schema = os.getenv("ORDERS_SCHEMA", "public")
    table = os.getenv("ORDERS_TABLE", "ordenes_app")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT order_id, order_ts, store_name, item_name, quantity, order_amount, payment_method, order_status FROM {schema}.{table} ORDER BY order_ts DESC LIMIT %s", (limit,))
            cols = [d[0] for d in cur.description]
            return cols, cur.fetchall()

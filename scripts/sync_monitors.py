#!/usr/bin/env python3
"""Aplica el schedule de refresh a los quality monitors de AXO.

Workaround: el CLI (DABs) no propaga el `schedule` del quality_monitor a Terraform,
así que el bundle gestiona la ESTRUCTURA y este script (que corre Jenkins post-deploy)
aplica el SCHEDULE leyendo el cron de `monitor_schedule.cron` (single source).

Idempotente: hace GET de cada monitor, conserva su perfil (time_series/snapshot/
inference_log + slicing) e inyecta el schedule. Auth por DATABRICKS_CONFIG_PROFILE.
"""
import json
import os
import subprocess
import sys

TZ = "America/Mexico_City"
TABLES = [
    "workspace.on.fact_orders",
    "workspace.on.products_silver",
    "workspace.on.predicciones_devolucion",
]
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cli(*args):
    return subprocess.run(["databricks", *args], capture_output=True, text=True)


def main():
    cron = open(os.path.join(HERE, "monitor_schedule.cron")).read().strip()
    print(f"Aplicando schedule '{cron}' ({TZ}) a {len(TABLES)} monitores")
    for table in TABLES:
        g = cli("quality-monitors", "get", table)
        if g.returncode != 0:
            print(f"  ! {table}: no se pudo leer ({g.stderr.strip()[:120]})")
            sys.exit(1)
        m = json.loads(g.stdout)
        body = {
            "output_schema_name": m["output_schema_name"],
            "schedule": {
                "quartz_cron_expression": cron,
                "timezone_id": TZ,
            },
        }
        for k in ("time_series", "snapshot", "inference_log"):
            if k in m:
                body[k] = m[k]
        if m.get("slicing_exprs"):
            body["slicing_exprs"] = m["slicing_exprs"]
        u = cli("quality-monitors", "update", table, "--json", json.dumps(body))
        if u.returncode != 0:
            print(f"  ! {table}: update falló ({u.stderr.strip()[:160]})")
            sys.exit(1)
        print(f"  ✓ {table} -> {cron}")


if __name__ == "__main__":
    main()

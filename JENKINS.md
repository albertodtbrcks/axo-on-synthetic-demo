# CI/CD local con Jenkins + Databricks Asset Bundles

## Bundle (DAB)
- `databricks.yml` — bundle `axo-on-synthetic`, targets `dev` (default) y `prod`.
- `resources/` — pipeline, AXO Main Job, job de carga (`for_each` 24x), dashboards, app.

Comandos (requieren el workaround de Terraform):
```bash
export DATABRICKS_TF_EXEC_PATH=/opt/homebrew/bin/terraform
export DATABRICKS_TF_VERSION=1.12.2
databricks bundle validate -t dev -p axo-on
databricks bundle deploy   -t dev -p axo-on
databricks bundle summary  -t dev -p axo-on
```

## Jenkins local (ya configurado)
- Jenkins corre en http://localhost:8080 (`brew services start jenkins-lts`).
- Job **`AXO-Bundle-CICD`** ya creado: Pipeline *from SCM* → repo público
  `https://github.com/albertodtbrcks/axo-on-synthetic-demo`, branch `main`, `Jenkinsfile`.
- **Auth:** el Jenkinsfile usa el perfil OAuth `axo-on` de `~/.databrickscfg`
  (Jenkins corre como el mismo usuario local). **No requiere PAT** — este workspace
  no permite tokens al usuario. Si el OAuth expira: `databricks auth login ... --profile axo-on`.
- **Sin credenciales Jenkins necesarias** (repo público + auth por perfil).

Correr: abrir el job `AXO-Bundle-CICD` → **Build Now**.
Pipeline: Tooling → Validate (dev) → Deploy (dev, solo en `main`).

## Migrar a CI desatendido (opcional, recomendado para prod)
El perfil OAuth U2M expira. Para CI real, usar un **service principal M2M**:
crear SP + OAuth secret, y en el Jenkinsfile usar `DATABRICKS_CLIENT_ID` /
`DATABRICKS_CLIENT_SECRET` (credenciales Jenkins) en vez del perfil.
(Requiere permisos de admin para crear el SP.)

## Notas
- El agente local debe tener `databricks` y `terraform` en PATH (`/opt/homebrew/bin`).
- `dev` usa `mode: development` (schedules en pausa, recursos prefijados por usuario) → seguro para CI.
- App y dashboards se administran **fuera del bundle** (ver `resources-manual/`): la app ya existe
  y los dashboards tienen un bug de path en esta versión del CLI. El bundle gestiona pipeline + jobs.
- `prod` queda como deploy manual (gate en el Jenkinsfile, comentado).

## Disparo automático (local, sin túnel)
- El job usa **SCM Polling** (`H/2 * * * *`, ~cada 2 min): Jenkins consulta GitHub
  (tráfico saliente, funciona en localhost sin exponer nada) y construye cuando `main` avanza.
- Un **webhook real** (push instantáneo) requeriría exponer Jenkins con un túnel
  (cloudflared/ngrok) porque GitHub no alcanza `localhost`. Para Jenkins local, polling es lo estándar.
- Si en el futuro Jenkins queda en un host público, cambiar el trigger a
  "GitHub hook trigger for GITScm polling" + webhook `<host>/github-webhook/`.

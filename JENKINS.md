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

## Jenkins local
1. Iniciar Jenkins: `brew services start jenkins-lts` (UI en http://localhost:8080).
2. Password inicial: `cat ~/.jenkins/secrets/initialAdminPassword` (o la ruta que indique el log).
3. Completar el wizard (plugins sugeridos + crear usuario admin).
4. Crear credencial **Secret text** con id `databricks-token` = PAT o token de service principal del workspace AXO.
   - PAT rápido: `databricks tokens create --comment jenkins-axo --lifetime-seconds 7776000 -p axo-on`
5. Crear un job **Pipeline**:
   - Pipeline → *Pipeline script from SCM* → Git → `https://github.com/albertodtbrcks/axo-on-synthetic-demo`
   - Branch `*/main`, Script Path `Jenkinsfile`.
   - (Repo privado → agregar credencial Git de `albertodtbrcks`.)
6. *Build Now*. El pipeline: Tooling → Validate (dev) → Deploy (dev, solo en `main`).

## Notas
- El agente local debe tener `databricks` y `terraform` en PATH (`/opt/homebrew/bin`).
- `dev` usa `mode: development` (schedules en pausa, recursos prefijados por usuario) → seguro para CI.
- `prod` queda como deploy manual.

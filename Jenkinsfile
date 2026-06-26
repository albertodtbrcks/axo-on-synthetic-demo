// CI/CD del bundle AXO (Databricks Asset Bundles) — Jenkins local.
// Auth: usa el perfil OAuth `axo-on` cacheado en ~/.databrickscfg del usuario local
// (Jenkins corre como ese usuario). No requiere PAT (este workspace no permite tokens
// al usuario). Si se migra a un SP/M2M, cambiar a DATABRICKS_CLIENT_ID/SECRET.
pipeline {
  agent any

  environment {
    DATABRICKS_CONFIG_PROFILE = 'axo-on'
    // Workaround al bug de descarga de Terraform (llave GPG expirada) en el CLI:
    DATABRICKS_TF_EXEC_PATH   = '/opt/homebrew/bin/terraform'
    DATABRICKS_TF_VERSION     = '1.12.2'
    // asegurar databricks/terraform en PATH para el agente local
    PATH                      = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {
    stage('Tooling') {
      steps {
        sh 'databricks --version && terraform --version | head -1'
      }
    }

    stage('Validate (dev)') {
      steps {
        sh 'databricks bundle validate -t dev'
      }
    }

    stage('Deploy (dev)') {
      // En jobs Pipeline-from-SCM (una rama) BRANCH_NAME no se setea; usamos GIT_BRANCH.
      when {
        expression { (env.GIT_BRANCH ?: '').endsWith('/main') || env.GIT_BRANCH == 'main' }
      }
      steps {
        sh 'databricks bundle deploy -t dev'
        sh 'databricks bundle summary -t dev || true'
      }
    }

    stage('Sync monitor schedules') {
      // El CLI no propaga el schedule del quality_monitor vía bundle; lo aplica este script
      // leyendo monitor_schedule.cron (single source). Solo en main.
      when {
        expression { (env.GIT_BRANCH ?: '').endsWith('/main') || env.GIT_BRANCH == 'main' }
      }
      steps {
        sh 'python3 scripts/sync_monitors.py'
      }
    }

    // Deploy a prod: manual con gate de aprobación
    // stage('Deploy (prod)') {
    //   when { branch 'main' }
    //   steps {
    //     input message: '¿Desplegar a prod?'
    //     sh 'databricks bundle deploy -t prod'
    //   }
    // }
  }

  post {
    success { echo '✅ Bundle validado/desplegado.' }
    failure { echo '❌ Falló el pipeline del bundle.' }
  }
}

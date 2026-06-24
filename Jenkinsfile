// CI/CD del bundle AXO (Databricks Asset Bundles) — Jenkins local.
// Requiere una credencial Jenkins de tipo "Secret text" con id 'databricks-token'
// (PAT o token de un service principal del workspace AXO).
pipeline {
  agent any

  environment {
    DATABRICKS_HOST         = 'https://dbc-2123a53c-916e.cloud.databricks.com'
    DATABRICKS_TOKEN        = credentials('databricks-token')
    // Workaround al bug de descarga de Terraform (llave GPG expirada) en el CLI:
    DATABRICKS_TF_EXEC_PATH = '/opt/homebrew/bin/terraform'
    DATABRICKS_TF_VERSION   = '1.12.2'
    // asegurar que databricks/terraform estén en PATH para el agente local
    PATH                    = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
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
      when { branch 'main' }
      steps {
        sh 'databricks bundle deploy -t dev'
        sh 'databricks bundle summary -t dev || true'
      }
    }

    // Deploy a prod solo manual (descomentar/usar un input gate si se desea)
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

@description('Location for all resources.')
param location string = resourceGroup().location

@description('Docker image tag to deploy (e.g., latest, v1.0.0).')
param imageTag string = 'latest'

@description('Docker image repository (e.g., ghcr.io/plato/skunkworks-commish).')
param imageRepository string

@description('Container registry username (if using private registry).')
@secure()
param registryUsername string = ''

@description('Container registry password (if using private registry).')
@secure()
param registryPassword string = ''

@description('Application Insights connection string.')
@secure()
param appInsightsConnectionString string = ''

@description('Environment variables for the application.')
param environmentVariables object = {}

var storageAccountName = 'sms${uniqueString(resourceGroup().id)}'
var appInsightsName = 'plato-ai-${uniqueString(resourceGroup().id)}'
var logAnalyticsWorkspaceName = 'plato-skunkworks-${uniqueString(resourceGroup().id)}'

// Log Analytics Workspace for centralized logging
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights for application monitoring
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

@description('App Service plan name.')
param appServicePlanName string = 'sms-asp'

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

@description('Containerized API app.')
param apiAppName string = 'sms-api'

var fullImageName = '${imageRepository}:${imageTag}'

resource apiApp 'Microsoft.Web/sites@2022-09-01' = {
  name: apiAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${fullImageName}'
      alwaysOn: true
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: empty(registryUsername) ? '' : 'https://ghcr.io'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: registryUsername
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: registryPassword
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'APPLICATIONINSIGHTS_ROLE_NAME'
          value: 'Plato Commission API'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        // Add custom environment variables
        if (!empty(environmentVariables)) {
          for (envVar in items(environmentVariables)) {
            {
              name: envVar.key
              value: string(envVar.value)
            }
          }
        }
      ]
    }
  }
}

// Output the API endpoint URL
output apiEndpoint string = 'https://${apiApp.properties.defaultHostName}'
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.customerId

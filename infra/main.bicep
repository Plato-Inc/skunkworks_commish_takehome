@description('Location for all resources.')
param location string = resourceGroup().location

var storageAccountName = 'sms${uniqueString(resourceGroup().id)}'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
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

@description('Docker image to deploy (e.g., ghcr.io/your-org/sms-api:latest).')
param containerImage string

resource apiApp 'Microsoft.Web/sites@2022-09-01' = {
  name: apiAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|' + containerImage
    }
  }
}

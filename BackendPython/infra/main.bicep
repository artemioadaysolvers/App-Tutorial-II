@description('Prefijo de 3 a 16 caracteres: letras minúsculas y números. Usar un grupo de recursos nuevo.')
@minLength(3)
@maxLength(16)
param prefix string
param location string = resourceGroup().location
param googleWebClientId string
@secure()
@minLength(32)
param jwtSecret string

var suffix = uniqueString(resourceGroup().id)
var webName = '${prefix}-api-${suffix}'
var registryName = '${prefix}${suffix}'
var cosmosName = '${prefix}-json-${suffix}'
var acrPullRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [{ name: 'EnableServerless' }]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [{ locationName: location, failoverPriority: 0, isZoneRedundant: false }]
    minimalTlsVersion: 'Tls12'
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'MensajesDB'
  properties: { resource: { id: 'MensajesDB' } }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'mensajes'
  properties: {
    resource: {
      id: 'mensajes'
      partitionKey: { paths: ['/userId'], kind: 'Hash', version: 2 }
      indexingPolicy: { indexingMode: 'consistent', automatic: true }
    }
  }
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${prefix}-plan'
  location: location
  kind: 'linux'
  sku: { name: 'B1', tier: 'Basic' }
  properties: { reserved: true }
}

resource web 'Microsoft.Web/sites@2024-04-01' = {
  name: webName
  location: location
  kind: 'app,linux,container'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    clientAffinityEnabled: false
    siteConfig: {
      // Bootstrap only; GitHub Actions replaces this with the Python image.
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/azuredocs/aci-helloworld:latest'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      healthCheckPath: '/ready'
      appSettings: [
        { name: 'WEBSITES_PORT', value: '8080' }
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'false' }
        { name: 'GOOGLE_WEB_CLIENT_ID', value: googleWebClientId }
        { name: 'JWT_SECRET', value: jwtSecret }
        { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
        { name: 'COSMOS_KEY', value: cosmos.listKeys().primaryMasterKey }
        { name: 'COSMOS_DATABASE', value: database.name }
        { name: 'COSMOS_CONTAINER', value: container.name }
      ]
    }
  }
}

resource pullPermission 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, web.id, acrPullRole)
  scope: registry
  properties: {
    roleDefinitionId: acrPullRole
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output webAppName string = web.name
output acrName string = registry.name
output cosmosAccount string = cosmos.name
output apiUrl string = 'https://${web.properties.defaultHostName}'
output resourceGroup string = resourceGroup().name

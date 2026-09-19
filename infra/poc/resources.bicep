targetScope = 'resourceGroup'

param location string
param nameSuffix string
param tags object
param deployerObjectId string

@secure()
param remediatorApiKey string

param existingAcrName string
param existingAcrResourceGroupName string
param checkerImageTag string
param remediatorImageTag string
param projectEndpoint string
param agentName string

var checkerAppName = 'app-ada-checker-poc-${nameSuffix}'
var remediatorAppName = 'app-ada-remediator-poc-${nameSuffix}'
var checkerImage = '${existingRegistry.properties.loginServer}/ada-accessibility-checker:${checkerImageTag}'
var remediatorImage = '${existingRegistry.properties.loginServer}/pdf-ada-remediator:${remediatorImageTag}'
var keyVaultReference = '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/remediator-api-key/)'
var keyVaultSecretsOfficerRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

resource existingRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  scope: resourceGroup(subscription().subscriptionId, existingAcrResourceGroupName)
  name: existingAcrName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-ada-poc-${nameSuffix}'
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-ada-poc-${nameSuffix}'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-ada-poc-${nameSuffix}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
  }
}

resource integrationSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: virtualNetwork
  name: 'snet-app-integration'
  properties: {
    addressPrefix: '10.42.1.0/24'
    delegations: [
      {
        name: 'app-service-delegation'
        properties: {
          serviceName: 'Microsoft.Web/serverFarms'
        }
      }
    ]
  }
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: virtualNetwork
  name: 'snet-private-endpoints'
  properties: {
    addressPrefix: '10.42.2.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
}

resource keyVaultPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

resource keyVaultPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: keyVaultPrivateDnsZone
  name: 'vnet-ada-poc-${nameSuffix}'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: 'kv-ada-poc-${nameSuffix}'
  location: location
  tags: tags
  properties: {
    enablePurgeProtection: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    publicNetworkAccess: 'Disabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: 7
    tenantId: subscription().tenantId
  }
}

resource keyVaultPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-kv-ada-poc-${nameSuffix}'
  location: location
  tags: tags
  properties: {
    privateLinkServiceConnections: [
      {
        name: 'key-vault'
        properties: {
          groupIds: [
            'vault'
          ]
          privateLinkServiceId: keyVault.id
        }
      }
    ]
    subnet: {
      id: privateEndpointSubnet.id
    }
  }
}

resource keyVaultPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: keyVaultPrivateEndpoint
  name: 'key-vault'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'key-vault'
        properties: {
          privateDnsZoneId: keyVaultPrivateDnsZone.id
        }
      }
    ]
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: 'asp-ada-poc-${nameSuffix}'
  location: location
  kind: 'linux'
  tags: tags
  properties: {
    reserved: true
  }
  sku: {
    capacity: 1
    name: 'B1'
    tier: 'Basic'
  }
}

resource remediatorApp 'Microsoft.Web/sites@2024-11-01' = {
  name: remediatorAppName
  location: location
  kind: 'app,linux,container'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    clientAffinityEnabled: false
    httpsOnly: true
    outboundVnetRouting: {
      allTraffic: true
    }
    serverFarmId: appServicePlan.id
    virtualNetworkSubnetId: integrationSubnet.id
    siteConfig: {
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${existingRegistry.properties.loginServer}'
        }
        {
          name: 'PORT'
          value: '8000'
        }
        {
          name: 'REMEDIATOR_API_KEY'
          value: keyVaultReference
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'WORKFLOW_HOST'
          value: '0.0.0.0'
        }
      ]
      ftpsState: 'Disabled'
      healthCheckPath: '/health'
      http20Enabled: true
      linuxFxVersion: 'DOCKER|${remediatorImage}'
      minTlsVersion: '1.2'
      numberOfWorkers: 1
    }
  }
}

resource checkerApp 'Microsoft.Web/sites@2024-11-01' = {
  name: checkerAppName
  location: location
  kind: 'app,linux,container'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    clientAffinityEnabled: true
    httpsOnly: true
    outboundVnetRouting: {
      allTraffic: true
    }
    serverFarmId: appServicePlan.id
    virtualNetworkSubnetId: integrationSubnet.id
    siteConfig: {
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      appSettings: [
        {
          name: 'AGENT_NAME'
          value: agentName
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${existingRegistry.properties.loginServer}'
        }
        {
          name: 'ENVIRONMENT'
          value: 'production'
        }
        {
          name: 'PORT'
          value: '8000'
        }
        {
          name: 'PROJECT_ENDPOINT'
          value: projectEndpoint
        }
        {
          name: 'REMEDIATOR_API_KEY'
          value: keyVaultReference
        }
        {
          name: 'REMEDIATOR_API_URL'
          value: 'https://${remediatorApp.properties.defaultHostName}'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
      ]
      ftpsState: 'Disabled'
      healthCheckPath: '/api/health'
      http20Enabled: true
      linuxFxVersion: 'DOCKER|${checkerImage}'
      minTlsVersion: '1.2'
      numberOfWorkers: 1
    }
  }
}

resource checkerScmAuth 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2023-12-01' = {
  parent: checkerApp
  name: 'scm'
  properties: {
    allow: false
  }
}

resource checkerFtpAuth 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2023-12-01' = {
  parent: checkerApp
  name: 'ftp'
  properties: {
    allow: false
  }
}

resource remediatorScmAuth 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2023-12-01' = {
  parent: remediatorApp
  name: 'scm'
  properties: {
    allow: false
  }
}

resource remediatorFtpAuth 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2023-12-01' = {
  parent: remediatorApp
  name: 'ftp'
  properties: {
    allow: false
  }
}

resource deployerKeyVaultRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, deployerObjectId, keyVaultSecretsOfficerRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: deployerObjectId
    principalType: 'User'
    roleDefinitionId: keyVaultSecretsOfficerRoleDefinitionId
  }
}

resource remediatorApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = {
  parent: keyVault
  name: 'remediator-api-key'
  properties: {
    value: remediatorApiKey
  }
  dependsOn: [
    deployerKeyVaultRole
  ]
}

module acrRoleAssignments './acr-role-assignments.bicep' = {
  name: 'acr-role-assignments'
  scope: resourceGroup(subscription().subscriptionId, existingAcrResourceGroupName)
  params: {
    acrName: existingAcrName
    checkerPrincipalId: checkerApp.identity.principalId
    remediatorPrincipalId: remediatorApp.identity.principalId
  }
}

resource checkerKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, checkerApp.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: checkerApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}

resource remediatorKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, remediatorApp.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: remediatorApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}

output checkerUrl string = 'https://${checkerApp.properties.defaultHostName}'
output remediatorUrl string = 'https://${remediatorApp.properties.defaultHostName}'
output checkerPrincipalId string = checkerApp.identity.principalId
targetScope = 'resourceGroup'

param acrName string
param checkerPrincipalId string
param remediatorPrincipalId string

var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource checkerAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, checkerPrincipalId, acrPullRoleDefinitionId)
  scope: registry
  properties: {
    principalId: checkerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource remediatorAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, remediatorPrincipalId, acrPullRoleDefinitionId)
  scope: registry
  properties: {
    principalId: remediatorPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}
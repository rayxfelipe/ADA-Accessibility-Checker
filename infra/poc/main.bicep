targetScope = 'subscription'

@minLength(1)
param location string = 'westus2'

@minLength(4)
@maxLength(12)
param nameSuffix string

@minLength(36)
@maxLength(36)
param deployerObjectId string

@secure()
param remediatorApiKey string

param existingAcrName string = 'crpdfadastaging33f3'
param existingAcrResourceGroupName string = 'rg-pdf-ada-staging-33f3'
param checkerImageTag string = 'foundry-v2-agent-v2'
param remediatorImageTag string = 'foundry-report-v2'
param projectEndpoint string = 'https://aifproject-ladbs-pdfrem-resource.services.ai.azure.com/api/projects/aifproject-ladbs-pdfremed-001'
param agentName string = 'ADAAccessibilityCheckerAgent'
param modelDeploymentName string = 'gpt-5'
param foundryResourceGroupName string = 'rg-aifproject-ladbs-pdfremed-001'
param foundryAccountName string = 'aifproject-ladbs-pdfrem-resource'
param foundryProjectName string = 'aifproject-ladbs-pdfremed-001'

var resourceGroupName = 'rg-ada-remediation-poc-${nameSuffix}'
var tags = {
  application: 'ada-accessibility-remediation-poc'
  environment: 'poc'
  rollback: 'delete-resource-group'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module resources './resources.bicep' = {
  name: 'ada-remediation-poc'
  scope: resourceGroup
  params: {
    location: location
    nameSuffix: nameSuffix
    tags: tags
    deployerObjectId: deployerObjectId
    remediatorApiKey: remediatorApiKey
    existingAcrName: existingAcrName
    existingAcrResourceGroupName: existingAcrResourceGroupName
    checkerImageTag: checkerImageTag
    remediatorImageTag: remediatorImageTag
    projectEndpoint: projectEndpoint
    agentName: agentName
    modelDeploymentName: modelDeploymentName
    foundryResourceGroupName: foundryResourceGroupName
    foundryAccountName: foundryAccountName
    foundryProjectName: foundryProjectName
  }
}

output resourceGroupName string = resourceGroup.name
output checkerUrl string = resources.outputs.checkerUrl
output remediatorUrl string = resources.outputs.remediatorUrl
output checkerPrincipalId string = resources.outputs.checkerPrincipalId
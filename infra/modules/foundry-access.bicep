// Lets a workload identity call a model on an existing Foundry account without keys.
// Deploy this module into the resource group that contains the Foundry account.
targetScope = 'resourceGroup'

@description('Name of the existing Foundry (AIServices) account in this resource group.')
param foundryAccountName string

@description('Object (principal) ID of the managed identity that calls the model.')
param principalId string

@description('Type of the principal in principalId.')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

// Cognitive Services User: the documented least-privilege role for inference calls.
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' existing = {
  name: foundryAccountName
}

resource inferenceAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, cognitiveServicesUserRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

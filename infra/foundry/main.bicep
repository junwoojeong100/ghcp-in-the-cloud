// Microsoft Foundry account + project + one Claude deployment.
//
// IMPORTANT: deploying a Claude model through this template accepts the Anthropic
// commercial terms on behalf of your organization (modelProviderData). Review
// https://www.anthropic.com/legal/commercial-terms and pass the real organization
// name, country and industry. Claude on Foundry needs an Enterprise or MCA-E subscription.
//
// The deployment is named after the model (for example `claude-sonnet-5-5`), which is
// the default FOUNDRY_MODEL of the demo app, so no extra app setting is needed.
targetScope = 'resourceGroup'

@description('Prefix for resource names (lowercase letters and digits).')
@minLength(2)
@maxLength(12)
param namePrefix string = 'ccd'

@description('Region. Claude models on Foundry are offered in these regions.')
@allowed([
  'eastus2'
  'swedencentral'
  'westus2'
])
param location string = 'swedencentral'

@description('Claude model to deploy. The deployment gets the same name; the app reads it as FOUNDRY_MODEL.')
@minLength(1)
param modelName string = 'claude-sonnet-5-5'

@description('Model version.')
param modelVersion string = '1'

@description('GlobalStandard capacity in units of 1K tokens per minute (TPM). Must fit your quota.')
@minValue(1)
param capacity int = 25

@description('Organization name submitted with the Anthropic terms (modelProviderData).')
@minLength(1)
param claudeOrganizationName string

@description('Two-letter ISO country code of the organization.')
@minLength(2)
@maxLength(2)
param claudeCountryCode string = 'US'

@description('Industry. Must be lowercase to match the Foundry portal list.')
@allowed([
  'technology'
  'finance'
  'healthcare'
  'education'
  'retail'
  'manufacturing'
  'government'
  'media'
  'other'
])
param claudeIndustry string = 'technology'

@description('Optional: object ID of a user (or service principal) that gets the Cognitive Services User role, so `az login` + keyless calls work locally.')
param principalId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Set to true to turn API keys off entirely and allow Microsoft Entra ID only. The quick-start API key path of the app stops working.')
param disableLocalAuth bool = false

param tags object = {
  demo: 'ghcp-in-the-cloud'
}

var suffix = take(uniqueString(resourceGroup().id), 6)
var accountName = '${namePrefix}-foundry-${suffix}'
var projectName = '${namePrefix}-project'
var grantAccess = !empty(principalId)

// Cognitive Services User: the documented least-privilege role for inference calls.
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: disableLocalAuth
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Declared before the deployment so RBAC propagates while the model deploys.
resource userAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantAccess) {
  name: guid(account.id, principalId, cognitiveServicesUserRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

resource claude 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = {
  parent: account
  name: modelName
  sku: {
    name: 'GlobalStandard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'Anthropic'
      name: modelName
      version: modelVersion
    }
    // Not in the published type definitions yet, but required by the service for Anthropic models.
    #disable-next-line BCP037
    modelProviderData: {
      organizationName: claudeOrganizationName
      countryCode: claudeCountryCode
      industry: claudeIndustry
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [
    project
    userAccess
  ]
}

@description('Value for FOUNDRY_RESOURCE.')
output foundryResource string = account.name

@description('Value for FOUNDRY_MODEL (the deployment name).')
output deploymentName string = claude.name

output resourceGroupName string = resourceGroup().name
output claudeBaseUrl string = 'https://${account.name}.services.ai.azure.com/anthropic'
output projectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'

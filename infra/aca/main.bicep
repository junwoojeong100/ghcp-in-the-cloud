// Azure Container Apps demo: registry, logs, environment, managed identity and the app.
//
// Deploy in two phases (scripts/deploy-aca.sh does this for you):
//   1. deployApp=false -> registry + identity + environment (and the optional Foundry role)
//   2. build the image into the registry, then deployApp=true -> the container app
// The identity pulls from the registry and, if foundryResource is set, calls Claude
// on Microsoft Foundry. No keys and no registry passwords are stored anywhere.
targetScope = 'resourceGroup'

@description('Prefix for resource names (lowercase letters and digits).')
@minLength(2)
@maxLength(12)
param namePrefix string = 'ccd'

param location string = resourceGroup().location

@description('Container app name. It is also the first part of the public host name.')
@minLength(2)
@maxLength(32)
param appName string = 'cloud-copilot-demo'

@description('false: registry, identity and environment only. true: also the container app (the image must already exist).')
param deployApp bool = false

@description('Tag of the cloud-copilot-demo image in the registry. Also shown as the app version.')
param imageTag string = 'v1'

@description('Optional fixed revision suffix (revision name becomes <appName>--<suffix>). Empty lets Azure generate one.')
param revisionSuffix string = ''

@secure()
@description('Password of the demo UI (HTTP Basic, user "demo").')
param demoPassword string

@description('Name of an existing Microsoft Foundry account. Empty runs the app with the offline mock backend.')
param foundryResource string = ''

@description('Resource group of the Foundry account.')
param foundryResourceGroup string = resourceGroup().name

@description('Foundry deployment name of the model.')
param foundryModel string = 'claude-sonnet-5-5'

@allowed([
  'low'
  'medium'
  'high'
  'xhigh'
  'max'
])
param foundryEffort string = 'max'

@description('Simulated model latency of the mock backend. Slow answers pile up concurrent requests, which makes scale-out visible.')
@minValue(0)
@maxValue(10000)
param mockLatencyMs int = 1000

@minValue(0)
param minReplicas int = 0

@minValue(1)
param maxReplicas int = 5

@description('Concurrent requests per replica that trigger scale-out.')
@minValue(1)
param concurrentRequests int = 5

param tags object = {
  demo: 'ghcp-in-the-cloud'
}

var suffix = take(uniqueString(resourceGroup().id), 6)
var registryName = '${namePrefix}acr${suffix}'
var imageRepository = 'cloud-copilot-demo'
var useFoundry = !empty(foundryResource)
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-logs-${suffix}'
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-aca-identity'
  location: location
  tags: tags
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

module foundryAccess '../modules/foundry-access.bicep' = if (useFoundry) {
  name: 'foundry-access'
  scope: resourceGroup(foundryResourceGroup)
  params: {
    foundryAccountName: foundryResource
    principalId: identity.properties.principalId
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-aca-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

var commonEnv = [
  {
    name: 'APP_VERSION'
    value: imageTag
  }
  {
    name: 'DEMO_PASSWORD'
    secretRef: 'demo-password'
  }
  {
    name: 'LLM_BACKEND'
    value: useFoundry ? 'foundry' : 'mock'
  }
  {
    name: 'MOCK_LATENCY_MS'
    value: string(mockLatencyMs)
  }
  {
    // Selects the user-assigned identity for DefaultAzureCredential.
    name: 'AZURE_CLIENT_ID'
    value: identity.properties.clientId
  }
]

var foundryEnv = useFoundry ? [
  {
    name: 'FOUNDRY_RESOURCE'
    value: foundryResource
  }
  {
    name: 'FOUNDRY_MODEL'
    value: foundryModel
  }
  {
    name: 'FOUNDRY_EFFORT'
    value: foundryEffort
  }
] : []

resource app 'Microsoft.App/containerApps@2024-03-01' = if (deployApp) {
  name: appName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      // Multiple revisions allow traffic splitting (canary) between revisions.
      activeRevisionsMode: 'Multiple'
      maxInactiveRevisions: 10
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
        // Re-deploying this template resets any canary split to "latest revision = 100%".
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: [
        {
          name: 'demo-password'
          value: demoPassword
        }
      ]
    }
    template: {
      revisionSuffix: !empty(revisionSuffix) ? revisionSuffix : null
      containers: [
        {
          name: 'app'
          image: '${registry.properties.loginServer}/${imageRepository}:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: concat(commonEnv, foundryEnv)
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8080
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: 8080
              }
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: string(concurrentRequests)
              }
            }
          }
        ]
      }
    }
  }
  dependsOn: [
    acrPull
    foundryAccess
  ]
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output imageRepository string = imageRepository
output environmentName string = environment.name
output identityClientId string = identity.properties.clientId
output identityPrincipalId string = identity.properties.principalId
output appName string = appName
output appUrl string = deployApp ? 'https://${app!.properties.configuration.ingress.fqdn}' : ''
output latestRevisionName string = deployApp ? app!.properties.latestRevisionName : ''

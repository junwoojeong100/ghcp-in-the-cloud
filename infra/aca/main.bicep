@description('Container image in a registry reachable by Azure Container Apps.')
param imageName string

@description('Microsoft Foundry resource name, without the hostname.')
param foundryResource string

@secure()
@description('Microsoft Foundry Anthropic API key. Supply securely at deployment time.')
param foundryApiKey string

@secure()
@description('Password used to protect the public demo interface.')
param demoPassword string

param location string = resourceGroup().location

var appName = 'cloud-copilot-demo'
var environmentName = 'cloud-copilot-demo-env'
var workspaceName = 'cloud-copilot-demo-logs'

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
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

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'foundry-api-key'
          value: foundryApiKey
        }
        {
          name: 'demo-password'
          value: demoPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: imageName
          env: [
            {
              name: 'FOUNDRY_RESOURCE'
              value: foundryResource
            }
            {
              name: 'FOUNDRY_MODEL'
              value: 'claude-sonnet-5-5'
            }
            {
              name: 'ANTHROPIC_FOUNDRY_API_KEY'
              secretRef: 'foundry-api-key'
            }
            {
              name: 'DEMO_PASSWORD'
              secretRef: 'demo-password'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 2
      }
    }
  }
}

output appUrl string = 'https://${app.properties.configuration.ingress.fqdn}'

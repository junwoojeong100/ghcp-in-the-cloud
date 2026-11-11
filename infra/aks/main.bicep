// AKS demo: registry, cluster with Microsoft Entra ID + Azure RBAC, and a workload identity.
//
// Security defaults: no local Kubernetes accounts (Entra ID only), Azure RBAC for
// Kubernetes authorization, OIDC issuer + Workload Identity so a pod calls a model on
// Microsoft Foundry without any key, and a registry without an admin user.
targetScope = 'resourceGroup'

@description('Prefix for resource names (lowercase letters and digits).')
@minLength(2)
@maxLength(12)
param namePrefix string = 'ccd'

@description('Region of all resources. Defaults to the region of the resource group.')
param location string = resourceGroup().location

@description('VM size of the node pool. Pick another size if this one is not available in your region or subscription.')
param nodeVmSize string = 'Standard_D2s_v5'

@description('Minimum node count of the cluster autoscaler.')
@minValue(1)
param nodeMinCount int = 1

@description('Maximum node count of the cluster autoscaler.')
@minValue(1)
param nodeMaxCount int = 3

@description('Namespace of the demo app. Must match infra/aks/k8s/namespace.yaml.')
param kubernetesNamespace string = 'cloud-copilot-demo'

@description('ServiceAccount of the demo app. Must match infra/aks/k8s/base/serviceaccount.yaml.')
param kubernetesServiceAccount string = 'cloud-copilot-demo'

@description('Optional: object ID of the person who runs the demo. Gets cluster admin through Azure RBAC.')
param principalId string = ''

@description('Type of the principal in principalId.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Name of an existing Microsoft Foundry account. Empty skips the Foundry role assignment (mock backend).')
param foundryResource string = ''

@description('Resource group of the Foundry account.')
param foundryResourceGroup string = resourceGroup().name

@description('Tags on every resource. scripts/cleanup.sh only deletes resource groups that carry demo=ghcp-in-the-cloud.')
param tags object = {
  demo: 'ghcp-in-the-cloud'
}

var suffix = take(uniqueString(resourceGroup().id), 6)
var registryName = '${namePrefix}acr${suffix}'
var clusterName = '${namePrefix}-aks'
var grantPresenter = !empty(principalId)

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var aksRbacClusterAdminRoleId = 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b'
var aksClusterUserRoleId = '4abbcc35-e782-43d8-92c5-2d3f1bd2253f'

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

resource cluster 'Microsoft.ContainerService/managedClusters@2025-01-01' = {
  name: clusterName
  location: location
  tags: tags
  sku: {
    name: 'Base'
    tier: 'Free'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dnsPrefix: '${clusterName}-${suffix}'
    enableRBAC: true
    // Only Microsoft Entra ID users can sign in; authorization is Azure RBAC.
    disableLocalAccounts: true
    aadProfile: {
      managed: true
      enableAzureRBAC: true
      tenantID: tenant().tenantId
    }
    // Both are required for Microsoft Entra Workload Identity.
    oidcIssuerProfile: {
      enabled: true
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      loadBalancerSku: 'standard'
    }
    autoUpgradeProfile: {
      upgradeChannel: 'patch'
    }
    agentPoolProfiles: [
      {
        name: 'system'
        mode: 'System'
        type: 'VirtualMachineScaleSets'
        osType: 'Linux'
        vmSize: nodeVmSize
        count: nodeMinCount
        enableAutoScaling: true
        minCount: nodeMinCount
        maxCount: nodeMaxCount
      }
    ]
  }
}

// Nodes pull images from the registry with the kubelet identity.
resource kubeletAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, cluster.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: cluster.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

resource presenterClusterAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPresenter) {
  name: guid(cluster.id, principalId, aksRbacClusterAdminRoleId)
  scope: cluster
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aksRbacClusterAdminRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Lets the same person run `az aks get-credentials`.
resource presenterClusterUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPresenter) {
  name: guid(cluster.id, principalId, aksClusterUserRoleId)
  scope: cluster
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aksClusterUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// The identity the demo pods act as when they call Microsoft Foundry.
resource workloadIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-aks-workload'
  location: location
  tags: tags
}

resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: workloadIdentity
  name: 'aks-${kubernetesNamespace}-${kubernetesServiceAccount}'
  properties: {
    issuer: cluster.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:${kubernetesNamespace}:${kubernetesServiceAccount}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

module foundryAccess '../modules/foundry-access.bicep' = if (!empty(foundryResource)) {
  name: 'foundry-access'
  scope: resourceGroup(foundryResourceGroup)
  params: {
    foundryAccountName: foundryResource
    principalId: workloadIdentity.properties.principalId
  }
}

@description('Name of the AKS cluster.')
output clusterName string = cluster.name

@description('Name of the container registry.')
output registryName string = registry.name

@description('Login server of the container registry.')
output registryLoginServer string = registry.properties.loginServer

@description('Client ID of the workload identity; it goes into the ServiceAccount annotation.')
output workloadClientId string = workloadIdentity.properties.clientId

@description('Object ID of the workload identity.')
output workloadPrincipalId string = workloadIdentity.properties.principalId

@description('OIDC issuer URL of the cluster, trusted by the federated credential.')
output oidcIssuerUrl string = cluster.properties.oidcIssuerProfile.issuerURL

@description('Microsoft Entra tenant ID.')
output tenantId string = tenant().tenantId

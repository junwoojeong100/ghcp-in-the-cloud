---
name: 'Bicep infrastructure'
description: 'Rules for Bicep templates under infra/: parameters, identity, RBAC, outputs and validation.'
applyTo: 'infra/**/*.bicep'
---

# Bicep rules (`infra/`)

- Every `param` and `output` you add or change has `@description`. Add `@allowed`, `@minLength`/`@maxLength` or `@minValue`/`@maxValue` when the valid values are limited.
- Secrets: mark secret params with `@secure()`. Never emit secrets, keys, connection strings or tokens in `output`s. Prefer keyless access (managed identity, Entra ID, Workload Identity) over keys.
- Identity: give the workload a user-assigned managed identity and grant the narrowest built-in role at the narrowest scope. For Foundry inference that is `Cognitive Services User` (`a97b65f3-24c7-4388-baec-2e87135dc908`) on the Foundry account only. Name role assignments deterministically, for example `guid(scope.id, principalId, roleDefinitionId)`.
- Names derive from a prefix parameter (default `ccd`) so copies can coexist. Respect Azure length and character limits.
- Use explicit, current API versions. Do not use `latest` image tags.
- Foundry model deployments default to `gpt-6.1-sol` (`modelFormat` `OpenAI`), which has no provider data. Claude (`modelFormat` `Anthropic`) needs `modelProviderData` (`organizationName`, `countryCode`, lowercase `industry`), which accepts Anthropic's commercial terms. Take the organization name from a parameter; never hard-code a person or company. Capacity uses `GlobalStandard` units (1 unit = 1K tokens per minute).
- Prefer secure defaults: HTTPS only, minimum TLS 1.2, no anonymous access, no public exposure that the demo does not need.
- Keep each demo deployable on its own (`infra/foundry`, `infra/aca`, `infra/aks`). Do not make one template depend on another template's resources unless a parameter carries the value.
- Validate with `bicep build infra/<name>/main.bicep` (or `az bicep build --file <file>`) and fix every warning you introduced.

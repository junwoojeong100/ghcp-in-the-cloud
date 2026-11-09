---
name: 'Kubernetes manifests'
description: 'Hardening, probes, resources and Workload Identity rules for the AKS manifests under infra/aks/.'
applyTo: 'infra/aks/**/*.yaml,infra/aks/**/*.yml'
---

# Kubernetes rules (`infra/aks/`)

- Security context: `runAsNonRoot: true` with a numeric `runAsUser`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]` and `seccompProfile.type: RuntimeDefault`. If the app needs a writable path, mount an `emptyDir` instead of loosening the root filesystem.
- Probes: `readinessProbe` and `livenessProbe` call `GET /healthz` on port 8080. `/healthz` is the only unauthenticated route, so never point probes at routes that need credentials.
- Resources: every container sets CPU and memory `requests` and `limits`. The HPA scales on CPU utilization, so it needs the CPU request. Keep the `PodDisruptionBudget`.
- Images: never `:latest`. Use an explicit tag or digest; the deploy script supplies the ACR image it built.
- Identity: Pods reach Foundry through Microsoft Entra Workload Identity. Label the Pod with `azure.workload.identity/use: "true"` and annotate the ServiceAccount `cloud-copilot-demo` with `azure.workload.identity/client-id`. Keep keys out of manifests; if a Secret is unavoidable, reference it with `secretKeyRef` and never commit its value.
- Exposure: the Service stays `ClusterIP` (access through `kubectl port-forward`). Do not add a LoadBalancer or Ingress unless asked.
- The namespace and the ServiceAccount are both named `cloud-copilot-demo`; labels and selectors must stay consistent across Deployment, Service, HPA and PDB.
- Validate with `kustomize build infra/aks/k8s/base | kubeconform -strict -summary`. `scripts/render-aks-manifests.sh` layers the environment values (image, identity, backend) on that base, so CI checks what the deploy script applies.

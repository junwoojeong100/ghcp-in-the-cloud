# Demo 6 — AKS: Rolling Updates, Autoscaling, Workload Identity and Secure Defaults

Run the same app on managed Kubernetes (AKS) and show what Kubernetes does well: zero-downtime rolling updates and rollback, pod autoscaling under load, secretless Azure authentication (Workload Identity), and secure defaults that block unsafe pods.

> **Language**: The app and the scripts in this repository are in Korean. This guide names their labels and messages in English; the Korean text is listed in [Language of the app and the scripts](../../README.md#language-of-the-app-and-the-scripts).

## At a glance

| Item | Details |
|---|---|
| Goal | Check the deployment state → HPA autoscaling → rolling update and rollback → check Workload Identity → (optional) reject a risky pod |
| Time | About 8 minutes. Finish the cluster deployment (5–10 minutes) and the v2 image build before the demo. |
| Difficulty | High. You run `kubectl` commands yourself. |
| Standalone | Yes. You only need an Azure subscription. The default is the `mock` backend, so it works without Foundry, and you can check Workload Identity with mock too. To see the Foundry call as well, do Demo 4 first. |

```text
browser ─ kubectl port-forward ─▶ Service(ClusterIP) ─▶ 2–5 pods (HPA, PDB)
                                                      ▲    │ Workload Identity (no secrets)
          load-generator (on only during the demo) ───┘    ▼
                                                     Microsoft Foundry (optional)
```

## Why this service (benefits)

- **Standard Kubernetes, with Azure operating the control plane**: You use `kubectl`, manifests and open-source tools as they are, and you do not manage the control plane, such as the API server (this demo uses the Free tier).
- **Zero-downtime rolling updates and rollback**: Thanks to `maxSurge: 1`, `maxUnavailable: 0` and the readiness probe, an old pod goes down only after a new pod is ready. If something goes wrong, one line, `kubectl rollout undo`, rolls it back.
- **Autoscaling**: The HPA adjusts pods between 2 and 5 based on CPU utilization (50% of requests), and when nodes run short, the cluster autoscaler adjusts nodes between 1 and 3.
- **Availability protection**: A PodDisruptionBudget (`minAvailable: 1`) protects the last pod even during a node drain or a cluster upgrade.
- **Keyless Azure authentication (Workload Identity)**: The pod's service account token is exchanged for a Microsoft Entra ID token. No API key or password goes into the pod.
- **A cluster that is safe by default**: Pod Security `restricted` is enforced on the namespace, and cluster access uses only Entra ID and Azure RBAC, with no local accounts.

## Prerequisites

1. **Tools**: `az` (sign in with `az login`), `kubectl`, `kubelogin`, `python3`, `curl` and `bash` 4 or later (on macOS, `brew install bash`). Install `kubectl` and `kubelogin` together with `az aks install-cli`. If your subscription blocks ACR Tasks, you also need local `docker`.
2. **Azure permissions**: You need an account that can create resource groups and role assignments (subscription Owner, or Contributor plus User Access Administrator). This is because the infrastructure assigns the cluster admin role and the registry read role.
3. **Deployment** (it takes 5–10 minutes, so do it before the demo):

   ```bash
   scripts/deploy-aks.sh                # answer y to the confirmation. Use --yes to skip the question.
   ```

   It creates the cluster, the registry and the Workload Identity, builds the image and applies the manifests. At the end it prints the **password** once, so write it down (set `DEMO_PASSWORD` to choose it yourself). The default resource group is `rg-cloud-copilot-aks`, the default region is `koreacentral` and the default node size is `Standard_D2s_v5`. A message that waits for cluster permissions to take effect may appear several times, and that is normal.

   To use a Foundry model, first do Demo 4, then run `source .azure/foundry.env` in the same shell and run this script.
4. **Build the v2 image in advance.** In the rolling update demo, you only swap to an image that is already pushed.

   ```bash
   ACR_NAME="$(az acr list --resource-group rg-cloud-copilot-aks --query "[0].name" --output tsv)"
   ACR_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)"
   az acr build --registry "$ACR_NAME" --image cloud-copilot-demo:v2 \
     --build-arg APP_VERSION=v2 --file app/Dockerfile .        # run from the repository root
   ```

5. **Check right before the demo**:

   ```bash
   kubectl get pods --namespace cloud-copilot-demo              # 2 or more pods Running, READY 1/1
   kubectl get deployment load-generator --namespace cloud-copilot-demo   # READY 0/0 (load is off)
   ```

   It is convenient to prepare three terminals: one for commands, one for `--watch` and one for port forwarding.

If you continue the demo from a different shell, reconnect to the cluster.

```bash
CLUSTER_NAME="$(az aks list --resource-group rg-cloud-copilot-aks --query "[0].name" --output tsv)"
az aks get-credentials --resource-group rg-cloud-copilot-aks --name "$CLUSTER_NAME" --overwrite-existing
kubelogin convert-kubeconfig --login azurecli
```

## Demo steps

> Portal menu names may change. Almost every step in this demo is a terminal command; the only web screens are the demo app UI and, optionally, the Azure portal. Text in angle brackets (`<>`) is a placeholder for your own value.

### 1. Tour the cluster and the workload (about 1.5 min)

```bash
kubectl get nodes
kubectl get deployment,hpa,pdb,service,pods --namespace cloud-copilot-demo
```

1. You see the `Deployment`, the `HorizontalPodAutoscaler` (minimum 2, maximum 5), the `PodDisruptionBudget` (`minAvailable 1`), the `Service` (`ClusterIP`) and the pods at once.
2. Open port forwarding in a separate terminal and connect with a browser. The service is `ClusterIP` so that it is not exposed to the internet.

   ```bash
   kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace cloud-copilot-demo
   ```

   Open `http://localhost:8080` and sign in with the user `demo` and the password. In the info chips, check **Platform** (`aks`), **Instance** (the pod name), **Revision** (the pod template hash) and **Version** (`v1`).
3. The same smoke test passes against the port-forward address too.

   ```bash
   DEMO_PASSWORD='<password>' scripts/smoke-test.sh http://localhost:8080 --expect-backend mock
   ```

Port forwarding connects to a single pod, so the **Show traffic distribution** button shows only one instance. Show the spread across several instances in the canary of Demo 5.

Success criteria: Two or more pods are `Running`, the Platform chip is `aks`, and the Instance chip equals one of the pod names from `kubectl get pods`. The smoke test prints `모든 확인(14개)을 통과했습니다.` (all 14 checks passed). If you deployed with the Foundry backend, use `--expect-backend foundry`.

### 2. When load rises, pods increase: HPA (about 2.5 min)

```bash
# Terminal A: keep watching the HPA and the pods (stop: Ctrl+C)
kubectl get hpa,pods --namespace cloud-copilot-demo --watch
```

```bash
# Terminal B: turn on the load generator
kubectl scale deployment/load-generator --replicas=1 --namespace cloud-copilot-demo
```

`load-generator` keeps calling the service's `/healthz` with the same image. It does not call the model, so only the CPU goes up, at no cost. The pod's CPU request is 100m and the target is 50%, so when the average CPU per pod exceeds about 50m, it becomes a scale-out candidate. The load generator exists to cross this threshold, and you can see the actual usage with `kubectl top pods --namespace cloud-copilot-demo`.

1. In Terminal A, the HPA's `TARGETS` value goes over the target (50%), `REPLICAS` grows from 2, and new pods go through `ContainerCreating` to `Running`. If the value shows `<unknown>` for a while, it is still collecting metrics, so wait a moment. Scale-out can take from tens of seconds to a few minutes.
2. When you have seen it, turn the load off.

   ```bash
   kubectl scale deployment/load-generator --replicas=0 --namespace cloud-copilot-demo
   ```

3. When the load is gone, the pods shrink again. To avoid flapping, the HPA waits for a stabilization window (60 seconds in this demo) before it scales down, so watch for a few minutes.

Success criteria: After you turn the load on, `REPLICAS` grows above 2 (up to 5), and after you turn it off, it returns to 2 after a while. How many pods it grows to depends on the environment, so do not promise a number.

### 3. Zero-downtime rolling update and rollback (about 2.5 min)

```bash
# Terminal A: watch the pods being replaced (stop: Ctrl+C)
kubectl get pods --namespace cloud-copilot-demo --watch
```

```bash
# Terminal B: swap the image to v2 (uses ACR_SERVER from prerequisite 4)
kubectl set image deployment/cloud-copilot-demo app="$ACR_SERVER/cloud-copilot-demo:v2" --namespace cloud-copilot-demo
kubectl rollout status deployment/cloud-copilot-demo --namespace cloud-copilot-demo
kubectl rollout history deployment/cloud-copilot-demo --namespace cloud-copilot-demo
```

1. In Terminal A, watch a new pod get created first (`maxSurge: 1`), and only after it is `READY 1/1` does the old pod change to `Terminating` (`maxUnavailable: 0`). The number of ready pods never drops below the desired replica count.
2. Port forwarding drops when the pod it is connected to is replaced (`lost connection to pod`). Run it again and refresh the browser, and you see that **Version** is `v2` and the Revision and Instance values are new.
3. Roll back. Assume there is a problem in v2.

   ```bash
   kubectl rollout undo deployment/cloud-copilot-demo --namespace cloud-copilot-demo
   kubectl rollout status deployment/cloud-copilot-demo --namespace cloud-copilot-demo
   ```

   Reopen the port forward and the version is back to `v1`.

Success criteria: `rollout status` prints `successfully rolled out`, `READY 1/1` pods remain even during the rollout, and the Version in the UI changes `v1` → `v2` → (after the rollback) `v1`. The `deploy-aks.yml` workflow of Demo 3 runs the same rolling update for you (the first 7 characters of the commit become the image tag).

### 4. Workload Identity: call Azure without secrets (about 1 min)

```bash
# which Managed Identity the service account is linked to (client-id annotation)
kubectl get serviceaccount cloud-copilot-demo --namespace cloud-copilot-demo --output jsonpath='{.metadata.annotations}'

# pick out only the four values injected into the pod that are used for authentication
kubectl exec --namespace cloud-copilot-demo deploy/cloud-copilot-demo -- printenv \
  | grep -E '^AZURE_(CLIENT_ID|TENANT_ID|FEDERATED_TOKEN_FILE|AUTHORITY_HOST)='
```

1. The service account's `azure.workload.identity/client-id` annotation points to the Managed Identity's client ID.
2. The pod gets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE` and `AZURE_AUTHORITY_HOST` injected. There are no secret values, and the token file is a short-lived service account token. The Azure SDK exchanges this token for an Entra ID token.
3. If you deployed with the Foundry backend (Demo 4), `auth` in `/api/info` is `entra-id` and there is no API key in the model call.

> Do not run `printenv` as it is while you share your screen. The app password (`DEMO_PASSWORD`) would show up with it. The command above filters out only the four lines you need.

Success criteria: The annotation has a client ID and all four environment variables appear. The trust is limited to a single service account, `system:serviceaccount:cloud-copilot-demo:cloud-copilot-demo`.

### 5. (Optional) Unsafe pods cannot get in (about 1 min)

The namespace enforces Pod Security `restricted`. If you try to create a privileged pod, it is rejected.

```bash
kubectl apply --namespace cloud-copilot-demo --filename - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: privileged-demo
spec:
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sleep", "3600"]
      securityContext:
        privileged: true
EOF
```

Success criteria: `Error from server (Forbidden)` is printed together with `violates PodSecurity "restricted:latest"`, and no pod is created. This app's pods already satisfy `restricted` with a non-root UID 10001, a read-only root filesystem and all capabilities dropped.

## Talking points

- **"The power of Kubernetes, with Azure taking over the operational burden."** The platform operates the control plane (this demo turns on the automatic upgrade channel for Kubernetes patch versions), and the team focuses on the workload.
- **Zero downtime is the result of configuration, not a default.** You need `maxUnavailable: 0`, the readiness probe and the PDB together. Three lines in the manifest are that promise.
- **The HPA decides by utilization against requests.** Setting realistic requests is a precondition for autoscaling.
- **Workload Identity is a feature that "removes secrets".** There is no key in the repository, in secrets or in the pod's environment variables, and the trust scope is a single pair of a namespace and a service account.
- **Access uses Entra ID too.** The cluster has local accounts turned off, and `kubectl` uses the `az login` token. The identity of the deploy pipeline (Demo 3) has write permission only on this namespace.
- **Cost**: On AKS the nodes are billed continuously. Clean up right after the demo.

## Cleanup

```bash
scripts/cleanup.sh aks             # deletes the AKS resource group (asks for confirmation)
```

Resource groups without the `demo=ghcp-in-the-cloud` tag are not deleted. If the load generator is on, first turn it off with `kubectl scale deployment/load-generator --replicas=0 --namespace cloud-copilot-demo`. If you finished the demo in the v2 state, you can go back to v1 with `kubectl rollout undo deployment/cloud-copilot-demo --namespace cloud-copilot-demo`, and you do not need to recreate the cluster. When you run `scripts/deploy-aks.sh` again, set `DEMO_PASSWORD`. If you do not, a new password is created, and the script restarts the pods to apply it. Check the contexts left in your local `kubeconfig` with `kubectl config get-contexts` and delete them with `kubectl config delete-context <name>`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `클러스터 권한이 적용되길 기다리는 중...` (waiting for the cluster permissions to take effect) repeats during deployment | Role assignments take a few minutes to reach the API server. This is normal. If it still fails after 20 retries, run the script again. |
| `kubectl` shows an authentication error or cannot find `kubelogin` | Run `az login` again, install the tools with `az aks install-cli`, and then run the "reconnect to the cluster" commands that follow the prerequisites. |
| An error says the node VM size is not available | Check the sizes available in the region (`az vm list-skus --location koreacentral --size Standard_D2s --output table`) and run again with `NODE_VM_SIZE=<size> scripts/deploy-aks.sh`. |
| `az acr build` fails (ACR Tasks blocked) | `deploy-aks.sh` uses local Docker automatically. For prerequisite 4, replace the build with `az acr login --name "$ACR_NAME"` followed by `docker build --build-arg APP_VERSION=v2 --file app/Dockerfile --tag "$ACR_SERVER/cloud-copilot-demo:v2" .` and `docker push "$ACR_SERVER/cloud-copilot-demo:v2"`. |
| A pod is in `ImagePullBackOff` | The image tag is not in the registry, or the registry read permission has not taken effect yet. Check the tags with `az acr repository show-tags --name "$ACR_NAME" --repository cloud-copilot-demo --output tsv` and look at the events of `kubectl describe pod <pod>`. |
| A pod is `Pending` | If node resources run short, the cluster autoscaler takes a few minutes to add a node (up to 3). If the subscription quota is short, `kubectl describe pod <pod>` shows the reason. |
| HPA `TARGETS` stays `<unknown>` | Metrics have not been collected yet. Wait 1–2 minutes and then check the reason with `kubectl describe hpa cloud-copilot-demo --namespace cloud-copilot-demo`. |
| Pods do not increase when you turn the load on | Check that the load pod is `Running` with `kubectl get pods --selector app.kubernetes.io/name=load-generator --namespace cloud-copilot-demo`. Scaling decisions take time. |
| Port forwarding drops with `lost connection to pod` | The pod it was connected to was replaced by the rollout. Run the command again. |
| You forgot the password | `kubectl get secret cloud-copilot-demo --namespace cloud-copilot-demo --output jsonpath='{.data.password}' \| base64 --decode` |
| The UI keeps showing the old version right after the rollout | The port forward is still attached to an old pod that has not terminated yet. After `rollout status` finishes, reopen the port forward and refresh. |

## Using it with other demos

This demo runs end to end on its own. Using it with the others connects the story.

- **Demo 3 (GitHub Actions)**: When you run `deploy-aks.yml` (`gh workflow run deploy-aks.yml`), it logs in with OIDC, builds the image and does the same rolling update. The identity of this pipeline has only the cluster user role and the RBAC Writer role scoped to this namespace.
- **Demo 4 (Foundry)**: If you run `scripts/deploy-aks.sh` after `source .azure/foundry.env`, the pod calls gpt-6.1-sol with a Workload Identity, and `/api/info` shows `backend=foundry` and `auth=entra-id`.
- **Demo 5 (ACA)**: It runs the same image as serverless. Compare the two approaches with the selection guide below.

### Choosing between AKS and ACA

The two demos run the same image in different ways. The difference is not which one is better but what the team wants.

| Aspect | Azure Container Apps (Demo 5) | AKS (this demo) |
|---|---|---|
| Operational burden | There is no cluster. It centers on the image and settings. | You handle node pools, upgrades, networking and manifests yourself (Azure operates the control plane). |
| Scaling | Request-count rules, scale-to-zero | HPA and the node autoscaler. The default HPA has a minimum of 1 or more, and scaling down to 0 needs extra setup such as KEDA. |
| Deployment strategy | Canary, blue-green and instant rollback are handled by settings, using revisions and traffic splitting | Rolling update is the default, and strategies such as canary are built by adding an ingress, a service mesh or dedicated tools |
| Scope of control | App-level control | The whole Kubernetes API (CRDs, operators, network policies, node scheduling) |
| Good fit | When you want to run web apps, APIs and event processing quickly | When you need the standard Kubernetes tools and ecosystem, or fine-grained control |

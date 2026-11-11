# Demo 3 — GitHub Actions: CI/CD Without Secrets (OIDC) and Reusable Pipelines

On every PR, verify the code, the container, the IaC and the workflows in parallel, and deploy by logging in to Azure with OIDC and no stored secrets. The same verification scripts run unchanged in CI, in the Copilot agent environment and locally.

> **Language**: The app and the scripts in this repository are in Korean. This guide names their labels and messages in English; the Korean text is listed in [Language of the app and the scripts](../../README.md#language-of-the-app-and-the-scripts).

## At a glance

| Item | Details |
|---|---|
| Goal | Show ① the 4 `CI` jobs running in parallel on a PR, ② how to set up trust with Azure with zero secrets, and ③ the flow from environment approval → OIDC login → image build → deployment of a new revision. |
| Time | About 7 minutes. The deploy workflow includes build time, so run it once before the demo, and live start a new run to show it up to the approval step. |
| Difficulty | Medium |
| Standalone | Step 1 needs only a GitHub repository (no Azure). Steps 2–3 need an Azure subscription and a deployment target (Container Apps or AKS). You can create the target with `scripts/deploy-aca.sh`; you do not have to follow Demo 5. |

```text
PR ─▶ CI ─┬─ Unit tests
          ├─ Container build and smoke test
          ├─ IaC validation
          └─ Workflow and script lint

manual run ─▶ azure-demo environment (approval) ─▶ GitHub OIDC token ─▶ Azure login
           ─▶ ACR build and push ─▶ build provenance attestation ─▶ new Container Apps revision
```

## Why this service (benefits)

- **Fast feedback**: Four independent jobs run at the same time, and `pip` dependencies are cached. When you push again to the same PR, the earlier run in progress is canceled automatically (`concurrency`).
- **Deployment without long-lived secrets**: Azure (Microsoft Entra ID) trusts the short-lived OIDC token that GitHub issues for each job. The repository has no service principal password and no keys. The only stored values are identifiers such as the client ID and the tenant ID, and they are all non-secret variables.
- **Narrow trust scope**: The subject of the federated credential is `repo:<owner>/<repo>:environment:azure-demo`, so only a job that uses this repository's `azure-demo` environment can log in. The roles on the Azure side are also limited to the target resource group, the registry and the namespace.
- **Least-privilege `permissions`**: The workflow default is `contents: read`. Only the deploy job additionally gets `id-token: write` and `attestations: write`.
- **Human approval gate**: If you set approvers on the `azure-demo` environment, the run does not reach the step that logs in to Azure before someone approves.
- **Supply-chain security**: Every third-party action is pinned to a full commit SHA (Dependabot opens update PRs), and in public repositories a build provenance attestation is recorded for the deployed image.
- **Code, IaC and container verification in one pipeline**: Unit tests, a read-only container smoke test, the Bicep build, Kubernetes manifest validation (kubeconform), actionlint, shellcheck and hadolint all run in the same `CI`.
- **Reuse**: The verification steps are `scripts/*.sh`, so you can reproduce them locally with the same commands. `scripts/install-dev-tools.sh` is used by both CI and `copilot-setup-steps.yml`.

## Prerequisites

**Step 1 (GitHub only)**

- You must be able to use Actions in this repository (or your fork). Prepare one branch for the demo change.

**Steps 2–3 (Azure required)**

1. **Tools**: `az` (signed in: `az login`), `gh` (signed in with repository admin access: `gh auth login`) and `bash` 4 or later. The default bash on macOS is 3.2, so install a newer one with `brew install bash`.
2. **Azure permissions**: You need an account that can create Managed Identities and role assignments (subscription Owner, or Contributor plus User Access Administrator).
3. **Create the deployment target first**: `setup-github-oidc.sh` grants roles on resources that already exist, so the target must exist first.

   ```bash
   scripts/deploy-aca.sh --yes     # the mock backend means no Foundry is needed. It takes a few minutes.
   ```

   To use the AKS deploy workflow (`deploy-aks.yml`), also create AKS with `scripts/deploy-aks.sh`. The two workflows are independent of each other.
4. **`azure-demo` environment (optional, for the approval gate)**: To show the approval step, set an approver. `setup-github-oidc.sh` also creates the environment if it is missing, but set the approver with this command.

   ```bash
   scripts/apply-repo-settings.sh --apply --only environment --reviewer <your GitHub user name>
   ```

   If you are the approver, you can approve runs that you started yourself. If you turn on "Prevent self-review" in the environment settings, someone else must approve.

## Demo steps

> Portal menu names may change. Text in angle brackets (`<>`) is a placeholder for your own value.

### 1. Parallel CI on a PR (about 2 min) — no Azure needed

1. Push a small change, such as one line in the docs, to a branch and open a PR.
2. On the PR's **Checks** tab or in **Actions → CI**, show the 4 jobs running at the same time. In a terminal, it looks like this:

   ```bash
   gh pr checks --watch
   ```

3. Open the log of the `Smoke test` step of `Container build and smoke test`. In a container started with a read-only filesystem and `--cap-drop ALL`, 14 checks pass one after another.
4. (Optional) Deliberately break one assertion in `app/tests` and push. Only `Unit tests` turns red and the rest keep going. With the ruleset on, the merge button is blocked too.

These are the commands that reproduce the same verification locally.

| Job | Local command |
|---|---|
| `Unit tests` | `python -m unittest discover -s app/tests -v` |
| `Container build and smoke test` | `docker build --file app/Dockerfile --tag cloud-copilot-demo .`, then start the container and run `scripts/smoke-test.sh` (see "Quick start" in the README) |
| `IaC validation` | `az bicep build --file infra/aca/main.bicep --stdout > /dev/null` and `scripts/render-aks-manifests.sh \| kubeconform -strict -summary` (install kubeconform with `scripts/install-dev-tools.sh kubeconform`) |
| `Workflow and script lint` | `actionlint`, `shellcheck scripts/*.sh scripts/lib/*.sh`, `hadolint app/Dockerfile` |

Success criteria: `Unit tests`, `Container build and smoke test`, `IaC validation` and `Workflow and script lint` are all green, and the end of the `Smoke test` log shows `모든 확인(14개)을 통과했습니다.` (all 14 checks passed).

### 2. Set up trust with Azure without secrets (about 2 min)

```bash
scripts/setup-github-oidc.sh            # preview: prints only the commands it would run and changes nothing
scripts/setup-github-oidc.sh --apply    # apply for real (running it many times gives the same result)
```

The script does three things. It handles only the deployment targets (Container Apps, AKS) that you have already created.

1. Creates a user-assigned Managed Identity (`ccd-github-actions`) and a federated credential. The subject is `repo:<owner>/<repo>:environment:azure-demo`.
2. Grants roles only on the target resources. For Container Apps: Contributor on the resource group and AcrPush on the registry. For AKS: the cluster user role, RBAC Writer scoped to the namespace, and AcrPush.
3. Stores `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and the per-target `ACA_*` and `AKS_*` variables in the `azure-demo` environment.

Then check it on screen.

- GitHub: Show that **Settings → Secrets and variables → Actions** has **no Secrets at all**. **Settings → Environments → azure-demo** has only identifier variables.
- Azure portal: Under **Federated credentials** of the Managed Identity `ccd-github-actions`, show the issuer and the subject.

Success criteria: `--apply` succeeds to the end, identifier variables appear in the `azure-demo` environment (if you created only Container Apps, 3 `AZURE_*` and 3 `ACA_*` variables), and the Secrets list is empty.

### 3. Run the deploy workflow: approval → OIDC login → new revision (about 3 min)

```bash
gh workflow run deploy-aca.yml          # or Actions → "Deploy to Azure Container Apps" → Run workflow
gh run watch                            # pick the run and follow its progress
```

1. If you set an approver on the environment, the run stops in the **Waiting** state. Approve `azure-demo` under **Review deployments**. Until this step passes, nothing reaches Azure.
2. Walk through the steps in order: `Log in to Azure with OIDC` (login without secrets), `Build and push the image`, `Attest the build provenance`, `Roll out a new revision`, `Wait until the app answers`.
3. In the run's **Summary**, look at the app URL, the new revision name, the image, the commit and the traffic split.
4. Open the app URL. The **Version** chip in the page header has changed to the first 7 characters of the commit, so you can tell right away which commit is answering.
5. Supply-chain check: verify the signed attestation that the image was built by this repository's workflow (public repositories).

   ```bash
   az acr login --name <ACR name>
   gh attestation verify oci://<ACR name>.azurecr.io/cloud-copilot-demo:<first 7 characters of the commit> --owner <owner>
   ```

   `<ACR name>` is the same as the `azure-demo` environment variable `ACA_ACR_NAME`, and you can also get it with `az acr list --resource-group rg-cloud-copilot-aca --query "[0].name" --output tsv`.

AKS works the same way. Running `gh workflow run deploy-aks.yml` builds and pushes the image, then does a rolling update with `kubectl set image` and `kubectl rollout status`.

Success criteria: The run ends green, `/api/info` of the app returns the new commit's version, and `gh attestation verify` reports a successful verification.

## Talking points

- **"There is no password in GitHub or in Azure."** When a job starts, GitHub issues an OIDC token, and `azure/login` presents that token to Entra ID. If the issuer and the subject match the federated credential, it receives an Azure token. The token is usable only during that job.
- **Trust is narrowed to the environment.** The subject contains `environment:azure-demo`, so jobs from other workflows or environments cannot log in. You can add environment approval and branch restrictions on top.
- **Permissions are granted per job, only as much as needed.** The default is read-only, and only the deploy job gets the permissions to issue a token and store an attestation.
- **Deployments are not canceled.** CI cancels the earlier run when a new push arrives, but the deploy workflow uses `cancel-in-progress: false`, so it queues runs instead of cutting off a deployment in progress.
- **Action versions are pinned by SHA.** Tags can be moved, but a commit SHA never changes. People review version updates in Dependabot PRs.
- **The build provenance attestation** lets you verify that "this image was built by this workflow, at this commit, in this repository".
- This workflow **does not touch traffic.** For an app with a canary split, the new revision is created at 0%, and you promote it with `scripts/aca-canary.sh` from Demo 5.

## Cleanup

```bash
scripts/cleanup.sh oidc        # deletes the Managed Identity, the role assignments and the azure-demo environment variables (asks for confirmation)
```

- Delete the deployed app and registry with the cleanup commands of Demos 5 and 6 (`scripts/cleanup.sh aca`, `scripts/cleanup.sh aks`).
- The image attestations stay in GitHub, but you do not need to delete them.
- The `azure-demo` environment itself and its approver settings are not deleted. You use them as they are in the next demo.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Log in to Azure with OIDC` fails with `AADSTS700213` or `AADSTS70021` (no matching federated identity record found) | The subject does not match. The log of the failed step has a `subject claim` line, so compare it with the subject of the federated credential in Azure. A recently created repository sends a format that includes numeric IDs, such as `repo:<owner>@<id>/<repo>@<id>:environment:azure-demo`. If you run `scripts/setup-github-oidc.sh --apply` again (add `--repo <owner>/<name>` for a fork), it matches the credential to the `sub_claim_prefix` that GitHub reports. |
| The error `azure-demo 환경에 변수가 없습니다` (the azure-demo environment is missing variables) | You have not run `scripts/setup-github-oidc.sh --apply` yet, or the variables were stored in another repository or environment. Check the variables under Settings → Environments → azure-demo. |
| The run stops at **Waiting** | It is waiting for the environment approver. Approve under **Review deployments**. If you do not get the approval notification, check the environment's approver settings. |
| `AuthorizationFailed` | Role assignments can take a few minutes to propagate. After a short while, run again with **Re-run failed jobs**. If it continues, check that `setup-github-oidc.sh` targeted the correct resource group. |
| The deployment succeeded but the version on the page is unchanged | In an app with a canary split, the new revision is created at 0%. Check with `scripts/aca-canary.sh status` and promote with `scripts/aca-canary.sh promote`, or run `scripts/deploy-aca.sh` again to reset the split. |
| `Wait until the app answers` fails | The app may be starting from scale-to-zero. This step retries 12 times. If it still fails, check the logs with `az containerapp logs show --name cloud-copilot-demo --resource-group rg-cloud-copilot-aca`. |
| The `Attest the build provenance` step is skipped | The workflow is set up not to create attestations in private repositories (they need GitHub Enterprise Cloud). It runs only in public repositories. |
| `gh attestation verify` fails | Check that you ran `az acr login` first, that the image tag equals the first 7 characters of the deployed commit, and that `--owner` is the repository owner. |
| A required check stays at "Expected — Waiting for status to be reported" | The workflow has not started yet (for a Copilot agent PR, a person must click **Approve and run workflows**), or the job name differs from the ruleset's required check name. |

## Using it with other demos

This demo is complete with step 1 alone. Using it with the others connects the story.

- **Demo 1 (GitHub Copilot)**: A PR made by the agent must pass the same `CI`. The moment a person clicks **Approve and run workflows** connects to this demo's "human approval" message.
- **Demo 2 (GitHub Repo)**: Three of the `CI` job names are the required status checks of the `main-protection` ruleset. The CodeQL and dependency review workflows run on the same PR.
- **Demo 4 (Foundry)**: Even if the target app is set to the Foundry backend, the workflow changes only the image and `APP_VERSION`, so the settings stay.
- **Demos 5 and 6 (Container Apps, AKS)**: These are the deployment targets. Step 3 of this demo leads into the canary of Demo 5 and the rolling update of Demo 6.

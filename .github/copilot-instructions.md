# Copilot instructions — Cloud Copilot Demo

## What this repo is
- A demo kit for Korean developers: one tiny app (Python 3.12 stdlib `http.server` + one HTML page; answers come from Claude Sonnet 5.5 on Microsoft Foundry) plus the GitHub and Azure setup around it.
- Six independent demos in `demos/`: `01-github-copilot`, `02-github-repo`, `03-github-actions`, `04-microsoft-foundry`, `05-azure-container-apps`, `06-aks`.
- Layout: `app/` (server, UI, Dockerfile, `tests/`), `infra/foundry/`, `infra/aca/` and `infra/aks/` (Bicep; Kubernetes manifests in `infra/aks/k8s/`), `scripts/` (bash), `.github/` (workflows, instructions, prompts, agents), `demos/`, `slides/`.

## Commands (trust these first; search only if one fails)
- Test: `python -m unittest discover -s app/tests -v`
- Run offline: `LLM_BACKEND=mock DEMO_PASSWORD=<any-local-value> python -m app.server` (port 8080, user `demo`)
- Image: `docker build --file app/Dockerfile --tag cloud-copilot-demo .`
- Bicep: `bicep build infra/<foundry|aca|aks>/main.bicep` (or `az bicep build --file <file>`)
- Kubernetes: `kustomize build infra/aks/k8s/base | kubeconform -strict -summary` (`scripts/render-aks-manifests.sh` layers environment values on the same base)
- Lint: `actionlint` and `shellcheck scripts/*.sh`

## Application rules
- Python 3.12 + stdlib only. The only third-party packages are `anthropic` and `azure-identity` (pinned in `app/requirements.txt`); do not add others.
- `GET /healthz` is the only unauthenticated route (platform probes). Every other route needs HTTP Basic auth (user `demo`, password from `DEMO_PASSWORD`), checked before the request body is read.
- Never log, echo or return secrets, API keys, tokens, passwords, `Authorization` headers or full prompts. Credentials come only from environment variables or platform secrets, never from source, tests, docs or examples.
- Prefer keyless Microsoft Entra ID (`DefaultAzureCredential`, scope `https://ai.azure.com/.default`) over API keys. `FOUNDRY_MODEL` is the Foundry deployment name.
- Keep the Claude Sonnet 5.5 default (`claude-sonnet-5-5`) with `effort=max` and `max_tokens=4096`.
- Keep `LLM_BACKEND=mock` working offline (no Azure, no network, no SDK import); demos and CI depend on it.
- UI: render model output with `textContent`, never `innerHTML`.
- Tests: `unittest` only, offline and deterministic. Every route needs tests for success, `401`, bad input and `/healthz` staying open.

## Infrastructure and workflows (details in `.github/instructions/`)
- Bicep: `@description` on every param and output you add, `@secure()` for secrets, no secrets in outputs, managed identity plus least-privilege RBAC.
- Kubernetes: non-root, read-only root filesystem, drop ALL capabilities, seccomp `RuntimeDefault`, probes on `/healthz`, requests and limits, Workload Identity instead of secrets.
- Actions: least-privilege `permissions`, OIDC instead of stored Azure secrets, pinned actions, no untrusted input inside `run:` scripts.

## Docs and language
- Docs, slides and speaker notes are Korean. Identifiers, commands, file names and code comments stay English.
- Use these terms consistently: 리비전, 워크로드 ID(Workload Identity), 관리 ID(Managed Identity), 스케일 투 제로(scale-to-zero).
- Do not invent benchmarks, prices or SLAs. No placeholder text, fake URLs or secret-looking strings.

## Pull requests
- Keep PRs small and focused. Add or update tests with every behavior change, and update `README.md`, `demos/` and slides when behavior, env vars or commands change.
- Fill in the PR template. The `CI` workflow must be green. A human reviews and merges; never self-approve.

## Demo guardrails
- Do not rename routes, env vars, the image `cloud-copilot-demo`, the Kubernetes namespace and ServiceAccount `cloud-copilot-demo`, CI job names or the `copilot-setup-steps` job. Docs, slides and required checks refer to them.
- `GET /api/info` and the UI header (platform, instance, revision, model) must keep working; the canary and scale demos make them visible.

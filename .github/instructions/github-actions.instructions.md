---
name: 'GitHub Actions workflows'
description: 'Least-privilege, keyless and injection-safe rules for the workflows under .github/workflows/.'
applyTo: '.github/workflows/*.yml,.github/workflows/*.yaml'
---

# GitHub Actions rules

- Permissions: set `permissions: contents: read` at the top of every workflow and raise it per job only where needed, for example `id-token: write` for Azure OIDC login or `security-events: write` for code scanning.
- Azure access uses OIDC federated credentials through `azure/login`, with `client-id`, `tenant-id` and `subscription-id` read from the variables of the `azure-demo` environment (`${{ vars.AZURE_CLIENT_ID }}` and so on, created by `scripts/setup-github-oidc.sh`). Never store Azure client secrets or publish profiles. Deploy jobs use `environment: azure-demo` so approvals apply.
- Pin every action, including `actions/*`, to a full commit SHA and keep the version in a trailing comment; Dependabot updates both. Never use `@main` or `@master`.
- Never check out or run untrusted pull request code from `pull_request_target`, and never expose secrets or write tokens to code from forks. CI runs on `pull_request`.
- Expression injection: never put `${{ github.event.* }}`, branch names, or issue and PR titles or bodies directly into a `run:` script. Pass them through `env:` and quote the shell variable, for example `"$PR_TITLE"`.
- `actions/checkout` uses `persist-credentials: false` unless the job pushes. The `copilot-setup-steps` job keeps the default, as in GitHub's documented example.
- Reliability: set `timeout-minutes` on every job. CI and deploy workflows also get a `concurrency` group: cancel superseded CI runs, but never cancel a running deployment (`cancel-in-progress: false`).
- Job display names are a contract. CI keeps `Unit tests`, `Container build and smoke test`, `IaC validation` and `Workflow and script lint` (required status checks).
- `.github/workflows/copilot-setup-steps.yml` keeps exactly one job named `copilot-setup-steps`. Copilot honors only `steps`, `permissions`, `runs-on`, `services`, `snapshot` and `timeout-minutes` (at most 59) there. Keep it small: checkout, Python 3.12, `pip install -r app/requirements.txt`, then `scripts/install-dev-tools.sh` (the lint tools CI uses), with `contents: read`. A failing step makes Copilot skip the remaining steps, so keep the optional installer last. Copilot code review reuses this file by default.
- Validate with `actionlint` before pushing.

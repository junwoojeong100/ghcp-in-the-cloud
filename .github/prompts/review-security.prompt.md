---
description: 'Security review of a change or area, using this repository''s checklist'
argument-hint: 'scope, e.g. the current changes, app/server.py or infra/aca'
agent: ask
---

Review for security problems: ${input:scope:the current changes, or a path such as app/server.py}

Check every item against the code that is actually there. Report only what you can point to in a file and line. Do not claim a control exists unless you can see it.

## Checklist
1. **Authentication**: only `GET /healthz` is public. Every other route needs Basic auth, compared in constant time and checked before the body is read. A missing `DEMO_PASSWORD` fails closed.
2. **Secrets**: no keys, tokens, passwords or `Authorization` values in source, tests, docs, examples, logs or error responses. Credentials come from env vars or platform secrets. Keyless Entra ID is preferred.
3. **Input and injection**: request size and field limits, JSON validation, no shell, `eval` or string-built commands. The UI renders model output with `textContent`, never `innerHTML`. The CSP stays strict.
4. **Abuse and availability**: shared state is locked and bounded, upstream calls have timeouts, and errors do not leak internals.
5. **Infrastructure** (Bicep, Kubernetes): least-privilege roles at the narrowest scope, no secret outputs, managed identity or Workload Identity, non-root with a read-only root filesystem, dropped capabilities, seccomp, probes, limits, and no unintended public exposure.
6. **Workflows**: least-privilege `permissions`, OIDC instead of stored secrets, pinned third-party actions, no `pull_request_target` with PR code, no `github.event` expressions (titles, branch names, bodies) interpolated directly into `run:` scripts.
7. **Dependencies**: only `anthropic` and `azure-identity`, with pinned versions.

## Output (Korean)
- A table sorted by severity: 심각도 (High, Medium, Low) · 위치 (`file:line`) · 문제 · 수정 제안.
- A short list of what you verified as fine, and a list of open questions.
- Do not edit files. If you find nothing, say so explicitly.

## Success criteria
- Every finding cites a file and line and explains the impact in one sentence.
- Nothing is invented. Anything you could not verify is listed as a question.

---
description: 'Add one API endpoint to the demo app, with tests and docs'
argument-hint: 'route and behavior, e.g. GET /api/version'
agent: agent
---

Add one new endpoint to the Cloud Copilot Demo app.

## Inputs
- Route and method: ${input:route:GET /api/version}
- Behavior: ${input:behavior:Return the app version as JSON}

## Steps
1. Read `.github/copilot-instructions.md` and `.github/instructions/python.instructions.md`. Then study how `app/server.py` serves `/api/info`: routing, the Basic auth check and the JSON error shape.
2. Implement the endpoint in `app/server.py` with the standard library only. Keep `GET /healthz` unauthenticated and put the new route behind the existing Basic auth check, before any request body is read. Do not rename or change existing routes.
3. Validate input and reuse the existing JSON error shape for bad input. Never log or return secrets.
4. Add `unittest` tests in `app/tests/` for success, `401` without credentials, bad input (if the route takes input) and `/healthz` staying open. Use `LLM_BACKEND=mock`; no network, no real credentials.
5. Document the endpoint: update the endpoint list and any new env var in `README.md`, and the matching Korean guide under `demos/` if one describes the API.
6. Run `python -m unittest discover -s app/tests -v` and fix failures.

## Success criteria
- New and existing tests pass.
- The route answers `401` without credentials and works with Basic auth (user `demo`).
- No new dependency and no secret; `LLM_BACKEND=mock` still works offline.
- Reply with a short Korean summary: changed files, the test command and its result, and anything the reviewer should check.

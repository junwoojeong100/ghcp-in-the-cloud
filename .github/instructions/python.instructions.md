---
name: 'Python app and tests'
description: 'Conventions for the stdlib HTTP server, the Foundry client and the unittest tests under app/.'
applyTo: 'app/**/*.py'
---

# Python rules (`app/`)

## Runtime
- Target Python 3.12. Use the standard library plus `anthropic` and `azure-identity` only. Import those SDKs lazily, inside the code path that needs them, so `LLM_BACKEND=mock` runs without Azure or network access.
- Read configuration from environment variables while handling a request, not at import time, so tests can patch `os.environ`. Document every new variable in `README.md`.
- Keep functions small and readable. Avoid new module-level mutable state; if you need it, guard it and bound it (see below).

## HTTP handling
- The server is a `ThreadingHTTPServer`, so handlers run on several threads. Protect shared mutable state with a `threading.Lock` and keep it bounded: never grow a dict per unvalidated client input without a cap or expiry.
- Authenticate first. Compare HTTP Basic credentials with `hmac.compare_digest` before reading the request body. Only `GET /healthz` skips authentication.
- Validate input: cap body and field sizes, require valid JSON of the expected shape, and answer `400` for bad input.
- Error responses are JSON with an English `error` message and, where helpful, a Korean `hint`. Follow the existing shape in `app/server.py`. Never include stack traces, secrets, tokens, `Authorization` headers, passwords or request bodies in responses or logs.
- Inject clocks and clients (arguments or attributes) so tests do not patch globals or sleep in real time.

## Foundry client
- GPT deployments (default `gpt-6.1-sol`) call the OpenAI-compatible endpoint with `urllib` and an Entra ID token; Claude deployments use `anthropic.AnthropicFoundry`. `model` is the Foundry deployment name (`FOUNDRY_MODEL`).
- Keyless by default: `DefaultAzureCredential` with `get_bearer_token_provider(credential, "https://ai.azure.com/.default")`. Use `FOUNDRY_API_KEY` (or the older `ANTHROPIC_FOUNDRY_API_KEY`) only when it is set.
- Keep the effort defaulting to `max` (GPT receives `xhigh`, Claude receives `output_config={"effort": ...}`) and the default of the token cap at `4096`.

## Tests (`app/tests/`)
- `unittest` only. Run `python -m unittest discover -s app/tests -v`.
- Tests are offline and deterministic: `LLM_BACKEND=mock`, an ephemeral port, patched environment variables, no real credentials.
- For each route cover success, `401` without or with wrong credentials, invalid input (`400`) and `/healthz` staying open.
- Reset any shared state (counters, caches, limiters) between tests so test order never matters.

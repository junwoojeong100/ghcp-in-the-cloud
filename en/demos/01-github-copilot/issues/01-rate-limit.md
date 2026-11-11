# [Demo] Add a per-client rate limit to POST /api/chat

### Context

Every call to `POST /api/chat` in the demo app costs model inference. Today there is no limit on the number of calls, so a badly written script or repeated clicks turn directly into cost and latency.

- Server: `app/server.py` (built on the standard library `http.server`, `ThreadingHTTPServer`)
- Tests: `app/tests/` (`unittest`; the server runs on a temporary port with `LLM_BACKEND=mock`)
- Docs: `README.md`

### Requirement

Add a per-client **token bucket** rate limit that applies to `POST /api/chat` only. A simple implementation that works only in process memory is enough.

- Environment variable `RATE_LIMIT_PER_MINUTE`: the number of requests one client can send per minute. The default is `30`. The bucket capacity equals this value, the bucket refills at `RATE_LIMIT_PER_MINUTE / 60` tokens per second, and each request uses one token.
- When no token is left, return HTTP `429` with JSON in the existing error format (`{"error": "Rate limit exceeded", "hint": "<short hint>"}`). Put the seconds until the next request is allowed in the `Retry-After` header, rounded up to an integer (minimum `1`). For example, with `RATE_LIMIT_PER_MINUTE=3`, the fourth request in a row is told to retry in about 20 seconds.
- The client identifier is the remote address of the TCP connection (`self.client_address[0]`). Do **not** read headers such as `X-Forwarded-For`, because they can be forged.
- Check order: authentication (`401`) → rate limit (`429`) → read and validate the request body → model call. A request that fails authentication does not use a token.
- Do not rate-limit `GET /healthz`, `GET /` or `GET /api/info`.
- The server handles requests on several threads, so protect shared state with `threading.Lock`. Keep the per-client bucket map from growing without bound: evict entries that have not been used for some time (for example, 10 minutes) or cap the number of entries.
- `RATE_LIMIT_PER_MINUTE=0` turns the limit off. If the value is not an integer or is negative, log one warning line and run with the default `30`. Read the environment variable when a request is handled, as the existing code does.
- Make the time source replaceable (for example, accept a clock function as an argument or attribute) so tests do not have to wait in real time.

### Acceptance criteria

- [ ] With `RATE_LIMIT_PER_MINUTE=3`, when the same client calls `POST /api/chat` four times in a row, the first three calls get `200` and the fourth gets `429` with an integer `Retry-After` (1 or more).
- [ ] Tokens refill as time passes, so requests succeed again (verified with a fake clock; tests do not use `sleep`).
- [ ] Clients with different addresses do not affect each other's limits (a bucket-level unit test is enough).
- [ ] A call without authentication returns `401` regardless of the limit, and that request does not use a token.
- [ ] `RATE_LIMIT_PER_MINUTE=0` turns the limit off, and invalid values (`abc`, `-5`) fall back to the default `30`.
- [ ] `/healthz`, `/` and `/api/info` are not affected by the rate limit.
- [ ] The limiter state can be reset between tests, and existing tests do not fail because of the new limit.
- [ ] New unit tests are in `app/tests/`, and `python -m unittest discover -s app/tests -v` passes.
- [ ] The environment variable section of `README.md` documents `RATE_LIMIT_PER_MINUTE` and the known limits (behind a proxy all clients may look like one address; the state lives only in process memory, so each replica counts separately).

### Constraints

- Scope of changes: `app/server.py`, `app/tests/` and `README.md`. Do not change any other file.
- Use only the Python 3.12 standard library. Do not add packages and do not change `app/requirements.txt`.
- Keep existing behavior: `/healthz` without authentication, the existing Basic authentication on every other route, the existing error response format, and offline operation with `LLM_BACKEND=mock`.
- Keep the rate-limit state on the server instance or behind an explicit reset function, so that tests running in the same process do not affect each other.
- Do not write secrets, the `Authorization` header or request bodies to logs.
- This change affects security and availability. Describe how it works and its known limits in the PR description so that a person can review it carefully.

### How to test

```bash
python -m unittest discover -s app/tests -v
```

Manual check (optional): start the server on a temporary port and call it four times. The last response should be `429`.

```bash
export DEMO_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(12))')"
RATE_LIMIT_PER_MINUTE=3 LLM_BACKEND=mock PORT=8081 python -m app.server &
SERVER_PID=$!
sleep 1
for i in 1 2 3 4; do
  curl -s -o /dev/null -w "%{http_code}\n" -u "demo:$DEMO_PASSWORD" \
    -H 'Content-Type: application/json' -d '{"message":"hello"}' http://127.0.0.1:8081/api/chat
done
kill "$SERVER_PID"
```

### Out of scope

- Interpreting proxy headers such as `X-Forwarded-For`, and trusted proxy lists
- Distributed rate limiting with an external store such as Redis (counting separately per replica is a known limit that is only documented)
- Per-user limits, IP blocklists and an API to change the limit
- Rate limits on routes other than `POST /api/chat`
- Changes to the slides and the `demos/` docs

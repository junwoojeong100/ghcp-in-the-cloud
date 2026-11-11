# [Demo] Add a Prometheus-format GET /metrics endpoint

### Context

When we run the app on ACA or AKS, we want to collect request counts and response times with a tool such as Prometheus. The app has no metrics endpoint today. Build the Prometheus text exposition format (version 0.0.4) by hand with only the standard library, without new dependencies.

- Server: `app/server.py` (built on the standard library `http.server`, `ThreadingHTTPServer`)
- Tests: `app/tests/` (`unittest`; the server runs on a temporary port with `LLM_BACKEND=mock`)
- Docs: `README.md`

### Requirement

Add `GET /metrics` and export the metrics below in the Prometheus text format.

- The response `Content-Type` is `text/plain; version=0.0.4; charset=utf-8`.
- `demo_http_requests_total{method,path,status}` (counter): the number of requests handled.
- `demo_http_request_duration_seconds{method,path}` (histogram): request handling time in seconds. Emit all of the `_bucket{le="..."}` (cumulative; the last one is `le="+Inf"`), `_sum` and `_count` series. Example bucket bounds: `0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 180` (`effort=max` reasoning can take a long time).
- Add `# HELP` and `# TYPE` lines for every metric.
- Normalize label values to a small fixed set so that cardinality does not grow. `path` is one of `/`, `/api/info`, `/api/chat`, `/healthz` and `/metrics`, and every other path is `other`. `method` is `GET` or `POST`, and every other method is `other`. `status` is the response code as a string.
- Count every response, including `401` and `404`. If you record the status code and the elapsed time at the common point where responses are sent, you do not have to add code to each route.
- Authentication: `/metrics` requires HTTP Basic authentication (user `demo`) just like every route except `/healthz`. Reuse the existing authentication check that `/api/info` uses.
- The server handles requests on several threads, so protect the metrics store with `threading.Lock`.
- Docs: add `/metrics` to the endpoint description in `README.md` and write a **note about scrape authentication**. For Prometheus to scrape this endpoint, the scrape config needs Basic authentication credentials (for example, `basic_auth` with `username: demo` and a `password_file`). Tell readers to inject the password through a file or a secret instead of writing it in plain text in the config file.

### Acceptance criteria

- [ ] `GET /metrics` without authentication returns `401`. With correct Basic authentication it returns `200` and `Content-Type` is `text/plain; version=0.0.4; charset=utf-8`.
- [ ] The response has `# HELP` and `# TYPE` lines: `counter` for `demo_http_requests_total` and `histogram` for `demo_http_request_duration_seconds`.
- [ ] After one call to `GET /api/info`, reading `/metrics` shows that `demo_http_requests_total{method="GET",path="/api/info",status="200"}` went up by 1.
- [ ] The histogram `_bucket` values are cumulative (monotonically increasing), the `le="+Inf"` value equals `_count`, and `_sum` is present.
- [ ] A request to a path that does not exist (for example, `/no-such-path`) is counted only as `path="other"`, so no new labels appear.
- [ ] `GET /healthz` still returns `200` without authentication.
- [ ] The metrics store can be reset between tests, new unit tests are in `app/tests/`, and `python -m unittest discover -s app/tests -v` passes.
- [ ] `README.md` describes `/metrics` and has the note about scrape authentication.

### Constraints

- Scope of changes: `app/server.py`, `app/tests/` and `README.md`. Do not change any other file.
- Use only the Python 3.12 standard library. Do not add packages such as `prometheus_client` and do not change `app/requirements.txt`.
- Keep `/healthz` unauthenticated and keep the existing Basic authentication on every other route, including `/metrics`. Also keep the existing error response format and offline operation with `LLM_BACKEND=mock`.
- Do not put secrets, request bodies, question text, `Authorization` values or client addresses in the metrics.
- Label combinations must stay inside the fixed set described above.

### How to test

```bash
python -m unittest discover -s app/tests -v
```

Manual check (optional): start the server on a temporary port, call `/api/info` once and read the metrics.

```bash
export DEMO_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(12))')"
LLM_BACKEND=mock PORT=8081 python -m app.server &
SERVER_PID=$!
sleep 1
curl -s -o /dev/null -u "demo:$DEMO_PASSWORD" http://127.0.0.1:8081/api/info
curl -s -u "demo:$DEMO_PASSWORD" http://127.0.0.1:8081/metrics | head -n 30
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/metrics
kill "$SERVER_PID"
```

The last `curl` (without authentication) should print `401`.

### Out of scope

- Azure Managed Prometheus, collection settings on ACA or AKS, ServiceMonitor, dashboards and alert rules
- Process and runtime metrics (`process_*`, `python_*`) and model token usage metrics
- Adopting OpenTelemetry and any new dependency
- Opening `/metrics` without authentication (keep Basic authentication)
- Changes to the slides and the `demos/` docs

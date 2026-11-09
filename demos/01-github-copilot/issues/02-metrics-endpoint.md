# [Demo] Prometheus 형식의 GET /metrics 엔드포인트 추가

### 배경 (Context)

ACA나 AKS에서 앱을 운영할 때 요청 수와 응답 시간을 Prometheus 같은 도구로 수집하고 싶습니다. 지금 앱에는 지표 엔드포인트가 없습니다. 새 의존성 없이 표준 라이브러리만으로 Prometheus 텍스트 노출 형식(text exposition format, 버전 0.0.4)을 직접 만들어 냅니다.

- 서버: `app/server.py` (표준 라이브러리 `http.server` 기반, `ThreadingHTTPServer`)
- 테스트: `app/tests/` (`unittest`, 서버를 임시 포트에서 실행하고 `LLM_BACKEND=mock` 사용)
- 문서: `README.md`

### 요구사항 (Requirement)

`GET /metrics`를 추가해 아래 지표를 Prometheus 텍스트 형식으로 내보냅니다.

- 응답 `Content-Type`은 `text/plain; version=0.0.4; charset=utf-8`입니다.
- `demo_http_requests_total{method,path,status}` (counter): 처리한 요청 수.
- `demo_http_request_duration_seconds{method,path}` (histogram): 요청 처리 시간(초). `_bucket{le="..."}`(누적, 마지막은 `le="+Inf"`), `_sum`, `_count` 시리즈를 모두 냅니다. 버킷 경계 예: `0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 180` (`effort=max` 추론은 오래 걸릴 수 있습니다).
- 지표마다 `# HELP`와 `# TYPE` 줄을 붙입니다.
- 라벨 값은 고정된 작은 집합으로 정규화해서 카디널리티가 늘지 않게 합니다. `path`는 `/`, `/api/info`, `/api/chat`, `/healthz`, `/metrics`이고 그 밖의 경로는 모두 `other`입니다. `method`는 `GET`, `POST`이고 그 밖의 메서드는 `other`입니다. `status`는 응답 코드 문자열입니다.
- 모든 응답(`401`, `404` 포함)을 셉니다. 응답을 내보내는 공통 지점에서 상태 코드와 소요 시간을 기록하면 경로마다 코드를 넣지 않아도 됩니다.
- 인증: `/metrics`도 `/healthz`를 뺀 다른 경로와 똑같이 HTTP Basic 인증(사용자 `demo`)을 요구합니다. `/api/info`가 쓰는 기존 인증 확인을 그대로 씁니다.
- 서버는 여러 스레드가 동시에 처리하므로 지표 저장소는 `threading.Lock`으로 보호합니다.
- 문서: `README.md`의 엔드포인트 설명에 `/metrics`를 추가하고 **스크래프 인증 주의사항**을 적습니다. Prometheus가 이 엔드포인트를 수집하려면 스크래프 설정에 Basic 인증 정보를 넣어야 합니다(예: `basic_auth`의 `username: demo`와 `password_file`). 비밀번호를 설정 파일에 평문으로 쓰지 말고 파일이나 시크릿으로 주입하라고 안내합니다.

### 수용 기준 (Acceptance criteria)

- [ ] 인증 없이 `GET /metrics`를 호출하면 `401`이다. 올바른 Basic 인증이면 `200`이고 `Content-Type`은 `text/plain; version=0.0.4; charset=utf-8`이다.
- [ ] 응답에 `# HELP`와 `# TYPE` 줄이 있다: `demo_http_requests_total`은 `counter`, `demo_http_request_duration_seconds`는 `histogram`.
- [ ] `GET /api/info`를 한 번 호출한 뒤 `/metrics`를 읽으면 `demo_http_requests_total{method="GET",path="/api/info",status="200"}` 값이 1 늘어난다.
- [ ] 히스토그램의 `_bucket` 값은 누적(단조 증가)이고, `le="+Inf"` 값은 `_count`와 같다. `_sum`도 있다.
- [ ] 존재하지 않는 경로(예: `/no-such-path`)를 호출해도 `path="other"`로만 집계되어 라벨이 늘어나지 않는다.
- [ ] `GET /healthz`는 여전히 인증 없이 `200`이다.
- [ ] 지표 저장소는 테스트마다 초기화할 수 있고, 새 단위 테스트가 `app/tests/`에 있으며 `python -m unittest discover -s app/tests -v`가 모두 통과한다.
- [ ] `README.md`에 `/metrics` 설명과 스크래프 인증 주의사항이 있다.

### 제약 사항 (Constraints)

- 수정 범위: `app/server.py`, `app/tests/`, `README.md`. 그 밖의 파일은 바꾸지 않습니다.
- Python 3.12 표준 라이브러리만 사용합니다. `prometheus_client` 같은 패키지를 추가하지 않고 `app/requirements.txt`를 바꾸지 않습니다.
- `/healthz`는 인증 없이, 그 밖의 경로(`/metrics` 포함)는 기존 Basic 인증을 유지합니다. 기존 오류 응답 형식과 `LLM_BACKEND=mock` 오프라인 동작도 유지합니다.
- 지표에 비밀, 요청 본문, 질문 내용, `Authorization` 값, 클라이언트 주소를 넣지 않습니다.
- 라벨 조합은 위에 적은 고정된 집합 안에 머물러야 합니다.

### 테스트 방법 (How to test)

```bash
python -m unittest discover -s app/tests -v
```

수동 확인(선택): 서버를 임시 포트로 띄우고 `/api/info`를 한 번 호출한 뒤 지표를 읽습니다.

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

마지막 `curl`(인증 없음)은 `401`을 출력해야 합니다.

### 범위 밖 (Out of scope)

- Azure Managed Prometheus, ACA, AKS 쪽 수집 설정, ServiceMonitor, 대시보드와 알림 규칙
- 프로세스와 런타임 지표(`process_*`, `python_*`), 모델 토큰 사용량 지표
- OpenTelemetry 도입과 새 의존성
- `/metrics`를 인증 없이 여는 것 (Basic 인증을 유지합니다)
- 슬라이드와 `demos/` 문서 수정

# [Demo] POST /api/chat에 클라이언트별 요청 제한(rate limit) 추가

### 배경 (Context)

데모 앱의 `POST /api/chat`은 호출할 때마다 모델 추론 비용이 듭니다. 지금은 호출 횟수에 제한이 없어서, 잘못 만든 스크립트나 반복 클릭이 그대로 비용과 지연으로 이어질 수 있습니다.

- 서버: `app/server.py` (표준 라이브러리 `http.server` 기반, `ThreadingHTTPServer`)
- 테스트: `app/tests/` (`unittest`, 서버를 임시 포트에서 실행하고 `LLM_BACKEND=mock` 사용)
- 문서: `README.md`

### 요구사항 (Requirement)

`POST /api/chat`에만 적용되는 클라이언트별 **토큰 버킷(token bucket)** 요청 제한을 추가합니다. 프로세스 메모리 안에서만 동작하는 단순한 구현이면 충분합니다.

- 환경 변수 `RATE_LIMIT_PER_MINUTE`: 클라이언트 한 곳이 분당 보낼 수 있는 요청 수입니다. 기본값은 `30`입니다. 버킷 용량은 이 값과 같고, 초당 `RATE_LIMIT_PER_MINUTE / 60`개씩 채워지며, 요청 하나가 토큰 하나를 씁니다.
- 토큰이 없으면 HTTP `429`와 기존 오류 응답 형식의 JSON(`{"error": "Rate limit exceeded", "hint": "<한국어 안내>"}`)을 돌려주고, `Retry-After` 헤더에 다음 요청까지 남은 초를 올림한 정수(최소 `1`)로 넣습니다. 예를 들어 `RATE_LIMIT_PER_MINUTE=3`에서 연속 4번째 요청은 약 20초 뒤에 다시 시도하라는 값을 받습니다.
- 클라이언트 식별자는 TCP 연결의 원격 주소(`self.client_address[0]`)입니다. `X-Forwarded-For` 같은 헤더는 위조할 수 있으므로 **읽지 않습니다**.
- 검사 순서: 인증(`401`) → 요청 제한(`429`) → 요청 본문 읽기와 검증 → 모델 호출. 인증에 실패한 요청은 토큰을 쓰지 않습니다.
- `GET /healthz`, `GET /`, `GET /api/info`에는 제한을 걸지 않습니다.
- 서버는 여러 스레드가 동시에 처리하므로 공유 상태는 `threading.Lock`으로 보호합니다. 클라이언트별 버킷 맵이 무한히 커지지 않게, 일정 시간(예: 10분) 쓰이지 않은 항목을 정리하거나 항목 수 상한을 둡니다.
- `RATE_LIMIT_PER_MINUTE=0`이면 제한을 끕니다. 정수가 아니거나 음수이면 경고 로그를 한 줄 남기고 기본값 `30`으로 동작합니다. 환경 변수는 기존 코드처럼 요청을 처리하는 시점에 읽습니다.
- 시간 소스를 바꿔 끼울 수 있게(예: 시계 함수를 인자나 속성으로 받기) 만들어, 테스트가 실제로 기다리지 않아도 되게 합니다.

### 수용 기준 (Acceptance criteria)

- [ ] `RATE_LIMIT_PER_MINUTE=3`일 때 같은 클라이언트가 `POST /api/chat`을 연속 4번 호출하면 앞의 3번은 `200`, 4번째는 `429`와 정수 `Retry-After`(1 이상)를 받는다.
- [ ] 시간이 지나면 토큰이 다시 채워져 요청이 다시 성공한다 (가짜 시계로 검증하며, 테스트에서 `sleep`을 쓰지 않는다).
- [ ] 클라이언트 주소가 다르면 서로의 한도에 영향을 주지 않는다 (버킷 단위 테스트로 검증해도 된다).
- [ ] 인증 없이 호출하면 한도와 관계없이 `401`이고, 이 요청은 토큰을 쓰지 않는다.
- [ ] `RATE_LIMIT_PER_MINUTE=0`이면 제한이 꺼지고, 잘못된 값(`abc`, `-5`)은 기본값 `30`으로 동작한다.
- [ ] `/healthz`, `/`, `/api/info`는 요청 제한의 영향을 받지 않는다.
- [ ] 제한 상태는 테스트마다 초기화할 수 있고, 기존 테스트가 새 제한 때문에 실패하지 않는다.
- [ ] 새 단위 테스트가 `app/tests/`에 있고 `python -m unittest discover -s app/tests -v`가 모두 통과한다.
- [ ] `README.md`의 환경 변수 설명에 `RATE_LIMIT_PER_MINUTE`와 알려진 한계(프록시 뒤에서는 주소가 하나로 보일 수 있음, 상태가 프로세스 메모리에만 있어 replica마다 따로 계산됨)를 적는다.

### 제약 사항 (Constraints)

- 수정 범위: `app/server.py`, `app/tests/`, `README.md`. 그 밖의 파일은 바꾸지 않습니다.
- Python 3.12 표준 라이브러리만 사용합니다. 새 패키지를 추가하지 않고 `app/requirements.txt`를 바꾸지 않습니다.
- 기존 동작을 유지합니다: `/healthz`는 인증 없이, 그 외 경로는 기존 Basic 인증, 기존 오류 응답 형식, `LLM_BACKEND=mock` 오프라인 동작.
- 요청 제한 상태는 서버 인스턴스나 명시적 초기화 함수로 관리해서, 같은 프로세스에서 도는 테스트끼리 영향을 주지 않게 합니다.
- 로그에 비밀, `Authorization` 헤더, 요청 본문을 남기지 않습니다.
- 보안과 가용성에 영향을 주는 변경입니다. PR 설명에 동작 방식과 알려진 한계를 적어서 사람이 꼼꼼히 리뷰할 수 있게 해 주세요.

### 테스트 방법 (How to test)

```bash
python -m unittest discover -s app/tests -v
```

수동 확인(선택): 서버를 임시 포트로 띄우고 4번 호출합니다. 마지막 응답이 `429`이면 정상입니다.

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

### 범위 밖 (Out of scope)

- `X-Forwarded-For` 같은 프록시 헤더 해석, 신뢰할 수 있는 프록시 목록
- Redis 같은 외부 저장소를 쓰는 분산 요청 제한 (replica마다 따로 계산되는 것은 알려진 한계로 문서에만 적습니다)
- 사용자별 한도, IP 차단 목록, 한도를 바꾸는 API
- `POST /api/chat` 이외 경로의 요청 제한
- 슬라이드와 `demos/` 문서 수정

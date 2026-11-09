#!/usr/bin/env bash
# Smoke-tests a running copy of the demo app: health, authentication and one chat round trip.
# CI runs it against the freshly built container; it is just as handy after a deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: DEMO_PASSWORD='<비밀번호>' scripts/smoke-test.sh [앱 주소] [옵션]

실행 중인 데모 앱(로컬 컨테이너, Container Apps, AKS port-forward)이 정상인지 빠르게 확인합니다.
앱 주소를 생략하면 http://127.0.0.1:8080 을 사용합니다.

확인 항목
  1. GET  /healthz     인증 없이 200
  2. GET  /            인증 없이는 401 (WWW-Authenticate 헤더 포함)
  3. GET  /api/info    잘못된 비밀번호는 401, 올바른 비밀번호는 200 과 백엔드/플랫폼/리비전 정보
  4. POST /api/chat    200, answer 와 served_by 포함
  5. POST /api/chat    빈 메시지는 400
  6. 응답 헤더         X-Content-Type-Options: nosniff, Cache-Control: no-store

옵션
  --wait 초                앱이 뜰 때까지 /healthz 를 기다리는 시간 (30)
  --expect-backend 이름    /api/info 의 backend 가 mock 또는 foundry 인지 확인
  -h, --help               도움말

Foundry 백엔드를 가리키면 4번 항목이 모델을 한 번 호출하므로 아주 적은 비용이 듭니다.
EOF
}

URL=http://127.0.0.1:8080
WAIT=30
EXPECT_BACKEND=''

while (($#)); do
  case "$1" in
    --wait)
      WAIT="${2:?--wait 값이 필요합니다}"
      shift
      ;;
    --expect-backend)
      EXPECT_BACKEND="${2:?--expect-backend 값이 필요합니다}"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    -*) die "알 수 없는 옵션: $1 (도움말: --help)" ;;
    *) URL="$1" ;;
  esac
  shift
done

[[ "$URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || die "앱 주소는 https://호스트 형식으로 지정하세요 (경로 없이): $URL"
[[ "$WAIT" =~ ^[0-9]+$ && "$WAIT" -ge 1 ]] || die "--wait 는 1 이상의 정수여야 합니다."
[[ -z "$EXPECT_BACKEND" || "$EXPECT_BACKEND" == mock || "$EXPECT_BACKEND" == foundry ]] || die "--expect-backend 는 mock 또는 foundry 여야 합니다."
: "${DEMO_PASSWORD:?DEMO_PASSWORD 환경 변수에 데모 비밀번호를 지정하세요}"
require_commands curl python3
URL="${URL%/}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
failures=0
checks=0

pass() {
  checks=$((checks + 1))
  printf '  ✓ %s\n' "$1"
}
fail() {
  checks=$((checks + 1))
  failures=$((failures + 1))
  printf '  ✗ %s\n' "$1" >&2
}
expect() { # description expected actual
  if [[ "$2" == "$3" ]]; then pass "$1"; else fail "$1 (기대: $2, 실제: ${3:-없음})"; fi
}
assert() { # description command...
  local description="$1"
  shift
  if "$@"; then pass "$description"; else fail "$description"; fi
}
all_set() { # succeeds when every argument is non-empty
  local value
  for value in "$@"; do [[ -n "$value" ]] || return 1; done
}

# request METHOD PATH [CURL_ARGS...]: unauthenticated; leaves headers/body in $work and prints the status code.
request() {
  local method="$1" path="$2"
  shift 2
  curl --silent --show-error --max-time 30 --request "$method" --output "$work/body" \
    --dump-header "$work/headers" --write-out '%{http_code}' "$@" "$URL$path"
}
# request_auth METHOD PATH [CURL_ARGS...]: same, with the demo credentials.
request_auth() {
  local method="$1" path="$2"
  shift 2
  curl_demo "$URL$path" --request "$method" --output "$work/body" \
    --dump-header "$work/headers" --write-out '%{http_code}' "$@"
}
json_get() { # KEY... : prints a value of the last response body, or nothing
  python3 - "$work/body" "$@" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        value = json.load(handle)
    for key in sys.argv[2:]:
        value = value[key]
    print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
except (OSError, ValueError, KeyError, TypeError):
    pass
PY
}
has_header() { grep -qi "^$1:[[:space:]]*$2" "$work/headers"; }

printf '대상: %s\n' "$URL"
wait_for_http "$URL/healthz" "$WAIT" 1 || die "$URL/healthz 가 ${WAIT}초 안에 응답하지 않았습니다."

expect 'GET /healthz → 200' 200 "$(request GET /healthz)"
expect '  본문 status' ok "$(json_get status)"

expect 'GET / 인증 없이 → 401' 401 "$(request GET /)"
assert '  WWW-Authenticate: Basic 헤더' has_header www-authenticate Basic

expect 'GET /api/info 잘못된 비밀번호 → 401' 401 "$(request GET /api/info --user 'demo:wrong-password')"

expect 'GET /api/info 인증 → 200' 200 "$(request_auth GET /api/info)"
backend="$(json_get backend)"
platform="$(json_get platform)"
revision="$(json_get revision)"
version="$(json_get version)"
assert "  backend=${backend:-?} platform=${platform:-?} version=${version:-?} revision=${revision:--}" \
  all_set "$backend" "$platform" "$version"
[[ -z "$EXPECT_BACKEND" ]] || expect "  backend 가 $EXPECT_BACKEND" "$EXPECT_BACKEND" "$backend"
assert '  X-Content-Type-Options: nosniff' has_header x-content-type-options nosniff
assert '  Cache-Control: no-store' has_header cache-control no-store

expect 'POST /api/chat → 200' 200 "$(request_auth POST /api/chat --header 'Content-Type: application/json' \
  --data '{"message":"안녕하세요. 한 문장으로 자기소개를 해 주세요."}')"
assert '  answer 가 비어 있지 않음' all_set "$(json_get answer)"
instance="$(json_get served_by instance)"
assert "  served_by.instance=${instance:-?}" all_set "$instance"

expect 'POST /api/chat 빈 메시지 → 400' 400 "$(request_auth POST /api/chat --header 'Content-Type: application/json' --data '{"message":""}')"

if ((failures > 0)); then
  printf '\n실패: %d / %d 항목\n' "$failures" "$checks" >&2
  exit 1
fi
printf '\n모든 확인(%d개)을 통과했습니다.\n' "$checks"

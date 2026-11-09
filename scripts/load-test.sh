#!/usr/bin/env bash
# Generates concurrent load against the demo app to show autoscaling on Azure Container Apps.
# (For AKS the manifests include an in-cluster load generator; see demos/06-aks.)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: DEMO_PASSWORD='<비밀번호>' scripts/load-test.sh --url <앱 주소> [옵션]

동시 요청을 보내 Container Apps 가 복제본을 늘리는 모습을 보여 줍니다.
mock 백엔드는 응답마다 MOCK_LATENCY_MS(기본 1초)만큼 기다리므로 동시 요청이 쌓여 스케일 아웃이 일어납니다.

옵션
  --url URL            앱 주소 (예: https://cloud-copilot-demo.<환경>.koreacentral.azurecontainerapps.io)
  --duration 초        부하를 거는 시간 (60, 최대 900)
  --concurrency 개수   동시에 요청하는 워커 수 (20, 최대 200)
  --path 경로          요청 경로 (/api/chat). /healthz 는 인증 없이 쓸 수 있는 가벼운 경로입니다
  --force              Foundry 백엔드에도 부하를 겁니다. 호출마다 비용이 발생하니 주의하세요
  -h, --help           도움말

기본 /api/chat 은 mock 백엔드일 때만 실행됩니다. 요청은 매번 새 연결로 보내지만 사용자 비밀번호는
명령줄에 노출하지 않고 권한 600 임시 파일로 curl 에 전달합니다.
EOF
}

URL=''
DURATION=60
CONCURRENCY=20
REQUEST_PATH=/api/chat
FORCE=0

while (($#)); do
  case "$1" in
    --url)
      URL="${2:?--url 값이 필요합니다}"
      shift
      ;;
    --duration)
      DURATION="${2:?--duration 값이 필요합니다}"
      shift
      ;;
    --concurrency)
      CONCURRENCY="${2:?--concurrency 값이 필요합니다}"
      shift
      ;;
    --path)
      REQUEST_PATH="${2:?--path 값이 필요합니다}"
      shift
      ;;
    --force) FORCE=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) die "알 수 없는 옵션: $1 (도움말: --help)" ;;
  esac
  shift
done

[[ "$URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || die "--url 에는 https://호스트 형식의 주소를 지정하세요 (경로 없이)."
[[ "$DURATION" =~ ^[0-9]+$ && "$DURATION" -ge 1 && "$DURATION" -le 900 ]] || die "--duration 은 1~900 이어야 합니다."
[[ "$CONCURRENCY" =~ ^[0-9]+$ && "$CONCURRENCY" -ge 1 && "$CONCURRENCY" -le 200 ]] || die "--concurrency 는 1~200 이어야 합니다."
[[ "$REQUEST_PATH" =~ ^/[A-Za-z0-9/_.-]*$ ]] || die "--path 형식이 올바르지 않습니다."
require_commands curl python3

URL="${URL%/}"
curl_args=()
if [[ "$REQUEST_PATH" == /api/chat ]]; then
  curl_args=(--request POST --header 'Content-Type: application/json' --data '{"message":"부하 테스트 요청입니다. 한 문장으로 답해 주세요."}')
fi

if [[ "$REQUEST_PATH" != /healthz ]]; then
  [[ -n "${DEMO_PASSWORD:-}" ]] || die "DEMO_PASSWORD 환경 변수가 필요합니다."
  info="$(curl_demo "$URL/api/info" --fail 2>/dev/null || true)"
  [[ -n "$info" ]] || die "$URL/api/info 에 접근하지 못했습니다. 주소와 비밀번호를 확인하세요."
  backend="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("backend", ""))' "$info")"
  if [[ "$backend" != mock && "$FORCE" != 1 ]]; then
    die "백엔드가 '$backend' 입니다. 모델 호출 비용이 발생하므로 --force 없이는 부하를 걸지 않습니다."
  fi
fi

work_dir="$(mktemp -d)"
config="$work_dir/curl.conf"
(
  umask 077
  if [[ "$REQUEST_PATH" == /healthz ]]; then
    : >"$config"
  else
    credentials="demo:$DEMO_PASSWORD"
    credentials="${credentials//\\/\\\\}"
    credentials="${credentials//\"/\\\"}"
    printf 'user = "%s"\n' "$credentials" >"$config"
  fi
)
pids=()
cleanup() {
  ((${#pids[@]} == 0)) || kill "${pids[@]}" 2>/dev/null || true
  rm -rf "$work_dir"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

worker() {
  local results="$1" deadline="$2"
  while ((SECONDS < deadline)); do
    curl --silent --output /dev/null --max-time 30 --config "$config" \
      --write-out '%{http_code} %{time_total}\n' "${curl_args[@]}" "$URL$REQUEST_PATH" >>"$results" || true
  done
}

log "부하 시작: $URL$REQUEST_PATH, 동시 $CONCURRENCY, $DURATION 초"
deadline=$((SECONDS + DURATION))
for ((i = 0; i < CONCURRENCY; i++)); do
  worker "$work_dir/worker-$i.txt" "$deadline" &
  pids+=("$!")
done

while ((SECONDS < deadline)); do
  remaining=$((deadline - SECONDS))
  sleep $((remaining < 5 ? remaining : 5))
  done_count="$(cat "$work_dir"/worker-*.txt 2>/dev/null | wc -l)"
  printf '  %3d초 경과, 요청 %s 건\n' "$((DURATION - (deadline - SECONDS)))" "$done_count" >&2
done
wait "${pids[@]}" 2>/dev/null || true
pids=()

cat "$work_dir"/worker-*.txt | python3 -c '
import collections
import sys

duration = int(sys.argv[1])
codes = collections.Counter()
times = []
for line in sys.stdin:
    parts = line.split()
    if len(parts) != 2:
        continue
    codes[parts[0]] += 1
    times.append(float(parts[1]))
total = sum(codes.values())
if not total:
    sys.exit("응답이 하나도 없습니다. 주소와 네트워크를 확인하세요.")
times.sort()
print()
print(f"요청 {total}건, 초당 약 {total / duration:.1f}건")
for code, count in sorted(codes.items()):
    print(f"  HTTP {code}: {count}건")
print(f"응답 시간 중앙값 {times[len(times) // 2]:.2f}초, 95백분위 {times[max(0, int(len(times) * 0.95) - 1)]:.2f}초")
' "$DURATION"

cat <<'EOF'

복제본 수 확인 (부하가 끝나면 몇 분 뒤 다시 줄어듭니다):
  az containerapp replica list --resource-group <리소스 그룹> --name <앱 이름> --output table
EOF

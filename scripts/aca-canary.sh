#!/usr/bin/env bash
# Blue/green and canary releases on Azure Container Apps with revision labels
# (the official blue-green flow: https://learn.microsoft.com/azure/container-apps/blue-green-deployment).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: scripts/aca-canary.sh <명령> [인자]

Container Apps 의 리비전과 레이블(blue/green)로 무중단 배포와 카나리를 시연합니다.
앱은 scripts/deploy-aca.sh 로 먼저 배포해 두세요.

명령
  status           트래픽 분포, 리비전, 레이블 주소를 보여 줍니다
  deploy <버전>    새 리비전(예: v2)을 만들어 비어 있는 레이블에 붙입니다. 트래픽은 0% 입니다
  canary <퍼센트>  새 리비전에 해당 비율(0~100)의 트래픽을 보냅니다
  promote          새 리비전으로 100% 전환합니다
  rollback         이전 리비전으로 100% 되돌립니다
  probe [횟수]     운영 주소로 /api/info 를 보내 어떤 버전이 몇 번 응답했는지 셉니다 (기본 20회)
  urls             운영 주소와 레이블 주소를 보여 줍니다

환경 변수 (괄호는 기본값)
  RESOURCE_GROUP  리소스 그룹 (rg-cloud-copilot-aca)
  APP_NAME        컨테이너 앱 이름 (cloud-copilot-demo)
  DEMO_PASSWORD   probe 와 deploy 의 상태 확인에 필요한 데모 UI 비밀번호

처음 deploy 를 실행하면 현재 리비전을 100% 로 고정하고 blue 레이블을 붙입니다.
이후에는 100% 를 받지 않는 쪽 레이블(blue 또는 green)로 새 리비전이 들어갑니다.
scripts/deploy-aca.sh 를 다시 실행하면 이 분할이 초기화됩니다.
EOF
}

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cloud-copilot-aca}"
APP_NAME="${APP_NAME:-cloud-copilot-demo}"

command="${1:-}"
case "$command" in
  -h | --help | help)
    usage
    exit 0
    ;;
  status | deploy | canary | promote | rollback | probe | urls) shift ;;
  '')
    usage >&2
    exit 1
    ;;
  *) die "알 수 없는 명령: $command (도움말: --help)" ;;
esac

require_commands python3 curl
require_azure_login
ensure_containerapp_extension

az_app() {
  az containerapp "$@" --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors
}

# Sets fqdn, domain and the labeled revisions as "label<TAB>revision<TAB>weight" rows, newest revision first.
load_state() {
  fqdn="$(az_app show --query properties.configuration.ingress.fqdn --output tsv 2>/dev/null || true)"
  [[ -n "$fqdn" ]] || die "컨테이너 앱 $APP_NAME 을 $RESOURCE_GROUP 에서 찾지 못했습니다. 먼저 scripts/deploy-aca.sh 를 실행하세요."
  domain="${fqdn#*.}"
  traffic_json="$(az containerapp ingress traffic show --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors --output json)"
  revisions_json="$(az containerapp revision list --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors --output json)"
  labeled=()
  while IFS= read -r row; do
    [[ -z "$row" ]] || labeled+=("$row")
  done < <(
    python3 - "$traffic_json" "$revisions_json" <<'PY'
import json
import sys

traffic = json.loads(sys.argv[1])
revisions = {item["name"]: item for item in json.loads(sys.argv[2])}
rows = []
for entry in traffic:
    label, name = entry.get("label"), entry.get("revisionName")
    if label and name:
        created = revisions.get(name, {}).get("properties", {}).get("createdTime", "")
        rows.append((created, label, name, int(entry.get("weight", 0))))
for _created, label, name, weight in sorted(rows, reverse=True):
    print(f"{label}\t{name}\t{weight}")
PY
  )
}

label_url() { printf 'https://%s---%s.%s' "$APP_NAME" "$1" "$domain"; }

# Prints the revision that currently receives most of the traffic.
primary_revision() {
  python3 - "$traffic_json" "$(az_app show --query properties.latestRevisionName --output tsv)" <<'PY'
import json
import sys

traffic = [e for e in json.loads(sys.argv[1]) if e.get("revisionName")]
print(max(traffic, key=lambda e: int(e.get("weight", 0)))["revisionName"] if traffic else sys.argv[2])
PY
}

show_versions() {
  [[ -n "${DEMO_PASSWORD:-}" ]] || return 0
  local url="$1" info
  info="$(curl_demo "$url/api/info" --fail 2>/dev/null || true)"
  [[ -n "$info" ]] || {
    printf '    (응답 없음)\n'
    return 0
  }
  python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("    버전=%s 리비전=%s 백엔드=%s" % (d.get("version"), d.get("revision"), d.get("backend")))' "$info"
}

set_split() {
  local newer_percent="$1" newer older
  ((${#labeled[@]} >= 2)) || die "비교할 리비전이 둘이 아닙니다. 먼저 'deploy <버전>' 을 실행하세요."
  IFS=$'\t' read -r newer _ <<<"${labeled[0]}"
  IFS=$'\t' read -r older _ <<<"${labeled[1]}"
  log "트래픽 분할: $newer(새 리비전) $newer_percent% / $older(이전 리비전) $((100 - newer_percent))%"
  az containerapp ingress traffic set --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors \
    --label-weight "$newer=$newer_percent" "$older=$((100 - newer_percent))" --output none
}

cmd_status() {
  load_state
  log "트래픽 분포"
  az containerapp ingress traffic show --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors --output table
  log "리비전"
  az containerapp revision list --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors --output table \
    --query "[].{Name:name, Active:properties.active, Traffic:properties.trafficWeight, Created:properties.createdTime}"
  cmd_urls_body
}

cmd_urls_body() {
  printf '\n운영 주소 : https://%s\n' "$fqdn"
  show_versions "https://$fqdn"
  local row label revision weight
  for row in "${labeled[@]}"; do
    IFS=$'\t' read -r label revision weight <<<"$row"
    printf '레이블 %-5s: %s  (%s, %s%%)\n' "$label" "$(label_url "$label")" "$revision" "$weight"
    show_versions "$(label_url "$label")"
  done
}

cmd_urls() {
  load_state
  cmd_urls_body
}

cmd_deploy() {
  local version="${1:-}"
  [[ -n "$version" ]] || die "새 버전 이름을 지정하세요. 예: scripts/aca-canary.sh deploy v2"
  [[ "$version" =~ ^[a-z][a-z0-9-]{0,19}$ && "$version" != *--* && "$version" != *- ]] ||
    die "버전 이름은 소문자로 시작하는 소문자/숫자/하이픈 20자 이내여야 합니다(연속 하이픈과 끝 하이픈 불가)."
  local new_revision="$APP_NAME--$version"

  load_state
  [[ "$(az_app show --query properties.configuration.activeRevisionsMode --output tsv)" == Multiple ]] ||
    die "이 앱은 다중 리비전 모드가 아닙니다. scripts/deploy-aca.sh 로 배포한 앱에서 사용하세요."
  if [[ "$(az_app revision list --query "[?name=='$new_revision'] | length(@)" --output tsv)" != 0 ]]; then
    die "리비전 $new_revision 이 이미 있습니다. 새 버전 이름을 사용하세요."
  fi

  local prod_label='' best=-1 row label revision weight
  if ((${#labeled[@]} == 0)); then
    revision="$(primary_revision)"
    log "처음 실행: 현재 리비전 $revision 을 100% 로 고정하고 blue 레이블을 붙입니다."
    az containerapp ingress traffic set --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" --only-show-errors \
      --revision-weight "$revision=100" --output none
    az_app revision label add --label blue --revision "$revision" --yes --output none
    prod_label=blue
  else
    for row in "${labeled[@]}"; do
      IFS=$'\t' read -r label revision weight <<<"$row"
      if ((weight > best)); then
        best=$weight
        prod_label=$label
      fi
    done
  fi

  local target
  case "$prod_label" in
    blue) target=green ;;
    green) target=blue ;;
    *) die "지원하지 않는 레이블입니다: $prod_label (blue 와 green 만 사용합니다)" ;;
  esac
  for row in "${labeled[@]}"; do
    IFS=$'\t' read -r label revision weight <<<"$row"
    if [[ "$label" == "$target" ]] && ((weight > 0)); then
      die "$target 레이블이 이미 ${weight}% 의 트래픽을 받고 있습니다. promote 또는 rollback 으로 정리한 뒤 deploy 하세요."
    fi
  done

  log "새 리비전 만드는 중: $new_revision (APP_VERSION=$version)"
  az_app update --revision-suffix "$version" --set-env-vars "APP_VERSION=$version" --output none
  # --yes moves a label that still sits on an older revision (0% traffic) instead of prompting.
  az_app revision label add --label "$target" --revision "$new_revision" --yes --output none

  local url
  url="$(label_url "$target")"
  log "새 리비전이 응답하길 기다리는 중... ($url)"
  wait_for_http "$url/healthz" 24 5 || warn "아직 응답하지 않습니다. 잠시 뒤 status 로 확인하세요."

  cat <<EOF

새 리비전 $new_revision 을 $target 레이블에 연결했습니다. 운영 트래픽은 아직 $prod_label 이 100% 받습니다.
  확인 주소: $url
다음 단계
  scripts/aca-canary.sh canary 10   # 새 리비전에 10%
  scripts/aca-canary.sh promote     # 새 리비전으로 100%
  scripts/aca-canary.sh rollback    # 이전 리비전으로 100%
EOF
}

cmd_canary() {
  local percent="${1:-}"
  [[ "$percent" =~ ^[0-9]+$ && "$percent" -le 100 ]] || die "퍼센트는 0~100 사이의 정수여야 합니다. 예: scripts/aca-canary.sh canary 10"
  load_state
  set_split "$percent"
}

cmd_promote() {
  load_state
  set_split 100
}

cmd_rollback() {
  load_state
  set_split 0
}

cmd_probe() {
  local count="${1:-20}"
  [[ "$count" =~ ^[0-9]+$ && "$count" -ge 1 && "$count" -le 500 ]] || die "횟수는 1~500 사이의 정수여야 합니다."
  [[ -n "${DEMO_PASSWORD:-}" ]] || die "DEMO_PASSWORD 환경 변수가 필요합니다."
  load_state
  log "https://$fqdn 로 /api/info 를 $count 번 요청합니다."
  local i
  for ((i = 0; i < count; i++)); do
    curl_demo "https://$fqdn/api/info" --fail 2>/dev/null || printf '{}'
    printf '\n'
  done | python3 -c '
import collections
import json
import sys

counts = collections.Counter()
for line in sys.stdin:
    try:
        data = json.loads(line)
    except ValueError:
        continue
    counts[(data.get("version", "?"), data.get("revision", "?"))] += 1
total = sum(counts.values())
for (version, revision), n in counts.most_common():
    print(f"  {version:<10} {revision:<34} {n:>4}회  {100 * n / total:5.1f}%  {chr(9608) * round(30 * n / total)}")
print(f"  합계 {total}회")
'
}

"cmd_$command" "$@"

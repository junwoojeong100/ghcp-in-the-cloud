#!/usr/bin/env bash
# Deploys the demo app to Azure Container Apps (infra/aca/main.bicep) in three steps:
# 1) registry + identity + environment, 2) image build in ACR, 3) the container app.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: scripts/deploy-aca.sh [--yes]

Azure Container Apps 에 데모 앱을 배포합니다. 기본은 mock 백엔드라서 Foundry 없이도 동작합니다.
Foundry 의 모델(기본 gpt-6.1-sol)을 쓰려면 먼저 scripts/deploy-foundry.sh 를 실행하고
`source .azure/foundry.env` 한 뒤 이 스크립트를 실행하세요.

환경 변수 (괄호는 기본값)
  RESOURCE_GROUP         리소스 그룹 (rg-cloud-copilot-aca)
  LOCATION               리전 (koreacentral)
  NAME_PREFIX            리소스 이름 접두사, 소문자/숫자 (ccd)
  APP_NAME               컨테이너 앱 이름 (cloud-copilot-demo)
  IMAGE_TAG              이미지 태그이자 앱 버전 (v1)
  REVISION_SUFFIX        앱을 처음 만들 때의 리비전 이름 접미사 (v1)
  DEMO_PASSWORD          데모 UI 비밀번호 (지정하지 않으면 자동 생성해 마지막에 한 번 보여 줍니다)
  MOCK_LATENCY_MS        mock 응답 지연, 스케일 아웃을 보여 주려고 기본 1000
  MIN_REPLICAS           최소 복제본 수 (0, 유휴 시 0 으로 줄어듭니다)
  MAX_REPLICAS           최대 복제본 수 (5)
  FOUNDRY_RESOURCE       지정하면 mock 대신 이 Foundry 리소스의 모델을 호출합니다
  FOUNDRY_RESOURCE_GROUP Foundry 리소스 그룹 (RESOURCE_GROUP 과 같다고 봅니다)
  FOUNDRY_MODEL          모델 배포 이름 (gpt-6.1-sol)
  FOUNDRY_EFFORT         low | medium | high | xhigh | max (max)

옵션
  -y, --yes   확인 질문 없이 진행
  -h, --help  도움말

같은 스크립트를 다시 실행하면 트래픽 분할(카나리)이 100% 최신 리비전으로 초기화됩니다.
정리: scripts/cleanup.sh aca
EOF
}

while (($#)); do
  case "$1" in
    -y | --yes) ASSUME_YES=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) die "알 수 없는 옵션: $1 (도움말: --help)" ;;
  esac
  shift
done

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cloud-copilot-aca}"
LOCATION="${LOCATION:-koreacentral}"
NAME_PREFIX="${NAME_PREFIX:-ccd}"
APP_NAME="${APP_NAME:-cloud-copilot-demo}"
IMAGE_TAG="${IMAGE_TAG:-v1}"
REVISION_SUFFIX="${REVISION_SUFFIX:-v1}"
MOCK_LATENCY_MS="${MOCK_LATENCY_MS:-1000}"
MIN_REPLICAS="${MIN_REPLICAS:-0}"
MAX_REPLICAS="${MAX_REPLICAS:-5}"
FOUNDRY_RESOURCE="${FOUNDRY_RESOURCE:-}"
FOUNDRY_RESOURCE_GROUP="${FOUNDRY_RESOURCE_GROUP:-$RESOURCE_GROUP}"
FOUNDRY_MODEL="${FOUNDRY_MODEL:-gpt-6.1-sol}"
FOUNDRY_EFFORT="${FOUNDRY_EFFORT:-max}"

[[ "$NAME_PREFIX" =~ ^[a-z][a-z0-9]{1,11}$ ]] || die "NAME_PREFIX 는 소문자/숫자 2~12자여야 합니다."
[[ "$APP_NAME" =~ ^[a-z][a-z0-9-]{0,30}[a-z0-9]$ ]] || die "APP_NAME 형식이 올바르지 않습니다: $APP_NAME"
[[ "$IMAGE_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]] || die "IMAGE_TAG 형식이 올바르지 않습니다: $IMAGE_TAG"
[[ "$REVISION_SUFFIX" =~ ^[a-z][a-z0-9-]{0,19}$ && "$REVISION_SUFFIX" != *--* && "$REVISION_SUFFIX" != *- ]] || die "REVISION_SUFFIX 형식이 올바르지 않습니다: $REVISION_SUFFIX"
[[ "$MOCK_LATENCY_MS" =~ ^[0-9]+$ && "$MOCK_LATENCY_MS" -le 10000 ]] || die "MOCK_LATENCY_MS 는 0~10000 이어야 합니다."
[[ "$MIN_REPLICAS" =~ ^[0-9]+$ && "$MAX_REPLICAS" =~ ^[0-9]+$ && "$MAX_REPLICAS" -ge 1 && "$MAX_REPLICAS" -ge "$MIN_REPLICAS" ]] || die "MIN_REPLICAS/MAX_REPLICAS 값이 올바르지 않습니다."
[[ -z "$FOUNDRY_RESOURCE" || "$FOUNDRY_RESOURCE" =~ ^[A-Za-z0-9][A-Za-z0-9-]{1,63}$ ]] || die "FOUNDRY_RESOURCE 는 호스트 이름이 아니라 리소스 이름이어야 합니다."

require_commands curl python3
require_azure_login

password_generated=0
if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  DEMO_PASSWORD="$(random_password)"
  password_generated=1
fi
export DEMO_PASSWORD

if [[ -n "$FOUNDRY_RESOURCE" ]]; then
  backend="Foundry ($FOUNDRY_RESOURCE / $FOUNDRY_MODEL, effort $FOUNDRY_EFFORT)"
else
  backend="mock (Azure 모델 호출 없음)"
fi
cat >&2 <<EOF

구독              : $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)
리소스 그룹 / 리전 : $RESOURCE_GROUP / $LOCATION
이미지 태그       : $IMAGE_TAG
백엔드            : $backend
복제본            : $MIN_REPLICAS ~ $MAX_REPLICAS

EOF
confirm "Azure 리소스를 만듭니다. 계속할까요?" || die "취소했습니다."

ensure_providers Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.ManagedIdentity

log "리소스 그룹 생성: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags demo=ghcp-in-the-cloud \
  --only-show-errors --output none

# Phase 1 creates only the registry, identity and environment; phase 2 adds the app once the image exists.
deploy_phase() {
  local deploy_app="$1" revision_suffix="${2:-}" parameters_file name
  parameters_file="$(mktemp)"
  name="aca-$([[ "$deploy_app" == true ]] && echo app || echo infra)-$(date +%Y%m%d%H%M%S)"
  write_parameters "$parameters_file" \
    "namePrefix=$NAME_PREFIX" \
    "location=$LOCATION" \
    "appName=$APP_NAME" \
    "deployApp:=$deploy_app" \
    "imageTag=$IMAGE_TAG" \
    "revisionSuffix=$revision_suffix" \
    "demoPassword@DEMO_PASSWORD" \
    "foundryResource=$FOUNDRY_RESOURCE" \
    "foundryResourceGroup=$FOUNDRY_RESOURCE_GROUP" \
    "foundryModel=$FOUNDRY_MODEL" \
    "foundryEffort=$FOUNDRY_EFFORT" \
    "mockLatencyMs:=$MOCK_LATENCY_MS" \
    "minReplicas:=$MIN_REPLICAS" \
    "maxReplicas:=$MAX_REPLICAS"
  if deploy_template "$RESOURCE_GROUP" "$name" "$REPO_ROOT/infra/aca/main.bicep" "$parameters_file"; then
    rm -f "$parameters_file"
    DEPLOYMENT_NAME="$name"
  else
    rm -f "$parameters_file"
    return 1
  fi
}

log "1/3 레지스트리, 관리 ID, Container Apps 환경 배포 중..."
deploy_phase false
registry_name="$(deployment_output "$RESOURCE_GROUP" "$DEPLOYMENT_NAME" registryName)"
login_server="$(deployment_output "$RESOURCE_GROUP" "$DEPLOYMENT_NAME" registryLoginServer)"

log "2/3 이미지 빌드"
build_and_push_image "$REPO_ROOT" "$registry_name" "$login_server" "$IMAGE_TAG"

log "3/3 컨테이너 앱 배포 중..."
app_count="$(az resource list --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.App/containerApps \
  --query "[?name=='$APP_NAME'] | length(@)" --output tsv)"
initial_suffix=''
[[ "$app_count" == 0 ]] && initial_suffix="$REVISION_SUFFIX"
# 실행 중인 복제본은 시작할 때만 Secret 을 읽으므로, 비밀번호가 바뀌면 아래에서 활성 리비전을 다시 시작합니다.
previous_password=''
if [[ "$app_count" != 0 ]]; then
  previous_password="$(az containerapp secret show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" \
    --secret-name demo-password --query value --output tsv --only-show-errors 2>/dev/null || true)"
fi
deploy_phase true "$initial_suffix"
app_url="$(deployment_output "$RESOURCE_GROUP" "$DEPLOYMENT_NAME" appUrl)"
revision="$(deployment_output "$RESOURCE_GROUP" "$DEPLOYMENT_NAME" latestRevisionName)"

if [[ -n "$previous_password" && "$previous_password" != "$DEMO_PASSWORD" ]]; then
  log "비밀번호가 바뀌어 활성 리비전을 다시 시작합니다."
  while IFS= read -r active_revision; do
    [[ -n "$active_revision" ]] || continue
    az containerapp revision restart --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" \
      --revision "$active_revision" --only-show-errors --output none ||
      warn "리비전 $active_revision 을 다시 시작하지 못했습니다. az containerapp revision restart 로 직접 다시 시작하세요."
  done < <(az containerapp revision list --resource-group "$RESOURCE_GROUP" --name "$APP_NAME" \
    --query "[?properties.active].name" --output tsv --only-show-errors)
fi

log "앱이 응답하길 기다리는 중... (최소 복제본이 0 이면 첫 요청에 시간이 걸립니다)"
wait_for_http "$app_url/healthz" 36 5 || die "앱이 응답하지 않습니다: $app_url/healthz (az containerapp logs show -n $APP_NAME -g $RESOURCE_GROUP)"
info="$(curl_demo "$app_url/api/info" --fail 2>/dev/null || true)"

cat <<EOF

배포를 마쳤습니다.
  URL         : $app_url
  사용자      : demo
  비밀번호    : $([[ "$password_generated" == 1 ]] && echo "$DEMO_PASSWORD" || echo "(지정한 DEMO_PASSWORD)")
  리비전      : $revision
  /api/info   : ${info:-확인하지 못했습니다}

다음 단계
  카나리 시연 : scripts/aca-canary.sh status
  부하 시연   : DEMO_PASSWORD='<비밀번호>' scripts/load-test.sh --url $app_url
  정리        : scripts/cleanup.sh aca
EOF
if [[ "$password_generated" == 1 ]]; then
  cat <<EOF

비밀번호를 잊었다면:
  az containerapp secret show --name $APP_NAME --resource-group $RESOURCE_GROUP --secret-name demo-password --query value --output tsv
EOF
fi

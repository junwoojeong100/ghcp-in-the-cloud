#!/usr/bin/env bash
# Deploys Microsoft Foundry + a Claude model (infra/foundry/main.bicep).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: CLAUDE_ORGANIZATION_NAME="<조직 이름>" scripts/deploy-foundry.sh [--yes]

Microsoft Foundry 계정, 프로젝트, Claude 모델 배포를 만듭니다.
배포 이름은 모델 이름(기본 claude-sonnet-5-5)과 같아서 앱의 기본값(FOUNDRY_MODEL)과 맞습니다.

필수 환경 변수
  CLAUDE_ORGANIZATION_NAME  Anthropic 약관에 제출할 조직 이름

선택 환경 변수 (괄호는 기본값)
  RESOURCE_GROUP       리소스 그룹 (rg-cloud-copilot-foundry)
  LOCATION             eastus2 | swedencentral | westus2 (swedencentral)
  MODEL_NAME           배포할 Claude 모델 (claude-sonnet-5-5)
  CAPACITY             GlobalStandard 용량, 1K TPM 단위 (25)
  CLAUDE_COUNTRY_CODE  조직의 국가 코드 두 글자 (US)
  CLAUDE_INDUSTRY      technology | finance | healthcare | education | retail |
                       manufacturing | government | media | other (technology)
  DISABLE_LOCAL_AUTH   true 면 API 키를 끄고 Microsoft Entra ID만 허용 (false)
  PRINCIPAL_ID         추론 권한(Cognitive Services User)을 받을 사용자 객체 ID (로그인한 사용자)
  PRINCIPAL_TYPE       User | ServicePrincipal | Group (User)

옵션
  -y, --yes  확인 질문 없이 진행
  -h, --help 도움말

주의: Claude 배포는 Anthropic 상용 약관에 동의하는 것으로 처리되며,
Enterprise 또는 MCA-E 구독이 필요합니다. 정리할 때는 scripts/cleanup.sh foundry 를 사용하세요.
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

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cloud-copilot-foundry}"
LOCATION="${LOCATION:-swedencentral}"
MODEL_NAME="${MODEL_NAME:-claude-sonnet-5-5}"
CAPACITY="${CAPACITY:-25}"
CLAUDE_COUNTRY_CODE="${CLAUDE_COUNTRY_CODE:-US}"
CLAUDE_INDUSTRY="${CLAUDE_INDUSTRY:-technology}"
DISABLE_LOCAL_AUTH="${DISABLE_LOCAL_AUTH:-false}"
CLAUDE_ORGANIZATION_NAME="${CLAUDE_ORGANIZATION_NAME:-}"

[[ -n "$CLAUDE_ORGANIZATION_NAME" ]] || die "CLAUDE_ORGANIZATION_NAME 을 지정하세요. 예: CLAUDE_ORGANIZATION_NAME=\"Contoso\" $0"
[[ "$CAPACITY" =~ ^[0-9]+$ && "$CAPACITY" -ge 1 ]] || die "CAPACITY 는 1 이상의 정수여야 합니다."
[[ "$CLAUDE_COUNTRY_CODE" =~ ^[A-Za-z]{2}$ ]] || die "CLAUDE_COUNTRY_CODE 는 두 글자여야 합니다. 예: KR"
[[ "$DISABLE_LOCAL_AUTH" == true || "$DISABLE_LOCAL_AUTH" == false ]] || die "DISABLE_LOCAL_AUTH 는 true 또는 false 여야 합니다."
[[ "$MODEL_NAME" =~ ^[A-Za-z0-9._-]+$ ]] || die "MODEL_NAME 형식이 올바르지 않습니다: $MODEL_NAME"
export CLAUDE_ORGANIZATION_NAME

require_azure_login
detect_principal

cat >&2 <<EOF

구독    : $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)
리소스 그룹 / 리전 : $RESOURCE_GROUP / $LOCATION
모델 배포 : $MODEL_NAME (GlobalStandard, 용량 $CAPACITY)

중요: 이 배포는 Anthropic 상용 약관(https://www.anthropic.com/legal/commercial-terms)에
      아래 정보로 동의하는 것으로 처리됩니다.
  조직 이름 : $CLAUDE_ORGANIZATION_NAME
  국가 코드 : ${CLAUDE_COUNTRY_CODE^^}
  업종      : $CLAUDE_INDUSTRY

EOF
confirm "계속할까요?" || die "취소했습니다."

log "리소스 그룹 생성: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags demo=ghcp-in-the-cloud \
  --only-show-errors --output none

parameters_file="$(mktemp)"
trap 'rm -f "$parameters_file"' EXIT
write_parameters "$parameters_file" \
  "location=$LOCATION" \
  "modelName=$MODEL_NAME" \
  "capacity:=$CAPACITY" \
  "claudeOrganizationName@CLAUDE_ORGANIZATION_NAME" \
  "claudeCountryCode=${CLAUDE_COUNTRY_CODE^^}" \
  "claudeIndustry=$CLAUDE_INDUSTRY" \
  "principalId=${PRINCIPAL_ID:-}" \
  "principalType=${PRINCIPAL_TYPE:-User}" \
  "disableLocalAuth:=$DISABLE_LOCAL_AUTH"

deployment_name="foundry-$(date +%Y%m%d%H%M%S)"
log "Foundry 배포 중... (모델 배포까지 몇 분 걸릴 수 있습니다)"
deploy_template "$RESOURCE_GROUP" "$deployment_name" "$REPO_ROOT/infra/foundry/main.bicep" "$parameters_file"

foundry_resource="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" foundryResource)"
deployment="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" deploymentName)"
base_url="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" claudeBaseUrl)"

mkdir -p "$REPO_ROOT/.azure"
cat >"$REPO_ROOT/.azure/foundry.env" <<EOF
export LLM_BACKEND=foundry
export FOUNDRY_RESOURCE=$foundry_resource
export FOUNDRY_MODEL=$deployment
export FOUNDRY_RESOURCE_GROUP=$RESOURCE_GROUP
EOF

cat <<EOF

완료했습니다.
  Foundry 리소스    : $foundry_resource
  모델 배포 이름    : $deployment
  Claude 엔드포인트 : $base_url/

로컬에서 키 없이 호출해 보기 (역할 전파에 몇 분 걸릴 수 있습니다):
  source .azure/foundry.env
  export DEMO_PASSWORD='<임의의 비밀번호>'
  python -m app.server          # http://127.0.0.1:8080  (사용자: demo)

ACA/AKS 데모를 이 Foundry에 연결하려면 같은 셸에서 source .azure/foundry.env 후 배포 스크립트를 실행하세요.
EOF

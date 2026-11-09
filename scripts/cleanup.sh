#!/usr/bin/env bash
# Removes the Azure resources (and GitHub variables) the demo scripts created.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: scripts/cleanup.sh <대상> [--yes]

데모가 만든 Azure 리소스를 지워 비용을 멈춥니다.

대상
  aca      Container Apps 리소스 그룹
  aks      AKS 리소스 그룹 (노드가 계속 과금되므로 시연 직후 꼭 지우세요)
  foundry  Foundry 리소스 그룹을 지우고 삭제된 계정을 영구 삭제(purge)합니다
  oidc     GitHub Actions 용 관리 ID, 그 역할 할당, azure-demo 환경 변수
  all      위의 모든 것

옵션
  -y, --yes   확인 질문 없이 진행
  -h, --help  도움말

환경 변수 (괄호는 기본값)
  ACA_RESOURCE_GROUP      (rg-cloud-copilot-aca)
  AKS_RESOURCE_GROUP      (rg-cloud-copilot-aks)
  FOUNDRY_RESOURCE_GROUP  (rg-cloud-copilot-foundry)
  IDENTITY_RESOURCE_GROUP (rg-cloud-copilot-github)
  IDENTITY_NAME           (ccd-github-actions)

안전장치: demo=ghcp-in-the-cloud 태그가 없는 리소스 그룹은 지우지 않습니다.
이 저장소의 배포 스크립트가 만든 그룹에는 이 태그가 붙어 있습니다.
EOF
}

TARGET=''
while (($#)); do
  case "$1" in
    -y | --yes) ASSUME_YES=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    aca | aks | foundry | oidc | all)
      [[ -z "$TARGET" ]] || die "대상은 하나만 지정하세요."
      TARGET="$1"
      ;;
    *) die "알 수 없는 인자: $1 (도움말: --help)" ;;
  esac
  shift
done
[[ -n "$TARGET" ]] || {
  usage >&2
  exit 1
}

ACA_RESOURCE_GROUP="${ACA_RESOURCE_GROUP:-rg-cloud-copilot-aca}"
AKS_RESOURCE_GROUP="${AKS_RESOURCE_GROUP:-rg-cloud-copilot-aks}"
FOUNDRY_RESOURCE_GROUP="${FOUNDRY_RESOURCE_GROUP:-rg-cloud-copilot-foundry}"
IDENTITY_RESOURCE_GROUP="${IDENTITY_RESOURCE_GROUP:-rg-cloud-copilot-github}"
IDENTITY_NAME="${IDENTITY_NAME:-ccd-github-actions}"
ENVIRONMENT_NAME=azure-demo

require_azure_login

# delete_group GROUP [wait] - deletes a resource group this repository's scripts created.
delete_group() {
  local group="$1" wait="${2:-}" tag
  if [[ "$(az group exists --name "$group")" != true ]]; then
    log "리소스 그룹이 없습니다(이미 정리됨): $group"
    return 0
  fi
  tag="$(az group show --name "$group" --query 'tags.demo' --output tsv 2>/dev/null || true)"
  [[ "$tag" == ghcp-in-the-cloud ]] ||
    die "리소스 그룹 $group 에 demo=ghcp-in-the-cloud 태그가 없어 지우지 않습니다. 이 저장소가 만든 그룹이 맞다면 태그를 붙이고 다시 실행하세요."
  if [[ "$wait" == wait ]]; then
    log "삭제 중: $group (끝날 때까지 기다립니다)"
    az group delete --name "$group" --yes --only-show-errors
  else
    log "삭제 요청: $group (백그라운드에서 진행됩니다)"
    az group delete --name "$group" --yes --no-wait --only-show-errors
  fi
}

cleanup_foundry() {
  local accounts='' name location
  if [[ "$(az group exists --name "$FOUNDRY_RESOURCE_GROUP")" == true ]]; then
    accounts="$(az cognitiveservices account list --resource-group "$FOUNDRY_RESOURCE_GROUP" --query '[].[name,location]' --output tsv)"
  fi
  delete_group "$FOUNDRY_RESOURCE_GROUP" wait
  # A deleted account stays soft-deleted (and keeps its name and quota) until it is purged.
  while IFS=$'\t' read -r name location; do
    [[ -n "$name" ]] || continue
    log "영구 삭제(purge): $name ($location)"
    az cognitiveservices account purge --name "$name" --resource-group "$FOUNDRY_RESOURCE_GROUP" --location "$location" --only-show-errors ||
      warn "$name 을 purge 하지 못했습니다. 이미 지워졌는지 'az cognitiveservices account list-deleted' 로 확인하세요."
  done <<<"$accounts"
  rm -f "$REPO_ROOT/.azure/foundry.env"
}

cleanup_oidc() {
  local principal_id assignments
  principal_id="$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query principalId --output tsv 2>/dev/null || true)"
  if [[ -n "$principal_id" ]]; then
    assignments="$(az role assignment list --all --assignee "$principal_id" --query '[].id' --output tsv)"
    if [[ -n "$assignments" ]]; then
      log "관리 ID 의 역할 할당 삭제"
      # shellcheck disable=SC2086 # One role assignment ID per line, none contain spaces.
      az role assignment delete --ids $assignments --only-show-errors
    fi
  fi
  delete_group "$IDENTITY_RESOURCE_GROUP"

  if command -v gh >/dev/null 2>&1; then
    local repo origin variable
    origin="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
    repo="$(printf '%s' "$origin" | sed -E 's#^(https?://[^/]+/|git@[^:]+:|ssh://git@[^/]+/)##; s#\.git$##')"
    if [[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
      for variable in AZURE_CLIENT_ID AZURE_TENANT_ID AZURE_SUBSCRIPTION_ID ACA_RESOURCE_GROUP ACA_APP_NAME ACA_ACR_NAME AKS_RESOURCE_GROUP AKS_CLUSTER_NAME AKS_ACR_NAME; do
        gh variable delete "$variable" --env "$ENVIRONMENT_NAME" --repo "$repo" >/dev/null 2>&1 || true
      done
      log "GitHub 환경 $ENVIRONMENT_NAME 의 변수를 지웠습니다. (환경 자체는 남깁니다)"
    fi
  else
    warn "gh 가 없어 GitHub 환경 변수는 지우지 못했습니다. 저장소 Settings > Environments > $ENVIRONMENT_NAME 에서 지우세요."
  fi
}

case "$TARGET" in
  aca) plan="Container Apps 그룹 $ACA_RESOURCE_GROUP" ;;
  aks) plan="AKS 그룹 $AKS_RESOURCE_GROUP" ;;
  foundry) plan="Foundry 그룹 $FOUNDRY_RESOURCE_GROUP (삭제 후 purge)" ;;
  oidc) plan="관리 ID 그룹 $IDENTITY_RESOURCE_GROUP, 그 역할 할당, GitHub 환경 변수" ;;
  all) plan="$ACA_RESOURCE_GROUP, $AKS_RESOURCE_GROUP, $FOUNDRY_RESOURCE_GROUP (삭제 후 purge), $IDENTITY_RESOURCE_GROUP, GitHub 환경 변수" ;;
esac
printf '\n구독: %s (%s)\n삭제 대상: %s\n\n' "$SUBSCRIPTION_NAME" "$SUBSCRIPTION_ID" "$plan" >&2
confirm "되돌릴 수 없습니다. 계속할까요?" || die "취소했습니다."

case "$TARGET" in
  aca) delete_group "$ACA_RESOURCE_GROUP" ;;
  aks) delete_group "$AKS_RESOURCE_GROUP" ;;
  foundry) cleanup_foundry ;;
  oidc) cleanup_oidc ;;
  all)
    cleanup_oidc
    delete_group "$ACA_RESOURCE_GROUP"
    delete_group "$AKS_RESOURCE_GROUP"
    cleanup_foundry
    ;;
esac

log "정리 요청을 마쳤습니다. 그룹 삭제는 몇 분 더 걸릴 수 있습니다."

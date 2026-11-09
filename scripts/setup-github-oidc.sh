#!/usr/bin/env bash
# Sets up passwordless (OIDC) GitHub Actions -> Azure access for the deploy workflows:
# a user-assigned managed identity with a federated credential, scoped role assignments
# and the non-secret values the workflows read from the azure-demo environment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

usage() {
  cat <<'EOF'
사용법: scripts/setup-github-oidc.sh [--apply] [--yes] [--repo <owner/name>]

GitHub Actions 가 저장된 비밀 없이 Azure 에 로그인하도록 OIDC 연동을 설정합니다.
기본은 dry-run 으로, 실행할 명령만 보여 주고 아무것도 바꾸지 않습니다. --apply 를 붙이면 실제로 적용합니다.
여러 번 실행해도 같은 결과가 됩니다(이미 있는 항목은 건너뜁니다).

먼저 scripts/deploy-aca.sh 또는 scripts/deploy-aks.sh 로 대상 리소스를 만들어 두세요.
GitHub 환경 azure-demo 는 scripts/apply-repo-settings.sh 가 만듭니다(없으면 이 스크립트가 만듭니다).

하는 일
  1. 사용자 할당 관리 ID 와 페더레이션 자격 증명 만들기
     subject: repo:<owner>/<repo>:environment:azure-demo (이 환경을 쓰는 잡만 로그인할 수 있습니다)
  2. 대상 리소스에만 역할 부여
     ACA: 리소스 그룹 Contributor, 레지스트리 AcrPush
     AKS: 클러스터 사용자 역할, 네임스페이스 범위 RBAC Writer, 레지스트리 AcrPush
  3. azure-demo 환경에 변수 저장: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID,
     ACA_RESOURCE_GROUP, ACA_APP_NAME, ACA_ACR_NAME, AKS_RESOURCE_GROUP, AKS_CLUSTER_NAME, AKS_ACR_NAME
     (모두 비밀이 아닌 식별자입니다)

환경 변수 (괄호는 기본값)
  LOCATION                사용자 할당 관리 ID 의 리전 (koreacentral)
  IDENTITY_RESOURCE_GROUP 관리 ID 를 둘 리소스 그룹 (rg-cloud-copilot-github)
  IDENTITY_NAME           관리 ID 이름 (ccd-github-actions)
  ACA_RESOURCE_GROUP      ACA 리소스 그룹 (rg-cloud-copilot-aca)
  ACA_APP_NAME            컨테이너 앱 이름 (cloud-copilot-demo)
  AKS_RESOURCE_GROUP      AKS 리소스 그룹 (rg-cloud-copilot-aks)

정리: scripts/cleanup.sh oidc
EOF
}

APPLY=0
REPO=''
while (($#)); do
  case "$1" in
    --apply) APPLY=1 ;;
    -y | --yes) ASSUME_YES=1 ;;
    --repo)
      REPO="${2:?--repo 값이 필요합니다}"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) die "알 수 없는 옵션: $1 (도움말: --help)" ;;
  esac
  shift
done

LOCATION="${LOCATION:-koreacentral}"
IDENTITY_RESOURCE_GROUP="${IDENTITY_RESOURCE_GROUP:-rg-cloud-copilot-github}"
IDENTITY_NAME="${IDENTITY_NAME:-ccd-github-actions}"
ACA_RESOURCE_GROUP="${ACA_RESOURCE_GROUP:-rg-cloud-copilot-aca}"
ACA_APP_NAME="${ACA_APP_NAME:-cloud-copilot-demo}"
AKS_RESOURCE_GROUP="${AKS_RESOURCE_GROUP:-rg-cloud-copilot-aks}"
ENVIRONMENT_NAME=azure-demo
NAMESPACE=cloud-copilot-demo
CREDENTIAL_NAME=github-azure-demo

require_commands az python3
require_azure_login
((APPLY == 0)) || require_commands gh

if [[ -z "$REPO" ]]; then
  origin="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
  REPO="$(printf '%s' "$origin" | sed -E 's#^(https?://[^/]+/|git@[^:]+:|ssh://git@[^/]+/)##; s#\.git$##')"
fi
[[ "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || die "저장소를 알 수 없습니다. --repo <owner/name> 으로 지정하세요."

# run CMD... prints the command in dry-run mode and executes it with --apply.
run() {
  if ((APPLY)); then
    "$@"
  else
    printf '  $' >&2
    printf ' %q' "$@" >&2
    printf '\n' >&2
  fi
}

# Discover what is deployed (read-only).
aca_acr='' aks_cluster='' aks_acr=''
if [[ "$(az group exists --name "$ACA_RESOURCE_GROUP")" == true ]]; then
  aca_acr="$(az acr list --resource-group "$ACA_RESOURCE_GROUP" --query '[0].name' --output tsv)"
fi
if [[ "$(az group exists --name "$AKS_RESOURCE_GROUP")" == true ]]; then
  aks_cluster="$(az aks list --resource-group "$AKS_RESOURCE_GROUP" --query '[0].name' --output tsv)"
  aks_acr="$(az acr list --resource-group "$AKS_RESOURCE_GROUP" --query '[0].name' --output tsv)"
fi
[[ -n "$aca_acr" || -n "$aks_cluster" ]] ||
  die "배포된 대상이 없습니다. 먼저 scripts/deploy-aca.sh 또는 scripts/deploy-aks.sh 를 실행하세요."

aca_summary=없음
[[ -z "$aca_acr" ]] || aca_summary="$ACA_RESOURCE_GROUP / $ACA_APP_NAME / $aca_acr"
aks_summary=없음
[[ -z "$aks_cluster" ]] || aks_summary="$AKS_RESOURCE_GROUP / $aks_cluster / $aks_acr"
mode_label="dry-run (아무것도 바꾸지 않습니다)"
((APPLY == 0)) || mode_label="적용 (--apply)"

cat >&2 <<EOF

모드        : $mode_label
구독        : $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)
GitHub 저장소: $REPO (환경 $ENVIRONMENT_NAME)
관리 ID     : $IDENTITY_NAME ($IDENTITY_RESOURCE_GROUP, $LOCATION)
ACA 대상    : $aca_summary
AKS 대상    : $aks_summary

EOF
if ((APPLY)); then
  confirm "위 설정을 적용합니다. 계속할까요?" || die "취소했습니다."
fi

log "1/3 관리 ID 와 페더레이션 자격 증명"
run az group create --name "$IDENTITY_RESOURCE_GROUP" --location "$LOCATION" --tags demo=ghcp-in-the-cloud --only-show-errors --output none
run az identity create --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --location "$LOCATION" --only-show-errors --output none

client_id='<identity-client-id>'
principal_id='<identity-principal-id>'
if ((APPLY)); then
  client_id="$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query clientId --output tsv)"
  principal_id="$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query principalId --output tsv)"
fi

subject="repo:$REPO:environment:$ENVIRONMENT_NAME"
if ((APPLY)) && az identity federated-credential show --identity-name "$IDENTITY_NAME" \
  --resource-group "$IDENTITY_RESOURCE_GROUP" --name "$CREDENTIAL_NAME" >/dev/null 2>&1; then
  log "페더레이션 자격 증명이 이미 있습니다: $CREDENTIAL_NAME"
else
  run az identity federated-credential create --name "$CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" \
    --resource-group "$IDENTITY_RESOURCE_GROUP" --issuer https://token.actions.githubusercontent.com \
    --subject "$subject" --audiences api://AzureADTokenExchange --only-show-errors --output none
fi

# ensure_role ROLE SCOPE
ensure_role() {
  local role="$1" scope="$2" existing=''
  if ((APPLY)); then
    existing="$(az role assignment list --assignee "$principal_id" --role "$role" --scope "$scope" --query '[0].id' --output tsv)"
    if [[ -n "$existing" ]]; then
      log "역할이 이미 있습니다: $role"
      return 0
    fi
  fi
  run az role assignment create --assignee-object-id "$principal_id" --assignee-principal-type ServicePrincipal \
    --role "$role" --scope "$scope" --only-show-errors --output none
}

log "2/3 역할 할당 (대상 리소스에만)"
if [[ -n "$aca_acr" ]]; then
  ensure_role Contributor "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ACA_RESOURCE_GROUP"
  ensure_role AcrPush "$(az acr show --name "$aca_acr" --resource-group "$ACA_RESOURCE_GROUP" --query id --output tsv)"
fi
if [[ -n "$aks_cluster" ]]; then
  aks_id="$(az aks show --name "$aks_cluster" --resource-group "$AKS_RESOURCE_GROUP" --query id --output tsv)"
  ensure_role "Azure Kubernetes Service Cluster User Role" "$aks_id"
  ensure_role "Azure Kubernetes Service RBAC Writer" "$aks_id/namespaces/$NAMESPACE"
  ensure_role AcrPush "$(az acr show --name "$aks_acr" --resource-group "$AKS_RESOURCE_GROUP" --query id --output tsv)"
fi

log "3/3 GitHub 환경 $ENVIRONMENT_NAME 변수"
if ((APPLY)); then
  if ! gh api "repos/$REPO/environments/$ENVIRONMENT_NAME" >/dev/null 2>&1; then
    log "환경 $ENVIRONMENT_NAME 이 없어 새로 만듭니다."
    gh api --method PUT "repos/$REPO/environments/$ENVIRONMENT_NAME" --silent
  fi
else
  printf '  # 환경 %s 가 없으면 gh api --method PUT repos/%s/environments/%s 로 만듭니다\n' "$ENVIRONMENT_NAME" "$REPO" "$ENVIRONMENT_NAME" >&2
fi

set_variable() {
  run gh variable set "$1" --env "$ENVIRONMENT_NAME" --repo "$REPO" --body "$2"
}
set_variable AZURE_CLIENT_ID "$client_id"
set_variable AZURE_TENANT_ID "$TENANT_ID"
set_variable AZURE_SUBSCRIPTION_ID "$SUBSCRIPTION_ID"
if [[ -n "$aca_acr" ]]; then
  set_variable ACA_RESOURCE_GROUP "$ACA_RESOURCE_GROUP"
  set_variable ACA_APP_NAME "$ACA_APP_NAME"
  set_variable ACA_ACR_NAME "$aca_acr"
fi
if [[ -n "$aks_cluster" ]]; then
  set_variable AKS_RESOURCE_GROUP "$AKS_RESOURCE_GROUP"
  set_variable AKS_CLUSTER_NAME "$aks_cluster"
  set_variable AKS_ACR_NAME "$aks_acr"
fi

if ((APPLY)); then
  cat <<EOF

완료했습니다. GitHub 저장소에는 비밀이 하나도 저장되지 않았습니다.
  Actions > Deploy to Azure Container Apps / Deploy to AKS 를 실행해 보세요.
  페더레이션 subject: $subject
EOF
else
  printf '\n위 명령을 실제로 실행하려면 --apply 를 붙여 다시 실행하세요.\n'
fi

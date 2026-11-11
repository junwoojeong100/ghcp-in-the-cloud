#!/usr/bin/env bash
# Deploys the demo app to Azure Kubernetes Service: infra/aks/main.bicep (cluster, ACR,
# workload identity), an image build in ACR, then the Kustomize manifests.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

NAMESPACE=cloud-copilot-demo

usage() {
  cat <<'EOF'
사용법: scripts/deploy-aks.sh [--yes]

AKS 클러스터를 만들고 데모 앱을 배포합니다. 기본은 mock 백엔드라서 Foundry 없이도 동작합니다.
Foundry 의 모델(기본 gpt-6.1-sol)을 쓰려면 먼저 scripts/deploy-foundry.sh 를 실행하고
`source .azure/foundry.env` 한 뒤 이 스크립트를 실행하세요.

필요한 도구: az, kubectl, kubelogin (az aks install-cli 로 kubectl 과 kubelogin 을 함께 설치), python3
(ACR 빌드를 쓸 수 없는 구독에서는 docker 도 필요합니다.)

환경 변수 (괄호는 기본값)
  RESOURCE_GROUP         리소스 그룹 (rg-cloud-copilot-aks)
  LOCATION               리전 (koreacentral)
  NAME_PREFIX            리소스 이름 접두사, 소문자/숫자 (ccd)
  NODE_VM_SIZE           노드 VM 크기 (Standard_D2s_v5). 리전에서 쓸 수 없으면 다른 크기를 지정하세요.
  IMAGE_TAG              이미지 태그이자 앱 버전 (v1)
  DEMO_PASSWORD          데모 UI 비밀번호 (지정하지 않으면 자동 생성해 마지막에 한 번 보여 줍니다)
  PRINCIPAL_ID           클러스터 관리자 역할을 받을 사용자 객체 ID (로그인한 사용자)
  PRINCIPAL_TYPE         User | ServicePrincipal | Group (User)
  FOUNDRY_RESOURCE       지정하면 mock 대신 이 Foundry 리소스의 모델을 호출합니다
  FOUNDRY_RESOURCE_GROUP Foundry 리소스 그룹 (RESOURCE_GROUP 과 같다고 봅니다)
  FOUNDRY_MODEL          모델 배포 이름 (gpt-6.1-sol)
  FOUNDRY_EFFORT         low | medium | high | xhigh | max (max)

옵션
  -y, --yes   확인 질문 없이 진행
  -h, --help  도움말

클러스터는 비용이 계속 발생합니다. 시연이 끝나면 scripts/cleanup.sh aks 로 정리하세요.
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

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cloud-copilot-aks}"
LOCATION="${LOCATION:-koreacentral}"
NAME_PREFIX="${NAME_PREFIX:-ccd}"
NODE_VM_SIZE="${NODE_VM_SIZE:-Standard_D2s_v5}"
IMAGE_TAG="${IMAGE_TAG:-v1}"
FOUNDRY_RESOURCE="${FOUNDRY_RESOURCE:-}"
FOUNDRY_RESOURCE_GROUP="${FOUNDRY_RESOURCE_GROUP:-$RESOURCE_GROUP}"
FOUNDRY_MODEL="${FOUNDRY_MODEL:-gpt-6.1-sol}"
FOUNDRY_EFFORT="${FOUNDRY_EFFORT:-max}"

[[ "$NAME_PREFIX" =~ ^[a-z][a-z0-9]{1,11}$ ]] || die "NAME_PREFIX 는 소문자/숫자 2~12자여야 합니다."
[[ "$NODE_VM_SIZE" =~ ^Standard_[A-Za-z0-9_]+$ ]] || die "NODE_VM_SIZE 형식이 올바르지 않습니다: $NODE_VM_SIZE"
[[ "$IMAGE_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]] || die "IMAGE_TAG 형식이 올바르지 않습니다: $IMAGE_TAG"
[[ -z "$FOUNDRY_RESOURCE" || "$FOUNDRY_RESOURCE" =~ ^[A-Za-z0-9][A-Za-z0-9-]{1,63}$ ]] || die "FOUNDRY_RESOURCE 는 호스트 이름이 아니라 리소스 이름이어야 합니다."

require_commands python3 kubectl kubelogin
require_azure_login
detect_principal
[[ -n "${PRINCIPAL_ID:-}" ]] || die "클러스터 관리자 역할을 줄 PRINCIPAL_ID 가 필요합니다. 로컬 계정이 꺼져 있어 이 역할이 없으면 kubectl 을 쓸 수 없습니다."

password_generated=0
if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  DEMO_PASSWORD="$(random_password)"
  password_generated=1
fi

if [[ -n "$FOUNDRY_RESOURCE" ]]; then
  backend="Foundry ($FOUNDRY_RESOURCE / $FOUNDRY_MODEL, effort $FOUNDRY_EFFORT)"
else
  backend="mock (Azure 모델 호출 없음)"
fi
cat >&2 <<EOF

구독              : $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)
리소스 그룹 / 리전 : $RESOURCE_GROUP / $LOCATION
노드              : $NODE_VM_SIZE, 자동 확장 1~3대 (실행하는 동안 계속 과금됩니다)
이미지 태그       : $IMAGE_TAG
백엔드            : $backend

EOF
confirm "Azure 리소스를 만듭니다. 계속할까요?" || die "취소했습니다."

ensure_providers Microsoft.ContainerService Microsoft.ContainerRegistry Microsoft.ManagedIdentity

log "리소스 그룹 생성: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags demo=ghcp-in-the-cloud \
  --only-show-errors --output none

parameters_file="$(mktemp)"
trap 'rm -f "$parameters_file"' EXIT
write_parameters "$parameters_file" \
  "namePrefix=$NAME_PREFIX" \
  "location=$LOCATION" \
  "nodeVmSize=$NODE_VM_SIZE" \
  "principalId=$PRINCIPAL_ID" \
  "principalType=${PRINCIPAL_TYPE:-User}" \
  "foundryResource=$FOUNDRY_RESOURCE" \
  "foundryResourceGroup=$FOUNDRY_RESOURCE_GROUP"

deployment_name="aks-$(date +%Y%m%d%H%M%S)"
log "1/4 AKS 클러스터, 레지스트리, Workload Identity 배포 중... (5~10분 걸립니다)"
deploy_template "$RESOURCE_GROUP" "$deployment_name" "$REPO_ROOT/infra/aks/main.bicep" "$parameters_file"
cluster_name="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" clusterName)"
registry_name="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" registryName)"
login_server="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" registryLoginServer)"
workload_client_id="$(deployment_output "$RESOURCE_GROUP" "$deployment_name" workloadClientId)"

log "2/4 이미지 빌드"
build_and_push_image "$REPO_ROOT" "$registry_name" "$login_server" "$IMAGE_TAG"

log "3/4 클러스터 연결"
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$cluster_name" --overwrite-existing --only-show-errors
kubelogin convert-kubeconfig --login azurecli

# Azure RBAC for Kubernetes can take a few minutes to reach the API server after the role assignment.
ready=0
for attempt in $(seq 1 20); do
  if kubectl get namespace default >/dev/null 2>&1; then
    ready=1
    break
  fi
  log "클러스터 권한이 적용되길 기다리는 중... ($attempt/20)"
  sleep 20
done
((ready)) || die "클러스터에 접근하지 못했습니다. 역할 할당이 전파되었는지 확인하고 스크립트를 다시 실행하세요."

log "4/4 매니페스트 적용"
kubectl apply --filename "$REPO_ROOT/infra/aks/k8s/namespace.yaml"
# 실행 중인 파드는 시작할 때만 Secret 을 읽으므로, 비밀번호가 바뀌면 아래에서 파드를 다시 시작합니다.
previous_password="$(kubectl get secret cloud-copilot-demo --namespace "$NAMESPACE" --output jsonpath='{.data.password}' 2>/dev/null || true)"
printf '%s' "$DEMO_PASSWORD" |
  kubectl create secret generic cloud-copilot-demo --namespace "$NAMESPACE" \
    --from-file=password=/dev/stdin --dry-run=client --output yaml |
  kubectl apply --filename -

IMAGE_REPOSITORY="$login_server/cloud-copilot-demo" \
  IMAGE_TAG="$IMAGE_TAG" \
  WORKLOAD_CLIENT_ID="$workload_client_id" \
  FOUNDRY_RESOURCE="$FOUNDRY_RESOURCE" \
  FOUNDRY_MODEL="$FOUNDRY_MODEL" \
  FOUNDRY_EFFORT="$FOUNDRY_EFFORT" \
  "$REPO_ROOT/scripts/render-aks-manifests.sh" |
  kubectl apply --filename -

if [[ -n "$previous_password" && "$previous_password" != "$(printf '%s' "$DEMO_PASSWORD" | base64 | tr -d '\n')" ]]; then
  log "비밀번호가 바뀌어 파드를 다시 시작합니다."
  kubectl rollout restart deployment/cloud-copilot-demo --namespace "$NAMESPACE"
fi
kubectl rollout status deployment/cloud-copilot-demo --namespace "$NAMESPACE" --timeout=300s

cat <<EOF

배포를 마쳤습니다.
  클러스터    : $cluster_name ($RESOURCE_GROUP)
  레지스트리  : $login_server
  백엔드      : $backend

접속 (포트 포워딩, 사용자 demo / 비밀번호 $([[ "$password_generated" == 1 ]] && echo "$DEMO_PASSWORD" || echo "(지정한 DEMO_PASSWORD)"))
  kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace $NAMESPACE
  브라우저에서 http://localhost:8080 을 여세요.

HPA 시연
  kubectl scale deployment/load-generator --replicas=1 --namespace $NAMESPACE
  kubectl get hpa,pods --namespace $NAMESPACE --watch
  kubectl scale deployment/load-generator --replicas=0 --namespace $NAMESPACE   # 부하 중지

정리: scripts/cleanup.sh aks
EOF
if [[ "$password_generated" == 1 ]]; then
  cat <<EOF

비밀번호를 잊었다면:
  kubectl get secret cloud-copilot-demo --namespace $NAMESPACE --output jsonpath='{.data.password}' | base64 --decode
EOF
fi

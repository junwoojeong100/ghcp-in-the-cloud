#!/usr/bin/env bash
# Renders the AKS manifests (infra/aks/k8s/base + environment values) to stdout.
# Used by scripts/deploy-aks.sh (kubectl apply) and by CI (kubeconform), so what CI
# validates is exactly what gets deployed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="$REPO_ROOT/infra/aks/k8s"

usage() {
  cat <<'EOF'
사용법: IMAGE_REPOSITORY=<레지스트리>/cloud-copilot-demo IMAGE_TAG=<태그> \
        WORKLOAD_CLIENT_ID=<GUID> scripts/render-aks-manifests.sh

infra/aks/k8s/base 에 환경 값을 입히고 완성된 YAML 을 표준 출력으로 내보냅니다.
클러스터나 Azure 로그인이 필요 없어서 적용 전에 내용을 미리 볼 때도 쓸 수 있습니다.

필수 환경 변수
  IMAGE_REPOSITORY    예: ccdacrab12cd.azurecr.io/cloud-copilot-demo
  IMAGE_TAG           예: v1 (이미지에 구워진 APP_VERSION 과 같은 값으로 빌드해 두세요)
  WORKLOAD_CLIENT_ID  Workload Identity 용 관리 ID 의 클라이언트 ID (GUID)

선택 환경 변수 (FOUNDRY_RESOURCE 를 지정하면 mock 대신 Foundry 의 모델을 호출합니다)
  FOUNDRY_RESOURCE    Foundry 리소스 이름
  FOUNDRY_MODEL       모델 배포 이름
  FOUNDRY_EFFORT      low | medium | high | xhigh | max

kustomize 또는 kubectl 이 필요합니다.
EOF
}

die() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}

case "${1:-}" in
  -h | --help)
    usage
    exit 0
    ;;
  '') ;;
  *) die "알 수 없는 인자: $1 (도움말: --help)" ;;
esac

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-}"
IMAGE_TAG="${IMAGE_TAG:-}"
WORKLOAD_CLIENT_ID="${WORKLOAD_CLIENT_ID:-}"
FOUNDRY_RESOURCE="${FOUNDRY_RESOURCE:-}"
FOUNDRY_MODEL="${FOUNDRY_MODEL:-}"
FOUNDRY_EFFORT="${FOUNDRY_EFFORT:-}"

[[ -n "$IMAGE_REPOSITORY" ]] || die "IMAGE_REPOSITORY 를 지정하세요. (--help)"
[[ -n "$IMAGE_TAG" ]] || die "IMAGE_TAG 를 지정하세요. (--help)"
[[ -n "$WORKLOAD_CLIENT_ID" ]] || die "WORKLOAD_CLIENT_ID 를 지정하세요. (--help)"

# Values end up in YAML, so only accept the characters each field legitimately needs.
[[ "$IMAGE_REPOSITORY" =~ ^[a-z0-9][a-z0-9.-]*(:[0-9]+)?(/[a-z0-9._-]+)+$ ]] || die "IMAGE_REPOSITORY 형식이 올바르지 않습니다: $IMAGE_REPOSITORY"
[[ "$IMAGE_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]] || die "IMAGE_TAG 형식이 올바르지 않습니다: $IMAGE_TAG"
[[ "$WORKLOAD_CLIENT_ID" =~ ^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$ ]] || die "WORKLOAD_CLIENT_ID 는 GUID 여야 합니다."
if [[ -n "$FOUNDRY_RESOURCE" ]]; then
  [[ "$FOUNDRY_RESOURCE" =~ ^[A-Za-z0-9][A-Za-z0-9-]{1,63}$ ]] || die "FOUNDRY_RESOURCE 는 호스트 이름이 아니라 리소스 이름이어야 합니다."
  [[ -z "$FOUNDRY_MODEL" || "$FOUNDRY_MODEL" =~ ^[A-Za-z0-9._-]+$ ]] || die "FOUNDRY_MODEL 형식이 올바르지 않습니다."
  [[ -z "$FOUNDRY_EFFORT" || "$FOUNDRY_EFFORT" =~ ^(low|medium|high|xhigh|max)$ ]] || die "FOUNDRY_EFFORT 는 low|medium|high|xhigh|max 중 하나여야 합니다."
fi

if command -v kustomize >/dev/null 2>&1; then
  kustomize_build=(kustomize build)
elif command -v kubectl >/dev/null 2>&1; then
  kustomize_build=(kubectl kustomize)
else
  die "kustomize 또는 kubectl 이 필요합니다."
fi

# Kustomize only follows relative references, so the overlay lives next to base.
overlay="$(mktemp -d "$K8S_DIR/.overlay.XXXXXX")"
trap 'rm -rf "$overlay"' EXIT

{
  cat <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: cloud-copilot-demo
resources:
  - ../base
images:
  - name: cloud-copilot-demo
    newName: $IMAGE_REPOSITORY
    newTag: "$IMAGE_TAG"
patches:
  - target:
      kind: ServiceAccount
      name: cloud-copilot-demo
    patch: |-
      - op: add
        path: /metadata/annotations/azure.workload.identity~1client-id
        value: "$WORKLOAD_CLIENT_ID"
EOF
  if [[ -n "$FOUNDRY_RESOURCE" ]]; then
    printf 'configMapGenerator:\n  - name: cloud-copilot-demo-config\n    behavior: merge\n    literals:\n'
    printf '      - LLM_BACKEND=foundry\n      - FOUNDRY_RESOURCE=%s\n' "$FOUNDRY_RESOURCE"
    [[ -z "$FOUNDRY_MODEL" ]] || printf '      - FOUNDRY_MODEL=%s\n' "$FOUNDRY_MODEL"
    [[ -z "$FOUNDRY_EFFORT" ]] || printf '      - FOUNDRY_EFFORT=%s\n' "$FOUNDRY_EFFORT"
  fi
} >"$overlay/kustomization.yaml"

"${kustomize_build[@]}" "$overlay"

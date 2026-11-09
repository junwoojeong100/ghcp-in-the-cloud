# shellcheck shell=bash
# Shared helpers for the demo scripts. Source it; do not execute it.

((BASH_VERSINFO[0] >= 4)) || {
  echo "오류: bash 4 이상이 필요합니다. macOS 에서는 'brew install bash' 후 다시 실행하세요." >&2
  exit 1
}

if [[ -t 2 ]]; then
  _blue=$'\033[1;34m'
  _yellow=$'\033[1;33m'
  _red=$'\033[1;31m'
  _reset=$'\033[0m'
else
  _blue=''
  _yellow=''
  _red=''
  _reset=''
fi

log() { printf '%s==>%s %s\n' "$_blue" "$_reset" "$*" >&2; }
warn() { printf '%s경고:%s %s\n' "$_yellow" "$_reset" "$*" >&2; }
die() {
  printf '%s오류:%s %s\n' "$_red" "$_reset" "$*" >&2
  exit 1
}

require_commands() {
  local missing=() cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  ((${#missing[@]} == 0)) || die "필요한 명령이 없습니다: ${missing[*]}"
}

# Sets SUBSCRIPTION_ID, SUBSCRIPTION_NAME and TENANT_ID from the active az login.
# shellcheck disable=SC2034 # The variables are read by the scripts that source this file.
require_azure_login() {
  require_commands az
  az account show >/dev/null 2>&1 || die "Azure에 로그인되어 있지 않습니다. 먼저 'az login' 을 실행하세요."
  SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
  SUBSCRIPTION_NAME="$(az account show --query name --output tsv)"
  TENANT_ID="$(az account show --query tenantId --output tsv)"
}

# confirm "question" -> succeeds on yes. ASSUME_YES=1 (or --yes) skips the prompt.
confirm() {
  [[ "${ASSUME_YES:-0}" == 1 ]] && return 0
  [[ -t 0 ]] || die "대화형 터미널이 아닙니다. 확인 없이 진행하려면 --yes 를 사용하세요."
  local answer
  read -r -p "$1 [y/N] " answer
  [[ "$answer" == [yY] || "$answer" == [yY][eE][sS] ]]
}

random_password() {
  python3 -c 'import secrets; print(secrets.token_urlsafe(18))'
}

# write_parameters FILE ITEM...  writes an ARM deployment parameter file.
# Secrets must never appear on a command line, so the file is created with mode 600
# and secret values are read from the environment:
#   name=value        string parameter
#   name:=JSON        typed parameter (number, boolean, ...)
#   name@ENV_VAR      string parameter whose value comes from $ENV_VAR
write_parameters() {
  local file="$1"
  shift
  python3 - "$file" "$@" <<'PY'
import json
import os
import re
import sys

path, *items = sys.argv[1:]
parameters = {}
for item in items:
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9]*)(:=|=|@)(.*)", item, re.DOTALL)
    if not match:
        sys.exit(f"invalid parameter item: {item!r}")
    name, operator, raw = match.groups()
    if operator == ":=":
        value = json.loads(raw)
    elif operator == "@":
        value = os.environ[raw]
    else:
        value = raw
    parameters[name] = {"value": value}

document = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": parameters,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(document, handle)
PY
}

# deploy_template GROUP NAME TEMPLATE PARAMETER_FILE
deploy_template() {
  az deployment group create \
    --resource-group "$1" \
    --name "$2" \
    --template-file "$3" \
    --parameters "@$4" \
    --only-show-errors \
    --output none
}

# deployment_output GROUP NAME OUTPUT_NAME -> prints the output value
deployment_output() {
  az deployment group show \
    --resource-group "$1" \
    --name "$2" \
    --query "properties.outputs.$3.value" \
    --output tsv
}

# Principal of the signed-in Azure user: sets PRINCIPAL_ID / PRINCIPAL_TYPE unless already set.
detect_principal() {
  if [[ -n "${PRINCIPAL_ID:-}" ]]; then
    PRINCIPAL_TYPE="${PRINCIPAL_TYPE:-User}"
    return 0
  fi
  PRINCIPAL_ID="$(az ad signed-in-user show --query id --output tsv 2>/dev/null || true)"
  PRINCIPAL_TYPE=User
  if [[ -z "$PRINCIPAL_ID" ]]; then
    warn "로그인한 사용자의 ID를 확인하지 못했습니다(서비스 주체로 로그인했거나 권한 부족)."
    warn "필요하면 PRINCIPAL_ID 와 PRINCIPAL_TYPE(User|ServicePrincipal|Group)을 직접 지정하세요."
  fi
}

# build_and_push_image ROOT REGISTRY LOGIN_SERVER TAG
# Builds app/Dockerfile inside ACR (no local Docker needed) and falls back to local
# Docker, because some subscriptions block ACR Tasks.
build_and_push_image() {
  local root="$1" registry="$2" login_server="$3" tag="$4"
  local image="$login_server/cloud-copilot-demo:$tag"
  log "컨테이너 이미지 빌드: $image"
  if az acr build --registry "$registry" --image "cloud-copilot-demo:$tag" \
    --build-arg "APP_VERSION=$tag" --file app/Dockerfile --only-show-errors "$root"; then
    return 0
  fi
  command -v docker >/dev/null 2>&1 || die "ACR 빌드에 실패했고 로컬에 docker 도 없습니다."
  warn "ACR 빌드에 실패해 로컬 Docker 로 다시 시도합니다. (일부 구독은 ACR Tasks 를 막아 둡니다)"
  az acr login --name "$registry" --only-show-errors
  docker build --build-arg "APP_VERSION=$tag" --file "$root/app/Dockerfile" --tag "$image" "$root"
  docker push "$image"
}

# wait_for_http URL [ATTEMPTS] [DELAY_SECONDS]
wait_for_http() {
  local url="$1" attempts="${2:-30}" delay="${3:-5}" i
  for ((i = 1; i <= attempts; i++)); do
    if curl --fail --silent --show-error --max-time 10 --output /dev/null "$url" 2>/dev/null; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

# curl_demo URL [CURL_ARGS...]
# Calls the demo app with HTTP Basic auth (user "demo", password $DEMO_PASSWORD) without
# putting the password on the command line, where other local users could read it.
curl_demo() {
  local url="$1" credentials
  shift
  credentials="demo:${DEMO_PASSWORD:?DEMO_PASSWORD 가 필요합니다}"
  credentials="${credentials//\\/\\\\}"
  credentials="${credentials//\"/\\\"}"
  printf 'user = "%s"\n' "$credentials" |
    curl --silent --show-error --max-time 30 --config - "$@" "$url"
}

# ensure_providers NAMESPACE... registers the resource providers a demo needs (first use per subscription).
ensure_providers() {
  local namespace state
  for namespace in "$@"; do
    state="$(az provider show --namespace "$namespace" --query registrationState --output tsv 2>/dev/null || true)"
    if [[ "$state" != Registered ]]; then
      log "리소스 공급자 등록: $namespace (처음 한 번만 걸립니다)"
      az provider register --namespace "$namespace" --wait --only-show-errors
    fi
  done
}

ensure_containerapp_extension() {
  az extension show --name containerapp >/dev/null 2>&1 ||
    az extension add --name containerapp --only-show-errors
}

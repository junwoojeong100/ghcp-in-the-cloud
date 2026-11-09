#!/usr/bin/env bash
# Runs once after the dev container is created (devcontainer.json -> postCreateCommand).
# Installs the app dependencies and the lint tools CI uses, then prints how to run the demo.
# It stores no credentials.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> app/requirements.txt 설치"
# The mock backend and the unit tests need nothing from this file, so a failure only warns.
if ! python -m pip install --user --disable-pip-version-check --quiet -r app/requirements.txt; then
  echo "경고: 의존성 설치에 실패했습니다. 나중에 다시 실행하세요:"
  echo "  python -m pip install --user -r app/requirements.txt"
fi

# Best effort: the tests and the demo run without these tools, so a failure only warns.
if [ -f scripts/install-dev-tools.sh ]; then
  echo
  echo "==> CI와 같은 검사 도구 설치 (actionlint, kubeconform, hadolint)"
  installer=(bash scripts/install-dev-tools.sh --dir /usr/local/bin)
  if [ "$(id -u)" -ne 0 ]; then
    installer=(sudo "${installer[@]}")
  fi
  if ! "${installer[@]}"; then
    echo "경고: 검사 도구 설치에 실패했습니다. 나중에 다시 실행하세요:"
    echo "  sudo bash scripts/install-dev-tools.sh --dir /usr/local/bin"
  fi
fi

show_version() {
  local label="$1"
  shift
  local output
  output="$("$@" 2>/dev/null)" || true
  output="${output%%$'\n'*}"
  printf '  %-12s %s\n' "$label" "${output:-확인할 수 없음}"
}

echo
echo "==> 설치된 도구"
show_version python python --version
show_version az az version --query '"azure-cli"' --output tsv
show_version bicep az bicep version
show_version gh gh --version
show_version kubectl kubectl version --client
show_version docker docker --version
show_version actionlint actionlint -version
show_version kubeconform kubeconform -v
show_version hadolint hadolint --version

if [ -n "${DEMO_PASSWORD:-}" ]; then
  run_app='LLM_BACKEND=mock python -m app.server'
else
  run_app='DEMO_PASSWORD=<시연용 임시 값> LLM_BACKEND=mock python -m app.server'
fi

cat <<EOF

==> 다음 단계
  테스트 실행:
    python -m unittest discover -s app/tests -v

  Azure 없이 앱 실행 (mock 백엔드, 포트 8080 자동 전달):
    ${run_app}
    사용자 이름은 demo, 비밀번호는 DEMO_PASSWORD 값입니다.

  AKS 데모에는 kubelogin도 필요합니다. 그때 한 번만 실행하세요:
    sudo az aks install-cli

  scripts/apply-repo-settings.sh는 저장소 관리자 권한이 필요합니다.
  Codespaces의 기본 GITHUB_TOKEN으로는 권한이 부족할 수 있습니다. 'unset GITHUB_TOKEN' 명령을
  실행한 뒤 gh auth login으로 로그인하세요. (자세한 내용은 demos/02-github-repo/README.md)
EOF

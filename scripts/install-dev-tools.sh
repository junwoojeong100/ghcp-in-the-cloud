#!/usr/bin/env bash
# Installs the pinned, checksum-verified tools that CI, the Copilot cloud agent and the dev
# container use to validate this repository. Linux only; on macOS use `brew install` instead.
#
#   kubeconform  validates rendered Kubernetes manifests
#   actionlint   lints GitHub Actions workflows
#   hadolint     lints the Dockerfile
#
# To bump a tool, change its version and both checksums together and copy the checksums from
# the release's published checksum file (never from a file you downloaded from somewhere else).
# This script avoids bash 4 features so it also runs on older shells.
set -euo pipefail

KUBECONFORM_VERSION='v0.8.0'
KUBECONFORM_SHA256_AMD64='9bc2bffbf71f261128533edaf912153948b7ff238f9a531ae6d34466ec287883'
KUBECONFORM_SHA256_ARM64='1f53fc8e81258197a35e8603054162a5af1de8c5af13746c71ab680d9534ed87'

ACTIONLINT_VERSION='1.7.12'
ACTIONLINT_SHA256_AMD64='8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8'
ACTIONLINT_SHA256_ARM64='325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6'

HADOLINT_VERSION='v2.15.1'
HADOLINT_SHA256_AMD64='c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507'
HADOLINT_SHA256_ARM64='f6198ef8090f404dbb771abfee086eb8c48ac177f30da7fd3510aca35b344b5d'

usage() {
  cat <<'EOF'
사용법: scripts/install-dev-tools.sh [--dir <경로>] [kubeconform] [actionlint] [hadolint]

CI, Copilot 클라우드 에이전트, 개발 컨테이너가 이 저장소를 검증할 때 쓰는 도구를
고정된 버전으로 내려받고 SHA-256 체크섬을 확인한 뒤 설치합니다. (Linux 전용)

  --dir 경로   설치 위치 (기본: $TOOLS_DIR, 없으면 ~/.local/bin)
  도구 이름    생략하면 세 가지를 모두 설치합니다

이미 같은 버전이 설치되어 있으면 건너뜁니다. GitHub Actions 에서는 설치 위치를 GITHUB_PATH 에 추가합니다.
EOF
}

die() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}

dir="${TOOLS_DIR:-$HOME/.local/bin}"
tools=()
while (($#)); do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --dir)
      [ "$#" -ge 2 ] || die '--dir 값이 필요합니다.'
      dir="$2"
      shift
      ;;
    kubeconform | actionlint | hadolint) tools+=("$1") ;;
    *) die "알 수 없는 인자: $1 (도움말: --help)" ;;
  esac
  shift
done
[ "${#tools[@]}" -gt 0 ] || tools=(kubeconform actionlint hadolint)

[ "$(uname -s)" = Linux ] || die 'Linux 에서만 동작합니다. macOS 에서는 brew install kubeconform actionlint hadolint 를 사용하세요.'
case "$(uname -m)" in
  x86_64 | amd64) arch=amd64 ;;
  aarch64 | arm64) arch=arm64 ;;
  *) die "지원하지 않는 CPU 아키텍처입니다: $(uname -m)" ;;
esac
command -v curl >/dev/null 2>&1 || die 'curl 이 필요합니다.'
command -v sha256sum >/dev/null 2>&1 || die 'sha256sum 이 필요합니다.'

mkdir -p "$dir"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# fetch URL FILE EXPECTED_SHA256
fetch() {
  local actual
  curl --fail --silent --show-error --location --retry 3 --retry-all-errors --connect-timeout 15 --output "$2" "$1"
  actual="$(sha256sum "$2" | cut -d' ' -f1)"
  [ "$actual" = "$3" ] || die "체크섬이 일치하지 않습니다: $1 (기대 $3, 실제 $actual)"
}

# installed NAME EXPECTED_FIRST_LINE VERSION_ARG
installed() {
  [ -x "$dir/$1" ] && [ "$("$dir/$1" "$3" 2>/dev/null | head -n 1)" = "$2" ]
}

install_kubeconform() {
  local sha="$KUBECONFORM_SHA256_AMD64" file="kubeconform-linux-$arch.tar.gz"
  [ "$arch" = amd64 ] || sha="$KUBECONFORM_SHA256_ARM64"
  if installed kubeconform "$KUBECONFORM_VERSION" -v; then
    echo "kubeconform $KUBECONFORM_VERSION 은(는) 이미 설치되어 있습니다."
    return
  fi
  echo "kubeconform $KUBECONFORM_VERSION 설치"
  fetch "https://github.com/yannh/kubeconform/releases/download/$KUBECONFORM_VERSION/$file" "$tmp/$file" "$sha"
  tar -xzf "$tmp/$file" -C "$tmp" kubeconform
  install -m 0755 "$tmp/kubeconform" "$dir/kubeconform"
}

install_actionlint() {
  local sha="$ACTIONLINT_SHA256_AMD64" file="actionlint_${ACTIONLINT_VERSION}_linux_$arch.tar.gz"
  [ "$arch" = amd64 ] || sha="$ACTIONLINT_SHA256_ARM64"
  if installed actionlint "$ACTIONLINT_VERSION" -version; then
    echo "actionlint $ACTIONLINT_VERSION 은(는) 이미 설치되어 있습니다."
    return
  fi
  echo "actionlint $ACTIONLINT_VERSION 설치"
  fetch "https://github.com/rhysd/actionlint/releases/download/v$ACTIONLINT_VERSION/$file" "$tmp/$file" "$sha"
  tar -xzf "$tmp/$file" -C "$tmp" actionlint
  install -m 0755 "$tmp/actionlint" "$dir/actionlint"
}

install_hadolint() {
  local sha="$HADOLINT_SHA256_AMD64" file='hadolint-linux-x86_64'
  if [ "$arch" = arm64 ]; then
    sha="$HADOLINT_SHA256_ARM64"
    file='hadolint-linux-arm64'
  fi
  if installed hadolint "Haskell Dockerfile Linter ${HADOLINT_VERSION#v}" --version; then
    echo "hadolint $HADOLINT_VERSION 은(는) 이미 설치되어 있습니다."
    return
  fi
  echo "hadolint $HADOLINT_VERSION 설치"
  fetch "https://github.com/hadolint/hadolint/releases/download/$HADOLINT_VERSION/$file" "$tmp/$file" "$sha"
  install -m 0755 "$tmp/$file" "$dir/hadolint"
}

for tool in "${tools[@]}"; do
  "install_$tool"
done

if [ -n "${GITHUB_PATH:-}" ]; then
  echo "$dir" >>"$GITHUB_PATH"
else
  case ":$PATH:" in
    *":$dir:"*) ;;
    *) echo "참고: $dir 이(가) PATH 에 없습니다. export PATH=\"$dir:\$PATH\" 를 실행하세요." ;;
  esac
fi

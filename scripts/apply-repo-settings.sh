#!/usr/bin/env bash
# Applies this repository's governance settings through the GitHub REST API:
# security features, labels, the azure-demo environment, the main-protection ruleset
# and merge options. Dry-run by default; --apply is required to change anything.
# Works with bash 3.2 (macOS default) and later.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
RULESET_FILE="$REPO_ROOT/.github/rulesets/main-protection.json"
API_VERSION="2022-11-28"
ENVIRONMENT_NAME="azure-demo"
ALL_STEPS="security labels environment ruleset merge"
LABELS=(
  "dependencies|0366d6|Dependabot 등 의존성 업데이트 PR"
  "copilot-demo|1d76db|Copilot 데모용 시작 이슈"
)

apply=0
repo=""
repo_source=""
reviewer=""
core_only=0
only=""
failed=0

usage() {
  cat <<'EOF'
apply-repo-settings.sh - 저장소 설정(보안, 라벨, 환경, 룰셋, 머지 옵션)을 코드로 적용합니다.

기본은 dry-run입니다. 실행할 gh api 호출만 출력하고 아무것도 바꾸지 않습니다.
--apply를 붙여야 실제로 적용하며, 여러 번 실행해도 결과가 같습니다(멱등).

사용법:
  scripts/apply-repo-settings.sh [옵션]

옵션:
  --apply               실제로 적용합니다. (기본: dry-run)
  --repo <owner/name>   대상 저장소. 생략하면 GITHUB_REPOSITORY, git origin,
                        gh repo view 순서로 찾습니다.
  --reviewer <login>    azure-demo 환경의 배포 승인자로 지정할 GitHub 사용자.
  --only <단계,...>     지정한 단계만 실행합니다. (기본: 모두)
                        단계: security, labels, environment, ruleset, merge
  --core-rules-only     룰셋에서 code_scanning, copilot_code_review 규칙을 뺍니다.
                        룰셋 가져오기가 이 두 규칙 때문에 실패할 때 사용하세요.
  -h, --help            이 도움말을 보여 줍니다.

단계:
  security     Dependabot 알림(의존성 그래프 포함)과 보안 업데이트, secret scanning, push protection 켜기
               (CodeQL 기본 설정은 켜지 않습니다. 저장소가 직접 codeql.yml을 제공합니다.)
  labels       dependencies, copilot-demo 라벨 만들기 (없을 때만)
  environment  azure-demo 환경 만들기 (없을 때만). --reviewer가 있으면 승인자를 갱신
  ruleset      .github/rulesets/main-protection.json을 이름으로 찾아 갱신하고, 없으면 새로 만듭니다
  merge        squash 머지만 허용, 머지 후 브랜치 삭제, auto-merge 허용, 브랜치 업데이트 버튼

요구 사항:
  jq (dry-run 포함), gh 2.x (--apply에서만).
  --apply를 쓰려면 저장소 관리자 권한이 필요합니다.
  Codespaces의 기본 GITHUB_TOKEN으로는 권한이 부족할 수 있습니다. 'unset GITHUB_TOKEN' 명령을
  실행한 뒤 gh auth login으로 로그인하거나, 로컬 터미널에서 실행하세요.

예시:
  scripts/apply-repo-settings.sh                     # dry-run: 무엇이 실행될지만 확인
  scripts/apply-repo-settings.sh --apply             # 모든 단계 적용
  scripts/apply-repo-settings.sh --apply --only ruleset
  scripts/apply-repo-settings.sh --apply --only environment --reviewer octocat
EOF
}

usage_error() {
  printf '오류: %s\n\n' "$*" >&2
  usage >&2
  exit 2
}

fatal() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}

header() {
  printf '\n== %s: %s ==\n' "$1" "$2"
}

note() {
  printf '  # %s\n' "$*"
}

record_failure() {
  printf '    -> 실패: %s\n' "$1"
  failed=$((failed + 1))
}

# Read-only call used for lookups; only runs with --apply, and prints nothing itself.
gh_read() {
  gh api -H "X-GitHub-Api-Version: $API_VERSION" "$@"
}

# api METHOD PATH [JSON_BODY]: prints the gh api call, runs it only with --apply.
api() {
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    printf '  $ gh api --method %s %s --input -\n' "$method" "$path"
    jq . <<<"$body" | sed 's/^/      /'
  else
    printf '  $ gh api --method %s %s\n' "$method" "$path"
  fi
  [ "$apply" -eq 1 ] || return 0

  local ok=1
  if [ -n "$body" ]; then
    printf '%s' "$body" | gh_read --method "$method" "$path" --input - >/dev/null || ok=0
  else
    gh_read --method "$method" "$path" >/dev/null || ok=0
  fi
  if [ "$ok" -eq 1 ]; then
    printf '    -> 완료\n'
  else
    record_failure "$method $path"
  fi
}

# api_file METHOD PATH FILE: like api, with the request body read from a file.
api_file() {
  local method="$1" path="$2" file="$3"
  printf '  $ gh api --method %s %s --input %s\n' "$method" "$path" "${file#"$REPO_ROOT"/}"
  [ "$apply" -eq 1 ] || return 0

  if gh_read --method "$method" "$path" -H "Content-Type: application/json" --input "$file" >/dev/null; then
    printf '    -> 완료\n'
  else
    record_failure "$method $path"
  fi
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --apply) apply=1 ;;
      --repo | --reviewer | --only)
        if [ $# -lt 2 ] || [ -z "$2" ]; then
          usage_error "$1에는 값이 필요합니다."
        fi
        case "$1" in
          --repo) repo="$2" ;;
          --reviewer) reviewer="$2" ;;
          --only) only="$2" ;;
        esac
        shift
        ;;
      --repo=*) repo="${1#*=}" ;;
      --reviewer=*) reviewer="${1#*=}" ;;
      --only=*) only="${1#*=}" ;;
      --core-rules-only) core_only=1 ;;
      -h | --help)
        usage
        exit 0
        ;;
      *) usage_error "알 수 없는 옵션입니다: $1" ;;
    esac
    shift
  done

  if [ -n "$repo" ] && ! [[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    usage_error "--repo는 owner/name 형식이어야 합니다: $repo"
  fi
  if [ -n "$reviewer" ] && ! [[ "$reviewer" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]]; then
    usage_error "--reviewer에는 GitHub 사용자 이름(login)을 넣으세요: $reviewer"
  fi
  if [ -n "$only" ]; then
    local item
    local -a requested
    IFS=',' read -r -a requested <<<"$only"
    for item in "${requested[@]}"; do
      case " $ALL_STEPS " in
        *" $item "*) ;;
        *) usage_error "알 수 없는 단계입니다: $item (가능한 값: ${ALL_STEPS// /, })" ;;
      esac
    done
  fi
}

resolve_repo() {
  if [ -n "$repo" ]; then
    repo_source="--repo"
    return 0
  fi
  if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    repo="$GITHUB_REPOSITORY"
    repo_source="GITHUB_REPOSITORY"
    return 0
  fi

  local url
  url="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
  if [[ "$url" =~ (^|[/@])github\.com[:/]+([^/]+)/([^/]+)$ ]]; then
    repo="${BASH_REMATCH[2]}/${BASH_REMATCH[3]%.git}"
    repo_source="git origin"
    return 0
  fi

  if command -v gh >/dev/null 2>&1; then
    repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
    if [ -n "$repo" ]; then
      repo_source="gh repo view"
      return 0
    fi
  fi
  usage_error "대상 저장소를 알 수 없습니다. --repo owner/name 옵션으로 지정하세요."
}

preflight() {
  command -v gh >/dev/null 2>&1 || fatal "gh CLI가 필요합니다. 설치 안내: https://cli.github.com"
  if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    fatal "gh에 로그인되어 있지 않습니다. 'gh auth login' 명령을 실행하세요. (Codespaces에서는 먼저 'unset GITHUB_TOKEN' 명령을 실행)"
  fi
  local admin
  admin="$(gh_read "repos/$repo" --jq .permissions.admin 2>/dev/null || true)"
  if [ "$admin" != "true" ]; then
    fatal "$repo에 대한 관리자 권한을 확인하지 못했습니다. 저장소 관리자 계정으로 로그인했는지 확인하세요."
  fi
}

step_security() {
  header security "Dependabot 알림과 보안 업데이트, secret scanning, push protection"
  note "vulnerability-alerts 호출은 의존성 그래프(dependency graph)도 함께 켭니다. Dependency review에 필요합니다."
  api PUT "repos/$repo/vulnerability-alerts"
  api PUT "repos/$repo/automated-security-fixes"
  api PATCH "repos/$repo" "$(jq -nc '{security_and_analysis: {secret_scanning: {status: "enabled"}, secret_scanning_push_protection: {status: "enabled"}}}')"
  note "CodeQL 기본 설정(default setup)은 켜지 않습니다. 저장소가 고급 설정 워크플로(codeql.yml)를 제공합니다."
}

step_labels() {
  header labels "dependencies, copilot-demo 라벨 (이미 있으면 건너뜀)"
  local existing=""
  if [ "$apply" -eq 1 ]; then
    if ! existing="$(gh_read --paginate "repos/$repo/labels" --jq '.[].name')"; then
      record_failure "라벨 목록을 읽지 못했습니다"
      return 0
    fi
  else
    printf '  $ gh api --paginate repos/%s/labels --jq ".[].name"   # 이미 있는 라벨 조회\n' "$repo"
  fi

  local entry name color description
  for entry in "${LABELS[@]}"; do
    IFS='|' read -r name color description <<<"$entry"
    if [ "$apply" -eq 1 ] && grep -Fxiq -- "$name" <<<"$existing"; then
      printf '  = %s: 이미 있어 건너뜁니다\n' "$name"
      continue
    fi
    api POST "repos/$repo/labels" \
      "$(jq -nc --arg name "$name" --arg color "$color" --arg description "$description" '{name: $name, color: $color, description: $description}')"
  done
}

step_environment() {
  header environment "$ENVIRONMENT_NAME 환경 (없을 때만 생성, --reviewer가 있으면 승인자 갱신)"
  local path="repos/$repo/environments/$ENVIRONMENT_NAME"

  if [ "$apply" -eq 0 ]; then
    printf '  $ gh api --paginate repos/%s/environments   # 환경이 이미 있는지 조회\n' "$repo"
    if [ -n "$reviewer" ]; then
      printf '  $ gh api users/%s --jq .id   # 승인자 ID 조회\n' "$reviewer"
      api PUT "$path" "$(jq -nc --arg id "<사용자 ID: $reviewer>" '{prevent_self_review: false, reviewers: [{type: "User", id: $id}]}')"
    else
      api PUT "$path"
    fi
    return 0
  fi

  local existing
  if ! existing="$(gh_read --paginate "repos/$repo/environments" | jq -c --arg n "$ENVIRONMENT_NAME" '.environments[] | select(.name == $n)')"; then
    record_failure "환경 목록을 읽지 못했습니다"
    return 0
  fi

  local reviewer_id=""
  if [ -n "$reviewer" ]; then
    if ! reviewer_id="$(gh_read "users/$reviewer" --jq .id)"; then
      record_failure "사용자를 찾지 못했습니다: $reviewer"
      return 0
    fi
  fi

  if [ -z "$existing" ]; then
    if [ -n "$reviewer_id" ]; then
      api PUT "$path" "$(jq -nc --argjson id "$reviewer_id" '{prevent_self_review: false, reviewers: [{type: "User", id: $id}]}')"
    else
      api PUT "$path"
    fi
  elif [ -n "$reviewer_id" ]; then
    # PUT replaces the whole configuration, so carry over the wait timer and branch policy.
    api PUT "$path" "$(jq -c --argjson id "$reviewer_id" '{
      wait_timer: (([.protection_rules[]? | select(.type == "wait_timer") | .wait_timer] | first) // 0),
      prevent_self_review: false,
      reviewers: [{type: "User", id: $id}],
      deployment_branch_policy: .deployment_branch_policy
    }' <<<"$existing")"
  else
    printf '  = 이미 있어 변경하지 않습니다. 승인자를 지정하려면 --reviewer를 사용하세요.\n'
  fi
}

# send_ruleset METHOD PATH: sends the ruleset file, minus the optional rules with --core-rules-only.
send_ruleset() {
  local method="$1" path="$2"
  if [ "$core_only" -eq 1 ]; then
    api "$method" "$path" "$(jq -c '.rules |= map(select(.type != "code_scanning" and .type != "copilot_code_review"))' "$RULESET_FILE")"
  else
    api_file "$method" "$path" "$RULESET_FILE"
  fi
}

step_ruleset() {
  header ruleset "main-protection 룰셋 가져오기 (같은 이름이 있으면 갱신, 없으면 생성)"
  if [ ! -f "$RULESET_FILE" ]; then
    record_failure "${RULESET_FILE#"$REPO_ROOT"/} 파일이 없습니다"
    return 0
  fi

  local name
  name="$(jq -r .name "$RULESET_FILE")"
  jq -r '"  # 이름: \(.name), 적용: \(.enforcement), 규칙: \([.rules[].type] | join(", "))"' "$RULESET_FILE"
  if [ "$core_only" -eq 1 ]; then
    note "--core-rules-only: code_scanning, copilot_code_review 규칙은 보내지 않습니다."
  fi

  if [ "$apply" -eq 0 ]; then
    printf '  $ gh api --paginate "repos/%s/rulesets?includes_parents=false"   # 같은 이름의 룰셋 조회\n' "$repo"
    note "같은 이름의 룰셋이 없으면 생성합니다."
    send_ruleset POST "repos/$repo/rulesets"
    note "이미 있으면 위 호출 대신 해당 id로 갱신합니다."
    send_ruleset PUT "repos/$repo/rulesets/<id>"
    return 0
  fi

  local ids
  if ! ids="$(gh_read --paginate "repos/$repo/rulesets?includes_parents=false" | jq -r --arg n "$name" '.[] | select(.name == $n) | .id')"; then
    record_failure "룰셋 목록을 읽지 못했습니다"
    return 0
  fi
  local id="${ids%%$'\n'*}"
  if [ -z "$id" ]; then
    send_ruleset POST "repos/$repo/rulesets"
  else
    if [ "$ids" != "$id" ]; then
      printf '  ! 같은 이름의 룰셋이 여러 개입니다. 첫 번째(id=%s)만 갱신합니다.\n' "$id"
    fi
    send_ruleset PUT "repos/$repo/rulesets/$id"
  fi
}

step_merge() {
  header merge "PR 머지 옵션"
  note "squash 머지만 허용합니다(머지 커밋과 rebase 머지는 끔). 설정 화면에서 언제든 다시 켤 수 있습니다."
  api PATCH "repos/$repo" "$(jq -nc '{
    allow_squash_merge: true,
    allow_merge_commit: false,
    allow_rebase_merge: false,
    squash_merge_commit_title: "PR_TITLE",
    squash_merge_commit_message: "PR_BODY",
    delete_branch_on_merge: true,
    allow_auto_merge: true,
    allow_update_branch: true
  }')"
}

main() {
  parse_args "$@"
  command -v jq >/dev/null 2>&1 || fatal "jq가 필요합니다. 먼저 설치하세요."
  resolve_repo

  if [ "$apply" -eq 1 ]; then
    printf '모드: 적용(--apply)\n'
  else
    printf '모드: dry-run (아무것도 바꾸지 않습니다. 적용하려면 --apply)\n'
  fi
  printf '저장소: %s (출처: %s)\n' "$repo" "$repo_source"
  printf 'API 버전 헤더: X-GitHub-Api-Version: %s\n' "$API_VERSION"
  if [ "$apply" -eq 1 ]; then
    preflight
  fi

  local step
  for step in $ALL_STEPS; do
    if [ -n "$only" ]; then
      case ",$only," in
        *",$step,"*) ;;
        *) continue ;;
      esac
    fi
    "step_$step"
  done

  printf '\n'
  if [ "$apply" -eq 0 ]; then
    printf 'dry-run이 끝났습니다. 위 호출을 실제로 실행하려면 --apply를 붙이세요.\n'
  elif [ "$failed" -gt 0 ]; then
    printf '완료했지만 실패한 호출이 %s개 있습니다. 위 메시지를 확인하고 다시 실행하세요(멱등).\n' "$failed"
    exit 1
  else
    printf '모든 단계를 적용했습니다.\n'
  fi
}

main "$@"

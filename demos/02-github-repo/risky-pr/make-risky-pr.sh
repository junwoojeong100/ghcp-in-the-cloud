#!/usr/bin/env bash
# make-risky-pr.sh - 보안 검사를 시연할 "위험한 변경" 데모 PR을 만듭니다.
# 사용법은 --help로 확인하세요. 기본은 dry-run이며, --apply를 붙여야 실제로 실행합니다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PR_BODY_FILE="$SCRIPT_DIR/pr-body.md"
PR_TITLE="[DEMO – DO NOT MERGE] 의도적으로 위험한 변경 (Rulesets·CodeQL 시연용)"
COMMIT_MESSAGE="demo: 보안 검사 시연용 위험한 샘플 추가 (DO NOT MERGE)"

# 샘플(.sample)과 같은 상대 경로로 복사되는 새 파일입니다. 기존 파일은 수정하지 않습니다.
FILES=(
  "app/extras/debug_files.py"
  "app/extras/requirements.txt"
)
DIRS=("app/extras")
# 워크플로 파일을 push하려면 인증에 workflow 권한이 필요하므로 --no-workflow로 뺄 수 있게 따로 둡니다.
WORKFLOW_FILE=".github/workflows/triage.yml"

usage() {
  cat <<'EOF'
make-risky-pr.sh - 보안 검사를 시연하려고 일부러 위험하게 만든 데모 PR을 엽니다.

기본은 dry-run입니다. 할 일만 출력하고 아무것도 바꾸지 않습니다.
--apply를 붙이면 현재 HEAD에서 새 브랜치를 만들고, 샘플 파일을 복사해 커밋한 뒤,
그 브랜치만 push하고 PR을 엽니다. 기본 브랜치에는 push하지 않습니다.
PR 제목과 본문에는 "DEMO – DO NOT MERGE"가 표시됩니다.

사용법:
  demos/02-github-repo/risky-pr/make-risky-pr.sh [옵션]

옵션:
  --apply             실제로 실행합니다. (기본: dry-run)
  --branch <이름>     만들 브랜치 이름 (기본: demo/risky-change)
  --base <브랜치>     PR 대상 브랜치 (기본: origin의 기본 브랜치, 알 수 없으면 main)
  --no-workflow       triage.yml 샘플을 빼고 나머지 2개만 추가합니다. (아래 참고)
  -h, --help          이 도움말을 보여 줍니다.

추가되는 파일 (모두 새 파일이며, .sample을 뗀 이름으로 복사됩니다):
  app/extras/debug_files.py       경로 조작, 명령어 삽입, Flask 디버그 모드 (CodeQL)
  app/extras/requirements.txt     알려진 취약점이 있는 flask==2.2.4 (Dependency review)
  .github/workflows/triage.yml    이슈 제목을 셸에 그대로 넣는 expression injection (CodeQL)

워크플로 파일이 들어 있는 브랜치를 push하려면 인증에 workflow 권한이 필요합니다.
  gh 로그인:  gh auth refresh --scopes workflow
  개인용 토큰: 클래식은 workflow 스코프, 세분화된 토큰은 Workflows 쓰기 권한
권한을 줄 수 없으면(예: Codespaces의 기본 토큰) --no-workflow를 쓰세요.

--apply 조건:
  - 작업 트리가 깨끗해야 합니다. (커밋하지 않은 변경이나 추적되지 않는 파일이 없어야 함)
  - 현재 HEAD에 origin/<base>보다 앞선 커밋이 없어야 합니다. (보통 기본 브랜치에서 실행)
  - 같은 이름의 브랜치가 로컬과 origin에 없어야 하고, 대상 경로가 비어 있어야 합니다.
  - gh 로그인이 되어 있고 origin에 push할 수 있어야 합니다.
dry-run에서는 조건을 지키지 못한 항목을 경고로만 알려 줍니다.

정리:
  git switch <base> && gh pr close <브랜치> --delete-branch && git fetch --prune origin
EOF
}

die() {
  echo "오류: $1" >&2
  exit 1
}

usage_error() {
  echo "오류: $1" >&2
  echo >&2
  usage >&2
  exit 2
}

show_cmd() {
  local arg out="  \$"
  for arg in "$@"; do
    case "$arg" in
      *[!A-Za-z0-9_./:=@%+,-]*) out="$out \"$arg\"" ;;
      *) out="$out $arg" ;;
    esac
  done
  printf '%s\n' "$out"
}

# dry-run에서는 명령만 보여 주고, --apply에서는 보여 준 뒤 실행합니다.
act() {
  show_cmd "$@"
  if [ "$apply" -eq 1 ]; then
    "$@"
  fi
}

apply=0
no_workflow=0
branch="demo/risky-change"
base=""

while [ $# -gt 0 ]; do
  case "$1" in
    --apply)
      apply=1
      shift
      ;;
    --no-workflow)
      no_workflow=1
      shift
      ;;
    --branch | --base)
      if [ $# -lt 2 ] || [ -z "$2" ]; then
        usage_error "$1에는 값이 필요합니다."
      fi
      if [ "$1" = "--branch" ]; then
        branch="$2"
      else
        base="$2"
      fi
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage_error "알 수 없는 옵션입니다: $1"
      ;;
  esac
done

if [ "$no_workflow" -eq 0 ]; then
  FILES+=("$WORKFLOW_FILE")
  DIRS+=(".github/workflows")
fi

command -v git >/dev/null 2>&1 || die "git이 필요합니다."
repo_root="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)" || die "git 저장소 안에서 실행하세요."
cd "$repo_root"

case "$SCRIPT_DIR" in
  "$repo_root"/*) kit_dir="${SCRIPT_DIR#"$repo_root"/}" ;;
  *) kit_dir="$SCRIPT_DIR" ;;
esac

if [ -z "$base" ]; then
  base="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  base="${base#origin/}"
  [ -n "$base" ] || base="main"
fi
orig_ref="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse --short HEAD)"

[ -f "$PR_BODY_FILE" ] || die "PR 본문 파일이 없습니다: $kit_dir/pr-body.md"
for rel in "${FILES[@]}"; do
  [ -f "$SCRIPT_DIR/$rel.sample" ] || die "샘플 파일이 없습니다: $kit_dir/$rel.sample"
done

problems=()
notes=()
add_problem() {
  problems+=("$1")
}

collect_problems() {
  local rel ahead behind rc have_origin=1

  if ! git remote get-url origin >/dev/null 2>&1; then
    have_origin=0
    add_problem "origin 원격이 없습니다. (git remote -v로 확인)"
  fi

  if [ "$apply" -eq 1 ] && [ "$have_origin" -eq 1 ]; then
    git fetch --quiet origin "$base" || add_problem "origin/$base 브랜치를 가져오지 못했습니다. 네트워크와 로그인을 확인하세요."
  fi

  if [ -n "$(git status --porcelain)" ]; then
    add_problem "작업 트리에 커밋하지 않은 변경이나 추적되지 않는 파일이 있습니다. 먼저 정리하세요. (git status)"
  fi

  if ! git check-ref-format --branch "$branch" >/dev/null 2>&1; then
    add_problem "브랜치 이름이 올바르지 않습니다: $branch"
  fi
  case "$branch" in
    "$base" | main | master)
      add_problem "기본 브랜치에는 만들거나 push하지 않습니다. --branch로 다른 이름을 지정하세요: $branch"
      ;;
  esac
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    add_problem "같은 이름의 로컬 브랜치가 이미 있습니다: $branch (지우거나 --branch로 다른 이름을 지정하세요)"
  fi
  if [ "$apply" -eq 0 ] && git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    add_problem "origin에 같은 이름의 브랜치가 있다고 기록되어 있습니다: $branch (이미 지웠다면 'git fetch --prune origin' 명령으로 기록을 갱신하세요)"
  fi

  if git rev-parse --verify --quiet "refs/remotes/origin/$base" >/dev/null; then
    ahead="$(git rev-list --count "refs/remotes/origin/$base..HEAD")"
    behind="$(git rev-list --count "HEAD..refs/remotes/origin/$base")"
    if [ "$ahead" -gt 0 ]; then
      add_problem "현재 HEAD가 origin/$base보다 ${ahead}개 앞서 있어 관련 없는 커밋이 PR에 함께 들어갑니다. $base 브랜치로 옮긴 뒤(git switch $base) 다시 실행하세요."
    fi
    if [ "$behind" -gt 0 ]; then
      notes+=("현재 HEAD가 origin/$base보다 ${behind}개 뒤처져 있습니다. 최신 코드로 시연하려면 먼저 git pull을 실행하세요.")
    fi
  else
    add_problem "origin/$base 브랜치를 찾을 수 없습니다. 먼저 'git fetch origin $base' 명령을 실행하세요."
  fi

  for rel in "${FILES[@]}"; do
    if [ -e "$rel" ]; then
      add_problem "이미 있는 경로라 덮어쓰지 않습니다: $rel"
    fi
  done

  if [ "$apply" -eq 1 ]; then
    if ! command -v gh >/dev/null 2>&1; then
      add_problem "gh CLI가 필요합니다."
    elif ! gh auth status --hostname github.com >/dev/null 2>&1; then
      add_problem "gh에 로그인되어 있지 않습니다. 'gh auth login' 명령을 실행하세요."
    fi
    if ! git var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
      add_problem "git의 user.name과 user.email이 설정되어 있지 않습니다."
    fi
    if [ "$have_origin" -eq 1 ]; then
      if git ls-remote --exit-code --heads origin "refs/heads/$branch" >/dev/null 2>&1; then
        add_problem "origin에 같은 이름의 브랜치가 이미 있습니다: $branch"
      else
        rc=$?
        if [ "$rc" -ne 2 ]; then
          add_problem "origin에 접근하지 못했습니다. 네트워크와 로그인을 확인하세요."
        fi
      fi
      if [ "${#problems[@]}" -eq 0 ]; then
        git push --dry-run --quiet origin "HEAD:refs/heads/$branch" || add_problem "origin에 push할 수 없습니다. 권한과 로그인을 확인하세요."
      fi
    fi
  fi
}

branch_created=0
on_exit() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$branch_created" -eq 1 ]; then
    {
      echo
      echo "중간에 멈췄습니다. 지금 '$branch' 브랜치에 있습니다."
      echo "되돌리려면: git switch $orig_ref && git branch -D $branch"
      echo "이미 push했다면 원격 브랜치도 지우세요: git push origin --delete $branch"
      echo "커밋 전에 멈췄다면 복사된 파일(${FILES[*]})도 직접 지우세요."
    } >&2
  fi
}

# 워크플로 파일을 push할 권한이 없으면 push가 거부되므로, 실패하면 원인과 해결 방법을 알려 줍니다.
push_branch() {
  if act git push --set-upstream origin "refs/heads/$branch:refs/heads/$branch"; then
    return 0
  fi
  {
    echo
    echo "push에 실패했습니다. 오류 메시지에 workflow가 언급되어 있다면 인증에 워크플로 파일을 쓸 권한이 없는 것입니다."
    echo "  gh 로그인:  gh auth refresh --scopes workflow"
    echo "  개인용 토큰: 클래식은 workflow 스코프, 세분화된 토큰은 Workflows 쓰기 권한"
    echo "  권한을 줄 수 없으면 아래 방법으로 되돌린 뒤 --no-workflow로 다시 실행하세요."
  } >&2
  return 1
}

if [ "$apply" -eq 1 ]; then
  echo "모드: 적용(--apply)"
else
  echo "모드: dry-run (아무것도 바꾸지 않습니다. 적용하려면 --apply)"
fi
echo "현재 위치: $orig_ref"
echo "새 브랜치: $branch (PR 대상: $base)"
echo "PR 제목: $PR_TITLE"
echo

collect_problems

if [ "${#problems[@]}" -gt 0 ]; then
  if [ "$apply" -eq 1 ]; then
    echo "중단합니다. 아무것도 바꾸지 않았습니다. 아래를 해결한 뒤 다시 실행하세요." >&2
    for item in "${problems[@]}"; do
      echo "  - $item" >&2
    done
    exit 1
  fi
  echo "경고: 아래 문제가 있어 --apply로 실행하면 중단됩니다."
  for item in "${problems[@]}"; do
    echo "  - $item"
  done
  echo
fi
if [ "${#notes[@]}" -gt 0 ]; then
  for item in "${notes[@]}"; do
    echo "참고: $item"
  done
  echo
fi

trap on_exit EXIT

echo "실행 순서:"
act git switch -c "$branch"
branch_created=$apply
act mkdir -p "${DIRS[@]}"
for rel in "${FILES[@]}"; do
  act cp "$kit_dir/$rel.sample" "$rel"
done
act git add -- "${FILES[@]}"
act git commit --quiet --message "$COMMIT_MESSAGE"
push_branch
pr_cmd=(gh pr create --base "$base" --head "$branch" --title "$PR_TITLE" --body-file "$kit_dir/pr-body.md")
show_cmd "${pr_cmd[@]}"

if [ "$apply" -eq 1 ]; then
  pr_url="$("${pr_cmd[@]}")"
  branch_created=0
  echo
  echo "PR을 열었습니다: $pr_url"
  echo "PR 화면의 Checks 탭과 Files changed에서 CodeQL, Dependency review, Copilot code review 결과를 확인하세요."
  echo "시연이 끝나면 정리하세요:"
  echo "  git switch $base"
  echo "  gh pr close $branch --delete-branch"
  echo "  git fetch --prune origin"
else
  echo
  echo "dry-run이 끝났습니다. 위 명령을 실제로 실행하려면 --apply를 붙이세요."
fi

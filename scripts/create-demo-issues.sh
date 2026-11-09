#!/usr/bin/env bash
# demos/01-github-copilot/issues/*.md 의 시작 이슈를 GitHub 이슈로 만듭니다.
# 기본은 dry-run(실행할 gh 명령만 출력)이고, --apply 를 줘야 실제로 실행합니다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISSUES_DIR="demos/01-github-copilot/issues"
LABEL_NAME="copilot-demo"
LABEL_COLOR="1d76db"
LABEL_DESCRIPTION="Copilot 데모용 시작 이슈"

APPLY=false
ASSIGN_COPILOT=false
ONLY=""
REPO=""
HAVE_GH=true
COPILOT_SUPPORTED=true
OPEN_ISSUES=""
OPEN_KNOWN=false
CREATED=0
ASSIGNED=0
SKIPPED=0

usage() {
  cat <<'EOF'
사용법: scripts/create-demo-issues.sh [옵션]

demos/01-github-copilot/issues/*.md 의 시작 이슈를 GitHub 이슈로 만듭니다.
기본은 dry-run 이라서 실행할 gh 명령만 출력하고 아무것도 바꾸지 않습니다.

옵션:
  --apply             레이블과 이슈를 실제로 만듭니다.
  --assign-copilot    만든 이슈를 Copilot 에게 할당합니다. 에이전트 세션이 시작됩니다.
  --only 1,3          파일 이름 앞 번호가 일치하는 이슈만 처리합니다.
  --repo OWNER/REPO   대상 저장소입니다. 생략하면 현재 저장소(또는 GH_REPO)를 씁니다.
  -h, --help          이 도움말을 출력합니다.

동작:
  - 제목이 같은 열린 이슈가 있으면 건너뜁니다. 여러 번 실행해도 안전합니다.
  - 레이블 copilot-demo 가 없으면 --apply 일 때 만듭니다.
  - --assign-copilot 은 gh 2.76 이상이 필요하고 GitHub Enterprise Server 에서는 지원되지 않습니다.
    지원하지 않거나 실패하면 이슈만 만들고 수동 할당 방법을 안내합니다.
  - 저장소에서 Copilot cloud agent 가 켜져 있어야 하고, 쓰기 권한이 있는 계정으로
    gh auth login 을 먼저 해야 합니다.

예시:
  scripts/create-demo-issues.sh                            # 미리보기
  scripts/create-demo-issues.sh --apply --only 3           # 3번 이슈만 생성
  scripts/create-demo-issues.sh --apply --assign-copilot   # 생성하고 Copilot 에게 할당
EOF
}

info() { printf '%s\n' "$*"; }
warn() { printf '경고: %s\n' "$*" >&2; }
die() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}
usage_error() {
  printf '오류: %s\n자세한 사용법은 --help 를 보세요.\n' "$*" >&2
  exit 2
}

# Single-quote a word so the printed command can be pasted into a shell.
quote() {
  local word="$1" sq="'"
  printf "'%s'" "${word//$sq/$sq\\$sq$sq}"
}

print_cmd() {
  local out="" word
  for word in "$@"; do
    if [[ $word =~ ^[A-Za-z0-9_./:=@%+-]+$ ]]; then
      out+=" $word"
    else
      out+=" $(quote "$word")"
    fi
  done
  printf '%s\n' "${out# }"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --apply) APPLY=true ;;
      --assign-copilot) ASSIGN_COPILOT=true ;;
      --only)
        [[ $# -ge 2 ]] || usage_error "--only 에는 번호 목록이 필요합니다. 예: --only 1,3"
        ONLY="$2"
        shift
        ;;
      --only=*) ONLY="${1#*=}" ;;
      --repo)
        [[ $# -ge 2 ]] || usage_error "--repo 에는 OWNER/REPO 가 필요합니다."
        REPO="$2"
        shift
        ;;
      --repo=*) REPO="${1#*=}" ;;
      -h | --help)
        usage
        exit 0
        ;;
      *) usage_error "알 수 없는 옵션입니다: $1" ;;
    esac
    shift
  done

  if [[ -n $ONLY && ! $ONLY =~ ^[0-9]+(,[0-9]+)*$ ]]; then
    usage_error "--only 값은 쉼표로 구분한 번호여야 합니다. 예: --only 1,3"
  fi
  if [[ -n $REPO && ! $REPO =~ ^([A-Za-z0-9.-]+/)?[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    usage_error "--repo 값은 OWNER/REPO 형식이어야 합니다."
  fi
}

# Number prefix of an issue file such as 01-rate-limit.md.
file_number() {
  local base
  base="$(basename "$1")"
  printf '%d' "$((10#${base:0:2}))"
}

number_requested() {
  local want="$1" n
  local -a nums
  IFS=',' read -r -a nums <<<"$ONLY"
  for n in "${nums[@]}"; do
    if [[ $((10#$n)) -eq $want ]]; then
      return 0
    fi
  done
  return 1
}

issue_title() {
  local line=""
  IFS= read -r line <"$1" || true
  if [[ $line != "# "* ]]; then
    die "$1: 첫 줄은 '# 제목' 형식이어야 합니다."
  fi
  printf '%s' "${line#\# }"
}

# Fills OPEN_ISSUES with "number<TAB>title" lines; OPEN_KNOWN says whether that worked.
load_open_issues() {
  OPEN_KNOWN=false
  OPEN_ISSUES=""
  if ! $HAVE_GH; then
    return 0
  fi
  if OPEN_ISSUES="$(gh issue list --state open --limit 200 --json number,title \
    --jq '.[] | "\(.number)\t\(.title)"' 2>/dev/null)"; then
    OPEN_KNOWN=true
  else
    OPEN_ISSUES=""
  fi
}

open_issue_number() {
  printf '%s\n' "$OPEN_ISSUES" | TITLE="$1" awk -F '\t' '$2 == ENVIRON["TITLE"] { print $1; exit }'
}

# Returns 0 when the label exists, 1 when it is missing, 2 when that could not be checked.
label_status() {
  local names
  if ! names="$(gh label list --search "$LABEL_NAME" --limit 100 --json name --jq '.[].name' 2>/dev/null)"; then
    return 2
  fi
  if printf '%s\n' "$names" | grep -Fxq -- "$LABEL_NAME"; then
    return 0
  fi
  return 1
}

ensure_label() {
  local status=2
  if $HAVE_GH; then
    status=0
    label_status || status=$?
  fi
  if [[ $status -eq 0 ]]; then
    info "레이블 $LABEL_NAME: 이미 있습니다."
    return 0
  fi
  if $APPLY; then
    if gh label create "$LABEL_NAME" --color "$LABEL_COLOR" --description "$LABEL_DESCRIPTION" >/dev/null; then
      info "레이블 $LABEL_NAME: 만들었습니다."
    else
      warn "레이블 $LABEL_NAME 을 만들지 못했습니다. 이미 있거나 권한이 없을 수 있습니다. 계속합니다."
    fi
    return 0
  fi
  if [[ $status -eq 1 ]]; then
    info "레이블 $LABEL_NAME: 없습니다. --apply 를 주면 아래 명령으로 만듭니다."
  else
    info "레이블 $LABEL_NAME: 있는지 확인하지 못했습니다. 없으면 --apply 가 아래 명령으로 만듭니다."
  fi
  print_cmd gh label create "$LABEL_NAME" --color "$LABEL_COLOR" --description "$LABEL_DESCRIPTION"
}

# gh 2.76 이상이 --assignee @copilot 을 도움말에 적어 둡니다.
detect_copilot_support() {
  local help_text=""
  help_text="$(gh issue create --help 2>&1)" || true
  [[ $help_text == *"@copilot"* ]]
}

create_command() {
  local file="$1" title="$2" assign="$3"
  local -a cmd=(gh issue create --title "$title" --label "$LABEL_NAME")
  if [[ $assign == true ]]; then
    cmd+=(--assignee "@copilot")
  fi
  cmd+=(--body-file -)
  # The first line is the title and the second is blank; the rest is the issue body.
  printf 'tail -n +3 %s | ' "$(quote "$file")"
  print_cmd "${cmd[@]}"
}

run_create() {
  local file="$1" title="$2" assign="$3"
  local -a cmd=(gh issue create --title "$title" --label "$LABEL_NAME")
  if [[ $assign == true ]]; then
    cmd+=(--assignee "@copilot")
  fi
  tail -n +3 "$file" | "${cmd[@]}" --body-file -
}

manual_assign_hint() {
  local number="$1"
  info "  Copilot 할당은 이슈의 Assignees 에서 Copilot 을 고르거나 다음 명령을 실행하세요:"
  info "    gh issue edit $number --add-assignee @copilot"
}

process_issue() {
  local file="$1" title existing url assign=false
  title="$(issue_title "$file")"

  existing="$(open_issue_number "$title")"
  if [[ -n $existing ]]; then
    info "건너뜀: 같은 제목의 열린 이슈가 있습니다 (#$existing) - $title"
    if $ASSIGN_COPILOT; then
      manual_assign_hint "$existing"
    fi
    SKIPPED=$((SKIPPED + 1))
    return 0
  fi

  if $ASSIGN_COPILOT && $COPILOT_SUPPORTED; then
    assign=true
  fi

  if ! $APPLY; then
    info "만들 이슈: $title"
    create_command "$file" "$title" "$assign"
    return 0
  fi

  if url="$(run_create "$file" "$title" "$assign")"; then
    info "만듦: $url"
    CREATED=$((CREATED + 1))
    if [[ $assign == true ]]; then
      ASSIGNED=$((ASSIGNED + 1))
    elif $ASSIGN_COPILOT; then
      manual_assign_hint "${url##*/}"
    fi
    return 0
  fi

  if [[ $assign == false ]]; then
    die "이슈를 만들지 못했습니다: $title"
  fi

  warn "Copilot 할당과 함께 만들지 못했습니다. 이슈가 만들어졌는지 확인합니다: $title"
  load_open_issues
  existing="$(open_issue_number "$title")"
  if [[ -n $existing ]]; then
    warn "이슈는 만들어졌습니다 (#$existing). Copilot 할당만 수동으로 하세요."
    manual_assign_hint "$existing"
    CREATED=$((CREATED + 1))
  elif url="$(run_create "$file" "$title" false)"; then
    info "할당 없이 만듦: $url"
    manual_assign_hint "${url##*/}"
    CREATED=$((CREATED + 1))
  else
    die "이슈를 만들지 못했습니다: $title"
  fi
}

main() {
  parse_args "$@"
  cd "$ROOT"

  if [[ -n $REPO ]]; then
    export GH_REPO="$REPO"
  fi

  local -a files=() selected=()
  local file n found
  shopt -s nullglob
  files=("$ISSUES_DIR"/[0-9][0-9]-*.md)
  shopt -u nullglob
  if [[ ${#files[@]} -eq 0 ]]; then
    die "$ISSUES_DIR 에 이슈 파일(NN-이름.md)이 없습니다."
  fi

  if [[ -n $ONLY ]]; then
    local -a wanted
    IFS=',' read -r -a wanted <<<"$ONLY"
    for n in "${wanted[@]}"; do
      found=false
      for file in "${files[@]}"; do
        if [[ $(file_number "$file") -eq $((10#$n)) ]]; then
          found=true
        fi
      done
      if ! $found; then
        die "번호 $((10#$n)) 에 해당하는 이슈 파일이 없습니다."
      fi
    done
  fi
  for file in "${files[@]}"; do
    if [[ -z $ONLY ]] || number_requested "$(file_number "$file")"; then
      selected+=("$file")
    fi
  done

  if ! command -v gh >/dev/null 2>&1; then
    HAVE_GH=false
    if $APPLY; then
      die "gh CLI 를 찾을 수 없습니다. gh 를 설치하고 gh auth login 을 실행하세요."
    fi
    warn "gh CLI 를 찾을 수 없습니다. 열린 이슈 확인은 건너뛰고 명령만 출력합니다."
  fi

  if $ASSIGN_COPILOT && $HAVE_GH && ! detect_copilot_support; then
    COPILOT_SUPPORTED=false
    warn "이 gh 는 --assignee @copilot 을 지원하지 않는 것 같습니다 (gh 2.76 이상 필요). 이슈만 만들고 수동 할당 방법을 안내합니다."
  fi

  load_open_issues
  if ! $OPEN_KNOWN && $HAVE_GH; then
    if $APPLY; then
      die "열린 이슈 목록을 읽지 못했습니다. gh auth status 로 로그인과 저장소를 확인하세요."
    fi
    warn "열린 이슈 목록을 읽지 못해 중복 검사를 건너뜁니다. gh auth login 이 필요할 수 있습니다."
  fi

  if $APPLY; then
    info "[apply] ${GH_REPO:-현재 저장소}에 이슈를 만듭니다."
  else
    info "[dry-run] 아무것도 만들지 않습니다. 아래는 저장소 루트에서 실행할 명령입니다."
    info "[dry-run] 대상 저장소: ${GH_REPO:-현재 저장소}"
  fi
  ensure_label

  for file in "${selected[@]}"; do
    process_issue "$file"
  done

  if $APPLY; then
    if $ASSIGN_COPILOT; then
      info "요약: 만든 이슈 $CREATED개 (Copilot 할당 $ASSIGNED개), 건너뜀 $SKIPPED개."
    else
      info "요약: 만든 이슈 $CREATED개, 건너뜀 $SKIPPED개."
    fi
    if [[ $ASSIGNED -gt 0 ]]; then
      info "Copilot 이 시작하면 이슈에 눈(👀) 반응이 붙고 잠시 뒤 초안(draft) PR 이 열립니다. 이슈 타임라인에서 확인하세요."
    fi
  else
    local suggest="scripts/create-demo-issues.sh --apply"
    if $ASSIGN_COPILOT; then
      suggest+=" --assign-copilot"
    fi
    if [[ -n $ONLY ]]; then
      suggest+=" --only $ONLY"
    fi
    if [[ -n $REPO ]]; then
      suggest+=" --repo $REPO"
    fi
    info "[dry-run] 실제로 만들려면: $suggest"
  fi
}

main "$@"

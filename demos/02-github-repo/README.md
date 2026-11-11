# Demo 2 — GitHub Repo: 안전한 협업의 기본값, Rulesets·보안·Codespaces

main 브랜치 보호, 코드 오너, 코드·공급망 보안 검사를 모두 저장소 안의 파일과 스크립트로 정의합니다. 새 기여자는 Codespaces로 클릭 몇 번이면 실행 가능한 개발 환경을 얻고, 마지막에는 일부러 위험하게 만든 PR을 열어 자동 검사가 그 변경을 잡아내는 모습을 보여 줍니다.

> **연습용 저장소에서 먼저 해 보세요**: 2단계 스크립트는 저장소 설정(보안 기능, 룰셋, 머지 옵션)을 바꾸고, 3단계 스크립트는 PR을 엽니다. 두 스크립트 모두 기본은 dry-run이지만, 발표 전에 연습용 저장소(템플릿으로 새로 만들거나 포크)에서 한 번 리허설하세요.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | 저장소 보호와 보안 설정이 코드로 정의돼 있음을 보여 주고, 새 기여자가 Codespaces로 바로 시작하며, 위험한 PR이 자동 검사에 걸리는 모습을 확인합니다. |
| 시간 | 약 6분(1단계 1분, 2단계 2분, 3단계 2분, 4단계 1분). Codespace 생성, 룰셋 적용, 위험한 PR의 CodeQL 분석에는 각각 몇 분이 걸리므로 시연 전에 미리 준비하세요. |
| 난이도 | 보통. 룰셋과 보안 설정을 적용하려면 저장소 관리자(Admin) 권한이 필요합니다. |
| 독립 실행 | 예. GitHub 저장소만 있으면 됩니다. Azure 구독은 필요 없습니다. Copilot 라이선스는 3단계에서 Copilot code review를 볼 때만 필요합니다. |

```text
Codespaces 열기 → 테스트 실행 → 룰셋·CODEOWNERS 확인과 적용 → 위험한 PR → CodeQL·Dependency review·Copilot review → Dependabot 확인
```

| 경로 | 역할 |
|---|---|
| `.github/rulesets/main-protection.json` | main 보호 룰셋. GitHub에 그대로 가져올 수 있는 JSON |
| `.github/CODEOWNERS` | 경로별 리뷰 책임자 |
| `.github/dependabot.yml` | 의존성 업데이트 설정 |
| `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/config.yml` | PR 작성 틀, 빈 이슈 차단과 안내 링크 |
| `.devcontainer/` | Codespaces와 Dev Container 설정, `post-create.sh` |
| `scripts/apply-repo-settings.sh` | 보안 기능, 라벨, 환경, 룰셋, 머지 옵션을 한 번에 적용(기본은 dry-run) |
| `demos/02-github-repo/risky-pr/` | 위험한 PR을 만드는 키트: `make-risky-pr.sh`, `.sample` 파일 3개, PR 본문 |

실제 검사는 `.github/workflows/`의 `ci.yml`, `codeql.yml`, `dependency-review.yml`이 수행합니다. 다른 데모와 함께 쓰는 저장소 공통 파일이라 위 표에는 넣지 않았습니다.

## 왜 이 서비스인가 (이점)

- **main 보호(Rulesets)**: 기본 브랜치는 PR로만 바뀌고, 승인·필수 체크·코드 스캐닝 조건을 통과해야 merge됩니다. 삭제와 force push는 막힙니다.
- **책임 분리(CODEOWNERS)**: PR이 바꾼 경로의 책임자가 자동으로 리뷰어가 되고, 룰셋과 함께 쓰면 그 승인이 필수가 됩니다.
- **코드와 공급망 보안**: CodeQL은 코드와 워크플로의 취약점을, Dependency review는 PR이 새로 들이는 의존성의 알려진 취약점을 merge 전에 알려 줍니다. Dependabot은 의존성 업데이트를 정해진 주기에 PR로 올립니다. secret scanning은 저장소의 비밀을 찾아 알리고, push protection은 비밀이 든 push를 저장소에 닿기 전에 막습니다.
- **AI 보조 리뷰(Copilot code review)**: PR마다 AI가 첫 리뷰를 달아, 사람 리뷰어가 핵심 판단에 집중하도록 돕습니다. 승인은 여전히 사람이 합니다.
- **빠른 시작(Codespaces와 dev container)**: 새 기여자가 클릭 몇 번으로 Python 3.12, Azure CLI, GitHub CLI, kubectl, Docker가 갖춰진 환경을 얻습니다. 로컬에 설치할 것이 없고 비밀은 저장소에 없습니다.
- **설정의 코드화**: 룰셋 JSON과 `apply-repo-settings.sh`가 저장소 설정을 파일로 만듭니다. 설정 변경도 PR로 리뷰하고, 다른 저장소에 가져가고, 몇 번이든 같은 결과로 다시 적용할 수 있습니다.

## 사전 준비

꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

1. **저장소 관리자 권한과 연습용 저장소**: 룰셋, 보안 기능, 환경을 바꾸려면 저장소 관리자(Admin) 권한이 필요합니다. 이 저장소를 템플릿으로 새로 만들었거나 포크한 연습용 저장소를 쓰세요(만드는 명령은 [DEMO_GUIDE_KO.md](../../DEMO_GUIDE_KO.md)의 체크리스트에 있습니다). 스크립트는 현재 폴더의 `origin`을 대상으로 하며 `--repo <owner>/<name>`으로 바꿀 수 있습니다. 연습용 저장소라면 `.github/CODEOWNERS`의 `@junwoojeong100`을 자신의 계정(또는 팀)으로 바꾸세요. 코드 오너는 저장소에 쓰기 권한이 있어야 동작합니다.
2. **터미널 도구**: `git`, `jq`, 로그인한 `gh`(`gh auth login`)가 필요합니다. 3단계는 새 워크플로 파일이 든 브랜치를 push하므로 로그인 토큰에 **`workflow` 권한**이 있어야 합니다. `gh auth status`의 Token scopes에 `workflow`가 없으면 `gh auth refresh --scopes workflow`로 추가하세요.
3. **개발 환경**: 1단계는 Codespaces에서 합니다. 로컬에서 하려면 Python 3.12와 `git`이면 충분합니다.
4. **공통 워크플로는 기본 브랜치에**: `ci.yml`, `codeql.yml`, `dependency-review.yml`이 main에 있고 PR마다 실행돼야 필수 체크와 코드 스캐닝 규칙이 의미를 가집니다. 이 데모의 파일도 모두 main에 merge된 상태에서 시작하세요.
5. **Copilot 라이선스(선택)**: Copilot code review를 보려면 PR을 연 사람이 Copilot을 쓸 수 있어야 합니다. 룰셋의 자동 리뷰 사용량은 기본적으로 PR 작성자에게 귀속됩니다. 라이선스가 없으면 그 부분은 말로 설명하세요.
6. **플랜**: 공개 저장소에서는 룰셋, secret scanning, 코드 스캐닝(CodeQL), Dependency review를 모두 쓸 수 있습니다. 비공개 저장소는 플랜과 보안 제품 구성에 따라 일부가 제한될 수 있으니 GitHub 문서에서 확인하세요.

### 시연 10~15분 전에 해 둘 일

- [ ] Codespace를 하나 만들어 둡니다. 생성이 끝난 상태에서 시작하면 대기 시간이 없습니다.
- [ ] 2단계의 `--apply`를 미리 실행해 룰셋, 라벨, 환경을 준비합니다. 청중 앞에서는 dry-run과 결과 화면만 보여 주면 됩니다.
- [ ] main에서 `ci.yml`이 한 번 이상 실행됐는지 확인합니다. 룰셋의 필수 체크 이름은 실행 기록이 있어야 선택 목록에 나타납니다.
- [ ] 3단계의 PR을 미리 열어 CodeQL 분석이 끝난 화면을 준비합니다. 라이브로 만들면 분석이 끝날 때까지 몇 분을 기다려야 합니다.

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 아래 클릭 경로는 작성 시점 기준입니다. 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요. (예: Security 탭이 Security and quality로 보일 수 있습니다.)

각 단계 끝의 **성공 기준**은 무엇이 보이면 성공인지 정리한 것입니다. 명령은 저장소 루트에서 실행합니다.

### 1. Codespaces로 열고 테스트 실행 (약 1분)

1. 저장소 페이지에서 **Code → Codespaces → Create codespace on main**을 누릅니다. 앱 로그인 비밀번호를 미리 정해 두려면 Codespaces 탭 오른쪽 위의 `⋯` 메뉴에서 **New with options**를 고르고 `DEMO_PASSWORD` 칸에 시연용 임시 값을 입력합니다. 건너뛰어도 됩니다.
2. Codespace가 열리면 이 README가 자동으로 열립니다. `.devcontainer/post-create.sh`는 `app/requirements.txt`를 설치하고 도구 버전과 다음 단계 안내를 터미널에 출력합니다.
3. 테스트를 실행합니다.

   ```bash
   python -m unittest discover -s app/tests -v
   ```

4. 앱을 mock 모드로 실행합니다. Azure나 Foundry 없이 돌아갑니다.

   ```bash
   export DEMO_PASSWORD='<시연용 임시 값>'   # Codespaces 시크릿으로 넣었다면 생략
   LLM_BACKEND=mock python -m app.server
   ```

   `<시연용 임시 값>`은 발표자가 정하는 임시 값으로 바꾸세요. 값은 저장소나 문서에 적지 않습니다.
5. 새 터미널을 열어 확인합니다.

   ```bash
   curl -s http://localhost:8080/healthz
   curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/
   ```

   PORTS 탭의 8080 링크를 열면 로그인 창이 뜹니다. 사용자 이름은 `demo`, 비밀번호는 위에서 정한 값입니다.

성공 기준:

- 테스트 출력의 마지막 줄이 `OK`입니다.
- 서버 로그에 `Listening on http://127.0.0.1:8080 (backend=mock)`가 보입니다.
- `/healthz`는 `{"status": "ok"}`를 돌려주고, 인증 없이 `/`를 호출하면 `401`입니다.
- PORTS 탭에 8080이 `Cloud Copilot Demo`라는 이름으로 전달돼 있습니다.

Codespace에는 Python 3.12, Azure CLI(Bicep 포함), GitHub CLI, kubectl, Docker와 VS Code 확장(Copilot, Python, Bicep, GitHub Actions, Docker, Kubernetes)이 미리 들어 있습니다. CI와 같은 검사 도구(actionlint, kubeconform, hadolint)도 가능하면 함께 설치됩니다. "로컬에 아무것도 설치하지 않았다"는 점을 말해 주세요.

### 2. Rulesets와 CODEOWNERS 확인, 설정 적용 (약 2분)

`.github/rulesets/main-protection.json`을 엽니다. 규칙마다 이유가 있습니다.

| 규칙 | 설정 | 왜 필요한가 |
|---|---|---|
| 대상 | 기본 브랜치(`~DEFAULT_BRANCH`), `enforcement: active` | 기본 브랜치 이름이 `main`이 아니어도 따라갑니다. |
| `deletion` | 삭제 금지 | 기본 브랜치를 실수로 지우는 사고를 막습니다. |
| `non_fast_forward` | force push 금지 | 이력을 덮어써서 변경 기록이 사라지는 일을 막습니다. |
| `pull_request` | 승인 1건, 새 push가 오면 기존 승인 취소, 코드 오너 리뷰 필수, 리뷰 대화 해결 필수 | 모든 변경이 다른 사람의 눈을 거치고, 승인 뒤에 바뀐 코드가 검토 없이 merge되지 않습니다. `require_last_push_approval`(마지막 push를 한 사람이 아닌 다른 사람의 승인)은 1인 시연을 위해 꺼 뒀습니다. 팀 저장소에서는 켜는 것을 권합니다. |
| `required_status_checks` | `Unit tests`, `Container build and smoke test`, `IaC validation`. `strict` 켜짐, `integration_id` 15368 | 세 검사를 통과해야 merge됩니다. `strict`는 PR이 최신 main을 포함한 상태에서 검사를 통과해야 한다는 뜻입니다. `integration_id`는 GitHub Actions 앱의 ID로, 같은 이름의 외부 상태가 필수 체크 행세를 하지 못하게 합니다. |
| `code_scanning` | 도구 `CodeQL`, 알림 `errors`, 보안 알림 `high_or_higher` | PR에서 기준 이상의 알림이 나오거나, 분석이 아직 끝나지 않았거나, 도구가 설정돼 있지 않으면 merge할 수 없습니다. 3단계의 위험한 PR을 막는 규칙입니다. |
| `copilot_code_review` | push마다 리뷰 꺼짐, 초안 PR 리뷰 꺼짐 | PR을 열면 Copilot이 자동으로 리뷰합니다. push마다 반복하거나 초안까지 리뷰하지 않아 소음과 사용량을 줄입니다. |
| `bypass_actors` | 저장소 Admin 역할, 모드 `pull_request` | 아래 "1인 저장소의 타협"을 보세요. |

Copilot의 리뷰는 기본적으로 필수 승인 수에 들어가지 않으므로, 사람의 승인은 그대로 필요합니다. 각 규칙의 자세한 설명은 [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)에 있습니다.

**1인 저장소의 타협**: PR 작성자는 자기 PR을 승인할 수 없고 코드 오너 리뷰도 필요하므로, 혼자 쓰는 저장소에서는 자기 PR을 merge할 수 없게 됩니다. 그래서 저장소 Admin 역할에 `pull_request` 모드의 우회(bypass)를 줬습니다. 이 모드는 PR을 통한 merge에만 우회를 허용하므로 직접 push와 브랜치 삭제는 여전히 막힙니다. 다만 우회는 룰셋 전체에 적용돼서 관리자는 필수 체크와 코드 스캐닝 조건도 건너뛸 수 있습니다. 그래서 3단계의 위험한 PR은 merge 상자에 우회 옵션이 보여도 **절대 merge하지 않습니다**. 팀 저장소에서는 `bypass_actors`를 비우거나 비상용 역할로 좁히세요.

**CODEOWNERS**: `.github/CODEOWNERS`는 `*`, `/app/`, `/infra/`, `/.github/`, `/slides/`, `/demos/`의 오너를 `@junwoojeong100`으로 지정합니다. 마지막으로 일치하는 패턴이 우선합니다. PR이 해당 경로를 바꾸면 오너가 자동으로 리뷰어가 되고, 룰셋의 코드 오너 리뷰 규칙 때문에 그 승인이 있어야 merge됩니다. 실제 팀에서는 개인 대신 `@org/team`을 쓰세요. 팀에도 저장소 쓰기 권한이 있어야 합니다. 자세한 문법은 [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)를 참고하세요.

**PR 템플릿과 이슈 설정**: `.github/PULL_REQUEST_TEMPLATE.md`는 PR 본문에 변경 요약, 변경 유형, 검증 방법과 결과, 보안 체크리스트(비밀 없음, 최소 권한, 입력 검증), 문서·슬라이드 영향, 관련 이슈(`Closes #`)를 채우게 합니다. `.github/ISSUE_TEMPLATE/config.yml`은 빈 이슈를 막고 이슈 폼만 쓰게 합니다.

이제 이 설정을 저장소에 적용합니다.

```bash
scripts/apply-repo-settings.sh            # dry-run: 실행할 gh api 호출만 출력
scripts/apply-repo-settings.sh --apply    # 실제 적용 (저장소 관리자 권한 필요)
```

| 단계 | 하는 일 |
|---|---|
| `security` | Dependabot 알림(의존성 그래프 포함)과 보안 업데이트, secret scanning, push protection을 켭니다. CodeQL "기본 설정"(default setup)은 켜지 않습니다. 이 저장소가 직접 `codeql.yml`을 제공하기 때문입니다. |
| `labels` | `dependencies`, `copilot-demo` 라벨을 없을 때만 만듭니다. Dependabot PR과 Demo 1의 이슈가 사용합니다. |
| `environment` | `azure-demo` 환경을 없을 때만 만듭니다. `--reviewer <GitHub 사용자 이름>`을 주면 배포 승인자를 지정합니다. |
| `ruleset` | `main-protection.json`을 이름으로 찾아 있으면 갱신(PUT)하고 없으면 새로 만듭니다(POST). |
| `merge` | squash merge만 허용하고, merge 뒤 브랜치를 자동 삭제하며, auto-merge와 "Update branch" 버튼을 허용합니다. |

옵션: `--repo <owner>/<name>`(대상 저장소), `--only <단계,...>`(일부 단계만. 예: `--only ruleset`), `--core-rules-only`(룰셋에서 `code_scanning`과 `copilot_code_review`를 뺍니다). `--apply`에는 관리자 권한이 필요합니다. Codespace의 기본 토큰으로는 부족할 수 있으니 로컬 터미널에서 실행하거나, Codespace에서는 `unset GITHUB_TOKEN`을 실행한 뒤 `gh auth login`으로 로그인하세요. 스크립트 대신 화면에서 하려면 **Settings → Rules → Rulesets → New ruleset → Import a ruleset**에서 JSON 파일을 올려도 같은 룰셋이 만들어집니다.

성공 기준:

- dry-run은 `== security`, `== labels`, `== environment`, `== ruleset`, `== merge` 다섯 구간과 `$ gh api ...` 호출 목록을 출력하고 "dry-run이 끝났습니다."로 끝납니다.
- `--apply`는 각 단계를 `-> 완료`로 마치고 "모든 단계를 적용했습니다."를 출력합니다.
- **Settings → Rules → Rulesets**에 `main-protection`이 Active로 보이고, **Settings → Advanced Security**에서 Dependabot 알림·보안 업데이트, secret scanning, push protection이 켜져 있습니다.
- `gh label list`에 `dependencies`, `copilot-demo`가 있고 **Settings → Environments**에 `azure-demo`가 있습니다.

### 3. 위험한 PR 만들기 (약 2분)

Codespaces의 기본 토큰으로는 워크플로 파일을 push할 수 없을 수 있으니 이 단계는 로컬 터미널에서 하는 편이 안전합니다. main 브랜치에서 작업 트리를 깨끗하게 둔 채 실행하세요.

```bash
git switch main && git pull --ff-only
demos/02-github-repo/risky-pr/make-risky-pr.sh             # dry-run: 할 일만 출력
demos/02-github-repo/risky-pr/make-risky-pr.sh --apply     # 브랜치 push와 PR 열기
```

`--apply`는 `demo/risky-change` 브랜치를 만들어 push하고 `[DEMO – DO NOT MERGE]` 제목의 PR을 엽니다. 기본 브랜치에는 push하지 않으며, 작업 트리가 깨끗하지 않거나 HEAD가 origin의 기본 브랜치보다 앞서 있으면 아무것도 바꾸지 않고 멈춥니다. 워크플로 파일을 push할 권한이 없으면 `--no-workflow`로 `triage.yml`을 뺄 수 있습니다.

| 샘플(`risky-pr/` 아래) | PR 브랜치에 복사되는 위치 | 일부러 넣은 문제 | 기대하는 탐지 |
|---|---|---|---|
| `app/extras/debug_files.py.sample` | `app/extras/debug_files.py` | 요청 값으로 파일 경로 조합(경로 조작), 요청 값을 셸 명령에 삽입(명령어 삽입), Flask 디버그 모드 | CodeQL(Python): `py/path-injection`, `py/command-line-injection`, `py/flask-debug` |
| `app/extras/requirements.txt.sample` | `app/extras/requirements.txt` | 알려진 취약점이 있는 `flask==2.2.4` | Dependency review: GHSA-m2qf-hxjv-5gpq(CVE-2023-30861, high) |
| `.github/workflows/triage.yml.sample` | `.github/workflows/triage.yml` | 이슈 제목을 `run:`에 그대로 삽입(expression injection) | CodeQL(Actions): `actions/code-injection/critical` |

샘플에 `.sample` 확장자를 붙인 이유는 main에서 CodeQL, 의존성 그래프, 린터가 이 파일들을 보지 않게 하려는 것입니다. 그래서 main에는 취약한 코드가 없고, 스크립트가 PR 브랜치에서만 `.sample`을 뗀 이름으로 복사합니다. 모두 새 파일이라 기존 코드는 건드리지 않습니다.

PR 화면(스크립트 마지막 줄의 URL)에서 차례로 봅니다.

1. 아래쪽 체크 목록에서 `CI`의 `Unit tests`, `Container build and smoke test`, `IaC validation`을 봅니다.
2. `Analyze (python)`, `Analyze (actions)`가 끝나면 **Files changed**에 코드 스캐닝 알림이 주석으로 달립니다.
3. `Dependency review` 체크의 요약에서 `flask 2.2.4`의 high 취약점을 봅니다.
4. Copilot code review가 코멘트를 달았는지 봅니다.
5. merge 상자에서 막힌 이유를 읽습니다.

**secret scanning과 push protection은 말로 설명합니다.** 비밀처럼 보이는 문자열을 저장소에 두는 것 자체가 위험하므로, 이 저장소에는 토큰 모양의 문자열을 두지 않고 시연에서도 만들지 않습니다. 설명할 내용은 이렇습니다. push protection은 지원하는 비밀이 든 push를 저장소에 닿기 전에 막고, 어떤 비밀이 어디에 있는지 알려 줍니다. 개발자는 비밀을 지우고 다시 push하면 됩니다. CLI push뿐 아니라 웹 UI 커밋, 파일 업로드, REST API 요청에도 적용됩니다. 쓰기 권한이 있으면 사유를 남기고 우회할 수 있으며, 우회는 알림으로 기록됩니다. 직접 확인하려면 [공식 문서의 안내](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)를 따르세요.

성공 기준:

- 필수 체크 3개가 초록색입니다. 추가한 파일을 앱이 import하지 않기 때문입니다.
- CodeQL이 위 표의 알림을 보고합니다. 알림 목록은 CodeQL 쿼리 버전에 따라 달라질 수 있는 "기대 결과"이며, 작성 시점에 CodeQL 번들 2.27.4로 로컬에서 네 가지(`py/path-injection`, `py/command-line-injection`, `py/flask-debug`, `actions/code-injection/critical`)를 확인했습니다.
- `Dependency review`가 실패하고 `flask 2.2.4`와 GHSA-m2qf-hxjv-5gpq를 보여 줍니다. `dependency-review.yml`이 `fail-on-severity: high`를 쓰기 때문입니다. 필수 체크는 아니어서 이 체크만으로 merge가 막히지는 않습니다.
- Copilot의 리뷰 코멘트가 달립니다. 자동으로 달리지 않으면 PR 오른쪽 **Reviewers**에서 Copilot을 요청하세요.
- merge 상자에 코드 스캐닝 조건과 코드 오너 승인이 충족되지 않았다고 표시되어 merge할 수 없습니다. 관리자에게는 우회 옵션이 보일 수 있지만 쓰지 않습니다.
- `Workflow and script lint` job이 `triage.yml`의 신뢰할 수 없는 입력 사용을 지적해 실패할 수 있습니다. 필수 체크가 아니라서 merge 조건에는 영향이 없습니다.

### 4. Dependabot 확인 (약 1분)

1. `.github/dependabot.yml`을 엽니다. GitHub Actions, pip(`/app`, `/slides`), Docker(`/app`), devcontainers 5개 항목을 매주 월요일 09:00(Asia/Seoul)에 점검합니다. minor와 patch 업데이트는 생태계별로 한 PR에 묶이고 major는 따로 열립니다. `cooldown`은 새 릴리스가 나온 지 3일이 지난 뒤에 제안하게 하며, 보안 업데이트에는 적용되지 않습니다. PR에는 `dependencies` 라벨과 `chore(...)` 접두사가 붙습니다. 옵션은 [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)에 있습니다.
2. **Security**(또는 **Security and quality**) 탭의 **Dependabot**에서 알림을 봅니다. 알림은 기본 브랜치의 매니페스트를 기준으로 생기므로, 3단계 PR의 `flask==2.2.4`는 merge 전이라 여기에 나타나지 않고 PR의 Dependency review에서만 보입니다.
3. **Insights → Dependency graph → Dependabot** 탭에서 매니페스트 옆의 **Recent update jobs**로 업데이트 작업 기록을 보고, **Check for updates**로 바로 다시 점검할 수 있습니다.
4. 터미널에서는 `gh pr list --label dependencies`로 Dependabot PR을 모아 봅니다.

성공 기준: Dependabot 탭에 설정한 생태계의 업데이트 작업이 보입니다. 오래된 의존성이 있으면 `dependencies` 라벨과 `chore(...)` 접두사가 붙은 PR이 열립니다. 모두 최신이면 PR이 없는 것이 정상이니, 시연 전에 열린 Dependabot PR이 있는지 확인해 두세요.

## 말하기 포인트

- **설정도 코드입니다.** 룰셋, CODEOWNERS, Dependabot, dev container, 적용 스크립트가 모두 저장소 파일입니다. PR로 리뷰하고, 다른 저장소에 그대로 가져가고, 몇 번이든 같은 결과로 다시 적용할 수 있습니다.
- **main에는 PR로만 들어갑니다.** 삭제와 force push는 막히고, 승인·필수 체크·코드 스캐닝을 통과해야 merge됩니다.
- **관리자 우회는 타협입니다.** 1인 저장소에서는 자기 PR을 승인할 수 없어서 `pull_request` 모드 우회를 열어 뒀습니다. 팀 저장소라면 이 항목을 비우고 `require_last_push_approval`도 켜는 쪽이 안전합니다.
- **보안은 PR 안에서 앞당겨 확인합니다.** CodeQL은 코드와 워크플로를, Dependency review는 새 의존성을, push protection은 비밀을 merge 전에 잡습니다. 문제가 배포까지 가기 전에 만나는 셈입니다.
- **Copilot은 리뷰를 돕고 승인은 사람이 합니다.** Copilot code review는 첫 리뷰어 역할이며 필수 승인 수에 들어가지 않습니다. 코드 오너와 사람이 최종 판단합니다.
- **온보딩은 클릭 몇 번입니다.** Codespaces가 도구를 갖춰 주고, 비밀번호는 저장소 어디에도 없습니다.

## 정리(Cleanup)

```bash
git switch main
gh pr close demo/risky-change --delete-branch   # PR을 닫고 원격·로컬 브랜치 삭제
git fetch --prune origin                        # 사라진 원격 브랜치 기록 정리
```

- 이 PR은 merge하지 않고 닫습니다. `make-risky-pr.sh --branch`로 다른 이름을 썼다면 그 이름으로 바꿔 실행하세요.
- Codespace는 github.com/codespaces에서 지우거나 `gh codespace delete`로 지웁니다.
- 룰셋을 되돌리려면 **Settings → Rules → Rulesets**에서 `main-protection`을 Disabled로 바꾸거나 삭제합니다. `apply-repo-settings.sh --apply`를 다시 실행하면 같은 이름의 룰셋이 JSON 내용(`active`)으로 돌아갑니다.
- 머지 옵션(squash만 허용)은 **Settings → General**의 Pull Requests 항목에서 되돌립니다.
- 두 스크립트는 여러 번 실행해도 안전합니다. 라벨, 환경, 보안 설정은 남겨 둬도 괜찮습니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| 룰셋 가져오기나 `--apply`의 ruleset 단계가 실패함 | 플랜이나 조직 정책이 `code_scanning` 또는 `copilot_code_review` 규칙을 받아들이지 않을 수 있습니다. `scripts/apply-repo-settings.sh --apply --only ruleset --core-rules-only`로 두 규칙을 뺀 룰셋을 만들고, 두 기능은 **Settings → Rules**에서 직접 추가하세요. 화면에서 가져온다면 JSON에서 두 규칙 블록을 지운 뒤 올립니다. |
| 필수 체크를 목록에서 고를 수 없거나 PR에서 "Waiting for status to be reported"로 멈춤 | 체크 이름은 그 워크플로가 한 번 실행된 뒤에야 선택 목록에 나타납니다. **Actions → CI → Run workflow**로 main에서 한 번 실행하세요. job 표시 이름이 JSON과 한 글자라도 다르거나, 워크플로에 `paths` 필터가 있거나, 재사용 워크플로로 이름이 바뀌면 체크가 보고되지 않습니다. 다른 앱이 보내는 체크라면 JSON에서 해당 `integration_id`를 지웁니다. |
| 혼자 쓰는 저장소에서 merge할 수 없음 | PR 작성자는 자기 PR을 승인할 수 없고 코드 오너 리뷰도 필요합니다. 관리자 우회(bypass)로 merge하거나 쓰기 권한이 있는 다른 계정으로 승인하세요. 3단계의 위험한 PR에는 쓰지 마세요. |
| 코드 오너 리뷰를 요청받는 사람이 엉뚱함 | 포크나 템플릿으로 만든 저장소에 `@junwoojeong100`이 그대로 남아 있습니다. `.github/CODEOWNERS`를 자신의 계정이나 팀으로 바꾸세요. 코드 오너는 저장소에 쓰기 권한이 있어야 합니다. |
| `apply-repo-settings.sh --apply`가 403이나 404를 돌려줌 | 관리자 권한이 없거나 Codespace의 기본 토큰을 쓰고 있습니다. `unset GITHUB_TOKEN` 뒤 `gh auth login`으로 로그인하거나 로컬 터미널에서 실행하세요. 일부 호출만 실패하면 스크립트가 끝에서 실패한 개수를 알려 주며, 멱등이라 다시 실행해도 됩니다. |
| `make-risky-pr.sh`의 push가 거부됨(오류에 `workflow`가 나옴) | 브랜치에 새 워크플로 파일이 있어서 토큰에 `workflow` 권한이 필요합니다. `gh auth refresh --scopes workflow`를 실행하세요. Codespaces의 기본 토큰으로는 막힐 수 있으니 로컬 터미널에서 실행하는 것이 안전합니다. 권한을 줄 수 없으면 스크립트가 출력한 명령으로 되돌린 뒤 `--no-workflow`로 다시 실행합니다. 이 경우 Actions 워크플로 알림 시연은 빠집니다. |
| `make-risky-pr.sh --apply`가 경고를 출력하고 멈춤 | 작업 트리가 깨끗하지 않거나, HEAD가 origin의 기본 브랜치보다 앞서 있거나, 같은 이름의 브랜치나 대상 파일이 이미 있거나, `gh` 로그인이 안 된 경우입니다. 이때는 아무것도 바꾸지 않으니 메시지대로 정리하고 다시 실행하세요. origin 브랜치 기록이 남아 있다는 경고는 `git fetch --prune origin`으로 지웁니다. 브랜치를 만든 뒤에 멈추면 되돌리는 명령이 출력됩니다. |
| CodeQL 알림이 없거나 규칙 ID가 다름 | `Analyze (python)`, `Analyze (actions)`가 아직 끝나지 않았거나, CodeQL 쿼리 버전에 따라 탐지 결과가 달라졌을 수 있습니다. 발표 전에 한 번 돌려 결과를 확인하세요. |
| Copilot 리뷰가 달리지 않음 | PR을 연 사람의 Copilot 라이선스와 정책을 확인하세요. 룰셋의 자동 리뷰는 초안 PR에는 요청되지 않으므로 Ready for review로 바꾸거나 **Reviewers**에서 Copilot을 직접 요청합니다. 지적할 내용이 없으면 코멘트 없이 끝나기도 합니다. |
| Dependabot이 `/slides` 항목에서 오류를 보고함 | `slides/requirements.txt`가 없는 경우입니다. 파일을 추가하거나 `.github/dependabot.yml`에서 해당 항목을 지웁니다. |
| 8080 포트가 열리지 않음 | 앱이 실행 중인지 확인하고 PORTS 탭에서 8080을 직접 추가하세요. 앱이 `503`을 돌려주면 `DEMO_PASSWORD`가 설정되지 않은 것입니다. |
| 스크립트가 `jq`를 찾지 못함 | `apply-repo-settings.sh`는 dry-run에서도 `jq`를 씁니다. Codespace에는 들어 있고, 로컬에서는 패키지 관리자로 설치하세요. |

## 다른 데모와 함께 쓰면

이 데모는 다른 데모 없이도 끝까지 진행됩니다. 함께 쓰면 이야기가 이어집니다.

- **[Demo 1 (GitHub Copilot)](../01-github-copilot/README.md)**: cloud agent가 만든 PR도 같은 룰셋을 통과해야 합니다. 에이전트에게 작업을 시킨 사람은 그 PR을 승인할 수 없으므로 관리자 우회나 다른 계정의 승인이 필요합니다. `copilot-demo` 라벨은 이 데모의 `apply-repo-settings.sh`가 미리 만들어 줍니다.
- **[Demo 3 (GitHub Actions)](../03-github-actions/README.md)**: 필수 체크 이름은 `ci.yml`의 job 이름과 같습니다. 병렬 CI가 곧 merge 조건입니다. `azure-demo` 환경은 이 데모의 스크립트가 만들고, `--reviewer`로 승인자를 지정하면 배포 승인 게이트를 바로 보여 줄 수 있습니다.
- **[Demo 4 (Microsoft Foundry)](../04-microsoft-foundry/README.md)**: Codespace에서도 `az login`(브라우저 로그인이 어렵다면 `--use-device-code`)을 마친 뒤 같은 방식으로 앱을 실행해 볼 수 있습니다.
- **[Demo 5 (Azure Container Apps)](../05-azure-container-apps/README.md), [Demo 6 (AKS)](../06-aks/README.md)**: Codespace의 `az`, `docker`, `kubectl`로 배포 스크립트를 그대로 실행할 수 있습니다. kubelogin이 필요하면 `sudo az aks install-cli`를 실행하세요. Dependabot은 Dockerfile의 베이스 이미지 업데이트도 PR로 올려 줍니다.

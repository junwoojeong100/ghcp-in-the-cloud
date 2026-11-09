# Demo 1 — GitHub Copilot: 이슈에서 PR까지, AI 팀원과 협업

이슈 하나를 AI 팀원(Copilot cloud agent)에게 맡기고, 결과를 PR로 받아 CI, Copilot code review, 사람 리뷰로 검증한 뒤 merge합니다. 이 저장소에는 팀의 Copilot 설정(지침, 프롬프트, 에이전트, MCP)이 코드로 들어 있어서, 에이전트 작업과 코드 리뷰에 같은 규칙이 적용됩니다.

> GitHub 문서는 이 에이전트를 Copilot cloud agent(구 coding agent)라고 부릅니다. 이 문서도 cloud agent라고 씁니다. 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | 이슈 → 에이전트 PR → CI → Copilot code review → 사람 리뷰와 merge를 한 번에 보여 주고, 저장소의 Copilot 설정이 결과의 품질을 어떻게 바꾸는지 설명합니다. |
| 시간 | 약 7분. 에이전트 작업에 몇 분이 걸리므로 시연 10~15분 전에 이슈 하나를 미리 할당해 두세요. |
| 난이도 | 보통 |
| 독립 실행 | 예. GitHub 저장소와 Copilot 라이선스(cloud agent 사용 가능)만 있으면 됩니다. Azure 구독은 필요 없습니다. 선택 단계인 5단계의 Azure MCP 질의만 `az login`이 필요합니다. |

```text
이슈 → Copilot 할당 → 에이전트 세션 → 초안(draft) PR → CI → Copilot code review → 사람 리뷰 → merge
```

## 왜 이 서비스인가 (이점)

- **생산성**: 이슈를 잘 쓰기만 하면 에이전트가 브랜치를 만들고 코드와 테스트를 작성해 PR로 올립니다. 사람은 구현 대신 리뷰와 판단에 시간을 씁니다.
- **팀 표준의 코드화**: 저장소 공통 지침(`.github/copilot-instructions.md`), 경로별 지침(`.github/instructions/`), 프롬프트 파일(`.github/prompts/`), 전용 에이전트(`.github/agents/`)가 코드와 함께 버전 관리되고 PR로 리뷰됩니다. 사람이 따르는 코딩 규칙을 에이전트도 그대로 따릅니다.
- **안전한 자동화**: 에이전트는 자기 전용 `copilot/` 브랜치에만 쓸 수 있고, PR을 Ready for review로 바꾸거나 승인·merge할 수 없습니다. 워크플로도 사람이 승인해야 돌아가며, 브랜치 보호와 필수 체크는 그대로 적용됩니다. 여기에 Copilot code review와 사람 리뷰가 겹칩니다.
- **클라우드 연결**: Azure MCP server로 Azure 리소스를 대화로 조회하고(기본은 읽기 전용), Copilot CLI로 터미널에서도 같은 작업을 이어 갑니다.

## 사전 준비

1. **cloud agent 사용 설정**: Copilot 유료 플랜과 저장소 쓰기 권한이 필요합니다. 조직 저장소라면 조직 정책에서 cloud agent("Copilot in the cloud")가 켜져 있고 이 저장소가 허용돼 있어야 합니다. 개인 저장소는 계정의 Copilot 설정에서 켭니다.
2. **GitHub CLI(`gh`)**: `scripts/create-demo-issues.sh`가 사용합니다. `gh auth login`을 마쳐 두세요. `--assign-copilot` 옵션은 `gh` 2.76 이상이 필요하고 GitHub Enterprise Server에서는 쓸 수 없습니다.
3. **설정 파일은 기본 브랜치에**: `.github/` 아래의 지침, 에이전트, 워크플로 파일이 기본 브랜치에 merge돼 있어야 cloud agent가 읽습니다. 특히 `.github/workflows/copilot-setup-steps.yml`(job 이름 `copilot-setup-steps`)은 기본 브랜치에 있어야 적용됩니다. 이 워크플로는 에이전트 세션이 GitHub Actions 위에서 돌 때 Python과 의존성 같은 개발 환경을 미리 준비하며, 이슈를 Copilot에게 할당해 시작한 세션도 여기에 해당할 수 있습니다. 단계가 실패해도 에이전트는 계속 진행하므로 세션 로그에서 이 단계를 확인하세요.
4. **룰셋을 켠 저장소라면 승인 규칙을 알아 두세요**: Demo 2의 `main-protection` 룰셋은 승인 1건, 코드 오너 리뷰, 필수 체크를 요구합니다. 에이전트에게 작업을 시킨 사람은 그 PR을 승인할 수 없습니다. 발표자 한 명뿐인 저장소에서는 승인 조건을 채울 수 없으므로, 관리자 우회(bypass)로 merge하거나(이 룰셋은 관리자의 PR 우회를 허용합니다) 쓰기 권한과 코드 오너 자격이 있는 다른 계정으로 승인하세요. 룰셋을 적용하지 않은 저장소에는 이 제약이 없습니다.
5. **`copilot-demo` 레이블**: `scripts/create-demo-issues.sh --apply`가 없으면 만듭니다. 이슈 폼(`Copilot demo task`)도 이 레이블을 붙이지만, 저장소에 레이블이 아직 없으면 붙지 않으므로 스크립트를 한 번 실행하거나 레이블을 먼저 만들어 두세요.
6. **VS Code와 CLI (선택, 5단계)**: GitHub Copilot Chat이 설치된 VS Code에서 저장소를 열면 `.vscode/extensions.json`이 추천 확장을 알려 줍니다. `.vscode/mcp.json`은 VS Code용이며 cloud agent는 읽지 않습니다. cloud agent의 MCP 서버는 저장소 설정의 Copilot 항목에서 따로 등록합니다. Azure MCP server(`azure`)는 Node.js(`npx`)와 `az login`이 필요하고 `--read-only`로 시작하므로 시연 중에 리소스를 바꾸지 않습니다. 버전을 고정하려면 `@azure/mcp@latest`의 `latest`를 특정 버전으로 바꾸세요. Copilot CLI(`copilot`)는 `npm install -g @github/copilot`으로 설치합니다.

### 시작 이슈 3개

`demos/01-github-copilot/issues/`의 이슈 본문은 배경, 요구사항, 수용 기준, 제약 사항, 테스트 방법, 범위 밖을 갖춰서 cloud agent가 성공하기 쉽게 썼고, 서로 독립적입니다. 앱에 아직 없는 기능이라 실행하면 실제 코드 변경이 생깁니다.

| 번호 | 제목 | 바뀌는 곳 | 시연 포인트 |
|---|---|---|---|
| 01 | `POST /api/chat`에 클라이언트별 요청 제한(rate limit) 추가 | `app/server.py`, `app/tests/`, `README.md` | HTTP 429와 `Retry-After`, 보안 관점의 리뷰 논의 |
| 02 | Prometheus 형식의 `GET /metrics` 엔드포인트 추가 | `app/server.py`, `app/tests/`, `README.md` | 새 의존성 없이 구현, 기존 Basic 인증 적용 |
| 03 | 화면에 최근 질문·답변 10개와 지우기 버튼 추가 | `app/index.html`, `app/tests/` | 화면에서 결과가 바로 보임, `innerHTML` 금지 규칙 |

라이브로 시작하는 이슈는 결과가 화면에 보이는 03을, 리뷰 시연에는 논의할 거리가 많은 01을 권합니다. 01과 02는 같은 파일을 고치므로 동시에 열어 두면 PR끼리 충돌할 수 있습니다. 충돌이 나면 PR에서 `@copilot`에게 해결을 요청하세요. 실행할 때마다 결과가 다르니 특정 코드나 지적이 나온다고 약속하지 마세요.

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 아래 클릭 경로는 작성 시점 기준입니다. 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요.

### 1. 저장소의 Copilot 설정 둘러보기 (약 1분)

GitHub 저장소 화면이나 VS Code 탐색기에서 아래 파일을 차례로 엽니다.

| 경로 | 보여 줄 것 |
|---|---|
| `.github/copilot-instructions.md` | 모든 Copilot 요청에 자동으로 붙는 저장소 공통 규칙: 명령어, `/healthz`만 인증 없음, 비밀 금지 |
| `.github/instructions/*.instructions.md` | 경로별 규칙. `applyTo` 글롭으로 Python, Bicep, Kubernetes, Actions 워크플로, 한국어 문서에 서로 다른 규칙이 적용됨 |
| `.github/prompts/*.prompt.md` | 슬래시 프롬프트: `/add-endpoint`, `/write-tests`, `/review-security`, `/explain-infra`, `/demo-script` |
| `.github/agents/*.agent.md` | 전용 에이전트: `azure-iac-reviewer`(읽기 전용 리뷰어), `demo-writer`, `foundry-integrator` |
| `.vscode/mcp.json` | MCP 서버 3개: Azure, GitHub(읽기 전용 주소), Microsoft Learn |
| `.github/ISSUE_TEMPLATE/copilot-demo.yml` | 에이전트가 성공하기 쉬운 이슈 폼: 배경, 요구사항, 수용 기준, 제약 사항, 테스트 방법, 범위 밖 |

성공 기준: `copilot-instructions.md`의 규칙 목록과 `instructions/` 파일의 `applyTo` 줄이 화면에 보이고, "이 규칙은 저장소에 있고 PR로 바뀐다"는 설명이 청중에게 전달됩니다.

### 2. 이슈를 만들고 Copilot에게 할당 (약 1.5분)

**방법 A. 스크립트 (권장)**

```bash
scripts/create-demo-issues.sh                                    # 미리보기: 실행할 gh 명령만 출력
scripts/create-demo-issues.sh --apply --assign-copilot --only 3  # 3번 이슈를 만들고 Copilot에게 할당
```

첫 줄은 아무것도 만들지 않고 실행할 `gh issue create` 명령만 보여 줍니다. 전체 이슈를 만들려면 `--only`를 빼세요. 같은 제목의 열린 이슈가 있으면 건너뛰므로 다시 실행해도 안전합니다. `--assign-copilot`을 쓸 수 없는 환경이면 이슈만 만들고 수동 할당 방법을 안내합니다.

**방법 B. 이슈 폼**

1. **Issues → New issue**에서 `Copilot demo task`를 고르고 각 칸(배경, 요구사항, 수용 기준, 제약 사항, 테스트 방법, 범위 밖)을 채웁니다. `demos/01-github-copilot/issues/`의 해당 섹션을 붙여 넣으면 빠릅니다.
2. 이슈를 만든 뒤 오른쪽 **Assignees**에서 **Copilot**을 고르고, 대화상자에서 대상 저장소와 기준(base) 브랜치를 확인한 다음 할당합니다.

성공 기준: 이슈에 `copilot-demo` 레이블과 Copilot 담당자가 붙고, 잠시 뒤 눈(👀) 반응이 달립니다. 이어서 타임라인에 Copilot의 작업 시작 표시와 초안 PR 링크가 나타납니다.

### 3. 에이전트 세션, PR, CI 확인 (약 2분)

1. 이슈나 PR 타임라인의 **View session**으로 에이전트 로그를 엽니다. 코드를 읽고, 구현하고, 테스트를 실행하는 과정이 보입니다.
2. 미리 만들어 둔 PR로 이동해 설명, **Files changed**의 구현·테스트·문서 변경, 커밋을 봅니다. 커밋 작성자는 Copilot이고, 이슈를 할당한 사람이 공동 작성자로 표시됩니다.
3. 체크가 대기 중이면 PR 화면의 **Approve and run workflows**를 눌러 `CI`를 시작합니다. `CI`의 job(`Unit tests`, `Container build and smoke test`, `IaC validation`, `Workflow and script lint`)이 병렬로 도는 것을 봅니다.
4. 실패한 체크가 있으면 PR 댓글로 에이전트에게 고치게 합니다. 예: `@copilot Unit tests가 실패했습니다. 원인을 찾아 고쳐 주세요.` 에이전트가 눈(👀) 반응을 달고 같은 브랜치에 커밋을 추가합니다.

성공 기준: PR이 이슈와 연결된 초안(draft) 상태이고, Files changed에 구현·테스트·문서가 함께 있으며, `CI`의 job이 모두 초록색입니다.

### 4. Copilot code review와 사람 리뷰, merge (약 2분)

1. 초안 PR을 **Ready for review**로 바꿉니다. 에이전트는 이 단계를 할 수 없습니다.
2. PR 오른쪽 **Reviewers**에서 **Copilot**을 요청합니다. 터미널에서는 `gh pr edit <PR번호> --add-reviewer "@copilot"`을 씁니다. 잠시 뒤 Copilot의 리뷰가 등록됩니다.
3. 코멘트를 사람이 판단합니다. 타당하면 제안을 반영하거나 `@copilot`에게 수정을 요청하고, 아니면 **Resolve**로 닫습니다. Copilot의 리뷰는 승인(Approve)이 아닌 코멘트라서 merge 조건을 대신하지 않습니다.
4. 사람이 diff를 읽고 승인한 뒤 merge합니다. 룰셋이 켜져 있으면 필수 체크 통과와 코드 오너 승인이 필요합니다(사전 준비 4번 참고).

성공 기준: PR에 Copilot의 리뷰가 등록되고(코멘트 수는 달라질 수 있음), 사람이 코멘트를 처리한 뒤 필수 체크가 통과한 상태로 merge됩니다. 연결된 이슈가 자동으로 닫힙니다.

### 5. (선택) VS Code agent mode, 프롬프트 파일, Azure MCP, Copilot CLI (약 2분)

1. VS Code에서 저장소를 열고 Copilot Chat을 **Agent** 모드로 둡니다.
2. **프롬프트 파일**: 입력창에 `/add-endpoint GET /api/version`처럼 라우트와 동작을 함께 적어 실행합니다. 코드, 테스트, 문서가 함께 바뀌면 터미널에서 `python -m unittest discover -s app/tests -v`로 확인합니다.
3. **전용 에이전트**: 채팅의 에이전트 선택에서 `azure-iac-reviewer`를 고르고 `infra/aca/main.bicep`을 검토해 달라고 요청합니다. 이 에이전트는 읽기·검색 도구만 있어서 파일을 수정하지 않고 의견만 냅니다.
4. **Azure MCP**: `az login`을 마친 뒤 명령 팔레트의 **MCP: List Servers**에서 `azure` 서버를 시작하고 "내 구독의 리소스 그룹을 나열해 줘"처럼 묻습니다. 읽기 전용이라 리소스를 바꾸지 않습니다. Demo 4~6에서 배포한 리소스가 있다면 그 리소스를 조회하는 편이 더 자연스럽습니다.
5. **Copilot CLI**: `copilot -p '이 저장소의 엔드포인트와 인증 방식을 표로 요약해 줘' -s` 한 줄을 실행합니다. 같은 `.github/copilot-instructions.md`를 읽습니다. 대화형 세션에서 `/delegate <작업>`을 입력하면 작업을 GitHub로 보내 PR을 만듭니다. 이슈 없이 바로 맡기려면 `gh agent-task create "<작업 설명>" --follow`(프리뷰 명령)도 있습니다.

성공 기준: `/add-endpoint`가 코드, 테스트, 문서를 함께 바꾸고 테스트가 통과하며, `azure-iac-reviewer`는 파일을 고치지 않고 의견만 내고, Azure MCP가 읽기 전용으로 목록을 돌려줍니다.

## 말하기 포인트

- **이슈의 품질이 곧 결과의 품질입니다.** 배경, 수용 기준, 제약, 테스트 방법이 있는 이슈는 에이전트가 스스로 검증하며 작업할 수 있습니다. 이슈 폼이 이 틀을 강제합니다. 에이전트는 할당 시점의 제목, 본문, 기존 댓글만 읽으므로 이후 지시는 PR에서 `@copilot`으로 합니다.
- **통제권은 사람에게 있습니다.** 에이전트는 `copilot/` 브랜치에만 쓰고, PR을 Ready로 바꾸거나 승인·merge할 수 없습니다. 워크플로 실행도 사람이 승인합니다.
- **추적할 수 있습니다.** 커밋은 서명되어 Verified로 보이고, Copilot이 작성하며 지시한 사람이 공동 작성자로 남고, 커밋 메시지에 세션 로그 링크가 있습니다.
- **팀 표준이 코드입니다.** 지침 파일은 cloud agent, VS Code, Copilot CLI, Copilot code review가 읽고, 전용 에이전트는 VS Code, cloud agent, Copilot CLI에서 고를 수 있습니다. 규칙을 바꾸려면 PR을 올려 리뷰받으면 됩니다.
- **리뷰는 두 겹입니다.** Copilot code review가 먼저 훑고 사람이 최종 판단합니다. Copilot의 리뷰는 승인으로 치지 않습니다.
- **비밀을 넣지 않습니다.** 지침, MCP 설정, 에이전트 환경 어디에도 키를 넣지 않고 Azure는 키 없는 인증(Entra ID)을 씁니다. 에이전트의 인터넷 접근은 기본적으로 제한됩니다. 이슈나 댓글에 HTML 주석으로 숨긴 지시는 에이전트에게 전달되지 않습니다.

## 정리(Cleanup)

```bash
gh issue list --label copilot-demo --state open                   # 남은 데모 이슈 확인
gh issue close <이슈번호> --reason "not planned"                   # 필요 없는 이슈 닫기
gh pr list --state open --json number,title,headRefName \
  --jq '.[] | select(.headRefName | startswith("copilot/"))'       # 에이전트 PR 확인
gh pr close <PR번호> --delete-branch                               # merge하지 않을 PR을 닫고 브랜치 삭제
gh label delete copilot-demo --yes                                 # (선택) 레이블 삭제
```

- merge한 PR의 브랜치는 PR 화면의 **Delete branch**로 지웁니다.
- merge한 변경을 되돌리려면 병합된 PR에서 **Revert**로 되돌리는 PR을 만듭니다. 이미 구현된 이슈를 다시 만들지 않도록 주의하세요.
- 스크립트는 열린 이슈만 중복으로 보므로, 닫은 이슈는 같은 제목으로 다시 만들 수 있습니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| Assignees 목록에 Copilot이 없음 | Copilot 유료 플랜, 저장소 쓰기 권한, 조직 정책(cloud agent 허용)과 저장소 접근 범위를 확인하세요. `--assign-copilot`도 같은 조건이 필요합니다. |
| 할당했는데 아무 일도 없음 | 몇 분 기다리고 새로고침하세요. 이슈에 눈(👀) 반응이 없으면 Copilot 할당을 해제했다가 다시 할당합니다. 오래 멈춘 세션은 시간 제한으로 종료될 수 있으니 같은 방법으로 다시 시작합니다. |
| 체크가 "대기 중"에서 시작하지 않음 | 에이전트 PR의 워크플로는 기본적으로 사람이 **Approve and run workflows**를 눌러야 실행됩니다. 저장소 설정에서 자동 실행으로 바꿀 수 있지만, 시연에서는 사람 승인 단계를 보여 주는 편이 좋습니다. |
| PR에 방화벽 경고가 보이거나 `pip install`이 실패 | cloud agent는 인터넷 접근이 기본적으로 제한됩니다. 의존성은 `copilot-setup-steps.yml`에서 미리 설치하고, 꼭 필요한 호스트는 저장소 설정의 Copilot 항목(Internet access)에서 허용 목록에 추가하세요. 허용 목록 변경은 새 세션부터 적용됩니다. |
| 에이전트가 규칙을 어김 | 지침 파일이 기본 브랜치에 있는지, `applyTo` 글롭이 대상 경로와 맞는지 확인하세요. 이슈의 제약 사항에 파일 위치와 금지 사항을 더 구체적으로 적고, PR에서 `@copilot`에게 수정을 요청합니다. |
| 전용 에이전트가 선택 목록에 없음 | `.github/agents/*.agent.md`가 기본 브랜치에 있고 `description`이 있는지 확인하세요. |
| merge 버튼이 막혀 있음 | 룰셋이 승인과 코드 오너 리뷰를 요구하는데, 에이전트에게 작업을 시킨 사람은 그 PR을 승인할 수 없습니다. 관리자 우회(bypass)나 다른 계정의 승인을 쓰세요(사전 준비 4번). |
| 필수 체크가 끝까지 보고되지 않음 | 워크플로가 아직 승인되지 않았거나, job 표시 이름이 룰셋의 필수 체크 이름(`Unit tests`, `Container build and smoke test`, `IaC validation`)과 다릅니다. |
| Copilot 리뷰에 코멘트가 없음 | 지적할 내용이 없으면 코멘트 없이 끝날 수 있습니다. 룰셋의 자동 리뷰는 초안 PR에 요청되지 않으므로, 초안일 때는 수동으로 요청하거나 Ready for review로 바꾼 뒤 요청하세요. |
| 스크립트가 `gh`를 못 찾거나 인증 오류 | `gh auth login`을 하고 `gh auth status`로 확인하세요. 미리보기(기본 동작)는 쓰기 호출을 하지 않습니다. `--assign-copilot`이 실패하면 이슈만 만들고 `gh issue edit <번호> --add-assignee @copilot` 또는 Assignees 메뉴를 안내합니다. |

## 다른 데모와 함께 쓰면

이 데모는 다른 데모 없이도 끝까지 진행됩니다. 함께 쓰면 이야기가 이어집니다.

- **Demo 2 (GitHub Repo)**: `main-protection` 룰셋을 적용하면 에이전트 PR도 같은 필수 체크, 코드 오너 리뷰, 승인 규칙을 통과해야 합니다. 4단계의 "최종 판단은 사람이 한다"는 메시지가 더 분명해집니다.
- **Demo 3 (GitHub Actions)**: 3단계에서 도는 `CI`가 Demo 3의 병렬 job 그 자체입니다. 이어서 보여 주면 자연스럽습니다.
- **Demo 4~6 (Foundry, Container Apps, AKS)**: 5단계의 Azure MCP로 배포된 리소스를 조회할 수 있습니다. 이슈 01(요청 제한)을 merge했다면 `scripts/load-test.sh`의 기본 경로 `/api/chat`이 `429`를 돌려줄 수 있습니다. 이때는 배포 환경에 `RATE_LIMIT_PER_MINUTE=0`을 설정해 제한을 끄거나 `--path /healthz`로 부하를 거세요.

# 시연 가이드 — Cloud Copilot Demo

발표 슬라이드를 넘기며 데모를 시연하는 분을 위한 진행 가이드입니다. 단계별 명령과 화면은 [`demos/`](demos/)의 데모 문서에 있고, 이 문서는 어떤 순서와 시간으로 엮을지, 발표 전에 무엇을 준비할지에 집중합니다.

> 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다. UI 메뉴 이름은 변경될 수 있음을 염두에 두세요. 화면이 다르면 문서에 적힌 CLI 명령과 설정 이름을 기준으로 찾으세요. 시간은 문서의 단계별 목표값이므로 첫 리허설에서 직접 재어 보고 조정하세요.

## 코스 선택

| 코스 | 시간 | 구성 | 어울리는 자리 |
|---|---|---|---|
| Full | 약 42분 | Demo 1 → 2 → 3 → 4 → 5 → 6 | 전체 소개 세션, 워크숍 |
| Lite | 약 15분 | Demo 1 → 3 → 4 → 5 (단계를 줄여서) | 짧은 발표 슬롯 |
| 단일 | 6~8분 | 데모 하나 | 특정 서비스 중심의 밋업 |

슬라이드는 데모마다 가치, 시연 흐름, 핵심 코드 세 장으로 되어 있습니다. 요약 코스에서는 시연 흐름 슬라이드에서 `Lite`로 표시된 단계만 진행합니다. 슬라이드 번호와 시간표, 슬라이드별 진행 대본은 [`slides/demo-presentation-ko.md`](slides/demo-presentation-ko.md)에 있습니다.

데모 순서는 개발(Copilot) → 협업과 보안(Repo) → 자동화(Actions) → AI 모델(Foundry) → 실행 환경(Container Apps) → 확장과 운영(AKS)으로, 앱이 만들어져 운영되기까지의 흐름을 따릅니다. 어느 데모든 단독으로 시연할 수 있으니 청중에 맞게 골라 쓰세요. 필요한 계정과 구독은 [README의 독립 실행 매트릭스](README.md#독립-실행-매트릭스)에 있습니다.

## Full 코스 (약 42분)

| 누적 시간 | 데모 | 청중에게 남길 메시지 | 라이브로 보여 줄 것 |
|---|---|---|---|
| 0:00 (7분) | [1. GitHub Copilot](demos/01-github-copilot/README.md) | AI 팀원에게 이슈를 맡기고, 저장소 지침으로 품질을 통제하며, 승인은 사람이 합니다. | 이슈 → 에이전트가 만든 PR → CI → Copilot code review |
| 0:07 (6분) | [2. GitHub Repo](demos/02-github-repo/README.md) | main 보호와 보안 설정이 코드로 정의돼 있어 누구의 PR이든 같은 규칙을 통과합니다. | Rulesets와 CODEOWNERS, 위험한 PR이 CodeQL과 Dependency review에 걸리는 화면 |
| 0:13 (7분) | [3. GitHub Actions](demos/03-github-actions/README.md) | 검증은 병렬로, 배포는 저장된 비밀 없이 OIDC로 하고 환경 승인으로 통제합니다. | CI의 job들, 환경 승인 → OIDC 로그인 → 새 리비전 |
| 0:20 (7분) | [4. Microsoft Foundry](demos/04-microsoft-foundry/README.md) | 같은 코드가 API 키 없이 Entra ID로 Claude를 부르고, 모델과 effort는 설정으로 바꿉니다. | 로컬 호출, `/api/info`의 `auth`, `model`, `effort` |
| 0:27 (7분) | [5. Azure Container Apps](demos/05-azure-container-apps/README.md) | 클러스터 없이 서비스하고, 유휴 시 0으로 줄며, 리비전으로 카나리 배포를 합니다. | 스케일 투 제로, 0% → 10% → 100%, 롤백, 스케일 아웃 |
| 0:34 (8분) | [6. AKS](demos/06-aks/README.md) | 같은 이미지를 쿠버네티스에서 무중단으로 갱신하고, 자동 확장하고, 비밀 없이 Azure를 부릅니다. | HPA, 롤링 업데이트와 롤백, 워크로드 ID |

데모 사이에 이렇게 이어 가면 흐름이 자연스럽습니다.

- 1 → 2: "AI가 만든 PR도 사람의 PR과 같은 규칙을 통과해야 합니다. 그 규칙을 저장소가 어떻게 강제하는지 보겠습니다."
- 2 → 3: "규칙의 핵심은 자동 검증입니다. 검증과 배포를 Actions로, 비밀 없이 구성해 보겠습니다."
- 3 → 4: "배포하는 앱은 Claude를 호출합니다. 그 연결도 키 없이 하는 방법을 보겠습니다."
- 4 → 5: "이제 이 앱을 어디서 돌릴지 봅니다. 운영 부담이 가장 적은 Container Apps부터 보겠습니다."
- 5 → 6: "더 세밀한 제어가 필요하면 AKS입니다. 같은 이미지가 그대로 올라갑니다."

## Lite 코스 (약 15분)

각 데모에서 핵심 단계만 보여 줍니다. 단계 번호는 해당 데모 문서의 "시연 순서"를 따릅니다.

| 데모 | 보여 줄 단계 | 시간 |
|---|---|---|
| 1. GitHub Copilot | 1단계(설정 둘러보기) → 3단계(미리 만든 에이전트 PR과 CI) → 4단계 중 Copilot code review 코멘트 | 약 4분 |
| 3. GitHub Actions | 2단계(비밀 없는 OIDC 신뢰) → 3단계(승인 → 로그인 → 새 리비전, 미리 돌려 둔 실행 결과 함께) | 약 4분 |
| 4. Microsoft Foundry | 2단계(키 없이 로컬 호출) → 3단계(`/api/info`) | 약 3분 |
| 5. Azure Container Apps | 1단계(스케일 투 제로) → 3단계(카나리 0% → 10% → 100%) | 약 4분 |

Lite 코스는 Demo 2와 Demo 6을 건너뜁니다. 질문이 나오면 해당 데모 문서의 "말하기 포인트"로 답하세요.

## 발표 전 체크리스트

### 하루 전까지

- [ ] 계정과 권한: Azure 구독(Owner, 또는 Contributor와 User Access Administrator), GitHub 저장소 관리자 권한, Copilot 라이선스(cloud agent 사용 가능)를 확인합니다. Claude 배포에는 Enterprise 또는 MCA-E 구독이 필요합니다([Demo 4](demos/04-microsoft-foundry/README.md) 참고).
- [ ] 도구: bash 4 이상, Python 3.12, `az`, `gh`(`gh auth login`), `jq`, `kubectl`과 `kubelogin`(`az aks install-cli`), `docker`(선택)를 설치합니다.
- [ ] 연습용 저장소(포크)를 준비합니다. 룰셋과 보안 설정을 바꾸는 스크립트는 연습용 저장소에서 먼저 실행하세요.
- [ ] 한 번 끝까지 리허설합니다. 이 키트는 정적 검사와 로컬 실행으로 확인했고, 실제 Azure 배포는 아직 실행해 보지 않았습니다.

### 시연 30~60분 전 (한 셸에서 순서대로)

```bash
az login
export CLAUDE_ORGANIZATION_NAME="<조직 이름>"
scripts/deploy-foundry.sh              # Demo 4, 몇 분
scripts/deploy-aca.sh                  # Demo 5, 출력되는 URL과 비밀번호를 적어 둡니다
scripts/deploy-aks.sh                  # Demo 6, 5~10분. 출력되는 비밀번호를 적어 둡니다
scripts/setup-github-oidc.sh --apply   # Demo 3, 배포 대상이 먼저 있어야 합니다
```

위 순서에서 `deploy-aca.sh`와 `deploy-aks.sh`는 `mock` 백엔드로 배포됩니다. Demo 5와 6의 시연 목적(스케일, 카나리, 롤링 업데이트)에는 충분하고 모델 호출 비용이 없으며, 화면에도 `mock`이라고 표시됩니다. Demo 4는 별도 터미널에서 `source .azure/foundry.env`를 실행한 뒤 로컬 앱으로 시연합니다. 배포한 앱까지 Claude에 연결하려면 `deploy-aca.sh`나 `deploy-aks.sh`를 실행하기 전에 같은 셸에서 `source .azure/foundry.env`를 실행하세요. 그러면 스모크 테스트는 `--expect-backend foundry`로, 부하 테스트는 `--path /healthz`로 실행해야 합니다([Demo 5](demos/05-azure-container-apps/README.md) 참고). Foundry를 쓰지 않으면 `scripts/deploy-foundry.sh` 줄도 건너뛰세요.

데모별로 미리 해 둘 일입니다.

| 데모 | 미리 해 둘 일 |
|---|---|
| 1 | 시연 10~15분 전에 `scripts/create-demo-issues.sh --apply --assign-copilot`로 이슈 하나를 Copilot에게 할당합니다. 에이전트 작업에 몇 분이 걸립니다. |
| 2 | Codespace를 하나 만들어 두고, `scripts/apply-repo-settings.sh --apply`로 룰셋, 라벨, 환경을 적용합니다. main에서 `ci.yml`이 한 번 이상 실행됐는지 확인하고, 위험한 PR을 미리 열어 CodeQL 분석이 끝난 화면을 준비합니다. |
| 3 | 승인 단계를 보이려면 `scripts/apply-repo-settings.sh --apply --only environment --reviewer <본인 GitHub 사용자 이름>`으로 승인자를 지정합니다. 배포 워크플로를 한 번 돌려 둡니다. |
| 4 | `python -m pip install --requirement app/requirements.txt`를 실행하고, 로컬에서 호출이 되는지 한 번 확인합니다. 역할 전파에 몇 분 걸릴 수 있습니다. |
| 5 | 배포가 끝난 뒤에는 앱에 요청을 보내지 마세요. 브라우저 탭과 스모크 테스트도 요청이므로, 시연 직전까지 열지 않아야 스케일 투 제로를 보여 줄 수 있습니다. `APP_URL`과 `DEMO_PASSWORD`를 셸에 준비합니다. |
| 6 | v2 이미지를 미리 빌드해 두고, `kubectl get pods --namespace cloud-copilot-demo`로 파드 2개 이상이 `Running`인지 확인합니다. 터미널을 셋(명령, 감시, 포트 포워딩) 준비합니다. |

### 시연 직전 5분

- [ ] `slides/demo-presentation-ko.pptx`를 열어 두고 발표자 노트를 확인합니다. 시연 큐는 노트와 `slides/demo-presentation-ko.md`에 같은 내용이 있습니다.
- [ ] 터미널 글꼴을 키우고, 시연에 쓸 탭을 미리 열어 둡니다. 알림을 끕니다.
- [ ] `DEMO_PASSWORD`는 `export`만 하고 화면에 출력하지 않습니다. 비밀번호가 보이는 창은 공유하지 마세요.
- [ ] 브라우저에서 GitHub, Azure 포털에 로그인한 상태로 필요한 탭만 남깁니다.
- [ ] 네트워크가 끊길 때를 대비해 아래 대체 시연을 떠올려 둡니다.

## 시연 중 운영 팁

- **오래 걸리는 것은 미리 돌려 두세요.** 에이전트 작업, CodeQL 분석, 클러스터와 이미지 빌드는 결과 화면을 먼저 열어 두고 "이렇게 끝납니다"로 이어 가면 흐름이 끊기지 않습니다. 라이브로 시작한 작업은 완료를 기다리지 말고 설명을 이어 가다가 돌아오세요.
- **각 데모의 "성공 기준"을 소리 내어 확인하세요.** 청중이 무엇을 보고 있는지 분명해집니다.
- **mock 백엔드는 숨기지 마세요.** 화면의 백엔드 칩이 `mock`이면 "스케일과 배포를 보여 주려고 모델 호출은 흉내 냅니다"라고 말하고, 실제 Claude 호출은 Demo 4에서 보여 줍니다.
- **effort `max`는 응답이 느릴 수 있습니다.** 시간이 빠듯하면 `FOUNDRY_EFFORT`를 낮춰 실행하고(Demo 4의 4단계), 깊게 추론하는 만큼 느리다고 설명하세요.

## 문제가 생기면 (대체 시연)

| 상황 | 대응 |
|---|---|
| Copilot cloud agent가 아직 끝나지 않음 | 미리 만들어 둔 에이전트 PR 화면으로 넘어가 CI와 리뷰를 설명합니다. |
| Azure 배포가 실패하거나 너무 느림 | `LLM_BACKEND=mock DEMO_PASSWORD=<임시 값> python -m app.server`로 로컬 앱을 띄우고 `scripts/smoke-test.sh`를 보여 줍니다. 배포 스크립트는 `--help`와 Bicep 파일(`infra/`)로 설명합니다. |
| Foundry 호출이 실패함 | [Demo 4의 문제 해결](demos/04-microsoft-foundry/README.md#문제-해결) 표를 확인하세요. 시간이 없으면 `LLM_BACKEND=mock`으로 바꿔 진행하고 Foundry는 슬라이드로 설명합니다. |
| 네트워크가 불안정함 | 로컬 mock 앱, 기본이 dry-run인 스크립트(`scripts/apply-repo-settings.sh`, `scripts/setup-github-oidc.sh`)의 출력, 슬라이드로 진행합니다. |
| 카나리나 배포 상태가 꼬임 | `scripts/aca-canary.sh status`로 상태를 보고 `rollback`으로 되돌립니다. `scripts/deploy-aca.sh`를 다시 실행하면 트래픽 분할도 초기화됩니다. |

## 시연이 끝나면

```bash
scripts/cleanup.sh all                 # 확인 질문에 y. 질문 없이 진행하려면 --yes
```

- 이 키트가 만든 Azure 리소스(Container Apps, AKS, Foundry, GitHub Actions용 관리 ID, `azure-demo` 환경 변수)를 지웁니다. 일부만 지우려면 `aca`, `aks`, `foundry`, `oidc`를 지정하세요. AKS 노드는 계속 과금되므로 시연 직후에 지우는 것을 권합니다.
- Demo 2의 위험한 PR은 merge하지 말고 닫은 뒤 브랜치를 지웁니다(`demos/02-github-repo/risky-pr/pr-body.md`의 "정리" 참고).
- 연습용 저장소의 시연용 이슈와 Codespace도 정리하세요.

## 관련 문서

- [README](README.md): 프로젝트 소개, 빠른 시작, 엔드포인트와 환경 변수
- [`demos/`](demos/): 데모별 시연 문서(한눈에 보기, 사전 준비, 시연 순서, 말하기 포인트, 정리, 문제 해결)
- [`slides/`](slides/): 발표 슬라이드(PPTX), 발표자 노트, 슬라이드별 진행 대본(Markdown)

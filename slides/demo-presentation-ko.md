# GitHub Copilot in the Cloud — 발표 개요와 진행 대본

> 이 파일은 `slides/build_deck.py`가 `demo-presentation-ko.pptx`와 같은 데이터로 만든 자동 생성 파일입니다. 직접 고치지 말고 스크립트의 데이터를 수정한 뒤 `python slides/build_deck.py`를 실행하세요. 각 슬라이드의 발표자 노트(PowerPoint의 노트 창)에도 같은 대본이 들어 있습니다.

## 진행 시간

| 구간 | 슬라이드 | Full | Lite |
|---|---|---|---|
| 오프닝 | 1–5 | 약 4.5분 | 약 4.5분 |
| 데모 1 · GitHub Copilot | 6–9 | 7분 | 4분 |
| 데모 2 · GitHub Repo | 10–13 | 6분 | 건너뜀 |
| 데모 3 · GitHub Actions | 14–17 | 7분 | 4분 |
| 데모 4 · Microsoft Foundry | 18–21 | 7분 | 3분 |
| 데모 5 · Azure Container Apps | 22–25 | 7분 | 4분 |
| 데모 6 · AKS | 26–29 | 8분 | 건너뜀 |
| 마무리 | 30–34 | 약 5.5분 + Q&A | 약 5.5분 + Q&A |
| **데모 합계** |  | **약 42분** | **약 15분** |
| 발표 전체(참고) |  | 약 52분 + Q&A | 약 25분 + Q&A |

- 각 데모의 시간은 데모 README의 목표 시간입니다. 가치 슬라이드 설명(약 1분)은 그 안에 넣어 말하고, 핵심 코드 슬라이드는 시연 대기 시간에 겹쳐 설명합니다. 단계 시간의 합이 조금 길면 설명을 줄여 맞추세요.
- Lite 경로는 Copilot → Actions → Foundry → Container Apps 순서이고, 각 흐름 슬라이드의 `Lite` 표시 단계만 진행합니다. 15분 슬롯에 맞추려면 오프닝(3–5)과 정리(24–27) 슬라이드는 한두 문장으로 줄이거나 건너뜁니다.
- 부록 슬라이드(체크리스트·트러블슈팅·링크)는 발표 중에는 건너뛰고 Q&A에서 사용합니다.

## 슬라이드 목록

| # | 제목 | 종류 | 예상 시간 |
|---|---|---|---|
| 1 | GitHub Copilot in the Cloud | 표지 | 약 0.5분 |
| 2 | 오늘의 여정: 데모 6개, 두 가지 경로 | 개요 | 약 1분 |
| 3 | 전체 그림: 코드는 GitHub에서, 실행과 AI는 Azure에서 | 다이어그램 | 약 1.5분 |
| 4 | 독립 시연 구조: 어느 데모든 혼자서도 됩니다 | 표 | 약 0.5분 |
| 5 | 샘플 앱: 이미지 하나가 어디서나 동작합니다 | 다이어그램 | 약 1분 |
| 6 | 이슈에서 PR까지, AI 팀원과 협업 | 가치 | 약 1분 |
| 7 | 시연 흐름: GitHub Copilot | 시연 흐름 | 약 6.5분 |
| 8 | 데모 영상: GitHub Copilot | 데모 영상 | – |
| 9 | 핵심 설정: 팀 규칙을 저장소에 둡니다 | 핵심 코드 | 약 1분 |
| 10 | 안전한 협업의 기본값: Rulesets·보안·Codespaces | 가치 | 약 1분 |
| 11 | 시연 흐름: GitHub Repo | 시연 흐름 | 약 6분 |
| 12 | 데모 영상: GitHub Repo | 데모 영상 | – |
| 13 | 핵심 설정: 룰셋과 CODEOWNERS | 핵심 코드 | 약 1분 |
| 14 | 비밀 없는 CI/CD(OIDC)와 재사용 가능한 파이프라인 | 가치 | 약 1분 |
| 15 | 시연 흐름: GitHub Actions | 시연 흐름 | 약 7분 |
| 16 | 데모 영상: GitHub Actions | 데모 영상 | – |
| 17 | 핵심 코드: 저장된 비밀 0개 | 핵심 코드 | 약 1분 |
| 18 | 모델 선택권과 키 없는 보안 연결 | 가치 | 약 1분 |
| 19 | 시연 흐름: Microsoft Foundry | 시연 흐름 | 약 5.5분 |
| 20 | 데모 영상: Microsoft Foundry | 데모 영상 | – |
| 21 | 핵심 코드: OpenAI 호환 엔드포인트 + Entra ID | 핵심 코드 | 약 1분 |
| 22 | 서버리스 컨테이너, 스케일 투 제로, 리비전 카나리 | 가치 | 약 1분 |
| 23 | 시연 흐름: Azure Container Apps | 시연 흐름 | 약 7분 |
| 24 | 데모 영상: Azure Container Apps | 데모 영상 | – |
| 25 | 핵심 명령: 카나리와 스케일 규칙 | 핵심 코드 | 약 1분 |
| 26 | 롤링 업데이트, 자동 확장, 워크로드 ID, 보안 기본값 | 가치 | 약 1분 |
| 27 | 시연 흐름: AKS | 시연 흐름 | 약 7.5분 |
| 28 | 데모 영상: AKS | 데모 영상 | – |
| 29 | 핵심 설정: 워크로드 ID와 HPA | 핵심 코드 | 약 1분 |
| 30 | 선택 가이드: Container Apps vs AKS | 비교표 | 약 1.5분 |
| 31 | End-to-end: 아이디어에서 Foundry까지 | 다이어그램 | 약 1분 |
| 32 | 보안·비용·거버넌스 체크리스트 | 체크리스트 | 약 1분 |
| 33 | 서비스별 핵심 이점 한 장 요약 | 요약 | 약 1분 |
| 34 | 시작하기 · Q&A | 마무리 | 약 1분 |
| 35 | 부록 A. 사전 준비 체크리스트 | 부록 | – |
| 36 | 부록 B. 트러블슈팅 Top 5 | 부록 | – |
| 37 | 부록 C. 참고 링크 | 부록 | – |

---

## 1. GitHub Copilot in the Cloud

*표지*

### 화면 구성

- 제목: GitHub Copilot in the Cloud
- 부제: 아이디어에서 프로덕션까지
- 태그라인: GitHub × Microsoft Foundry × AKS / ACA
- 서비스 칩: GitHub Copilot · GitHub Repo · GitHub Actions · Microsoft Foundry · Container Apps · AKS
- 하단: 라이브 데모 6개 · Full 약 42분 · Lite 약 15분

### 말할 내용

- 안녕하세요. 오늘은 아이디어 하나가 프로덕션까지 가는 길을 GitHub와 Azure로 직접 만들어 보여 드리겠습니다.
- 슬라이드는 짧게 쓰고, 대부분의 시간은 라이브 데모에 씁니다. 여섯 가지 서비스를 순서대로 보시되, 각 데모는 단독으로도 시연할 수 있게 만들어져 있습니다.

### 시연 큐

- 시작 전: 터미널 글꼴을 키우고 알림을 끕니다. DEMO_PASSWORD는 export만 하고 화면에 출력하지 않습니다(printenv 금지).
- 슬라이드 쇼를 시작하기 전에 데모 1의 이슈를 미리 할당해 두었는지 확인합니다.

[예상 시간] 약 0.5분

---

## 2. 오늘의 여정: 데모 6개, 두 가지 경로

*개요 · 오프닝 · 오늘의 여정*

### 화면 구성

| # | 데모 | 내용 | 시간 | Lite |
|---|---|---|---|---|
| 1 | Copilot | 이슈 → 에이전트 PR → 리뷰 → 사람 merge | 7분 | 4분 |
| 2 | Repo | Rulesets · CODEOWNERS · 위험한 PR 차단 | 6분 | – |
| 3 | Actions | 병렬 CI와 비밀 없는 OIDC 배포 | 7분 | 4분 |
| 4 | Foundry | 키 없이 모델 호출 · /api/info | 7분 | 3분 |
| 5 | ACA | 스케일 투 제로 · 리비전 카나리 | 7분 | 4분 |
| 6 | AKS | 롤링 업데이트 · 자동 확장 · 워크로드 ID | 8분 | – |

- Full: 데모 합계 약 42분 · Lite: 약 15분
- 오프닝·마무리는 약 10분 별도

### 말할 내용

- 개발에서 운영까지 이어지는 순서로 여섯 가지를 봅니다. Copilot으로 만들고, 저장소 규칙으로 지키고, Actions로 배포하고, Foundry로 모델을 연결하고, Container Apps와 AKS에서 실행합니다.
- 전부 이어서 하면 데모 합계가 약 42분입니다. 시간이 짧으면 Lite 경로로 Copilot, Actions, Foundry, Container Apps만 핵심 단계로 약 15분에 마칩니다.
- 오프닝과 마무리 슬라이드는 합쳐서 약 10분이 따로 듭니다. 데모마다 가치 슬라이드는 1분, 핵심 코드 슬라이드는 시연 대기 시간에 겹쳐서 설명합니다.

### 시연 큐

- 오늘 청중에게 맞는 경로(Full 또는 Lite)를 말로 확정하고, Lite라면 각 흐름 슬라이드의 'Lite' 표시 단계만 진행합니다.
- Lite를 15분 슬롯에 맞추려면 3~5번과 24~27번 슬라이드는 한두 문장으로 줄이거나 건너뛰고 28번으로 마무리합니다.

[예상 시간] 약 1분

---

## 3. 전체 그림: 코드는 GitHub에서, 실행과 AI는 Azure에서

*다이어그램 · 오프닝 · 전체 그림*

### 화면 구성

- 흐름: 개발자 → GitHub(Copilot · 저장소 · Actions) → Azure(ACR → Container Apps / AKS → Microsoft Foundry)
- ID 흐름(주황색, 저장된 키 없음): 개발자 `az login` → Foundry · Actions `OIDC` → Azure · Container Apps `관리 ID` → Foundry · AKS `워크로드 ID` → Foundry
- 코드·이미지 흐름(회색): push · PR, Copilot PR, 저장소 → Actions, ACR 이미지 pull

### 말할 내용

- 왼쪽부터 보겠습니다. 개발자는 로컬이나 Codespaces에서 작업하고, 코드는 GitHub 저장소로 갑니다. Copilot이 PR을 만들고, 룰셋과 CI가 검사하고, Actions가 배포합니다.
- 오른쪽은 Azure입니다. Actions는 이미지를 ACR에 올리고, Container Apps와 AKS가 그 이미지를 받아 실행하며, 앱은 Microsoft Foundry의 gpt-6.1-sol을 호출합니다.
- 주황색 선에 주목해 주세요. 이 선이 모두 아이덴티티 흐름이고 저장된 키가 없습니다. 로컬은 az login, Actions는 OIDC, Container Apps는 관리 ID, AKS는 워크로드 ID를 씁니다.

### 시연 큐

- 선을 손가락이나 포인터로 따라가며 말합니다. 주황색 선 다섯 개를 하나씩 짚는 데 30초면 충분합니다.

[예상 시간] 약 1.5분

---

## 4. 독립 시연 구조: 어느 데모든 혼자서도 됩니다

*표 · 오프닝 · 독립 시연*

### 화면 구성

| 데모 | 필요한 것 | 혼자서도 되는 이유 |
|---|---|---|
| 1 Copilot | GitHub 저장소, Copilot 라이선스 | Azure 없이 이슈에서 PR까지 GitHub 안에서 |
| 2 Repo | GitHub 저장소(관리자 권한) | 설정이 파일이고, 앱은 Codespaces에서 mock 실행 |
| 3 Actions | GitHub 저장소 (2·3단계는 Azure) | CI는 Azure 없이, 배포 대상은 따로 만들기 |
| 4 Foundry | Azure 구독(Enterprise 또는 MCA-E) | az login과 로컬 앱만으로 호출 |
| 5 ACA | Azure 구독 | mock 백엔드라 Foundry 없이 시연 |
| 6 AKS | Azure 구독 | 같은 이미지, 같은 mock 백엔드 |

- LLM_BACKEND=mock — Foundry 없이도 앱 전체가 동작합니다(CI와 데모 5·6의 기본값)

### 말할 내용

- 이 키트의 설계 원칙은 독립 시연입니다. 어떤 데모도 다른 데모를 먼저 할 필요가 없습니다.
- 비결은 mock 백엔드입니다. LLM_BACKEND를 mock으로 두면 Foundry도 Azure도 없이 앱 전체가 돌아가서, CI와 Container Apps, AKS 데모는 모델 호출 비용 없이 시연됩니다.
- 그래서 청중과 시간에 맞게 데모를 골라서 쓰시면 됩니다. 필요한 계정과 구독은 표에 있습니다.

### 시연 큐

- README의 독립 실행 매트릭스를 한 번 가리키고 넘어갑니다.

[예상 시간] 약 0.5분

---

## 5. 샘플 앱: 이미지 하나가 어디서나 동작합니다

*다이어그램 · 오프닝 · 샘플 앱*

### 화면 구성

- 흐름: 브라우저 UI → `POST /api/chat` → Python 앱(stdlib, `app/server.py`) → Entra ID 토큰 → Microsoft Foundry(gpt-6.1-sol, effort `xhigh`)
- `GET /healthz`: 인증 없음, 플랫폼 프로브용
- `GET /api/info`: 인증 필요, `backend` `auth` `model` `effort` `platform` `instance` `revision`
- `POST /api/chat`: 데모 인증 뒤
- 같은 이미지: 로컬·Codespaces(`az login`) · Container Apps(관리 ID) · AKS(워크로드 ID)

### 말할 내용

- 데모에 쓰는 앱은 아주 작은 챗 앱입니다. 브라우저에서 질문하면 /api/chat이 Microsoft Foundry의 gpt-6.1-sol을 높은 effort로 호출하고, 답변과 함께 어느 플랫폼과 리비전이 응답했는지 화면에 보여 줍니다.
- 엔드포인트는 셋입니다. /healthz는 플랫폼 프로브용이라 인증이 없고, /api/info는 backend, auth, model, effort 같은 설정을 보여 주며, /api/chat은 데모 인증 뒤에 있습니다.
- 컨테이너 이미지는 하나입니다. 로컬과 Codespaces, Container Apps, AKS에서 같은 이미지가 돌고, 달라지는 것은 Entra ID 토큰을 얻는 경로뿐입니다.

### 시연 큐

- 여기서 앱을 열지는 않습니다. 데모 4에서 처음 실행하므로 구조만 짚고 넘어갑니다.

[예상 시간] 약 1분

---

## 6. 이슈에서 PR까지, AI 팀원과 협업

*가치 · 데모 1 / 6 · GitHub Copilot · 가치*

### 화면 구성

- 데모 1 · GitHub Copilot · 약 7분 (Lite 4분)
- 필요한 것: GitHub 저장소 + Copilot 라이선스
- 독립 시연: Azure 불필요
- 이점 카드:
  - **생산성** — 이슈를 쓰면 에이전트가 코드와 테스트를 만들어 초안 PR로 올립니다. (시연: 이슈 할당 → 초안 PR)
  - **팀 표준의 코드화** — 지침·프롬프트·전용 에이전트를 코드처럼 버전 관리하고 PR로 리뷰합니다. (시연: .github/ 아래 설정 파일)
  - **안전한 자동화** — 에이전트는 copilot/ 브랜치에만 쓰고 승인·merge는 사람이 합니다. (시연: CI + Copilot 리뷰)
  - **클라우드 연결** — Azure MCP로 리소스를 조회하고 Copilot CLI로 터미널에서 이어 갑니다. (시연: (옵션) agent mode)

### 말할 내용

- 첫 번째는 GitHub Copilot입니다. 이슈 하나를 AI 팀원, 즉 Copilot cloud agent에게 맡기고 결과를 PR로 받습니다.
- 핵심은 속도만이 아닙니다. 팀의 규칙이 저장소 안의 파일로 들어 있어서 에이전트도 사람과 같은 규칙을 따릅니다.
- 마지막 관문은 항상 사람입니다. 에이전트는 승인도 merge도 할 수 없습니다.

### 시연 큐

- 에이전트 작업에는 몇 분이 걸리므로 시연 10~15분 전에 이슈 하나를 미리 할당해 두고, 그 PR 탭을 열어 둡니다.

[예상 시간] 약 1분 · 데모 1 전체 약 7분

---

## 7. 시연 흐름: GitHub Copilot

*시연 흐름 · 데모 1 / 6 · GitHub Copilot · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. 설정 둘러보기 | 1분 | `GitHub → .github/ 폴더`<br>`copilot-instructions.md`<br>`instructions/ prompts/ agents/` | 규칙 목록과 applyTo 줄이 보인다 | Lite |
| 2. 이슈 만들고 할당 | 1.5분 | `scripts/create-demo-issues.sh`<br>`--apply --assign-copilot`<br>`--only 3` | Copilot 담당자가 붙고 눈 반응이 달린다 |  |
| 3. 세션 · PR · CI | 2분 | `View session`<br>`Files changed`<br>`Approve and run workflows` | 초안 PR, CI job이 모두 초록색 | Lite |
| 4. 리뷰와 merge | 2분 | `Ready for review`<br>`Reviewers → Copilot`<br>`사람 승인 → merge` | Copilot 코멘트 뒤 사람이 승인·merge | Lite |

- 옵션 · agent mode (2분): VS Code Agent 모드 · /add-endpoint GET /api/version · MCP: List Servers → azure
- 참고: UI 메뉴 이름은 변경될 수 있으니 같은 뜻의 메뉴를 찾아 주세요.

### 말할 내용

- 먼저 .github 폴더의 Copilot 설정을 보여 주고, 이슈를 만들어 Copilot에게 할당합니다.
- 작업에는 시간이 걸리므로 미리 만들어 둔 PR로 이동해 세션 로그, 변경 파일, CI를 확인합니다.
- Ready for review로 바꾸고 Copilot code review를 요청한 뒤, 사람이 판단해서 merge합니다.

### 시연 큐

- 1) GitHub에서 .github/copilot-instructions.md → instructions/ → prompts/ → agents/ 순서로 엽니다.
- 2) scripts/create-demo-issues.sh --apply --assign-copilot --only 3 (또는 이슈 폼 → Assignees → Copilot).
- 3) 타임라인의 View session → Files changed → 대기 중이면 Approve and run workflows.
- 4) Ready for review → Reviewers에서 Copilot 요청(gh pr edit <PR번호> --add-reviewer "@copilot"). 룰셋이 켜져 있으면 에이전트를 시킨 본인은 승인할 수 없으니 관리자 우회나 다른 계정을 준비합니다.
- 5) (옵션) VS Code Agent 모드에서 /add-endpoint GET /api/version, MCP: List Servers → azure.
- UI 메뉴 이름은 변경될 수 있으니 같은 뜻의 메뉴를 찾아 주세요. Lite 경로: 1·3·4단계만 진행합니다.

[예상 시간] 단계 합계 약 6.5분 (옵션 5단계 약 2분 별도)

---

## 8. 데모 영상: GitHub Copilot

*데모 영상 · 데모 1 / 6 · GitHub Copilot · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/copilot.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/copilot.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 9. 핵심 설정: 팀 규칙을 저장소에 둡니다

*핵심 코드 · 데모 1 / 6 · GitHub Copilot · 핵심 코드*

### 화면 구성

**.github/copilot-instructions.md (발췌)**

```
# Copilot instructions — Cloud Copilot Demo
- Python 3.12 + stdlib only; no new dependencies
- Test: python -m unittest discover -s app/tests -v
- GET /healthz is the only unauthenticated route
- Prefer keyless Entra ID (DefaultAzureCredential)
- Never log or commit secrets, keys or tokens
- Keep LLM_BACKEND=mock working offline
- Render model output with textContent, never innerHTML
- A human reviews and merges; never self-approve
```

**이슈에서 merge까지**: 이슈 → @copilot → 초안 PR → CI → Copilot 리뷰 → 사람 merge

- 콜아웃:
  - **한 번 쓰면 모두 적용** — 에이전트·VS Code·코드 리뷰가 같은 지침을 읽습니다.
  - **경로별 규칙** — `applyTo`로 Python·Bicep·K8s마다 다른 규칙을 줍니다.
  - **사람이 마지막 관문** — 에이전트는 승인과 merge를 할 수 없습니다.

### 말할 내용

- 왼쪽은 저장소 공통 지침의 발췌입니다. 이 파일은 .github 아래에 있고 에이전트와 코드 리뷰가 자동으로 읽습니다.
- 규칙을 바꾸고 싶으면 이 파일을 PR로 고치면 됩니다. 사람이 따르는 코딩 규칙과 에이전트가 따르는 규칙이 한 곳에 있습니다.
- 아래 띠는 방금 본 흐름입니다. 이슈에서 시작해 사람의 merge로 끝납니다.

### 시연 큐

- 에이전트가 작업하는 대기 시간에 이 슬라이드로 설명하면 시간이 겹쳐서 절약됩니다.

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 10. 안전한 협업의 기본값: Rulesets·보안·Codespaces

*가치 · 데모 2 / 6 · GitHub Repo · 가치*

### 화면 구성

- 데모 2 · GitHub Repo · 약 6분
- 필요한 것: GitHub 저장소(관리자 권한)
- 독립 시연: Azure 불필요
- 이점 카드:
  - **main 보호** — PR 필수, 필수 체크, 코드 오너 리뷰를 통과해야 merge됩니다. (시연: 룰셋 Active, 체크 3개)
  - **책임 분리** — 바뀐 경로의 책임자가 자동으로 리뷰어가 되고 승인이 필수가 됩니다. (시연: CODEOWNERS 한 줄)
  - **공급망·코드 보안** — CodeQL, Dependency review, Dependabot, secret scanning을 켭니다. (시연: 위험한 PR이 막힘)
  - **클릭 몇 번으로 시작** — Codespaces로 설치 없이 테스트·앱을 실행하고 설정은 파일로 관리합니다. (시연: 테스트 OK, /healthz 200)

### 말할 내용

- 두 번째는 GitHub 저장소 자체입니다. 좋은 협업은 기능이 아니라 기본값에서 시작합니다.
- main 보호, 코드 오너, 보안 검사가 모두 저장소 안의 파일과 스크립트로 정의되어 있어서 새 저장소에 그대로 가져갈 수 있습니다.
- Codespaces로 설치 없이 개발 환경을 얻고, 마지막에는 일부러 위험하게 만든 PR이 어떻게 걸러지는지 보여 드립니다.

### 시연 큐

- Codespace는 미리 하나 만들어 두고, 위험한 PR도 미리 열어 CodeQL 분석이 끝난 화면을 준비합니다.
- 설정 스크립트는 저장소 설정을 바꾸므로 연습용 저장소나 포크에서 먼저 리허설합니다.

[예상 시간] 약 1분 · 데모 2 전체 약 6분

---

## 11. 시연 흐름: GitHub Repo

*시연 흐름 · 데모 2 / 6 · GitHub Repo · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. Codespaces 시작 | 1분 | `Code → Codespaces → Create`<br>`python -m unittest discover`<br>`-s app/tests -v` | 테스트 통과, /healthz 200 |  |
| 2. Rulesets 확인 | 2분 | `main-protection.json, CODEOWNERS`<br>`scripts/apply-repo-settings.sh`<br>`(dry-run) → --apply` | main-protection이 Active로 보인다 |  |
| 3. 위험한 PR | 2분 | `demos/02-github-repo/risky-pr/`<br>`make-risky-pr.sh --apply`<br>`→ PR 체크와 merge 상자 확인` | 보안 검사가 잡고 merge가 막힌다 |  |
| 4. Dependabot | 1분 | `.github/dependabot.yml`<br>`Security → Dependabot`<br>`gh pr list --label dependencies` | 업데이트 기록 또는 PR이 보인다 |  |
- 참고: 설정 스크립트는 저장소 설정을 바꿉니다. 연습용 저장소에서 먼저 리허설하세요. [DEMO – DO NOT MERGE] PR은 merge하지 않습니다.

### 말할 내용

- Codespaces에서 테스트와 mock 모드 앱을 실행해 설치할 것이 없다는 점을 보여 줍니다.
- 룰셋 JSON을 열어 규칙마다 이유를 설명합니다. apply-repo-settings.sh는 dry-run 출력까지만 청중 앞에서 보여 줍니다.
- 위험한 PR에서는 CodeQL, Dependency review, Copilot review, 그리고 막힌 merge 상자를 차례로 짚습니다. 관리자에게 보이는 우회 옵션은 쓰지 않습니다.

### 시연 큐

- 1) Code → Codespaces → Create codespace on main → python -m unittest discover -s app/tests -v → LLM_BACKEND=mock python -m app.server (DEMO_PASSWORD는 임시 값).
- 2) .github/rulesets/main-protection.json, .github/CODEOWNERS → scripts/apply-repo-settings.sh (dry-run). --apply는 미리 실행해 둡니다.
- 3) 로컬 터미널에서 demos/02-github-repo/risky-pr/make-risky-pr.sh --apply. PR 제목은 [DEMO – DO NOT MERGE]이며 절대 merge하지 않습니다.
- 4) .github/dependabot.yml → Security → Dependabot, gh pr list --label dependencies.
- secret scanning과 push protection은 토큰 모양 문자열을 만들지 않고 말로만 설명합니다. UI 메뉴 이름은 변경될 수 있으니 같은 뜻의 메뉴를 찾아 주세요.

[예상 시간] 단계 합계 약 6분 (1 + 2 + 2 + 1분)

---

## 12. 데모 영상: GitHub Repo

*데모 영상 · 데모 2 / 6 · GitHub Repo · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/repo.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/repo.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 13. 핵심 설정: 룰셋과 CODEOWNERS

*핵심 코드 · 데모 2 / 6 · GitHub Repo · 핵심 코드*

### 화면 구성

**.github/rulesets/main-protection.json (요약)**

- `pull_request` — PR 필수 · 승인 1건 · 코드 오너 리뷰 필수
- `required_status_checks` — Unit tests · Container build and smoke test · IaC validation
- `non_fast_forward` — 강제 푸시(force push) 금지
- `code_scanning` — CodeQL 알림이 기준 이상이면 차단

**.github/CODEOWNERS**

```
/app/      @junwoojeong100
/.github/  @junwoojeong100
```

- 콜아웃:
  - **필수 체크 = job 이름** — 룰셋의 체크 이름은 CI job 이름과 같아야 합니다.
  - **관리자 우회는 타협** — 1인 저장소라 열어 뒀습니다. 팀에서는 비우세요.
  - **설정도 코드** — JSON을 가져오거나 스크립트로 한 번에 적용합니다.

### 말할 내용

- 룰셋은 JSON 하나입니다. PR 필수, 필수 상태 체크 세 개, 코드 오너 리뷰, 강제 푸시와 삭제 금지, CodeQL 알림 기준이 들어 있습니다.
- 필수 체크 이름은 CI의 job 표시 이름과 같아야 해서, 워크플로를 바꿀 때 룰셋도 함께 봐야 합니다.
- CODEOWNERS는 경로별 책임자를 지정하고, 룰셋의 코드 오너 리뷰 규칙과 만나 승인이 필수가 됩니다. 이 데모는 1인 저장소라 Admin의 PR 우회를 열어 두었다는 점도 솔직하게 말씀드립니다.

### 시연 큐

- 팀 저장소라면 bypass_actors를 비우고 CODEOWNERS를 @org/team으로 바꾸라고 안내합니다.

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 14. 비밀 없는 CI/CD(OIDC)와 재사용 가능한 파이프라인

*가치 · 데모 3 / 6 · GitHub Actions · 가치*

### 화면 구성

- 데모 3 · GitHub Actions · 약 7분 (Lite 4분)
- 필요한 것: GitHub (배포는 Azure 구독)
- 독립 시연: CI는 Azure 불필요
- 이점 카드:
  - **빠른 피드백** — 독립 job 4개가 병렬로 돌고 pip 의존성은 캐시합니다. (시연: PR에서 4개 job 동시 실행)
  - **비밀 없는 배포** — 짧게 사는 OIDC 토큰을 Azure가 신뢰합니다. 저장되는 것은 식별자뿐입니다. (시연: Secrets 목록이 비어 있음)
  - **최소 권한·승인** — 기본은 읽기 전용, 배포 job만 id-token: write. 승인 뒤에 로그인합니다. (시연: Review deployments 승인)
  - **공급망 증명** — 액션을 커밋 SHA로 고정하고 배포 이미지의 빌드 출처 증명을 남깁니다. (시연: Attest the build provenance)

### 말할 내용

- 세 번째는 GitHub Actions입니다. PR마다 병렬로 도는 검증, 그리고 저장된 비밀 없이 Azure에 배포하는 방법 두 가지를 보여 드립니다.
- OIDC는 GitHub가 job마다 발급하는 짧은 수명의 토큰을 Azure가 신뢰하게 만드는 방식입니다. 저장소에는 비밀번호도 키도 없고 클라이언트 ID 같은 식별자만 변수로 있습니다.
- 배포 전에는 환경 승인 게이트가 있어서, 사람이 승인하기 전에는 Azure에 아무것도 닿지 않습니다.

### 시연 큐

- 1단계는 GitHub만 있으면 됩니다. 2·3단계는 Azure 구독이 필요하며 배포 대상은 scripts/deploy-aca.sh --yes로 미리 만들어 둡니다(mock 백엔드).

[예상 시간] 약 1분 · 데모 3 전체 약 7분

---

## 15. 시연 흐름: GitHub Actions

*시연 흐름 · 데모 3 / 6 · GitHub Actions · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. CI 병렬 실행 | 2분 | `gh pr checks --watch`<br>`(PR의 Checks 탭에서도 확인)` | 4개 job 초록색, Smoke test 14개 통과 |  |
| 2. 비밀 없는 신뢰 | 2분 | `scripts/setup-github-oidc.sh`<br>`(미리보기) → --apply`<br>`Settings → Secrets: 비어 있음` | 환경 변수만 있고 Secrets는 비어 있다 | Lite |
| 3. 승인 → 배포 | 3분 | `gh workflow run deploy-aca.yml`<br>`Review deployments → 승인`<br>`gh run watch` | 앱 버전이 커밋 앞 7자리로 바뀐다 | Lite |
- 참고: 1단계는 Azure 없이 가능합니다. 2·3단계는 배포 대상이 필요합니다(scripts/deploy-aca.sh --yes).

### 말할 내용

- 먼저 PR을 열고 CI의 job 네 개가 동시에 도는 모습을 보여 드립니다. Azure 자격 증명은 필요 없습니다.
- 다음은 setup-github-oidc.sh로 Azure 쪽 신뢰를 구성하는 부분입니다. 끝난 뒤 Settings의 Secrets 목록이 비어 있다는 것을 직접 확인해 주세요.
- 마지막으로 배포 워크플로를 실행하고 환경 승인, OIDC 로그인, 새 리비전 순서를 따라갑니다.

### 시연 큐

- 1) 작은 변경으로 PR → gh pr checks --watch → Container build and smoke test의 Smoke test 단계 로그(14개 확인).
- 2) scripts/setup-github-oidc.sh (미리보기) → --apply → Settings → Secrets and variables → Actions에서 Secrets 없음, 변수만 있음.
- 3) gh workflow run deploy-aca.yml → Review deployments에서 azure-demo 승인 → gh run watch → Summary의 앱 주소·리비전, 앱 화면의 버전.
- UI 메뉴 이름은 변경될 수 있으니 같은 뜻의 메뉴를 찾아 주세요. Lite 경로: 2·3단계만(3단계는 미리 돌려 둔 실행을 보여 주고 승인 단계만 라이브).

[예상 시간] 단계 합계 약 7분 (2 + 2 + 3분)

---

## 16. 데모 영상: GitHub Actions

*데모 영상 · 데모 3 / 6 · GitHub Actions · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/actions.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/actions.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 17. 핵심 코드: 저장된 비밀 0개

*핵심 코드 · 데모 3 / 6 · GitHub Actions · 핵심 코드*

### 화면 구성

**.github/workflows/deploy-aca.yml (발췌)**

```
permissions:
  id-token: write   # OIDC 토큰 발급
  contents: read

steps:
  - uses: azure/login@v3
    with:
      client-id: ${{ vars.AZURE_CLIENT_ID }}
      tenant-id: ${{ vars.AZURE_TENANT_ID }}
      subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

- 콜아웃:
  - **저장된 비밀 0개** — ID 값은 비밀이 아닌 `vars`에 둡니다.
  - **좁은 신뢰 범위** — `environment:azure-demo`의 job만 로그인합니다.
  - **최소 권한** — `id-token: write`는 배포 job에만 줍니다.

### 말할 내용

- 이 몇 줄이 비밀 없는 배포의 전부입니다. permissions에서 id-token: write를 주면 job이 OIDC 토큰을 받을 수 있고, azure/login이 그 토큰을 Azure 토큰으로 교환합니다.
- client-id, tenant-id, subscription-id는 비밀이 아니라 식별자라서 secrets가 아니라 vars에 둡니다. 저장된 비밀은 0개입니다.
- Azure 쪽에는 subject가 repo:<owner>/<repo>:environment:azure-demo인 페더레이션 자격 증명이 있어서, 이 저장소의 azure-demo 환경을 쓰는 job만 로그인할 수 있습니다.

### 시연 큐

- 발췌는 가독성을 위해 azure/login@v3로 적었고 실제 워크플로는 액션을 커밋 SHA로 고정합니다. <owner>/<repo>는 자신의 저장소 값입니다.

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 18. 모델 선택권과 키 없는 보안 연결

*가치 · 데모 4 / 6 · Microsoft Foundry · 가치*

### 화면 구성

- 데모 4 · Microsoft Foundry · 약 7분 (Lite 3분)
- 필요한 것: Azure 구독 + gpt-6.1-sol 쿼터
- 독립 시연: GitHub·ACA·AKS 불필요
- 이점 카드:
  - **Azure 거버넌스** — Entra ID·RBAC·쿼터·리전을 다른 Azure 리소스와 같은 방식으로 씁니다. (시연: 배포 목록의 gpt-6.1-sol 배포)
  - **배포 이름으로 교체** — 앱은 배포 이름만 압니다. 모델 교체는 환경 변수 하나면 됩니다. (시연: FOUNDRY_MODEL만 변경)
  - **effort = xhigh** — 요청마다 추론 깊이를 지정하고 환경 변수로 low부터 xhigh까지 조절합니다. (시연: /api/info의 effort: xhigh)
  - **키 없는 인증** — 로컬은 az login, ACA는 관리 ID, AKS는 워크로드 ID로 같은 코드가 동작합니다. (시연: /api/info의 auth: entra-id)

### 말할 내용

- 네 번째는 Microsoft Foundry입니다. gpt-6.1-sol을 Azure의 거버넌스 안에서 키 없이 쓰는 방법을 보여 드립니다.
- Entra ID 인증, RBAC, 쿼터와 리전 같은 Azure 리소스의 관리 방식이 그대로 적용됩니다. 앱은 모델이 아니라 배포 이름만 알기 때문에 모델 교체가 설정 변경으로 끝납니다.
- 요청마다 effort를 지정해 깊은 추론을 씁니다. 이 키트의 기본값 max는 GPT가 받는 가장 높은 단계인 xhigh로 전달됩니다. 깊게 생각하는 만큼 시간과 토큰을 더 쓴다는 점도 함께 말씀드립니다.

### 시연 큐

- gpt-6.1-sol은 모델 쿼터가 있는 구독이면 배포할 수 있고, 지원 리전은 eastus2, swedencentral, westus2입니다. Claude를 쓰려면 Enterprise 또는 MCA-E 구독과 Anthropic 약관 동의가 필요합니다.
- 배포(scripts/deploy-foundry.sh)는 몇 분 걸리므로 시연 전에 끝내 둡니다.

[예상 시간] 약 1분 · 데모 4 전체 약 7분

---

## 19. 시연 흐름: Microsoft Foundry

*시연 흐름 · 데모 4 / 6 · Microsoft Foundry · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. 배포 확인 | 1.5분 | `az cognitiveservices account`<br>`deployment list ... -o table`<br>`(또는 ai.azure.com 포털)` | gpt-6.1-sol 배포, API 키 없음 |  |
| 2. 키 없이 호출 | 2.5분 | `az login`<br>`source .azure/foundry.env`<br>`python -m app.server` | 한국어 답변, 인스턴스 표시 | Lite |
| 3. /api/info 확인 | 1.5분 | `curl -s -u "demo:$DEMO_PASSWORD"`<br>`http://127.0.0.1:8080/api/info` | auth: entra-id, model, effort: xhigh | Lite |

- 옵션 · 모델·effort 교체 (1.5분): FOUNDRY_EFFORT=low python -m app.server · FOUNDRY_MODEL=<다른 배포 이름>
- 참고: 배포(deploy-foundry.sh)는 시연 전에 끝내 두세요. 역할 부여 직후에는 전파 지연이 있을 수 있습니다.

### 말할 내용

- 배포된 모델을 확인하고, 연결 정보 파일에 API 키가 없다는 점을 먼저 보여 드립니다.
- az login만 한 상태에서 로컬 앱을 띄워 한국어로 질문합니다. 코드에는 키가 없고 DefaultAzureCredential이 토큰을 받아 옵니다.
- 마지막으로 /api/info에서 인증 방식이 entra-id이고 모델과 effort가 설정대로인지 확인합니다.

### 시연 큐

- 1) cat .azure/foundry.env → source .azure/foundry.env → az cognitiveservices account deployment list --resource-group "$FOUNDRY_RESOURCE_GROUP" --name "$FOUNDRY_RESOURCE" --output table.
- 2) az login → source .azure/foundry.env → export DEMO_PASSWORD='<임의 값>' → python -m app.server → http://127.0.0.1:8080(사용자 demo) → 한국어로 질문.
- 3) curl -s -u "demo:$DEMO_PASSWORD" http://127.0.0.1:8080/api/info → backend foundry · auth entra-id · model gpt-6.1-sol · effort xhigh.
- 4) (옵션) FOUNDRY_EFFORT=low python -m app.server로 같은 질문을 비교합니다.
- 역할을 방금 부여했다면 전파에 몇 분이 걸려 첫 호출이 권한 오류일 수 있습니다. Lite 경로: 2·3단계.

[예상 시간] 단계 합계 약 5.5분 + 옵션 1.5분 = 약 7분

---

## 20. 데모 영상: Microsoft Foundry

*데모 영상 · 데모 4 / 6 · Microsoft Foundry · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/foundry.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/foundry.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 21. 핵심 코드: OpenAI 호환 엔드포인트 + Entra ID

*핵심 코드 · 데모 4 / 6 · Microsoft Foundry · 핵심 코드*

### 화면 구성

**app/server.py (발췌, 키 없는 경로)**

```
token = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default")
headers = {"Authorization":
           f"Bearer {token()}"}
body = {
    "model": "gpt-6.1-sol",  # 배포 이름
    "max_completion_tokens": 4096,
    "reasoning_effort": "xhigh",
    "messages": messages}
url = f"https://{resource}.services.ai.azure.com"
      "/openai/v1/chat/completions"
```

- 콜아웃:
  - **model = 배포 이름** — 모델 ID가 아닌 Foundry 배포 이름입니다.
  - **키가 없다** — `DefaultAzureCredential`이 토큰을 얻습니다.
  - **effort = xhigh** — GPT의 최고 단계입니다. 추론은 깊어지고 시간·토큰은 늘어납니다.

### 말할 내용

- 코드는 이 열두 줄입니다. get_bearer_token_provider가 DefaultAzureCredential로 Entra ID 토큰을 받아 오고, 그 토큰을 Authorization 헤더에 실어 Foundry의 OpenAI 호환 엔드포인트를 부릅니다. API 키는 어디에도 없습니다.
- model 인자는 모델 ID가 아니라 Foundry의 배포 이름입니다. 다른 모델을 배포했다면 이름만 바꾸면 됩니다.
- reasoning_effort로 추론 깊이를 지정했고, 낮추려면 환경 변수만 바꾸면 됩니다.

### 시연 큐

- 로컬은 az login, ACA는 관리 ID, AKS는 워크로드 ID가 같은 DefaultAzureCredential 경로로 토큰을 만든다고 다음 두 데모의 복선으로 말합니다.
- 필요한 역할은 Cognitive Services User 하나입니다. API 키(FOUNDRY_API_KEY)는 선택적 대안일 뿐입니다. Claude 배포는 이름이 claude로 시작하면 자동으로 AnthropicFoundry 경로를 씁니다.

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 22. 서버리스 컨테이너, 스케일 투 제로, 리비전 카나리

*가치 · 데모 5 / 6 · Azure Container Apps · 가치*

### 화면 구성

- 데모 5 · Azure Container Apps · 약 7분 (Lite 4분)
- 필요한 것: Azure 구독
- 독립 시연: mock 백엔드라 Foundry 불필요
- 이점 카드:
  - **클러스터 운영 없음** — 이미지와 설정만 올리면 HTTPS 주소가 생깁니다. 노드를 관리하지 않습니다. (시연: deploy-aca.sh → URL)
  - **스케일 투 제로** — 요청이 없으면 복제본이 0개가 되고 다음 요청에 다시 시작합니다. (시연: Replicas 0 → 1)
  - **리비전 카나리** — 새 리비전에 트래픽 일부만 보내고 승격하거나 즉시 롤백합니다. (시연: 90/10 분할을 probe로 확인)
  - **관리 ID와 로그** — 관리 ID로 비밀 없이 Foundry를 호출하고 로그는 Log Analytics로 모입니다. (시연: (옵션) auth: entra-id)

### 말할 내용

- 다섯 번째는 Azure Container Apps입니다. 클러스터를 운영하지 않고 컨테이너를 HTTPS로 서비스하는 서버리스 컨테이너입니다.
- 요청이 없으면 복제본이 0개로 줄어 컴퓨팅 비용이 멈추고, 새 버전은 리비전으로 올려 트래픽을 나눠 보냅니다.
- 카나리와 롤백이 설정 변경만으로 끝난다는 점이 이 데모의 핵심입니다.

### 시연 큐

- 배포 후 시연 시작 전까지 앱에 요청을 보내지 마세요(브라우저 탭과 스모크 테스트도 요청입니다). 그래야 복제본 0개를 보여 줄 수 있습니다.

[예상 시간] 약 1분 · 데모 5 전체 약 7분

---

## 23. 시연 흐름: Azure Container Apps

*시연 흐름 · 데모 5 / 6 · Azure Container Apps · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. 스케일 투 제로 | 1.5분 | `az containerapp revision list`<br>`-g $RG -n $APP -o table`<br>`curl $APP_URL/healthz  # 2회` | Replicas 0 → 첫 요청 느림 → 1 | Lite |
| 2. 배포 확인 | 1분 | `브라우저로 $APP_URL 열기`<br>`scripts/smoke-test.sh $APP_URL`<br>`--expect-backend mock` | 플랫폼 칩 aca, 모든 확인 통과 |  |
| 3. 리비전 카나리 | 3분 | `scripts/aca-canary.sh`<br>`deploy v2 → canary 10 → probe 30`<br>`→ promote  (또는 rollback)` | v1·v2가 섞여 응답, promote 후 v2만 | Lite |
| 4. 부하와 스케일 아웃 | 1.5분 | `scripts/load-test.sh`<br>`--url $APP_URL --duration 120`<br>`--concurrency 20` | 복제본이 늘어난다(최대 5) |  |
- 참고: 배포 후 시연 전까지 요청을 보내지 마세요(브라우저 탭·스모크 테스트도 요청입니다). 그래야 복제본 0개를 보여 줄 수 있습니다.

### 말할 내용

- 먼저 아무 요청도 없는 상태에서 Replicas가 0인 것을 보여 주고, 첫 요청이 느린 콜드 스타트를 확인합니다.
- 다음은 리비전 카나리입니다. v2를 0%로 올리고 10%만 보낸 뒤 승격하거나 즉시 되돌립니다.
- 마지막으로 부하를 걸어 복제본이 늘어나는 모습을 봅니다.

### 시연 큐

- 1) az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo -o table에서 Replicas 0 → curl로 $APP_URL/healthz를 두 번(첫 요청 느림, 두 번째 빠름) → 다시 revision list에서 Replicas 1.
- 2) 브라우저로 $APP_URL → 정보 칩의 플랫폼 aca → scripts/smoke-test.sh "$APP_URL" --wait 60 --expect-backend mock.
- 3) scripts/aca-canary.sh status → deploy v2 → canary 10 → 브라우저의 '트래픽 분포 보기' 또는 probe 30 → promote → probe → rollback.
- 4) 터미널 A에서 revision list를 5초마다 반복하고, 터미널 B에서 scripts/load-test.sh --url "$APP_URL" --duration 120 --concurrency 20.
- Lite 경로: 1·3단계. 대기 시간이 없다면 1단계는 말로 설명합니다.

[예상 시간] 단계 합계 약 7분 (1.5 + 1 + 3 + 1.5분)

---

## 24. 데모 영상: Azure Container Apps

*데모 영상 · 데모 5 / 6 · Azure Container Apps · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/aca.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/aca.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 25. 핵심 명령: 카나리와 스케일 규칙

*핵심 코드 · 데모 5 / 6 · Azure Container Apps · 핵심 코드*

### 화면 구성

**scripts/aca-canary.sh · az containerapp**

```
scripts/aca-canary.sh deploy v2  # 새 리비전, 0%
scripts/aca-canary.sh canary 10  # v2 10% · 이전 90%
scripts/aca-canary.sh probe 30   # 30회 호출 집계
scripts/aca-canary.sh promote    # v2 100% (또는 rollback)

# 스크립트가 쓰는 az 명령
az containerapp revision list -g $RG -n $APP -o table
az containerapp ingress traffic set -g $RG -n $APP \
  --label-weight blue=90 green=10
```

- 콜아웃:
  - **스케일 투 제로** — min 0 · max 5, 유휴 시 복제본이 0개가 됩니다.
  - **리비전 = 스냅샷** — 새 버전은 새 리비전, 레이블로 먼저 확인합니다.
  - **즉시 롤백** — `rollback`이 이전 리비전에 100%를 돌립니다.

### 말할 내용

- 카나리는 스크립트 네 줄입니다. deploy가 새 리비전을 트래픽 0%로 만들고, canary 10이 10 대 90으로 나누고, probe가 호출 비율을 집계합니다. 마지막은 promote 또는 rollback입니다.
- 스크립트가 쓰는 것은 az containerapp의 트래픽 분할 명령이고, 레이블 가중치로 blue와 green을 나눕니다.
- 스케일 규칙은 Bicep에 있습니다. 최소 복제본 0, 최대 5, 동시 요청 5건당 복제본 하나입니다.

### 시연 큐

- rollback은 이전 리비전으로 100%를 되돌릴 뿐 새 리비전은 남아 있어서 다시 승격할 수 있다고 덧붙입니다.

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 26. 롤링 업데이트, 자동 확장, 워크로드 ID, 보안 기본값

*가치 · 데모 6 / 6 · AKS · 가치*

### 화면 구성

- 데모 6 · AKS · 약 8분
- 필요한 것: Azure 구독
- 독립 시연: mock 백엔드라 Foundry 불필요
- 이점 카드:
  - **Kubernetes 그대로** — kubectl·매니페스트·생태계를 그대로 쓰고 컨트롤 플레인은 Azure가 운영합니다. (시연: kubectl get deploy,hpa,pdb)
  - **무중단 롤링 업데이트** — 새 파드가 준비된 뒤에만 이전 파드가 내려가고, 한 줄로 롤백합니다. (시연: v1 → v2 → 롤백)
  - **자동 확장** — HPA는 CPU 50%를 기준으로 파드를 2~5개로, 노드는 오토스케일러가 조절합니다. (시연: REPLICAS가 늘어남)
  - **비밀 없는 ID** — 워크로드 ID로 비밀 없이 Azure를 호출하고 클러스터 접근은 Entra ID로만 합니다. (시연: SA 어노테이션 + 주입 변수)

### 말할 내용

- 여섯 번째는 AKS입니다. 쿠버네티스가 잘하는 일을 눈으로 보여 드립니다. 무중단 롤링 업데이트, 부하에 따른 자동 확장, 비밀 없는 워크로드 ID입니다.
- 컨트롤 플레인은 Azure가 운영하고, 접근은 로컬 계정 없이 Entra ID와 Azure RBAC로만 합니다. 네임스페이스에는 Pod Security restricted가 강제됩니다.
- ACA보다 손이 가는 만큼 제어할 수 있는 것이 많다는 이야기를 마지막 비교 슬라이드에서 이어 가겠습니다.

### 시연 큐

- 클러스터 배포(5~10분)와 v2 이미지 빌드(az acr build ... --image cloud-copilot-demo:v2 --build-arg APP_VERSION=v2)는 시연 전에 끝내 둡니다.
- 터미널 셋을 준비합니다: 명령용, --watch용, port-forward용.

[예상 시간] 약 1분 · 데모 6 전체 약 8분

---

## 27. 시연 흐름: AKS

*시연 흐름 · 데모 6 / 6 · AKS · 시연 흐름*

### 화면 구성

| 단계 | 시간 | 명령 · 클릭 | 성공 기준 | Lite |
|---|---|---|---|---|
| 1. 클러스터 둘러보기 | 1.5분 | `kubectl get deploy,hpa,pdb,svc,pods`<br>`kubectl port-forward \`<br>`svc/cloud-copilot-demo 8080:80` | 파드 2개 이상 Running, 플랫폼 칩 aks |  |
| 2. HPA 자동 확장 | 2.5분 | `kubectl get hpa,pods -w`<br>`kubectl scale deploy/load-generator`<br>`--replicas=1` | REPLICAS가 2에서 늘어난다(최대 5) |  |
| 3. 롤링 업데이트 | 2.5분 | `kubectl set image \`<br>`deploy/cloud-copilot-demo \`<br>`app=$IMG:v2` | READY 유지, v2 전환, undo로 복귀 |  |
| 4. 워크로드 ID | 1분 | `kubectl get serviceaccount \`<br>`cloud-copilot-demo -o yaml`<br>`→ 파드의 AZURE_* 환경 변수 확인` | client-id 어노테이션과 AZURE_* 주입 |  |

- 옵션 · 보안 기본값 (1분): privileged 파드 적용 → Forbidden: violates PodSecurity "restricted"
- 참고: kubectl은 --namespace cloud-copilot-demo 기준(생략) · $IMG = $ACR_SERVER/cloud-copilot-demo

### 말할 내용

- 먼저 클러스터에 무엇이 올라와 있는지 한 화면으로 보고, 포트 포워딩으로 앱에 접속합니다. 서비스는 일부러 ClusterIP로 두어 인터넷에 노출하지 않았습니다.
- 부하 생성기를 켜면 HPA가 파드를 늘리고, 이미지를 v2로 바꾸면 새 파드가 준비된 뒤에만 이전 파드가 내려갑니다. 문제가 있으면 rollout undo 한 줄로 돌아옵니다.
- 마지막으로 서비스 어카운트의 어노테이션과 파드에 주입된 값을 보여 주며 비밀이 어디에도 없다는 점을 확인합니다.

### 시연 큐

- 1) kubectl get nodes → kubectl get deployment,hpa,pdb,service,pods --namespace cloud-copilot-demo → kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace cloud-copilot-demo → http://localhost:8080(사용자 demo).
- 2) 터미널 A: kubectl get hpa,pods --namespace cloud-copilot-demo --watch / 터미널 B: kubectl scale deployment/load-generator --replicas=1 --namespace cloud-copilot-demo → 확인 후 --replicas=0.
- 3) kubectl set image deployment/cloud-copilot-demo app="$ACR_SERVER/cloud-copilot-demo:v2" --namespace cloud-copilot-demo → kubectl rollout status → kubectl rollout undo deployment/cloud-copilot-demo.
- 4) kubectl get serviceaccount cloud-copilot-demo --namespace cloud-copilot-demo -o yaml, 그리고 파드에 주입된 AZURE_* 변수만 걸러서 보여 줍니다. 화면 공유 중에는 printenv를 그대로 실행하지 않습니다(DEMO_PASSWORD 노출).
- (옵션) README의 5단계: privileged 파드를 적용하면 Forbidden, violates PodSecurity "restricted:latest"가 출력됩니다.

[예상 시간] 단계 합계 약 7.5분 (옵션 약 1분 별도)

---

## 28. 데모 영상: AKS

*데모 영상 · 데모 6 / 6 · AKS · 녹화 영상*

### 화면 구성

- 영상 파일: `slides/videos/aks.mp4`
- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.
- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`

### 말할 내용

- 이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.

### 시연 큐

- slides/videos/aks.mp4 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다.

[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음

---

## 29. 핵심 설정: 워크로드 ID와 HPA

*핵심 코드 · 데모 6 / 6 · AKS · 핵심 코드*

### 화면 구성

**infra/aks/k8s/base (발췌)**

```
# serviceaccount.yaml
annotations:
  azure.workload.identity/client-id: "<managed-identity-client-id>"
# deployment.yaml (pod template)
labels:
  azure.workload.identity/use: "true"
# hpa.yaml
minReplicas: 2
maxReplicas: 5
averageUtilization: 50   # CPU 50%
```

**관찰**

```
kubectl get hpa,pods -n cloud-copilot-demo --watch
```

- 콜아웃:
  - **워크로드 ID** — 파드의 서비스 어카운트 토큰을 Entra ID 토큰으로 교환합니다. 키는 어디에도 없습니다.
  - **HPA · PDB** — CPU 50% 기준 2~5개로 늘고 줄며, PDB `minAvailable: 1`이 마지막 파드를 지킵니다.

### 말할 내용

- 워크로드 ID는 세 곳의 설정으로 완성됩니다. 서비스 어카운트의 client-id 어노테이션, 파드 템플릿의 use 레이블, 그리고 Azure 쪽 페더레이션 자격 증명입니다.
- 파드는 서비스 어카운트 토큰을 Entra ID 토큰으로 교환하므로 키나 비밀번호를 넣을 곳이 없습니다.
- HPA는 CPU 사용률 50%를 기준으로 파드를 2개에서 5개 사이로 조절하고, PDB가 마지막 파드를 지킵니다.

### 시연 큐

- 어노테이션의 client-id는 배포 스크립트가 만든 관리 ID 값으로 치환됩니다(저장소에는 자리 표시자).

[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)

---

## 30. 선택 가이드: Container Apps vs AKS

*비교표 · 정리 · 선택 가이드*

### 화면 구성

| 기준 | Container Apps | AKS |
|---|---|---|
| 운영 부담 | 낮음 · 노드 관리 없음 | 높음 · 클러스터·노드 풀 직접 운영 |
| 제어·확장성 | 앱 중심 설정, 규칙 기반 스케일 | 쿠버네티스 API 전체, 커스텀 확장 |
| 스케일 투 제로 | 기본 지원 (최소 복제본 0) | HPA 최소 1 · 0은 KEDA 등 추가 |
| HTTPS·인그레스 | 기본 제공 (자동 HTTPS 주소) | 인그레스·인증서를 직접 구성 |
| 네트워킹 | VNet 통합 등 관리형 옵션 | CNI·네트워크 정책·사설 클러스터 |
| 비용 모델(정성) | 쓴 만큼, 유휴 시 0까지 | 실행 중인 노드 기준, 상시 비용 |
| 적합 워크로드 | HTTP API·이벤트, 빠른 출시 | 복잡한 서비스, 플랫폼 팀 보유 |

- 같은 이미지가 둘 다에서 돕니다. 먼저 ACA로 시작하고, 제어가 더 필요해질 때 AKS로 가도 됩니다.

### 말할 내용

- 두 서비스는 경쟁이 아니라 운영 부담과 제어 수준을 맞바꾸는 선택입니다. Container Apps는 클러스터를 신경 쓰지 않고 HTTPS 서비스를 빨리 올리고, 쓰지 않을 때는 0까지 줄입니다.
- AKS는 쿠버네티스의 모든 기능을 쓰는 대신 클러스터와 노드를 운영해야 합니다. 네트워킹, 커스텀 컨트롤러, 플랫폼 팀 표준이 필요하면 AKS가 맞습니다.
- 오늘 본 것처럼 같은 이미지가 둘 다에서 돌기 때문에, 먼저 ACA로 시작하고 필요가 생길 때 옮겨도 됩니다.

### 시연 큐

- 비용은 숫자로 말하지 않고 모델(사용량 기반 대 노드 기반)만 비교합니다. 정확한 비용은 청중이 Azure 가격 계산기로 확인하도록 안내합니다.

[예상 시간] 약 1.5분

---

## 31. End-to-end: 아이디어에서 Foundry까지

*다이어그램 · 정리 · End-to-end*

### 화면 구성

- 단계: Idea → Issue (데모 1) → Copilot PR (데모 1) → Rulesets + CI (데모 2) → Actions (OIDC) (데모 3) → ACR (데모 3) → ACA 또는 AKS (데모 5·6) → Foundry (데모 4)
- 계획: 아이디어를 이슈로 정리합니다.
- 구현·검증: Copilot이 PR을 만들고 룰셋·CI가 검증합니다.
- 배포: OIDC로 로그인하고 이미지를 ACR에 올립니다.
- 실행·AI: 같은 이미지로 실행, Foundry는 키 없이 호출
- 키 없는 ID 경로: 로컬 · az login · Actions · OIDC · ACA · 관리 ID · AKS · 워크로드 ID

### 말할 내용

- 오늘 본 것을 한 줄로 이으면 이렇습니다. 아이디어가 이슈가 되고, Copilot이 PR을 만들고, 룰셋과 CI가 검증합니다.
- 통과한 코드는 Actions가 OIDC로 Azure에 로그인해 이미지를 ACR에 올리고, Container Apps나 AKS가 그 이미지를 실행하며, 앱은 Foundry의 gpt-6.1-sol을 키 없이 부릅니다.
- 아래 띠를 보세요. 사람의 로그인부터 CI, 컨테이너까지 모든 구간이 키 대신 아이덴티티로 연결되어 있습니다. 이것이 오늘 전하고 싶은 가장 큰 메시지입니다.

### 시연 큐

- 각 단계 아래의 '데모 N' 배지를 따라 어느 데모에서 본 것인지 짚습니다.

[예상 시간] 약 1분

---

## 32. 보안·비용·거버넌스 체크리스트

*체크리스트 · 정리 · 거버넌스*

### 화면 구성

1. **키 없는 인증** — API 키 대신 Entra ID를 씁니다. az login, 관리 ID, 워크로드 ID, OIDC.
2. **최소 권한** — 역할은 필요한 범위에만 주고 `id-token: write`는 배포 job에만 둡니다.
3. **모델 약관·구독** — gpt-6.1-sol은 쿼터면 충분합니다. Claude는 Enterprise·MCA-E 구독과 Anthropic 약관이 필요합니다.
4. **쿼터·리전** — 지원 리전과 모델 쿼터를 미리 확인하세요. 부족하면 용량이나 리전을 바꿉니다.
5. **공개 엔드포인트** — `/healthz`만 무인증, 나머지는 데모 비밀번호입니다. 실서비스는 조직 인증으로.
6. **정리와 비용** — 시연 직후 `cleanup.sh`로 정리합니다. AKS는 과금이 이어지고 Foundry는 purge가 필요합니다.

### 말할 내용

- 도입 전에 확인할 여섯 가지입니다. 첫째, 키가 없습니다. 둘째, 권한은 필요한 범위에만 줍니다. 셋째, 모델 약관과 구독입니다. gpt-6.1-sol은 모델 쿼터만 있으면 되고, Claude를 쓰려면 Enterprise 또는 MCA-E 구독과 Anthropic 약관 동의가 필요합니다.
- 넷째, 모델 쿼터와 지원 리전을 미리 확인하세요. 다섯째, 데모 앱은 공개 주소에 올라가므로 /healthz를 제외한 모든 경로에 데모 비밀번호를 걸었고, 실서비스에서는 조직의 인증으로 바꿔야 합니다.
- 마지막으로 정리입니다. 특히 AKS는 노드가 계속 비용을 만들기 때문에 시연이 끝나면 바로 cleanup.sh로 지우고, Foundry는 purge까지 해야 쿼터가 돌아옵니다.

### 시연 큐

- 시연 직후 scripts/cleanup.sh aks --yes처럼 대상을 지정해 실행합니다(all은 전부 정리). demo=ghcp-in-the-cloud 태그가 없는 리소스 그룹은 지우지 않는 안전장치가 있습니다.

[예상 시간] 약 1분

---

## 33. 서비스별 핵심 이점 한 장 요약

*요약 · 정리 · 핵심 이점*

### 화면 구성

| 서비스 | 핵심 이점 | 시연에서 본 증거 |
|---|---|---|
| GitHub Copilot | 이슈를 PR로, 규칙은 저장소 지침으로 | 에이전트 PR + Copilot 리뷰 |
| GitHub Repo | main 보호·코드 오너·보안 검사를 코드로 | 위험한 PR의 merge 차단 |
| GitHub Actions | 병렬 CI, 비밀 없는 OIDC 배포 | Secrets 목록이 비어 있음 |
| Microsoft Foundry | Azure 거버넌스 안의 gpt-6.1-sol, 키 없는 호출 | /api/info의 auth: entra-id |
| Container Apps | 서버리스: 스케일 투 제로와 카나리 | Replicas 0 → 1, 90/10 |
| AKS | 롤링 업데이트·HPA·워크로드 ID | READY 유지, 파드 증가 |

### 말할 내용

- 한 장으로 정리합니다. 각 서비스가 가져다 주는 이점과, 오늘 화면에서 직접 확인한 증거를 짝지었습니다.
- Copilot은 이슈를 PR로 바꾸고, 저장소는 규칙을 코드로 강제하고, Actions는 비밀 없이 배포하고, Foundry는 키 없이 모델을 쓰게 하고, Container Apps와 AKS는 같은 이미지를 서로 다른 운영 방식으로 실행합니다.

### 시연 큐

- 오른쪽 '시연에서 본 증거' 열을 읽으며 청중이 기억하도록 합니다.

[예상 시간] 약 1분

---

## 34. 시작하기 · Q&A

*마무리*

### 화면 구성

- 저장소: `github.com/junwoojeong100/ghcp-in-the-cloud`
- `README.md` — 개요 · 빠른 시작 · 독립 실행 매트릭스
- `demos/` — 데모 6개 각각의 시연 문서
- `slides/` — 이 발표 자료와 재생성 스크립트
- `DEMO_GUIDE_KO.md` — Full·Lite 시간표와 사전 준비
- 5분 만에 시작 (Azure 없이):

```
python -m unittest discover -s app/tests -v
LLM_BACKEND=mock python -m app.server
```

- 정리: scripts/cleanup.sh <aca|aks|foundry|oidc|all>

### 말할 내용

- 시작하는 가장 쉬운 방법은 저장소를 열어서 README의 빠른 시작을 따라 해 보는 것입니다. Azure 없이 mock 백엔드로 앱과 테스트를 먼저 돌려 보실 수 있습니다.
- demos 폴더에는 오늘 본 여섯 가지 데모의 시연 문서가 있고, slides 폴더에는 이 발표 자료와 재생성 스크립트가 있습니다. 필요하면 가져가서 고쳐 쓰세요.
- 질문 받겠습니다.

### 시연 큐

- Q&A 중 자주 나오는 질문은 부록의 트러블슈팅과 체크리스트로 답합니다.
- 발표 후 반드시 scripts/cleanup.sh로 Azure 리소스를 정리합니다.

[예상 시간] Q&A 포함 가변 (본문 약 1분)

---

## 35. 부록 A. 사전 준비 체크리스트

*부록 · 부록*

### 화면 구성

- **GitHub**
  - 연습용 저장소(포크 또는 템플릿)
  - 저장소 관리자 권한
  - Copilot 라이선스 (cloud agent)
  - `gh auth login`
  - `azure-demo` 환경 승인자 지정
- **Azure**
  - 구독 Owner (또는 Contributor + User Access Administrator)
  - gpt-6.1-sol 쿼터가 있는 구독·리전 (Claude는 Enterprise 또는 MCA-E)
  - 시연 30~60분 전 배포: foundry → aca → aks → oidc
- **로컬 도구**
  - bash 4+, Python 3.12
  - `az`, `gh`, `jq`
  - `kubectl` + `kubelogin`, `docker`(선택)
  - 터미널 글꼴 키우기, 알림 끄기
  - `DEMO_PASSWORD`는 export만 (출력 금지)

### 말할 내용

- 발표 전에 점검할 항목입니다. 질문이 나오면 이 페이지로 돌아와 답하세요.
- 배포가 오래 걸리는 Foundry, Container Apps, AKS는 시연 30~60분 전에 미리 만들어 둡니다. OIDC 설정은 배포 대상이 먼저 있어야 해서 마지막에 합니다.

### 시연 큐

- 상세 체크리스트와 데모별 사전 작업은 DEMO_GUIDE_KO.md의 '발표 전 체크리스트'에 있습니다.

[예상 시간] 부록 (발표 중에는 건너뜀)

---

## 36. 부록 B. 트러블슈팅 Top 5

*부록 · 부록*

### 화면 구성

| 문제 | 증상 | 해결 |
|---|---|---|
| RBAC 전파 지연 | 403 · AuthorizationFailed | 역할 부여 직후에는 수 분이 걸립니다. 잠시 뒤 다시 시도하세요. |
| 모델 쿼터·리전 | 배포가 쿼터·용량 오류 | `CAPACITY`를 줄이거나 `LOCATION`을 바꿉니다. (Claude는 Enterprise·MCA-E 필요) |
| ACR 이름 충돌 | 이름이 이미 사용 중 | 이름은 전역 고유입니다. `NAME_PREFIX`를 바꿔 다시 배포합니다. |
| kubelogin · Azure RBAC | kubectl 인증 오류 | `az login` → `az aks install-cli` → `kubelogin convert-kubeconfig --login azurecli` |
| OIDC subject 불일치 | AADSTS70021 | 저장소·환경 이름 확인, `setup-github-oidc.sh --apply --repo <owner>/<name>` |

### 말할 내용

- 리허설에서 가장 자주 만나는 문제 다섯 가지입니다. 대부분 몇 분 기다리거나 이름을 맞추면 해결됩니다.
- 역할을 방금 줬다면 전파에 몇 분이 걸립니다. 모델은 쿼터와 리전이 맞아야 배포되고, ACR 이름은 전역에서 유일해야 합니다.
- AKS는 Entra ID와 Azure RBAC로만 접근하므로 kubelogin이 필요하고, OIDC 로그인이 실패하면 subject의 저장소 이름과 환경 이름부터 확인합니다.

### 시연 큐

- 데모 문서마다 '문제 해결' 표가 있습니다. 증상별 상세 해결책은 해당 데모의 README를 보라고 안내합니다.

[예상 시간] 부록 (필요할 때만)

---

## 37. 부록 C. 참고 링크

*부록 · 부록*

### 화면 구성

| 주제 | 시작 페이지 |
|---|---|
| GitHub Copilot | [docs.github.com/copilot](https://docs.github.com/copilot) |
| GitHub Actions | [docs.github.com/actions](https://docs.github.com/actions) |
| GitHub 저장소 | [docs.github.com/repositories](https://docs.github.com/repositories) |
| 코드 보안 | [docs.github.com/code-security](https://docs.github.com/code-security) |
| Microsoft Foundry | [ai.azure.com](https://ai.azure.com) |
| Azure Container Apps | [learn.microsoft.com/azure/container-apps](https://learn.microsoft.com/azure/container-apps) |
| AKS | [learn.microsoft.com/azure/aks](https://learn.microsoft.com/azure/aks) |
| Workload Identity | [learn.microsoft.com/entra/workload-id](https://learn.microsoft.com/entra/workload-id) |
| 이 데모 키트 | [github.com/junwoojeong100/ghcp-in-the-cloud](https://github.com/junwoojeong100/ghcp-in-the-cloud) |

- 각 제품의 최신 문서는 위 시작 페이지에서 찾아 들어가세요. UI와 기능 이름은 바뀔 수 있습니다.

### 말할 내용

- 더 깊이 보고 싶은 분을 위한 시작 페이지입니다. 세부 문서 주소는 자주 바뀌므로 각 제품의 문서 첫 화면 링크만 적었습니다.

### 시연 큐

- 링크는 PowerPoint에서 클릭할 수 있습니다. Foundry 문서는 learn.microsoft.com에서 'Microsoft Foundry'를 검색하세요.

[예상 시간] 부록

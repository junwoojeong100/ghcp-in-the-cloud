# 데모 영상 녹화·45장 덱 게시 안내

## 목표와 현재 상태

현재 발표 자료는 데모 영상 32편이 들어 있는 [45장 녹화 덱](README.md)입니다. 이 안내는 데모를 다시 녹화하고, 저장소 PPTX의 영상을 교체한 뒤 GitHub Pages에 게시하는 절차입니다.

각 데모의 클릭 경로, 명령, 성공 기준은 링크된 데모 안내를 따릅니다. PPTX 원본은 저장소에서 관리하고, 전체 영문 영상(MP4)은 별도 릴리스 파일로 관리합니다.

## 이미 녹화한 영상과 다시 녹화할 때

국문 덱은 [`slides/GHCP_in_the_Cloud_Demo_KO.pptx`](GHCP_in_the_Cloud_Demo_KO.pptx), 영문 덱은 [`en/slides/GHCP_in_the_Cloud_Demo_EN.pptx`](../en/slides/GHCP_in_the_Cloud_Demo_EN.pptx)에 있습니다. 각각 45장·영상 32편이며, 저장소를 clone하면 함께 받습니다([발표 자료와 가이드](../README.md#발표-자료와-가이드)). 전체 영문 영상(`ghcp-in-the-cloud-demo-en.mp4`, 약 24분)은 릴리스 `recorded-demo-slides`에 있고 [영문 웹 페이지](https://junwoojeong100.github.io/ghcp-in-the-cloud/en/)에서 볼 수 있습니다.

녹화에 사용한 자동화 스크립트는 이 저장소에 없고, 이전 연습용 저장소도 삭제했습니다. 다시 녹화할 때는 [템플릿으로 새 연습용 저장소](../README.md#원본과-연습용-저장소)를 만들고, 각 데모 안내대로 실행하며 화면 녹화 도구로 촬영합니다.

## 녹화 전 준비

1. 저장소 루트의 `README.md`와 촬영할 데모의 안내를 따라 데모 환경을 구성하고, 전체 순서를 한 번 리허설합니다. GitHub·Azure 리소스 생성과 배포는 각 안내의 권한, 비용, 정리 절차를 확인한 뒤 진행합니다.
2. 발표용 브라우저 프로필과 터미널을 준비하고 알림을 끕니다. 화면 배율과 글꼴 크기를 읽기 쉽게 설정합니다.
3. 실사용 자격 증명과 개인 정보가 화면·음성·알림에 들어가지 않도록 확인합니다. `DEMO_PASSWORD`, 토큰, `Authorization` 헤더, 키, 비밀 값, 민감한 리소스 식별자를 표시하거나 말하지 않습니다. 기록된 파일을 발표에 쓰기 전에 전체 화면과 오디오를 다시 확인합니다.
4. 화면 녹화 도구에서 16:9 화면 전체와 마이크를 선택합니다. 영상 편집 시 데모 동작과 성공 기준이 끊기지 않도록 하고, 대기 구간은 짧게 편집하되 실제 결과를 대체하거나 꾸미지 않습니다.

## 데모별 녹화 구성

| 데모 | 실제 화면에 담을 흐름 | 성공 화면 | 안내 |
|---|---|---|---|
| GitHub Copilot | 설정 파일 → 이슈 할당 → 에이전트 세션·PR·CI → Copilot 리뷰와 사람 merge | 실제 PR의 변경과 통과한 체크, 리뷰, 사람이 승인한 결과 | [Demo 1](../demos/01-github-copilot/README.md). 에이전트 작업을 미리 시작해 대기 시간을 줄입니다. |
| GitHub Repo | Codespaces 테스트 → Rulesets·CODEOWNERS → 의도적으로 위험한 PR의 검사 결과 → Dependabot | 활성 룰셋과 보안 검사가 PR을 막는 화면 | [Demo 2](../demos/02-github-repo/README.md). 연습용 저장소를 사용하고 위험한 PR은 merge하지 않습니다. |
| GitHub Actions | PR의 병렬 CI → 저장된 Actions 비밀이 없는 설정 → 승인 게이트와 OIDC 배포 | 통과한 CI, 승인 단계, 실제 배포 실행의 성공 결과 | [Demo 3](../demos/03-github-actions/README.md). Azure 배포 장면은 실제 구독에서 수행하고 화면에 자격 증명을 노출하지 않습니다. |
| Microsoft Foundry | gpt-6.1-sol 배포 확인 → Entra ID로 실제 호출 → `/api/info` 확인 | `backend`, `auth`, `model`, `effort` 값과 앱의 응답 | [Demo 4](../demos/04-microsoft-foundry/README.md). API 키 대신 문서의 키 없는 인증 흐름을 사용합니다. |
| Azure Container Apps | 복제본 0개 확인 → 요청으로 기동 → 리비전 카나리와 롤백 → 부하 기반 스케일 아웃 | 실제 Container Apps 리비전·복제본 상태와 앱 응답 | [Demo 5](../demos/05-azure-container-apps/README.md). 전파 및 기동 대기 시간은 환경에 따라 달라집니다. |
| AKS | 파드와 HPA → 롤링 업데이트·롤백 → 워크로드 ID → Pod Security 거부 확인 | 준비된 파드, 실제 롤아웃 결과, 비밀 없는 ID 설정 | [Demo 6](../demos/06-aks/README.md). 실패 장면은 안내에 있는 안전한 거부 테스트만 사용합니다. |

## PPTX 수정과 게시

1. 저장소의 `slides/GHCP_in_the_Cloud_Demo_KO.pptx`를 PowerPoint에서 열어 필요한 내용과 영상을 수정합니다. 영문판은 `en/slides/GHCP_in_the_Cloud_Demo_EN.pptx`입니다([영문 안내](../en/slides/VIDEO_GUIDE.md)).
2. 45장 구성과 영상 32편의 재생, 화면 비율, 소리, 자막·민감 정보 노출을 확인합니다. 파일 이름과 위치를 유지하고, 국문 내용이 바뀌면 영문 덱도 함께 맞춥니다.
3. 수정한 PPTX를 PR에 포함합니다. 사람이 검토한 뒤 `main`에 merge하면 `Pages`가 저장소의 두 PPTX를 사이트 루트로 복사해 자동 게시합니다. PPTX를 릴리스에 따로 올릴 필요는 없습니다.
4. `Pages` 워크플로가 성공한 뒤 [웹 페이지](https://junwoojeong100.github.io/ghcp-in-the-cloud/)에서 PPTX를 열거나 다시 내려받아 변경과 영상 재생을 확인합니다.

전체 영문 MP4만 교체할 때는 릴리스 `recorded-demo-slides`의 해당 파일을 교체한 뒤 **Actions → Pages → Run workflow**로 다시 게시합니다. 릴리스에 남아 있는 PPTX 배포 사본은 자동 갱신되지 않으며, 최신 덱은 저장소와 GitHub Pages를 기준으로 사용합니다.

실제 영상을 녹화하지 않은 상태에서 mock 응답이나 정지 화면을 실제 GitHub·Azure 실행 결과처럼 제시하지 않습니다. 오프라인 mock 영상이 필요하면 영상 제목과 설명에 mock 모드임을 분명히 표시합니다.

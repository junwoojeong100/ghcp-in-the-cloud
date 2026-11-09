# 발표자 가이드 (약 15분)

## 목표

하나의 작은 채팅 앱으로 개발자 도구와 Azure 실행 환경이 어떻게 이어지는지 보여주되, 각 데모는 개별 실행이 가능하도록 구성했습니다. Copilot/저장소와 Actions는 Azure 없이, Foundry는 로컬 실행만으로, ACA와 AKS는 각자 따로 시연할 수 있습니다.

## 진행 순서

1. **GitHub 저장소와 Copilot (3분)** — Copilot demo task 이슈를 열고 Copilot에 입력합니다: “입력 유효성 검사 오류를 명확히 하고 단위 테스트를 추가해줘. README 명령도 확인해줘.” 생성된 PR에서 diff, 저장소 지침, 리뷰를 확인합니다.
2. **Actions (2분)** — PR의 `Demo CI` 체크를 열어 Python 테스트 후 Docker 빌드가 실행되는 것을 보여줍니다. 이 파이프라인은 Azure credential이나 배포를 필요로 하지 않습니다.
3. **Foundry (4분)** — 로컬 앱을 실행하고 한국어로 “Actions 테스트를 통과한 컨테이너를 AKS와 ACA에 배포할 때 각각 무엇을 관리해야 하는가?”라고 질문합니다. 요청은 Claude Sonnet 5.5(`claude-sonnet-5-5`)에 `max` effort로 전달됩니다. API 키와 데모 비밀번호는 서버 환경변수이며 브라우저에 모델 키를 노출하지 않습니다.
4. **ACA (3분)** — Bicep이 앱 환경을 생성하고 로그를 Log Analytics에 보내며, 0~2개 복제본으로 확장하는 설정을 보여줍니다. 기본 인증 뒤 HTTPS로 같은 질문을 시연합니다. 모델 호출과 Azure 리소스 사용량에 따라 비용이 발생합니다.
5. **AKS (3분)** — 동일 컨테이너의 Deployment/ClusterIP Service, readiness/liveness probe, 리소스 요청/제한, Kubernetes Secret 참조를 확인합니다. 로컬 port-forward와 기본 인증으로 앱에 접속합니다. ACA와 비교해 클러스터의 운영 책임이 더 크다는 점을 설명합니다.

## 단독 시연 모드

- **Copilot/저장소만:** 이슈 템플릿과 Copilot으로 PR을 만들고 리뷰합니다. Azure 계정 불필요.
- **Actions만:** 저장소에서 PR을 생성하고 CI 로그를 엽니다. Azure 계정/credential 불필요.
- **Foundry만:** 저장소 루트에서 `python -m app.server` 실행. Foundry 리소스와 키만 필요.
- **ACA만:** 이미지를 게시하고 `infra/aca/main.bicep`을 배포. AKS는 필요하지 않습니다.
- **AKS만:** 기존 AKS에 `infra/aks/`를 적용. ACA는 필요하지 않습니다.

## 운영 메모

- Claude 모델 접근 여부, 배포 옵션, 리전, 약관/비용을 발표 전에 확인합니다. 모델 배포를 위해 Anthropic 상업 약관 동의가 요구될 수 있습니다.
- 공개 데모에서는 테스트/CI를 먼저 보여주고 Foundry/배포 데모는 승인된 계정에서만 진행합니다. UI 비밀번호로 보호되지 않은 채팅 앱을 인터넷에 노출하지 말고, 실제 API 키/비밀번호를 슬라이드, 저장소, 명령 기록, 화면 공유에 노출하지 않습니다.
- 라이브 채팅이 불가능하면 CI와 정적 매니페스트로 GitHub/배포 경로를 설명합니다. 저장소에 키가 필요 없는 데모를 유지합니다.
- 종료할 때 전용 ACA 리소스 그룹 또는 앱 리소스만 정리하고 AKS 애플리케이션/Secret을 삭제합니다. 공유 리소스 그룹 전체를 삭제하지 않습니다. 로그 보존과 데이터 취급 정책을 확인합니다.

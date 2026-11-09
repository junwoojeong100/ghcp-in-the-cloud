# GitHub × Microsoft Azure: 독립형 클라우드 AI 데모

## 1. 한 저장소, 다섯 가지 데모
- GitHub Copilot으로 이슈를 구현하고 PR에서 검토
- GitHub Actions로 테스트와 컨테이너 빌드를 자동화
- Microsoft Foundry에서 Claude Sonnet 5.5 호출
- 같은 컨테이너를 Azure Container Apps 또는 AKS에서 실행
- Azure 실습은 선택 사항이며 GitHub 데모는 독립 실행 가능

## 2. Copilot과 저장소: 아이디어에서 PR까지
- 구조화된 이슈 템플릿에 변경 및 완료 조건 작성
- 저장소 Copilot 지침으로 테스트/보안 규칙 제공
- Copilot이 구현하고 PR에서 사람이 diff, 리뷰, 체크를 확인
- 효과: 빠른 구현 + 추적 가능한 사람 중심 검토

## 3. Actions: 반복 가능한 검증
- PR/푸시마다 Python 3.12 테스트 실행
- 같은 소스로 컨테이너 이미지 빌드
- Azure credential 없이 CI 시연 가능
- 성공 체크와 실패 로그가 팀의 공유 증거가 됨

## 4. Foundry: 관리형 Claude 추론
- 모델: Claude Sonnet 5.5 (`claude-sonnet-5-5`)
- 추론 노력: `max`; 응답 토큰 상한: 4,096
- Anthropic SDK Foundry 클라이언트, 키는 서버 환경변수
- UI는 기본 인증으로 보호, `/healthz`는 probe 전용
- 한국어 UI → `/api/chat` → Foundry → 답변

## 5. ACA: 간결한 앱 운영
- 인증된 HTTPS ingress와 Log Analytics
- 최소 0, 최대 2 복제본으로 scale-to-zero 시연
- 기존 이미지와 Foundry 리소스만 연결해 독립 배포
- 앱 환경은 Azure가 관리, 모델 사용량/로그 비용 주의

## 6. AKS: Kubernetes 제어
- Deployment와 ClusterIP Service를 별도로 적용
- readiness/liveness probe 및 CPU/메모리 제한
- API 키/비밀번호는 Kubernetes Secret, port-forward로 접속
- 세밀한 제어와 생태계의 대가로 클러스터 운영 필요

## 7. 같은 앱, 다른 선택
- Actions: 빌드가 재현되는지 검증
- ACA: 운영 부담을 줄이고 짧거나 간헐적인 앱 실행
- AKS: Kubernetes 기능과 클러스터 제어가 필요할 때
- 모든 Azure 배포에서 이미지, 비밀, 비용을 관리

## 8. 데모 요약과 다음 단계
- Copilot은 작업 속도를 높이고, PR 검토는 품질/책임성을 유지
- Actions는 테스트와 빌드를 일관되게 수행
- Foundry는 관리형 모델 접근, ACA/AKS는 선택 가능한 실행 경로
- 데모 후 리소스/Secret을 정리하고 약관·비용·로그 정책 확인
- 참고: README.md 및 DEMO_GUIDE_KO.md

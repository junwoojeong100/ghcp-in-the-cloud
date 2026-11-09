# Demo 3 — GitHub Actions: 비밀 없는 CI/CD(OIDC)와 재사용 가능한 파이프라인

PR마다 코드, 컨테이너, IaC, 워크플로를 병렬로 검증하고, 배포는 저장된 비밀 없이 OIDC로 Azure에 로그인해 진행합니다. 같은 검증 스크립트를 CI, Copilot 에이전트 환경, 로컬에서 그대로 다시 씁니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | ① PR에서 `CI`의 4개 job이 병렬로 도는 모습 ② 비밀 0개로 Azure 신뢰를 구성하는 방법 ③ 환경 승인 → OIDC 로그인 → 이미지 빌드 → 새 리비전 배포까지의 흐름을 보여 줍니다. |
| 시간 | 약 7분. 배포 워크플로는 빌드 시간이 있으니 시연 전에 한 번 돌려 두고, 라이브로는 새 실행을 시작해 승인 단계까지 보여 주세요. |
| 난이도 | 보통 |
| 독립 실행 | 1단계는 GitHub 저장소만 있으면 됩니다(Azure 불필요). 2~3단계는 Azure 구독과 배포 대상(Container Apps 또는 AKS)이 필요합니다. 대상은 `scripts/deploy-aca.sh`로 만들면 되고, Demo 5를 따라 할 필요는 없습니다. |

```text
PR ─▶ CI ─┬─ Unit tests
          ├─ Container build and smoke test
          ├─ IaC validation
          └─ Workflow and script lint

수동 실행 ─▶ azure-demo 환경(승인) ─▶ GitHub OIDC 토큰 ─▶ Azure 로그인
          ─▶ ACR 빌드·푸시 ─▶ 빌드 출처 증명(attestation) ─▶ Container Apps 새 리비전
```

## 왜 이 서비스인가 (이점)

- **빠른 피드백**: 서로 독립적인 4개 job이 동시에 실행되고, `pip` 의존성은 캐시합니다. 같은 PR에 새로 push하면 진행 중이던 이전 실행은 자동으로 취소됩니다(`concurrency`).
- **장기 비밀이 없는 배포**: GitHub가 job마다 발급하는 짧은 수명의 OIDC 토큰을 Azure(Microsoft Entra ID)가 신뢰합니다. 저장소에는 서비스 주체 비밀번호도, 키도 없습니다. 저장되는 값은 클라이언트 ID, 테넌트 ID 같은 식별자뿐이고 모두 비밀이 아닌 변수입니다.
- **좁은 신뢰 범위**: 페더레이션 자격 증명의 subject가 `repo:<owner>/<repo>:environment:azure-demo`라서, 이 저장소의 `azure-demo` 환경을 쓰는 job만 로그인할 수 있습니다. Azure 쪽 역할도 대상 리소스 그룹, 레지스트리, 네임스페이스로 한정합니다.
- **최소 권한 `permissions`**: 워크플로 기본값은 `contents: read`입니다. 배포 job만 `id-token: write`와 `attestations: write`를 추가로 받습니다.
- **사람 승인 게이트**: `azure-demo` 환경에 승인자를 지정하면, 승인하기 전에는 Azure에 로그인하는 단계에 도달하지 않습니다.
- **공급망 보안**: 모든 서드파티 액션을 전체 커밋 SHA로 고정하고(Dependabot이 갱신 PR을 올립니다), 공개 저장소에서는 배포한 이미지의 빌드 출처 증명(attestation)을 남깁니다.
- **한 파이프라인에서 코드, IaC, 컨테이너 검증**: 단위 테스트, 읽기 전용 컨테이너 스모크 테스트, Bicep 빌드, Kubernetes 매니페스트 검증(kubeconform), actionlint, shellcheck, hadolint가 같은 `CI`에서 돕니다.
- **재사용**: 검증 단계가 `scripts/*.sh`로 되어 있어 로컬에서도 같은 명령으로 재현됩니다. `scripts/install-dev-tools.sh`는 CI와 `copilot-setup-steps.yml`이 함께 씁니다.

## 사전 준비

**1단계 (GitHub만)**

- 이 저장소(또는 포크)에서 Actions를 쓸 수 있어야 합니다. 시연용 변경을 올릴 브랜치를 하나 준비하세요.

**2~3단계 (Azure 필요)**

1. **도구**: `az`(로그인 완료: `az login`), `gh`(저장소 관리자 권한으로 로그인: `gh auth login`), `bash` 4 이상. macOS 기본 bash는 3.2이므로 `brew install bash`로 설치하세요.
2. **Azure 권한**: 관리 ID와 역할 할당을 만들 수 있는 계정(구독 Owner, 또는 Contributor와 User Access Administrator)이 필요합니다.
3. **배포 대상을 먼저 만들기**: `setup-github-oidc.sh`는 이미 있는 리소스에 역할을 부여하므로 대상이 먼저 있어야 합니다.

   ```bash
   scripts/deploy-aca.sh --yes     # mock 백엔드라서 Foundry 없이 됩니다. 몇 분 걸립니다.
   ```

   AKS 배포 워크플로(`deploy-aks.yml`)를 쓰려면 `scripts/deploy-aks.sh`로 AKS도 만들어 두세요. 두 워크플로는 서로 독립적입니다.
4. **`azure-demo` 환경 (선택, 승인 게이트용)**: 승인 단계를 보여 주려면 승인자를 지정합니다. 환경은 없으면 `setup-github-oidc.sh`도 만들지만, 승인자는 이 명령으로 지정하세요.

   ```bash
   scripts/apply-repo-settings.sh --apply --only environment --reviewer <본인 GitHub 사용자 이름>
   ```

   승인자가 본인이면 본인이 시작한 실행도 승인할 수 있습니다. 환경 설정에서 "Prevent self-review"를 켜면 다른 사람의 승인이 필요합니다.

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 아래 클릭 경로는 작성 시점 기준입니다. 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요. 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

### 1. PR에서 CI 병렬 실행 (약 2분) — Azure 불필요

1. 브랜치에서 문서 한 줄 같은 작은 변경을 push하고 PR을 엽니다.
2. PR 화면의 **Checks** 탭이나 **Actions → CI**에서 job 4개가 동시에 도는 것을 보여 줍니다. 터미널이라면 다음과 같습니다.

   ```bash
   gh pr checks --watch
   ```

3. `Container build and smoke test`의 `Smoke test` 단계 로그를 엽니다. 읽기 전용 파일 시스템과 `--cap-drop ALL`로 띄운 컨테이너에 14개 확인이 차례로 통과합니다.
4. (선택) `app/tests`의 단언을 하나 일부러 틀리게 고쳐 push하면 `Unit tests`만 빨갛게 되고 나머지는 그대로 진행됩니다. 룰셋이 켜져 있으면 merge 버튼도 막힙니다.

성공 기준: `Unit tests`, `Container build and smoke test`, `IaC validation`, `Workflow and script lint`가 모두 초록색이고, `Smoke test` 로그 마지막에 `모든 확인(14개)을 통과했습니다.`가 보입니다.

같은 검증을 로컬에서 재현하는 명령입니다.

| job | 로컬 명령 |
|---|---|
| `Unit tests` | `python -m unittest discover -s app/tests -v` |
| `Container build and smoke test` | `docker build --file app/Dockerfile --tag cloud-copilot-demo .` 후 컨테이너를 띄우고 `scripts/smoke-test.sh` (README의 "빠른 시작" 참고) |
| `IaC validation` | `az bicep build --file infra/aca/main.bicep --stdout > /dev/null` 와 `scripts/render-aks-manifests.sh \| kubeconform -strict -summary` (kubeconform은 `scripts/install-dev-tools.sh kubeconform`으로 설치) |
| `Workflow and script lint` | `actionlint`, `shellcheck scripts/*.sh scripts/lib/*.sh`, `hadolint app/Dockerfile` |

### 2. 비밀 없이 Azure 신뢰 구성 (약 2분)

```bash
scripts/setup-github-oidc.sh            # 미리보기: 실행할 명령만 출력, 아무것도 바꾸지 않음
scripts/setup-github-oidc.sh --apply    # 실제 적용 (여러 번 실행해도 같은 결과)
```

이 스크립트가 하는 일은 세 가지입니다. 이미 만들어 둔 배포 대상(Container Apps, AKS)에 대해서만 처리합니다.

1. 사용자 할당 관리 ID(`ccd-github-actions`)와 페더레이션 자격 증명을 만듭니다. subject는 `repo:<owner>/<repo>:environment:azure-demo`입니다.
2. 대상 리소스에만 역할을 줍니다. Container Apps는 리소스 그룹 Contributor와 레지스트리 AcrPush, AKS는 클러스터 사용자 역할과 네임스페이스 범위 RBAC Writer, 그리고 AcrPush입니다.
3. `azure-demo` 환경에 `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`와 대상별 `ACA_*`, `AKS_*` 변수를 저장합니다.

그다음 화면으로 확인합니다.

- GitHub: **Settings → Secrets and variables → Actions**에 저장된 **Secrets가 하나도 없는지** 보여 줍니다. **Settings → Environments → azure-demo**에는 식별자 변수만 있습니다.
- Azure 포털: 관리 ID `ccd-github-actions`의 **Federated credentials**에서 issuer와 subject를 보여 줍니다.

성공 기준: `--apply`가 끝까지 성공하고, `azure-demo` 환경에 식별자 변수가 보이며(Container Apps만 만들었다면 `AZURE_*` 3개와 `ACA_*` 3개), Secrets 목록은 비어 있습니다.

### 3. 배포 워크플로 실행: 승인 → OIDC 로그인 → 새 리비전 (약 3분)

```bash
gh workflow run deploy-aca.yml          # 또는 Actions → "Deploy to Azure Container Apps" → Run workflow
gh run watch                            # 실행을 고르면 진행 상황을 따라갑니다
```

1. 환경에 승인자를 지정했다면 실행이 **Waiting** 상태로 멈춥니다. **Review deployments**에서 `azure-demo`를 승인하세요. 이 단계가 지나기 전에는 Azure에 아무것도 닿지 않습니다.
2. 단계를 차례로 보여 줍니다. `Log in to Azure with OIDC`(비밀 없이 로그인), `Build and push the image`, `Attest the build provenance`, `Roll out a new revision`, `Wait until the app answers`.
3. 실행 요약(**Summary**)에서 앱 주소, 새 리비전 이름, 이미지, 커밋, 트래픽 분포를 봅니다.
4. 앱 주소를 열면 화면 머리글의 **앱 버전**이 커밋 앞 7자리로 바뀌어 있습니다. 어느 커밋이 응답하는지 바로 알 수 있습니다.
5. 공급망 확인: 이미지가 이 저장소의 워크플로에서 빌드됐다는 서명된 증명을 검증합니다(공개 저장소).

   ```bash
   az acr login --name <ACR 이름>
   gh attestation verify oci://<ACR 이름>.azurecr.io/cloud-copilot-demo:<커밋 앞 7자리> --owner <owner>
   ```

   `<ACR 이름>`은 `azure-demo` 환경 변수 `ACA_ACR_NAME`과 같고, `az acr list --resource-group rg-cloud-copilot-aca --query "[0].name" --output tsv`로도 알 수 있습니다.

성공 기준: 실행이 초록색으로 끝나고, 앱의 `/api/info`가 새 커밋의 버전을 돌려주며, `gh attestation verify`가 검증 성공을 알려 줍니다.

AKS도 같은 방식입니다. `gh workflow run deploy-aks.yml`을 실행하면 이미지를 빌드해 올린 뒤 `kubectl set image`와 `kubectl rollout status`로 롤링 업데이트합니다.

## 말하기 포인트

- **"GitHub에도 Azure에도 비밀번호가 없습니다."** job이 시작되면 GitHub가 OIDC 토큰을 발급하고, `azure/login`이 그 토큰을 Entra ID에 제시합니다. 발급자와 subject가 페더레이션 자격 증명과 맞으면 Azure 토큰을 받습니다. 토큰은 그 job 동안만 쓸 수 있습니다.
- **신뢰는 환경 단위로 좁혔습니다.** subject에 `environment:azure-demo`가 들어 있어서 다른 워크플로나 환경의 job은 로그인할 수 없습니다. 여기에 환경 승인과 브랜치 제한을 더할 수 있습니다.
- **권한은 job마다 필요한 만큼만** 줍니다. 기본은 읽기 전용이고, 배포 job만 토큰 발급과 증명 저장 권한을 받습니다.
- **배포는 취소하지 않습니다.** CI는 새 push가 오면 이전 실행을 취소하지만, 배포 워크플로는 `cancel-in-progress: false`라서 진행 중인 배포를 중간에 끊지 않고 줄을 세웁니다.
- **액션 버전은 SHA로 고정**했습니다. 태그는 옮겨질 수 있지만 커밋 SHA는 바뀌지 않습니다. 버전 갱신은 Dependabot PR로 사람이 검토합니다.
- **빌드 출처 증명**으로 "이 이미지는 이 저장소의 이 커밋, 이 워크플로가 만들었다"를 검증할 수 있습니다.
- 이 워크플로는 **트래픽을 건드리지 않습니다.** 카나리 분할이 설정된 앱에서는 새 리비전이 0%로 만들어지고, 승격은 Demo 5의 `scripts/aca-canary.sh`로 합니다.

## 정리(Cleanup)

```bash
scripts/cleanup.sh oidc        # 관리 ID, 역할 할당, azure-demo 환경 변수를 지웁니다 (확인 질문 있음)
```

- 배포한 앱과 레지스트리는 Demo 5와 6의 정리 명령(`scripts/cleanup.sh aca`, `scripts/cleanup.sh aks`)으로 지웁니다.
- 이미지 attestation은 GitHub에 남지만 지울 필요는 없습니다.
- `azure-demo` 환경 자체와 승인자 설정은 지우지 않습니다. 다음 시연에서 그대로 씁니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| `Log in to Azure with OIDC`에서 `AADSTS70021`(일치하는 페더레이션 ID 레코드 없음) | subject가 맞지 않습니다. 저장소 이름(`<owner>/<name>`)과 환경 이름 `azure-demo`가 자격 증명과 같은지 확인하세요. 포크라면 `scripts/setup-github-oidc.sh --apply --repo <owner>/<name>`을 다시 실행합니다. |
| `azure-demo 환경에 변수가 없습니다` 오류 | `scripts/setup-github-oidc.sh --apply`를 아직 실행하지 않았거나, 변수가 다른 저장소·환경에 저장됐습니다. Settings → Environments → azure-demo의 변수를 확인하세요. |
| 실행이 **Waiting**에서 멈춤 | 환경 승인자의 승인을 기다리는 중입니다. **Review deployments**에서 승인하세요. 승인 알림을 받지 못하면 환경의 승인자 설정을 확인합니다. |
| `AuthorizationFailed` | 역할 할당이 전파되는 데 몇 분 걸릴 수 있습니다. 잠시 뒤 **Re-run failed jobs**로 다시 실행하세요. 계속되면 `setup-github-oidc.sh`가 올바른 리소스 그룹을 대상으로 했는지 확인합니다. |
| 배포는 성공했는데 화면 버전이 그대로임 | 카나리 분할이 설정된 앱에서는 새 리비전이 0%로 만들어집니다. `scripts/aca-canary.sh status`로 확인하고 `scripts/aca-canary.sh promote`로 승격하거나, `scripts/deploy-aca.sh`를 다시 실행해 분할을 초기화하세요. |
| `Wait until the app answers`가 실패 | 앱이 스케일 투 제로 상태에서 시작하는 중일 수 있습니다. 이 단계는 12번 재시도합니다. 그래도 실패하면 `az containerapp logs show --name cloud-copilot-demo --resource-group rg-cloud-copilot-aca`로 로그를 확인하세요. |
| `Attest the build provenance` 단계가 건너뛰어짐 | 비공개 저장소에서는 attestation을 만들지 않도록 해 두었습니다(GitHub Enterprise Cloud가 필요합니다). 공개 저장소에서만 실행됩니다. |
| `gh attestation verify`가 실패 | `az acr login`을 먼저 실행했는지, 이미지 태그가 배포한 커밋 앞 7자리와 같은지, `--owner`가 저장소 소유자인지 확인하세요. |
| 필수 체크가 "Expected — Waiting for status to be reported"로 남음 | 워크플로가 아직 시작되지 않았거나(Copilot 에이전트 PR은 사람이 **Approve and run workflows**를 눌러야 합니다), job 이름이 룰셋의 필수 체크 이름과 다릅니다. |

## 다른 데모와 함께 쓰면

이 데모는 1단계만으로도 완결됩니다. 함께 쓰면 이야기가 이어집니다.

- **Demo 1 (GitHub Copilot)**: 에이전트가 만든 PR도 같은 `CI`를 통과해야 합니다. 사람이 **Approve and run workflows**를 누르는 순간이 이 데모의 "사람 승인" 메시지와 이어집니다.
- **Demo 2 (GitHub Repo)**: `CI`의 job 이름 세 개가 `main-protection` 룰셋의 필수 상태 체크입니다. CodeQL과 dependency review 워크플로가 같은 PR에서 함께 돕니다.
- **Demo 4 (Foundry)**: 배포 대상 앱이 Foundry 백엔드로 설정되어 있어도 워크플로는 이미지와 `APP_VERSION`만 바꾸므로 설정이 유지됩니다.
- **Demo 5와 6 (Container Apps, AKS)**: 배포 대상입니다. 이 데모의 3단계가 Demo 5의 카나리와 Demo 6의 롤링 업데이트로 이어집니다.

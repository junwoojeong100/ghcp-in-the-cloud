# Demo 5 — Azure Container Apps: 서버리스 컨테이너, 스케일 투 제로, 리비전 카나리

클러스터를 운영하지 않고 컨테이너 앱을 HTTPS로 서비스합니다. 요청이 없으면 복제본이 0개로 줄고, 새 버전은 리비전으로 올려 트래픽을 나눠 보내다가 한 번에 승격하거나 즉시 되돌립니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | 배포 → 스케일 투 제로와 첫 요청의 콜드 스타트 → 리비전 카나리(0% → 10% → 100%, 롤백) → 부하에 따른 스케일 아웃을 순서대로 보여 줍니다. |
| 시간 | 약 7분. 배포와 유휴 대기는 시연 전에 끝내 두세요. |
| 난이도 | 보통 |
| 독립 실행 | 예. Azure 구독만 있으면 됩니다. 기본은 `mock` 백엔드라서 Foundry 없이 동작합니다. Foundry 연결은 선택입니다(Demo 4). |

```text
                 ┌─ 운영 주소 ─▶ 리비전 v1 (90%) ─┐
사용자 ─ HTTPS ─▶ Ingress ──────────────────────┤ 복제본 0~5개
                 └─ 레이블 주소 ▶ 리비전 v2 (10%) ─┘ 동시 요청 5건당 1개 (HTTP 스케일 규칙)
```

## 왜 이 서비스인가 (이점)

- **운영할 클러스터가 없음**: 노드, 업그레이드, 인그레스 컨트롤러를 관리하지 않습니다. 컨테이너 이미지와 설정만 올리면 HTTPS 주소가 생깁니다.
- **스케일 투 제로(scale-to-zero)**: 최소 복제본이 0이라 요청이 없으면 복제본이 사라져 컴퓨팅 비용이 멈춥니다. 다음 요청이 오면 복제본이 다시 시작됩니다. 사내 도구나 데모처럼 사용 패턴이 들쭉날쭉한 앱에 맞습니다.
- **리비전 기반 트래픽 분할**: 새 버전을 새 리비전으로 올리고 레이블 주소로 먼저 확인한 뒤 트래픽 일부만 보내는 카나리와 블루-그린, 승격, 즉시 롤백을 설정 변경만으로 합니다.
- **요청 수 기반 자동 확장**: HTTP 스케일 규칙으로 복제본당 동시 요청 5건을 넘으면 복제본을 늘립니다(최대 5개).
- **키 없는 Foundry 호출**: 앱에 연결된 사용자 할당 관리 ID가 Foundry의 `Cognitive Services User` 역할을 받아 비밀 없이 모델을 호출합니다.
- **기본 제공 로그**: 콘솔 로그가 Log Analytics로 모입니다.

## 사전 준비

1. **도구**: `az`(로그인: `az login`), `curl`, `python3`, `bash` 4 이상(macOS는 `brew install bash`). `containerapp` 확장과 필요한 리소스 공급자 등록은 스크립트가 처리합니다.
2. **Azure 권한**: 리소스 그룹과 역할 할당을 만들 수 있는 계정(구독 Owner, 또는 Contributor와 User Access Administrator)이 필요합니다. 인프라가 앱의 관리 ID에 레지스트리 읽기(`AcrPull`) 역할을 부여하기 때문입니다.
3. **배포** (몇 분 걸리므로 시연 전에):

   ```bash
   scripts/deploy-aca.sh                # 확인 질문에 y. 질문 없이 진행하려면 --yes
   ```

   레지스트리, 관리 ID, Log Analytics, Container Apps 환경을 만들고 이미지를 빌드한 뒤 앱을 배포합니다. 끝에 **URL, 사용자, 비밀번호**가 출력되니 적어 두세요. 비밀번호를 직접 정하려면 `DEMO_PASSWORD`를 지정합니다. 기본 리소스 그룹은 `rg-cloud-copilot-aca`, 리전은 `koreacentral`입니다.

   Foundry의 모델을 쓰려면 먼저 Demo 4를 진행한 뒤 같은 셸에서 `source .azure/foundry.env`를 실행하고 이 스크립트를 실행하세요.
4. **시연 셸 준비**:

   ```bash
   export DEMO_PASSWORD='<deploy-aca.sh가 출력한 비밀번호>'
   APP_URL="https://$(az containerapp show --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
     --query properties.configuration.ingress.fqdn --output tsv)"
   echo "$APP_URL"
   ```

   기본값(`RESOURCE_GROUP`, `APP_NAME`)을 바꿔 배포했다면 `scripts/aca-canary.sh`에도 같은 값을 환경 변수로 넘기세요.
5. **스케일 투 제로를 보이려면** 배포가 끝난 뒤 시연 시작까지 앱에 요청을 보내지 마세요(브라우저 탭과 스모크 테스트도 요청입니다). 요청이 없는 상태가 몇 분 이어지면 복제본이 0개가 됩니다.

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 아래 포털 클릭 경로는 작성 시점 기준입니다. 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요. 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

### 1. 스케일 투 제로와 콜드 스타트 (약 1.5분)

배포 뒤 아무 요청도 보내지 않은 상태에서 시작합니다(사전 준비 5).

```bash
az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
  --query "[?properties.active].{Name:name, Traffic:properties.trafficWeight, Replicas:properties.replicas}" --output table
```

1. 위 명령에서 `Replicas`가 `0`입니다. 실행 중인 복제본이 없으니 컴퓨팅 비용도 없습니다. `Replicas` 열이 비어 보이면 `az containerapp replica list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo --output table`로 복제본 목록을 확인하세요(복제본이 없으면 목록이 비어 있습니다).
2. 첫 요청을 보냅니다. 복제본이 시작될 때까지 기다리느라 응답이 느립니다.

   ```bash
   curl -s -o /dev/null -w '%{http_code} %{time_total}초\n' "$APP_URL/healthz"   # 첫 요청: 느림
   curl -s -o /dev/null -w '%{http_code} %{time_total}초\n' "$APP_URL/healthz"   # 두 번째: 빠름
   ```

3. 위의 `az containerapp revision list` 명령을 다시 실행하면 `Replicas`가 `1`입니다.

성공 기준: 같은 요청이 처음에는 눈에 띄게 느리고 두 번째는 빠르며, `Replicas`가 0에서 1로 바뀝니다. 지연 시간은 환경에 따라 다르니 숫자를 약속하지 마세요. 복제본이 0이 될 때까지 기다릴 시간이 없었다면 이 단계를 말로만 설명하고 넘어가도 됩니다.

### 2. 배포 결과 확인: 웹 UI와 스모크 테스트 (약 1분)

1. 브라우저에서 `$APP_URL`을 열고 사용자 `demo`와 비밀번호로 로그인합니다. 정보 칩에서 **플랫폼 `aca`**, 인스턴스(복제본 이름), 리비전, 앱 버전, 백엔드를 확인합니다.
2. CI에서 쓰는 스모크 테스트를 실제 배포에 그대로 실행합니다.

   ```bash
   scripts/smoke-test.sh "$APP_URL" --wait 60 --expect-backend mock
   ```

성공 기준: HTTPS 주소로 로그인되고, 모든 확인이 통과하며(`모든 확인(14개)을 통과했습니다.`), 플랫폼 칩이 `aca`입니다. Foundry 백엔드로 배포했다면 `--expect-backend foundry`를 쓰세요.

### 3. 리비전 카나리: 0% → 10% → 100%, 롤백 (약 3분)

```bash
scripts/aca-canary.sh status           # 현재 트래픽 분포, 리비전, 레이블 주소
scripts/aca-canary.sh deploy v2        # 새 리비전 v2를 만들고 빈 레이블에 연결. 트래픽은 0%
scripts/aca-canary.sh canary 10        # v2에 10%, 이전 리비전에 90%
scripts/aca-canary.sh probe 30         # 운영 주소로 30번 호출해 버전별 응답 비율 집계
scripts/aca-canary.sh promote          # v2로 100% 전환
scripts/aca-canary.sh rollback         # 이전 리비전으로 100% 되돌림 (문제가 생겼다는 가정)
```

1. `deploy v2`는 이미지를 다시 빌드하지 않고 `APP_VERSION=v2` 환경 변수만 바꿔 새 리비전을 만듭니다. 처음 실행하면 현재 리비전을 100%로 고정하고 `blue` 레이블을 붙인 뒤, 새 리비전을 `green` 레이블 주소(`https://<앱>---green.<환경 도메인>`)에 연결합니다. 이 주소로는 운영 트래픽을 받기 전에 v2를 미리 확인할 수 있습니다.
2. `canary 10` 뒤에 브라우저에서 **트래픽 분포 보기 (20회 호출)** 버튼을 누르면 리비전별, 앱 버전별 응답 횟수가 막대로 나옵니다. 같은 내용을 `probe`가 터미널에 표로 보여 줍니다. 10%는 확률적인 분할이라 호출 횟수가 적으면 비율이 조금 어긋납니다.
3. `promote`로 100% 전환하고 `probe`로 모두 v2가 응답하는지 확인합니다.
4. `rollback`으로 이전 리비전이 다시 100%를 받게 되돌립니다. 새 리비전은 그대로 남아 있어서 언제든 다시 승격할 수 있습니다.
5. 포털에서 보려면 컨테이너 앱의 **Revisions and replicas**(리비전과 복제본)를 엽니다.

성공 기준: `deploy` 직후 `status`에서 v2가 0%이고 레이블 주소는 v2의 버전을 돌려줍니다. `canary 10` 뒤 `probe`에 v1과 v2가 섞여 나타나고, `promote` 뒤에는 v2만, `rollback` 뒤에는 이전 리비전만 나옵니다.

### 4. 부하로 스케일 아웃 (약 1.5분)

터미널 두 개를 씁니다. 왼쪽에서 복제본 수를 지켜보고 오른쪽에서 부하를 겁니다.

```bash
# 터미널 A: 5초마다 리비전별 복제본 수 출력 (중지: Ctrl+C)
while true; do
  az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
    --query "[?properties.active].{Name:name, Traffic:properties.trafficWeight, Replicas:properties.replicas}" --output table
  sleep 5
done
```

```bash
# 터미널 B: 동시 요청 20개로 2분 동안 부하
scripts/load-test.sh --url "$APP_URL" --duration 120 --concurrency 20
```

mock 백엔드는 응답마다 약 1초(`MOCK_LATENCY_MS`)를 기다리므로 동시 요청이 쌓이고, 복제본당 동시 요청 5건 기준을 넘으면서 복제본이 늘어납니다. 스케일 아웃에는 시간이 걸리니 부하를 충분히 길게 거세요. 끝나면 요청 수, HTTP 상태 코드별 건수, 응답 시간 중앙값과 95백분위가 출력됩니다.

성공 기준: 터미널 A의 `Replicas`가 부하 중에 늘어나 최대 5까지 오르고, 터미널 B의 결과에 오류 없이 `HTTP 200`이 대부분입니다. 부하가 끝나고 몇 분이 지나면 복제본이 다시 줄어듭니다. 포털의 **Metrics**에서 Replica Count를 그래프로 보여 줄 수도 있습니다.

Foundry 백엔드에서는 `/api/chat` 부하가 모델 호출 비용을 만들기 때문에 `load-test.sh`가 기본으로 거부합니다. 이때는 `--path /healthz`로 부하를 거세요.

## 말하기 포인트

- **"클러스터가 없습니다."** 이미지, 포트, 스케일 규칙만 정하면 Container Apps가 나머지를 운영합니다. 쿠버네티스 지식이 없는 팀도 컨테이너를 서비스할 수 있습니다.
- **스케일 투 제로는 비용 모델**입니다. 쓰지 않는 시간에는 복제본이 없고, 첫 요청이 콜드 스타트를 부담합니다. 지연에 민감한 서비스라면 최소 복제본을 1 이상으로 두는 선택지가 있습니다(`MIN_REPLICAS`).
- **리비전은 불변**입니다. 새 버전은 새 리비전이고 이전 리비전은 그대로 남아 있어서, 롤백은 재배포가 아니라 트래픽 가중치 변경입니다.
- **레이블 주소로 운영 트래픽 없이 먼저 확인**합니다. 카나리 전에 v2에 직접 들어가 볼 수 있습니다.
- **같은 이미지, 같은 코드**입니다. Demo 3의 배포 워크플로가 이 앱에 새 리비전을 올리고, 인증 코드는 로컬, AKS와 같습니다.
- **비용**: 복제본이 0이면 컴퓨팅 비용이 없지만 레지스트리와 로그 같은 항목은 남습니다. 시연이 끝나면 정리하세요.

## 정리(Cleanup)

```bash
scripts/cleanup.sh aca             # Container Apps 리소스 그룹을 지웁니다 (확인 질문 있음)
```

`demo=ghcp-in-the-cloud` 태그가 없는 리소스 그룹은 지우지 않습니다. 카나리 상태만 초기화하려면 `DEMO_PASSWORD`를 설정한 채 `scripts/deploy-aca.sh`를 다시 실행하세요(같은 비밀번호를 그대로 씁니다). 비밀번호를 바꿔 실행하면 활성 리비전을 다시 시작해 적용합니다. 분할이 초기화되고 최신 리비전이 100%를 받습니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| 배포 직후 첫 요청이 오래 걸리거나 실패 | 최소 복제본이 0이면 첫 요청이 복제본을 시작합니다. 스크립트는 `/healthz`를 최대 3분쯤 기다립니다. 계속 실패하면 `az containerapp logs show --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo --type console`로 로그를 확인하세요. |
| `Replicas`가 0으로 줄지 않음 | 요청이 없는 상태를 더 기다리세요. 브라우저 탭이 열려 있으면 정보를 갱신하는 요청이 갈 수 있으니 탭을 닫으세요. |
| `aca-canary.sh deploy`가 `이미 있습니다`라고 함 | 같은 버전 이름(`v2`)의 리비전이 이미 있습니다. `v3`처럼 새 이름을 쓰세요. |
| `deploy`가 `<레이블> 레이블이 이미 N% 의 트래픽을 받고 있습니다`라고 함 | 이전 카나리가 끝나지 않았습니다. `promote` 또는 `rollback`으로 정리한 뒤 다시 `deploy`하세요. |
| `probe`가 `DEMO_PASSWORD 환경 변수가 필요합니다` | 사전 준비 4번처럼 `export DEMO_PASSWORD=...`를 하세요. 비밀번호를 잊었다면 `az containerapp secret show --name cloud-copilot-demo --resource-group rg-cloud-copilot-aca --secret-name demo-password --query value --output tsv`로 확인합니다. |
| `load-test.sh`가 거부하거나 `HTTP 429`가 나옴 | Foundry 백엔드면 비용 보호로 거부합니다(`--path /healthz` 사용). 요청 제한(Demo 1의 이슈 01)을 merge했다면 `/api/chat` 부하가 `429`를 받을 수 있으니 환경 변수 `RATE_LIMIT_PER_MINUTE=0`으로 끄거나 `--path /healthz`를 쓰세요. |
| 스케일 아웃이 보이지 않음 | 부하를 더 오래(`--duration 180`) 걸거나 동시 요청을 늘리세요(`--concurrency 40`). 스케일 규칙은 복제본당 동시 요청 5건 기준입니다. |
| `deploy-aca.yml` 실행 뒤 새 리비전이 0% | 카나리 분할이 설정된 상태입니다. `scripts/aca-canary.sh status`로 확인하고 `promote`하세요. |
| 지원하지 않는 리전/SKU 오류 | `LOCATION=<다른 리전> scripts/deploy-aca.sh`로 리전을 바꾸세요. |

## 다른 데모와 함께 쓰면

이 데모는 단독으로 끝까지 진행됩니다. 함께 쓰면 이야기가 이어집니다.

- **Demo 3 (GitHub Actions)**: `deploy-aca.yml`이 OIDC로 로그인해 이 앱에 새 리비전을 올립니다. 카나리 상태에서는 새 리비전이 0%로 만들어지므로 이 데모의 `promote`와 이어집니다.
- **Demo 4 (Foundry)**: `source .azure/foundry.env` 후 `scripts/deploy-aca.sh`를 실행하면 앱이 mock 대신 gpt-6.1-sol을 호출하고, 앱의 관리 ID가 비밀 없이 인증합니다. 이때 `/api/info`가 `backend=foundry`, `auth=entra-id`를 보여 줍니다.
- **Demo 6 (AKS)**: 같은 이미지를 AKS에도 올립니다. 마지막의 "AKS와 ACA 선택 가이드"에서 두 데모를 비교하세요.

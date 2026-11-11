# Demo 6 — AKS: 롤링 업데이트, 자동 확장, 워크로드 ID, 보안 기본값

같은 앱을 관리형 쿠버네티스(AKS)에 올리고, 쿠버네티스가 잘하는 일을 눈으로 보여 줍니다. 무중단 롤링 업데이트와 롤백, 부하에 따른 파드 자동 확장, 비밀 없는 Azure 인증(워크로드 ID), 안전하지 않은 파드를 막는 보안 기본값입니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | 배포 상태 확인 → HPA 자동 확장 → 롤링 업데이트와 롤백 → 워크로드 ID 확인 → (선택) 위험한 파드 거부 |
| 시간 | 약 8분. 클러스터 배포(5~10분)와 v2 이미지 빌드는 시연 전에 끝내 두세요. |
| 난이도 | 높음. `kubectl` 명령을 직접 실행합니다. |
| 독립 실행 | 예. Azure 구독만 있으면 됩니다. 기본은 `mock` 백엔드라서 Foundry 없이 동작하고, 워크로드 ID 확인도 mock에서 됩니다. Foundry 호출까지 보려면 Demo 4를 먼저 하세요. |

```text
브라우저 ─ kubectl port-forward ─▶ Service(ClusterIP) ─▶ 파드 2~5개 (HPA, PDB)
                                                  ▲            │ 워크로드 ID (비밀 없음)
          load-generator (시연할 때만 켬) ────────┘            ▼
                                                     Microsoft Foundry (선택)
```

## 왜 이 서비스인가 (이점)

- **쿠버네티스 표준 그대로, 컨트롤 플레인은 Azure가 운영**: `kubectl`, 매니페스트, 오픈소스 도구를 그대로 쓰면서 API 서버 같은 컨트롤 플레인은 직접 관리하지 않습니다(이 데모는 Free 티어).
- **무중단 롤링 업데이트와 롤백**: `maxSurge: 1`, `maxUnavailable: 0`과 readiness 프로브 덕분에 새 파드가 준비된 뒤에만 이전 파드가 내려갑니다. 문제가 생기면 `kubectl rollout undo` 한 줄로 되돌립니다.
- **자동 확장**: HPA가 CPU 사용률(요청량의 50%)을 보고 파드를 2~5개로 조절하고, 노드가 모자라면 클러스터 오토스케일러가 노드를 1~3개로 조절합니다.
- **가용성 보호**: PodDisruptionBudget(`minAvailable: 1`)이 노드 드레인이나 클러스터 업그레이드 중에도 마지막 파드를 지킵니다.
- **키 없는 Azure 인증(워크로드 ID, Workload Identity)**: 파드의 서비스 어카운트 토큰을 Microsoft Entra ID 토큰으로 교환합니다. API 키나 비밀번호를 파드에 넣지 않습니다.
- **기본이 안전한 클러스터**: 네임스페이스에 Pod Security `restricted`를 강제하고, 클러스터 접근은 로컬 계정 없이 Entra ID와 Azure RBAC로만 합니다.

## 사전 준비

1. **도구**: `az`(로그인: `az login`), `kubectl`, `kubelogin`, `python3`, `curl`, `bash` 4 이상(macOS는 `brew install bash`). `kubectl`과 `kubelogin`은 `az aks install-cli`로 함께 설치합니다. 구독이 ACR Tasks를 막아 두었다면 로컬 `docker`도 필요합니다.
2. **Azure 권한**: 리소스 그룹과 역할 할당을 만들 수 있는 계정(구독 Owner, 또는 Contributor와 User Access Administrator)이 필요합니다. 인프라가 클러스터 관리자 역할과 레지스트리 읽기 역할을 할당하기 때문입니다.
3. **배포** (5~10분 걸리므로 시연 전에):

   ```bash
   scripts/deploy-aks.sh                # 확인 질문에 y. 질문 없이 진행하려면 --yes
   ```

   클러스터, 레지스트리, 워크로드 ID를 만들고 이미지를 빌드한 뒤 매니페스트를 적용합니다. 끝에 **비밀번호**가 한 번 출력되니 적어 두세요(직접 정하려면 `DEMO_PASSWORD`). 기본 리소스 그룹은 `rg-cloud-copilot-aks`, 리전은 `koreacentral`, 노드 크기는 `Standard_D2s_v5`입니다. 클러스터 권한이 적용되길 기다리는 메시지가 몇 번 나올 수 있으며 정상입니다.

   Foundry의 모델을 쓰려면 먼저 Demo 4를 진행한 뒤 같은 셸에서 `source .azure/foundry.env`를 실행하고 이 스크립트를 실행하세요.
4. **v2 이미지를 미리 빌드**해 둡니다. 롤링 업데이트 시연에서는 이미 올라가 있는 이미지로 교체만 합니다.

   ```bash
   ACR_NAME="$(az acr list --resource-group rg-cloud-copilot-aks --query "[0].name" --output tsv)"
   ACR_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)"
   az acr build --registry "$ACR_NAME" --image cloud-copilot-demo:v2 \
     --build-arg APP_VERSION=v2 --file app/Dockerfile .        # 저장소 루트에서 실행
   ```

5. **시연 직전 점검**:

   ```bash
   kubectl get pods --namespace cloud-copilot-demo              # 파드 2개 이상이 Running, READY 1/1
   kubectl get deployment load-generator --namespace cloud-copilot-demo   # READY 0/0 (부하 꺼짐)
   ```

   터미널을 셋 준비하면 편합니다. 명령 실행용, `--watch` 감시용, 포트 포워딩용입니다.

다른 셸에서 이어서 시연한다면 클러스터에 다시 연결합니다.

```bash
CLUSTER_NAME="$(az aks list --resource-group rg-cloud-copilot-aks --query "[0].name" --output tsv)"
az aks get-credentials --resource-group rg-cloud-copilot-aks --name "$CLUSTER_NAME" --overwrite-existing
kubelogin convert-kubeconfig --login azurecli
```

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 이 데모는 거의 모든 단계가 터미널 명령이고, 웹 화면은 데모 앱 UI와 (선택) Azure 포털뿐입니다. 포털 메뉴 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요. 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

### 1. 클러스터와 워크로드 둘러보기 (약 1.5분)

```bash
kubectl get nodes
kubectl get deployment,hpa,pdb,service,pods --namespace cloud-copilot-demo
```

1. `Deployment`, `HorizontalPodAutoscaler`(최소 2, 최대 5), `PodDisruptionBudget`(`minAvailable 1`), `Service`(`ClusterIP`), 파드가 한 번에 보입니다.
2. 별도 터미널에서 포트 포워딩을 열고 브라우저로 접속합니다. 서비스를 인터넷에 노출하지 않으려고 `ClusterIP`로 두었습니다.

   ```bash
   kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace cloud-copilot-demo
   ```

   `http://localhost:8080`을 열고 사용자 `demo`와 비밀번호로 로그인합니다. 정보 칩에서 **플랫폼 `aks`**, 인스턴스(파드 이름), 리비전(파드 템플릿 해시), 앱 버전 `v1`을 확인합니다.
3. 같은 스모크 테스트가 포트 포워딩 주소에도 통과합니다.

   ```bash
   DEMO_PASSWORD='<비밀번호>' scripts/smoke-test.sh http://localhost:8080 --expect-backend mock
   ```

성공 기준: 파드가 2개 이상 `Running`이고, 플랫폼 칩이 `aks`이며, 인스턴스 칩이 `kubectl get pods`의 파드 이름 중 하나와 같습니다. 스모크 테스트는 `모든 확인(14개)을 통과했습니다.`를 출력합니다. Foundry 백엔드로 배포했다면 `--expect-backend foundry`를 쓰세요.

포트 포워딩은 파드 하나에 연결되므로 **트래픽 분포 보기** 버튼은 한 인스턴스만 보여 줍니다. 여러 인스턴스로 분산되는 모습은 Demo 5의 카나리에서 보여 주세요.

### 2. 부하가 오르면 파드가 늘어난다: HPA (약 2.5분)

```bash
# 터미널 A: HPA와 파드 변화를 계속 지켜봅니다 (중지: Ctrl+C)
kubectl get hpa,pods --namespace cloud-copilot-demo --watch
```

```bash
# 터미널 B: 부하 생성기를 켭니다
kubectl scale deployment/load-generator --replicas=1 --namespace cloud-copilot-demo
```

`load-generator`는 같은 이미지로 서비스의 `/healthz`를 계속 호출합니다. 모델을 호출하지 않으므로 비용 없이 CPU만 오릅니다. 파드의 CPU 요청량이 100m이고 목표가 50%이므로 파드당 평균 CPU가 약 50m를 넘으면 확장 대상이 됩니다. 부하 생성기는 이 기준을 넘기기 위한 것이며, 실제 사용량은 `kubectl top pods --namespace cloud-copilot-demo`로 볼 수 있습니다.

1. 터미널 A에서 HPA의 `TARGETS` 값이 목표(50%)를 넘고 `REPLICAS`가 2에서 늘어나며 새 파드가 `ContainerCreating`을 거쳐 `Running`이 됩니다. 값이 한동안 `<unknown>`이면 메트릭을 모으는 중이니 잠시 기다립니다. 확장에는 수십 초에서 몇 분이 걸릴 수 있습니다.
2. 확인했으면 부하를 끕니다.

   ```bash
   kubectl scale deployment/load-generator --replicas=0 --namespace cloud-copilot-demo
   ```

3. 부하가 사라지면 파드가 다시 줄어듭니다. HPA는 흔들림을 막으려고 줄이기 전에 안정화 시간(이 데모는 60초)을 두므로 몇 분 지켜보세요.

성공 기준: 부하를 켠 뒤 `REPLICAS`가 2보다 커지고(최대 5), 부하를 끈 뒤 시간이 지나 다시 2로 돌아옵니다. 몇 개까지 늘어나는지는 환경에 따라 다르니 숫자를 약속하지 마세요.

### 3. 무중단 롤링 업데이트와 롤백 (약 2.5분)

```bash
# 터미널 A: 파드 교체 과정을 지켜봅니다 (중지: Ctrl+C)
kubectl get pods --namespace cloud-copilot-demo --watch
```

```bash
# 터미널 B: 이미지를 v2로 교체합니다 (사전 준비 4의 ACR_SERVER 사용)
kubectl set image deployment/cloud-copilot-demo app="$ACR_SERVER/cloud-copilot-demo:v2" --namespace cloud-copilot-demo
kubectl rollout status deployment/cloud-copilot-demo --namespace cloud-copilot-demo
kubectl rollout history deployment/cloud-copilot-demo --namespace cloud-copilot-demo
```

1. 터미널 A에서 새 파드가 먼저 만들어지고(`maxSurge: 1`), `READY 1/1`이 된 뒤에야 이전 파드가 `Terminating`으로 바뀌는 것을 봅니다(`maxUnavailable: 0`). 준비된 파드는 원하는 복제본 수 아래로 내려가지 않습니다.
2. 포트 포워딩은 연결된 파드가 교체되면 끊깁니다(`lost connection to pod`). 다시 실행하고 브라우저를 새로 고치면 **앱 버전이 `v2`**, 리비전과 인스턴스 이름이 새 값으로 바뀐 것이 보입니다.
3. 롤백합니다. v2에 문제가 있다는 가정입니다.

   ```bash
   kubectl rollout undo deployment/cloud-copilot-demo --namespace cloud-copilot-demo
   kubectl rollout status deployment/cloud-copilot-demo --namespace cloud-copilot-demo
   ```

   포트 포워딩을 다시 열면 앱 버전이 `v1`로 돌아와 있습니다.

성공 기준: `rollout status`가 `successfully rolled out`을 출력하고, 롤아웃 중에도 `READY 1/1` 파드가 계속 남아 있으며, UI의 앱 버전이 `v1` → `v2` → (롤백 후) `v1`로 바뀝니다. 같은 롤링 업데이트를 Demo 3의 `deploy-aks.yml` 워크플로가 대신 실행합니다(커밋 앞 7자리가 이미지 태그가 됩니다).

### 4. 워크로드 ID: 비밀 없이 Azure를 부른다 (약 1분)

```bash
# 서비스 어카운트가 어떤 관리 ID와 연결되는지 (client-id 어노테이션)
kubectl get serviceaccount cloud-copilot-demo --namespace cloud-copilot-demo --output jsonpath='{.metadata.annotations}'

# 파드에 주입된 값 중 인증에 쓰이는 네 가지만 골라 봅니다
kubectl exec --namespace cloud-copilot-demo deploy/cloud-copilot-demo -- printenv \
  | grep -E '^AZURE_(CLIENT_ID|TENANT_ID|FEDERATED_TOKEN_FILE|AUTHORITY_HOST)='
```

1. 서비스 어카운트의 `azure.workload.identity/client-id` 어노테이션이 관리 ID의 클라이언트 ID를 가리킵니다.
2. 파드에는 `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE`, `AZURE_AUTHORITY_HOST`가 주입됩니다. 비밀 값은 없고, 토큰 파일은 짧게 사는 서비스 어카운트 토큰입니다. Azure SDK가 이 토큰을 Entra ID 토큰으로 교환합니다.
3. Foundry 백엔드(Demo 4)로 배포했다면 `/api/info`의 `auth`가 `entra-id`이고 모델 호출에 API 키가 없습니다.

성공 기준: 어노테이션에 클라이언트 ID가 있고 네 환경 변수가 모두 나옵니다. 신뢰는 서비스 어카운트 `system:serviceaccount:cloud-copilot-demo:cloud-copilot-demo` 하나로 한정되어 있습니다.

> 화면을 공유하는 중에는 `printenv`를 그대로 실행하지 마세요. 앱 비밀번호(`DEMO_PASSWORD`)가 함께 보입니다. 위 명령은 필요한 네 줄만 걸러서 보여 줍니다.

### 5. (선택) 안전하지 않은 파드는 들어올 수 없다 (약 1분)

네임스페이스에는 Pod Security `restricted`가 강제됩니다. 권한이 높은 파드를 만들어 보면 거부됩니다.

```bash
kubectl apply --namespace cloud-copilot-demo --filename - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: privileged-demo
spec:
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sleep", "3600"]
      securityContext:
        privileged: true
EOF
```

성공 기준: `Error from server (Forbidden)`와 함께 `violates PodSecurity "restricted:latest"`가 출력되고 어떤 파드도 만들어지지 않습니다. 이 앱의 파드는 비루트 UID 10001, 읽기 전용 루트 파일 시스템, 모든 capability 제거로 이미 `restricted`를 만족합니다.

## 말하기 포인트

- **"쿠버네티스의 힘, 운영 부담은 Azure가 덜어 줍니다."** 컨트롤 플레인은 플랫폼이 운영하고(이 데모는 쿠버네티스 패치 버전 자동 업그레이드 채널을 켭니다), 팀은 워크로드에 집중합니다.
- **무중단은 기본값이 아니라 설정의 결과**입니다. `maxUnavailable: 0`, readiness 프로브, PDB가 함께 있어야 합니다. 매니페스트 세 줄이 그 약속입니다.
- **HPA는 요청량(requests) 대비 사용률**로 판단합니다. 요청량을 현실적으로 정하는 것이 자동 확장의 전제입니다.
- **워크로드 ID는 "비밀을 없애는" 기능**입니다. 저장소에도, 시크릿에도, 파드 환경 변수에도 키가 없고, 신뢰 범위는 네임스페이스와 서비스 어카운트 한 쌍입니다.
- **접근도 Entra ID**입니다. 클러스터는 로컬 계정이 꺼져 있고 `kubectl`은 `az login` 토큰을 씁니다. 배포 파이프라인(Demo 3)의 ID는 이 네임스페이스에만 쓰기 권한이 있습니다.
- **비용**: AKS는 노드가 계속 과금됩니다. 시연이 끝나면 바로 정리하세요.

## 정리(Cleanup)

```bash
scripts/cleanup.sh aks             # AKS 리소스 그룹을 지웁니다 (확인 질문 있음)
```

`demo=ghcp-in-the-cloud` 태그가 없는 리소스 그룹은 지우지 않습니다. 부하 생성기가 켜져 있다면 먼저 `kubectl scale deployment/load-generator --replicas=0 --namespace cloud-copilot-demo`로 끕니다. v2 상태로 시연을 끝냈다면 `kubectl rollout undo deployment/cloud-copilot-demo --namespace cloud-copilot-demo`로 v1로 되돌리면 되고, 클러스터를 다시 만들 필요는 없습니다. `scripts/deploy-aks.sh`를 다시 실행할 때는 `DEMO_PASSWORD`를 지정하세요. 지정하지 않으면 새 비밀번호가 만들어지고, 스크립트가 파드를 다시 시작해 새 비밀번호를 적용합니다. 로컬 `kubeconfig`에 남은 컨텍스트는 `kubectl config get-contexts`로 확인해 `kubectl config delete-context <이름>`으로 지웁니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| 배포 중 `클러스터 권한이 적용되길 기다리는 중...`이 반복됨 | 역할 할당이 API 서버에 반영되는 데 몇 분 걸립니다. 정상이며, 20번 재시도 후에도 실패하면 스크립트를 다시 실행하세요. |
| `kubectl`이 인증 오류를 내거나 `kubelogin`을 찾지 못함 | `az login`을 다시 하고 `az aks install-cli`로 도구를 설치한 뒤 사전 준비 아래의 "클러스터에 다시 연결" 명령을 실행하세요. |
| 노드 VM 크기를 쓸 수 없다는 오류 | 리전에서 가능한 크기를 확인(`az vm list-skus --location koreacentral --size Standard_D2s --output table`)하고 `NODE_VM_SIZE=<크기> scripts/deploy-aks.sh`로 다시 실행하세요. |
| `az acr build`가 실패(ACR Tasks 차단) | `deploy-aks.sh`는 자동으로 로컬 Docker를 씁니다. 사전 준비 4는 `az acr login --name "$ACR_NAME"` 후 `docker build --build-arg APP_VERSION=v2 --file app/Dockerfile --tag "$ACR_SERVER/cloud-copilot-demo:v2" .`와 `docker push "$ACR_SERVER/cloud-copilot-demo:v2"`로 대체합니다. |
| 파드가 `ImagePullBackOff` | 이미지 태그가 레지스트리에 없거나 레지스트리 읽기 권한이 아직 반영되지 않았습니다. `az acr repository show-tags --name "$ACR_NAME" --repository cloud-copilot-demo --output tsv`로 태그를 확인하고 `kubectl describe pod <파드>`의 이벤트를 보세요. |
| 파드가 `Pending` | 노드 자원이 부족하면 클러스터 오토스케일러가 노드를 추가하기까지 몇 분 걸립니다(최대 3대). 구독 쿼터가 부족하면 `kubectl describe pod <파드>`에 이유가 나옵니다. |
| HPA `TARGETS`가 계속 `<unknown>` | 메트릭을 아직 모으지 못했습니다. 1~2분 기다린 뒤 `kubectl describe hpa cloud-copilot-demo --namespace cloud-copilot-demo`로 이유를 확인하세요. |
| 부하를 켜도 파드가 늘지 않음 | `kubectl get pods --selector app.kubernetes.io/name=load-generator --namespace cloud-copilot-demo`로 부하 파드가 `Running`인지 확인하세요. 확장 결정에는 시간이 걸립니다. |
| 포트 포워딩이 `lost connection to pod`로 끊김 | 롤아웃으로 연결된 파드가 교체되었습니다. 명령을 다시 실행하세요. |
| 비밀번호를 잊음 | `kubectl get secret cloud-copilot-demo --namespace cloud-copilot-demo --output jsonpath='{.data.password}' \| base64 --decode` |
| 롤아웃 직후 UI에 이전 버전이 계속 보임 | 포트 포워딩이 아직 종료되지 않은 이전 파드에 붙어 있습니다. `rollout status`가 끝난 뒤 포트 포워딩을 다시 열고 새로 고치세요. |

## 다른 데모와 함께 쓰면

이 데모는 단독으로 끝까지 진행됩니다. 함께 쓰면 이야기가 이어집니다.

- **Demo 3 (GitHub Actions)**: `deploy-aks.yml`을 실행하면(`gh workflow run deploy-aks.yml`) OIDC로 로그인해 이미지를 빌드하고 같은 롤링 업데이트를 합니다. 이 파이프라인의 ID는 클러스터 사용자 역할과 이 네임스페이스에 한정된 RBAC Writer 역할만 가집니다.
- **Demo 4 (Foundry)**: `source .azure/foundry.env` 후 `scripts/deploy-aks.sh`를 실행하면 파드가 워크로드 ID로 gpt-6.1-sol을 호출하고 `/api/info`가 `backend=foundry`, `auth=entra-id`를 보여 줍니다.
- **Demo 5 (ACA)**: 같은 이미지를 서버리스로 운영합니다. 아래 선택 가이드로 두 방식을 비교하세요.

### AKS와 ACA 선택 가이드

두 데모는 같은 이미지를 서로 다른 방식으로 운영합니다. 어느 쪽이 더 좋은지가 아니라 팀이 무엇을 원하는지의 차이입니다.

| 관점 | Azure Container Apps (Demo 5) | AKS (이 데모) |
|---|---|---|
| 운영 부담 | 클러스터가 없습니다. 이미지와 설정 중심입니다. | 노드 풀, 업그레이드, 네트워킹, 매니페스트를 직접 다룹니다(컨트롤 플레인은 Azure가 운영). |
| 확장 | 요청 수 규칙, 스케일 투 제로 | HPA와 노드 오토스케일러. 기본 HPA는 최소 1개 이상이며 0까지 줄이려면 KEDA 같은 추가 구성이 필요합니다. |
| 배포 전략 | 리비전과 트래픽 분할로 카나리, 블루-그린, 즉시 롤백을 설정으로 처리 | 롤링 업데이트가 기본이며 카나리 같은 전략은 인그레스, 서비스 메시, 전용 도구를 더해 구성 |
| 제어 범위 | 앱 수준의 제어 | 쿠버네티스 API 전체(CRD, 오퍼레이터, 네트워크 정책, 노드 스케줄링) |
| 어울리는 경우 | 웹 앱, API, 이벤트 처리를 빠르게 운영하고 싶을 때 | 쿠버네티스 표준 도구와 생태계가 필요하거나 세밀한 제어가 필요할 때 |

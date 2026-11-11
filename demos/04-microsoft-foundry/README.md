# Demo 4 — Microsoft Foundry: 모델 선택권과 키 없는 보안 연결

gpt-6.1-sol을 Microsoft Foundry에 배포하고, 같은 앱 코드가 API 키 없이 Microsoft Entra ID로 모델을 호출하는 모습을 보여 줍니다. 로컬, Container Apps, AKS에서 인증 코드는 똑같고 달라지는 것은 "누구로 로그인했는가"뿐입니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 목표 | 모델(gpt-6.1-sol) 배포 → 키 없는 로컬 호출 → `/api/info`로 인증 방식·모델·effort 확인까지 한 흐름으로 보여 주고, 배포 이름과 effort만 바꿔 모델 설정을 바꾸는 방법을 설명합니다. |
| 시간 | 약 7분. 배포는 시연 전에 미리 끝내 두세요. |
| 난이도 | 보통 |
| 독립 실행 | 예. Azure 구독만 있으면 됩니다. GitHub, Container Apps, AKS는 필요 없습니다. |

```text
az login ─▶ DefaultAzureCredential ─▶ Entra ID 토큰 (범위: https://ai.azure.com/.default)
        ─▶ https://<리소스>.services.ai.azure.com/openai/v1/ ─▶ gpt-6.1-sol (effort=max → xhigh)
```

## 왜 이 서비스인가 (이점)

- **Azure 거버넌스 안에서 모델 사용**: Microsoft Entra ID 인증, Azure RBAC, 구독 쿼터와 리전, 리소스 태그가 다른 Azure 리소스와 같은 방식으로 적용됩니다. 별도의 외부 API 키 관리 체계가 필요 없습니다.
- **키 없는 인증**: 호출하는 쪽에 비밀이 없습니다. 로컬은 `az login`, Container Apps는 관리 ID, AKS는 워크로드 ID가 같은 코드(`DefaultAzureCredential`)로 토큰을 받습니다. 필요한 역할은 모델 호출 전용인 `Cognitive Services User` 하나입니다.
- **배포 이름으로 모델 교체**: 앱은 모델 ID가 아니라 Foundry의 **배포 이름**(`FOUNDRY_MODEL`)만 압니다. 다른 모델을 배포해 이름만 바꾸면 코드 수정 없이 교체됩니다.
- **`effort=max`로 깊은 추론**: `low`, `medium`, `high`, `xhigh`, `max` 중에서 `FOUNDRY_EFFORT`로 정합니다. gpt-6.1-sol은 `max`가 없어서 `reasoning_effort=xhigh`로 보내고(`/api/info`도 `xhigh`로 보여 줍니다), Claude는 `output_config={"effort": "max"}`를 그대로 씁니다. 깊게 생각할수록 답이 좋아질 수 있고 대신 시간과 토큰을 더 씁니다.
- **키 인증을 아예 끌 수 있음**: `DISABLE_LOCAL_AUTH=true`로 배포하면 API 키 인증이 꺼지고 Entra ID만 허용됩니다.
- **코드로 만든 배포**: 계정, 프로젝트, 모델 배포, 약관 동의 정보가 `infra/foundry/main.bicep`에 있어서 같은 환경을 다시 만들거나 정리하기 쉽습니다.

## 사전 준비

1. **Azure 구독**: gpt-6.1-sol은 모델 쿼터가 있는 구독이면 됩니다. 지원 리전은 `eastus2`, `swedencentral`, `westus2`이고 이 데모의 기본값은 `swedencentral`입니다. Claude를 쓰려면 마켓플레이스 구매가 가능한 Enterprise 또는 MCA-E 구독이 필요합니다(Microsoft 내부 구독은 `UnsupportedForInternalSubscription`으로 거부됩니다).
2. **Anthropic 약관(Claude를 쓸 때만)**: `MODEL_NAME=claude-sonnet-5-5`로 배포하면 Anthropic 상용 약관에 동의하는 것으로 처리되고, 조직 이름을 `CLAUDE_ORGANIZATION_NAME`으로 넘겨야 합니다. gpt-6.1-sol에는 해당하지 않습니다.
3. **도구**: `az`(로그인: `az login`), Python 3.12, `bash` 4 이상(macOS는 `brew install bash`).
4. **Python 의존성**:

   ```bash
   python -m pip install --requirement app/requirements.txt
   ```

5. **Foundry 배포** (몇 분 걸리므로 시연 전에):

   ```bash
   scripts/deploy-foundry.sh            # 확인 질문에 y. 질문 없이 진행하려면 --yes
   ```

   로그인한 사용자에게 `Cognitive Services User` 역할이 자동으로 부여되고, 연결 정보가 `.azure/foundry.env`에 저장됩니다(`.gitignore` 대상). 다른 사용자에게 권한을 주려면 `PRINCIPAL_ID`, `PRINCIPAL_TYPE`을 지정하세요. 포털(ai.azure.com)에서 직접 배포해도 되지만 이 문서는 스크립트 기준으로 설명합니다.

## 시연 순서

> **UI 메뉴 이름은 변경될 수 있음**: 아래 클릭 경로는 작성 시점 기준입니다. 이름이 다르면 같은 뜻의 메뉴를 찾아 주세요. 꺾쇠(`<>`) 안은 자신의 값으로 바꾸는 자리 표시자입니다.

### 1. 배포된 모델 확인 (약 1.5분)

1. 터미널에서 방금 만든 것을 보여 줍니다.

   ```bash
   cat .azure/foundry.env               # FOUNDRY_RESOURCE, FOUNDRY_MODEL(배포 이름) 등. 비밀은 없습니다.
   source .azure/foundry.env
   az cognitiveservices account deployment list \
     --resource-group "$FOUNDRY_RESOURCE_GROUP" --name "$FOUNDRY_RESOURCE" \
     --query "[].{Name:name, Model:properties.model.name, Capacity:sku.capacity}" --output table
   ```

2. 포털(ai.azure.com)에서 프로젝트를 열어 같은 모델 배포를 보여 줍니다. 배포 이름, 모델, 용량(1K TPM 단위)이 보입니다.
3. 엔드포인트 형태를 설명합니다. `https://<리소스>.services.ai.azure.com/openai/v1/` (Claude는 `.../anthropic/`)

성공 기준: 배포 목록에 `gpt-6.1-sol`이 있고, `.azure/foundry.env`에 API 키가 없다는 점이 청중에게 보입니다.

### 2. 키 없이 로컬에서 호출 (약 2.5분)

```bash
az login                                  # 이미 했다면 건너뜁니다
source .azure/foundry.env                 # LLM_BACKEND=foundry, FOUNDRY_RESOURCE, FOUNDRY_MODEL
export DEMO_PASSWORD='<임의의 비밀번호>'     # 데모 UI 비밀번호. 저장소에 넣지 마세요.
python -m app.server                      # http://127.0.0.1:8080  (사용자: demo)
```

1. 브라우저에서 `http://127.0.0.1:8080`을 열고 사용자 `demo`와 위 비밀번호로 로그인합니다.
2. 한국어로 질문합니다. 예: "Azure Container Apps와 AKS 중 팀 2명이 운영할 사내 API에는 무엇이 맞는지 근거와 함께 알려 줘."
3. 코드에 키가 없다는 점을 보여 줍니다. `FOUNDRY_API_KEY`(또는 `ANTHROPIC_FOUNDRY_API_KEY`)가 설정돼 있지 않으면 앱은 `DefaultAzureCredential`로 `az login` 계정의 토큰을 씁니다.

역할이 방금 부여됐다면 전파에 몇 분이 걸릴 수 있어 처음 호출이 권한 오류로 실패할 수 있습니다. 잠시 뒤 다시 시도하세요.

성공 기준: 모델이 한국어 답변을 돌려주고, 화면에 응답한 인스턴스와 앱 버전이 표시됩니다.

### 3. `/api/info`로 인증 방식, 모델, effort 확인 (약 1.5분)

화면 위쪽의 정보 칩이나 아래 명령으로 확인합니다.

```bash
curl -s -u "demo:$DEMO_PASSWORD" http://127.0.0.1:8080/api/info
```

성공 기준: 응답에 `"backend": "foundry"`, `"auth": "entra-id"`, `"model": "gpt-6.1-sol"`, `"effort": "xhigh"`가 들어 있습니다. (mock 백엔드에서는 `"auth": "none"`입니다.)

### 4. (선택) effort와 모델 배포 바꿔 보기 (약 1.5분)

앱을 중지(Ctrl+C)한 뒤 환경 변수만 바꿔 다시 시작합니다. 코드는 그대로입니다.

```bash
FOUNDRY_EFFORT=low python -m app.server      # 같은 질문의 답변 깊이와 지연을 max(xhigh)와 비교
```

다른 모델로 교체하려면 새 배포를 추가하고 이름만 가리킵니다. 사용할 수 있는 모델 이름은 포털의 모델 카탈로그에서 확인하세요. 배포가 늘면 쿼터도 더 씁니다.

```bash
MODEL_NAME="<다른 모델 이름>" MODEL_VERSION="<모델 버전>" scripts/deploy-foundry.sh --yes   # 같은 계정에 배포가 하나 더 생깁니다
source .azure/foundry.env                                              # FOUNDRY_MODEL이 새 배포 이름으로 바뀝니다
python -m app.server
```

(선택) 키 인증을 끈 상태를 보여 주려면 `DISABLE_LOCAL_AUTH=true scripts/deploy-foundry.sh --yes`로 다시 배포합니다. 이후에는 API 키로 호출하면 거부되고 Entra ID 호출만 통과합니다. 이 데모의 모든 경로가 Entra ID를 쓰므로 앱 동작은 그대로입니다.

성공 기준: `FOUNDRY_EFFORT=low`로 시작한 앱의 `/api/info`가 `"effort": "low"`를 보여 주고, 모델 배포를 추가했다면 `model`이 새 배포 이름으로 바뀌어 있습니다. 코드는 한 줄도 바꾸지 않았습니다.

## 말하기 포인트

- **"앱 코드에 키가 없습니다."** 같은 이미지가 로컬에서는 `az login`, Container Apps에서는 관리 ID, AKS에서는 워크로드 ID로 같은 방식의 토큰을 받습니다. 누가 호출하는지는 Entra ID와 Azure RBAC가 기록하고 통제합니다.
- **최소 권한**: 추론 호출에는 `Cognitive Services User`만 있으면 됩니다. 계정 설정을 바꾸는 권한은 필요 없습니다.
- **모델은 설정**입니다. 코드는 배포 이름 하나만 알고, 모델 교체는 배포와 환경 변수 변경으로 끝납니다.
- **effort는 비용과 품질의 손잡이**입니다. `max`(GPT에서는 `xhigh`)는 가장 깊게 추론하는 대신 응답이 느리고 토큰을 많이 씁니다. 용도에 따라 낮춰서 쓰세요.
- **비용 통제**: 호출마다 토큰 비용이 발생하고 쿼터(1K TPM 단위)로 상한을 둡니다. 시연이 끝나면 정리하고, 쿼터를 돌려받으려면 purge까지 해야 합니다.
- **범위**: 이 데모는 공용 엔드포인트를 씁니다. 프라이빗 엔드포인트나 방화벽 같은 네트워크 격리는 다루지 않습니다.

## 정리(Cleanup)

```bash
scripts/cleanup.sh foundry         # 리소스 그룹을 지우고 삭제된 계정을 purge해 쿼터를 돌려받습니다 (확인 질문 있음)
rm -f .azure/foundry.env           # 로컬 연결 정보
```

`demo=ghcp-in-the-cloud` 태그가 없는 리소스 그룹은 지우지 않습니다. Foundry 계정은 삭제만 하면 일정 기간 "삭제됨" 상태로 남아 쿼터와 이름을 붙잡으므로 `cleanup.sh`가 purge까지 수행합니다.

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| 배포가 쿼터 또는 용량 오류로 실패 | `CAPACITY=10`처럼 줄이거나 `LOCATION=eastus2`처럼 다른 리전을 지정해 다시 실행하세요. 구독 쿼터는 포털에서 확인합니다. |
| Claude 배포가 `UnsupportedForInternalSubscription`(마켓플레이스 구매 불가)으로 거부됨 | Enterprise 또는 MCA-E 구독이 필요합니다. 구독 종류를 확인하세요. 이 키트의 기본 모델 gpt-6.1-sol은 해당하지 않습니다. |
| 앱 호출이 `403` 또는 권한 오류 | 역할 전파를 몇 분 기다리세요. `az account show`의 사용자가 `deploy-foundry.sh`를 실행한 사용자와 같은지도 확인합니다. 다르면 `PRINCIPAL_ID=<객체 ID> scripts/deploy-foundry.sh --yes`로 권한을 부여하세요. |
| `DefaultAzureCredential` 인증 실패 | `az login`을 다시 하고 올바른 테넌트인지 확인하세요(`az login --tenant <테넌트>`). 환경에 `AZURE_CLIENT_ID` 같은 변수가 남아 있다면 `unset`하세요. |
| `404` 또는 배포를 찾지 못함 | `FOUNDRY_MODEL`은 모델 ID가 아니라 **배포 이름**이고, `FOUNDRY_RESOURCE`는 호스트 이름이 아니라 **리소스 이름**입니다. `source .azure/foundry.env` 후 다시 시작하세요. |
| `모델이 텍스트 응답을 반환하지 않았습니다 (stop_reason=...)` | 추론에 토큰을 모두 쓴 경우입니다. `FOUNDRY_MAX_TOKENS=8000`처럼 늘리거나(256~16000) `FOUNDRY_EFFORT`를 낮추세요. |
| 다시 배포할 때 이름이 이미 사용 중이라는 오류 | 이전 계정이 "삭제됨" 상태로 남아 있습니다. `scripts/cleanup.sh foundry`로 purge하거나 `az cognitiveservices account purge --name <계정> --resource-group <그룹> --location <리전>`을 실행하세요. |
| 키 인증이 안 됨 | `DISABLE_LOCAL_AUTH=true`로 배포한 계정입니다. Entra ID(`az login`)를 쓰세요. |

## 다른 데모와 함께 쓰면

이 데모는 단독으로 끝까지 진행됩니다. 함께 쓰면 연결이 보입니다.

- **Demo 5 (Container Apps)**: 같은 셸에서 `source .azure/foundry.env` 후 `scripts/deploy-aca.sh`를 실행하면 앱이 mock 대신 이 Foundry의 gpt-6.1-sol을 호출합니다. 앱의 관리 ID가 `Cognitive Services User` 역할을 받습니다.
- **Demo 6 (AKS)**: 같은 방식으로 `scripts/deploy-aks.sh`를 실행하면 Pod가 워크로드 ID로 Foundry를 호출합니다. 비밀은 어디에도 없습니다.
- **Demo 1 (GitHub Copilot)**: Copilot이 만든 코드가 이 앱의 `/api/chat`을 바꾸는 이슈를 시연할 때, 이 Foundry 연결이 있으면 결과를 실제 모델 응답으로 확인할 수 있습니다.

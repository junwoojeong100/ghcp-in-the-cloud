# GitHub × Microsoft Azure 데모

GitHub Copilot, GitHub 저장소와 Actions, Microsoft Foundry, Azure Container Apps(ACA), AKS를 각각 독립적으로 시연할 수 있는 작은 한국어 데모입니다. 브라우저에서 질문하면 Microsoft Foundry의 **Claude Sonnet 5.5**가 답하며, 모델 ID `claude-sonnet-5-5`와 추론 노력 `max`를 사용합니다.

## 데모 메뉴

| 데모 | 무엇을 보여주나요? | 필요한 것 |
|---|---|---|
| Copilot + GitHub 저장소 | 이슈 작성 → Copilot에 구현 요청 → PR/리뷰/체크 확인 | GitHub 저장소, Copilot 사용 권한 |
| GitHub Actions | PR에서 유닛 테스트와 컨테이너 빌드 자동 실행 | GitHub Actions |
| Microsoft Foundry | 한국어 웹 UI에서 Claude Sonnet 5.5 호출 | Claude 모델을 배포한 Foundry 리소스 |
| ACA | 같은 컨테이너를 scale-to-zero가 가능한 관리형 컨테이너 앱으로 실행 | Azure 구독, 컨테이너 이미지 |
| AKS | 같은 컨테이너를 Kubernetes Deployment/Service로 실행 | Azure 구독, 실행 중인 AKS 클러스터, 이미지 레지스트리 |

Copilot/저장소, Actions, Foundry, ACA, AKS 데모는 서로 결합되어 있지 않습니다. ACA와 AKS는 같은 이미지를 각자 배포하므로 둘 중 하나만 시연해도 됩니다. Azure 리소스는 생성 시 비용이 발생할 수 있습니다. 불필요한 리소스와 외부 로드 밸런서는 데모 후 삭제하세요.

## 빠른 시작: GitHub 데모

1. 저장소에서 **Issues → New issue → Copilot demo task**를 선택해 작은 변경과 완료 조건을 작성합니다.
2. Copilot 사용 권한이 있으면 이슈에 `@copilot`을 할당하거나 Copilot coding agent에 구현을 요청합니다. 예: “이 이슈를 구현하고 경계값 테스트를 추가한 뒤 변경 이유를 요약해줘.”
3. Copilot이 만든 PR에서 diff, 테스트, `Demo CI` 체크를 검토합니다. `.github/copilot-instructions.md`가 프로젝트의 실행/보안 규칙을 제공합니다.
4. 직접 확인하려면 다음 테스트와 컨테이너 빌드를 실행합니다.

```bash
python -m pip install -r app/requirements.txt
python -m unittest discover -s app/tests -v
docker build --file app/Dockerfile --tag cloud-copilot-demo .
```

GitHub Actions는 PR/푸시에서 같은 테스트와 Docker 빌드를 실행하며 Azure 자격 증명 없이 동작합니다.

## 빠른 시작: Microsoft Foundry

1. Foundry에서 Anthropic Claude Sonnet 5.5를 사용할 수 있는 구독/리전을 확인하고 모델을 배포합니다. 구독 자격, 지역 지원, Anthropic 이용 약관을 먼저 확인하세요. [Microsoft Foundry: Claude 모델 배포 및 사용](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-claude)
2. 저장소 루트에서 환경 변수로 리소스 이름과 API 키를 설정합니다. API 키를 소스, 이슈, 로그에 저장하지 마세요.

```bash
export FOUNDRY_RESOURCE="your-foundry-resource-name"
read -rsp "Foundry API key: " ANTHROPIC_FOUNDRY_API_KEY; echo
export ANTHROPIC_FOUNDRY_API_KEY
read -rsp "Demo UI password: " DEMO_PASSWORD; echo
export DEMO_PASSWORD
python -m app.server
```

3. `http://localhost:8080`을 열고 사용자 이름 `demo`와 UI 비밀번호를 입력해 질문합니다. `/healthz`에서 상태를 확인합니다. 종료 후 `unset ANTHROPIC_FOUNDRY_API_KEY DEMO_PASSWORD`를 실행합니다.

앱은 Anthropic SDK의 Foundry 클라이언트, 모델 ID `claude-sonnet-5-5`, `output_config.effort=max`를 사용합니다. API 키와 UI 비밀번호는 서버에만 존재하며, 인증되지 않은 채팅 요청은 거부됩니다. 모델 접근이 아직 준비되지 않아도 테스트와 이미지 빌드는 가능하며, 앱은 설정이 없으면 채팅 요청에 안전한 오류를 반환합니다.

## Azure 배포용 이미지 준비

ACA/AKS에 배포하려면 두 서비스에서 읽을 수 있는 Azure Container Registry(ACR)와 권한이 필요합니다. 기존 ACR에 소스에서 이미지를 빌드하고 전체 이미지 이름을 저장합니다.

```bash
export ACR_NAME="your-existing-acr"
az acr build --registry "$ACR_NAME" --image cloud-copilot-demo:latest --file app/Dockerfile .
export IMAGE_NAME="$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)/cloud-copilot-demo:latest"
```

GitHub Actions의 CI는 검증/이미지 빌드만 하며 이미지를 Azure에 게시하지 않습니다. 따라서 Azure 자격 증명 없이 PR 검증을 시연할 수 있습니다.

## 빠른 시작: Azure Container Apps

이미지 레지스트리에 앱 이미지를 올린 후 아래 템플릿으로 리소스 그룹에 ACA 환경과 앱을 생성합니다. `imageName`에는 Azure에서 읽을 수 있는 전체 이미지 이름과 태그를 지정하세요.

```bash
export AZURE_RESOURCE_GROUP="your-resource-group"
export IMAGE_NAME="your-registry.example/cloud-copilot-demo:latest"
export FOUNDRY_RESOURCE="your-foundry-resource-name"
bash scripts/deploy-aca.sh
```

Bicep은 Log Analytics 작업 공간, ACA 환경 및 외부 HTTPS ingress가 있는 앱을 만듭니다. 최소 복제본은 0, 최대는 2입니다. 배포 출력의 `appUrl`을 열고 사용자 이름 `demo`와 스크립트에서 지정한 비밀번호로 로그인하세요. 스크립트는 Foundry 키와 UI 비밀번호를 숨겨 입력받고 권한이 제한된 임시 파라미터 파일로 전달한 뒤 삭제합니다. **데모 전용 리소스 그룹**을 사용하면 시연 후 해당 그룹을 삭제해 리소스를 정리할 수 있습니다. 공유 리소스 그룹 전체를 삭제하지 마세요.

## 빠른 시작: AKS

실행 중인 클러스터와 클러스터가 읽을 수 있는 이미지가 필요합니다. 클러스터가 ACR을 아직 읽을 수 없다면 관리자와 `az aks update --resource-group "$AZURE_RESOURCE_GROUP" --name "$AKS_CLUSTER" --attach-acr "$ACR_NAME"` 실행 여부를 확인하세요. `infra/aks/deployment.yaml`의 이미지와 Foundry 리소스 이름을 바꾸고, Foundry API 키를 환경 변수로 설정한 다음 임시 환경 파일을 이용해 Secret을 만들고 매니페스트를 적용합니다.

```bash
az aks get-credentials --resource-group "$AZURE_RESOURCE_GROUP" --name "$AKS_CLUSTER"
read -rsp "Foundry API key: " ANTHROPIC_FOUNDRY_API_KEY; echo
read -rsp "Demo UI password: " DEMO_PASSWORD; echo
secret_file="$(mktemp)"
chmod 600 "$secret_file"
trap 'rm -f "$secret_file"; unset ANTHROPIC_FOUNDRY_API_KEY DEMO_PASSWORD' EXIT
printf '%s=%s\n' 'api-key' "$ANTHROPIC_FOUNDRY_API_KEY" > "$secret_file"
printf '%s=%s\n' 'demo-password' "$DEMO_PASSWORD" >> "$secret_file"
kubectl create secret generic foundry-credentials --from-env-file="$secret_file"
rm -f "$secret_file"
trap - EXIT
unset ANTHROPIC_FOUNDRY_API_KEY DEMO_PASSWORD
kubectl apply -f infra/aks/
kubectl port-forward service/cloud-copilot-demo 8080:80
```

`kubectl port-forward`를 실행한 상태에서 `http://localhost:8080`을 열고 사용자 이름 `demo`와 UI 비밀번호로 로그인합니다. ClusterIP는 외부에 공개되지 않습니다. Kubernetes Secret은 클러스터 RBAC 및 etcd 암호화 설정에 따라 보호 수준이 달라집니다. 실제 환경에서는 Key Vault 연동과 etcd 암호화를 확인하세요. 실습 후 `kubectl delete -f infra/aks/` 및 `kubectl delete secret foundry-credentials`로 앱과 Secret을 삭제합니다. 클러스터 자체가 필요 없다면 전용 Azure 리소스도 별도로 삭제하세요.

## 발표 자료

- [한국어 PPT 발표자 가이드](DEMO_GUIDE_KO.md)
- [슬라이드 원본](slides/demo-presentation-ko.md)
- [PowerPoint 파일](slides/demo-presentation-ko.pptx)

각 데모는 기존 GitHub/Azure 환경을 활용합니다. 이 저장소는 Azure 구독, Foundry 모델 배포, AKS 클러스터를 자동 생성하지 않습니다.

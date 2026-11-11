# Demo 4 — Microsoft Foundry: Model Choice and Keyless, Secure Connections

Deploy gpt-6.1-sol to Microsoft Foundry and show the same app code calling the model through Microsoft Entra ID, without an API key. The authentication code is identical locally, on Container Apps and on AKS. The only thing that changes is who is signed in.

> **Language**: The app and the scripts in this repository are in Korean. This guide names their labels and messages in English; the Korean text is listed in [Language of the app and the scripts](../../README.md#language-of-the-app-and-the-scripts).

## At a glance

| Item | Details |
|---|---|
| Goal | Show the flow in one pass: deploy the model (gpt-6.1-sol) → call it locally without a key → check the authentication method, model and effort in `/api/info`. Then explain how to change the model settings by changing only the deployment name and the effort. |
| Time | About 7 minutes. Finish the deployment before the demo. |
| Difficulty | Medium |
| Standalone | Yes. You only need an Azure subscription. GitHub, Container Apps and AKS are not needed. |

```text
az login ─▶ DefaultAzureCredential ─▶ Entra ID token (scope: https://ai.azure.com/.default)
        ─▶ https://<resource>.services.ai.azure.com/openai/v1/ ─▶ gpt-6.1-sol (effort=max → xhigh)
```

## Why this service (benefits)

- **Use models inside Azure governance**: Microsoft Entra ID authentication, Azure RBAC, subscription quotas and regions, and resource tags apply the same way as for other Azure resources. You do not need a separate system for managing external API keys.
- **Keyless authentication**: The caller holds no secret. Locally `az login`, on Container Apps a Managed Identity, and on AKS a Workload Identity get a token with the same code (`DefaultAzureCredential`). The only role you need is `Cognitive Services User`, which is just for calling models.
- **Swap models by deployment name**: The app knows only the Foundry **deployment name** (`FOUNDRY_MODEL`), not the model ID. Deploy another model and change only the name to swap it, with no code change.
- **Deep reasoning with `effort=max`**: Choose among `low`, `medium`, `high`, `xhigh` and `max` with `FOUNDRY_EFFORT`. gpt-6.1-sol has no `max`, so the app sends `reasoning_effort=xhigh` (and `/api/info` also shows `xhigh`), while Claude uses `output_config={"effort": "max"}` as it is. Thinking deeper can improve answers, but it uses more time and tokens.
- **You can turn key authentication off completely**: If you deploy with `DISABLE_LOCAL_AUTH=true`, API key authentication is turned off and only Entra ID is allowed.
- **Deployment as code**: The account, the project, the model deployment and the terms acceptance are in `infra/foundry/main.bicep`, so it is easy to recreate or clean up the same environment.

## Prerequisites

1. **Azure subscription**: For gpt-6.1-sol, a subscription with model quota is enough. Supported regions are `eastus2`, `swedencentral` and `westus2`, and this demo's default is `swedencentral`. To use Claude, you need an Enterprise or MCA-E subscription that can make Marketplace purchases (Microsoft internal subscriptions are rejected with `UnsupportedForInternalSubscription`).
2. **Anthropic terms (only when you use Claude)**: Deploying with `MODEL_NAME=claude-sonnet-5-5` counts as accepting Anthropic's commercial terms, and you must pass your organization name in `CLAUDE_ORGANIZATION_NAME`. This does not apply to gpt-6.1-sol.
3. **Tools**: `az` (sign in with `az login`), Python 3.12 and `bash` 4 or later (on macOS, `brew install bash`).
4. **Python dependencies**:

   ```bash
   python -m pip install --requirement app/requirements.txt
   ```

5. **Foundry deployment** (it takes a few minutes, so do it before the demo):

   ```bash
   scripts/deploy-foundry.sh            # answer y to the confirmation. Use --yes to skip the question.
   ```

   The `Cognitive Services User` role is granted to the signed-in user automatically, and the connection settings are saved in `.azure/foundry.env` (ignored by `.gitignore`). To give permission to another user, set `PRINCIPAL_ID` and `PRINCIPAL_TYPE`. You can also deploy directly in the portal (ai.azure.com), but this guide describes the script.

## Demo steps

> Portal menu names may change. Text in angle brackets (`<>`) is a placeholder for your own value.

### 1. Check the deployed model (about 1.5 min)

1. In a terminal, show what you just created.

   ```bash
   cat .azure/foundry.env               # FOUNDRY_RESOURCE, FOUNDRY_MODEL (the deployment name) and so on. No secrets.
   source .azure/foundry.env
   az cognitiveservices account deployment list \
     --resource-group "$FOUNDRY_RESOURCE_GROUP" --name "$FOUNDRY_RESOURCE" \
     --query "[].{Name:name, Model:properties.model.name, Capacity:sku.capacity}" --output table
   ```

2. In the portal (ai.azure.com), open the project and show the same model deployment. You can see the deployment name, the model and the capacity (in units of 1K TPM).
3. Explain the endpoint shape: `https://<resource>.services.ai.azure.com/openai/v1/` (for Claude, `.../anthropic/`).

Success criteria: The deployment list has `gpt-6.1-sol`, and the audience can see that `.azure/foundry.env` has no API key.

### 2. Call it locally without a key (about 2.5 min)

```bash
az login                                  # skip this if you already did
source .azure/foundry.env                 # LLM_BACKEND=foundry, FOUNDRY_RESOURCE, FOUNDRY_MODEL
export DEMO_PASSWORD='<any password>'     # password for the demo UI. Do not put it in the repository.
python -m app.server                      # http://127.0.0.1:8080  (user: demo)
```

1. Open `http://127.0.0.1:8080` in a browser and sign in with the user `demo` and the password above.
2. Ask a question. For example: "Which fits an internal API run by a team of two, Azure Container Apps or AKS? Explain your reasoning."
3. Show that the code has no key. If `FOUNDRY_API_KEY` (or `ANTHROPIC_FOUNDRY_API_KEY`) is not set, the app uses the token of the `az login` account through `DefaultAzureCredential`.

If the role was just granted, propagation can take a few minutes, so the first call may fail with a permission error. Try again after a short while.

Success criteria: The model returns an answer, and the screen shows the instance and the version that answered.

### 3. Check the authentication method, model and effort in `/api/info` (about 1.5 min)

Check them with the info chips at the top of the page or with the command below.

```bash
curl -s -u "demo:$DEMO_PASSWORD" http://127.0.0.1:8080/api/info
```

Success criteria: The response contains `"backend": "foundry"`, `"auth": "entra-id"`, `"model": "gpt-6.1-sol"` and `"effort": "xhigh"`. (With the mock backend, it shows `"auth": "none"`.)

### 4. (Optional) Change the effort and the model deployment (about 1.5 min)

Stop the app (Ctrl+C) and restart it with only an environment variable changed. The code stays the same.

```bash
FOUNDRY_EFFORT=low python -m app.server      # compare the depth and latency of the answer to the same question with max (xhigh)
```

To switch to another model, add a new deployment and point to its name only. Check the available model names in the portal's model catalog. More deployments use more quota.

```bash
MODEL_NAME="<other model name>" MODEL_VERSION="<model version>" scripts/deploy-foundry.sh --yes   # adds one more deployment to the same account
source .azure/foundry.env                                              # FOUNDRY_MODEL changes to the new deployment name
python -m app.server
```

(Optional) To show key authentication turned off, deploy again with `DISABLE_LOCAL_AUTH=true scripts/deploy-foundry.sh --yes`. After that, a call with an API key is rejected and only Entra ID calls pass. Every path in this demo uses Entra ID, so the app behaves the same.

Success criteria: `/api/info` of the app started with `FOUNDRY_EFFORT=low` shows `"effort": "low"`, and if you added a model deployment, `model` has changed to the new deployment name. You did not change a single line of code.

## Talking points

- **"There is no key in the app code."** The same image gets the same kind of token with `az login` locally, a Managed Identity on Container Apps and a Workload Identity on AKS. Entra ID and Azure RBAC record and control who is calling.
- **Least privilege**: Inference calls need only `Cognitive Services User`. You do not need the permission to change account settings.
- **The model is a setting.** The code knows only one deployment name, and swapping models is done by changing the deployment and an environment variable.
- **Effort is a dial between cost and quality.** `max` (`xhigh` for GPT) reasons the deepest, but responses are slower and use more tokens. Lower it depending on the use.
- **Cost control**: Every call incurs token costs, and quota (in units of 1K TPM) sets the upper limit. Clean up when the demo is over, and purge as well to get the quota back.
- **Scope**: This demo uses the public endpoint. It does not cover network isolation such as private endpoints or firewalls.

## Cleanup

```bash
scripts/cleanup.sh foundry         # deletes the resource group and purges the deleted account to get the quota back (asks for confirmation)
rm -f .azure/foundry.env           # local connection settings
```

Resource groups without the `demo=ghcp-in-the-cloud` tag are not deleted. If you only delete a Foundry account, it stays in a "deleted" state for a while and holds the quota and the name, so `cleanup.sh` also purges it.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The deployment fails with a quota or capacity error | Reduce the capacity, for example `CAPACITY=10`, or choose another region, for example `LOCATION=eastus2`, and run it again. Check the subscription quota in the portal. |
| The Claude deployment is rejected with `UnsupportedForInternalSubscription` (Marketplace purchase not possible) | You need an Enterprise or MCA-E subscription. Check your subscription type. The kit's default model, gpt-6.1-sol, is not affected. |
| The app call returns `403` or a permission error | Wait a few minutes for the role to propagate. Also check that the user shown by `az account show` is the same user who ran `deploy-foundry.sh`. If not, grant the permission with `PRINCIPAL_ID=<object ID> scripts/deploy-foundry.sh --yes`. |
| `DefaultAzureCredential` fails to authenticate | Run `az login` again and check that you are in the right tenant (`az login --tenant <tenant>`). If variables such as `AZURE_CLIENT_ID` remain in the environment, `unset` them. |
| `404` or the deployment is not found | `FOUNDRY_MODEL` is the **deployment name**, not the model ID, and `FOUNDRY_RESOURCE` is the **resource name**, not the host name. Run `source .azure/foundry.env` and restart. |
| The error `모델이 텍스트 응답을 반환하지 않았습니다 (stop_reason=...)` (the model returned no text) | The reasoning used up all the tokens. Raise the limit, for example `FOUNDRY_MAX_TOKENS=8000` (256–16000), or lower `FOUNDRY_EFFORT`. |
| An error says the name is already in use when you deploy again | The previous account remains in a "deleted" state. Purge it with `scripts/cleanup.sh foundry`, or run `az cognitiveservices account purge --name <account> --resource-group <group> --location <region>`. |
| Key authentication does not work | The account was deployed with `DISABLE_LOCAL_AUTH=true`. Use Entra ID (`az login`). |

## Using it with other demos

This demo runs end to end on its own. Using it with the others shows the connections.

- **Demo 5 (Container Apps)**: If you run `source .azure/foundry.env` and then `scripts/deploy-aca.sh` in the same shell, the app calls gpt-6.1-sol in this Foundry instead of mock. The app's Managed Identity gets the `Cognitive Services User` role.
- **Demo 6 (AKS)**: If you run `scripts/deploy-aks.sh` the same way, the pod calls Foundry with a Workload Identity. There are no secrets anywhere.
- **Demo 1 (GitHub Copilot)**: When you demo an issue where Copilot-written code changes `/api/chat` of this app, this Foundry connection lets you check the result with real model responses.

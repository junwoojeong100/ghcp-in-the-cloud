# Demo 5 — Azure Container Apps: Serverless Containers, scale-to-zero and Revision Canary

Serve a container app over HTTPS without operating a cluster. When there are no requests, the replicas drop to zero. You roll out a new version as a revision, split traffic to it, and then promote it all at once or roll back immediately.

> **Language**: The app and the scripts in this repository are in Korean. This guide names their labels and messages in English; the Korean text is listed in [Language of the app and the scripts](../../README.md#language-of-the-app-and-the-scripts).

## At a glance

| Item | Details |
|---|---|
| Goal | Show, in order: deploy → scale-to-zero and the cold start of the first request → a revision canary (0% → 10% → 100%, rollback) → scale-out under load. |
| Time | About 7 minutes. Finish the deployment and the idle wait before the demo. |
| Difficulty | Medium |
| Standalone | Yes. You only need an Azure subscription. The default is the `mock` backend, so it works without Foundry. Connecting Foundry is optional (Demo 4). |

```text
                ┌─ production URL ─▶ revision v1 (90%) ─┐
user ─ HTTPS ─▶ Ingress ────────────────────────────────┤ 0–5 replicas
                └─ label URL ──────▶ revision v2 (10%) ─┘ 1 replica per 5 concurrent requests (HTTP scale rule)
```

## Why this service (benefits)

- **No cluster to operate**: You do not manage nodes, upgrades or an ingress controller. Upload a container image and settings, and you get an HTTPS URL.
- **Scale-to-zero**: The minimum replica count is 0, so when there are no requests the replicas disappear and compute cost stops. When the next request arrives, a replica starts again. It fits apps with uneven usage patterns, such as internal tools or demos.
- **Revision-based traffic splitting**: Roll out a new version as a new revision, check it first through a label URL, and then send only part of the traffic to it. Canary and blue-green deployments, promotion and instant rollback are all done by changing settings.
- **Request-based autoscaling**: An HTTP scale rule adds replicas when there are more than 5 concurrent requests per replica (up to 5 replicas).
- **Keyless Foundry calls**: The user-assigned Managed Identity attached to the app gets the Foundry `Cognitive Services User` role and calls the model without secrets.
- **Built-in logs**: Console logs go to Log Analytics.

## Prerequisites

1. **Tools**: `az` (sign in with `az login`), `curl`, `python3` and `bash` 4 or later (on macOS, `brew install bash`). The script takes care of the `containerapp` extension and the required resource provider registrations.
2. **Azure permissions**: You need an account that can create resource groups and role assignments (subscription Owner, or Contributor plus User Access Administrator). This is because the infrastructure grants the registry read role (`AcrPull`) to the app's Managed Identity.
3. **Deployment** (it takes a few minutes, so do it before the demo):

   ```bash
   scripts/deploy-aca.sh                # answer y to the confirmation. Use --yes to skip the question.
   ```

   It creates the registry, the Managed Identity, Log Analytics and the Container Apps environment, builds the image and deploys the app. At the end it prints the **URL, the user and the password**, so write them down. To choose the password yourself, set `DEMO_PASSWORD`. The default resource group is `rg-cloud-copilot-aca` and the default region is `koreacentral`.

   To use a Foundry model, first do Demo 4, then run `source .azure/foundry.env` in the same shell and run this script.
4. **Prepare the demo shell**:

   ```bash
   export DEMO_PASSWORD='<the password printed by deploy-aca.sh>'
   APP_URL="https://$(az containerapp show --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
     --query properties.configuration.ingress.fqdn --output tsv)"
   echo "$APP_URL"
   ```

   If you deployed with different defaults (`RESOURCE_GROUP`, `APP_NAME`), pass the same values to `scripts/aca-canary.sh` as environment variables.
5. **To show scale-to-zero**, do not send any request to the app between the end of the deployment and the start of the demo (a browser tab and the smoke test count as requests too). After a few minutes with no requests, the replicas drop to 0.

## Demo steps

> Portal menu names may change. Text in angle brackets (`<>`) is a placeholder for your own value.

### 1. Scale-to-zero and the cold start (about 1.5 min)

Start from the state where you have sent no request since the deployment (prerequisite 5).

```bash
az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
  --query "[?properties.active].{Name:name, Traffic:properties.trafficWeight, Replicas:properties.replicas}" --output table
```

1. In the output of the command above, `Replicas` is `0`. No replica is running, so there is no compute cost. If the `Replicas` column looks empty, check the replica list with `az containerapp replica list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo --output table` (if there is no replica, the list is empty).
2. Send the first request. The response is slow because it waits for a replica to start.

   ```bash
   curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' "$APP_URL/healthz"   # first request: slow
   curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' "$APP_URL/healthz"   # second request: fast
   ```

3. Run the `az containerapp revision list` command above again, and `Replicas` is `1`.

Success criteria: The same request is noticeably slow the first time and fast the second time, and `Replicas` changes from 0 to 1. The latency depends on the environment, so do not promise a number. If you had no time to wait for the replicas to drop to 0, you can explain this step verbally and move on.

### 2. Check the deployment: the web UI and the smoke test (about 1 min)

1. In a browser, open `$APP_URL` and sign in with the user `demo` and the password. In the info chips, check **Platform** (`aca`), **Instance** (the replica name), **Revision**, **Version** and **Backend**.
2. Run the smoke test that CI uses, as it is, against the real deployment.

   ```bash
   scripts/smoke-test.sh "$APP_URL" --wait 60 --expect-backend mock
   ```

Success criteria: You can sign in over the HTTPS URL, all checks pass (`모든 확인(14개)을 통과했습니다.`, all 14 checks passed), and the Platform chip is `aca`. If you deployed with the Foundry backend, use `--expect-backend foundry`.

### 3. Revision canary: 0% → 10% → 100%, rollback (about 3 min)

```bash
scripts/aca-canary.sh status           # current traffic split, revisions and label URLs
scripts/aca-canary.sh deploy v2        # create the new revision v2 and attach it to an empty label. Traffic is 0%
scripts/aca-canary.sh canary 10        # 10% to v2, 90% to the previous revision
scripts/aca-canary.sh probe 30         # call the production URL 30 times and count the responses per version
scripts/aca-canary.sh promote          # switch 100% to v2
scripts/aca-canary.sh rollback         # return 100% to the previous revision (assume something went wrong)
```

1. `deploy v2` does not rebuild the image. It creates a new revision by changing only the environment variable `APP_VERSION=v2`. The first time you run it, it pins the current revision at 100% and attaches the `blue` label to it, and then it attaches the new revision to the `green` label URL (`https://<app>---green.<environment domain>`). With this URL you can check v2 before it receives production traffic.
2. After `canary 10`, click **Show traffic distribution (20 calls)** in the browser, and bars show the number of responses by revision, instance and version. `probe` shows the same thing as a table in the terminal. A 10% split is probabilistic, so with few calls the ratio drifts a little.
3. Switch to 100% with `promote`, and check with `probe` that every response comes from v2.
4. With `rollback`, the previous revision gets 100% again. The new revision stays, so you can promote it again at any time.
5. To see it in the portal, open **Revisions and replicas** of the container app.

Success criteria: Right after `deploy`, `status` shows v2 at 0% and the label URL returns v2's version. After `canary 10`, `probe` shows a mix of v1 and v2. After `promote`, only v2 appears, and after `rollback`, only the previous revision appears.

### 4. Scale out under load (about 1.5 min)

Use two terminals. Watch the replica count in Terminal A and generate load in Terminal B.

```bash
# Terminal A: print the replica count per revision every 5 seconds (stop: Ctrl+C)
while true; do
  az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo \
    --query "[?properties.active].{Name:name, Traffic:properties.trafficWeight, Replicas:properties.replicas}" --output table
  sleep 5
done
```

```bash
# Terminal B: load with 20 concurrent requests for 2 minutes
scripts/load-test.sh --url "$APP_URL" --duration 120 --concurrency 20
```

The mock backend waits about 1 second (`MOCK_LATENCY_MS`) for each response, so concurrent requests pile up, and when the concurrency per replica passes the threshold of 5, replicas are added. Scale-out takes time, so run the load long enough. When it finishes, it prints the number of requests, the count per HTTP status code, and the median and 95th percentile response times.

With the Foundry backend, load on `/api/chat` creates model call costs, so `load-test.sh` refuses it by default. In that case, load `--path /healthz`.

Success criteria: `Replicas` in Terminal A grows during the load, up to 5, and the result in Terminal B is mostly `HTTP 200` with no errors. A few minutes after the load ends, the replicas shrink again. You can also graph Replica Count under **Metrics** in the portal.

## Talking points

- **"There is no cluster."** Decide only the image, the port and the scale rules, and Container Apps operates the rest. A team with no Kubernetes knowledge can also serve containers.
- **Scale-to-zero is a cost model.** When the app is not used, there are no replicas, and the first request bears the cold start. For latency-sensitive services, you can keep the minimum replica count at 1 or more (`MIN_REPLICAS`).
- **Revisions are immutable.** A new version is a new revision and the old revision stays as it is, so a rollback is a change of traffic weights, not a redeployment.
- **Check first with the label URL, without production traffic.** Before the canary, you can go directly to v2.
- **Same image, same code.** The deploy workflow of Demo 3 rolls out a new revision of this app, and the authentication code is the same as locally and on AKS.
- **Cost**: With 0 replicas there is no compute cost, but items such as the registry and logs remain. Clean up when the demo is over.

## Cleanup

```bash
scripts/cleanup.sh aca             # deletes the Container Apps resource group (asks for confirmation)
```

Resource groups without the `demo=ghcp-in-the-cloud` tag are not deleted. To reset only the canary state, run `scripts/deploy-aca.sh` again with `DEMO_PASSWORD` set (it keeps the same password). If you run it with a different password, it restarts the active revision to apply it. The split is reset and the latest revision gets 100%.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The first request right after deployment takes long or fails | With a minimum replica count of 0, the first request starts a replica. The script waits for `/healthz` for up to about 3 minutes. If it keeps failing, check the logs with `az containerapp logs show --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo --type console`. |
| `Replicas` does not drop to 0 | Wait longer with no requests. If a browser tab is open, it may send requests that refresh the info, so close the tab. |
| `aca-canary.sh deploy` says `이미 있습니다` (already exists) | A revision with the same version name (`v2`) already exists. Use a new name such as `v3`. |
| `deploy` says `<레이블> 레이블이 이미 N% 의 트래픽을 받고 있습니다` (the `<label>` label already receives N% of the traffic) | The previous canary is not finished. Clean it up with `promote` or `rollback`, and then run `deploy` again. |
| `probe` says `DEMO_PASSWORD 환경 변수가 필요합니다` (the DEMO_PASSWORD environment variable is required) | Run `export DEMO_PASSWORD=...` as in prerequisite 4. If you forgot the password, check it with `az containerapp secret show --name cloud-copilot-demo --resource-group rg-cloud-copilot-aca --secret-name demo-password --query value --output tsv`. |
| `load-test.sh` refuses, or `HTTP 429` appears | With the Foundry backend, it refuses as cost protection (use `--path /healthz`). If you merged the rate limit (issue 01 of Demo 1), load on `/api/chat` can get `429`, so turn it off with the environment variable `RATE_LIMIT_PER_MINUTE=0` or use `--path /healthz`. |
| You do not see scale-out | Run the load longer (`--duration 180`) or raise the concurrency (`--concurrency 40`). The scale rule is 5 concurrent requests per replica. |
| After running `deploy-aca.yml`, the new revision is at 0% | A canary split is set. Check with `scripts/aca-canary.sh status` and run `promote`. |
| Unsupported region or SKU error | Change the region with `LOCATION=<another region> scripts/deploy-aca.sh`. |

## Using it with other demos

This demo runs end to end on its own. Using it with the others connects the story.

- **Demo 3 (GitHub Actions)**: `deploy-aca.yml` logs in with OIDC and rolls out a new revision of this app. In a canary state, the new revision is created at 0%, so it connects to the `promote` of this demo.
- **Demo 4 (Foundry)**: If you run `scripts/deploy-aca.sh` after `source .azure/foundry.env`, the app calls gpt-6.1-sol instead of mock, and the app's Managed Identity authenticates without secrets. Then `/api/info` shows `backend=foundry` and `auth=entra-id`.
- **Demo 6 (AKS)**: The same image also runs on AKS. Compare the two demos with the "Choosing between AKS and ACA" guide at the end of Demo 6.

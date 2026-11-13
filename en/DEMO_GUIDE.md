# Demo Guide — Cloud Copilot Demo

**English** · [한국어](../DEMO_GUIDE_KO.md)

A guide for presenters who show the demos while moving through the presentation slides. The step-by-step commands and screens are in the demo guides under [`demos/`](demos/). This guide focuses on how to combine the demos, in what order and timing, and what to prepare before the talk.

> Text in angle brackets (`<>`) is a placeholder for your own value. Portal menu names may change. If a screen looks different, search by the CLI command and the setting name given in the documents. The times are per-step targets from the documents, so measure them yourself in your first rehearsal and adjust.

## Choosing a course

| Course | Time | Contents | Best for |
|---|---|---|---|
| Full | About 42 minutes | Demo 1 → 2 → 3 → 4 → 5 → 6 | Overview sessions, workshops |
| Lite | About 15 minutes | Demo 1 → 3 → 4 → 5 (with fewer steps) | Short talk slots |
| Single | 6–8 minutes | One demo | Meetups focused on a specific service |

The presentation is the [45-slide recorded-demo deck](slides/README.md) with 32 embedded videos. Play a video on the relevant slide or run the demos yourself in the order below. The Full and Lite courses follow the order and estimated times in this guide, independently of the recorded videos' playback time.

The demo order follows the path of an app from being built to being operated: development (Copilot) → collaboration and security (Repo) → automation (Actions) → AI model (Foundry) → runtime (Container Apps) → scale and operations (AKS). You can show any demo on its own, so pick the ones that suit your audience. The accounts and subscriptions you need are in [the standalone matrix in the README](README.md#standalone-matrix).

## Full course (about 42 minutes)

| Elapsed time | Demo | Message to leave with the audience | What to show live |
|---|---|---|---|
| 0:00 (7 min) | [1. GitHub Copilot](demos/01-github-copilot/README.md) | Hand an issue to an AI teammate, control quality with repository instructions, and let a person approve. | Issue → the PR made by the agent → CI → Copilot code review |
| 0:07 (6 min) | [2. GitHub Repo](demos/02-github-repo/README.md) | Main protection and security settings are defined as code, so every PR, whoever opens it, passes the same rules. | Rulesets and CODEOWNERS, the risky PR caught by CodeQL and Dependency review |
| 0:13 (7 min) | [3. GitHub Actions](demos/03-github-actions/README.md) | Verify in parallel, deploy with OIDC and no stored secrets, and control deployment with environment approval. | The CI jobs, environment approval → OIDC login → a new revision |
| 0:20 (7 min) | [4. Microsoft Foundry](demos/04-microsoft-foundry/README.md) | The same code calls gpt-6.1-sol through Entra ID without an API key, and you change the model and the effort through settings. | A local call, `auth`, `model` and `effort` in `/api/info` |
| 0:27 (7 min) | [5. Azure Container Apps](demos/05-azure-container-apps/README.md) | Serve without a cluster, use scale-to-zero when idle, and do canary deployments with revisions. | Scale-to-zero, 0% → 10% → 100%, rollback, scale-out |
| 0:34 (8 min) | [6. AKS](demos/06-aks/README.md) | Update the same image on Kubernetes with zero downtime, autoscale it, and call Azure without secrets. | HPA, rolling update and rollback, Workload Identity |

Connecting the demos like this keeps the flow natural.

- 1 → 2: "A PR made by AI has to pass the same rules as a PR from a person. Let's see how the repository enforces those rules."
- 2 → 3: "The core of those rules is automated verification. Let's set up verification and deployment with Actions, without secrets."
- 3 → 4: "The app we deploy calls gpt-6.1-sol. Let's see how to make that connection keyless too."
- 4 → 5: "Now let's look at where to run this app. We start with Container Apps, which has the lowest operational burden."
- 5 → 6: "If you need finer control, there is AKS. The same image goes up as it is."

## Lite course (about 15 minutes)

Show only the key steps of each demo. The step numbers follow "Demo steps" in the guide of that demo.

| Demo | Steps to show | Time |
|---|---|---|
| 1. GitHub Copilot | Step 1 (tour the settings) → step 3 (the agent PR you prepared and its CI) → in step 4, the Copilot code review comments | About 4 minutes |
| 3. GitHub Actions | Step 2 (OIDC trust without secrets) → step 3 (approval → login → new revision, together with a run you started earlier) | About 4 minutes |
| 4. Microsoft Foundry | Step 2 (a local call without keys) → step 3 (`/api/info`) | About 3 minutes |
| 5. Azure Container Apps | Step 1 (scale-to-zero) → step 3 (canary 0% → 10% → 100%) | About 4 minutes |

The Lite course skips Demo 2 and Demo 6. If a question comes up, answer with the "Talking points" of that demo's guide.

## Before you present

### Up to one day before

- [ ] Accounts and permissions: Check your Azure subscription (Owner, or Contributor plus User Access Administrator), GitHub repository admin access and a Copilot license (with cloud agent access). gpt-6.1-sol only needs quota (an Enterprise or MCA-E subscription is needed only if you use Claude; see [Demo 4](demos/04-microsoft-foundry/README.md)).
- [ ] Tools: Install bash 4 or later, Python 3.12, `az`, `gh` (`gh auth login`), `jq`, `kubectl` and `kubelogin` (`az aks install-cli`), and `docker` (optional).
- [ ] Create a new practice repository. Run the scripts that change rulesets and security settings and open PRs on the practice repository, not on the source. If you use the source as a template, every run starts clean: `gh repo create <owner>/<name> --template junwoojeong100/ghcp-in-the-cloud --public --clone`. A fork works too. If you make it private, first check whether your plan lets you use rulesets and code scanning.
- [ ] Rehearse once from start to finish. This kit was checked with static checks and local runs, and the six demos were deployed to Azure from a practice repository, run end to end and recorded. Check once more with your own subscription and permissions.

### 30–60 minutes before the demo (in one shell, in order)

```bash
az login
scripts/deploy-foundry.sh              # Demo 4, a few minutes
scripts/deploy-aca.sh                  # Demo 5, note the printed URL and password
scripts/deploy-aks.sh                  # Demo 6, 5–10 minutes. Note the printed password
scripts/setup-github-oidc.sh --apply   # Demo 3, the deployment targets must exist first
```

In the order above, `deploy-aca.sh` and `deploy-aks.sh` deploy with the `mock` backend. That is enough for the purpose of Demos 5 and 6 (scaling, canary, rolling update), it has no model call cost, and the screen also shows `mock`. For Demo 4, run `source .azure/foundry.env` in a separate terminal and demo with the local app. To connect the deployed apps to the Foundry model as well, run `source .azure/foundry.env` in the same shell before you run `deploy-aca.sh` or `deploy-aks.sh`. In that case, run the smoke test with `--expect-backend foundry` and the load test with `--path /healthz` (see [Demo 5](demos/05-azure-container-apps/README.md)). If you do not use Foundry, also skip the `scripts/deploy-foundry.sh` line.

These are the things to do ahead of time for each demo.

| Demo | What to do ahead of time |
|---|---|
| 1 | 10–15 minutes before the demo, assign one issue to Copilot with `scripts/create-demo-issues.sh --apply --assign-copilot`. The agent takes a few minutes to work. |
| 2 | Create one Codespace, and apply the ruleset, labels and the environment with `scripts/apply-repo-settings.sh --apply`. Check that `ci.yml` has run at least once on main, and open the risky PR in advance so you have the screen after the CodeQL analysis has finished. |
| 3 | To show the approval step, set an approver with `scripts/apply-repo-settings.sh --apply --only environment --reviewer <your GitHub user name>`. Run the deploy workflow once. |
| 4 | Run `python -m pip install --requirement app/requirements.txt`, and check once that a local call works. Role propagation can take a few minutes. |
| 5 | After the deployment is finished, do not send any request to the app. A browser tab and the smoke test are requests too, so do not open them until right before the demo, so that you can show scale-to-zero. Prepare `APP_URL` and `DEMO_PASSWORD` in the shell. |
| 6 | Build the v2 image in advance, and check that 2 or more pods are `Running` with `kubectl get pods --namespace cloud-copilot-demo`. Prepare three terminals (commands, watch and port forwarding). |

### The last 5 minutes before the demo

- [ ] Open the repository's [45-slide English recorded-demo deck](slides/GHCP_in_the_Cloud_Demo_EN.pptx), `en/slides/GHCP_in_the_Cloud_Demo_EN.pptx`. Check the slides you need and each video's picture, sound and playback.
- [ ] Increase the terminal font size and open the tabs you will use for the demo in advance. Turn off notifications.
- [ ] Only `export` `DEMO_PASSWORD` and do not print it on screen. Do not share a window that shows the password.
- [ ] In the browser, stay signed in to GitHub and the Azure portal, and keep only the tabs you need.
- [ ] Think through the fallback demos below in case the network drops.

## Tips during the demo

- **Run long tasks ahead of time.** For the agent work, the CodeQL analysis, and the cluster and image builds, open the result screen first and continue with "this is how it ends", and the flow does not break. For a task you start live, do not wait for it to finish; keep explaining and come back to it.
- **Say the "Success criteria" of each demo out loud.** It makes clear to the audience what they are looking at.
- **Do not hide the mock backend.** If the backend chip on the screen says `mock`, say "to show scaling and deployment, the model call is simulated", and show the real model call in Demo 4.
- **Effort `max` can be slow.** If time is tight, run with a lower `FOUNDRY_EFFORT` (step 4 of Demo 4) and explain that it is slower because it reasons more deeply.

## If something goes wrong (fallback demos)

| Situation | What to do |
|---|---|
| The Copilot cloud agent has not finished yet | Move to the agent PR screen you prepared in advance and explain CI and the review. |
| The Azure deployment fails or is too slow | Start the local app with `LLM_BACKEND=mock DEMO_PASSWORD=<temporary value> python -m app.server` and show `scripts/smoke-test.sh`. Explain the deploy scripts with `--help` and the Bicep files (`infra/`). |
| The Foundry call fails | Check the table in the [troubleshooting section of Demo 4](demos/04-microsoft-foundry/README.md#troubleshooting). If you have no time, switch to `LLM_BACKEND=mock` and explain Foundry with the slides. |
| The network is unstable | Go on with the local mock app, the output of the scripts that are dry-run by default (`scripts/apply-repo-settings.sh`, `scripts/setup-github-oidc.sh`) and the slides. |
| The canary or deployment state is tangled | Check the state with `scripts/aca-canary.sh status` and go back with `rollback`. Running `scripts/deploy-aca.sh` again also resets the traffic split. |

## After the demo

```bash
scripts/cleanup.sh all                 # answer y to the confirmation. Use --yes to skip the question
```

- It deletes the Azure resources this kit created (Container Apps, AKS, Foundry, the Managed Identity for GitHub Actions and the `azure-demo` environment variables). To delete only some of them, specify `aca`, `aks`, `foundry` or `oidc`. AKS nodes are billed continuously, so we recommend deleting them right after the demo.
- Do not merge the risky PR of Demo 2. Close it and delete the branch (see "정리" (Cleanup) in `demos/02-github-repo/risky-pr/pr-body.md`, which is in Korean).
- Delete the practice repository altogether; that is the cleanest (`gh repo delete <owner>/<name>`; if you get a permission error, run `gh auth refresh -s delete_repo`). Check the name carefully so you do not delete the source. If you keep it, clean up the demo issues and the Codespace.

## Related documents

- [README](README.md): the project introduction, the quick start, the endpoints and the environment variables
- [`demos/`](demos/): the demo guide for each demo (At a glance, Prerequisites, Demo steps, Talking points, Cleanup, Troubleshooting)
- [`slides/`](slides/): the presentation slides (PPTX), the speaker notes and the per-slide script (Markdown)

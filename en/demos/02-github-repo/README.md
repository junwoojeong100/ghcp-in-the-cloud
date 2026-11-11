# Demo 2 — GitHub Repo: Safe Collaboration by Default with Rulesets, Security and Codespaces

Protection for the main branch, code owners, and code and supply-chain security checks are all defined as files and scripts inside the repository. A new contributor gets a runnable development environment in Codespaces with a few clicks. At the end, you open a PR that is risky on purpose and show the automated checks catching it.

> **Try it on a practice repository first**: The script in step 2 changes repository settings (security features, the ruleset and merge options), and the script in step 3 opens a PR. Both scripts are dry-run by default, but rehearse once on a practice repository (create one from the template, or fork) before your talk.

## At a glance

| Item | Details |
|---|---|
| Goal | Show that repository protection and security settings are defined as code, that a new contributor can start right away in Codespaces, and that a risky PR is caught by the automated checks. |
| Time | About 6 minutes (step 1: 1 min, step 2: 2 min, step 3: 2 min, step 4: 1 min). Creating a Codespace, applying the ruleset and the CodeQL analysis of the risky PR each take a few minutes, so prepare them before the demo. |
| Difficulty | Medium. Applying the ruleset and the security settings needs repository admin access. |
| Standalone | Yes. You only need a GitHub repository. No Azure subscription is needed. A Copilot license is needed only to see Copilot code review in step 3. |

```text
Open Codespaces → run tests → review and apply the ruleset and CODEOWNERS → risky PR → CodeQL, Dependency review and Copilot review → check Dependabot
```

| Path | Role |
|---|---|
| `.github/rulesets/main-protection.json` | Ruleset that protects main. JSON that you can import into GitHub as is |
| `.github/CODEOWNERS` | Review owners per path |
| `.github/dependabot.yml` | Dependency update settings |
| `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/config.yml` | The PR template, and blocking blank issues with a link to the guidance |
| `.devcontainer/` | Codespaces and Dev Container settings, `post-create.sh` |
| `scripts/apply-repo-settings.sh` | Applies security features, labels, the environment, the ruleset and merge options in one go (dry-run by default) |
| `demos/02-github-repo/risky-pr/` | Kit that creates the risky PR: `make-risky-pr.sh`, three `.sample` files and the PR body |

The checks themselves are run by `ci.yml`, `codeql.yml` and `dependency-review.yml` in `.github/workflows/`. These are shared repository files that other demos use too, so they are not in the table above.

## Why this service (benefits)

- **Protection for main (Rulesets)**: The default branch changes only through PRs, and a change merges only after it passes the approval, required check and code scanning conditions. Deletion and force push are blocked.
- **Separation of responsibility (CODEOWNERS)**: The owner of a path that a PR changes becomes a reviewer automatically, and together with the ruleset that approval becomes mandatory.
- **Code and supply-chain security**: CodeQL reports vulnerabilities in code and workflows, and Dependency review reports known vulnerabilities in the dependencies a PR adds, both before the merge. Dependabot opens PRs for dependency updates on a schedule. Secret scanning finds secrets in the repository and reports them, and push protection blocks a push that contains a secret before it reaches the repository.
- **AI-assisted review (Copilot code review)**: AI leaves a first review on each PR so that human reviewers can focus on the key decisions. A person still approves.
- **Fast start (Codespaces and dev container)**: A new contributor gets an environment with Python 3.12, the Azure CLI, the GitHub CLI, kubectl and Docker in a few clicks. There is nothing to install locally, and there are no secrets in the repository.
- **Settings as code**: The ruleset JSON and `apply-repo-settings.sh` turn repository settings into files. You can review a settings change in a PR, take it to another repository, and apply it again any number of times with the same result.

## Prerequisites

Text in angle brackets (`<>`) is a placeholder for your own value.

1. **Repository admin access and a practice repository**: Changing the ruleset, security features and environments needs repository admin access. Use a practice repository that you created from this repository as a template or forked (the command to create one is in the checklist of [DEMO_GUIDE.md](../../DEMO_GUIDE.md)). The scripts target the `origin` of the current folder, and you can change that with `--repo <owner>/<name>`. In a practice repository, replace `@junwoojeong100` in `.github/CODEOWNERS` with your own account (or team). A code owner must have write access to the repository to take effect.
2. **Terminal tools**: You need `git`, `jq` and a signed-in `gh` (`gh auth login`). Step 3 pushes a branch that contains a new workflow file, so your login token needs the **`workflow` scope**. If `workflow` is missing from Token scopes in `gh auth status`, add it with `gh auth refresh --scopes workflow`.
3. **Development environment**: Step 1 runs in Codespaces. To run it locally, Python 3.12 and `git` are enough.
4. **Shared workflows on the default branch**: `ci.yml`, `codeql.yml` and `dependency-review.yml` must be on main and run on every PR, otherwise the required checks and the code scanning rule have no meaning. Start with all the files of this demo merged into main.
5. **Copilot license (optional)**: To see Copilot code review, the person who opens the PR must be able to use Copilot. The usage of the ruleset's automatic review is charged to the PR author by default. Without a license, explain that part verbally.
6. **Plan**: In a public repository you can use rulesets, secret scanning, code scanning (CodeQL) and Dependency review. In a private repository, some of them may be limited depending on your plan and security product setup, so check the GitHub documentation.

### 10–15 minutes before the demo

- [ ] Create one Codespace. If you start with it already created, there is no waiting time.
- [ ] Run `--apply` of step 2 ahead of time so the ruleset, labels and the environment are ready. In front of the audience you only need to show the dry-run and the result screens.
- [ ] Check that `ci.yml` has run at least once on main. The required check names of the ruleset appear in the selection list only after they have a run history.
- [ ] Open the PR of step 3 in advance and prepare the screen after the CodeQL analysis has finished. If you create it live, you wait a few minutes for the analysis to finish.

## Demo steps

> Portal menu names may change. (For example, the Security tab may appear as Security and quality.)

The **Success criteria** at the end of each step list what you should see when it works. Run commands from the repository root.

### 1. Open in Codespaces and run the tests (about 1 min)

1. On the repository page, click **Code → Codespaces → Create codespace on main**. To set the app login password in advance, choose **New with options** from the `⋯` menu at the top right of the Codespaces tab and enter a temporary demo value in the `DEMO_PASSWORD` field. You can skip this.
2. When the Codespace opens, this README opens automatically. `.devcontainer/post-create.sh` installs `app/requirements.txt` and prints the tool versions and hints for the next steps in the terminal.
3. Run the tests.

   ```bash
   python -m unittest discover -s app/tests -v
   ```

4. Run the app in mock mode. It runs without Azure or Foundry.

   ```bash
   export DEMO_PASSWORD='<temporary demo value>'   # skip if you set it as a Codespaces secret
   LLM_BACKEND=mock python -m app.server
   ```

   Replace `<temporary demo value>` with a temporary value that the presenter chooses. Do not write the value in the repository or in docs.
5. Open a new terminal and check.

   ```bash
   curl -s http://localhost:8080/healthz
   curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/
   ```

   Open the link for port 8080 in the PORTS tab and a login dialog appears. The user name is `demo`, and the password is the value you chose above.

The Codespace comes with Python 3.12, the Azure CLI (with Bicep), the GitHub CLI, kubectl, Docker and the VS Code extensions (Copilot, Python, Bicep, GitHub Actions, Docker, Kubernetes) preinstalled. The same check tools as CI (actionlint, kubeconform, hadolint) are installed too when possible. Point out that nothing was installed locally.

Success criteria:

- The last line of the test output is `OK`.
- The server log shows `Listening on http://127.0.0.1:8080 (backend=mock)`.
- `/healthz` returns `{"status": "ok"}`, and calling `/` without authentication returns `401`.
- The PORTS tab shows 8080 forwarded with the name `Cloud Copilot Demo`.

### 2. Review Rulesets and CODEOWNERS, then apply the settings (about 2 min)

Open `.github/rulesets/main-protection.json`. Every rule has a reason.

| Rule | Setting | Why it is needed |
|---|---|---|
| Target | The default branch (`~DEFAULT_BRANCH`), `enforcement: active` | Follows the default branch even if it is not named `main`. |
| `deletion` | Deletion blocked | Prevents the accident of deleting the default branch. |
| `non_fast_forward` | Force push blocked | Prevents overwriting history and losing the change record. |
| `pull_request` | 1 approval, existing approvals are dismissed when new commits are pushed, code owner review required, review conversations must be resolved | Every change goes through another person's eyes, and code that changed after approval is not merged without review. `require_last_push_approval` (approval from someone other than the person who made the last push) is turned off to allow single-person demos. In a team repository, we recommend turning it on. |
| `required_status_checks` | `Unit tests`, `Container build and smoke test`, `IaC validation`. `strict` on, `integration_id` 15368 | A PR cannot merge until these three checks pass. `strict` means the PR must pass the checks while it contains the latest main. `integration_id` is the ID of the GitHub Actions app; it keeps an external status with the same name from posing as a required check. |
| `code_scanning` | Tool `CodeQL`, alerts threshold `errors`, security alerts threshold `high_or_higher` | A PR cannot merge if it has alerts at or above the threshold, if the analysis has not finished yet, or if the tool is not configured. This is the rule that blocks the risky PR of step 3. |
| `copilot_code_review` | Review on every push off, review of draft PRs off | Copilot reviews automatically when a PR is opened. Not repeating on every push and not reviewing drafts reduces noise and usage. |
| `bypass_actors` | Repository Admin role, mode `pull_request` | See "Compromise for a single-person repository" below. |

Copilot's review does not count toward the required number of approvals by default, so a person's approval is still needed. Details on each rule are in [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

**Compromise for a single-person repository**: The PR author cannot approve their own PR, and a code owner review is also required, so in a repository you use alone you cannot merge your own PR. That is why the repository Admin role has a bypass in `pull_request` mode. This mode allows the bypass only for merges through a PR, so direct pushes and branch deletion are still blocked. However, the bypass applies to the whole ruleset, so an admin can also skip the required checks and the code scanning condition. For that reason you **never merge** the risky PR of step 3, even if the merge box shows a bypass option. In a team repository, empty `bypass_actors` or narrow it to an emergency role.

**CODEOWNERS**: `.github/CODEOWNERS` assigns `@junwoojeong100` as the owner of `*`, `/app/`, `/infra/`, `/.github/`, `/slides/` and `/demos/`. The last matching pattern wins. When a PR changes one of those paths, the owner becomes a reviewer automatically, and because of the ruleset's code owner review rule, that approval is required to merge. In a real team, use `@org/team` instead of an individual. The team also needs write access to the repository. For the syntax, see [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

**PR template and issue settings**: `.github/PULL_REQUEST_TEMPLATE.md` makes the PR body include a change summary, the change type, how it was verified and the result, a security checklist (no secrets, least privilege, input validation), the impact on docs and slides, and the related issue (`Closes #`). `.github/ISSUE_TEMPLATE/config.yml` blocks blank issues so that only the issue forms are used.

Now apply these settings to the repository.

```bash
scripts/apply-repo-settings.sh            # dry-run: prints only the gh api calls it would make
scripts/apply-repo-settings.sh --apply    # apply for real (needs repository admin access)
```

| Step | What it does |
|---|---|
| `security` | Turns on Dependabot alerts (including the dependency graph) and security updates, secret scanning and push protection. It does not turn on CodeQL "default setup", because this repository provides its own `codeql.yml`. |
| `labels` | Creates the `dependencies` and `copilot-demo` labels only if they do not exist. Dependabot PRs and the Demo 1 issues use them. |
| `environment` | Creates the `azure-demo` environment only if it does not exist. With `--reviewer <GitHub user name>`, it sets the deployment approver. |
| `ruleset` | Finds `main-protection.json` by name, updates it (PUT) if it exists and creates it (POST) if not. |
| `merge` | Allows only squash merge, deletes the branch automatically after the merge, and allows auto-merge and the "Update branch" button. |

Options: `--repo <owner>/<name>` (the target repository), `--only <step,...>` (run only some steps, for example `--only ruleset`), and `--core-rules-only` (leaves `code_scanning` and `copilot_code_review` out of the ruleset). `--apply` needs admin access. The default token in a Codespace may not be enough, so run it from a local terminal, or in the Codespace run `unset GITHUB_TOKEN` and then sign in with `gh auth login`. To use the UI instead of the script, you can upload the JSON file at **Settings → Rules → Rulesets → New ruleset → Import a ruleset**, which creates the same ruleset.

Success criteria:

- The dry-run prints five sections (`== security`, `== labels`, `== environment`, `== ruleset`, `== merge`) with the `$ gh api ...` calls it would make, and ends with `dry-run이 끝났습니다.` (dry-run finished).
- `--apply` marks each step with `-> 완료` (done) and ends with `모든 단계를 적용했습니다.` (all steps applied).
- **Settings → Rules → Rulesets** shows `main-protection` as Active, and **Settings → Advanced Security** shows Dependabot alerts and security updates, secret scanning and push protection turned on.
- `gh label list` shows `dependencies` and `copilot-demo`, and **Settings → Environments** shows `azure-demo`.

### 3. Create the risky PR (about 2 min)

The default token in Codespaces may not be able to push workflow files, so it is safer to do this step in a local terminal. Run it on the main branch with a clean working tree.

```bash
git switch main && git pull --ff-only
demos/02-github-repo/risky-pr/make-risky-pr.sh             # dry-run: prints only what it would do
demos/02-github-repo/risky-pr/make-risky-pr.sh --apply     # push the branch and open the PR
```

`--apply` creates and pushes the `demo/risky-change` branch and opens a PR whose title starts with `[DEMO – DO NOT MERGE]`. It does not push to the default branch, and if the working tree is not clean or HEAD is ahead of the origin's default branch, it stops without changing anything. If you do not have permission to push workflow files, `--no-workflow` leaves `triage.yml` out.

| Sample (under `risky-pr/`) | Where it is copied in the PR branch | Problem added on purpose | Expected detection |
|---|---|---|---|
| `app/extras/debug_files.py.sample` | `app/extras/debug_files.py` | Builds a file path from a request value (path injection), inserts a request value into a shell command (command injection), Flask debug mode | CodeQL (Python): `py/path-injection`, `py/command-line-injection`, `py/flask-debug` |
| `app/extras/requirements.txt.sample` | `app/extras/requirements.txt` | `flask==2.2.4`, which has a known vulnerability | Dependency review: GHSA-m2qf-hxjv-5gpq (CVE-2023-30861, high) |
| `.github/workflows/triage.yml.sample` | `.github/workflows/triage.yml` | Inserts an issue title directly into `run:` (expression injection) | CodeQL (Actions): `actions/code-injection/critical` |

The samples have the `.sample` extension so that CodeQL, the dependency graph and linters on main do not look at these files. That is why main has no vulnerable code, and the script copies the files only on the PR branch, with `.sample` removed from the name. All of them are new files, so existing code is untouched.

On the PR page (the URL on the last line of the script output), look at these in order:

1. At the bottom, in the check list, look at `Unit tests`, `Container build and smoke test` and `IaC validation` of `CI`.
2. When `Analyze (python)` and `Analyze (actions)` finish, code scanning alerts appear as annotations in **Files changed**.
3. In the summary of the `Dependency review` check, look at the high-severity vulnerability in `flask 2.2.4`.
4. Check whether Copilot code review has left comments.
5. In the merge box, read why the merge is blocked.

**Explain secret scanning and push protection verbally.** Keeping a string that looks like a secret in the repository is itself risky, so this repository contains no token-shaped strings, and the demo does not create any. Explain it like this: push protection blocks a push that contains a supported secret before it reaches the repository, and tells you which secret is where. The developer removes the secret and pushes again. It applies not only to CLI pushes but also to web UI commits, file uploads and REST API requests. A person with write access can bypass it with a reason, and the bypass is recorded as an alert. To try it yourself, follow [the official documentation](https://docs.github.com/en/code-security/concepts/secret-security/push-protection).

Success criteria:

- The three required checks are green, because the app does not import the added files.
- CodeQL reports the alerts in the table above. The alert list is an "expected result" that can vary with the CodeQL query version. At the time of writing, we confirmed four of them locally with CodeQL bundle 2.27.4 (`py/path-injection`, `py/command-line-injection`, `py/flask-debug` and `actions/code-injection/critical`).
- `Dependency review` fails and shows `flask 2.2.4` and GHSA-m2qf-hxjv-5gpq, because `dependency-review.yml` uses `fail-on-severity: high`. It is not a required check, so this check alone does not block the merge.
- Copilot's review comments appear. If they do not appear automatically, request Copilot under **Reviewers** on the right of the PR.
- The merge box says that the code scanning condition and the code owner approval are not met, so you cannot merge. Admins may see a bypass option, but do not use it.
- The `Workflow and script lint` job may fail because it flags the use of untrusted input in `triage.yml`. It is not a required check, so it does not affect the merge conditions.

### 4. Check Dependabot (about 1 min)

1. Open `.github/dependabot.yml`. It checks five entries (GitHub Actions, pip for `/app` and `/slides`, Docker for `/app`, and devcontainers) every Monday at 09:00 (Asia/Seoul). Minor and patch updates are grouped into one PR per ecosystem, and major updates open separate PRs. `cooldown` makes it propose a release only after the release has been out for 3 days, and it does not apply to security updates. PRs get the `dependencies` label and a `chore(...)` prefix. The options are in the [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
2. Look at the alerts under **Dependabot** on the **Security** (or **Security and quality**) tab. Alerts are based on the manifests on the default branch, so `flask==2.2.4` from the step 3 PR does not appear here before it is merged; it appears only in the PR's Dependency review.
3. On the **Insights → Dependency graph → Dependabot** tab, look at the update job history with **Recent update jobs** next to a manifest, and re-check right away with **Check for updates**.
4. In a terminal, list the Dependabot PRs with `gh pr list --label dependencies`.

Success criteria: The Dependabot tab shows update jobs for the ecosystems you configured. If there are outdated dependencies, PRs with the `dependencies` label and the `chore(...)` prefix are open. If everything is up to date, having no PRs is normal, so check before the demo whether any Dependabot PRs are open.

## Talking points

- **Settings are code too.** The ruleset, CODEOWNERS, Dependabot, the dev container and the apply script are all repository files. You can review them in a PR, take them to another repository as they are, and apply them again any number of times with the same result.
- **Changes reach main only through PRs.** Deletion and force push are blocked, and a change merges only after it passes approval, the required checks and code scanning.
- **The admin bypass is a compromise.** In a single-person repository you cannot approve your own PR, so we opened a `pull_request`-mode bypass. In a team repository, it is safer to empty this entry and also turn on `require_last_push_approval`.
- **Security checks move earlier, into the PR.** CodeQL catches problems in code and workflows, Dependency review catches new dependencies, and push protection catches secrets, all before the merge. You meet the problem before it reaches deployment.
- **Copilot helps with review, and a person approves.** Copilot code review acts as the first reviewer and does not count toward the required approvals. Code owners and people make the final call.
- **Onboarding takes a few clicks.** Codespaces provides the tools, and the password is nowhere in the repository.

## Cleanup

```bash
git switch main
gh pr close demo/risky-change --delete-branch   # close the PR and delete the remote and local branch
git fetch --prune origin                        # clean up records of deleted remote branches
```

- Close this PR without merging it. If you used another name with `make-risky-pr.sh --branch`, run the commands with that name instead.
- Delete the Codespace at github.com/codespaces or with `gh codespace delete`.
- To undo the ruleset, set `main-protection` to Disabled or delete it at **Settings → Rules → Rulesets**. If you run `apply-repo-settings.sh --apply` again, a ruleset with the same name returns to the content of the JSON (`active`).
- Undo the merge options (squash only) in the Pull Requests section of **Settings → General**.
- Both scripts are safe to run many times. It is fine to leave the labels, the environment and the security settings in place.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Importing the ruleset, or the ruleset step of `--apply`, fails | Your plan or organization policy may not accept the `code_scanning` or `copilot_code_review` rule. Create the ruleset without those two rules with `scripts/apply-repo-settings.sh --apply --only ruleset --core-rules-only`, and add the two features yourself under **Settings → Rules**. If you import in the UI, delete the two rule blocks from the JSON before you upload it. |
| You cannot pick a required check from the list, or the PR stays at "Waiting for status to be reported" | A check name appears in the selection list only after that workflow has run once. Run it once on main with **Actions → CI → Run workflow**. The check is not reported if the job display name differs from the JSON by even one character, if the workflow has a `paths` filter, or if a reusable workflow changes the name. If the check is sent by another app, delete the matching `integration_id` from the JSON. |
| You cannot merge in a repository you use alone | The PR author cannot approve their own PR, and a code owner review is also required. Merge with an admin bypass, or approve with another account that has write access. Do not use it on the risky PR of step 3. |
| The person asked for a code owner review is the wrong one | A fork or a repository made from the template still has `@junwoojeong100`. Change `.github/CODEOWNERS` to your own account or team. A code owner must have write access to the repository. |
| `apply-repo-settings.sh --apply` returns 403 or 404 | You do not have admin access, or you are using the default token of a Codespace. Run `unset GITHUB_TOKEN` and then sign in with `gh auth login`, or run it from a local terminal. If only some calls fail, the script reports the number of failures at the end, and since it is idempotent you can run it again. |
| The push of `make-risky-pr.sh` is rejected (the error mentions `workflow`) | The branch has a new workflow file, so the token needs the `workflow` scope. Run `gh auth refresh --scopes workflow`. The default token in Codespaces may be blocked, so running from a local terminal is safer. If you cannot grant the scope, undo the change with the commands the script printed and run it again with `--no-workflow`. In that case the demo of Actions workflow alerts is skipped. |
| `make-risky-pr.sh --apply` prints a warning and stops | The working tree is not clean, HEAD is ahead of the origin's default branch, a branch or target file with the same name already exists, or `gh` is not signed in. It changes nothing in these cases, so fix the problem as the message says and run it again. Clear a warning that origin branch records remain with `git fetch --prune origin`. If it stops after creating the branch, it prints the commands to undo it. |
| No CodeQL alerts, or the rule IDs differ | `Analyze (python)` and `Analyze (actions)` have not finished yet, or the detection results changed with the CodeQL query version. Run it once before the talk and check the results. |
| No Copilot review appears | Check the Copilot license and policy of the person who opened the PR. The ruleset's automatic review is not requested on draft PRs, so change the PR to Ready for review or request Copilot directly under **Reviewers**. If there is nothing to flag, the review can also end without comments. |
| Dependabot reports an error for the `/slides` entry | `slides/requirements.txt` is missing. Add the file, or delete that entry from `.github/dependabot.yml`. |
| Port 8080 does not open | Check that the app is running, and add 8080 yourself in the PORTS tab. If the app returns `503`, `DEMO_PASSWORD` is not set. |
| The script cannot find `jq` | `apply-repo-settings.sh` uses `jq` even in a dry-run. A Codespace has it; locally, install it with your package manager. |

## Using it with other demos

This demo runs end to end without any other demo. Using them together connects the story.

- **[Demo 1 (GitHub Copilot)](../01-github-copilot/README.md)**: A PR made by the cloud agent must pass the same ruleset. The person who asked the agent to do the work cannot approve that PR, so you need an admin bypass or an approval from another account. The `copilot-demo` label is created in advance by `apply-repo-settings.sh` of this demo.
- **[Demo 3 (GitHub Actions)](../03-github-actions/README.md)**: The required check names are the same as the job names in `ci.yml`. The parallel CI is the merge condition. The `azure-demo` environment is created by this demo's script, and if you set an approver with `--reviewer`, you can show the deployment approval gate right away.
- **[Demo 4 (Microsoft Foundry)](../04-microsoft-foundry/README.md)**: In a Codespace too, you can run the app the same way after `az login` (use `--use-device-code` if a browser login is hard).
- **[Demo 5 (Azure Container Apps)](../05-azure-container-apps/README.md), [Demo 6 (AKS)](../06-aks/README.md)**: You can run the deploy scripts as they are with the `az`, `docker` and `kubectl` in a Codespace. If you need kubelogin, run `sudo az aks install-cli`. Dependabot also opens PRs for updates to the base image in the Dockerfile.

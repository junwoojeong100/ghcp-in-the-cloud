# Demo 1 — GitHub Copilot: From Issue to PR, Working with an AI Teammate

Hand one issue to an AI teammate (the Copilot cloud agent), receive the result as a PR, and verify it with CI, Copilot code review and a human review before you merge. This repository holds the team's Copilot configuration (instructions, prompts, agents and MCP) as code, so the same rules apply to agent work and to code review.

> GitHub's documentation calls this agent the Copilot cloud agent (formerly the coding agent). This guide also says "cloud agent". Text in angle brackets (`<>`) is a placeholder for your own value.

## At a glance

| Item | Details |
|---|---|
| Goal | Show issue → agent PR → CI → Copilot code review → human review and merge in one pass, and explain how the repository's Copilot settings change the quality of the result. |
| Time | About 7 minutes. The agent needs a few minutes to work, so assign one issue 10–15 minutes before the demo. |
| Difficulty | Medium |
| Standalone | Yes. You only need a GitHub repository and a Copilot license (with cloud agent access). No Azure subscription is needed. Only the Azure MCP query in the optional step 5 needs `az login`. |

```text
Issue → assign Copilot → agent session → draft PR → CI → Copilot code review → human review → merge
```

## Why this service (benefits)

- **Productivity**: If you write the issue well, the agent creates a branch, writes the code and tests, and opens a PR. People spend their time on review and judgment instead of implementation.
- **Team standards as code**: Repository-wide instructions (`.github/copilot-instructions.md`), path-specific instructions (`.github/instructions/`), prompt files (`.github/prompts/`) and custom agents (`.github/agents/`) are versioned with the code and reviewed in PRs. The agent follows the same coding rules that people follow.
- **Safe automation**: The agent can write only to its own `copilot/` branches, and it cannot mark a PR as Ready for review, approve it or merge it. A person must approve workflow runs, and branch protection and required checks still apply. Copilot code review and a human review sit on top of that.
- **Cloud connection**: The Azure MCP server lets you query Azure resources in conversation (read-only by default), and the Copilot CLI continues the same work from the terminal.

## Prerequisites

1. **Enable the cloud agent**: You need a paid Copilot plan and write access to the repository. For an organization repository, the cloud agent ("Copilot in the cloud") must be enabled in the organization's policies and this repository must be allowed. For a personal repository, turn it on in your account's Copilot settings.
2. **GitHub CLI (`gh`)**: `scripts/create-demo-issues.sh` uses it. Run `gh auth login` beforehand. The `--assign-copilot` option needs `gh` 2.76 or later and does not work on GitHub Enterprise Server.
3. **Configuration files on the default branch**: The instructions, agents and workflow files under `.github/` must be merged into the default branch for the cloud agent to read them. In particular, `.github/workflows/copilot-setup-steps.yml` (job name `copilot-setup-steps`) takes effect only on the default branch. This workflow prepares the development environment (Python and dependencies) in advance when an agent session runs on GitHub Actions. A session that you start by assigning an issue to Copilot may also use it. The agent continues even if a step fails, so check this step in the session log.
4. **If the repository uses the ruleset, know the approval rules**: The `main-protection` ruleset from Demo 2 requires one approval, a code owner review and the required checks. The person who asked the agent to do the work cannot approve that PR. In a repository with a single presenter, you cannot meet the approval requirement. Either merge with an admin bypass (this ruleset lets admins bypass the PR requirement) or approve with another account that has write access and code owner status. A repository without the ruleset does not have this constraint.
5. **`copilot-demo` label**: `scripts/create-demo-issues.sh --apply` creates it if it does not exist. The issue form (`Copilot demo task`) also applies this label, but it is not applied if the repository does not have the label yet, so run the script once or create the label first.
6. **VS Code and CLI (optional, step 5)**: When you open the repository in VS Code with GitHub Copilot Chat installed, `.vscode/extensions.json` suggests the recommended extensions. `.vscode/mcp.json` is for VS Code only; the cloud agent does not read it. Register the cloud agent's MCP servers separately in the repository settings under Copilot. The Azure MCP server (`azure`) needs Node.js (`npx`) and `az login`, and it starts with `--read-only`, so it does not change resources during the demo. To pin the version, replace `latest` in `@azure/mcp@latest` with a specific version. Install the Copilot CLI (`copilot`) with `npm install -g @github/copilot`.

### Three starter issues

The issue bodies in `demos/01-github-copilot/issues/` include Context, Requirement, Acceptance criteria, Constraints, How to test and Out of scope, so the cloud agent is likely to succeed, and they are independent of each other. They describe features the app does not have yet, so running them produces real code changes.

| # | Title | What changes | Demo point |
|---|---|---|---|
| 01 | Add a per-client rate limit to `POST /api/chat` | `app/server.py`, `app/tests/`, `README.md` | HTTP 429 and `Retry-After`, a security-minded review discussion |
| 02 | Add a Prometheus-format `GET /metrics` endpoint | `app/server.py`, `app/tests/`, `README.md` | Implemented without new dependencies, existing Basic authentication applies |
| 03 | Show the last 10 questions and answers with a Clear button | `app/index.html`, `app/tests/` | The result is visible on screen right away, the `innerHTML` ban |

We recommend 03 for the live start because its result is visible on screen, and 01 for the review demo because it gives you the most to discuss. 01 and 02 change the same file, so their PRs can conflict if both issues are open at once. If they conflict, ask `@copilot` in the PR to resolve it. Results differ on every run, so do not promise specific code or review comments.

## Demo steps

> Portal menu names may change.

### 1. Tour the repository's Copilot settings (about 1 min)

On the GitHub repository page or in the VS Code explorer, open the files below in order.

| Path | What to show |
|---|---|
| `.github/copilot-instructions.md` | Repository-wide rules that are attached automatically to every Copilot request: commands, only `/healthz` is unauthenticated, no secrets |
| `.github/instructions/*.instructions.md` | Path-specific rules. `applyTo` globs apply different rules to Python, Bicep, Kubernetes, Actions workflows and English docs |
| `.github/prompts/*.prompt.md` | Slash prompts: `/add-endpoint`, `/write-tests`, `/review-security`, `/explain-infra`, `/demo-script` |
| `.github/agents/*.agent.md` | Custom agents: `azure-iac-reviewer` (a read-only reviewer), `demo-writer`, `foundry-integrator` |
| `.vscode/mcp.json` | Three MCP servers: Azure, GitHub (read-only URL) and Microsoft Learn |
| `.github/ISSUE_TEMPLATE/copilot-demo.yml` | An issue form that helps the agent succeed: Context, Requirement, Acceptance criteria, Constraints, How to test, Out of scope |

Success criteria: The rule list in `copilot-instructions.md` and the `applyTo` lines in the `instructions/` files are on screen, and the audience understands that "these rules live in the repository and change through PRs".

### 2. Create an issue and assign it to Copilot (about 1.5 min)

**Option A. Script (recommended)**

```bash
scripts/create-demo-issues.sh                                    # preview: prints only the gh commands it would run
scripts/create-demo-issues.sh --apply --assign-copilot --only 3  # create issue 3 and assign it to Copilot
```

The first line creates nothing and only prints the `gh issue create` command it would run. Remove `--only` to create all issues. The script skips an open issue with the same title, so it is safe to run again. If `--assign-copilot` is not available in your environment, the script creates the issue only and tells you how to assign it manually.

**Option B. Issue form**

1. In **Issues → New issue**, choose `Copilot demo task` and fill in each field (Context, Requirement, Acceptance criteria, Constraints, How to test, Out of scope). Pasting the matching sections from `demos/01-github-copilot/issues/` is the fastest way.
2. After you create the issue, choose **Copilot** under **Assignees** on the right, confirm the target repository and the base branch in the dialog, and assign it.

Success criteria: The issue has the `copilot-demo` label and a Copilot assignee, and shortly afterwards an eyes (👀) reaction appears. Then the timeline shows that Copilot has started work, followed by a link to the draft PR.

### 3. Check the agent session, the PR and CI (about 2 min)

1. Open the agent log with **View session** on the issue or PR timeline. You can see it read the code, implement the change and run tests.
2. Go to the PR you prepared in advance and look at the description, the implementation, tests and docs changes under **Files changed**, and the commits. The commit author is Copilot, and the person who assigned the issue is shown as a co-author.
3. If the checks are pending, click **Approve and run workflows** on the PR to start `CI`. Watch the `CI` jobs (`Unit tests`, `Container build and smoke test`, `IaC validation`, `Workflow and script lint`) run in parallel.
4. If a check failed, ask the agent to fix it in a PR comment. Example: `@copilot The Unit tests failed. Find the cause and fix it.` The agent adds an eyes (👀) reaction and pushes more commits to the same branch.

Success criteria: The PR is a draft linked to the issue, **Files changed** shows the implementation, tests and docs together, and every `CI` job is green.

### 4. Copilot code review, human review and merge (about 2 min)

1. Change the draft PR to **Ready for review**. The agent cannot do this step.
2. Request **Copilot** under **Reviewers** on the right of the PR. In a terminal, use `gh pr edit <PR number> --add-reviewer "@copilot"`. Copilot's review appears shortly.
3. A person judges each comment. If it is valid, apply the suggestion or ask `@copilot` to make the change. Otherwise, close it with **Resolve**. Copilot's review is a comment, not an approval, so it does not replace a merge requirement.
4. A person reads the diff, approves and merges. With the ruleset on, the required checks must pass and a code owner must approve (see prerequisite 4).

Success criteria: Copilot's review is on the PR (the number of comments can vary), and the PR is merged with the required checks passing after a person has handled the comments. The linked issue closes automatically.

### 5. (Optional) VS Code agent mode, prompt files, Azure MCP, Copilot CLI (about 2 min)

1. Open the repository in VS Code and set Copilot Chat to **Agent** mode.
2. **Prompt file**: In the input box, run a prompt with the route and behavior together, such as `/add-endpoint GET /api/version`. When the code, tests and docs change together, check in the terminal with `python -m unittest discover -s app/tests -v`.
3. **Custom agent**: In the chat's agent picker, choose `azure-iac-reviewer` and ask it to review `infra/aca/main.bicep`. This agent has only read and search tools, so it gives feedback without modifying files.
4. **Azure MCP**: After `az login`, start the `azure` server from **MCP: List Servers** in the command palette and ask something like "List the resource groups in my subscription." It is read-only, so it does not change any resource. If you deployed resources in Demos 4–6, querying those is more natural.
5. **Copilot CLI**: Run one line: `copilot -p 'Summarize the endpoints and authentication of this repository in a table' -s`. It reads the same `.github/copilot-instructions.md`. In an interactive session, `/delegate <task>` sends the task to GitHub and creates a PR. To hand off a task without an issue, there is also `gh agent-task create "<task description>" --follow` (a preview command).

Success criteria: `/add-endpoint` changes the code, tests and docs together and the tests pass, `azure-iac-reviewer` gives feedback without editing files, and Azure MCP returns the list read-only.

## Talking points

- **The quality of the issue is the quality of the result.** An issue with context, acceptance criteria, constraints and a test method lets the agent work and verify itself. The issue form enforces this shape. The agent reads only the title, the body and the existing comments at assignment time, so give later instructions in the PR with `@copilot`.
- **People stay in control.** The agent writes only to `copilot/` branches, and it cannot mark a PR as Ready, approve it or merge it. A person also approves workflow runs.
- **It is traceable.** Commits are signed and show as Verified, Copilot is the author with the person who gave the instruction as co-author, and the commit message has a link to the session log.
- **Team standards are code.** Instruction files are read by the cloud agent, VS Code, the Copilot CLI and Copilot code review, and custom agents can be picked in VS Code, the cloud agent and the Copilot CLI. To change a rule, open a PR and get it reviewed.
- **Review has two layers.** Copilot code review goes first and a person makes the final call. Copilot's review does not count as an approval.
- **No secrets go in.** There are no keys in the instructions, the MCP config or the agent environment, and Azure uses keyless authentication (Entra ID). The agent's internet access is restricted by default. Instructions hidden in an HTML comment in an issue or a comment are not passed to the agent.

## Cleanup

```bash
gh issue list --label copilot-demo --state open                   # list remaining demo issues
gh issue close <issue number> --reason "not planned"              # close issues you do not need
gh pr list --state open --json number,title,headRefName \
  --jq '.[] | select(.headRefName | startswith("copilot/"))'       # list agent PRs
gh pr close <PR number> --delete-branch                           # close a PR you will not merge and delete its branch
gh label delete copilot-demo --yes                                 # (optional) delete the label
```

- Delete the branch of a merged PR with **Delete branch** on the PR page.
- To undo a merged change, use **Revert** on the merged PR to create a reverting PR. Take care not to recreate an issue that is already implemented.
- The script treats only open issues as duplicates, so you can recreate a closed issue with the same title.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Copilot is not in the Assignees list | Check the paid Copilot plan, write access to the repository, the organization policy (cloud agent allowed) and the repository access scope. `--assign-copilot` needs the same conditions. |
| Nothing happens after you assign the issue | Wait a few minutes and refresh. If the issue has no eyes (👀) reaction, unassign Copilot and assign it again. A session that has been stuck for a long time can end because of a time limit, so restart it the same way. |
| Checks stay pending and do not start | Workflows on an agent's PR need a person to click **Approve and run workflows** by default. You can change the repository setting to run them automatically, but in a demo it is better to show the human approval step. |
| The PR shows a firewall warning, or `pip install` fails | The cloud agent's internet access is restricted by default. Install dependencies ahead of time in `copilot-setup-steps.yml`, and add the hosts you really need to the allowlist in the repository settings under Copilot (Internet access). Allowlist changes apply from the next session. |
| The agent breaks the rules | Check that the instruction files are on the default branch and that the `applyTo` glob matches the target path. Write the file locations and prohibitions more concretely in the issue's Constraints, and ask `@copilot` in the PR to fix it. |
| A custom agent is missing from the picker | Check that `.github/agents/*.agent.md` is on the default branch and has a `description`. |
| The merge button is blocked | The ruleset requires approval and a code owner review, and the person who asked the agent to do the work cannot approve that PR. Use an admin bypass or an approval from another account (prerequisite 4). |
| Required checks are never reported | The workflow has not been approved yet, or the job display name differs from the ruleset's required check names (`Unit tests`, `Container build and smoke test`, `IaC validation`). |
| Copilot's review has no comments | If there is nothing to flag, the review can end without comments. The ruleset's automatic review is not requested on draft PRs, so request it manually while the PR is a draft, or change the PR to Ready for review and then request it. |
| The script cannot find `gh`, or shows an authentication error | Run `gh auth login` and check with `gh auth status`. The preview (the default behavior) makes no write calls. If `--assign-copilot` fails, the script creates only the issue and tells you to use `gh issue edit <number> --add-assignee @copilot` or the Assignees menu. |

## Using it with other demos

This demo runs end to end without any other demo. Using them together connects the story.

- **Demo 2 (GitHub Repo)**: With the `main-protection` ruleset applied, an agent PR must pass the same required checks, code owner review and approval rules. The "a person makes the final call" message in step 4 becomes clearer.
- **Demo 3 (GitHub Actions)**: The `CI` that runs in step 3 is exactly the set of parallel jobs shown in Demo 3. Showing them back to back flows naturally.
- **Demos 4–6 (Foundry, Container Apps, AKS)**: In step 5, Azure MCP can query the deployed resources. If you merged issue 01 (rate limit), the default path `/api/chat` of `scripts/load-test.sh` can return `429`. In that case, set `RATE_LIMIT_PER_MINUTE=0` in the deployed environment to turn the limit off, or load `--path /healthz`.

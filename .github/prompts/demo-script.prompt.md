---
description: 'Turn a change into a three-step live-demo script, in Korean'
argument-hint: 'what changed, or a PR or commit reference'
agent: ask
---

Create a live-demo script of about 5 minutes for this change: ${input:change:describe the change, a PR number or a commit}

Base it on the source-control changes or the files the user names. Keep every command and path real: use only commands from `.github/copilot-instructions.md` or scripts under `scripts/`. Prefer `LLM_BACKEND=mock` so the demo also works without Azure.

## Output (Korean): exactly three steps
Each step has:
- **말할 것**: one or two spoken sentences on why it matters.
- **할 것**: the exact command, click or prompt.
- **성공 기준**: what the audience should see.
- **Plan B**: what to do if it fails or is slow, for example a prepared PR or a screenshot.

Finish with a one-sentence takeaway and a short cleanup that restores the demo state.

## Success criteria
- Three steps, each doable in under two minutes.
- No invented URLs, outputs, numbers or UI labels. If a UI label is uncertain, describe the control generically.
- Works offline with `LLM_BACKEND=mock`; real Azure is optional.

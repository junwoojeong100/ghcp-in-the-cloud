---
name: 'English docs and demo guides'
description: 'Language, terminology and section skeleton for the English edition under en/: README.md, DEMO_GUIDE.md, the guides under en/demos/ and en/slides/.'
applyTo: 'en/**/*.md'
---

# English docs rules

- The English edition under `en/` is a translation of the Korean docs. Korean is the source of truth: when a Korean doc changes, change its English twin in the same PR (`README.md` and `en/README.md`, `DEMO_GUIDE_KO.md` and `en/DEMO_GUIDE.md`, `demos/` and `en/demos/`, `slides/` and `en/slides/`).
- Write natural English for developers and architects: short sentences, concrete steps, no marketing language, few emoji. Put CLI commands, file names, env vars and code in backticks, and use the official product names.
- Use the same terms everywhere: revision, Workload Identity, Managed Identity, scale-to-zero.
- Every `en/demos/*/README.md` keeps this section skeleton, in this order:
  1. `## At a glance` (goal, time, difficulty, standalone or not)
  2. `## Why this service (benefits)`
  3. `## Prerequisites`
  4. `## Demo steps`
  5. `## Talking points`
  6. `## Cleanup`
  7. `## Troubleshooting`
  8. `## Using it with other demos` (optional integrations only; never require another demo)
- In `## Demo steps`, number every step, give the exact command or click, and end each step with a `Success criteria:` line that says what the audience should see.
- Every command, path, script and env var in a document must exist in the repo or be created by a documented step. Check with `ls` or `grep` before finishing. Paths in prose are repository-root paths (for example `scripts/deploy-aca.sh` or `en/slides/build_deck.py`), and every relative Markdown link must resolve from the file that contains it.
- The app and the scripts in this repository print Korean. Quote their labels and messages in Korean with an English gloss, and keep the table in `en/README.md` ("Language of the app and the scripts") up to date.
- Do not state benchmark numbers, prices, SLAs or "x% faster". Describe features qualitatively. Say "Portal menu names may change." once per document instead of hedging every step.
- No secrets or token-shaped strings, no `TODO` text and no invented URLs. Use `<owner>`-style placeholders only where unavoidable, and say so.
- `en/slides/demo-presentation-en.pptx` and `en/slides/demo-presentation-en.md` are generated: edit the data in `en/slides/build_deck.py` and run `python en/slides/build_deck.py` instead of editing the outputs.
- `en/demos/01-github-copilot/issues/*.md` are English versions of the issue bodies, not guides: they start with a `# [Demo] ...` title line, like the Korean files.

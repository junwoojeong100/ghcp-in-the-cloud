---
name: 'Korean docs and demo guides'
description: 'Language, terminology and section skeleton for README.md, DEMO_GUIDE_KO.md and the guides under demos/.'
applyTo: 'demos/**/*.md,README.md,DEMO_GUIDE_KO.md'
---

# Korean docs rules

- Write natural Korean for developers and architects: short sentences, concrete steps, no marketing language, few emoji. Keep product names, CLI commands, file names, env vars and code in English and in backticks.
- Use the same terms everywhere: 리비전, 워크로드 ID(Workload Identity), 관리 ID(Managed Identity), 스케일 투 제로(scale-to-zero).
- Every `demos/*/README.md` keeps this section skeleton, in this order:
  1. `## 한눈에 보기` (목표, 시간, 난이도, 독립 실행 여부)
  2. `## 왜 이 서비스인가 (이점)`
  3. `## 사전 준비`
  4. `## 시연 순서`
  5. `## 말하기 포인트`
  6. `## 정리(Cleanup)`
  7. `## 문제 해결`
  8. `## 다른 데모와 함께 쓰면` (선택 연동만; 다른 데모를 필수로 요구하면 안 됨)
- In `## 시연 순서`, number every step, give the exact command or click, and end each step with a `성공 기준:` line that says what the audience should see.
- Every command, path, script and env var in a document must exist in the repo or be created by a documented step. Check with `ls` or `grep` before finishing.
- Do not state benchmark numbers, prices, SLAs or "x% faster". Describe features qualitatively. Say "UI 메뉴 이름은 변경될 수 있음" once per document instead of hedging every step.
- No secrets or token-shaped strings, no `TODO` text and no invented URLs. Use `<owner>`-style placeholders only where unavoidable, and say so.
- When behavior, commands or env vars change, update the matching demo guide and `slides/` in the same PR, and their English twins under `en/` (see `docs-en.instructions.md`). `slides/demo-presentation-ko.pptx` and `slides/demo-presentation-ko.md` are generated: edit the data in `slides/build_deck.py` and run `python slides/build_deck.py` instead of editing the outputs.
- `demos/01-github-copilot/issues/*.md` are issue bodies, not guides: they start with a `# [Demo] ...` title line and use the same headings as `.github/ISSUE_TEMPLATE/copilot-demo.yml`.

---
description: 'Write offline unittest tests for a function, route or module of the demo app'
argument-hint: 'what to cover, e.g. POST /api/chat validation'
agent: agent
---

Write tests for: ${input:target:the function, route or file to cover}

## Steps
1. Read `.github/instructions/python.instructions.md` and the existing tests in `app/tests/`. Reuse their helpers and style.
2. List the behaviors that are not covered yet: happy path, `401` failures, invalid input, boundary values, error paths. Start with the most valuable ones.
3. Use `unittest` only. Keep tests offline and deterministic: `LLM_BACKEND=mock`, an ephemeral port, patched environment variables, injected clocks instead of real sleeping, no real credentials.
4. Do not change production code unless a test exposes a real bug. If it does, make the smallest fix and say so.
5. Run `python -m unittest discover -s app/tests -v` until it is green.

## Success criteria
- Each new test can fail: confirm at least one by reasoning about, or temporarily breaking, the behavior it checks. Undo any temporary change.
- The whole suite passes offline and quickly.
- Reply in Korean: what is covered, what is intentionally not covered, and the command to run.

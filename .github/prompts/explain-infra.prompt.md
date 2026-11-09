---
description: 'Explain a Bicep, Kubernetes or workflow file to a presenter, in Korean'
argument-hint: 'file path, e.g. infra/aca/main.bicep'
agent: ask
---

Explain this file for a Korean-speaking presenter who will show it live: ${input:file:infra/aca/main.bicep}

Read the file and what it references (modules, kustomize bases, scripts it calls). Describe only what the files contain. Do not invent resources, values or behavior.

## Output (Korean, about 40 lines at most)
1. **한 줄 요약**: what the file creates or does.
2. **핵심 구성 요소**: a table with 리소스 또는 단계 · 역할 · 눈여겨볼 설정.
3. **보안 포인트**: identity (관리 ID, 워크로드 ID, OIDC), 최소 권한, 비밀 없음, 네트워크 노출. Say which of these the file does not show.
4. **발표 멘트**: three spoken-style sentences the presenter can read out.
5. **보여줄 명령**: one or two commands with the expected result, using only commands that exist in this repo or are standard CLIs (`bicep build`, `kubectl get`, `gh run list`).
6. **예상 질문**: two likely audience questions with short answers.

Use these terms consistently: 리비전, 워크로드 ID(Workload Identity), 관리 ID(Managed Identity), 스케일 투 제로(scale-to-zero).

## Success criteria
- Every claim can be traced to a line in the file.
- The three spoken sentences are usable without further editing.

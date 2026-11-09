> **DEMO – DO NOT MERGE**
> Rulesets, CodeQL, Dependency review가 위험한 변경을 잡는 모습을 보여 주려고 일부러 취약하게 만든 시연용 PR입니다.
> 머지하지 마세요. 시연이 끝나면 PR을 닫고 브랜치를 삭제합니다.

## 변경 요약

의도적으로 취약하게 만든 파일 세 개를 새로 추가합니다. 기존 파일은 수정하지 않습니다. (`--no-workflow`로 만든 PR에는 `triage.yml`이 없습니다.)

| 파일 | 일부러 넣은 문제 | 기대하는 탐지 |
|---|---|---|
| `app/extras/debug_files.py` | 요청 값으로 파일 경로를 조합(경로 조작), 요청 값을 셸 명령에 삽입(명령어 삽입), Flask 디버그 모드 | CodeQL: `py/path-injection`, `py/command-line-injection`, `py/flask-debug` |
| `app/extras/requirements.txt` | 알려진 취약점이 있는 `flask==2.2.4` (GHSA-m2qf-hxjv-5gpq, 심각도 high) | Dependency review |
| `.github/workflows/triage.yml` | 이슈 제목을 셸 스크립트에 그대로 삽입(expression injection) | CodeQL(GitHub Actions): `actions/code-injection/critical` |

탐지 결과는 CodeQL 쿼리와 어드바이저리 데이터베이스의 버전에 따라 조금 달라질 수 있습니다.

## 확인할 곳

- **Checks 탭**: CodeQL 분석과 Dependency review 결과
- **Files changed**: 코드 스캐닝 알림 주석과 Copilot code review 코멘트
- **머지 상자**: 필수 상태 체크, 코드 오너 리뷰, 코드 스캐닝 규칙 중 충족하지 못한 항목

## 정리

```bash
git switch main
gh pr close demo/risky-change --delete-branch
git fetch --prune origin
```

`make-risky-pr.sh`에서 `--branch`로 다른 이름을 썼다면 그 이름으로 바꿔 실행하세요.

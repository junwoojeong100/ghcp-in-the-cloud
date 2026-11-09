# [Demo] 화면에 최근 질문·답변 10개와 지우기 버튼 추가

### 배경 (Context)

데모 화면(`app/index.html`, 서버가 `GET /`로 내려 주는 한 장짜리 HTML)은 질문을 보내면 가장 최근 답변 하나만 보여 줍니다. 발표 중에 앞서 한 질문과 답변을 다시 보여 주려면 같은 질문을 다시 입력해야 합니다.

- 화면: `app/index.html` (순수 HTML, CSS, 자바스크립트. 프레임워크와 빌드 도구 없음)
- 서버: `app/server.py` (이번 작업에서는 바꾸지 않습니다)
- 테스트: `app/tests/` (`unittest`)

### 요구사항 (Requirement)

현재 페이지를 열어 둔 동안 주고받은 **최근 질문·답변 최대 10개**를 화면에 목록으로 보여 주고, 목록을 비우는 **"지우기"** 버튼을 추가합니다.

- 브라우저 쪽에서만 구현합니다. `POST /api/chat`의 요청과 응답 형식은 그대로 둡니다.
- 질문과 답변은 자바스크립트 배열(메모리)에만 보관합니다. `localStorage`, `sessionStorage`, 쿠키에는 저장하지 않습니다. 새로고침하면 목록이 사라지는 것이 의도한 동작입니다.
- 가장 최근 항목이 위에 오고, 11번째 항목부터는 가장 오래된 항목을 버립니다.
- 성공한 질문·답변 쌍만 기록합니다. 오류 응답은 기록하지 않고, 지금처럼 오류만 표시합니다.
- 모델 답변은 신뢰할 수 없는 텍스트입니다. DOM에 넣을 때는 `textContent`나 `createElement`와 `append` 같은 DOM API만 쓰고, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`는 쓰지 않습니다.
- "지우기" 버튼은 화면의 목록과 배열을 모두 비웁니다. 기록이 없을 때는 "아직 기록이 없습니다" 같은 안내 문구를 보여 주고 버튼을 비활성화합니다.
- 기존 CSP(nonce 기반 `script-src`, `style-src`)를 그대로 지킵니다. `onclick=` 같은 인라인 이벤트 핸들러를 쓰지 말고, 기존 `<script>` 블록 안에서 `addEventListener`로 연결합니다. 새 스타일은 기존 `<style>` 블록에 추가하고 기존 CSS 변수(라이트·다크 모드)를 씁니다.
- 접근성: 버튼은 `<button>`을 쓰고, 목록에는 "최근 대화" 같은 제목을 붙입니다.

### 수용 기준 (Acceptance criteria)

- [ ] 질문을 12번 보내면(mock 백엔드) 목록에는 가장 최근 10개만 최신순으로 보인다.
- [ ] 각 항목에 질문과 답변이 함께 보이고, 답변에 `<b>x</b>` 같은 HTML이 들어 있어도 태그로 해석되지 않고 글자 그대로 보인다.
- [ ] "지우기"를 누르면 목록이 비고 안내 문구가 보인다. 페이지를 새로고침하면 목록이 비어 있다.
- [ ] 오류 응답은 목록에 추가되지 않는다.
- [ ] `app/index.html`에 `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `localStorage`, `sessionStorage`가 없고 인라인 이벤트 핸들러 속성도 없다 (정적 검사 테스트로 확인한다).
- [ ] 정적 검사 테스트가 "지우기" 버튼의 존재도 확인하고, 인증된 `GET /`가 계속 `200`을 돌려준다.
- [ ] 기존 화면 요소(실행 환경 칩, 새로고침, 트래픽 분포 보기, 예시 질문)가 그대로 동작한다.
- [ ] `python -m unittest discover -s app/tests -v`가 모두 통과한다.

### 제약 사항 (Constraints)

- 수정 범위: `app/index.html`과 `app/tests/`(정적 검사 테스트 추가). 서버 코드, API, `app/requirements.txt`는 바꾸지 않습니다.
- 외부 CDN, 폰트, 스크립트와 UI 프레임워크를 추가하지 않습니다.
- 모델 출력은 `textContent`와 DOM API로만 화면에 넣습니다.
- 기존 CSP와 접근성 속성(`aria-live` 등)을 약하게 만들지 않습니다.
- 가능하면 `LLM_BACKEND=mock`으로 앱을 띄워 화면에서 직접 확인하고, 확인 결과나 스크린샷을 PR 설명에 남깁니다.

### 테스트 방법 (How to test)

```bash
python -m unittest discover -s app/tests -v
```

수동 확인(선택): 서버를 임시 포트로 띄우고 브라우저에서 엽니다. 사용자 이름은 `demo`이고 비밀번호는 `echo "$DEMO_PASSWORD"`로 확인합니다.

```bash
export DEMO_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(12))')"
LLM_BACKEND=mock PORT=8081 python -m app.server
```

브라우저에서 `http://127.0.0.1:8081/`을 열고 질문을 12번 보낸 뒤 목록이 10개인지, "지우기"가 목록을 비우는지 확인합니다.

### 범위 밖 (Out of scope)

- 서버 쪽 대화 저장, 사용자별 기록, 영구 저장(`localStorage`, 쿠키, 데이터베이스)
- 대화 내보내기, 검색, 마크다운 렌더링, 스트리밍 응답
- UI 프레임워크나 빌드 도구 도입
- 슬라이드와 `demos/` 문서 수정

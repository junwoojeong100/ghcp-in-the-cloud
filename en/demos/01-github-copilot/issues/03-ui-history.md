# [Demo] Show the last 10 questions and answers with a Clear button

### Context

The demo screen (`app/index.html`, the single HTML page the server returns for `GET /`) shows only the latest answer after you send a question. To show an earlier question and answer again during a talk, you have to type the same question again.

- Screen: `app/index.html` (plain HTML, CSS and JavaScript; no framework or build tool)
- Server: `app/server.py` (not changed in this task)
- Tests: `app/tests/` (`unittest`)

### Requirement

Show a list of the **last 10 questions and answers** exchanged while the current page stays open, and add a **"Clear"** button that empties the list.

- Implement this in the browser only. Keep the request and response format of `POST /api/chat` as it is.
- Keep the questions and answers only in a JavaScript array (memory). Do not store them in `localStorage`, `sessionStorage` or cookies. The list disappearing on reload is the intended behavior.
- The newest item goes on top. From the 11th item on, drop the oldest item.
- Record only successful question-and-answer pairs. Do not record error responses; show only the error, as it does now.
- Model answers are untrusted text. When you put them in the DOM, use only DOM APIs such as `textContent`, or `createElement` and `append`. Do not use `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write`.
- The "Clear" button empties both the list on screen and the array. When there is no history, show a message such as "No history yet" and disable the button.
- Keep the existing CSP (nonce-based `script-src` and `style-src`) intact. Do not use inline event handlers such as `onclick=`; connect events with `addEventListener` inside the existing `<script>` block. Add new styles to the existing `<style>` block and use the existing CSS variables (light and dark mode).
- Accessibility: use a `<button>` for the button, and give the list a heading such as "Recent conversation".

### Acceptance criteria

- [ ] After 12 questions are sent (mock backend), the list shows only the 10 most recent ones, newest first.
- [ ] Each item shows the question and the answer together. If an answer contains HTML such as `<b>x</b>`, it is shown literally and not interpreted as a tag.
- [ ] Clicking "Clear" empties the list and shows the "No history yet" message. After a page reload, the list is empty.
- [ ] Error responses are not added to the list.
- [ ] `app/index.html` contains none of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `localStorage` and `sessionStorage`, and has no inline event handler attributes (verified by a static check test).
- [ ] The static check test also verifies that the "Clear" button exists, and an authenticated `GET /` still returns `200`.
- [ ] The existing screen elements (the runtime chips, the refresh button, the traffic distribution button and the example questions) still work.
- [ ] `python -m unittest discover -s app/tests -v` passes.

### Constraints

- Scope of changes: `app/index.html` and `app/tests/` (add a static check test). Do not change the server code, the API or `app/requirements.txt`.
- Do not add external CDNs, fonts, scripts or UI frameworks.
- Put model output on screen only with `textContent` and DOM APIs.
- Do not weaken the existing CSP or the accessibility attributes (such as `aria-live`).
- If possible, run the app with `LLM_BACKEND=mock`, check it in the browser, and leave the result or a screenshot in the PR description.

### How to test

```bash
python -m unittest discover -s app/tests -v
```

Manual check (optional): start the server on a temporary port and open it in a browser. The user name is `demo`, and you can see the password with `echo "$DEMO_PASSWORD"`.

```bash
export DEMO_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(12))')"
LLM_BACKEND=mock PORT=8081 python -m app.server
```

Open `http://127.0.0.1:8081/` in the browser, send 12 questions, and check that the list shows 10 items and that "Clear" empties it.

### Out of scope

- Server-side conversation storage, per-user history and persistent storage (`localStorage`, cookies, a database)
- Exporting conversations, search, Markdown rendering and streaming responses
- Introducing a UI framework or build tool
- Changes to the slides and the `demos/` docs

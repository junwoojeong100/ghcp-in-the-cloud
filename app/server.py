import base64
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from anthropic import AnthropicFoundry

MODEL = os.getenv("FOUNDRY_MODEL", "claude-sonnet-5-5")
MAX_MESSAGE_LENGTH = 2_000
MAX_REQUEST_SIZE = 8_192


def answer(message):
    resource = os.getenv("FOUNDRY_RESOURCE")
    api_key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
    if not resource or not api_key:
        raise RuntimeError("Microsoft Foundry credentials are not configured")

    client = AnthropicFoundry(api_key=api_key, resource=resource)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4_096,
        output_config={"effort": "max"},
        messages=[{"role": "user", "content": message}],
    )
    return "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )


class DemoHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        if self.path == "/":
            if not self._authorized():
                return
            body = Path(__file__).with_name("index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        if not self._authorized():
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid request"})
            return
        if length < 1 or length > MAX_REQUEST_SIZE:
            self._send_json(400, {"error": "Invalid request size"})
            return

        try:
            payload = json.loads(self.rfile.read(length))
            message = payload.get("message", "").strip()
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, TypeError):
            self._send_json(400, {"error": "Invalid request"})
            return
        if not isinstance(message, str) or not message or len(message) > MAX_MESSAGE_LENGTH:
            self._send_json(400, {"error": "Message must contain 1–2000 characters"})
            return

        try:
            self._send_json(200, {"answer": answer(message)})
        except RuntimeError:
            self._send_json(503, {"error": "Microsoft Foundry is not configured"})
        except Exception:
            self._send_json(502, {"error": "The model request failed"})

    def _authorized(self):
        password = os.getenv("DEMO_PASSWORD")
        if not password:
            self._send_json(503, {"error": "Demo access is not configured"})
            return False

        expected = "Basic " + base64.b64encode(f"demo:{password}".encode()).decode()
        if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Cloud Copilot Demo"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        return True

    def log_message(self, format, *args):
        super().log_message(format, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), DemoHandler)
    server.serve_forever()

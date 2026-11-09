import base64
import io
import json
import os
import unittest
from unittest.mock import patch

from app.server import DemoHandler, answer


class DemoHandlerTests(unittest.TestCase):
    def request(self, method, path, body=b"", authenticated=True):
        handler = DemoHandler.__new__(DemoHandler)
        handler.path = path
        handler.command = method
        handler.headers = {"Content-Length": str(len(body))}
        if authenticated:
            handler.headers["Authorization"] = "Basic " + base64.b64encode(
                b"demo:test"
            ).decode()
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler._headers = []
        handler.send_response = lambda status: setattr(handler, "_status", status)
        handler.send_header = lambda name, value: handler._headers.append((name, value))
        handler.end_headers = lambda: None
        with patch.dict(os.environ, {"DEMO_PASSWORD": "test"}):
            getattr(handler, f"do_{method}")()
        return handler._status, handler.wfile.getvalue()

    def test_health_endpoint(self):
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_chat_rejects_empty_message(self):
        status, body = self.request("POST", "/api/chat", b'{"message":"  "}')
        self.assertEqual(status, 400)
        self.assertIn("Message must", json.loads(body)["error"])

    def test_chat_rejects_oversized_body(self):
        status, body = self.request("POST", "/api/chat", b"x" * 8_193)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "Invalid request size")

    def test_chat_reports_missing_foundry_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            status, body = self.request("POST", "/api/chat", b'{"message":"hello"}')

        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {"error": "Microsoft Foundry is not configured"})

    def test_chat_requires_demo_authentication(self):
        status, _ = self.request("POST", "/api/chat", b'{"message":"hello"}', authenticated=False)
        self.assertEqual(status, 401)

    @patch("app.server.AnthropicFoundry")
    def test_answer_uses_foundry_claude_max_effort(self, client_class):
        content = type("Content", (), {"type": "text", "text": "안녕하세요"})()
        client_class.return_value.messages.create.return_value.content = [content]
        with patch.dict(
            os.environ,
            {"FOUNDRY_RESOURCE": "demo-resource", "ANTHROPIC_FOUNDRY_API_KEY": "test-key"},
        ):
            result = answer("안녕")

        self.assertEqual(result, "안녕하세요")
        client_class.assert_called_once_with(api_key="test-key", resource="demo-resource")
        client_class.return_value.messages.create.assert_called_once_with(
            model="claude-sonnet-5-5",
            max_tokens=4_096,
            output_config={"effort": "max"},
            messages=[{"role": "user", "content": "안녕"}],
        )

    def test_answer_requires_foundry_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                answer("안녕")


if __name__ == "__main__":
    unittest.main()

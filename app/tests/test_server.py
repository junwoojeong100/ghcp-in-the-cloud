import base64
import http.client
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from app import server

PASSWORD = "test-password"
REPO_ROOT = Path(__file__).resolve().parents[2]


def basic(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


class Reply:
    def __init__(self, response, body):
        self.status = response.status
        self.headers = response.headers
        self.body = body

    def json(self):
        return json.loads(self.body)


class ServerTestCase(unittest.TestCase):
    """Runs the real handler on an ephemeral port with an isolated environment."""

    @classmethod
    def setUpClass(cls):
        quiet = patch.object(server.DemoHandler, "log_message", lambda *args, **kwargs: None)
        quiet.start()
        cls.addClassCleanup(quiet.stop)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.DemoHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        env = patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD, "LLM_BACKEND": "mock"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        server._foundry_client.cache_clear()
        server._token_provider.cache_clear()
        self.addCleanup(server._foundry_client.cache_clear)
        self.addCleanup(server._token_provider.cache_clear)

    def call(self, method, path, body=None, authorization=True, declared_length=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            payload = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
            connection.putrequest(method, path)
            if authorization is True:
                connection.putheader("Authorization", basic("demo", PASSWORD))
            elif authorization:
                connection.putheader("Authorization", authorization)
            if payload is not None or declared_length is not None:
                length = declared_length if declared_length is not None else len(payload)
                connection.putheader("Content-Type", "application/json")
                connection.putheader("Content-Length", str(length))
            connection.endheaders()
            if payload is not None:
                connection.send(payload)
            response = connection.getresponse()
            return Reply(response, response.read())
        finally:
            connection.close()

    def chat(self, message="안녕", **kwargs):
        return self.call("POST", "/api/chat", {"message": message}, **kwargs)


class HttpBehaviourTests(ServerTestCase):
    def test_health_endpoint_needs_no_authentication(self):
        reply = self.call("GET", "/healthz", authorization=False)
        self.assertEqual(reply.status, 200)
        self.assertEqual(reply.json(), {"status": "ok"})

    def test_health_endpoint_ignores_query_string(self):
        self.assertEqual(self.call("GET", "/healthz?probe=1", authorization=False).status, 200)

    def test_everything_else_requires_authentication(self):
        for method, path in (("GET", "/"), ("GET", "/api/info"), ("POST", "/api/chat")):
            with self.subTest(path=path):
                reply = self.call(method, path, b'{"message":"hi"}' if method == "POST" else None, authorization=False)
                self.assertEqual(reply.status, 401)
                self.assertIn("Basic", reply.headers["WWW-Authenticate"])

    def test_wrong_password_and_non_ascii_header_are_rejected(self):
        self.assertEqual(self.call("GET", "/api/info", authorization=basic("demo", "wrong")).status, 401)
        self.assertEqual(self.call("GET", "/api/info", authorization="Basic \xe4\xf6").status, 401)

    def test_unconfigured_password_fails_closed(self):
        del os.environ["DEMO_PASSWORD"]
        self.assertEqual(self.call("GET", "/api/info").status, 503)

    def test_unknown_paths_return_404(self):
        self.assertEqual(self.call("GET", "/nope").status, 404)
        self.assertEqual(self.call("POST", "/nope", b"{}").status, 404)

    def test_index_page_uses_a_fresh_csp_nonce(self):
        first = self.call("GET", "/")
        second = self.call("GET", "/")
        self.assertEqual(first.status, 200)
        self.assertIn("text/html", first.headers["Content-Type"])
        self.assertNotIn(b"__CSP_NONCE__", first.body)

        policy = first.headers["Content-Security-Policy"]
        nonce = re.search(r"script-src 'nonce-([^']+)'", policy).group(1)
        self.assertIn(f"style-src 'nonce-{nonce}'", policy)
        self.assertEqual(first.body.count(f'nonce="{nonce}"'.encode()), 2)
        self.assertNotEqual(policy, second.headers["Content-Security-Policy"])

    def test_responses_carry_security_headers(self):
        reply = self.call("GET", "/api/info")
        self.assertEqual(reply.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(reply.headers["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", reply.headers["Content-Security-Policy"])
        self.assertEqual(reply.headers["Server"], "cloud-copilot-demo")


class ChatValidationTests(ServerTestCase):
    def test_rejects_empty_message(self):
        reply = self.chat("   ")
        self.assertEqual(reply.status, 400)
        self.assertIn("Message must", reply.json()["error"])

    def test_rejects_message_that_is_too_long(self):
        self.assertEqual(self.chat("가" * 2_001).status, 400)
        self.assertEqual(self.chat("가" * 2_000).status, 200)

    def test_rejects_oversized_body_without_reading_it(self):
        reply = self.call("POST", "/api/chat", declared_length=32_769)
        self.assertEqual(reply.status, 400)
        self.assertEqual(reply.json()["error"], "Invalid request size")

    def test_rejects_missing_body(self):
        self.assertEqual(self.call("POST", "/api/chat").status, 400)

    def test_rejects_malformed_payloads(self):
        for body in (b"not json", b"[1, 2]", b'{"message": 42}', b'{"msg": "hi"}', b"\xff\xfe"):
            with self.subTest(body=body):
                self.assertEqual(self.call("POST", "/api/chat", body).status, 400)


class MockBackendTests(ServerTestCase):
    def test_info_describes_the_mock_runtime(self):
        os.environ["APP_VERSION"] = "v7"
        info = self.call("GET", "/api/info").json()
        self.assertEqual(info["backend"], "mock")
        self.assertEqual(info["auth"], "none")
        self.assertEqual(info["model"], "mock")
        self.assertIsNone(info["effort"])
        self.assertEqual(info["platform"], "local")
        self.assertEqual(info["version"], "v7")
        self.assertTrue(info["instance"])

    def test_chat_returns_a_labelled_mock_answer_with_server_identity(self):
        os.environ["APP_VERSION"] = "v2"
        data = self.chat("AKS가 뭐야?").json()
        self.assertTrue(data["answer"].startswith("[mock]"))
        self.assertIn("Kubernetes", data["answer"])
        self.assertEqual(data["served_by"]["version"], "v2")

    def test_mock_answers_follow_the_topic_of_the_question(self):
        self.assertIn("scale-to-zero", server.mock_answer("ACA는 뭐가 좋아?"))
        self.assertIn("OIDC", server.mock_answer("GitHub Actions 설명"))
        comparison = server.mock_answer("AKS와 ACA 차이")
        self.assertIn("Kubernetes", comparison)
        self.assertIn("scale-to-zero", comparison)
        self.assertIn("LLM_BACKEND=foundry", server.mock_answer("전혀 상관없는 질문"))

    def test_mock_topics_do_not_match_inside_other_words(self):
        self.assertIn("LLM_BACKEND=foundry", server.mock_answer("vacation academy"))

    def test_mock_latency_simulates_a_slow_model(self):
        os.environ["MOCK_LATENCY_MS"] = "300"
        started = time.monotonic()
        reply = self.chat()
        self.assertEqual(reply.status, 200)
        self.assertGreaterEqual(time.monotonic() - started, 0.3)

    def test_invalid_mock_latency_is_a_configuration_error(self):
        for value in ("slow", "-1", "10001"):
            with self.subTest(value=value):
                os.environ["MOCK_LATENCY_MS"] = value
                reply = self.chat()
                self.assertEqual(reply.status, 503)
                self.assertIn("MOCK_LATENCY_MS", reply.json()["hint"])

    def test_unsupported_backend_is_a_configuration_error(self):
        os.environ["LLM_BACKEND"] = "openai"
        reply = self.chat()
        self.assertEqual(reply.status, 503)
        self.assertIn("LLM_BACKEND", reply.json()["hint"])


class PlatformDetectionTests(ServerTestCase):
    def test_container_apps_environment_is_detected(self):
        os.environ.update(
            CONTAINER_APP_NAME="ccd-app",
            CONTAINER_APP_REVISION="ccd-app--v2",
            CONTAINER_APP_REPLICA_NAME="ccd-app--v2-abc-123",
        )
        info = self.call("GET", "/api/info").json()
        self.assertEqual(info["platform"], "aca")
        self.assertEqual(info["revision"], "ccd-app--v2")
        self.assertEqual(info["instance"], "ccd-app--v2-abc-123")

    def test_kubernetes_settings_come_from_the_manifest(self):
        os.environ.update(APP_PLATFORM="aks", POD_NAME="cloud-copilot-demo-7d9-x2", APP_REVISION="7d9")
        info = self.call("GET", "/api/info").json()
        self.assertEqual((info["platform"], info["instance"], info["revision"]), ("aks", "cloud-copilot-demo-7d9-x2", "7d9"))

    def test_plain_kubernetes_is_not_reported_as_aks(self):
        os.environ["KUBERNETES_SERVICE_HOST"] = "10.0.0.1"
        self.assertEqual(self.call("GET", "/api/info").json()["platform"], "kubernetes")


def text_block(text):
    return type("TextBlock", (), {"type": "text", "text": text})()


def thinking_block():
    return type("ThinkingBlock", (), {"type": "thinking", "thinking": "internal reasoning"})()


class FoundryBackendTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        os.environ.update(LLM_BACKEND="foundry", FOUNDRY_RESOURCE="demo-resource")
        patcher = patch("app.server.AnthropicFoundry")
        self.client_class = patcher.start()
        self.addCleanup(patcher.stop)
        self.create = self.client_class.return_value.messages.create
        self.create.return_value.content = [thinking_block(), text_block("안녕하세요")]

    def test_api_key_mode_calls_claude_sonnet_5_5_with_max_effort(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        reply = self.chat("안녕")

        self.assertEqual(reply.json()["answer"], "안녕하세요")
        self.client_class.assert_called_once_with(
            api_key="test-key", resource="demo-resource", timeout=180.0, max_retries=1
        )
        self.create.assert_called_once_with(
            model="claude-sonnet-5-5",
            max_tokens=4_096,
            system=server.SYSTEM_PROMPT,
            output_config={"effort": "max"},
            messages=[{"role": "user", "content": "안녕"}],
        )

    def test_without_api_key_the_client_uses_entra_id_tokens(self):
        provider = object()
        with patch("app.server._token_provider", return_value=provider):
            self.assertEqual(self.chat().status, 200)

        self.client_class.assert_called_once_with(
            azure_ad_token_provider=provider, resource="demo-resource", timeout=180.0, max_retries=1
        )
        self.assertNotIn("api_key", self.client_class.call_args.kwargs)

    def test_token_provider_requests_the_foundry_scope(self):
        fake_identity = type(sys)("azure.identity")
        fake_identity.DefaultAzureCredential = lambda: "credential"
        fake_identity.get_bearer_token_provider = lambda credential, scope: (credential, scope)
        with patch.dict(sys.modules, {"azure": type(sys)("azure"), "azure.identity": fake_identity}):
            self.assertEqual(server._token_provider(), ("credential", "https://ai.azure.com/.default"))

    def test_client_is_reused_between_requests(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        self.chat()
        self.chat()
        self.assertEqual(self.client_class.call_count, 1)
        self.assertEqual(self.create.call_count, 2)

    def test_deployment_effort_and_token_budget_are_configurable(self):
        os.environ.update(FOUNDRY_MODEL="my-deployment", FOUNDRY_EFFORT="HIGH", FOUNDRY_MAX_TOKENS="8000")
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        self.chat()
        kwargs = self.create.call_args.kwargs
        self.assertEqual((kwargs["model"], kwargs["output_config"], kwargs["max_tokens"]), ("my-deployment", {"effort": "high"}, 8_000))

    def test_invalid_settings_are_reported_as_configuration_errors(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        for name, value in (
            ("FOUNDRY_EFFORT", "turbo"),
            ("FOUNDRY_MAX_TOKENS", "lots"),
            ("FOUNDRY_MAX_TOKENS", "100"),
            ("FOUNDRY_RESOURCE", "demo.services.ai.azure.com"),
            ("FOUNDRY_RESOURCE", ""),
        ):
            with self.subTest(name=name, value=value), patch.dict(os.environ, {name: value}):
                reply = self.chat()
                self.assertEqual(reply.status, 503)
                self.assertIn(name, reply.json()["hint"])
        self.create.assert_not_called()

    def test_missing_anthropic_package_is_a_configuration_error(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        with patch("app.server.AnthropicFoundry", None):
            reply = self.chat()
        self.assertEqual(reply.status, 503)
        self.assertIn("anthropic", reply.json()["hint"])

    def test_empty_text_response_explains_the_stop_reason(self):
        self.create.return_value.content = [thinking_block()]
        self.create.return_value.stop_reason = "max_tokens"
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        answer = self.chat().json()["answer"]
        self.assertIn("stop_reason=max_tokens", answer)
        self.assertIn("FOUNDRY_MAX_TOKENS", answer)

    def test_info_reports_the_auth_mode_without_leaking_the_key(self):
        os.environ["FOUNDRY_MODEL"] = "my-deployment"
        keyless = self.call("GET", "/api/info").json()
        self.assertEqual((keyless["auth"], keyless["model"], keyless["effort"]), ("entra-id", "my-deployment", "max"))

        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "super-secret-key"
        reply = self.call("GET", "/api/info")
        self.assertEqual(reply.json()["auth"], "api-key")
        self.assertNotIn(b"super-secret-key", reply.body)

    def test_upstream_failures_become_502_with_an_actionable_hint(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "super-secret-key"
        permission_denied = type("PermissionDeniedError", (Exception,), {})
        self.create.side_effect = permission_denied("Error code: 403")

        with self.assertLogs("cloud-copilot-demo", level="WARNING"):
            reply = self.chat()

        self.assertEqual(reply.status, 502)
        self.assertEqual(reply.json()["error"], "The model request failed")
        self.assertIn("Cognitive Services User", reply.json()["hint"])
        self.assertNotIn(b"super-secret-key", reply.body)

    def test_unknown_upstream_failures_have_no_hint(self):
        os.environ["ANTHROPIC_FOUNDRY_API_KEY"] = "test-key"
        self.create.side_effect = TimeoutError("slow")
        with self.assertLogs("cloud-copilot-demo", level="WARNING"):
            reply = self.chat()
        self.assertEqual(reply.status, 502)
        self.assertNotIn("hint", reply.json())

    def test_credential_errors_point_to_the_identity_setup(self):
        credential_error = type("CredentialUnavailableError", (Exception,), {})
        self.assertIn("Workload Identity", server.error_hint(credential_error("no credential")))


class GracefulShutdownTests(unittest.TestCase):
    def test_sigterm_stops_the_server_cleanly(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = {**os.environ, "PORT": str(port), "DEMO_PASSWORD": PASSWORD, "LLM_BACKEND": "mock"}
        process = subprocess.Popen(
            [sys.executable, "-m", "app.server"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(process.kill)

        deadline = time.monotonic() + 15
        while True:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                connection.request("GET", "/healthz")
                if connection.getresponse().status == 200:
                    break
            except OSError:
                if time.monotonic() > deadline or process.poll() is not None:
                    self.fail("server did not start")
                time.sleep(0.1)

        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(timeout=10), 0)


if __name__ == "__main__":
    unittest.main()

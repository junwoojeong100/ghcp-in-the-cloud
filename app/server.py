"""Cloud Copilot Demo: a small stdlib HTTP server in front of a model on Microsoft Foundry (default gpt-6.1-sol).

The same file runs locally, in Docker, on Azure Container Apps and on AKS.
Set LLM_BACKEND=mock to run everything without Azure or any installed dependency.
"""

import base64
import functools
import hmac
import json
import logging
import os
import re
import secrets
import signal
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

try:  # The mock backend must keep working when optional dependencies are missing.
    from anthropic import AnthropicFoundry
except ImportError:
    AnthropicFoundry = None

logger = logging.getLogger("cloud-copilot-demo")

DEFAULT_MODEL = "gpt-6.1-sol"  # Foundry *deployment* name, not the model id.
DEFAULT_EFFORT = "max"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
# "max" is a Claude level. GPT deployments accept low, medium, high and xhigh, so max means xhigh there.
OPENAI_EFFORT_ALIASES = {"max": "xhigh"}
PROVIDERS = ("anthropic", "openai")
DEFAULT_MAX_TOKENS = 4_096
MAX_MOCK_LATENCY_MS = 10_000
FOUNDRY_SCOPE = "https://ai.azure.com/.default"
REQUEST_TIMEOUT_SECONDS = 180.0  # Stay below the 240 s ingress limit of Azure Container Apps.
MAX_MESSAGE_LENGTH = 2_000
MAX_REQUEST_SIZE = 32_768  # Fits 2,000 characters even if a client escapes each one as \uXXXX (12 bytes).
INDEX_HTML = Path(__file__).with_name("index.html")

SYSTEM_PROMPT = (
    "You are the assistant inside a live demo of GitHub Copilot, GitHub Actions, "
    "Microsoft Foundry, Azure Kubernetes Service and Azure Container Apps. "
    "Answer in Korean, clearly and concisely (about 10 sentences at most)."
)

MOCK_PREFIX = "[mock] 실제 모델을 호출하지 않은 예시 응답입니다.\n\n"
MOCK_DEFAULT = (
    "mock 백엔드는 Azure 없이도 배포 파이프라인과 플랫폼 기능을 시연할 수 있게 해 줍니다. "
    "GitHub Actions, AKS, ACA, Foundry, Copilot에 대해 물어보면 주제별 예시 답변을 보여 드립니다. "
    "실제 모델 응답을 보려면 LLM_BACKEND=foundry 와 FOUNDRY_RESOURCE 를 설정하세요."
)
MOCK_TOPICS = (
    (
        re.compile(r"(?<![a-z])aks(?![a-z])|kubernetes|k8s|쿠버네티스", re.IGNORECASE),
        "AKS(Azure Kubernetes Service)는 관리형 Kubernetes입니다. 전체 Kubernetes API와 생태계를 "
        "그대로 쓰면서 컨트롤 플레인 운영은 Azure가 맡습니다. Workload Identity를 쓰면 Pod가 "
        "비밀 없이 Azure 서비스를 호출할 수 있습니다.",
    ),
    (
        re.compile(r"(?<![a-z])aca(?![a-z])|container apps|컨테이너 ?앱", re.IGNORECASE),
        "Azure Container Apps는 서버리스 컨테이너 플랫폼입니다. 클러스터를 직접 운영하지 않고도 "
        "HTTPS ingress, 리비전 기반 트래픽 분할, 요청이 없을 때 replica를 0으로 줄이는 "
        "scale-to-zero를 사용할 수 있습니다.",
    ),
    (
        re.compile(r"actions|워크플로|oidc|ci/cd", re.IGNORECASE),
        "GitHub Actions는 코드와 같은 저장소에서 CI/CD를 정의합니다. OIDC 페더레이션을 쓰면 "
        "저장된 클라우드 비밀 없이 Azure에 로그인할 수 있고, Environments로 배포 승인 단계를 둘 수 있습니다.",
    ),
    (
        re.compile(r"foundry|claude|파운드리|클로드", re.IGNORECASE),
        "Microsoft Foundry는 Claude를 포함한 모델을 Azure의 인증·권한·쿼터 체계 안에서 배포하고 "
        "사용하게 해 줍니다. 코드는 배포 이름만 바꿔서 모델을 교체할 수 있고, Entra ID 인증으로 "
        "API 키 없이 호출할 수도 있습니다.",
    ),
    (
        re.compile(r"copilot|코파일럿", re.IGNORECASE),
        "GitHub Copilot은 이슈에서 PR까지 AI 에이전트와 협업하게 해 줍니다. 저장소의 instructions, "
        "prompt files, custom agents로 팀의 표준을 AI에 전달하고, 결과는 사람 리뷰와 CI로 검증합니다.",
    ),
)

ERROR_HINTS = {
    "PermissionDeniedError": (
        "권한이 없습니다. 이 ID에 Foundry 계정의 'Cognitive Services User' 역할이 있는지 확인하세요 "
        "(역할 할당이 적용되기까지 몇 분 걸릴 수 있습니다)."
    ),
    "AuthenticationError": "인증에 실패했습니다. API 키 또는 Entra ID 토큰이 올바른지 확인하세요.",
    "NotFoundError": "배포를 찾을 수 없습니다. FOUNDRY_MODEL(배포 이름)과 FOUNDRY_RESOURCE를 확인하세요.",
    "RateLimitError": "요청 한도(쿼터)를 초과했습니다. 잠시 후 다시 시도하세요.",
    "CredentialUnavailableError": (
        "Entra ID 자격 증명을 찾지 못했습니다. 로컬은 `az login`, ACA는 관리 ID, "
        "AKS는 Workload Identity 설정을 확인하세요."
    ),
    "ClientAuthenticationError": (
        "Entra ID 토큰을 받지 못했습니다. 로컬은 `az login`, ACA는 관리 ID, "
        "AKS는 Workload Identity 설정을 확인하세요."
    ),
}


class ConfigurationError(RuntimeError):
    """The selected backend cannot be used because a setting is missing or invalid."""


class FoundryHTTPError(RuntimeError):
    """HTTP error from the OpenAI-compatible Foundry endpoint. Subclass names match ERROR_HINTS."""


class AuthenticationError(FoundryHTTPError):
    pass


class PermissionDeniedError(FoundryHTTPError):
    pass


class NotFoundError(FoundryHTTPError):
    pass


class RateLimitError(FoundryHTTPError):
    pass


HTTP_ERRORS = {401: AuthenticationError, 403: PermissionDeniedError, 404: NotFoundError, 429: RateLimitError}


def selected_backend():
    return os.getenv("LLM_BACKEND", "").strip().lower() or "foundry"


def foundry_settings():
    model = os.getenv("FOUNDRY_MODEL", "").strip() or DEFAULT_MODEL
    effort = os.getenv("FOUNDRY_EFFORT", "").strip().lower() or DEFAULT_EFFORT
    if effort not in EFFORT_LEVELS:
        raise ConfigurationError(f"FOUNDRY_EFFORT 는 {', '.join(EFFORT_LEVELS)} 중 하나여야 합니다.")
    explicit_provider = os.getenv("FOUNDRY_PROVIDER", "").strip().lower()
    if explicit_provider and explicit_provider not in PROVIDERS:
        raise ConfigurationError(f"FOUNDRY_PROVIDER 는 {', '.join(PROVIDERS)} 중 하나여야 합니다.")
    raw_tokens = os.getenv("FOUNDRY_MAX_TOKENS", "").strip()
    try:
        max_tokens = int(raw_tokens) if raw_tokens else DEFAULT_MAX_TOKENS
    except ValueError:
        max_tokens = 0
    if not 256 <= max_tokens <= 16_000:
        raise ConfigurationError("FOUNDRY_MAX_TOKENS 는 256 이상 16000 이하의 정수여야 합니다.")
    return model, effort, max_tokens


def provider(model):
    """anthropic for Claude deployments, openai for everything else. FOUNDRY_PROVIDER overrides the guess from the name."""
    explicit = os.getenv("FOUNDRY_PROVIDER", "").strip().lower()
    if explicit in PROVIDERS:
        return explicit
    return "anthropic" if model.lower().startswith("claude") else "openai"


def resolved_effort(model, effort):
    return effort if provider(model) == "anthropic" else OPENAI_EFFORT_ALIASES.get(effort, effort)


def foundry_api_key():
    return os.getenv("FOUNDRY_API_KEY", "").strip() or os.getenv("ANTHROPIC_FOUNDRY_API_KEY", "").strip()


def auth_mode():
    if selected_backend() == "mock":
        return "none"
    return "api-key" if foundry_api_key() else "entra-id"


@functools.lru_cache(maxsize=1)
def _token_provider():
    # Imported lazily: only the keyless Entra ID path needs azure-identity.
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    return get_bearer_token_provider(DefaultAzureCredential(), FOUNDRY_SCOPE)


@functools.lru_cache(maxsize=4)
def _foundry_client(resource, api_key):
    if AnthropicFoundry is None:
        raise ConfigurationError("anthropic 패키지가 설치되어 있지 않습니다. `pip install -r app/requirements.txt`")
    options = {"resource": resource, "timeout": REQUEST_TIMEOUT_SECONDS, "max_retries": 1}
    if api_key:
        return AnthropicFoundry(api_key=api_key, **options)
    return AnthropicFoundry(azure_ad_token_provider=_token_provider(), **options)


def foundry_answer(message):
    resource = os.getenv("FOUNDRY_RESOURCE", "").strip()
    if not resource:
        raise ConfigurationError(
            "FOUNDRY_RESOURCE 환경 변수에 Foundry 리소스 이름을 설정하세요. "
            "Azure 없이 시연하려면 LLM_BACKEND=mock 으로 실행하세요."
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,62}", resource):
        raise ConfigurationError("FOUNDRY_RESOURCE 에는 호스트 이름이 아니라 리소스 이름만 입력하세요.")
    model, effort, max_tokens = foundry_settings()
    if provider(model) == "anthropic":
        return claude_answer(resource, model, effort, max_tokens, message)
    return openai_answer(resource, model, resolved_effort(model, effort), max_tokens, message)


def no_text_answer(stop_reason):
    return (
        f"모델이 텍스트 응답을 반환하지 않았습니다 (stop_reason={stop_reason}). "
        "추론에 토큰을 모두 쓴 경우 FOUNDRY_MAX_TOKENS 를 늘려 보세요."
    )


def claude_answer(resource, model, effort, max_tokens, message):
    client = _foundry_client(resource, foundry_api_key())
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": message}],
    )
    # Claude 5.5 can also return thinking blocks; only the text blocks are for the user.
    text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    return text or no_text_answer(response.stop_reason)


def upstream_message(exc):
    """The service's own error text (never the prompt), shortened for the log."""
    try:
        return str(json.load(exc)["error"]["message"])[:200]
    except (ValueError, KeyError, TypeError, OSError):
        return exc.reason or "error"


def openai_answer(resource, model, effort, max_tokens, message):
    """GPT deployments use Foundry's OpenAI-compatible v1 endpoint; stdlib only, keyless with Entra ID."""
    api_key = foundry_api_key()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {_token_provider()()}"
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}],
        "max_completion_tokens": max_tokens,
        "reasoning_effort": effort,
    }
    request = Request(
        f"https://{resource}.services.ai.azure.com/openai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise HTTP_ERRORS.get(exc.code, FoundryHTTPError)(f"HTTP {exc.code}: {upstream_message(exc)}") from None
    choice = (payload.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    return text or no_text_answer(choice.get("finish_reason"))


def mock_latency_seconds():
    raw = os.getenv("MOCK_LATENCY_MS", "").strip()
    try:
        milliseconds = int(raw) if raw else 0
    except ValueError:
        milliseconds = -1
    if not 0 <= milliseconds <= MAX_MOCK_LATENCY_MS:
        raise ConfigurationError(f"MOCK_LATENCY_MS 는 0 이상 {MAX_MOCK_LATENCY_MS} 이하의 정수여야 합니다.")
    return milliseconds / 1000


def mock_answer(message):
    matched = [reply for pattern, reply in MOCK_TOPICS if pattern.search(message)]
    return MOCK_PREFIX + ("\n\n".join(matched[:2]) if matched else MOCK_DEFAULT)


def answer(message):
    backend = selected_backend()
    if backend == "mock":
        # A real model takes seconds; this lets in-flight requests pile up so autoscaling is visible.
        time.sleep(mock_latency_seconds())
        return mock_answer(message)
    if backend == "foundry":
        return foundry_answer(message)
    raise ConfigurationError("LLM_BACKEND 는 foundry 또는 mock 이어야 합니다.")


def error_hint(exc):
    for cls in type(exc).__mro__:
        if cls.__name__ in ERROR_HINTS:
            return ERROR_HINTS[cls.__name__]
    return None


def runtime_platform():
    explicit = os.getenv("APP_PLATFORM", "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("CONTAINER_APP_NAME"):
        return "aca"
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "kubernetes"
    return "local"


def served_by():
    return {
        "instance": os.getenv("CONTAINER_APP_REPLICA_NAME")
        or os.getenv("POD_NAME")
        or socket.gethostname(),
        "revision": os.getenv("CONTAINER_APP_REVISION") or os.getenv("APP_REVISION") or "",
        "version": os.getenv("APP_VERSION", "").strip() or "dev",
    }


def runtime_info():
    mock = selected_backend() == "mock"
    model = os.getenv("FOUNDRY_MODEL", "").strip() or DEFAULT_MODEL
    effort = os.getenv("FOUNDRY_EFFORT", "").strip().lower() or DEFAULT_EFFORT
    return {
        "app": "cloud-copilot-demo",
        "backend": selected_backend(),
        "model": "mock" if mock else model,
        "effort": None if mock else resolved_effort(model, effort),
        "auth": auth_mode(),
        "platform": runtime_platform(),
        **served_by(),
    }


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "cloud-copilot-demo"
    sys_version = ""
    timeout = 30  # Seconds a client may stall while sending a request.

    def _write(self, status, body, content_type, headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, payload, headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        policy = ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self._write(status, body, "application/json; charset=utf-8", (policy, *headers))

    def _send_index(self):
        nonce = secrets.token_urlsafe(16)
        body = INDEX_HTML.read_bytes().replace(b"__CSP_NONCE__", nonce.encode())
        policy = (
            "Content-Security-Policy",
            f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        )
        self._write(200, body, "text/html; charset=utf-8", (policy,))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._send_json(200, {"status": "ok"})
        elif path in ("/", "/api/info"):
            if not self._authorized():
                return
            if path == "/":
                self._send_index()
            else:
                self._send_json(200, runtime_info())
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        if not self._authorized():
            return

        message = self._read_message()
        if message is None:
            return

        try:
            self._send_json(200, {"answer": answer(message), "served_by": served_by()})
        except ConfigurationError as exc:
            logger.warning("Configuration error: %s", exc)
            self._send_json(503, {"error": "The service is not configured", "hint": str(exc)})
        except Exception as exc:  # noqa: BLE001 - every upstream failure becomes a 502.
            logger.warning("Model request failed: %s: %s", type(exc).__name__, exc)
            payload = {"error": "The model request failed"}
            hint = error_hint(exc)
            if hint:
                payload["hint"] = hint
            self._send_json(502, payload)

    def _read_message(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid request"})
            return None
        if length < 1 or length > MAX_REQUEST_SIZE:
            self._send_json(400, {"error": "Invalid request size"})
            return None

        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid request"})
            return None
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= MAX_MESSAGE_LENGTH:
            self._send_json(400, {"error": "Message must contain 1–2000 characters"})
            return None
        return message.strip()

    def _authorized(self):
        password = os.getenv("DEMO_PASSWORD")
        if not password:
            self._send_json(503, {"error": "Demo access is not configured"})
            return False

        expected = "Basic " + base64.b64encode(f"demo:{password}".encode()).decode()
        supplied = self.headers.get("Authorization", "")
        # Compare bytes: compare_digest rejects non-ASCII str input.
        if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            challenge = ("WWW-Authenticate", 'Basic realm="Cloud Copilot Demo", charset="UTF-8"')
            self._send_json(401, {"error": "Authentication required"}, (challenge,))
            return False
        return True

    def log_request(self, code="-", size="-"):
        if urlsplit(self.path).path == "/healthz":
            return  # Probes would otherwise flood the logs.
        super().log_request(code, size)

    def version_string(self):
        return self.server_version  # Do not advertise the Python version.


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), DemoHandler)

    # As PID 1 in a container Python ignores SIGTERM unless a handler is installed,
    # which would make rolling updates and scale-in wait for the kill timeout.
    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    logger.info("Listening on http://%s:%s (backend=%s)", host, port, selected_backend())
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""OpenAI-compatible model client with bounded output and safe gateway validation."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional
from urllib.parse import urlparse

import requests

from .constants import DEFAULT_BASE_URL, DEFAULT_MODEL
from .errors import ModelGatewayError, configuration_error, unavailable_error


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    return default if not raw else raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)).strip())
    except ValueError:
        value = default
    return max(0.0, min(value, 1.0))


def public_model_enabled() -> bool:
    return _env_flag("PUBLIC_MODEL_ENABLED", False)


def _public_model_key() -> str:
    # Never fall back to OPENAI_API_KEY: private/local keys must not become public credentials.
    return os.getenv("PUBLIC_MODEL_API_KEY", "").strip()


def _public_model_base_url() -> str:
    return os.getenv("PUBLIC_MODEL_BASE_URL", DEFAULT_BASE_URL).strip()


def _public_model_name() -> str:
    return os.getenv("PUBLIC_MODEL_MODEL", DEFAULT_MODEL).strip()


def public_model_available() -> bool:
    return bool(public_model_enabled() and _public_model_key() and _public_model_base_url() and _public_model_name())


def public_model_status() -> Dict[str, object]:
    available = public_model_available()
    return {
        "available": available,
        "provider": os.getenv("PUBLIC_MODEL_PROVIDER", "阿里云百炼 DashScope").strip() if available else "",
        "model": _public_model_name() if available else "",
        "user_override_allowed": _env_flag("ALLOW_USER_API_OVERRIDE", True),
    }


@dataclass
class LLMConfig:
    """Resolved model configuration without exposing server secrets to the browser."""

    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.35
    timeout: int = 120
    source: str = field(default="unconfigured", init=False)

    def __post_init__(self) -> None:
        supplied_key = self.api_key.strip()
        if supplied_key:
            if not _env_flag("ALLOW_USER_API_OVERRIDE", True):
                raise configuration_error("当前部署未开放自定义模型接口，请使用公共模型。")
            self.api_key = supplied_key
            self.base_url = self.base_url.strip()
            self.model = self.model.strip()
            self.temperature = max(0.0, min(float(self.temperature), 1.0))
            self.source = "user"
            return

        if public_model_available():
            self.api_key = _public_model_key()
            self.base_url = _public_model_base_url()
            self.model = _public_model_name()
            self.temperature = _env_float("PUBLIC_MODEL_TEMPERATURE", self.temperature)
            self.source = "server"
            return

        self.api_key = ""
        self.base_url = self.base_url.strip()
        self.model = self.model.strip()
        self.temperature = max(0.0, min(float(self.temperature), 1.0))

    @classmethod
    def from_env(cls) -> "LLMConfig":
        legacy_key = os.getenv("OPENAI_API_KEY", "").strip()
        if legacy_key:
            return cls(
                api_key=legacy_key,
                base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
                model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            )
        return cls(api_key="", base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL)


_PUBLIC_USAGE_LOCK = threading.Lock()
_PUBLIC_USAGE_DAY = ""
_PUBLIC_USAGE_COUNT = 0


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    return max(60, 86400 - (now.hour * 3600 + now.minute * 60 + now.second))


def _consume_public_model_quota() -> None:
    """Process-local fuse; provider-side budgets remain authoritative."""
    limit = _env_int("PUBLIC_MODEL_DAILY_REQUEST_LIMIT", 200)
    if limit <= 0:
        return

    global _PUBLIC_USAGE_DAY, _PUBLIC_USAGE_COUNT
    today = datetime.now(timezone.utc).date().isoformat()
    with _PUBLIC_USAGE_LOCK:
        if _PUBLIC_USAGE_DAY != today:
            _PUBLIC_USAGE_DAY, _PUBLIC_USAGE_COUNT = today, 0
        if _PUBLIC_USAGE_COUNT >= limit:
            raise ModelGatewayError(
                code="PUBLIC_MODEL_QUOTA_EXHAUSTED",
                user_message="今日公共体验额度已用完，请填写自己的 API Key 后继续使用。",
                status_code=429,
                retryable=True,
                retry_after=_seconds_until_utc_midnight(),
            )
        _PUBLIC_USAGE_COUNT += 1


def _allowed_hosts() -> set[str]:
    return {item.strip().lower() for item in os.getenv("LLM_ALLOWED_HOSTS", "").split(",") if item.strip()}


def _is_blocked_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified))


def _resolve_public_addresses(host: str, port: int) -> set[str]:
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise ModelGatewayError(
            code="MODEL_GATEWAY_UNREACHABLE",
            user_message="模型网关域名解析失败，请检查 Base URL。",
            status_code=502,
            retryable=True,
        ) from exc
    if not addresses or any(_is_blocked_ip(address) for address in addresses):
        raise configuration_error("Base URL 不能指向本机、内网或保留地址。")
    return addresses


def _validate_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"}:
        raise configuration_error("Base URL 只允许 http/https。")
    if parsed.scheme == "http" and not _env_flag("ALLOW_INSECURE_LLM_HTTP", False):
        raise configuration_error("Base URL 必须使用 HTTPS。")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise configuration_error("Base URL 格式不合法。")

    host = parsed.hostname.lower()
    allowlist = _allowed_hosts()
    if _env_flag("LLM_REQUIRE_HOST_ALLOWLIST", False) and not allowlist:
        raise configuration_error("当前部署要求配置 LLM_ALLOWED_HOSTS 后才能调用模型网关。")
    if allowlist and host not in allowlist:
        raise configuration_error("该模型网关不在服务端允许列表中。")

    _resolve_public_addresses(host, parsed.port or 443)
    return value


def _retry_after_seconds(response: requests.Response, default: int = 30) -> int:
    raw = response.headers.get("Retry-After", "").strip()
    return max(1, min(int(raw), 3600)) if raw.isdigit() else default


def _request_error(exc: requests.RequestException) -> ModelGatewayError:
    if isinstance(exc, requests.Timeout):
        return ModelGatewayError("MODEL_TIMEOUT", "模型响应超时，请缩短输入内容或稍后重试。", 504, True)
    if isinstance(exc, requests.ConnectionError):
        return ModelGatewayError("MODEL_CONNECTION_FAILED", "无法连接模型服务，请检查 Base URL 或稍后重试。", 502, True)
    return ModelGatewayError("MODEL_REQUEST_FAILED", "模型请求发送失败，请检查网络和模型配置。", 502, True)


def _http_error(response: requests.Response) -> ModelGatewayError:
    status = response.status_code
    if status == 401:
        return ModelGatewayError("MODEL_AUTH_FAILED", "模型接口鉴权失败，请检查 API Key。", 401, False)
    if status == 403:
        return ModelGatewayError("MODEL_PERMISSION_DENIED", "当前 API Key 无权使用该模型或接口。", 403, False)
    if status == 429:
        retry_after = _retry_after_seconds(response)
        return ModelGatewayError("MODEL_RATE_LIMITED", f"模型服务请求过于频繁，请在 {retry_after} 秒后重试。", 429, True, retry_after)
    if status in {400, 404, 409, 422}:
        return ModelGatewayError("MODEL_REQUEST_REJECTED", "模型拒绝了请求，请检查模型名称、Base URL 和输入内容。", 400, False)
    if status in {408, 504}:
        return ModelGatewayError("MODEL_TIMEOUT", "模型响应超时，请缩短输入内容或稍后重试。", 504, True)
    if status in {500, 502, 503}:
        return unavailable_error()
    return ModelGatewayError("MODEL_GATEWAY_ERROR", "模型网关返回异常，请检查配置或稍后重试。", 502, False)


def _output_limit_error() -> ModelGatewayError:
    return ModelGatewayError(
        code="MODEL_OUTPUT_LIMIT_EXCEEDED",
        user_message="模型输出超过服务端安全上限，请缩小任务范围后重试。",
        status_code=502,
        retryable=True,
    )


def _response_limit_error() -> ModelGatewayError:
    return ModelGatewayError(
        code="MODEL_RESPONSE_LIMIT_EXCEEDED",
        user_message="模型网关返回的数据超过服务端安全上限，请缩小任务范围或更换接口后重试。",
        status_code=502,
        retryable=True,
    )


def _stream_timeout_error() -> ModelGatewayError:
    return ModelGatewayError(
        code="MODEL_TIMEOUT",
        user_message="模型生成时间超过服务端上限，请缩小任务范围后重试。",
        status_code=504,
        retryable=True,
    )


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        complete = bool(self.config.api_key.strip() and self.config.base_url.strip() and self.config.model.strip())
        self._base_url = _validate_base_url(self.config.base_url) if complete else self.config.base_url.strip().rstrip("/")
        self._max_output_chars = _env_int("MODEL_MAX_OUTPUT_CHARS", 120000, 1000, 500000)
        self._max_completion_tokens = _env_int("MODEL_MAX_COMPLETION_TOKENS", 8192, 256, 32768)
        default_response_bytes = max(262144, self._max_output_chars * 8)
        self._max_response_bytes = _env_int("MODEL_MAX_RESPONSE_BYTES", default_response_bytes, 1024, 8_000_000)
        self._max_stream_seconds = _env_int("MODEL_MAX_STREAM_SECONDS", max(self.config.timeout, 180), 10, 1800)

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self._base_url and self.config.model)

    def _url(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }

    def _messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    def _payload(self, system_prompt: str, user_prompt: str, *, stream: bool = False) -> Dict[str, object]:
        return {
            "model": self.config.model,
            "messages": self._messages(system_prompt, user_prompt),
            "temperature": self.config.temperature,
            "max_tokens": self._max_completion_tokens,
            "stream": stream,
        }

    def _post(self, system_prompt: str, user_prompt: str, *, stream: bool) -> requests.Response:
        if self.config.source == "server":
            _consume_public_model_quota()

        # Re-check DNS immediately before connecting to narrow rebinding/TOCTOU exposure.
        _validate_base_url(self._base_url)
        try:
            # Always stream the HTTP body so a non-streaming model response cannot be
            # buffered without bounds by requests before our byte cap is enforced.
            response = requests.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(system_prompt, user_prompt, stream=stream),
                timeout=self.config.timeout,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise _request_error(exc) from exc

        if response.is_redirect:
            response.close()
            raise ModelGatewayError("MODEL_REDIRECT_REJECTED", "模型网关返回了不安全的重定向，请检查 Base URL。", 502, False)
        if not response.ok:
            error = _http_error(response)
            response.close()
            raise error

        content_length = response.headers.get("Content-Length", "").strip()
        if content_length.isdigit() and int(content_length) > self._max_response_bytes:
            response.close()
            raise _response_limit_error()
        return response

    def _read_json_body(self, response: requests.Response) -> object:
        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > self._max_response_bytes:
                    raise _response_limit_error()
                chunks.append(chunk)
        except ModelGatewayError:
            raise
        except requests.RequestException as exc:
            raise _request_error(exc) from exc

        raw = b"".join(chunks)
        encoding = getattr(response, "encoding", None) or "utf-8"
        try:
            return json.loads(raw.decode(encoding, errors="replace"))
        except (LookupError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModelGatewayError(
                "MODEL_BAD_RESPONSE",
                "模型返回了无法解析的数据，请更换模型或接口后重试。",
                502,
                False,
            ) from exc

    def _iter_bounded_lines(self, response: requests.Response, *, deadline: float) -> Iterator[str]:
        """Split a streamed HTTP body into lines without unbounded ``iter_lines`` buffering."""
        buffer = bytearray()
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if time.monotonic() > deadline:
                    raise _stream_timeout_error()
                if not chunk:
                    continue
                total += len(chunk)
                if total > self._max_response_bytes:
                    raise _response_limit_error()
                buffer.extend(chunk)
                while True:
                    newline = buffer.find(b"\n")
                    if newline < 0:
                        break
                    raw_line = bytes(buffer[:newline])
                    del buffer[: newline + 1]
                    yield raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
            if time.monotonic() > deadline:
                raise _stream_timeout_error()
            if buffer:
                yield bytes(buffer).rstrip(b"\r").decode("utf-8", errors="replace")
        except ModelGatewayError:
            raise
        except requests.RequestException as exc:
            raise _request_error(exc) from exc

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ModelGatewayError("MODEL_NOT_CONFIGURED", "公共模型尚未配置，请填写自己的 API Key、Base URL 和模型名称。", 400, False)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self._require_enabled()
        response = self._post(system_prompt, user_prompt, stream=False)
        try:
            data = self._read_json_body(response)
            try:
                content = str(data["choices"][0]["message"]["content"]).strip()  # type: ignore[index]
            except (KeyError, IndexError, TypeError) as exc:
                raise ModelGatewayError("MODEL_BAD_RESPONSE", "模型返回格式不兼容，请检查模型接口。", 502, False) from exc
            if not content:
                raise ModelGatewayError("MODEL_EMPTY_RESPONSE", "模型没有返回有效内容，请重新生成或更换模型。", 502, True)
            if len(content) > self._max_output_chars:
                raise _output_limit_error()
            return content
        finally:
            response.close()

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        self._require_enabled()
        response = self._post(system_prompt, user_prompt, stream=True)
        yielded = False
        total_chars = 0
        deadline = time.monotonic() + self._max_stream_seconds
        try:
            for raw_line in self._iter_bounded_lines(response, deadline=deadline):
                line = raw_line.strip()
                if line.startswith("data:"):
                    line = line[5:].strip()
                if not line or line == "[DONE]":
                    if line == "[DONE]":
                        break
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("error"):
                    raise ModelGatewayError("MODEL_GATEWAY_ERROR", "模型网关在生成过程中返回异常，请稍后重试。", 502, True)
                choices = data.get("choices") or []
                if not choices:
                    continue
                choice = choices[0] or {}
                content = (choice.get("delta") or {}).get("content") or (choice.get("message") or {}).get("content") or choice.get("text") or ""
                if content:
                    text = str(content)
                    total_chars += len(text)
                    if total_chars > self._max_output_chars:
                        raise _output_limit_error()
                    yielded = True
                    yield text
            if not yielded:
                raise ModelGatewayError("MODEL_EMPTY_RESPONSE", "模型没有返回有效内容，请重新生成或更换模型。", 502, True)
        finally:
            response.close()

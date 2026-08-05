# -*- coding: utf-8 -*-
"""OpenAI-compatible client with stable, user-safe error classification."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional
from urllib.parse import urlparse

import requests

from .constants import DEFAULT_BASE_URL, DEFAULT_MODEL
from .errors import ModelGatewayError, configuration_error, unavailable_error


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.0, min(value, 1.0))


def _public_model_key() -> str:
    return (os.getenv("PUBLIC_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()


def _public_model_base_url() -> str:
    return (
        os.getenv("PUBLIC_MODEL_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_BASE_URL
    ).strip()


def _public_model_name() -> str:
    return (
        os.getenv("PUBLIC_MODEL_MODEL")
        or os.getenv("OPENAI_MODEL")
        or DEFAULT_MODEL
    ).strip()


def public_model_available() -> bool:
    """Return whether the server has a complete public/demo model configuration."""

    return bool(_public_model_key() and _public_model_base_url() and _public_model_name())


@dataclass
class LLMConfig:
    """Resolved model configuration.

    A request with its own API key uses the user-supplied compatible endpoint. A request
    without an API key may use the server-side public model. When the public key is used,
    the base URL and model are always taken from trusted environment variables so a client
    cannot redirect the server secret to an attacker-controlled gateway.
    """

    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.35
    timeout: int = 120
    source: str = field(default="unconfigured", init=False)

    def __post_init__(self) -> None:
        supplied_key = self.api_key.strip()
        allow_user_override = _env_flag("ALLOW_USER_API_OVERRIDE", True)

        if supplied_key:
            if not allow_user_override:
                raise configuration_error("当前部署未开放自定义模型接口，请使用公共模型。")
            self.api_key = supplied_key
            self.base_url = self.base_url.strip()
            self.model = self.model.strip()
            self.temperature = max(0.0, min(float(self.temperature), 1.0))
            self.source = "user"
            return

        public_key = _public_model_key()
        if public_key:
            self.api_key = public_key
            self.base_url = _public_model_base_url()
            self.model = _public_model_name()
            self.temperature = _env_float("PUBLIC_MODEL_TEMPERATURE", self.temperature)
            self.source = "server"
            return

        self.api_key = ""
        self.base_url = self.base_url.strip()
        self.model = self.model.strip()
        self.temperature = max(0.0, min(float(self.temperature), 1.0))
        self.source = "unconfigured"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        # Empty client credentials intentionally trigger the secure server-side resolver.
        return cls(api_key="", base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL)


_PUBLIC_USAGE_LOCK = threading.Lock()
_PUBLIC_USAGE_DAY = ""
_PUBLIC_USAGE_COUNT = 0


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = tomorrow.replace(day=now.day) if False else tomorrow
    # Avoid date arithmetic dependencies while keeping Retry-After bounded and useful.
    elapsed = now.hour * 3600 + now.minute * 60 + now.second
    return max(60, 86400 - elapsed)


def _consume_public_model_quota() -> None:
    """Apply a process-local safety fuse to public-key model calls.

    Provider-side spending limits remain the authoritative cost control. This local fuse is
    deliberately simple and resets after a process restart, so it supplements rather than
    replaces provider budgets and the existing per-client rate/concurrency limits.
    """

    limit = _env_int("PUBLIC_MODEL_DAILY_REQUEST_LIMIT", 200)
    if limit <= 0:
        return

    global _PUBLIC_USAGE_DAY, _PUBLIC_USAGE_COUNT
    today = datetime.now(timezone.utc).date().isoformat()
    with _PUBLIC_USAGE_LOCK:
        if _PUBLIC_USAGE_DAY != today:
            _PUBLIC_USAGE_DAY = today
            _PUBLIC_USAGE_COUNT = 0
        if _PUBLIC_USAGE_COUNT >= limit:
            raise ModelGatewayError(
                code="PUBLIC_MODEL_QUOTA_EXHAUSTED",
                user_message="今日公共体验额度已用完，请填写自己的 API Key 后继续使用。",
                status_code=429,
                retryable=True,
                retry_after=_seconds_until_utc_midnight(),
            )
        _PUBLIC_USAGE_COUNT += 1


def _is_blocked_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _allowed_hosts() -> set[str]:
    raw = os.getenv("LLM_ALLOWED_HOSTS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _validate_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    parsed = urlparse(value)

    if parsed.scheme not in {"https", "http"}:
        raise configuration_error("Base URL 只允许 http/https。")
    if parsed.scheme == "http" and os.getenv("ALLOW_INSECURE_LLM_HTTP", "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise configuration_error("Base URL 必须使用 HTTPS。")
    if not parsed.hostname or parsed.username or parsed.password:
        raise configuration_error("Base URL 格式不合法。")
    if parsed.query or parsed.fragment:
        raise configuration_error("Base URL 不能带 query 或 fragment。")

    host = parsed.hostname.lower()
    allowlist = _allowed_hosts()
    if allowlist and host not in allowlist:
        raise configuration_error("该模型网关不在服务端允许列表中。")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
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

    return value


def _retry_after_seconds(response: requests.Response, default: int = 30) -> int:
    raw = response.headers.get("Retry-After", "").strip()
    if raw.isdigit():
        return max(1, min(int(raw), 3600))
    return default


def _request_error(exc: requests.RequestException) -> ModelGatewayError:
    if isinstance(exc, requests.Timeout):
        return ModelGatewayError(
            code="MODEL_TIMEOUT",
            user_message="模型响应超时，请缩短输入内容或稍后重试。",
            status_code=504,
            retryable=True,
        )
    if isinstance(exc, requests.ConnectionError):
        return ModelGatewayError(
            code="MODEL_CONNECTION_FAILED",
            user_message="无法连接模型服务，请检查 Base URL 或稍后重试。",
            status_code=502,
            retryable=True,
        )
    return ModelGatewayError(
        code="MODEL_REQUEST_FAILED",
        user_message="模型请求发送失败，请检查网络和模型配置。",
        status_code=502,
        retryable=True,
    )


def _http_error(response: requests.Response) -> ModelGatewayError:
    status = response.status_code
    if status == 401:
        return ModelGatewayError(
            code="MODEL_AUTH_FAILED",
            user_message="模型接口鉴权失败，请检查 API Key。",
            status_code=401,
            retryable=False,
        )
    if status == 403:
        return ModelGatewayError(
            code="MODEL_PERMISSION_DENIED",
            user_message="当前 API Key 无权使用该模型或接口。",
            status_code=403,
            retryable=False,
        )
    if status == 429:
        retry_after = _retry_after_seconds(response)
        return ModelGatewayError(
            code="MODEL_RATE_LIMITED",
            user_message=f"模型服务请求过于频繁，请在 {retry_after} 秒后重试。",
            status_code=429,
            retryable=True,
            retry_after=retry_after,
        )
    if status in {400, 404, 409, 422}:
        return ModelGatewayError(
            code="MODEL_REQUEST_REJECTED",
            user_message="模型拒绝了请求，请检查模型名称、Base URL 和输入内容。",
            status_code=400,
            retryable=False,
        )
    if status in {408, 504}:
        return ModelGatewayError(
            code="MODEL_TIMEOUT",
            user_message="模型响应超时，请缩短输入内容或稍后重试。",
            status_code=504,
            retryable=True,
        )
    if status in {500, 502, 503}:
        return unavailable_error()
    return ModelGatewayError(
        code="MODEL_GATEWAY_ERROR",
        user_message="模型网关返回异常，请检查配置或稍后重试。",
        status_code=502,
        retryable=False,
    )


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        complete = bool(
            self.config.api_key.strip()
            and self.config.base_url.strip()
            and self.config.model.strip()
        )
        self._base_url = (
            _validate_base_url(self.config.base_url)
            if complete
            else self.config.base_url.strip().rstrip("/")
        )

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
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _payload(self, system_prompt: str, user_prompt: str, *, stream: bool = False) -> Dict[str, object]:
        return {
            "model": self.config.model,
            "messages": self._messages(system_prompt, user_prompt),
            "temperature": self.config.temperature,
            "stream": stream,
        }

    def _post(self, system_prompt: str, user_prompt: str, *, stream: bool) -> requests.Response:
        if self.config.source == "server":
            _consume_public_model_quota()
        try:
            response = requests.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(system_prompt, user_prompt, stream=stream),
                timeout=self.config.timeout,
                stream=stream,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise _request_error(exc) from exc

        if response.is_redirect:
            response.close()
            raise ModelGatewayError(
                code="MODEL_REDIRECT_REJECTED",
                user_message="模型网关返回了不安全的重定向，请检查 Base URL。",
                status_code=502,
                retryable=False,
            )
        if not response.ok:
            error = _http_error(response)
            response.close()
            raise error
        return response

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ModelGatewayError(
                code="MODEL_NOT_CONFIGURED",
                user_message="公共模型尚未配置，请填写自己的 API Key、Base URL 和模型名称。",
                status_code=400,
                retryable=False,
            )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self._require_enabled()
        response = self._post(system_prompt, user_prompt, stream=False)
        try:
            try:
                data = response.json()
            except ValueError as exc:
                raise ModelGatewayError(
                    code="MODEL_BAD_RESPONSE",
                    user_message="模型返回了无法解析的数据，请更换模型或接口后重试。",
                    status_code=502,
                    retryable=False,
                ) from exc
            try:
                content = str(data["choices"][0]["message"]["content"]).strip()
            except (KeyError, IndexError, TypeError) as exc:
                raise ModelGatewayError(
                    code="MODEL_BAD_RESPONSE",
                    user_message="模型返回格式不兼容，请检查模型接口。",
                    status_code=502,
                    retryable=False,
                ) from exc
            if not content:
                raise ModelGatewayError(
                    code="MODEL_EMPTY_RESPONSE",
                    user_message="模型没有返回有效内容，请重新生成或更换模型。",
                    status_code=502,
                    retryable=True,
                )
            return content
        finally:
            response.close()

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        self._require_enabled()
        response = self._post(system_prompt, user_prompt, stream=True)
        yielded = False
        try:
            try:
                for raw_line in response.iter_lines(chunk_size=1, decode_unicode=True):
                    if not raw_line:
                        continue
                    if isinstance(raw_line, bytes):
                        raw_line = raw_line.decode("utf-8", errors="replace")
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
                        raise ModelGatewayError(
                            code="MODEL_GATEWAY_ERROR",
                            user_message="模型网关在生成过程中返回异常，请稍后重试。",
                            status_code=502,
                            retryable=True,
                        )
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0] or {}
                    delta = choice.get("delta") or {}
                    message = choice.get("message") or {}
                    content = delta.get("content") or message.get("content") or choice.get("text") or ""
                    if content:
                        yielded = True
                        yield str(content)
            except requests.RequestException as exc:
                raise _request_error(exc) from exc
            if not yielded:
                raise ModelGatewayError(
                    code="MODEL_EMPTY_RESPONSE",
                    user_message="模型没有返回有效内容，请重新生成或更换模型。",
                    status_code=502,
                    retryable=True,
                )
        finally:
            response.close()

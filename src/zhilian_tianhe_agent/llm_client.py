# -*- coding: utf-8 -*-
"""OpenAI-compatible client."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional
from urllib.parse import urlparse

import requests

from .constants import DEFAULT_BASE_URL, DEFAULT_MODEL


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.35
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        )


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
        raise RuntimeError("Base URL 只允许 http/https。")
    if parsed.scheme == "http" and os.getenv("ALLOW_INSECURE_LLM_HTTP", "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise RuntimeError("Base URL 必须使用 HTTPS。")
    if not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("Base URL 格式不合法。")
    if parsed.query or parsed.fragment:
        raise RuntimeError("Base URL 不能带 query 或 fragment。")

    host = parsed.hostname.lower()
    allowlist = _allowed_hosts()
    if allowlist and host not in allowlist:
        raise RuntimeError("该模型网关不在服务端允许列表中。")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise RuntimeError("模型网关域名解析失败。") from exc

    if not addresses or any(_is_blocked_ip(address) for address in addresses):
        raise RuntimeError("Base URL 不能指向本机、内网或保留地址。")

    return value


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self._base_url = _validate_base_url(self.config.base_url) if self.config.base_url else ""

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self._base_url and self.config.model)

    def _url(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
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

    @staticmethod
    def _http_error(resp: requests.Response) -> RuntimeError:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        text = str(detail).replace("\n", " ")[:800]
        return RuntimeError(f"模型接口返回错误：HTTP {resp.status_code}，{text}")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled:
            raise RuntimeError("未配置 API Key，请先在页面中填写 API Key、Base URL 和模型名称。")

        resp = requests.post(
            self._url(),
            headers=self._headers(),
            json=self._payload(system_prompt, user_prompt, stream=False),
            timeout=self.config.timeout,
            allow_redirects=False,
        )
        if resp.is_redirect:
            raise RuntimeError("模型网关返回了重定向，已拒绝继续请求。")
        if not resp.ok:
            raise self._http_error(resp)
        data = resp.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("模型接口返回格式不兼容。") from exc

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        if not self.enabled:
            raise RuntimeError("未配置 API Key，请先在页面中填写 API Key、Base URL 和模型名称。")

        with requests.post(
            self._url(),
            headers=self._headers(),
            json=self._payload(system_prompt, user_prompt, stream=True),
            timeout=self.config.timeout,
            stream=True,
            allow_redirects=False,
        ) as resp:
            if resp.is_redirect:
                raise RuntimeError("模型网关返回了重定向，已拒绝继续请求。")
            if not resp.ok:
                raise self._http_error(resp)

            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

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
                    # 部分兼容网关会塞心跳，丢掉就行。
                    continue

                choices = data.get("choices") or []
                if not choices:
                    continue

                choice = choices[0] or {}
                delta = choice.get("delta") or {}
                message = choice.get("message") or {}
                content = delta.get("content") or message.get("content") or choice.get("text") or ""

                if content:
                    yield str(content)

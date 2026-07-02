# -*- coding: utf-8 -*-
"""OpenAI兼容大模型客户端，支持 DashScope compatible-mode 与流式输出。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

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


class LLMClient:
    """简单、稳定的 chat completions 客户端。

    不配置 API Key 时不生成业务结果，由调用方提示用户先完成模型配置。
    支持普通一次性返回，也支持 OpenAI-compatible 的 stream=True 流式返回。
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self.config.base_url and self.config.model)

    def _url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/chat/completions"

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
        except Exception:  # noqa: BLE001
            detail = resp.text
        return RuntimeError(f"模型接口返回错误：HTTP {resp.status_code}，{detail}")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled:
            raise RuntimeError("未配置 API Key，请先在页面中填写 API Key、Base URL 和模型名称。")

        resp = requests.post(
            self._url(),
            headers=self._headers(),
            json=self._payload(system_prompt, user_prompt, stream=False),
            timeout=self.config.timeout,
        )
        if not resp.ok:
            raise self._http_error(resp)
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """逐段返回模型输出文本。

        兼容 OpenAI / DashScope compatible-mode 常见 SSE 格式：
        data: {"choices":[{"delta":{"content":"..."}}]}
        data: [DONE]
        """
        if not self.enabled:
            raise RuntimeError("未配置 API Key，请先在页面中填写 API Key、Base URL 和模型名称。")

        with requests.post(
            self._url(),
            headers=self._headers(),
            json=self._payload(system_prompt, user_prompt, stream=True),
            timeout=self.config.timeout,
            stream=True,
        ) as resp:
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
                    # 某些网关可能会输出心跳或非 JSON 片段，直接跳过。
                    continue

                choices = data.get("choices") or []
                if not choices:
                    continue

                choice = choices[0] or {}
                delta = choice.get("delta") or {}
                message = choice.get("message") or {}

                content = (
                    delta.get("content")
                    or message.get("content")
                    or choice.get("text")
                    or ""
                )

                if content:
                    yield str(content)

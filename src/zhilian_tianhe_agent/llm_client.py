# -*- coding: utf-8 -*-
"""OpenAI兼容大模型客户端，支持DashScope compatible-mode。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from .constants import DEFAULT_BASE_URL, DEFAULT_MODEL


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.35
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        )


class LLMClient:
    """简单、稳定的chat completions客户端。

    不配置 API Key 时不生成业务结果，由调用方提示用户先完成模型配置。
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self.config.base_url and self.config.model)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled:
            raise RuntimeError("未配置 API Key，请先在页面中填写 API Key、Base URL 和模型名称。")

        base_url = self.config.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

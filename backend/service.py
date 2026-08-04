# -*- coding: utf-8 -*-
"""Application service helpers. Stateless by design."""

from __future__ import annotations

import os
from typing import Dict

from zhilian_tianhe_agent.agents import AgentResult, ZhilianAgentHub
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig
from zhilian_tianhe_agent.reporting import build_docx_bytes, build_markdown_report

from .schemas import APIConfig, AgentResponse, ProfileData


def model_request_timeout_seconds() -> int:
    """Return a bounded upstream model timeout for generation requests."""

    raw = os.getenv("MODEL_REQUEST_TIMEOUT_SECONDS", "120").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 120
    return max(10, min(value, 600))


def make_hub(config: APIConfig) -> ZhilianAgentHub:
    """Create an AgentHub from user supplied config.

    The API key is only kept in memory for the current HTTP request.
    It is not written to logs, databases, files, exported reports, or environment variables.
    """

    llm_cfg = LLMConfig(
        api_key=config.api_key.strip(),
        base_url=config.base_url.strip(),
        model=config.model.strip(),
        temperature=config.temperature,
        timeout=model_request_timeout_seconds(),
    )
    return ZhilianAgentHub(LLMClient(llm_cfg))


def profile_to_dict(profile: ProfileData) -> Dict[str, str]:
    return profile.model_dump()


def agent_response(result: AgentResult) -> AgentResponse:
    return AgentResponse(
        ok=True,
        content=result.content,
        mode=result.mode,
        error=result.error,
    )


def build_markdown(results: Dict[str, str]) -> str:
    return build_markdown_report(results)


def build_docx(results: Dict[str, str]) -> bytes:
    return build_docx_bytes(results)

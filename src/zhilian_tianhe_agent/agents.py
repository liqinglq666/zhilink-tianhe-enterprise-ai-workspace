# -*- coding: utf-8 -*-
"""业务Agent编排层。

本版本面向真实用户使用：业务模块必须配置模型 API 后生成，不再提供本地示例兜底。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .llm_client import LLMClient
from .prompts import (
    SYSTEM_PROMPT,
    profile_prompt,
    meeting_prompt,
    contract_prompt,
    policy_prompt,
    match_prompt,
    landing_prompt,
    report_prompt,
)
from .utils import load_json


@dataclass
class AgentResult:
    content: str
    mode: str
    error: str = ""


class BaseAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def _run(self, prompt: str) -> AgentResult:
        if not self.llm.enabled:
            raise RuntimeError("请先配置 API Key、Base URL 和模型名称。")
        try:
            return AgentResult(content=self.llm.chat(SYSTEM_PROMPT, prompt), mode="AI模型模式")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"模型调用失败：{exc}") from exc


class ProfileAgent(BaseAgent):
    def run(self, profile: Dict[str, str]) -> AgentResult:
        knowledge = load_json("tianhe_knowledge.json")
        prompt = profile_prompt(profile, knowledge["tianhe_context"])
        return self._run(prompt)


class MeetingAgent(BaseAgent):
    def run(self, meeting_text: str, profile_summary: str = "") -> AgentResult:
        prompt = meeting_prompt(meeting_text, profile_summary)
        return self._run(prompt)


class ContractAgent(BaseAgent):
    def run(self, contract_text: str, profile_summary: str = "") -> AgentResult:
        prompt = contract_prompt(contract_text, profile_summary)
        return self._run(prompt)


class PolicyAgent(BaseAgent):
    def run(self, profile: Dict[str, str], demand: str = "") -> AgentResult:
        directions = load_json("policy_directions.json")
        prompt = policy_prompt(profile, directions, demand)
        return self._run(prompt)


class MatchAgent(BaseAgent):
    def run(self, profile: Dict[str, str], offer: str, need: str, target: str, scenario: str) -> AgentResult:
        prompt = match_prompt(profile, offer, need, target, scenario)
        return self._run(prompt)


class LandingAgent(BaseAgent):
    def run(self, profile: Dict[str, str], landing_info: Dict[str, str], existing_results: Dict[str, str]) -> AgentResult:
        prompt = landing_prompt(profile, landing_info, existing_results)
        return self._run(prompt)


class ReportAgent(BaseAgent):
    def run(self, all_results: Dict[str, str]) -> AgentResult:
        prompt = report_prompt(all_results)
        return self._run(prompt)


class ZhilianAgentHub:
    """统一Agent入口，方便前端调用。"""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.profile = ProfileAgent(self.llm)
        self.meeting = MeetingAgent(self.llm)
        self.contract = ContractAgent(self.llm)
        self.policy = PolicyAgent(self.llm)
        self.match = MatchAgent(self.llm)
        self.landing = LandingAgent(self.llm)
        self.report = ReportAgent(self.llm)

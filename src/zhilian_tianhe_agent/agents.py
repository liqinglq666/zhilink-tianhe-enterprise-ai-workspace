# -*- coding: utf-8 -*-
"""业务 Agent 编排层。

本版本面向真实用户使用：业务模块必须配置模型 API 后生成，不再提供本地示例兜底。
支持普通一次性生成和流式生成。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Optional

from .contract_rules import ContractRuleScan, scan_contract_rules
from .errors import ModelGatewayError
from .llm_client import LLMClient
from .prompts import (
    SYSTEM_PROMPT,
    contract_prompt,
    landing_prompt,
    match_prompt,
    meeting_prompt,
    policy_prompt,
    profile_prompt,
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
        try:
            return AgentResult(content=self.llm.chat(SYSTEM_PROMPT, prompt), mode="AI模型模式")
        except ModelGatewayError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ModelGatewayError(
                code="MODEL_INTERNAL_ERROR",
                user_message="模型处理过程发生异常，请稍后重试。",
                status_code=502,
                retryable=True,
            ) from exc

    def _stream(self, prompt: str) -> Iterator[str]:
        try:
            yield from self.llm.chat_stream(SYSTEM_PROMPT, prompt)
        except ModelGatewayError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ModelGatewayError(
                code="MODEL_INTERNAL_ERROR",
                user_message="模型流式处理发生异常，请稍后重试。",
                status_code=502,
                retryable=True,
            ) from exc


class ProfileAgent(BaseAgent):
    def run(self, profile: Dict[str, str]) -> AgentResult:
        knowledge = load_json("tianhe_knowledge.json")
        prompt = profile_prompt(profile, knowledge["tianhe_context"])
        return self._run(prompt)

    def stream(self, profile: Dict[str, str]) -> Iterator[str]:
        knowledge = load_json("tianhe_knowledge.json")
        prompt = profile_prompt(profile, knowledge["tianhe_context"])
        yield from self._stream(prompt)


class MeetingAgent(BaseAgent):
    def run(self, meeting_text: str, profile_summary: str = "") -> AgentResult:
        prompt = meeting_prompt(meeting_text, profile_summary)
        return self._run(prompt)

    def stream(self, meeting_text: str, profile_summary: str = "") -> Iterator[str]:
        prompt = meeting_prompt(meeting_text, profile_summary)
        yield from self._stream(prompt)


class ContractAgent(BaseAgent):
    def _prepare(
        self,
        contract_text: str,
        profile_summary: str,
    ) -> tuple[str, ContractRuleScan]:
        scan = scan_contract_rules(contract_text)
        prompt = contract_prompt(contract_text, profile_summary, scan.to_prompt_dict())
        return prompt, scan

    @staticmethod
    def _with_local_scan(content: str, scan: ContractRuleScan) -> str:
        return f"{content.rstrip()}\n\n{scan.to_markdown()}".strip()

    def run(self, contract_text: str, profile_summary: str = "") -> AgentResult:
        prompt, scan = self._prepare(contract_text, profile_summary)
        result = self._run(prompt)
        return AgentResult(
            content=self._with_local_scan(result.content, scan),
            mode="AI模型模式（含本地规则预检）",
            error=result.error,
        )

    def stream(self, contract_text: str, profile_summary: str = "") -> Iterator[str]:
        prompt, scan = self._prepare(contract_text, profile_summary)
        yield from self._stream(prompt)
        yield f"\n\n{scan.to_markdown()}"


class PolicyAgent(BaseAgent):
    def run(self, profile: Dict[str, str], demand: str = "") -> AgentResult:
        directions = load_json("policy_directions.json")
        prompt = policy_prompt(profile, directions, demand)
        return self._run(prompt)

    def stream(self, profile: Dict[str, str], demand: str = "") -> Iterator[str]:
        directions = load_json("policy_directions.json")
        prompt = policy_prompt(profile, directions, demand)
        yield from self._stream(prompt)


class MatchAgent(BaseAgent):
    def run(
        self,
        profile: Dict[str, str],
        offer: str,
        need: str,
        target: str,
        scenario: str,
    ) -> AgentResult:
        prompt = match_prompt(profile, offer, need, target, scenario)
        return self._run(prompt)

    def stream(
        self,
        profile: Dict[str, str],
        offer: str,
        need: str,
        target: str,
        scenario: str,
    ) -> Iterator[str]:
        prompt = match_prompt(profile, offer, need, target, scenario)
        yield from self._stream(prompt)


class LandingAgent(BaseAgent):
    def run(
        self,
        profile: Dict[str, str],
        landing_info: Dict[str, str],
        existing_results: Dict[str, str],
    ) -> AgentResult:
        prompt = landing_prompt(profile, landing_info, existing_results)
        return self._run(prompt)

    def stream(
        self,
        profile: Dict[str, str],
        landing_info: Dict[str, str],
        existing_results: Dict[str, str],
    ) -> Iterator[str]:
        prompt = landing_prompt(profile, landing_info, existing_results)
        yield from self._stream(prompt)


class ReportAgent(BaseAgent):
    def run(self, all_results: Dict[str, str]) -> AgentResult:
        prompt = report_prompt(all_results)
        return self._run(prompt)

    def stream(self, all_results: Dict[str, str]) -> Iterator[str]:
        prompt = report_prompt(all_results)
        yield from self._stream(prompt)


class ZhilianAgentHub:
    """统一 Agent 入口，方便前端调用。"""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.profile = ProfileAgent(self.llm)
        self.meeting = MeetingAgent(self.llm)
        self.contract = ContractAgent(self.llm)
        self.policy = PolicyAgent(self.llm)
        self.match = MatchAgent(self.llm)
        self.landing = LandingAgent(self.llm)
        self.report = ReportAgent(self.llm)

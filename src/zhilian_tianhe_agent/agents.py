# -*- coding: utf-8 -*-
"""业务 Agent 编排层。

本版本面向真实用户使用：业务模块必须配置模型 API 后生成，不再提供本地示例兜底。
支持普通一次性生成和流式生成。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Optional

from .contract_quality import (
    CONTRACT_RECOMMENDATION_SAFETY_RULES,
    audit_contract_output,
)
from .contract_rules import ContractRuleScan, scan_contract_rules
from .errors import ModelGatewayError
from .evidence import (
    EvidenceBundle,
    append_evidence_appendix,
    build_landing_evidence,
    build_match_evidence,
    build_policy_evidence,
    build_profile_evidence,
    build_report_evidence,
)
from .llm_client import LLMClient
from .meeting_quality import (
    MEETING_FACT_SAFETY_RULES,
    audit_meeting_output,
    build_meeting_evidence_v2,
)
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


@dataclass(frozen=True)
class AgentStreamEvent:
    """Trusted server-side stream event.

    ``delta`` may be shown as an explicitly provisional draft. ``verified`` is emitted
    only after deterministic post-generation checks and is the only event that may be
    persisted as a formal meeting/contract result.
    """

    type: str
    content: str = ""
    mode: str = ""


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

    def _run_grounded(
        self,
        prompt: str,
        bundle: EvidenceBundle,
    ) -> AgentResult:
        result = self._run(prompt)
        return AgentResult(
            content=append_evidence_appendix(result.content, bundle),
            mode="AI模型模式（含证据索引）",
            error=result.error,
        )

    def _stream_grounded(
        self,
        prompt: str,
        bundle: EvidenceBundle,
    ) -> Iterator[str]:
        yield from self._stream(prompt)
        yield f"\n\n{bundle.to_markdown()}"


class ProfileAgent(BaseAgent):
    def _prepare(self, profile: Dict[str, str]) -> tuple[str, EvidenceBundle]:
        knowledge = load_json("tianhe_knowledge.json")
        bundle = build_profile_evidence(profile)
        prompt = profile_prompt(
            profile,
            knowledge["tianhe_context"],
            bundle.to_prompt_dict(),
        )
        return prompt, bundle

    def run(self, profile: Dict[str, str]) -> AgentResult:
        prompt, bundle = self._prepare(profile)
        return self._run_grounded(prompt, bundle)

    def stream(self, profile: Dict[str, str]) -> Iterator[str]:
        prompt, bundle = self._prepare(profile)
        yield from self._stream_grounded(prompt, bundle)


class MeetingAgent(BaseAgent):
    def _prepare(
        self,
        meeting_text: str,
        profile_summary: str,
    ) -> tuple[str, EvidenceBundle]:
        bundle = build_meeting_evidence_v2(meeting_text, profile_summary)
        prompt = meeting_prompt(
            meeting_text,
            profile_summary,
            bundle.to_prompt_dict(),
        )
        prompt = f"{prompt}\n\n{MEETING_FACT_SAFETY_RULES}"
        return prompt, bundle

    def run(self, meeting_text: str, profile_summary: str = "") -> AgentResult:
        prompt, bundle = self._prepare(meeting_text, profile_summary)
        result = self._run(prompt)
        checked = audit_meeting_output(result.content, meeting_text, bundle)
        return AgentResult(
            content=append_evidence_appendix(checked, bundle),
            mode="AI模型模式（含证据索引）",
            error=result.error,
        )

    def stream_events(self, meeting_text: str, profile_summary: str = "") -> Iterator[AgentStreamEvent]:
        """Stream a provisional draft immediately, then replace it with verified content."""
        prompt, bundle = self._prepare(meeting_text, profile_summary)
        chunks: list[str] = []
        for chunk in self._stream(prompt):
            chunks.append(chunk)
            yield AgentStreamEvent(type="delta", content=chunk)

        yield AgentStreamEvent(type="verifying")
        checked = audit_meeting_output("".join(chunks), meeting_text, bundle)
        verified = append_evidence_appendix(checked, bundle)
        yield AgentStreamEvent(
            type="verified",
            content=verified,
            mode="AI模型模式（已事实校验）",
        )


class ContractAgent(BaseAgent):
    def _prepare(
        self,
        contract_text: str,
        profile_summary: str,
    ) -> tuple[str, ContractRuleScan]:
        scan = scan_contract_rules(contract_text)
        prompt = contract_prompt(contract_text, profile_summary, scan.to_prompt_dict())
        prompt = f"{prompt}\n\n{CONTRACT_RECOMMENDATION_SAFETY_RULES}"
        return prompt, scan

    @staticmethod
    def _with_local_scan(content: str, scan: ContractRuleScan) -> str:
        return f"{content.rstrip()}\n\n{scan.to_markdown()}".strip()

    def run(self, contract_text: str, profile_summary: str = "") -> AgentResult:
        prompt, scan = self._prepare(contract_text, profile_summary)
        result = self._run(prompt)
        checked = audit_contract_output(result.content, contract_text, scan)
        return AgentResult(
            content=self._with_local_scan(checked, scan),
            mode="AI模型模式（含本地规则预检）",
            error=result.error,
        )

    def stream_events(self, contract_text: str, profile_summary: str = "") -> Iterator[AgentStreamEvent]:
        """Stream a provisional draft immediately, then replace it with verified content."""
        prompt, scan = self._prepare(contract_text, profile_summary)
        chunks: list[str] = []
        for chunk in self._stream(prompt):
            chunks.append(chunk)
            yield AgentStreamEvent(type="delta", content=chunk)

        yield AgentStreamEvent(type="verifying")
        checked = audit_contract_output("".join(chunks), contract_text, scan)
        verified = self._with_local_scan(checked, scan)
        yield AgentStreamEvent(
            type="verified",
            content=verified,
            mode="AI模型模式（已校验，含本地规则预检）",
        )


class PolicyAgent(BaseAgent):
    def _prepare(
        self,
        profile: Dict[str, str],
        demand: str,
    ) -> tuple[str, EvidenceBundle]:
        directions = load_json("policy_directions.json")
        bundle = build_policy_evidence(profile, demand, directions)
        prompt = policy_prompt(
            profile,
            directions,
            demand,
            bundle.to_prompt_dict(),
        )
        return prompt, bundle

    def run(self, profile: Dict[str, str], demand: str = "") -> AgentResult:
        prompt, bundle = self._prepare(profile, demand)
        return self._run_grounded(prompt, bundle)

    def stream(self, profile: Dict[str, str], demand: str = "") -> Iterator[str]:
        prompt, bundle = self._prepare(profile, demand)
        yield from self._stream_grounded(prompt, bundle)


class MatchAgent(BaseAgent):
    def _prepare(
        self,
        profile: Dict[str, str],
        offer: str,
        need: str,
        target: str,
        scenario: str,
    ) -> tuple[str, EvidenceBundle]:
        bundle = build_match_evidence(profile, offer, need, target, scenario)
        prompt = match_prompt(
            profile,
            offer,
            need,
            target,
            scenario,
            bundle.to_prompt_dict(),
        )
        return prompt, bundle

    def run(
        self,
        profile: Dict[str, str],
        offer: str,
        need: str,
        target: str,
        scenario: str,
    ) -> AgentResult:
        prompt, bundle = self._prepare(profile, offer, need, target, scenario)
        return self._run_grounded(prompt, bundle)

    def stream(
        self,
        profile: Dict[str, str],
        offer: str,
        need: str,
        target: str,
        scenario: str,
    ) -> Iterator[str]:
        prompt, bundle = self._prepare(profile, offer, need, target, scenario)
        yield from self._stream_grounded(prompt, bundle)


class LandingAgent(BaseAgent):
    def _prepare(
        self,
        profile: Dict[str, str],
        landing_info: Dict[str, str],
        existing_results: Dict[str, str],
    ) -> tuple[str, EvidenceBundle]:
        bundle = build_landing_evidence(profile, landing_info, existing_results)
        prompt = landing_prompt(
            profile,
            landing_info,
            existing_results,
            bundle.to_prompt_dict(),
        )
        return prompt, bundle

    def run(
        self,
        profile: Dict[str, str],
        landing_info: Dict[str, str],
        existing_results: Dict[str, str],
    ) -> AgentResult:
        prompt, bundle = self._prepare(profile, landing_info, existing_results)
        return self._run_grounded(prompt, bundle)

    def stream(
        self,
        profile: Dict[str, str],
        landing_info: Dict[str, str],
        existing_results: Dict[str, str],
    ) -> Iterator[str]:
        prompt, bundle = self._prepare(profile, landing_info, existing_results)
        yield from self._stream_grounded(prompt, bundle)


class ReportAgent(BaseAgent):
    def _prepare(
        self,
        all_results: Dict[str, str],
    ) -> tuple[str, EvidenceBundle]:
        bundle = build_report_evidence(all_results)
        prompt = report_prompt(all_results, bundle.to_prompt_dict())
        return prompt, bundle

    def run(self, all_results: Dict[str, str]) -> AgentResult:
        prompt, bundle = self._prepare(all_results)
        return self._run_grounded(prompt, bundle)

    def stream(self, all_results: Dict[str, str]) -> Iterator[str]:
        prompt, bundle = self._prepare(all_results)
        yield from self._stream_grounded(prompt, bundle)


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

# -*- coding: utf-8 -*-
"""API request/response schemas and server-side input limits."""

from __future__ import annotations

import os
from typing import Dict

from pydantic import BaseModel, Field, field_validator, model_validator


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


MAX_API_KEY_CHARS = _env_int("MAX_API_KEY_CHARS", 2048)
MAX_BASE_URL_CHARS = _env_int("MAX_BASE_URL_CHARS", 2048)
MAX_MODEL_NAME_CHARS = _env_int("MAX_MODEL_NAME_CHARS", 200)
MAX_PROFILE_FIELD_CHARS = _env_int("MAX_PROFILE_FIELD_CHARS", 500)
MAX_PROFILE_DEMANDS_CHARS = _env_int("MAX_PROFILE_DEMANDS_CHARS", 8000)
MAX_PROFILE_SUMMARY_CHARS = _env_int("MAX_PROFILE_SUMMARY_CHARS", 12000)
MAX_MEETING_CHARS = _env_int("MAX_MEETING_CHARS", 30000)
MAX_CONTRACT_CHARS = _env_int("MAX_CONTRACT_CHARS", 50000)
MAX_POLICY_DEMAND_CHARS = _env_int("MAX_POLICY_DEMAND_CHARS", 20000)
MAX_MATCH_FIELD_CHARS = _env_int("MAX_MATCH_FIELD_CHARS", 12000)
MAX_MATCH_TOTAL_CHARS = _env_int("MAX_MATCH_TOTAL_CHARS", 30000)
MAX_LANDING_VALUE_CHARS = _env_int("MAX_LANDING_VALUE_CHARS", 12000)
MAX_LANDING_TOTAL_CHARS = _env_int("MAX_LANDING_TOTAL_CHARS", 50000)
MAX_RESULT_VALUE_CHARS = _env_int("MAX_RESULT_VALUE_CHARS", 80000)
MAX_REPORT_TOTAL_CHARS = _env_int("MAX_REPORT_TOTAL_CHARS", 200000)
MAX_MAPPING_ITEMS = _env_int("MAX_MAPPING_ITEMS", 20)
MAX_MAPPING_KEY_CHARS = _env_int("MAX_MAPPING_KEY_CHARS", 100)


def _validate_mapping(
    value: Dict[str, str],
    *,
    field_label: str,
    max_value_chars: int,
    max_total_chars: int,
) -> Dict[str, str]:
    if len(value) > MAX_MAPPING_ITEMS:
        raise ValueError(f"{field_label}最多允许 {MAX_MAPPING_ITEMS} 项。")

    total = 0
    for key, item in value.items():
        if len(key) > MAX_MAPPING_KEY_CHARS:
            raise ValueError(f"{field_label}字段名称过长。")
        if len(item) > max_value_chars:
            raise ValueError(f"{field_label}单项内容过长，最多允许 {max_value_chars} 个字符。")
        total += len(key) + len(item)

    if total > max_total_chars:
        raise ValueError(f"{field_label}总内容过长，最多允许 {max_total_chars} 个字符。")
    return value


class APIConfig(BaseModel):
    """OpenAI-compatible model configuration supplied by the end user."""

    api_key: str = Field(
        default="",
        max_length=MAX_API_KEY_CHARS,
        description="User supplied API key; never persisted by backend.",
    )
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        max_length=MAX_BASE_URL_CHARS,
    )
    model: str = Field(default="qwen-plus", max_length=MAX_MODEL_NAME_CHARS)
    temperature: float = Field(default=0.35, ge=0, le=1)


class ProfileData(BaseModel):
    name: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    industry: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    location: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    scale: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    stage: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    contact_role: str = Field(default="", max_length=MAX_PROFILE_FIELD_CHARS)
    demands: str = Field(default="", max_length=MAX_PROFILE_DEMANDS_CHARS)


class BaseAgentRequest(BaseModel):
    config: APIConfig = Field(default_factory=APIConfig)


class ProfileRequest(BaseAgentRequest):
    profile: ProfileData


class MeetingRequest(BaseAgentRequest):
    profile_summary: str = Field(default="", max_length=MAX_PROFILE_SUMMARY_CHARS)
    text: str = Field(max_length=MAX_MEETING_CHARS)


class ContractRequest(BaseAgentRequest):
    profile_summary: str = Field(default="", max_length=MAX_PROFILE_SUMMARY_CHARS)
    text: str = Field(max_length=MAX_CONTRACT_CHARS)


class PolicyRequest(BaseAgentRequest):
    profile: ProfileData
    demand: str = Field(default="", max_length=MAX_POLICY_DEMAND_CHARS)


class MatchRequest(BaseAgentRequest):
    profile: ProfileData
    offer: str = Field(default="", max_length=MAX_MATCH_FIELD_CHARS)
    need: str = Field(default="", max_length=MAX_MATCH_FIELD_CHARS)
    target: str = Field(default="", max_length=MAX_MATCH_FIELD_CHARS)
    scenario: str = Field(default="", max_length=MAX_MATCH_FIELD_CHARS)

    @model_validator(mode="after")
    def validate_total_match_text(self) -> "MatchRequest":
        total = sum(len(item) for item in (self.offer, self.need, self.target, self.scenario))
        if total > MAX_MATCH_TOTAL_CHARS:
            raise ValueError(f"供需协作总内容过长，最多允许 {MAX_MATCH_TOTAL_CHARS} 个字符。")
        return self


class LandingRequest(BaseAgentRequest):
    profile: ProfileData
    landing_info: Dict[str, str] = Field(default_factory=dict)
    existing_results: Dict[str, str] = Field(default_factory=dict)

    @field_validator("landing_info")
    @classmethod
    def validate_landing_info(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_mapping(
            value,
            field_label="实施计划配置",
            max_value_chars=MAX_LANDING_VALUE_CHARS,
            max_total_chars=MAX_LANDING_TOTAL_CHARS,
        )

    @field_validator("existing_results")
    @classmethod
    def validate_existing_results(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_mapping(
            value,
            field_label="已有模块结果",
            max_value_chars=MAX_RESULT_VALUE_CHARS,
            max_total_chars=MAX_REPORT_TOTAL_CHARS,
        )


class ReportRequest(BaseAgentRequest):
    results: Dict[str, str]
    use_ai_summary: bool = True

    @field_validator("results")
    @classmethod
    def validate_results(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_mapping(
            value,
            field_label="报告内容",
            max_value_chars=MAX_RESULT_VALUE_CHARS,
            max_total_chars=MAX_REPORT_TOTAL_CHARS,
        )


class AgentResponse(BaseModel):
    ok: bool = True
    content: str = ""
    mode: str = "AI模型模式"
    error: str = ""
    error_code: str = ""
    retryable: bool = False
    retry_after: int | None = None


class HealthResponse(BaseModel):
    ok: bool = True
    app: str
    version: str


class PublicModelStatus(BaseModel):
    available: bool = False
    provider: str = ""
    model: str = ""
    user_override_allowed: bool = True


class DefaultsResponse(BaseModel):
    provider_presets: Dict[str, Dict[str, str]]
    modules: Dict[str, str]
    disclaimer: str
    public_model: PublicModelStatus = Field(default_factory=PublicModelStatus)

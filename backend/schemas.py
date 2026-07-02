# -*- coding: utf-8 -*-
"""API request/response schemas."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """OpenAI-compatible model configuration supplied by the end user."""

    api_key: str = Field(default="", description="User supplied API key; never persisted by backend.")
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    model: str = Field(default="qwen-plus")
    temperature: float = Field(default=0.35, ge=0, le=1)


class ProfileData(BaseModel):
    name: str = ""
    industry: str = ""
    location: str = ""
    scale: str = ""
    stage: str = ""
    contact_role: str = ""
    demands: str = ""


class BaseAgentRequest(BaseModel):
    config: APIConfig = Field(default_factory=APIConfig)


class ProfileRequest(BaseAgentRequest):
    profile: ProfileData


class TextRequest(BaseAgentRequest):
    profile_summary: str = ""
    text: str


class PolicyRequest(BaseAgentRequest):
    profile: ProfileData
    demand: str = ""


class MatchRequest(BaseAgentRequest):
    profile: ProfileData
    offer: str = ""
    need: str = ""
    target: str = ""
    scenario: str = ""


class LandingRequest(BaseAgentRequest):
    profile: ProfileData
    landing_info: Dict[str, str] = Field(default_factory=dict)
    existing_results: Dict[str, str] = Field(default_factory=dict)


class ReportRequest(BaseAgentRequest):
    results: Dict[str, str]
    use_ai_summary: bool = True


class AgentResponse(BaseModel):
    ok: bool = True
    content: str = ""
    mode: str = "AI模型模式"
    error: str = ""


class HealthResponse(BaseModel):
    ok: bool = True
    app: str
    version: str


class DefaultsResponse(BaseModel):
    provider_presets: Dict[str, Dict[str, str]]
    modules: Dict[str, str]
    disclaimer: str

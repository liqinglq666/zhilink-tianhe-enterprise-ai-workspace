# -*- coding: utf-8 -*-
"""Strict schemas for the organization-scoped Tianhe enterprise-service knowledge base."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

KnowledgeReviewStatus = Literal["draft", "in_review", "approved", "rejected"]
KnowledgeLifecycleStatus = Literal["active", "archived"]
KnowledgeAction = Literal["submit", "approve", "reject", "archive", "unarchive", "restore"]
KnowledgeSourceType = Literal["official", "internal", "service_guide", "case", "template", "faq", "other"]

OFFICIAL_DOMAIN_SUFFIXES = ("gov.cn", "gd.gov.cn", "gz.gov.cn", "thnet.gov.cn")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_list(values: list[str], *, max_items: int, max_chars: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values[:max_items]:
        value = " ".join(str(raw or "").split())[:max_chars]
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            result.append(value)
    return result


class KnowledgeApplicability(StrictModel):
    regions: list[str] = Field(default_factory=list, max_length=20)
    industries: list[str] = Field(default_factory=list, max_length=20)
    entity_types: list[str] = Field(default_factory=list, max_length=20)
    scenarios: list[str] = Field(default_factory=list, max_length=20)
    roles: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("regions", "industries", "entity_types", "scenarios", "roles")
    @classmethod
    def normalize_values(cls, value: list[str]) -> list[str]:
        return _clean_list(value, max_items=20, max_chars=100)


class KnowledgeSourceInput(StrictModel):
    source_type: KnowledgeSourceType
    title: str = Field(min_length=1, max_length=500)
    issuer: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=2000)
    published_at: date | None = None
    reference_number: str = Field(default="", max_length=200)
    excerpt: str = Field(default="", max_length=2000)

    @field_validator("title", "issuer", "reference_number", "excerpt")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        parsed = urlparse(cleaned)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError("知识来源链接必须是无凭据、无非标准端口的 HTTPS 地址。")
        return cleaned

    @model_validator(mode="after")
    def validate_official_source(self) -> "KnowledgeSourceInput":
        if self.source_type == "official":
            if not self.url:
                raise ValueError("官方来源必须填写官方 HTTPS 原文链接。")
            host = (urlparse(self.url).hostname or "").lower()
            if not any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_DOMAIN_SUFFIXES):
                raise ValueError("官方来源必须使用受信任的政府网站域名。")
            if not self.issuer:
                raise ValueError("官方来源必须填写发布机关。")
            if not self.excerpt:
                raise ValueError("官方来源必须保存一段可核对的原文摘录。")
        return self


class KnowledgeVersionInput(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=2000)
    content: str = Field(min_length=1, max_length=50000)
    tags: list[str] = Field(default_factory=list, max_length=30)
    applicability: KnowledgeApplicability = Field(default_factory=KnowledgeApplicability)
    source: KnowledgeSourceInput
    valid_from: date | None = None
    valid_until: date | None = None
    change_note: str = Field(default="", max_length=500)

    @field_validator("title", "category", "summary", "content", "change_note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return _clean_list(value, max_items=30, max_chars=80)

    @model_validator(mode="after")
    def validate_dates(self) -> "KnowledgeVersionInput":
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("失效日期不能早于生效日期。")
        return self


class KnowledgeCreateRequest(KnowledgeVersionInput):
    pass


class KnowledgeUpdateRequest(KnowledgeVersionInput):
    expected_version: int = Field(ge=1)


class KnowledgeActionRequest(StrictModel):
    action: KnowledgeAction
    expected_version: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)
    version_number: int | None = Field(default=None, ge=1)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_action(self) -> "KnowledgeActionRequest":
        if self.action in {"reject", "archive"} and not self.note:
            raise ValueError("退回或归档时必须填写原因。")
        if self.action == "restore" and self.version_number is None:
            raise ValueError("恢复历史版本时必须指定版本号。")
        return self


class KnowledgeSourceResponse(KnowledgeSourceInput):
    source_sha256: str = Field(min_length=64, max_length=64)


class KnowledgeVersionResponse(StrictModel):
    article_id: str
    citation_code: str = Field(pattern=r"^THKB-[A-F0-9]{8}$")
    citation_id: str = Field(pattern=r"^THKB-[A-F0-9]{8}@v\d+$")
    version_number: int = Field(ge=1)
    title: str
    category: str
    summary: str
    content: str
    tags: list[str]
    applicability: KnowledgeApplicability
    source: KnowledgeSourceResponse
    valid_from: date | None = None
    valid_until: date | None = None
    content_sha256: str = Field(min_length=64, max_length=64)
    change_note: str
    created_by_user_id: str
    created_at: datetime


class KnowledgeArticleSummary(StrictModel):
    id: str
    organization_id: str
    citation_code: str
    title: str
    category: str
    review_status: KnowledgeReviewStatus
    lifecycle_status: KnowledgeLifecycleStatus
    current_version: int
    published_version: int | None = None
    updated_at: datetime
    can_edit: bool
    can_review: bool


class KnowledgeArticleResponse(KnowledgeArticleSummary):
    version: KnowledgeVersionResponse
    published: KnowledgeVersionResponse | None = None


class KnowledgeListResponse(StrictModel):
    items: list[KnowledgeArticleSummary]
    total: int


class KnowledgeVersionListResponse(StrictModel):
    items: list[KnowledgeVersionResponse]
    total: int


class KnowledgeReviewEventResponse(StrictModel):
    id: str
    article_id: str
    version_number: int
    action: KnowledgeAction
    before_status: str
    after_status: str
    actor_user_id: str
    actor_name: str
    actor_role: str
    note: str
    created_at: datetime


class KnowledgeReviewEventListResponse(StrictModel):
    items: list[KnowledgeReviewEventResponse]
    total: int


class KnowledgeSearchProfile(StrictModel):
    industry: str = Field(default="", max_length=500)
    location: str = Field(default="", max_length=500)
    scale: str = Field(default="", max_length=500)
    stage: str = Field(default="", max_length=500)
    demands: str = Field(default="", max_length=4000)


class KnowledgeSearchRequest(StrictModel):
    query: str = Field(default="", max_length=4000)
    profile: KnowledgeSearchProfile = Field(default_factory=KnowledgeSearchProfile)
    category: str = Field(default="", max_length=100)
    limit: int = Field(default=8, ge=1, le=20)


class KnowledgeSearchItem(StrictModel):
    article_id: str
    citation_id: str
    title: str
    category: str
    summary: str
    excerpt: str
    tags: list[str]
    applicability: KnowledgeApplicability
    source: KnowledgeSourceResponse
    valid_from: date | None = None
    valid_until: date | None = None
    score: float = Field(ge=0)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class KnowledgeSearchResponse(StrictModel):
    status: Literal["ok", "no_results"]
    query: str
    generated_at: datetime
    items: list[KnowledgeSearchItem]
    markdown_context: str = Field(max_length=50000)

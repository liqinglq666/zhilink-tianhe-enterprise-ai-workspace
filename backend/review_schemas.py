# -*- coding: utf-8 -*-
"""API contracts for human editing, confirmation, and review workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ReviewModule = Literal[
    "profile",
    "meeting",
    "contract",
    "policy",
    "match",
    "landing",
    "report",
]
ReviewStatus = Literal[
    "ai_draft",
    "edited",
    "pending_review",
    "changes_requested",
    "approved",
    "confirmed",
]
ReviewAction = Literal[
    "save_edit",
    "submit_review",
    "approve",
    "request_changes",
    "confirm",
    "revert_ai",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectReviewState(StrictModel):
    status: ReviewStatus = "ai_draft"
    source_content: str = Field(default="", max_length=80000)
    source_hash: str = Field(default="", max_length=64)
    content_hash: str = Field(default="", max_length=64)
    note: str = Field(default="", max_length=2000)
    revision: int = Field(default=1, ge=1, le=1000000)
    submitted_by_name: str = Field(default="", max_length=120)
    submitted_at: str = Field(default="", max_length=100)
    reviewed_by_name: str = Field(default="", max_length=120)
    reviewed_at: str = Field(default="", max_length=100)
    updated_by_name: str = Field(default="", max_length=120)
    updated_at: str = Field(default="", max_length=100)


class ProjectReviewSummary(StrictModel):
    module: ReviewModule
    status: ReviewStatus
    content_hash: str = Field(default="", max_length=64)
    note: str = Field(default="", max_length=2000)
    revision: int = Field(ge=1)
    submitted_by_name: str = Field(default="", max_length=120)
    submitted_at: str = Field(default="", max_length=100)
    reviewed_by_name: str = Field(default="", max_length=120)
    reviewed_at: str = Field(default="", max_length=100)
    updated_by_name: str = Field(default="", max_length=120)
    updated_at: str = Field(default="", max_length=100)


class ProjectReviewListResponse(StrictModel):
    items: list[ProjectReviewSummary]
    total: int
    project_lock_version: int = Field(ge=1)


class ProjectReviewDetailResponse(StrictModel):
    module: ReviewModule
    review: ProjectReviewState
    working_content: str = Field(max_length=80000)
    project_lock_version: int = Field(ge=1)


class ProjectReviewActionRequest(StrictModel):
    lock_version: int = Field(ge=1)
    action: ReviewAction
    content: str | None = Field(default=None, max_length=80000)
    note: str = Field(default="", max_length=2000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ProjectReviewActionRequest":
        if self.action == "save_edit":
            if self.content is None or not self.content.strip():
                raise ValueError("人工编辑内容不能为空。")
        if self.action == "request_changes" and not self.note:
            raise ValueError("退回修改时必须填写审核意见。")
        return self


class ProjectReviewEventResponse(StrictModel):
    id: str
    project_id: str
    module: ReviewModule
    action: ReviewAction
    from_status: ReviewStatus
    to_status: ReviewStatus
    actor_name: str
    actor_role: str
    note: str
    content_hash: str
    created_at: datetime


class ProjectReviewEventListResponse(StrictModel):
    items: list[ProjectReviewEventResponse]
    total: int


class ProjectReviewActionResponse(StrictModel):
    project: dict
    review: ProjectReviewState
    event: ProjectReviewEventResponse

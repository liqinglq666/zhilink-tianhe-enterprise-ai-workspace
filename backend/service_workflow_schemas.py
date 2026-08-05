# -*- coding: utf-8 -*-
"""Strict schemas for organization-scoped enterprise-service workflows."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WorkflowPriority = Literal["low", "normal", "high", "urgent"]
WorkflowStatus = Literal["draft", "active", "on_hold", "pending_review", "completed", "cancelled"]
WorkflowNodeStatus = Literal["pending", "in_progress", "blocked", "pending_review", "completed", "skipped"]
WorkflowNodeType = Literal["intake", "diagnosis", "evidence", "plan", "delivery", "closeout"]
WorkflowCaseAction = Literal["activate", "hold", "resume", "submit_review", "complete", "cancel", "reopen"]
WorkflowNodeAction = Literal["start", "block", "resume", "submit", "approve", "return", "skip", "reopen"]


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


class WorkflowCreateRequest(StrictModel):
    project_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=4000)
    priority: WorkflowPriority = "normal"
    owner_user_id: str | None = Field(default=None, max_length=36)
    due_date: date | None = None
    knowledge_citations: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("project_id", "title", "objective", "owner_user_id")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("knowledge_citations")
    @classmethod
    def normalize_citations(cls, value: list[str]) -> list[str]:
        return _clean_list(value, max_items=20, max_chars=40)


class WorkflowUpdateRequest(StrictModel):
    lock_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    objective: str | None = Field(default=None, min_length=1, max_length=4000)
    priority: WorkflowPriority | None = None
    owner_user_id: str | None = Field(default=None, max_length=36)
    due_date: date | None = None
    clear_due_date: bool = False

    @field_validator("title", "objective", "owner_user_id")
    @classmethod
    def normalize_optional_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self) -> "WorkflowUpdateRequest":
        if (
            self.title is None
            and self.objective is None
            and self.priority is None
            and self.owner_user_id is None
            and self.due_date is None
            and not self.clear_due_date
        ):
            raise ValueError("请至少提交一个需要修改的流程字段。")
        return self


class WorkflowContextRefreshRequest(StrictModel):
    lock_version: int = Field(ge=1)
    knowledge_citations: list[str] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=1000)

    @field_validator("knowledge_citations")
    @classmethod
    def normalize_citations(cls, value: list[str]) -> list[str]:
        return _clean_list(value, max_items=20, max_chars=40)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return value.strip()


class WorkflowCaseActionRequest(StrictModel):
    action: WorkflowCaseAction
    lock_version: int = Field(ge=1)
    note: str = Field(default="", max_length=3000)
    acknowledge_open_items: bool = False

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_action(self) -> "WorkflowCaseActionRequest":
        if self.action in {"hold", "cancel", "complete"} and not self.note:
            raise ValueError("暂停、取消或结项时必须填写说明。")
        return self


class WorkflowNodeUpdateRequest(StrictModel):
    lock_version: int = Field(ge=1)
    assignee_user_id: str | None = Field(default=None, max_length=36)
    due_date: date | None = None
    clear_due_date: bool = False
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("assignee_user_id", "description")
    @classmethod
    def normalize_optional_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self) -> "WorkflowNodeUpdateRequest":
        if self.assignee_user_id is None and self.due_date is None and not self.clear_due_date and self.description is None:
            raise ValueError("请至少提交一个需要修改的节点字段。")
        return self


class WorkflowNodeActionRequest(StrictModel):
    action: WorkflowNodeAction
    lock_version: int = Field(ge=1)
    note: str = Field(default="", max_length=3000)
    output_summary: str = Field(default="", max_length=10000)

    @field_validator("note", "output_summary")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_action(self) -> "WorkflowNodeActionRequest":
        if self.action in {"block", "return", "skip"} and not self.note:
            raise ValueError("阻塞、退回或跳过节点时必须填写原因。")
        if self.action == "submit" and not self.output_summary:
            raise ValueError("提交审核前必须填写节点处理结果。")
        return self


class WorkflowModuleReference(StrictModel):
    module: str
    result_sha256: str = Field(min_length=64, max_length=64)
    excerpt: str
    review_status: str
    reviewed_by: str
    reviewed_at: str


class WorkflowPolicyReference(StrictModel):
    citation_id: str = Field(pattern=r"^POL-\d{3}$")
    title: str
    official_url: str


class WorkflowKnowledgeReference(StrictModel):
    citation_id: str = Field(pattern=r"^THKB-[A-F0-9]{8}@v\d+$")
    title: str
    category: str
    source_type: str
    issuer: str
    valid_until: date | None = None
    content_sha256: str = Field(min_length=64, max_length=64)


class WorkflowPendingItem(StrictModel):
    module: str
    text: str


class WorkflowContextResponse(StrictModel):
    context_version: int = Field(ge=1)
    project_id: str
    project_name: str
    project_version: int = Field(ge=1)
    project_updated_at: datetime
    profile: dict
    identity: dict
    modules: list[WorkflowModuleReference]
    official_policy_references: list[WorkflowPolicyReference]
    knowledge_references: list[WorkflowKnowledgeReference]
    pending_items: list[WorkflowPendingItem]
    context_sha256: str = Field(min_length=64, max_length=64)
    created_by_user_id: str
    created_at: datetime


class WorkflowNodeResponse(StrictModel):
    id: str
    case_id: str
    sequence: int
    node_type: WorkflowNodeType
    title: str
    description: str
    status: WorkflowNodeStatus
    assignee_user_id: str | None = None
    assignee_name: str
    due_date: date | None = None
    output_summary: str
    decision_note: str
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class WorkflowCaseSummary(StrictModel):
    id: str
    organization_id: str
    project_id: str
    case_number: str = Field(pattern=r"^THSC-[A-F0-9]{8}$")
    title: str
    objective: str
    priority: WorkflowPriority
    status: WorkflowStatus
    owner_user_id: str
    owner_name: str
    due_date: date | None = None
    lock_version: int
    current_context_version: int
    completed_nodes: int
    total_nodes: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class WorkflowCaseResponse(WorkflowCaseSummary):
    closure_summary: str
    nodes: list[WorkflowNodeResponse]
    context: WorkflowContextResponse


class WorkflowCaseListResponse(StrictModel):
    items: list[WorkflowCaseSummary]
    total: int


class WorkflowEventResponse(StrictModel):
    id: str
    case_id: str
    node_id: str | None = None
    action: str
    before_status: str
    after_status: str
    actor_user_id: str
    actor_name: str
    actor_role: str
    note: str
    payload_sha256: str = Field(min_length=64, max_length=64)
    created_at: datetime


class WorkflowEventListResponse(StrictModel):
    items: list[WorkflowEventResponse]
    total: int

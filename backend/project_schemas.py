# -*- coding: utf-8 -*-
"""Validated API schemas for persistent projects and immutable history."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProjectStatus = Literal["active", "archived"]
ProjectModule = Literal[
    "project", "identity", "profile", "meeting", "contract", "policy", "match", "landing", "report"
]
ProjectChangeKind = Literal[
    "create", "baseline", "save", "metadata", "archive", "unarchive", "restore"
]


def _validate_string_mapping(
    value: Dict[str, str],
    *,
    label: str,
    max_items: int,
    max_key_chars: int,
    max_value_chars: int,
    max_total_chars: int,
) -> Dict[str, str]:
    if len(value) > max_items:
        raise ValueError(f"{label}最多允许 {max_items} 项。")
    total = 0
    for key, item in value.items():
        if len(key) > max_key_chars:
            raise ValueError(f"{label}字段名称过长。")
        if len(item) > max_value_chars:
            raise ValueError(f"{label}单项内容过长，最多允许 {max_value_chars} 个字符。")
        total += len(key) + len(item)
    if total > max_total_chars:
        raise ValueError(f"{label}总内容过长，最多允许 {max_total_chars} 个字符。")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredProfile(StrictModel):
    name: str = Field(default="", max_length=500)
    industry: str = Field(default="", max_length=500)
    location: str = Field(default="", max_length=500)
    scale: str = Field(default="", max_length=500)
    stage: str = Field(default="", max_length=500)
    contact_role: str = Field(default="", max_length=500)
    demands: str = Field(default="", max_length=8000)


class ProjectResultMeta(StrictModel):
    mode: str = Field(default="", max_length=200)
    error: str = Field(default="", max_length=1000)
    time: str = Field(default="", max_length=100)


class ProjectSnapshot(StrictModel):
    """Persistable workspace state. Model credentials are intentionally absent."""

    identity: Dict[str, str] = Field(default_factory=dict)
    profile: StoredProfile = Field(default_factory=StoredProfile)
    forms: Dict[str, str] = Field(default_factory=dict)
    results: Dict[str, str] = Field(default_factory=dict)
    meta: Dict[str, ProjectResultMeta] = Field(default_factory=dict)
    current_section: Literal[
        "home", "profile", "meeting", "contract", "policy", "match", "landing", "report"
    ] = "home"

    @field_validator("identity")
    @classmethod
    def validate_identity(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_string_mapping(
            value,
            label="使用身份",
            max_items=10,
            max_key_chars=50,
            max_value_chars=500,
            max_total_chars=3000,
        )

    @field_validator("forms")
    @classmethod
    def validate_forms(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_string_mapping(
            value,
            label="项目表单",
            max_items=40,
            max_key_chars=100,
            max_value_chars=50000,
            max_total_chars=180000,
        )

    @field_validator("results")
    @classmethod
    def validate_results(cls, value: Dict[str, str]) -> Dict[str, str]:
        return _validate_string_mapping(
            value,
            label="项目结果",
            max_items=12,
            max_key_chars=100,
            max_value_chars=80000,
            max_total_chars=300000,
        )

    @field_validator("meta")
    @classmethod
    def validate_meta(
        cls, value: Dict[str, ProjectResultMeta]
    ) -> Dict[str, ProjectResultMeta]:
        if len(value) > 12:
            raise ValueError("结果元数据最多允许 12 项。")
        if any(len(key) > 100 for key in value):
            raise ValueError("结果元数据字段名称过长。")
        return value


class ProjectCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    snapshot: ProjectSnapshot = Field(default_factory=ProjectSnapshot)
    version_label: str = Field(default="", max_length=200)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("项目名称不能为空。")
        return cleaned

    @field_validator("description", "version_label")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProjectUpdateRequest(StrictModel):
    lock_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None
    snapshot: ProjectSnapshot | None = None
    version_label: str = Field(default="", max_length=200)

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("项目名称不能为空。")
        return cleaned

    @field_validator("description")
    @classmethod
    def strip_optional_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("version_label")
    @classmethod
    def strip_version_label(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdateRequest":
        if (
            all(value is None for value in (self.name, self.description, self.status, self.snapshot))
            and not self.version_label
        ):
            raise ValueError("请至少提交一个需要更新的项目字段或版本说明。")
        return self


class ProjectRestoreRequest(StrictModel):
    lock_version: int = Field(ge=1)
    version_label: str = Field(default="", max_length=200)

    @field_validator("version_label")
    @classmethod
    def strip_version_label(cls, value: str) -> str:
        return value.strip()


class ProjectSummary(StrictModel):
    id: str
    name: str
    description: str
    status: ProjectStatus
    lock_version: int
    created_at: datetime
    updated_at: datetime


class ProjectResponse(ProjectSummary):
    snapshot: ProjectSnapshot


class ProjectListResponse(StrictModel):
    items: list[ProjectSummary]
    total: int


class ProjectDeleteResponse(StrictModel):
    ok: bool = True
    id: str


class ProjectVersionSummary(StrictModel):
    id: str
    project_id: str
    version_number: int
    change_kind: ProjectChangeKind
    label: str
    changed_modules: list[ProjectModule]
    source_version_number: int | None = None
    created_at: datetime


class ProjectVersionResponse(ProjectVersionSummary):
    name: str
    description: str
    status: ProjectStatus
    snapshot: ProjectSnapshot


class ProjectVersionListResponse(StrictModel):
    items: list[ProjectVersionSummary]
    total: int

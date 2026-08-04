# -*- coding: utf-8 -*-
"""Pydantic contracts for accounts, organizations, memberships, and sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["owner", "admin", "editor", "viewer"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    organization_name: str = Field(default="", max_length=120)

    @field_validator("email", "display_name", "organization_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return value.strip()


class UserResponse(StrictModel):
    id: str
    email: str
    display_name: str


class OrganizationResponse(StrictModel):
    id: str
    name: str
    slug: str
    role: Role
    created_at: datetime


class SessionResponse(StrictModel):
    authenticated: bool = True
    user: UserResponse
    organizations: list[OrganizationResponse]
    csrf_token: str
    expires_at: datetime


class AnonymousSessionResponse(StrictModel):
    authenticated: bool = False
    user: None = None
    organizations: list[OrganizationResponse] = Field(default_factory=list)
    csrf_token: str = ""
    expires_at: None = None


class OrganizationCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("组织名称不能为空。")
        return cleaned


class MemberCreateRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    role: Role = "viewer"

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return value.strip()


class MemberUpdateRequest(StrictModel):
    role: Role


class MemberResponse(StrictModel):
    user_id: str
    email: str
    display_name: str
    role: Role
    created_at: datetime


class MemberListResponse(StrictModel):
    items: list[MemberResponse]
    total: int


class ClaimWorkspaceProjectsResponse(StrictModel):
    ok: bool = True
    claimed: int


class DeleteResponse(StrictModel):
    ok: bool = True

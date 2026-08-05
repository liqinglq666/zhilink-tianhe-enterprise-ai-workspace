# -*- coding: utf-8 -*-
"""Local account, organization, RBAC, session, and scoped project access store."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    delete,
    exists,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .project_store import (
    Base,
    ProjectHistoryNotFound,
    ProjectHistoryRecord,
    ProjectNotFound,
    ProjectRecord,
    ProjectStoreUnavailable,
    ProjectVersionConflict,
    _changed_modules,
    _history_to_dict,
    _initial_modules,
    _project_to_dict,
    get_project_store,
    hash_workspace_key,
)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ROLE_ORDER = {"viewer": 10, "editor": 20, "admin": 30, "owner": 40}
ROLE_PERMISSIONS = {
    "viewer": {"organization:read", "member:read", "project:read", "history:read"},
    "editor": {
        "organization:read",
        "member:read",
        "project:read",
        "project:create",
        "project:update",
        "history:read",
        "history:restore",
    },
    "admin": {
        "organization:read",
        "organization:update",
        "member:read",
        "member:manage",
        "project:read",
        "project:create",
        "project:update",
        "project:delete",
        "project:claim",
        "history:read",
        "history:restore",
    },
    "owner": {
        "organization:read",
        "organization:update",
        "organization:delete",
        "member:read",
        "member:manage",
        "owner:manage",
        "project:read",
        "project:create",
        "project:update",
        "project:delete",
        "project:claim",
        "history:read",
        "history:restore",
    },
}
Role = Literal["owner", "admin", "editor", "viewer"]


class AccountStoreError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class AuthSession:
    id: str
    user_id: str
    email: str
    display_name: str
    csrf_hash: str
    expires_at: datetime


@dataclass(frozen=True)
class ProjectScope:
    kind: Literal["anonymous", "organization"]
    storage_hash: str
    organization_id: str | None = None
    user_id: str | None = None
    role: Role | None = None


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrganizationRecord(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class OrganizationMembershipRecord(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuthSessionRecord(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class OrganizationProjectRecord(Base):
    __tablename__ = "organization_projects"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if len(email) > 320 or not EMAIL_RE.fullmatch(email):
        raise AccountStoreError(422, "AUTH_EMAIL_INVALID", "请输入有效的邮箱地址。")
    return email


def password_min_length() -> int:
    try:
        configured = int(os.getenv("PASSWORD_MIN_LENGTH", "10"))
    except ValueError:
        configured = 10
    return max(8, min(configured, 64))


def validate_password(password: str) -> str:
    value = password or ""
    minimum = password_min_length()
    if len(value) < minimum:
        raise AccountStoreError(
            422,
            "AUTH_PASSWORD_TOO_SHORT",
            f"密码至少需要 {minimum} 个字符。",
        )
    if len(value) > 128:
        raise AccountStoreError(422, "AUTH_PASSWORD_TOO_LONG", "密码最多允许 128 个字符。")
    return value


def hash_password(password: str) -> str:
    value = validate_password(password)
    salt = secrets.token_bytes(16)
    n, r, p = 16384, 8, 1
    digest = hashlib.scrypt(value.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"scrypt${n}${r}${p}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n_raw, r_raw, p_raw, salt_raw, digest_raw = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        pad = lambda value: value + ("=" * (-len(value) % 4))
        salt = base64.urlsafe_b64decode(pad(salt_raw))
        expected = base64.urlsafe_b64decode(pad(digest_raw))
        actual = hashlib.scrypt(
            (password or "").encode("utf-8"),
            salt=salt,
            n=int(n_raw),
            r=int(r_raw),
            p=int(p_raw),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _organization_slug() -> str:
    return f"org-{secrets.token_hex(8)}"


def _organization_storage_hash(organization_id: str) -> str:
    return _sha256(f"organization:{organization_id}")


class AccountStore:
    def __init__(self, projects=None) -> None:
        try:
            self.projects = projects or get_project_store()
            Base.metadata.create_all(self.projects.engine)
            self.sessions = self.projects.sessions
        except (SQLAlchemyError, ProjectStoreUnavailable) as exc:
            raise AccountStoreError(
                503,
                "ACCOUNT_STORAGE_UNAVAILABLE",
                "账号与组织存储暂时不可用，请稍后重试。",
                retryable=True,
            ) from exc

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        organization_name: str,
        user_agent: str = "",
    ) -> tuple[AuthSession, str, str]:
        if os.getenv("AUTH_ALLOW_REGISTRATION", "true").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            raise AccountStoreError(403, "AUTH_REGISTRATION_DISABLED", "当前部署未开放注册。")
        normalized = normalize_email(email)
        name = (display_name or "").strip()[:120]
        if not name:
            raise AccountStoreError(422, "AUTH_DISPLAY_NAME_REQUIRED", "请填写姓名或显示名称。")
        org_name = (organization_name or "").strip()[:120] or f"{name}的工作区"
        user = UserRecord(
            id=str(uuid4()),
            email=normalized,
            display_name=name,
            password_hash=hash_password(password),
        )
        organization = OrganizationRecord(
            id=str(uuid4()),
            name=org_name,
            slug=_organization_slug(),
            created_by_user_id=user.id,
        )
        membership = OrganizationMembershipRecord(
            id=str(uuid4()),
            organization_id=organization.id,
            user_id=user.id,
            role="owner",
        )
        try:
            with self.sessions.begin() as session:
                session.add_all([user, organization, membership])
                session.flush()
            return self._create_session(user, user_agent=user_agent)
        except IntegrityError as exc:
            raise AccountStoreError(409, "AUTH_EMAIL_EXISTS", "该邮箱已经注册，请直接登录。") from exc
        except SQLAlchemyError as exc:
            raise AccountStoreError(
                503,
                "ACCOUNT_STORAGE_UNAVAILABLE",
                "账号创建失败，请稍后重试。",
                retryable=True,
            ) from exc

    def login(
        self, *, email: str, password: str, user_agent: str = ""
    ) -> tuple[AuthSession, str, str]:
        normalized = normalize_email(email)
        try:
            with self.sessions.begin() as session:
                user = session.scalar(select(UserRecord).where(UserRecord.email == normalized))
                if (
                    user is None
                    or user.status != "active"
                    or not verify_password(password, user.password_hash)
                ):
                    raise AccountStoreError(
                        401,
                        "AUTH_INVALID_CREDENTIALS",
                        "邮箱或密码不正确。",
                    )
                user.last_login_at = _now()
                session.flush()
            return self._create_session(user, user_agent=user_agent)
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(
                503,
                "ACCOUNT_STORAGE_UNAVAILABLE",
                "登录服务暂时不可用，请稍后重试。",
                retryable=True,
            ) from exc

    def _create_session(
        self, user: UserRecord, *, user_agent: str
    ) -> tuple[AuthSession, str, str]:
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        ttl_hours = max(1, min(int(os.getenv("SESSION_TTL_HOURS", "168")), 720))
        record = AuthSessionRecord(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=_sha256(token),
            csrf_hash=_sha256(csrf),
            user_agent_hash=_sha256((user_agent or "")[:1000]),
            expires_at=_now() + timedelta(hours=ttl_hours),
        )
        try:
            with self.sessions.begin() as session:
                session.execute(
                    delete(AuthSessionRecord).where(AuthSessionRecord.expires_at < _now())
                )
                session.add(record)
                session.flush()
            context = AuthSession(
                id=record.id,
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                csrf_hash=record.csrf_hash,
                expires_at=record.expires_at,
            )
            return context, token, csrf
        except SQLAlchemyError as exc:
            raise AccountStoreError(
                503,
                "ACCOUNT_STORAGE_UNAVAILABLE",
                "登录会话创建失败，请稍后重试。",
                retryable=True,
            ) from exc

    def get_session(self, token: str | None) -> AuthSession | None:
        raw = (token or "").strip()
        if not raw:
            return None
        try:
            with self.sessions.begin() as session:
                record = session.scalar(
                    select(AuthSessionRecord).where(AuthSessionRecord.token_hash == _sha256(raw))
                )
                if record is None:
                    return None
                if _aware(record.expires_at) <= _now():
                    session.delete(record)
                    return None
                user = session.get(UserRecord, record.user_id)
                if user is None or user.status != "active":
                    session.delete(record)
                    return None
                if _now() - _aware(record.last_seen_at) > timedelta(minutes=5):
                    record.last_seen_at = _now()
                return AuthSession(
                    id=record.id,
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    csrf_hash=record.csrf_hash,
                    expires_at=record.expires_at,
                )
        except SQLAlchemyError as exc:
            raise AccountStoreError(
                503,
                "ACCOUNT_STORAGE_UNAVAILABLE",
                "登录状态暂时无法读取，请稍后重试。",
                retryable=True,
            ) from exc

    def rotate_csrf(self, session_id: str) -> str:
        csrf = secrets.token_urlsafe(32)
        try:
            with self.sessions.begin() as session:
                record = session.get(AuthSessionRecord, session_id)
                if record is None or _aware(record.expires_at) <= _now():
                    raise AccountStoreError(401, "AUTH_REQUIRED", "登录状态已失效，请重新登录。")
                record.csrf_hash = _sha256(csrf)
            return csrf
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "会话更新失败。", retryable=True) from exc

    def verify_csrf(self, auth: AuthSession, header_token: str, cookie_token: str) -> None:
        header = (header_token or "").strip()
        cookie = (cookie_token or "").strip()
        if not header or not cookie or not hmac.compare_digest(header, cookie):
            raise AccountStoreError(403, "CSRF_TOKEN_INVALID", "安全校验失败，请刷新页面后重试。")
        if not hmac.compare_digest(_sha256(header), auth.csrf_hash):
            raise AccountStoreError(403, "CSRF_TOKEN_INVALID", "安全校验失败，请刷新页面后重试。")

    def logout(self, session_id: str) -> None:
        try:
            with self.sessions.begin() as session:
                session.execute(delete(AuthSessionRecord).where(AuthSessionRecord.id == session_id))
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "退出登录失败。", retryable=True) from exc

    def list_organizations(self, user_id: str) -> list[dict[str, Any]]:
        try:
            with self.sessions() as session:
                rows = session.execute(
                    select(OrganizationRecord, OrganizationMembershipRecord)
                    .join(
                        OrganizationMembershipRecord,
                        OrganizationMembershipRecord.organization_id == OrganizationRecord.id,
                    )
                    .where(
                        OrganizationMembershipRecord.user_id == user_id,
                        OrganizationMembershipRecord.status == "active",
                    )
                    .order_by(OrganizationRecord.created_at.asc())
                ).all()
                return [
                    {
                        "id": organization.id,
                        "name": organization.name,
                        "slug": organization.slug,
                        "role": membership.role,
                        "created_at": organization.created_at,
                    }
                    for organization, membership in rows
                ]
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "组织列表读取失败。", retryable=True) from exc

    def create_organization(self, user_id: str, name: str) -> dict[str, Any]:
        cleaned = (name or "").strip()[:120]
        if not cleaned:
            raise AccountStoreError(422, "ORGANIZATION_NAME_REQUIRED", "请填写组织名称。")
        organization = OrganizationRecord(
            id=str(uuid4()),
            name=cleaned,
            slug=_organization_slug(),
            created_by_user_id=user_id,
        )
        membership = OrganizationMembershipRecord(
            id=str(uuid4()),
            organization_id=organization.id,
            user_id=user_id,
            role="owner",
        )
        try:
            with self.sessions.begin() as session:
                session.add_all([organization, membership])
                session.flush()
            return {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
                "role": "owner",
                "created_at": organization.created_at,
            }
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "组织创建失败。", retryable=True) from exc

    def membership(self, user_id: str, organization_id: str) -> dict[str, Any]:
        try:
            with self.sessions() as session:
                row = session.execute(
                    select(OrganizationRecord, OrganizationMembershipRecord)
                    .join(
                        OrganizationMembershipRecord,
                        OrganizationMembershipRecord.organization_id == OrganizationRecord.id,
                    )
                    .where(
                        OrganizationRecord.id == organization_id,
                        OrganizationMembershipRecord.user_id == user_id,
                        OrganizationMembershipRecord.status == "active",
                    )
                ).first()
                if row is None:
                    raise AccountStoreError(404, "ORGANIZATION_NOT_FOUND", "组织不存在或无权访问。")
                organization, member = row
                return {
                    "organization_id": organization.id,
                    "organization_name": organization.name,
                    "user_id": user_id,
                    "role": member.role,
                }
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "组织权限读取失败。", retryable=True) from exc

    def require_permission(self, user_id: str, organization_id: str, permission: str) -> dict[str, Any]:
        member = self.membership(user_id, organization_id)
        if permission not in ROLE_PERMISSIONS.get(member["role"], set()):
            raise AccountStoreError(403, "RBAC_FORBIDDEN", "当前组织角色没有执行此操作的权限。")
        return member

    def list_members(self, actor_user_id: str, organization_id: str) -> list[dict[str, Any]]:
        self.require_permission(actor_user_id, organization_id, "member:read")
        try:
            with self.sessions() as session:
                rows = session.execute(
                    select(UserRecord, OrganizationMembershipRecord)
                    .join(
                        OrganizationMembershipRecord,
                        OrganizationMembershipRecord.user_id == UserRecord.id,
                    )
                    .where(
                        OrganizationMembershipRecord.organization_id == organization_id,
                        OrganizationMembershipRecord.status == "active",
                    )
                    .order_by(OrganizationMembershipRecord.created_at.asc())
                ).all()
                return [
                    {
                        "user_id": user.id,
                        "email": user.email,
                        "display_name": user.display_name,
                        "role": member.role,
                        "created_at": member.created_at,
                    }
                    for user, member in rows
                ]
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "成员列表读取失败。", retryable=True) from exc

    def _validate_role_change(self, actor_role: str, target_role: str, new_role: str | None) -> None:
        if target_role == "owner" and actor_role != "owner":
            raise AccountStoreError(403, "RBAC_FORBIDDEN", "只有组织所有者可以管理所有者。")
        if new_role in {"owner", "admin"} and actor_role != "owner":
            raise AccountStoreError(403, "RBAC_FORBIDDEN", "只有组织所有者可以授予所有者或管理员角色。")
        if actor_role == "admin" and target_role == "admin":
            raise AccountStoreError(403, "RBAC_FORBIDDEN", "管理员不能修改其他管理员。")

    def add_member(self, actor_user_id: str, organization_id: str, email: str, role: Role) -> dict[str, Any]:
        actor = self.require_permission(actor_user_id, organization_id, "member:manage")
        self._validate_role_change(actor["role"], "viewer", role)
        normalized = normalize_email(email)
        try:
            with self.sessions.begin() as session:
                user = session.scalar(select(UserRecord).where(UserRecord.email == normalized))
                if user is None:
                    raise AccountStoreError(
                        404,
                        "MEMBER_USER_NOT_FOUND",
                        "该邮箱尚未注册。请对方先注册，再添加为组织成员。",
                    )
                existing = session.scalar(
                    select(OrganizationMembershipRecord).where(
                        OrganizationMembershipRecord.organization_id == organization_id,
                        OrganizationMembershipRecord.user_id == user.id,
                    )
                )
                if existing is not None and existing.status == "active":
                    raise AccountStoreError(409, "MEMBER_ALREADY_EXISTS", "该用户已经是组织成员。")
                if existing is None:
                    existing = OrganizationMembershipRecord(
                        id=str(uuid4()),
                        organization_id=organization_id,
                        user_id=user.id,
                        role=role,
                    )
                    session.add(existing)
                else:
                    existing.status = "active"
                    existing.role = role
                    existing.updated_at = _now()
                session.flush()
                return {
                    "user_id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": existing.role,
                    "created_at": existing.created_at,
                }
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "成员添加失败。", retryable=True) from exc

    def _owner_count(self, session, organization_id: str) -> int:
        return int(
            session.scalar(
                select(func.count(OrganizationMembershipRecord.id)).where(
                    OrganizationMembershipRecord.organization_id == organization_id,
                    OrganizationMembershipRecord.status == "active",
                    OrganizationMembershipRecord.role == "owner",
                )
            )
            or 0
        )

    def update_member_role(
        self,
        actor_user_id: str,
        organization_id: str,
        target_user_id: str,
        role: Role,
    ) -> dict[str, Any]:
        actor = self.require_permission(actor_user_id, organization_id, "member:manage")
        try:
            with self.sessions.begin() as session:
                membership = session.scalar(
                    select(OrganizationMembershipRecord)
                    .where(
                        OrganizationMembershipRecord.organization_id == organization_id,
                        OrganizationMembershipRecord.user_id == target_user_id,
                        OrganizationMembershipRecord.status == "active",
                    )
                    .with_for_update()
                )
                if membership is None:
                    raise AccountStoreError(404, "MEMBER_NOT_FOUND", "组织成员不存在。")
                self._validate_role_change(actor["role"], membership.role, role)
                if membership.role == "owner" and role != "owner" and self._owner_count(session, organization_id) <= 1:
                    raise AccountStoreError(409, "LAST_OWNER_REQUIRED", "组织必须至少保留一名所有者。")
                membership.role = role
                membership.updated_at = _now()
                user = session.get(UserRecord, target_user_id)
                session.flush()
                return {
                    "user_id": target_user_id,
                    "email": user.email if user else "",
                    "display_name": user.display_name if user else "",
                    "role": role,
                    "created_at": membership.created_at,
                }
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "成员角色更新失败。", retryable=True) from exc

    def remove_member(self, actor_user_id: str, organization_id: str, target_user_id: str) -> None:
        actor = self.require_permission(actor_user_id, organization_id, "member:manage")
        try:
            with self.sessions.begin() as session:
                membership = session.scalar(
                    select(OrganizationMembershipRecord)
                    .where(
                        OrganizationMembershipRecord.organization_id == organization_id,
                        OrganizationMembershipRecord.user_id == target_user_id,
                        OrganizationMembershipRecord.status == "active",
                    )
                    .with_for_update()
                )
                if membership is None:
                    raise AccountStoreError(404, "MEMBER_NOT_FOUND", "组织成员不存在。")
                self._validate_role_change(actor["role"], membership.role, None)
                if membership.role == "owner" and self._owner_count(session, organization_id) <= 1:
                    raise AccountStoreError(409, "LAST_OWNER_REQUIRED", "组织必须至少保留一名所有者。")
                membership.status = "removed"
                membership.updated_at = _now()
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "成员移除失败。", retryable=True) from exc

    def anonymous_scope(self, workspace_key: str) -> ProjectScope:
        return ProjectScope(kind="anonymous", storage_hash=hash_workspace_key(workspace_key))

    def organization_scope(
        self,
        user_id: str,
        organization_id: str,
        permission: str,
    ) -> ProjectScope:
        member = self.require_permission(user_id, organization_id, permission)
        return ProjectScope(
            kind="organization",
            storage_hash=_organization_storage_hash(organization_id),
            organization_id=organization_id,
            user_id=user_id,
            role=member["role"],
        )

    def _project_query(self, scope: ProjectScope):
        query = select(ProjectRecord)
        if scope.kind == "organization":
            return query.join(
                OrganizationProjectRecord,
                OrganizationProjectRecord.project_id == ProjectRecord.id,
            ).where(OrganizationProjectRecord.organization_id == scope.organization_id)
        return query.where(
            ProjectRecord.workspace_hash == scope.storage_hash,
            ~exists(
                select(OrganizationProjectRecord.project_id).where(
                    OrganizationProjectRecord.project_id == ProjectRecord.id
                )
            ),
        )

    def _get_project_record(self, session, scope: ProjectScope, project_id: str, *, lock: bool = False):
        query = self._project_query(scope).where(ProjectRecord.id == project_id)
        if lock:
            query = query.with_for_update()
        record = session.scalar(query)
        if record is None:
            raise ProjectNotFound("项目不存在或无权访问。")
        return record

    def list_projects(
        self,
        scope: ProjectScope,
        *,
        limit: int,
        offset: int,
        include_archived: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        try:
            with self.sessions() as session:
                query = self._project_query(scope)
                if not include_archived:
                    query = query.where(ProjectRecord.status == "active")
                total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
                records = session.scalars(
                    query.order_by(ProjectRecord.updated_at.desc()).limit(limit).offset(offset)
                ).all()
                return [_project_to_dict(record, include_snapshot=False) for record in records], int(total)
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目列表读取失败。") from exc

    def create_project(
        self,
        scope: ProjectScope,
        *,
        name: str,
        description: str,
        snapshot: dict[str, Any],
        version_label: str,
    ) -> dict[str, Any]:
        record = ProjectRecord(
            id=str(uuid4()),
            workspace_hash=scope.storage_hash,
            name=name,
            description=description,
            snapshot=snapshot,
        )
        try:
            with self.sessions.begin() as session:
                session.add(record)
                session.flush()
                if scope.kind == "organization":
                    session.add(
                        OrganizationProjectRecord(
                            project_id=record.id,
                            organization_id=scope.organization_id or "",
                            created_by_user_id=scope.user_id or "",
                        )
                    )
                self.projects._append_history(
                    session,
                    record,
                    change_kind="create",
                    label=version_label,
                    changed_modules=_initial_modules(snapshot),
                )
            return _project_to_dict(record)
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目保存失败。") from exc

    def get_project(self, scope: ProjectScope, project_id: str) -> dict[str, Any]:
        try:
            with self.sessions() as session:
                return _project_to_dict(self._get_project_record(session, scope, project_id))
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目读取失败。") from exc

    def update_project(
        self,
        scope: ProjectScope,
        project_id: str,
        *,
        expected_lock_version: int,
        name: str | None,
        description: str | None,
        status: str | None,
        snapshot: dict[str, Any] | None,
        version_label: str,
    ) -> dict[str, Any]:
        try:
            with self.sessions.begin() as session:
                record = self._get_project_record(session, scope, project_id, lock=True)
                if record.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(record.lock_version)
                old_snapshot = dict(record.snapshot or {})
                old_name, old_description, old_status = record.name, record.description, record.status
                if name is not None:
                    record.name = name
                if description is not None:
                    record.description = description
                if status is not None:
                    record.status = status
                if snapshot is not None:
                    record.snapshot = snapshot
                metadata_changed = (
                    record.name != old_name
                    or record.description != old_description
                    or record.status != old_status
                )
                snapshot_changed = dict(record.snapshot or {}) != old_snapshot
                if not metadata_changed and not snapshot_changed and not version_label:
                    return _project_to_dict(record)
                change_kind = "save"
                if (
                    record.status != old_status
                    and not snapshot_changed
                    and record.name == old_name
                    and record.description == old_description
                ):
                    change_kind = "archive" if record.status == "archived" else "unarchive"
                elif metadata_changed and not snapshot_changed:
                    change_kind = "metadata"
                record.lock_version += 1
                record.updated_at = _now()
                session.flush()
                self.projects._append_history(
                    session,
                    record,
                    change_kind=change_kind,
                    label=version_label,
                    changed_modules=_changed_modules(
                        old_snapshot,
                        record.snapshot or {},
                        metadata_changed=metadata_changed,
                    )
                    or ["project"],
                )
            return _project_to_dict(record)
        except (ProjectNotFound, ProjectVersionConflict):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目更新失败。") from exc

    def list_history(
        self, scope: ProjectScope, project_id: str, *, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        try:
            with self.sessions() as session:
                self._get_project_record(session, scope, project_id)
                filters = [ProjectHistoryRecord.project_id == project_id]
                total = session.scalar(select(func.count(ProjectHistoryRecord.id)).where(*filters)) or 0
                records = session.scalars(
                    select(ProjectHistoryRecord)
                    .where(*filters)
                    .order_by(ProjectHistoryRecord.version_number.desc())
                    .limit(limit)
                    .offset(offset)
                ).all()
                return [_history_to_dict(record) for record in records], int(total)
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目版本历史读取失败。") from exc

    def get_history(self, scope: ProjectScope, project_id: str, version_number: int) -> dict[str, Any]:
        try:
            with self.sessions() as session:
                self._get_project_record(session, scope, project_id)
                record = session.scalar(
                    select(ProjectHistoryRecord).where(
                        ProjectHistoryRecord.project_id == project_id,
                        ProjectHistoryRecord.version_number == version_number,
                    )
                )
                if record is None:
                    raise ProjectHistoryNotFound("项目版本不存在。")
                return _history_to_dict(record, include_snapshot=True)
        except (ProjectNotFound, ProjectHistoryNotFound):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目版本读取失败。") from exc

    def restore_history(
        self,
        scope: ProjectScope,
        project_id: str,
        version_number: int,
        *,
        expected_lock_version: int,
        version_label: str,
    ) -> dict[str, Any]:
        try:
            with self.sessions.begin() as session:
                project = self._get_project_record(session, scope, project_id, lock=True)
                if project.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(project.lock_version)
                source = session.scalar(
                    select(ProjectHistoryRecord).where(
                        ProjectHistoryRecord.project_id == project_id,
                        ProjectHistoryRecord.version_number == version_number,
                    )
                )
                if source is None:
                    raise ProjectHistoryNotFound("项目版本不存在。")
                old_snapshot = dict(project.snapshot or {})
                project.snapshot = dict(source.snapshot or {})
                project.lock_version += 1
                project.updated_at = _now()
                session.flush()
                self.projects._append_history(
                    session,
                    project,
                    change_kind="restore",
                    label=version_label,
                    changed_modules=_changed_modules(old_snapshot, project.snapshot or {}) or ["project"],
                    source_version_number=version_number,
                )
            return _project_to_dict(project)
        except (ProjectNotFound, ProjectHistoryNotFound, ProjectVersionConflict):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目版本恢复失败。") from exc

    def delete_project(self, scope: ProjectScope, project_id: str) -> None:
        try:
            with self.sessions.begin() as session:
                record = self._get_project_record(session, scope, project_id, lock=True)
                session.execute(delete(OrganizationProjectRecord).where(OrganizationProjectRecord.project_id == project_id))
                session.execute(delete(ProjectHistoryRecord).where(ProjectHistoryRecord.project_id == project_id))
                session.delete(record)
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目删除失败。") from exc

    def claim_workspace_projects(
        self, actor_user_id: str, organization_id: str, workspace_key: str
    ) -> int:
        self.require_permission(actor_user_id, organization_id, "project:claim")
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions.begin() as session:
                records = session.scalars(
                    select(ProjectRecord).where(
                        ProjectRecord.workspace_hash == workspace_hash,
                        ~exists(
                            select(OrganizationProjectRecord.project_id).where(
                                OrganizationProjectRecord.project_id == ProjectRecord.id
                            )
                        ),
                    )
                ).all()
                for record in records:
                    session.add(
                        OrganizationProjectRecord(
                            project_id=record.id,
                            organization_id=organization_id,
                            created_by_user_id=actor_user_id,
                        )
                    )
                return len(records)
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "ACCOUNT_STORAGE_UNAVAILABLE", "匿名项目迁移失败。", retryable=True) from exc


_ACCOUNT_STORE: AccountStore | None = None


def get_account_store() -> AccountStore:
    global _ACCOUNT_STORE
    projects = get_project_store()
    if _ACCOUNT_STORE is None or _ACCOUNT_STORE.projects is not projects:
        _ACCOUNT_STORE = AccountStore(projects)
    return _ACCOUNT_STORE


def reset_account_store_for_tests() -> None:
    global _ACCOUNT_STORE
    _ACCOUNT_STORE = None

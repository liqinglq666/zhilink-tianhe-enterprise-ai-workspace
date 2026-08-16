# -*- coding: utf-8 -*-
"""Portable SQLAlchemy project store with immutable project versions."""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    select,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./runtime/zhilink.db"
MODULE_ORDER = (
    "project",
    "identity",
    "profile",
    "meeting",
    "contract",
    "policy",
    "match",
    "landing",
    "report",
)
FORM_MODULES = {
    "profileName": "profile",
    "profileIndustry": "profile",
    "profileLocation": "profile",
    "profileScale": "profile",
    "profileStage": "profile",
    "profileRole": "profile",
    "profileDemands": "profile",
    "meetingInput": "meeting",
    "contractInput": "contract",
    "policyDemand": "policy",
    "offerInput": "match",
    "needInput": "match",
    "targetInput": "match",
    "scenarioInput": "match",
    "pilotScene": "landing",
    "userRoles": "landing",
    "dataScope": "landing",
    "deployment": "landing",
    "pilotPeriod": "landing",
    "reviewMode": "landing",
}


class ProjectStoreError(Exception):
    pass


class ProjectNotFound(ProjectStoreError):
    pass


class ProjectHistoryNotFound(ProjectStoreError):
    pass


class ProjectVersionConflict(ProjectStoreError):
    def __init__(self, current_version: int):
        super().__init__("project version conflict")
        self.current_version = current_version


class ProjectStoreUnavailable(ProjectStoreError):
    pass


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ProjectHistoryRecord(Base):
    __tablename__ = "project_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_project_version_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    workspace_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    changed_modules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_name: Mapped[str] = mapped_column(String(120), nullable=False)
    project_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_status: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


def normalize_database_url(raw: str | None) -> str:
    value = (raw or DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    if value.startswith("postgresql+psycopg://") or value.startswith("sqlite://"):
        return value
    raise ValueError("DATABASE_URL 仅支持 SQLite 或 PostgreSQL。")


def hash_workspace_key(workspace_key: str) -> str:
    key = (workspace_key or "").strip()
    if not 32 <= len(key) <= 256:
        raise ValueError("工作区密钥长度必须在 32 到 256 个字符之间。")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.drivername.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database == ":memory:":
            kwargs["poolclass"] = StaticPool
        elif url.database:
            Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, **kwargs)


def _project_to_dict(record: ProjectRecord, *, include_snapshot: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": record.id,
        "name": record.name,
        "description": record.description,
        "status": record.status,
        "lock_version": record.lock_version,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    if include_snapshot:
        data["snapshot"] = dict(record.snapshot or {})
    return data


def _history_to_dict(record: ProjectHistoryRecord, *, include_snapshot: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": record.id,
        "project_id": record.project_id,
        "version_number": record.version_number,
        "change_kind": record.change_kind,
        "label": record.label,
        "changed_modules": list(record.changed_modules or []),
        "source_version_number": record.source_version_number,
        "created_at": record.created_at,
    }
    if include_snapshot:
        data.update(
            {
                "name": record.project_name,
                "description": record.project_description,
                "status": record.project_status,
                "snapshot": dict(record.snapshot or {}),
            }
        )
    return data


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _changed_modules(
    old_snapshot: Mapping[str, Any],
    new_snapshot: Mapping[str, Any],
    *,
    metadata_changed: bool = False,
) -> list[str]:
    changed: set[str] = set()
    if metadata_changed:
        changed.add("project")
    if _mapping(old_snapshot).get("current_section") != _mapping(new_snapshot).get("current_section"):
        changed.add("project")
    if _mapping(old_snapshot).get("identity") != _mapping(new_snapshot).get("identity"):
        changed.add("identity")
    if _mapping(old_snapshot).get("profile") != _mapping(new_snapshot).get("profile"):
        changed.add("profile")

    old_forms = _mapping(_mapping(old_snapshot).get("forms"))
    new_forms = _mapping(_mapping(new_snapshot).get("forms"))
    for field in set(old_forms) | set(new_forms):
        if old_forms.get(field) != new_forms.get(field):
            changed.add(FORM_MODULES.get(field, "project"))

    for container_name in ("results", "meta"):
        old_values = _mapping(_mapping(old_snapshot).get(container_name))
        new_values = _mapping(_mapping(new_snapshot).get(container_name))
        for key in set(old_values) | set(new_values):
            if old_values.get(key) != new_values.get(key):
                changed.add(key if key in MODULE_ORDER else "project")

    return [module for module in MODULE_ORDER if module in changed]


def _initial_modules(snapshot: Mapping[str, Any]) -> list[str]:
    empty: dict[str, Any] = {
        "identity": {},
        "profile": {},
        "forms": {},
        "results": {},
        "meta": {},
        "current_section": "home",
    }
    modules = _changed_modules(empty, snapshot, metadata_changed=True)
    return modules or ["project"]


def _default_label(change_kind: str, source_version_number: int | None = None) -> str:
    labels = {
        "create": "创建项目",
        "baseline": "启用版本历史时的当前快照",
        "save": "保存项目",
        "metadata": "更新项目信息",
        "archive": "归档项目",
        "unarchive": "恢复归档项目",
    }
    if change_kind == "restore":
        return f"恢复自版本 v{source_version_number}"
    return labels.get(change_kind, "更新项目")


class ProjectStore:
    def __init__(self, database_url: str):
        """Connect to a schema that has already been upgraded by Alembic."""
        try:
            self.database_url = normalize_database_url(database_url)
            self.engine = _build_engine(self.database_url)
            self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        except (SQLAlchemyError, OSError, ValueError) as exc:
            raise ProjectStoreUnavailable("项目数据库初始化失败。") from exc

    def _append_history(
        self,
        session,
        record: ProjectRecord,
        *,
        change_kind: str,
        label: str = "",
        changed_modules: list[str] | None = None,
        source_version_number: int | None = None,
    ) -> ProjectHistoryRecord:
        item = ProjectHistoryRecord(
            id=str(uuid4()),
            project_id=record.id,
            workspace_hash=record.workspace_hash,
            version_number=record.lock_version,
            change_kind=change_kind,
            label=(label or _default_label(change_kind, source_version_number))[:200],
            changed_modules=changed_modules or ["project"],
            source_version_number=source_version_number,
            project_name=record.name,
            project_description=record.description,
            project_status=record.status,
            snapshot=dict(record.snapshot or {}),
        )
        session.add(item)
        session.flush()
        return item

    def create(
        self,
        workspace_key: str,
        *,
        name: str,
        description: str,
        snapshot: dict[str, Any],
        version_label: str = "",
    ) -> dict[str, Any]:
        record = ProjectRecord(
            id=str(uuid4()),
            workspace_hash=hash_workspace_key(workspace_key),
            name=name,
            description=description,
            snapshot=snapshot,
        )
        try:
            with self.sessions.begin() as session:
                session.add(record)
                session.flush()
                self._append_history(
                    session,
                    record,
                    change_kind="create",
                    label=version_label,
                    changed_modules=_initial_modules(snapshot),
                )
            return _project_to_dict(record)
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目保存失败。") from exc

    def list(
        self,
        workspace_key: str,
        *,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions() as session:
                filters = [ProjectRecord.workspace_hash == workspace_hash]
                if not include_archived:
                    filters.append(ProjectRecord.status == "active")
                total = session.scalar(select(func.count(ProjectRecord.id)).where(*filters)) or 0
                records = session.scalars(
                    select(ProjectRecord)
                    .where(*filters)
                    .order_by(ProjectRecord.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                ).all()
                return [_project_to_dict(record, include_snapshot=False) for record in records], int(total)
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目列表读取失败。") from exc

    def get(self, workspace_key: str, project_id: str) -> dict[str, Any]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions() as session:
                record = session.scalar(
                    select(ProjectRecord).where(
                        ProjectRecord.id == project_id,
                        ProjectRecord.workspace_hash == workspace_hash,
                    )
                )
                if record is None:
                    raise ProjectNotFound("项目不存在或无权访问。")
                return _project_to_dict(record)
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目读取失败。") from exc

    def update(
        self,
        workspace_key: str,
        project_id: str,
        *,
        expected_lock_version: int,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        snapshot: dict[str, Any] | None = None,
        version_label: str = "",
    ) -> dict[str, Any]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions.begin() as session:
                record = session.scalar(
                    select(ProjectRecord)
                    .where(
                        ProjectRecord.id == project_id,
                        ProjectRecord.workspace_hash == workspace_hash,
                    )
                    .with_for_update()
                )
                if record is None:
                    raise ProjectNotFound("项目不存在或无权访问。")
                if record.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(record.lock_version)

                old_snapshot = dict(record.snapshot or {})
                old_name = record.name
                old_description = record.description
                old_status = record.status
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
                record.updated_at = datetime.now(timezone.utc)
                session.flush()
                self._append_history(
                    session,
                    record,
                    change_kind=change_kind,
                    label=version_label,
                    changed_modules=_changed_modules(
                        old_snapshot,
                        record.snapshot or {},
                        metadata_changed=metadata_changed,
                    ) or ["project"],
                )
            return _project_to_dict(record)
        except (ProjectNotFound, ProjectVersionConflict):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目更新失败。") from exc

    def list_history(
        self,
        workspace_key: str,
        project_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions() as session:
                project_exists = session.scalar(
                    select(func.count(ProjectRecord.id)).where(
                        ProjectRecord.id == project_id,
                        ProjectRecord.workspace_hash == workspace_hash,
                    )
                )
                if not project_exists:
                    raise ProjectNotFound("项目不存在或无权访问。")
                filters = [
                    ProjectHistoryRecord.project_id == project_id,
                    ProjectHistoryRecord.workspace_hash == workspace_hash,
                ]
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

    def get_history(self, workspace_key: str, project_id: str, version_number: int) -> dict[str, Any]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions() as session:
                record = session.scalar(
                    select(ProjectHistoryRecord).where(
                        ProjectHistoryRecord.project_id == project_id,
                        ProjectHistoryRecord.workspace_hash == workspace_hash,
                        ProjectHistoryRecord.version_number == version_number,
                    )
                )
                if record is None:
                    project_exists = session.scalar(
                        select(func.count(ProjectRecord.id)).where(
                            ProjectRecord.id == project_id,
                            ProjectRecord.workspace_hash == workspace_hash,
                        )
                    )
                    if not project_exists:
                        raise ProjectNotFound("项目不存在或无权访问。")
                    raise ProjectHistoryNotFound("项目版本不存在。")
                return _history_to_dict(record, include_snapshot=True)
        except (ProjectNotFound, ProjectHistoryNotFound):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目版本读取失败。") from exc

    def restore_history(
        self,
        workspace_key: str,
        project_id: str,
        version_number: int,
        *,
        expected_lock_version: int,
        version_label: str = "",
    ) -> dict[str, Any]:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions.begin() as session:
                project = session.scalar(
                    select(ProjectRecord)
                    .where(
                        ProjectRecord.id == project_id,
                        ProjectRecord.workspace_hash == workspace_hash,
                    )
                    .with_for_update()
                )
                if project is None:
                    raise ProjectNotFound("项目不存在或无权访问。")
                if project.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(project.lock_version)

                source = session.scalar(
                    select(ProjectHistoryRecord).where(
                        ProjectHistoryRecord.project_id == project_id,
                        ProjectHistoryRecord.workspace_hash == workspace_hash,
                        ProjectHistoryRecord.version_number == version_number,
                    )
                )
                if source is None:
                    raise ProjectHistoryNotFound("项目版本不存在。")

                old_snapshot = dict(project.snapshot or {})
                project.snapshot = dict(source.snapshot or {})
                project.lock_version += 1
                project.updated_at = datetime.now(timezone.utc)
                session.flush()
                self._append_history(
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

    def delete(self, workspace_key: str, project_id: str) -> None:
        workspace_hash = hash_workspace_key(workspace_key)
        try:
            with self.sessions.begin() as session:
                record = session.scalar(
                    select(ProjectRecord).where(
                        ProjectRecord.id == project_id,
                        ProjectRecord.workspace_hash == workspace_hash,
                    )
                )
                if record is None:
                    raise ProjectNotFound("项目不存在或无权访问。")
                session.execute(
                    delete(ProjectHistoryRecord).where(
                        ProjectHistoryRecord.project_id == project_id,
                        ProjectHistoryRecord.workspace_hash == workspace_hash,
                    )
                )
                session.delete(record)
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目删除失败。") from exc

    def ping(self) -> bool:
        try:
            with self.sessions() as session:
                session.execute(select(1))
            return True
        except SQLAlchemyError:
            return False


_STORE: ProjectStore | None = None
_STORE_URL = ""
_STORE_LOCK = threading.Lock()


def get_project_store() -> ProjectStore:
    global _STORE, _STORE_URL
    try:
        configured_url = normalize_database_url(os.getenv("DATABASE_URL"))
    except ValueError as exc:
        raise ProjectStoreUnavailable("项目数据库配置无效。") from exc
    with _STORE_LOCK:
        if _STORE is None or _STORE_URL != configured_url:
            if _STORE is not None:
                _STORE.engine.dispose()
            _STORE = ProjectStore(configured_url)
            _STORE_URL = configured_url
        return _STORE


def reset_project_store_for_tests() -> None:
    global _STORE, _STORE_URL
    with _STORE_LOCK:
        if _STORE is not None:
            _STORE.engine.dispose()
        _STORE = None
        _STORE_URL = ""

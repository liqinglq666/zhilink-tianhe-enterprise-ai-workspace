# -*- coding: utf-8 -*-
"""Portable SQLAlchemy project store for SQLite and PostgreSQL."""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, Text, create_engine, func, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./runtime/zhilink.db"


class ProjectStoreError(Exception):
    pass


class ProjectNotFound(ProjectStoreError):
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


def _record_to_dict(record: ProjectRecord, *, include_snapshot: bool = True) -> dict[str, Any]:
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


class ProjectStore:
    def __init__(self, database_url: str):
        self.database_url = normalize_database_url(database_url)
        try:
            self.engine = _build_engine(self.database_url)
            Base.metadata.create_all(self.engine)
        except (SQLAlchemyError, OSError, ValueError) as exc:
            raise ProjectStoreUnavailable("项目数据库初始化失败。") from exc
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create(
        self,
        workspace_key: str,
        *,
        name: str,
        description: str,
        snapshot: dict[str, Any],
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
            return _record_to_dict(record)
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
                total = session.scalar(
                    select(func.count(ProjectRecord.id)).where(*filters)
                ) or 0
                records = session.scalars(
                    select(ProjectRecord)
                    .where(*filters)
                    .order_by(ProjectRecord.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                ).all()
                return [
                    _record_to_dict(record, include_snapshot=False) for record in records
                ], int(total)
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
                return _record_to_dict(record)
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
    ) -> dict[str, Any]:
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
                if record.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(record.lock_version)
                if name is not None:
                    record.name = name
                if description is not None:
                    record.description = description
                if status is not None:
                    record.status = status
                if snapshot is not None:
                    record.snapshot = snapshot
                record.lock_version += 1
                record.updated_at = datetime.now(timezone.utc)
                session.flush()
            return _record_to_dict(record)
        except (ProjectNotFound, ProjectVersionConflict):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("项目更新失败。") from exc

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
    configured_url = normalize_database_url(os.getenv("DATABASE_URL"))
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

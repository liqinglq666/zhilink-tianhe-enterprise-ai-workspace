# -*- coding: utf-8 -*-
"""Server-owned review state and immutable review events."""
from __future__ import annotations

import copy
import hashlib
import threading
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, delete, event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .auth_store import ProjectScope, UserRecord, get_account_store
from .project_store import (
    Base,
    ProjectNotFound,
    ProjectRecord,
    ProjectStoreUnavailable,
    ProjectVersionConflict,
    _project_to_dict,
)

REVIEW_MODULES = ("profile", "meeting", "contract", "policy", "match", "landing", "report")
REVIEW_STATUSES = {"ai_draft", "edited", "pending_review", "changes_requested", "approved", "confirmed"}
REVIEW_ACTIONS = {"save_edit", "submit_review", "approve", "request_changes", "confirm", "revert_ai"}
ACTION_LABELS = {
    "save_edit": "人工编辑",
    "submit_review": "提交人工审核",
    "approve": "审核通过",
    "request_changes": "退回修改",
    "confirm": "匿名空间本地确认",
    "revert_ai": "恢复 AI 原始稿",
}


class ReviewWorkflowError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ProjectReviewEventRecord(Base):
    __tablename__ = "project_review_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    module: Mapped[str] = mapped_column(String(30), index=True)
    action: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


@event.listens_for(ProjectRecord, "before_delete")
def _cleanup_review_events(mapper, connection, target) -> None:  # noqa: ARG001
    connection.execute(delete(ProjectReviewEventRecord).where(ProjectReviewEventRecord.project_id == target.id))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _blank(content: str, updated_by: str = "系统") -> dict[str, Any]:
    digest = _hash(content)
    return {
        "status": "ai_draft",
        "source_content": "",
        "source_hash": digest,
        "content_hash": digest,
        "note": "",
        "revision": 1,
        "submitted_by_name": "",
        "submitted_at": "",
        "reviewed_by_name": "",
        "reviewed_at": "",
        "updated_by_name": updated_by,
        "updated_at": _now(),
    }


def _normalize(raw: Any, content: str) -> dict[str, Any]:
    data = dict(_map(raw))
    status = str(data.get("status") or "ai_draft")
    if status not in REVIEW_STATUSES:
        status = "ai_draft"
    current_hash = _hash(content)
    try:
        revision = max(1, min(int(data.get("revision") or 1), 1000000))
    except (TypeError, ValueError):
        revision = 1
    review = {
        "status": status,
        "source_content": str(data.get("source_content") or "")[:80000],
        "source_hash": str(data.get("source_hash") or "")[:64] or current_hash,
        "content_hash": str(data.get("content_hash") or current_hash)[:64],
        "note": str(data.get("note") or "")[:2000],
        "revision": revision,
        "submitted_by_name": str(data.get("submitted_by_name") or "")[:120],
        "submitted_at": str(data.get("submitted_at") or "")[:100],
        "reviewed_by_name": str(data.get("reviewed_by_name") or "")[:120],
        "reviewed_at": str(data.get("reviewed_at") or "")[:100],
        "updated_by_name": str(data.get("updated_by_name") or "系统")[:120],
        "updated_at": str(data.get("updated_at") or _now())[:100],
    }
    if review["content_hash"] != current_hash:
        return _blank(content, "系统：内容已变化，旧审核失效")
    return review


def prepare_created_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    prepared = copy.deepcopy(snapshot)
    results = dict(_map(prepared.get("results")))
    prepared["reviews"] = {
        module: _blank(str(results.get(module) or ""))
        for module in REVIEW_MODULES
        if str(results.get(module) or "")
    }
    return prepared


def prepare_updated_snapshot(current_snapshot: dict[str, Any], incoming_snapshot: dict[str, Any]) -> dict[str, Any]:
    current = copy.deepcopy(current_snapshot or {})
    prepared = copy.deepcopy(incoming_snapshot or {})
    old_results = dict(_map(current.get("results")))
    new_results = dict(_map(prepared.get("results")))
    old_reviews = dict(_map(current.get("reviews")))
    reviews: dict[str, Any] = {}
    for module in REVIEW_MODULES:
        new_content = str(new_results.get(module) or "")
        old_content = str(old_results.get(module) or "")
        if not new_content:
            continue
        reviews[module] = (
            _blank(new_content, "系统：内容已重新生成，需重新审核")
            if new_content != old_content
            else _normalize(old_reviews.get(module), new_content)
        )
    prepared["reviews"] = reviews
    return prepared


def _summary(module: str, review: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "status", "content_hash", "note", "revision", "submitted_by_name", "submitted_at",
        "reviewed_by_name", "reviewed_at", "updated_by_name", "updated_at",
    )
    return {"module": module, **{key: review.get(key, "") for key in keys}}


def _event(record: ProjectReviewEventRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "module": record.module,
        "action": record.action,
        "from_status": record.from_status,
        "to_status": record.to_status,
        "actor_name": record.actor_name,
        "actor_role": record.actor_role,
        "note": record.note,
        "content_hash": record.content_hash,
        "created_at": record.created_at,
    }


class ReviewStore:
    def __init__(self) -> None:
        self.accounts = get_account_store()
        try:
            Base.metadata.create_all(self.accounts.projects.engine)
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("人工审核数据表初始化失败。") from exc

    def _actor(self, session, scope: ProjectScope) -> tuple[str | None, str, str]:
        if scope.kind == "anonymous":
            return None, "匿名工作区使用者", "anonymous"
        user = session.get(UserRecord, scope.user_id) if scope.user_id else None
        return scope.user_id, (user.display_name if user else "组织成员")[:120], scope.role or "member"

    @staticmethod
    def _allow(scope: ProjectScope, action: str) -> None:
        if action not in REVIEW_ACTIONS:
            raise ReviewWorkflowError(400, "REVIEW_ACTION_INVALID", "不支持的审核操作。")
        if scope.kind == "anonymous":
            if action not in {"save_edit", "submit_review", "confirm", "revert_ai"}:
                raise ReviewWorkflowError(403, "REVIEW_ACTION_FORBIDDEN", "匿名空间不能形成组织审批。")
            return
        role = scope.role or "viewer"
        if role == "editor" and action not in {"save_edit", "submit_review", "revert_ai"}:
            raise ReviewWorkflowError(403, "REVIEW_ACTION_FORBIDDEN", "编辑者可以修改和提交，但不能批准或退回。")
        if role not in {"owner", "admin", "editor"}:
            raise ReviewWorkflowError(403, "REVIEW_ACTION_FORBIDDEN", "当前角色没有审核写入权限。")
        if action == "confirm":
            raise ReviewWorkflowError(400, "REVIEW_ACTION_INVALID", "组织空间请使用正式批准流程。")

    def list_reviews(self, scope: ProjectScope, project_id: str) -> dict[str, Any]:
        try:
            with self.accounts.sessions() as session:
                project = self.accounts._get_project_record(session, scope, project_id)
                snapshot = dict(project.snapshot or {})
                results, reviews = dict(_map(snapshot.get("results"))), dict(_map(snapshot.get("reviews")))
                items = []
                for module in REVIEW_MODULES:
                    content = str(results.get(module) or "")
                    if content:
                        items.append(_summary(module, _normalize(reviews.get(module), content)))
                return {"items": items, "total": len(items), "project_lock_version": project.lock_version}
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("审核状态读取失败。") from exc

    def get_review(self, scope: ProjectScope, project_id: str, module: str) -> dict[str, Any]:
        if module not in REVIEW_MODULES:
            raise ReviewWorkflowError(404, "REVIEW_MODULE_NOT_FOUND", "审核模块不存在。")
        try:
            with self.accounts.sessions() as session:
                project = self.accounts._get_project_record(session, scope, project_id)
                snapshot = dict(project.snapshot or {})
                content = str(_map(snapshot.get("results")).get(module) or "")
                if not content:
                    raise ReviewWorkflowError(404, "REVIEW_RESULT_NOT_FOUND", "当前模块还没有可审核的已保存结果。")
                return {
                    "module": module,
                    "review": _normalize(_map(snapshot.get("reviews")).get(module), content),
                    "working_content": content,
                    "project_lock_version": project.lock_version,
                }
        except (ProjectNotFound, ReviewWorkflowError):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("审核详情读取失败。") from exc

    def list_events(self, scope: ProjectScope, project_id: str, module: str) -> tuple[list[dict[str, Any]], int]:
        if module not in REVIEW_MODULES:
            raise ReviewWorkflowError(404, "REVIEW_MODULE_NOT_FOUND", "审核模块不存在。")
        try:
            with self.accounts.sessions() as session:
                self.accounts._get_project_record(session, scope, project_id)
                filters = [ProjectReviewEventRecord.project_id == project_id, ProjectReviewEventRecord.module == module]
                total = session.scalar(select(func.count(ProjectReviewEventRecord.id)).where(*filters)) or 0
                records = session.scalars(
                    select(ProjectReviewEventRecord).where(*filters).order_by(ProjectReviewEventRecord.created_at.desc()).limit(100)
                ).all()
                return [_event(item) for item in records], int(total)
        except ProjectNotFound:
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("审核记录读取失败。") from exc

    def act(
        self,
        scope: ProjectScope,
        project_id: str,
        module: str,
        *,
        expected_lock_version: int,
        action: str,
        content: str | None,
        note: str,
    ) -> dict[str, Any]:
        if module not in REVIEW_MODULES:
            raise ReviewWorkflowError(404, "REVIEW_MODULE_NOT_FOUND", "审核模块不存在。")
        self._allow(scope, action)
        note = (note or "").strip()[:2000]
        try:
            with self.accounts.sessions.begin() as session:
                project = self.accounts._get_project_record(session, scope, project_id, lock=True)
                if project.lock_version != expected_lock_version:
                    raise ProjectVersionConflict(project.lock_version)
                snapshot = copy.deepcopy(project.snapshot or {})
                results, reviews = dict(_map(snapshot.get("results"))), dict(_map(snapshot.get("reviews")))
                working = str(results.get(module) or "")
                if not working:
                    raise ReviewWorkflowError(404, "REVIEW_RESULT_NOT_FOUND", "当前模块还没有可审核的已保存结果。")
                review = _normalize(reviews.get(module), working)
                if not review["source_content"]:
                    review["source_content"] = working
                    review["source_hash"] = _hash(working)
                old_status = review["status"]
                user_id, actor_name, actor_role = self._actor(session, scope)
                now = _now()

                if action == "save_edit":
                    working = str(content or "")[:80000]
                    if not working.strip():
                        raise ReviewWorkflowError(422, "REVIEW_CONTENT_REQUIRED", "人工编辑内容不能为空。")
                    results[module], review["status"], review["note"] = working, "edited", note
                    review.update(submitted_by_name="", submitted_at="", reviewed_by_name="", reviewed_at="")
                elif action == "submit_review":
                    if content is not None:
                        working = str(content)[:80000]
                        if not working.strip():
                            raise ReviewWorkflowError(422, "REVIEW_CONTENT_REQUIRED", "提交审核的内容不能为空。")
                        results[module] = working
                    review.update(status="pending_review", note=note, submitted_by_name=actor_name, submitted_at=now, reviewed_by_name="", reviewed_at="")
                elif action == "approve":
                    if old_status != "pending_review":
                        raise ReviewWorkflowError(409, "REVIEW_STATUS_CONFLICT", "只有待审核材料可以批准。")
                    review.update(status="approved", note=note, reviewed_by_name=actor_name, reviewed_at=now)
                elif action == "request_changes":
                    if old_status != "pending_review":
                        raise ReviewWorkflowError(409, "REVIEW_STATUS_CONFLICT", "只有待审核材料可以退回修改。")
                    if not note:
                        raise ReviewWorkflowError(422, "REVIEW_NOTE_REQUIRED", "退回修改时必须填写审核意见。")
                    review.update(status="changes_requested", note=note, reviewed_by_name=actor_name, reviewed_at=now)
                elif action == "confirm":
                    review.update(status="confirmed", note=note, reviewed_by_name=actor_name, reviewed_at=now)
                elif action == "revert_ai":
                    source = str(review.get("source_content") or "")
                    if not source:
                        raise ReviewWorkflowError(409, "REVIEW_SOURCE_MISSING", "没有可恢复的 AI 原始稿。")
                    working, results[module] = source, source
                    review = _blank(source, actor_name)
                    review.update(source_content=source, source_hash=_hash(source), note=note)

                review["revision"] = min(int(review.get("revision") or 1) + 1, 1000000)
                review.update(content_hash=_hash(working), updated_by_name=actor_name, updated_at=now)
                reviews[module] = review
                snapshot.update(results=results, reviews=reviews)
                project.snapshot = snapshot
                project.lock_version += 1
                project.updated_at = datetime.now(timezone.utc)
                session.flush()
                self.accounts.projects._append_history(
                    session,
                    project,
                    change_kind="save",
                    label=f"{ACTION_LABELS[action]} · {module}",
                    changed_modules=[module],
                )
                record = ProjectReviewEventRecord(
                    id=str(uuid4()), project_id=project.id, module=module, action=action,
                    from_status=old_status, to_status=review["status"], actor_user_id=user_id,
                    actor_name=actor_name, actor_role=actor_role, note=note, content_hash=review["content_hash"],
                )
                session.add(record)
                session.flush()
                project_data, event_data = _project_to_dict(project), _event(record)
            return {"project": project_data, "review": review, "event": event_data}
        except (ProjectNotFound, ProjectVersionConflict, ReviewWorkflowError):
            raise
        except SQLAlchemyError as exc:
            raise ProjectStoreUnavailable("审核操作保存失败。") from exc


_REVIEW_STORE: ReviewStore | None = None
_REVIEW_LOCK = threading.Lock()


def get_review_store() -> ReviewStore:
    global _REVIEW_STORE
    accounts = get_account_store()
    with _REVIEW_LOCK:
        if _REVIEW_STORE is None or _REVIEW_STORE.accounts is not accounts:
            _REVIEW_STORE = ReviewStore()
        return _REVIEW_STORE


def reset_review_store_for_tests() -> None:
    global _REVIEW_STORE
    with _REVIEW_LOCK:
        _REVIEW_STORE = None

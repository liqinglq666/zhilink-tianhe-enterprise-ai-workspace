# -*- coding: utf-8 -*-
"""Persistent, organization-scoped enterprise-service workflows."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .auth_store import (
    AccountStoreError,
    OrganizationMembershipRecord,
    OrganizationProjectRecord,
    UserRecord,
    get_account_store,
)
from .knowledge_store import KnowledgeArticleRecord, KnowledgeVersionRecord
from .project_store import Base, ProjectRecord
from .service_workflow_guards import safe_official_references
from .service_workflow_schemas import WorkflowCreateRequest

EDITORS = {"owner", "admin", "editor"}
REVIEWERS = {"owner", "admin"}
ASSIGNEES = EDITORS
KB = re.compile(r"^THKB-([A-F0-9]{8})@v(\d+)$")
NO_PENDING_TEXT = re.compile(
    r"^(?:(?:无|暂无|没有|不存在)(?:任何|其他)?(?:待确认|未决)(?:事项|信息|内容|问题|项)?|"
    r"(?:待确认|未决)(?:事项|信息|内容|问题|项)?[：:]?(?:无|暂无|没有|不存在))[。.!！；;]?$"
)
DEFAULT_NODES = (
    ("intake", "接收建档", "核对企业身份、联系人、服务目标和当前项目材料。"),
    ("diagnosis", "需求诊断", "梳理企业需求、约束、优先级和仍需补充的信息。"),
    ("evidence", "资料与依据核验", "核对项目模块、人工审核状态、官方政策引用和组织知识引用。"),
    ("plan", "服务方案", "形成可执行方案、责任分工、时间节点和风险处理方式。"),
    ("delivery", "执行跟进", "记录服务动作、企业反馈、阻塞事项和阶段交付。"),
    ("closeout", "结项审核", "汇总结论、未决事项、后续责任和结项依据。"),
)


class ServiceCaseRecord(Base):
    __tablename__ = "service_cases"
    __table_args__ = (UniqueConstraint("organization_id", "case_number", name="uq_service_case_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    case_number: Mapped[str] = mapped_column(String(13))
    title: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    due_date: Mapped[date | None] = mapped_column(Date)
    lock_version: Mapped[int] = mapped_column(Integer, default=1)
    current_context_version: Mapped[int] = mapped_column(Integer, default=1)
    closure_summary: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ServiceCaseNodeRecord(Base):
    __tablename__ = "service_case_nodes"
    __table_args__ = (UniqueConstraint("case_id", "sequence", name="uq_service_case_node_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_cases.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    node_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    assignee_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    due_date: Mapped[date | None] = mapped_column(Date)
    output_summary: Mapped[str] = mapped_column(Text, default="")
    decision_note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ServiceCaseContextRecord(Base):
    __tablename__ = "service_case_contexts"
    __table_args__ = (UniqueConstraint("case_id", "context_version", name="uq_service_case_context_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_cases.id", ondelete="CASCADE"), index=True)
    context_version: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[str] = mapped_column(String(36))
    project_name: Mapped[str] = mapped_column(String(120))
    project_version: Mapped[int] = mapped_column(Integer)
    project_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    context_sha256: Mapped[str] = mapped_column(String(64))
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ServiceCaseEventRecord(Base):
    __tablename__ = "service_case_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_cases.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("service_case_nodes.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(40))
    before_status: Mapped[str] = mapped_column(String(30))
    after_status: Mapped[str] = mapped_column(String(30))
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    payload_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def now() -> datetime:
    return datetime.now(timezone.utc)


def digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def clean(value: str, limit: int = 500) -> str:
    return " ".join(re.sub(r"^[\s>*#\-+\d.\[\]xX]+", "", value or "").split())[:limit]


def pending(results: dict[str, str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for module, content in results.items():
        active = False
        for raw in (content or "").splitlines():
            line = raw.strip()
            if line.startswith("#"):
                active = "待确认" in line or "未决" in line
                continue
            is_item = active and line.startswith(("-", "*", "+", "1.", "2.", "3.", "["))
            if not (is_item or "待确认" in line):
                continue
            text = clean(line, 300)
            key = (module, text)
            if text and text not in {"待确认", "待确认信息"} and not NO_PENDING_TEXT.fullmatch(text) and key not in seen:
                seen.add(key)
                out.append({"module": module, "text": text})
            if len(out) >= 40:
                return out
    return out


class ServiceWorkflowStore:
    def __init__(self) -> None:
        """Attach to the already-migrated shared database without runtime DDL."""
        try:
            account = get_account_store()
            self.sessions = account.sessions
            self.engine = account.projects.engine
        except AccountStoreError as exc:
            raise AccountStoreError(
                503,
                "WORKFLOW_STORAGE_UNAVAILABLE",
                "企业服务流程存储暂时不可用。",
                retryable=True,
            ) from exc

    def case(self, session, organization_id: str, case_id: str, lock: bool = False) -> ServiceCaseRecord:
        query = select(ServiceCaseRecord).where(
            ServiceCaseRecord.id == case_id,
            ServiceCaseRecord.organization_id == organization_id,
        )
        record = session.scalar(query.with_for_update() if lock else query)
        if not record:
            raise AccountStoreError(404, "WORKFLOW_NOT_FOUND", "企业服务流程不存在或无权访问。")
        return record

    def node(self, session, case_id: str, node_id: str, lock: bool = False) -> ServiceCaseNodeRecord:
        query = select(ServiceCaseNodeRecord).where(
            ServiceCaseNodeRecord.id == node_id,
            ServiceCaseNodeRecord.case_id == case_id,
        )
        record = session.scalar(query.with_for_update() if lock else query)
        if not record:
            raise AccountStoreError(404, "WORKFLOW_NODE_NOT_FOUND", "流程节点不存在。")
        return record

    def project(self, session, organization_id: str, project_id: str) -> ProjectRecord:
        record = session.scalar(
            select(ProjectRecord)
            .join(OrganizationProjectRecord, OrganizationProjectRecord.project_id == ProjectRecord.id)
            .where(
                ProjectRecord.id == project_id,
                OrganizationProjectRecord.organization_id == organization_id,
            )
        )
        if not record:
            raise AccountStoreError(404, "WORKFLOW_PROJECT_NOT_FOUND", "项目不存在、未迁移到当前组织或无权访问。")
        return record

    def member(self, session, organization_id: str, user_id: str, assign: bool = False):
        row = session.execute(
            select(UserRecord, OrganizationMembershipRecord)
            .join(OrganizationMembershipRecord, OrganizationMembershipRecord.user_id == UserRecord.id)
            .where(
                OrganizationMembershipRecord.organization_id == organization_id,
                OrganizationMembershipRecord.user_id == user_id,
                OrganizationMembershipRecord.status == "active",
            )
        ).first()
        if not row or (assign and row[1].role not in ASSIGNEES):
            raise AccountStoreError(422, "WORKFLOW_ASSIGNEE_INVALID", "负责人不是当前组织可处理流程的有效成员。")
        return row

    def kbrefs(self, session, organization_id: str, citations: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        today = date.today()
        for citation in citations:
            match = KB.fullmatch(citation)
            if not match:
                raise AccountStoreError(422, "WORKFLOW_KNOWLEDGE_CITATION_INVALID", f"知识引用格式无效：{citation}")
            code = f"THKB-{match.group(1)}"
            version_number = int(match.group(2))
            article = session.scalar(
                select(KnowledgeArticleRecord).where(
                    KnowledgeArticleRecord.organization_id == organization_id,
                    KnowledgeArticleRecord.citation_code == code,
                    KnowledgeArticleRecord.lifecycle_status == "active",
                )
            )
            if not article or article.published_version != version_number:
                raise AccountStoreError(
                    422,
                    "WORKFLOW_KNOWLEDGE_CITATION_UNPUBLISHED",
                    f"知识引用不是当前组织的已发布版本：{citation}",
                )
            version = session.scalar(
                select(KnowledgeVersionRecord).where(
                    KnowledgeVersionRecord.article_id == article.id,
                    KnowledgeVersionRecord.version_number == version_number,
                )
            )
            if not version or (version.valid_from and version.valid_from > today) or (version.valid_until and version.valid_until < today):
                raise AccountStoreError(
                    422,
                    "WORKFLOW_KNOWLEDGE_CITATION_EXPIRED",
                    f"知识引用尚未生效或已经失效：{citation}",
                )
            source = dict(version.source or {})
            out.append(
                {
                    "citation_id": citation,
                    "title": version.title,
                    "category": version.category,
                    "source_type": str(source.get("source_type") or ""),
                    "issuer": str(source.get("issuer") or source.get("title") or ""),
                    "valid_until": version.valid_until.isoformat() if version.valid_until else None,
                    "content_sha256": version.content_sha256,
                }
            )
        return out

    def snapshot(self, session, organization_id: str, project: ProjectRecord, citations: list[str]):
        snapshot = dict(project.snapshot or {})
        results = dict(snapshot.get("results") or {})
        reviews = dict(snapshot.get("reviews") or {})
        modules: list[dict[str, str]] = []
        for module, content in results.items():
            if not content:
                continue
            review = dict(reviews.get(module) or {})
            modules.append(
                {
                    "module": module,
                    "result_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "excerpt": " ".join(content.split())[:500],
                    "review_status": str(review.get("status") or "unreviewed"),
                    "reviewed_by": str(review.get("reviewed_by_name") or ""),
                    "reviewed_at": str(review.get("reviewed_at") or ""),
                }
            )
        context = {
            "profile": dict(snapshot.get("profile") or {}),
            "identity": dict(snapshot.get("identity") or {}),
            "modules": modules[:12],
            "official_policy_references": safe_official_references(results.get("policy", "")),
            "knowledge_references": self.kbrefs(session, organization_id, citations),
            "pending_items": pending(results),
        }
        return context, digest(context)

    def add_context(self, session, case: ServiceCaseRecord, project: ProjectRecord, user_id: str, citations: list[str]):
        snapshot, context_hash = self.snapshot(session, case.organization_id, project, citations)
        current = session.scalar(
            select(ServiceCaseContextRecord).where(
                ServiceCaseContextRecord.case_id == case.id,
                ServiceCaseContextRecord.context_version == case.current_context_version,
            )
        )
        if current and current.context_sha256 == context_hash and current.project_version == project.lock_version:
            return current
        version = 1 if not current else case.current_context_version + 1
        record = ServiceCaseContextRecord(
            id=str(uuid4()),
            case_id=case.id,
            context_version=version,
            project_id=project.id,
            project_name=project.name,
            project_version=project.lock_version,
            project_updated_at=project.updated_at,
            snapshot=snapshot,
            context_sha256=context_hash,
            created_by_user_id=user_id,
        )
        session.add(record)
        case.current_context_version = version
        return record

    def event(self, session, case, node, action, before, after, user_id, name, role, note, payload) -> None:
        session.add(
            ServiceCaseEventRecord(
                id=str(uuid4()),
                case_id=case.id,
                node_id=node.id if node else None,
                action=action,
                before_status=before,
                after_status=after,
                actor_user_id=user_id,
                actor_name=name[:120],
                actor_role=role,
                note=(note or "")[:3000],
                payload_sha256=digest(payload),
            )
        )

    def check(self, case: ServiceCaseRecord, version: int) -> None:
        if case.lock_version != version:
            raise AccountStoreError(
                409,
                "WORKFLOW_VERSION_CONFLICT",
                f"流程已更新到 v{case.lock_version}，请重新载入后操作。",
            )

    def create(self, *, organization_id, actor_user_id, actor_name, actor_role, payload: WorkflowCreateRequest):
        if actor_role not in EDITORS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "当前角色不能创建企业服务流程。")
        try:
            with self.sessions.begin() as session:
                project = self.project(session, organization_id, payload.project_id)
                owner = payload.owner_user_id or actor_user_id
                self.member(session, organization_id, owner, True)
                case = ServiceCaseRecord(
                    id=str(uuid4()),
                    organization_id=organization_id,
                    project_id=project.id,
                    case_number=f"THSC-{uuid4().hex[:8].upper()}",
                    title=payload.title,
                    objective=payload.objective,
                    priority=payload.priority,
                    owner_user_id=owner,
                    due_date=payload.due_date,
                    created_by_user_id=actor_user_id,
                )
                session.add(case)
                session.flush()
                for sequence, (node_type, title, description) in enumerate(DEFAULT_NODES, 1):
                    session.add(
                        ServiceCaseNodeRecord(
                            id=str(uuid4()),
                            case_id=case.id,
                            sequence=sequence,
                            node_type=node_type,
                            title=title,
                            description=description,
                            assignee_user_id=owner,
                        )
                    )
                self.add_context(session, case, project, actor_user_id, payload.knowledge_citations)
                self.event(
                    session,
                    case,
                    None,
                    "create",
                    "none",
                    "draft",
                    actor_user_id,
                    actor_name,
                    actor_role,
                    "创建企业服务流程",
                    {"project_id": project.id, "knowledge_citations": payload.knowledge_citations},
                )
                session.flush()
            return self.get(organization_id=organization_id, case_id=case.id)
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "WORKFLOW_STORAGE_UNAVAILABLE", "企业服务流程创建失败。", retryable=True) from exc

    def list(self, *, organization_id, limit, offset, status):
        with self.sessions() as session:
            query = select(ServiceCaseRecord).where(ServiceCaseRecord.organization_id == organization_id)
            if status:
                query = query.where(ServiceCaseRecord.status == status)
            total = int(session.scalar(select(func.count()).select_from(query.subquery())) or 0)
            rows = session.scalars(
                query.order_by(ServiceCaseRecord.updated_at.desc()).limit(limit).offset(offset)
            ).all()
            return [self.case_dict(session, row, False) for row in rows], total

    def get(self, *, organization_id, case_id):
        with self.sessions() as session:
            return self.case_dict(session, self.case(session, organization_id, case_id), True)

    def case_dict(self, session, case, detail):
        owner = session.get(UserRecord, case.owner_user_id)
        nodes = session.scalars(
            select(ServiceCaseNodeRecord)
            .where(ServiceCaseNodeRecord.case_id == case.id)
            .order_by(ServiceCaseNodeRecord.sequence)
        ).all()
        data = {
            "id": case.id,
            "organization_id": case.organization_id,
            "project_id": case.project_id,
            "case_number": case.case_number,
            "title": case.title,
            "objective": case.objective,
            "priority": case.priority,
            "status": case.status,
            "owner_user_id": case.owner_user_id,
            "owner_name": owner.display_name if owner else "",
            "due_date": case.due_date,
            "lock_version": case.lock_version,
            "current_context_version": case.current_context_version,
            "completed_nodes": sum(node.status in {"completed", "skipped"} for node in nodes),
            "total_nodes": len(nodes),
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "completed_at": case.completed_at,
        }
        if not detail:
            return data
        context = session.scalar(
            select(ServiceCaseContextRecord).where(
                ServiceCaseContextRecord.case_id == case.id,
                ServiceCaseContextRecord.context_version == case.current_context_version,
            )
        )
        data.update(
            {
                "closure_summary": case.closure_summary,
                "nodes": [self.node_dict(session, node) for node in nodes],
                "context": self.context_dict(context),
            }
        )
        return data

    def node_dict(self, session, node):
        user = session.get(UserRecord, node.assignee_user_id) if node.assignee_user_id else None
        return {
            "id": node.id,
            "case_id": node.case_id,
            "sequence": node.sequence,
            "node_type": node.node_type,
            "title": node.title,
            "description": node.description,
            "status": node.status,
            "assignee_user_id": node.assignee_user_id,
            "assignee_name": user.display_name if user else "",
            "due_date": node.due_date,
            "output_summary": node.output_summary,
            "decision_note": node.decision_note,
            "started_at": node.started_at,
            "submitted_at": node.submitted_at,
            "completed_at": node.completed_at,
            "updated_at": node.updated_at,
        }

    def context_dict(self, context):
        snapshot = dict(context.snapshot or {})
        return {
            "context_version": context.context_version,
            "project_id": context.project_id,
            "project_name": context.project_name,
            "project_version": context.project_version,
            "project_updated_at": context.project_updated_at,
            "profile": snapshot.get("profile") or {},
            "identity": snapshot.get("identity") or {},
            "modules": snapshot.get("modules") or [],
            "official_policy_references": snapshot.get("official_policy_references") or [],
            "knowledge_references": snapshot.get("knowledge_references") or [],
            "pending_items": snapshot.get("pending_items") or [],
            "context_sha256": context.context_sha256,
            "created_by_user_id": context.created_by_user_id,
            "created_at": context.created_at,
        }

    def update(self, *, organization_id, case_id, actor_user_id, actor_name, actor_role, lock_version, title, objective, priority, owner_user_id, due_date, clear_due_date):
        if actor_role not in EDITORS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "当前角色不能修改企业服务流程。")
        with self.sessions.begin() as session:
            case = self.case(session, organization_id, case_id, True)
            self.check(case, lock_version)
            before = case.status
            if title is not None:
                case.title = title
            if objective is not None:
                case.objective = objective
            if priority is not None:
                case.priority = priority
            if owner_user_id is not None:
                if actor_role not in REVIEWERS and owner_user_id != actor_user_id:
                    raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "编辑者只能把自己设为流程负责人。")
                self.member(session, organization_id, owner_user_id, True)
                case.owner_user_id = owner_user_id
            if due_date is not None:
                case.due_date = due_date
            elif clear_due_date:
                case.due_date = None
            case.lock_version += 1
            case.updated_at = now()
            self.event(session, case, None, "update", before, case.status, actor_user_id, actor_name, actor_role, "更新流程信息", {"owner": owner_user_id, "due": due_date})
        return self.get(organization_id=organization_id, case_id=case_id)

    def refresh_context(self, *, organization_id, case_id, actor_user_id, actor_name, actor_role, lock_version, citations, note):
        if actor_role not in EDITORS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "当前角色不能刷新流程依据。")
        with self.sessions.begin() as session:
            case = self.case(session, organization_id, case_id, True)
            self.check(case, lock_version)
            project = self.project(session, organization_id, case.project_id)
            previous_version = case.current_context_version
            context = self.add_context(session, case, project, actor_user_id, citations)
            if context.context_version != previous_version:
                case.lock_version += 1
                case.updated_at = now()
                self.event(
                    session,
                    case,
                    None,
                    "refresh_context",
                    str(previous_version),
                    str(context.context_version),
                    actor_user_id,
                    actor_name,
                    actor_role,
                    note or "刷新办理依据",
                    {"project_version": project.lock_version, "knowledge_citations": citations},
                )
        return self.get(organization_id=organization_id, case_id=case_id)

    def update_node(self, *, organization_id, case_id, node_id, actor_user_id, actor_name, actor_role, lock_version, assignee_user_id, due_date, clear_due_date, description):
        if actor_role not in REVIEWERS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "只有管理员或所有者可以调整节点责任。")
        with self.sessions.begin() as session:
            case = self.case(session, organization_id, case_id, True)
            self.check(case, lock_version)
            node = self.node(session, case.id, node_id, True)
            before = node.status
            if assignee_user_id is not None:
                self.member(session, organization_id, assignee_user_id, True)
                node.assignee_user_id = assignee_user_id
            if due_date is not None:
                node.due_date = due_date
            elif clear_due_date:
                node.due_date = None
            if description is not None:
                node.description = description
            node.updated_at = now()
            case.lock_version += 1
            case.updated_at = now()
            self.event(session, case, node, "update_node", before, node.status, actor_user_id, actor_name, actor_role, "调整节点责任或期限", {"assignee": assignee_user_id, "due": due_date})
        return self.get(organization_id=organization_id, case_id=case_id)

    def node_action(self, *, organization_id, case_id, node_id, actor_user_id, actor_name, actor_role, action, lock_version, note, output_summary):
        if actor_role not in EDITORS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "当前角色不能处理流程节点。")
        with self.sessions.begin() as session:
            case = self.case(session, organization_id, case_id, True)
            self.check(case, lock_version)
            if case.status in {"completed", "cancelled"}:
                raise AccountStoreError(409, "WORKFLOW_ACTION_INVALID", "已结项或已取消的流程不能继续处理节点。")
            node = self.node(session, case.id, node_id, True)
            if actor_role not in REVIEWERS:
                if node.assignee_user_id and node.assignee_user_id != actor_user_id:
                    raise AccountStoreError(403, "WORKFLOW_NODE_ASSIGNEE_REQUIRED", "该节点已分配给其他处理人。")
                if not node.assignee_user_id:
                    node.assignee_user_id = actor_user_id
            before = node.status
            if action == "start" and node.status == "pending":
                node.status = "in_progress"
                node.started_at = node.started_at or now()
                case.status = "active" if case.status == "draft" else case.status
            elif action == "block" and node.status == "in_progress":
                node.status = "blocked"
                node.decision_note = note
            elif action == "resume" and node.status == "blocked":
                node.status = "in_progress"
                node.decision_note = note
            elif action == "submit" and node.status in {"in_progress", "blocked"}:
                node.status = "pending_review"
                node.output_summary = output_summary
                node.submitted_at = now()
                node.decision_note = note
            elif action == "approve" and node.status == "pending_review" and actor_role in REVIEWERS:
                node.status = "completed"
                node.completed_at = now()
                node.decision_note = note
            elif action == "return" and node.status == "pending_review" and actor_role in REVIEWERS:
                node.status = "in_progress"
                node.decision_note = note
            elif action == "skip" and node.status not in {"completed", "skipped"} and actor_role in REVIEWERS:
                node.status = "skipped"
                node.completed_at = now()
                node.decision_note = note
            elif action == "reopen" and node.status in {"completed", "skipped"} and actor_role in REVIEWERS:
                node.status = "in_progress"
                node.completed_at = None
                node.decision_note = note
                case.status = "active" if case.status == "pending_review" else case.status
            elif action in {"approve", "return", "skip", "reopen"} and actor_role not in REVIEWERS:
                raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "只有管理员或所有者可以审核节点。")
            else:
                raise AccountStoreError(409, "WORKFLOW_NODE_ACTION_INVALID", "当前节点状态不能执行该操作。")
            node.updated_at = now()
            case.lock_version += 1
            case.updated_at = now()
            self.event(session, case, node, action, before, node.status, actor_user_id, actor_name, actor_role, note, {"output_summary": output_summary, "assignee": node.assignee_user_id})
        return self.get(organization_id=organization_id, case_id=case_id)

    def case_action(self, *, organization_id, case_id, actor_user_id, actor_name, actor_role, action, lock_version, note, acknowledge_open_items):
        if actor_role not in EDITORS:
            raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "当前角色不能操作企业服务流程。")
        with self.sessions.begin() as session:
            case = self.case(session, organization_id, case_id, True)
            self.check(case, lock_version)
            before = case.status
            nodes = session.scalars(select(ServiceCaseNodeRecord).where(ServiceCaseNodeRecord.case_id == case.id)).all()
            context = session.scalar(
                select(ServiceCaseContextRecord).where(
                    ServiceCaseContextRecord.case_id == case.id,
                    ServiceCaseContextRecord.context_version == case.current_context_version,
                )
            )
            if action == "activate" and case.status == "draft":
                case.status = "active"
            elif action == "hold" and case.status in {"active", "pending_review"}:
                case.status = "on_hold"
            elif action == "resume" and case.status == "on_hold":
                case.status = "active"
            elif action == "submit_review" and case.status in {"active", "draft"}:
                if any(node.status not in {"completed", "skipped"} for node in nodes):
                    raise AccountStoreError(409, "WORKFLOW_NODES_INCOMPLETE", "仍有未完成节点，不能提交结项审核。")
                case.status = "pending_review"
            elif action == "complete" and case.status == "pending_review" and actor_role in REVIEWERS:
                project = self.project(session, organization_id, case.project_id)
                if not context or context.project_version != project.lock_version:
                    raise AccountStoreError(409, "WORKFLOW_CONTEXT_STALE", "项目材料已更新，请刷新流程依据后再结项。")
                if (context.snapshot or {}).get("pending_items") and not acknowledge_open_items:
                    raise AccountStoreError(409, "WORKFLOW_OPEN_ITEMS_UNACKNOWLEDGED", "仍有待确认事项，请确认已处理或转入后续跟踪。")
                case.status = "completed"
                case.completed_at = now()
                case.closure_summary = note
            elif action == "cancel" and case.status not in {"completed", "cancelled"} and actor_role in REVIEWERS:
                case.status = "cancelled"
                case.closure_summary = note
            elif action == "reopen" and case.status in {"completed", "cancelled"} and actor_role in REVIEWERS:
                case.status = "active"
                case.completed_at = None
            elif action in {"complete", "cancel", "reopen"} and actor_role not in REVIEWERS:
                raise AccountStoreError(403, "WORKFLOW_FORBIDDEN", "只有管理员或所有者可以执行该流程操作。")
            else:
                raise AccountStoreError(409, "WORKFLOW_ACTION_INVALID", "当前流程状态不能执行该操作。")
            case.lock_version += 1
            case.updated_at = now()
            self.event(session, case, None, action, before, case.status, actor_user_id, actor_name, actor_role, note, {"acknowledge_open_items": acknowledge_open_items})
        return self.get(organization_id=organization_id, case_id=case_id)

    def events(self, *, organization_id, case_id):
        with self.sessions() as session:
            self.case(session, organization_id, case_id)
            rows = session.scalars(
                select(ServiceCaseEventRecord)
                .where(ServiceCaseEventRecord.case_id == case_id)
                .order_by(ServiceCaseEventRecord.created_at.desc())
            ).all()
            return [
                {
                    "id": row.id,
                    "case_id": row.case_id,
                    "node_id": row.node_id,
                    "action": row.action,
                    "before_status": row.before_status,
                    "after_status": row.after_status,
                    "actor_user_id": row.actor_user_id,
                    "actor_name": row.actor_name,
                    "actor_role": row.actor_role,
                    "note": row.note,
                    "payload_sha256": row.payload_sha256,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


_STORE: ServiceWorkflowStore | None = None
_STORE_LOCK = threading.Lock()


def get_service_workflow_store() -> ServiceWorkflowStore:
    global _STORE
    account = get_account_store()
    with _STORE_LOCK:
        if _STORE is None or _STORE.engine is not account.projects.engine:
            _STORE = ServiceWorkflowStore()
        return _STORE


def reset_service_workflow_store_for_tests() -> None:
    global _STORE
    with _STORE_LOCK:
        _STORE = None

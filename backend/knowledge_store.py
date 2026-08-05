# -*- coding: utf-8 -*-
"""Versioned, reviewed, organization-scoped Tianhe enterprise-service knowledge base."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .auth_store import AccountStoreError, get_account_store
from .project_store import Base
from .knowledge_schemas import KnowledgeSearchRequest, KnowledgeVersionInput

EDITOR_ROLES = {"owner", "admin", "editor"}
REVIEWER_ROLES = {"owner", "admin"}
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}|[\u4e00-\u9fff]{2,}")
MAX_SEARCH_TEXT = 60000


class KnowledgeArticleRecord(Base):
    __tablename__ = "knowledge_articles"
    __table_args__ = (UniqueConstraint("organization_id", "citation_code", name="uq_knowledge_org_citation"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    citation_code: Mapped[str] = mapped_column(String(13), nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="draft", index=True, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class KnowledgeVersionRecord(Base):
    __tablename__ = "knowledge_versions"
    __table_args__ = (UniqueConstraint("article_id", "version_number", name="uq_knowledge_article_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_articles.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    applicability: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_note: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class KnowledgeReviewEventRecord(Base):
    __tablename__ = "knowledge_review_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_articles.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    before_status: Mapped[str] = mapped_column(String(30), nullable=False)
    after_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cell(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def _citation() -> str:
    return f"THKB-{uuid4().hex[:8].upper()}"


def _source_payload(payload: KnowledgeVersionInput) -> tuple[dict[str, Any], str]:
    source = payload.source.model_dump(mode="json")
    canonical = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return source, _sha(canonical)


def _content_hash(payload: KnowledgeVersionInput) -> str:
    canonical = json.dumps(
        {
            "title": payload.title,
            "category": payload.category,
            "summary": payload.summary,
            "content": payload.content,
            "tags": payload.tags,
            "applicability": payload.applicability.model_dump(mode="json"),
            "valid_from": payload.valid_from.isoformat() if payload.valid_from else None,
            "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha(canonical)


def _can_edit(role: str) -> bool:
    return role in EDITOR_ROLES


def _can_review(role: str) -> bool:
    return role in REVIEWER_ROLES


def _require_role(role: str, allowed: set[str], message: str) -> None:
    if role not in allowed:
        raise AccountStoreError(403, "KNOWLEDGE_FORBIDDEN", message)


def _version_dict(article: KnowledgeArticleRecord, version: KnowledgeVersionRecord) -> dict[str, Any]:
    source = dict(version.source or {})
    source["source_sha256"] = version.source_sha256
    return {
        "article_id": article.id,
        "citation_code": article.citation_code,
        "citation_id": f"{article.citation_code}@v{version.version_number}",
        "version_number": version.version_number,
        "title": version.title,
        "category": version.category,
        "summary": version.summary,
        "content": version.content,
        "tags": list(version.tags or []),
        "applicability": dict(version.applicability or {}),
        "source": source,
        "valid_from": version.valid_from,
        "valid_until": version.valid_until,
        "content_sha256": version.content_sha256,
        "change_note": version.change_note,
        "created_by_user_id": version.created_by_user_id,
        "created_at": version.created_at,
    }


def _summary_dict(article: KnowledgeArticleRecord, version: KnowledgeVersionRecord, *, role: str) -> dict[str, Any]:
    viewer_mode = role not in EDITOR_ROLES
    visible_version = article.published_version if viewer_mode else article.current_version
    return {
        "id": article.id,
        "organization_id": article.organization_id,
        "citation_code": article.citation_code,
        "title": version.title,
        "category": version.category,
        "review_status": "approved" if viewer_mode else article.review_status,
        "lifecycle_status": article.lifecycle_status,
        "current_version": int(visible_version or version.version_number),
        "published_version": article.published_version,
        "updated_at": article.updated_at,
        "can_edit": _can_edit(role),
        "can_review": _can_review(role),
    }


def _tokens(text: str) -> list[str]:
    raw = " ".join(str(text or "").split()).lower()
    tokens: list[str] = []
    for match in WORD_RE.findall(raw):
        if match not in tokens:
            tokens.append(match)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", match):
            for index in range(len(match) - 1):
                pair = match[index : index + 2]
                if pair not in tokens:
                    tokens.append(pair)
    return tokens[:80]


def _excerpt(text: str, tokens: list[str], limit: int = 360) -> str:
    normalized = " ".join((text or "").split())
    if not normalized:
        return ""
    lower = normalized.lower()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    start = max(0, (min(positions) if positions else 0) - 80)
    value = normalized[start : start + limit]
    if start:
        value = "…" + value
    if start + limit < len(normalized):
        value += "…"
    return value


def _scope_matches(profile_value: str, allowed_values: list[str]) -> bool:
    if not profile_value or not allowed_values:
        return True
    profile = " ".join(profile_value.split()).lower()
    for raw in allowed_values:
        candidate = " ".join(str(raw or "").split()).lower()
        if candidate and (candidate in profile or profile in candidate):
            return True
    return False


class KnowledgeStore:
    def __init__(self) -> None:
        try:
            account = get_account_store()
            self.sessions = account.sessions
            self.engine = account.projects.engine
            Base.metadata.create_all(self.engine)
        except (SQLAlchemyError, AccountStoreError) as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识库存储暂时不可用，请稍后重试。", retryable=True) from exc

    @staticmethod
    def _article(session, organization_id: str, article_id: str, *, lock: bool = False) -> KnowledgeArticleRecord:
        query = select(KnowledgeArticleRecord).where(KnowledgeArticleRecord.id == article_id, KnowledgeArticleRecord.organization_id == organization_id)
        if lock:
            query = query.with_for_update()
        record = session.scalar(query)
        if record is None:
            raise AccountStoreError(404, "KNOWLEDGE_NOT_FOUND", "知识条目不存在或无权访问。")
        return record

    @staticmethod
    def _version(session, article_id: str, version_number: int) -> KnowledgeVersionRecord:
        version = session.scalar(select(KnowledgeVersionRecord).where(KnowledgeVersionRecord.article_id == article_id, KnowledgeVersionRecord.version_number == version_number))
        if version is None:
            raise AccountStoreError(404, "KNOWLEDGE_VERSION_NOT_FOUND", "知识条目版本不存在。")
        return version

    @staticmethod
    def _new_version(article: KnowledgeArticleRecord, payload: KnowledgeVersionInput, *, version_number: int, actor_user_id: str) -> KnowledgeVersionRecord:
        source, source_sha256 = _source_payload(payload)
        return KnowledgeVersionRecord(
            id=str(uuid4()), article_id=article.id, version_number=version_number, title=payload.title,
            category=payload.category, summary=payload.summary, content=payload.content, tags=list(payload.tags),
            applicability=payload.applicability.model_dump(mode="json"), source=source,
            source_sha256=source_sha256, content_sha256=_content_hash(payload), valid_from=payload.valid_from,
            valid_until=payload.valid_until, change_note=payload.change_note, created_by_user_id=actor_user_id,
        )

    def create(self, *, organization_id: str, actor_user_id: str, actor_role: str, payload: KnowledgeVersionInput) -> dict[str, Any]:
        _require_role(actor_role, EDITOR_ROLES, "只有编辑者、管理员或所有者可以创建知识条目。")
        article = KnowledgeArticleRecord(
            id=str(uuid4()), organization_id=organization_id, citation_code=_citation(), review_status="draft",
            lifecycle_status="active", current_version=1, created_by_user_id=actor_user_id,
            updated_by_user_id=actor_user_id,
        )
        version = self._new_version(article, payload, version_number=1, actor_user_id=actor_user_id)
        try:
            with self.sessions.begin() as session:
                session.add(article)
                session.flush()
                session.add(version)
                session.flush()
            return self.get(organization_id=organization_id, article_id=article.id, actor_role=actor_role)
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识条目创建失败，请稍后重试。", retryable=True) from exc

    def list(self, *, organization_id: str, actor_role: str, limit: int, offset: int, include_archived: bool, review_status: str) -> tuple[list[dict[str, Any]], int]:
        try:
            with self.sessions() as session:
                query = select(KnowledgeArticleRecord).where(KnowledgeArticleRecord.organization_id == organization_id)
                if not include_archived:
                    query = query.where(KnowledgeArticleRecord.lifecycle_status == "active")
                if review_status:
                    query = query.where(KnowledgeArticleRecord.review_status == review_status)
                if actor_role not in EDITOR_ROLES:
                    query = query.where(KnowledgeArticleRecord.lifecycle_status == "active", KnowledgeArticleRecord.published_version.is_not(None))
                total = int(session.scalar(select(func.count()).select_from(query.subquery())) or 0)
                articles = session.scalars(query.order_by(KnowledgeArticleRecord.updated_at.desc()).limit(limit).offset(offset)).all()
                items: list[dict[str, Any]] = []
                for article in articles:
                    selected_version = article.current_version if actor_role in EDITOR_ROLES else article.published_version
                    if selected_version is None:
                        continue
                    version = self._version(session, article.id, selected_version)
                    items.append(_summary_dict(article, version, role=actor_role))
                return items, total
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识条目列表读取失败。", retryable=True) from exc

    def get(self, *, organization_id: str, article_id: str, actor_role: str, version_number: int | None = None) -> dict[str, Any]:
        try:
            with self.sessions() as session:
                article = self._article(session, organization_id, article_id)
                if actor_role not in EDITOR_ROLES and article.published_version is None:
                    raise AccountStoreError(404, "KNOWLEDGE_NOT_FOUND", "知识条目不存在或无权访问。")
                selected = version_number or (article.current_version if actor_role in EDITOR_ROLES else article.published_version)
                if selected is None:
                    raise AccountStoreError(404, "KNOWLEDGE_VERSION_NOT_FOUND", "知识条目尚无可读取版本。")
                if actor_role not in EDITOR_ROLES and selected != article.published_version:
                    raise AccountStoreError(403, "KNOWLEDGE_FORBIDDEN", "只读成员只能查看已发布版本。")
                version = self._version(session, article.id, selected)
                published = self._version(session, article.id, article.published_version) if article.published_version and article.published_version != selected else None
                return {**_summary_dict(article, version, role=actor_role), "version": _version_dict(article, version), "published": _version_dict(article, published) if published else None}
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识条目读取失败。", retryable=True) from exc

    def update(self, *, organization_id: str, article_id: str, actor_user_id: str, actor_role: str, expected_version: int, payload: KnowledgeVersionInput) -> dict[str, Any]:
        _require_role(actor_role, EDITOR_ROLES, "当前角色不能编辑知识条目。")
        try:
            with self.sessions.begin() as session:
                article = self._article(session, organization_id, article_id, lock=True)
                if article.current_version != expected_version:
                    raise AccountStoreError(409, "KNOWLEDGE_VERSION_CONFLICT", f"知识条目已更新到 v{article.current_version}，请重新载入后编辑。")
                current = self._version(session, article.id, article.current_version)
                new_hash = _content_hash(payload)
                _, source_hash = _source_payload(payload)
                if current.content_sha256 != new_hash or current.source_sha256 != source_hash:
                    next_version = article.current_version + 1
                    version = self._new_version(article, payload, version_number=next_version, actor_user_id=actor_user_id)
                    article.current_version = next_version
                    article.review_status = "draft"
                    article.updated_by_user_id = actor_user_id
                    article.updated_at = _now()
                    session.add(version)
                    session.flush()
            return self.get(organization_id=organization_id, article_id=article_id, actor_role=actor_role)
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识条目更新失败。", retryable=True) from exc

    def action(self, *, organization_id: str, article_id: str, actor_user_id: str, actor_name: str, actor_role: str, action: str, expected_version: int, note: str, version_number: int | None) -> dict[str, Any]:
        if action in {"submit", "restore"}:
            _require_role(actor_role, EDITOR_ROLES, "当前角色不能提交或恢复知识条目。")
        else:
            _require_role(actor_role, REVIEWER_ROLES, "只有管理员或所有者可以审核或归档知识条目。")
        try:
            with self.sessions.begin() as session:
                article = self._article(session, organization_id, article_id, lock=True)
                if article.current_version != expected_version:
                    raise AccountStoreError(409, "KNOWLEDGE_VERSION_CONFLICT", f"知识条目已更新到 v{article.current_version}，请重新载入后操作。")
                before = article.review_status if article.lifecycle_status == "active" else "archived"
                event_version = article.current_version
                if action == "submit":
                    if article.lifecycle_status != "active" or article.review_status not in {"draft", "rejected"}:
                        raise AccountStoreError(409, "KNOWLEDGE_ACTION_INVALID", "当前状态不能提交审核。")
                    article.review_status = "in_review"
                elif action == "approve":
                    if article.lifecycle_status != "active" or article.review_status != "in_review":
                        raise AccountStoreError(409, "KNOWLEDGE_ACTION_INVALID", "只有待审核版本可以批准。")
                    article.review_status = "approved"
                    article.published_version = article.current_version
                elif action == "reject":
                    if article.lifecycle_status != "active" or article.review_status != "in_review":
                        raise AccountStoreError(409, "KNOWLEDGE_ACTION_INVALID", "只有待审核版本可以退回。")
                    article.review_status = "rejected"
                elif action == "archive":
                    if article.lifecycle_status == "archived":
                        raise AccountStoreError(409, "KNOWLEDGE_ACTION_INVALID", "知识条目已经归档。")
                    article.lifecycle_status = "archived"
                elif action == "unarchive":
                    if article.lifecycle_status != "archived":
                        raise AccountStoreError(409, "KNOWLEDGE_ACTION_INVALID", "知识条目当前未归档。")
                    article.lifecycle_status = "active"
                elif action == "restore":
                    if version_number is None:
                        raise AccountStoreError(422, "KNOWLEDGE_VERSION_REQUIRED", "请指定需要恢复的版本。")
                    source = self._version(session, article.id, version_number)
                    next_version = article.current_version + 1
                    restored = KnowledgeVersionRecord(
                        id=str(uuid4()), article_id=article.id, version_number=next_version, title=source.title,
                        category=source.category, summary=source.summary, content=source.content, tags=list(source.tags or []),
                        applicability=dict(source.applicability or {}), source=dict(source.source or {}),
                        source_sha256=source.source_sha256, content_sha256=source.content_sha256,
                        valid_from=source.valid_from, valid_until=source.valid_until,
                        change_note=(note or f"恢复自 v{version_number}")[:500], created_by_user_id=actor_user_id,
                    )
                    session.add(restored)
                    article.current_version = next_version
                    article.review_status = "draft"
                    article.lifecycle_status = "active"
                    event_version = next_version
                else:
                    raise AccountStoreError(422, "KNOWLEDGE_ACTION_INVALID", "不支持的知识库操作。")
                article.updated_by_user_id = actor_user_id
                article.updated_at = _now()
                after = article.review_status if article.lifecycle_status == "active" else "archived"
                session.add(KnowledgeReviewEventRecord(
                    id=str(uuid4()), article_id=article.id, version_number=event_version, action=action,
                    before_status=before, after_status=after, actor_user_id=actor_user_id,
                    actor_name=actor_name[:120], actor_role=actor_role, note=(note or "")[:2000],
                ))
                session.flush()
            return self.get(organization_id=organization_id, article_id=article_id, actor_role=actor_role)
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识条目操作失败。", retryable=True) from exc

    def versions(self, *, organization_id: str, article_id: str, actor_role: str) -> list[dict[str, Any]]:
        try:
            with self.sessions() as session:
                article = self._article(session, organization_id, article_id)
                query = select(KnowledgeVersionRecord).where(KnowledgeVersionRecord.article_id == article.id)
                if actor_role not in EDITOR_ROLES:
                    if article.published_version is None:
                        return []
                    query = query.where(KnowledgeVersionRecord.version_number == article.published_version)
                rows = session.scalars(query.order_by(KnowledgeVersionRecord.version_number.desc())).all()
                return [_version_dict(article, row) for row in rows]
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识版本读取失败。", retryable=True) from exc

    def events(self, *, organization_id: str, article_id: str, actor_role: str) -> list[dict[str, Any]]:
        try:
            with self.sessions() as session:
                article = self._article(session, organization_id, article_id)
                if actor_role not in EDITOR_ROLES and article.published_version is None:
                    return []
                query = select(KnowledgeReviewEventRecord).where(KnowledgeReviewEventRecord.article_id == article.id)
                if actor_role not in EDITOR_ROLES:
                    query = query.where(KnowledgeReviewEventRecord.action == "approve", KnowledgeReviewEventRecord.version_number == article.published_version)
                rows = session.scalars(query.order_by(KnowledgeReviewEventRecord.created_at.desc())).all()
                return [{
                    "id": row.id, "article_id": row.article_id, "version_number": row.version_number,
                    "action": row.action, "before_status": row.before_status, "after_status": row.after_status,
                    "actor_user_id": row.actor_user_id, "actor_name": row.actor_name, "actor_role": row.actor_role,
                    "note": row.note, "created_at": row.created_at,
                } for row in rows]
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识审核记录读取失败。", retryable=True) from exc

    def search(self, *, organization_id: str, payload: KnowledgeSearchRequest) -> dict[str, Any]:
        today = date.today()
        profile = payload.profile.model_dump()
        query_text = " ".join(value for value in (payload.query, profile.get("industry", ""), profile.get("location", ""), profile.get("scale", ""), profile.get("stage", ""), profile.get("demands", "")) if value)
        tokens = _tokens(query_text)
        try:
            with self.sessions() as session:
                articles = session.scalars(select(KnowledgeArticleRecord).where(
                    KnowledgeArticleRecord.organization_id == organization_id,
                    KnowledgeArticleRecord.lifecycle_status == "active",
                    KnowledgeArticleRecord.published_version.is_not(None),
                )).all()
                ranked: list[tuple[float, KnowledgeArticleRecord, KnowledgeVersionRecord, list[str]]] = []
                for article in articles:
                    version = self._version(session, article.id, int(article.published_version or 0))
                    if payload.category and version.category != payload.category:
                        continue
                    warnings: list[str] = []
                    if version.valid_from and version.valid_from > today:
                        continue
                    if version.valid_until and version.valid_until < today:
                        continue
                    applicability = dict(version.applicability or {})
                    if not _scope_matches(profile.get("location", ""), list(applicability.get("regions") or [])):
                        continue
                    if not _scope_matches(profile.get("industry", ""), list(applicability.get("industries") or [])):
                        continue
                    if not _scope_matches(profile.get("scale", ""), list(applicability.get("entity_types") or [])):
                        continue
                    title, summary, content = version.title.lower(), version.summary.lower(), version.content[:MAX_SEARCH_TEXT].lower()
                    category = version.category.lower()
                    tags = " ".join(version.tags or []).lower()
                    app_text = " ".join(str(item) for values in applicability.values() for item in (values if isinstance(values, list) else [])).lower()
                    score = 0.0
                    for token in tokens:
                        if token in title: score += 8
                        if token in tags: score += 5
                        if token in category: score += 4
                        if token in summary: score += 3
                        if token in app_text: score += 4
                        if token in content: score += 1
                    if not tokens: score = 1.0
                    if profile.get("location") and not applicability.get("regions"):
                        warnings.append("该条目未限定适用区域，需要人工确认是否适用于当前主体。")
                    if profile.get("industry") and not applicability.get("industries"):
                        warnings.append("该条目未限定适用行业，需要人工确认行业适配性。")
                    if score > 0:
                        ranked.append((score, article, version, warnings))
                ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
                items: list[dict[str, Any]] = []
                for score, article, version, warnings in ranked[: payload.limit]:
                    source = dict(version.source or {})
                    source["source_sha256"] = version.source_sha256
                    items.append({
                        "article_id": article.id, "citation_id": f"{article.citation_code}@v{version.version_number}",
                        "title": version.title, "category": version.category, "summary": version.summary,
                        "excerpt": _excerpt(f"{version.summary} {version.content}", tokens), "tags": list(version.tags or []),
                        "applicability": dict(version.applicability or {}), "source": source,
                        "valid_from": version.valid_from, "valid_until": version.valid_until,
                        "score": round(score, 2), "warnings": warnings,
                    })
                return {"status": "ok" if items else "no_results", "query": payload.query.strip(), "generated_at": _now(), "items": items, "markdown_context": self._markdown_context(items)}
        except AccountStoreError:
            raise
        except SQLAlchemyError as exc:
            raise AccountStoreError(503, "KNOWLEDGE_STORAGE_UNAVAILABLE", "知识库检索失败。", retryable=True) from exc

    @staticmethod
    def _markdown_context(items: list[dict[str, Any]]) -> str:
        lines = ["## 天河企业服务知识库引用", "", "> 仅包含当前组织已批准且仍在有效期内的发布版本。知识库审核不等于政府官方认定；具体政策仍以官方原文为准。", ""]
        if not items:
            lines.append("- 未检索到可用的已发布知识条目。不得据此补写事实、资格、金额、期限或服务承诺。")
            return "\n".join(lines)
        lines.extend(["| 引用编号 | 标题 | 分类 | 来源类型 | 发布机构/维护方 | 有效期 |", "|---|---|---|---|---|---|"])
        for item in items:
            source = item["source"]
            valid = " 至 ".join(value.isoformat() if hasattr(value, "isoformat") else str(value) for value in (item.get("valid_from"), item.get("valid_until")) if value) or "未限定，需人工复核"
            lines.append(f"| {_cell(item['citation_id'])} | {_cell(item['title'])} | {_cell(item['category'])} | {_cell(source.get('source_type', ''))} | {_cell(source.get('issuer') or source.get('title', ''))} | {_cell(valid)} |")
        lines.extend(["", "### 可引用摘录", ""])
        for item in items:
            lines.append(f"- **[{_cell(item['citation_id'])}] {_cell(item['title'])}**：{_cell(item['excerpt'])}")
        lines.extend(["", "## 使用边界", "", "- 只有上述具体版本号可以引用；编辑中的草稿、待审核版本和已归档条目不得进入 AI 结论。", "- 内部指南、案例和模板必须标明来源类型，不得改写成官方政策、法定要求或已发生事实。", "- 适用区域、行业、主体类型、时间和服务承诺缺失时，必须列为待确认信息。"])
        return "\n".join(lines)


_KNOWLEDGE_STORE: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _KNOWLEDGE_STORE
    account = get_account_store()
    if _KNOWLEDGE_STORE is None or _KNOWLEDGE_STORE.sessions is not account.sessions:
        _KNOWLEDGE_STORE = KnowledgeStore()
    return _KNOWLEDGE_STORE


def reset_knowledge_store_for_tests() -> None:
    global _KNOWLEDGE_STORE
    _KNOWLEDGE_STORE = None

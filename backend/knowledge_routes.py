# -*- coding: utf-8 -*-
"""Organization-scoped knowledge-base APIs with versioning and review controls."""
from __future__ import annotations

import re

from fastapi import APIRouter, FastAPI, Query, Request

from .auth_routes import require_auth, require_csrf
from .auth_store import AccountStoreError, get_account_store
from .knowledge_schemas import (
    KnowledgeActionRequest,
    KnowledgeArticleResponse,
    KnowledgeArticleSummary,
    KnowledgeCreateRequest,
    KnowledgeListResponse,
    KnowledgeReviewEventListResponse,
    KnowledgeReviewEventResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeUpdateRequest,
    KnowledgeVersionListResponse,
    KnowledgeVersionResponse,
)
from .knowledge_store import get_knowledge_store

router = APIRouter(prefix="/api/knowledge", tags=["knowledge-base"])


def _scope_key(value: str) -> str:
    normalized = " ".join(str(value or "").split())
    normalized = re.sub(r"(自治县|新区|省|市|区|县)$", "", normalized)
    for prefix in ("广东省", "广州市", "广州"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    return normalized


def _normalized_search_payload(payload: KnowledgeSearchRequest) -> KnowledgeSearchRequest:
    profile = payload.profile.model_copy(
        update={
            "location": _scope_key(payload.profile.location),
            # 团队人数或经营规模不能可靠代表企业、个体工商户等主体类型。
            "scale": "",
        }
    )
    return payload.model_copy(update={"profile": profile})


def _context(request: Request, *, write: bool = False) -> tuple[str, str, str, str]:
    auth = require_auth(request)
    if write:
        require_csrf(request, auth)
    organization_id = request.headers.get("x-organization-id", "").strip()
    if not organization_id:
        raise AccountStoreError(
            400,
            "KNOWLEDGE_ORGANIZATION_REQUIRED",
            "请选择一个组织空间后再使用知识库。",
        )
    membership = get_account_store().membership(auth.user_id, organization_id)
    return organization_id, auth.user_id, auth.display_name, membership["role"]


@router.get("", response_model=KnowledgeListResponse)
def list_knowledge(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = False,
    review_status: str = Query(default="", max_length=30),
) -> KnowledgeListResponse:
    organization_id, _, _, role = _context(request)
    items, total = get_knowledge_store().list(
        organization_id=organization_id,
        actor_role=role,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        review_status=review_status.strip(),
    )
    return KnowledgeListResponse(
        items=[KnowledgeArticleSummary.model_validate(item) for item in items],
        total=total,
    )


@router.post("", response_model=KnowledgeArticleResponse, status_code=201)
def create_knowledge(request: Request, payload: KnowledgeCreateRequest) -> KnowledgeArticleResponse:
    organization_id, user_id, _, role = _context(request, write=True)
    record = get_knowledge_store().create(
        organization_id=organization_id,
        actor_user_id=user_id,
        actor_role=role,
        payload=payload,
    )
    return KnowledgeArticleResponse.model_validate(record)


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(request: Request, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    organization_id, _, _, _ = _context(request)
    return KnowledgeSearchResponse.model_validate(
        get_knowledge_store().search(
            organization_id=organization_id,
            payload=_normalized_search_payload(payload),
        )
    )


@router.get("/{article_id}", response_model=KnowledgeArticleResponse)
def get_knowledge(
    request: Request,
    article_id: str,
    version: int | None = Query(default=None, ge=1),
) -> KnowledgeArticleResponse:
    organization_id, _, _, role = _context(request)
    record = get_knowledge_store().get(
        organization_id=organization_id,
        article_id=article_id,
        actor_role=role,
        version_number=version,
    )
    return KnowledgeArticleResponse.model_validate(record)


@router.put("/{article_id}", response_model=KnowledgeArticleResponse)
def update_knowledge(
    request: Request,
    article_id: str,
    payload: KnowledgeUpdateRequest,
) -> KnowledgeArticleResponse:
    organization_id, user_id, _, role = _context(request, write=True)
    values = payload.model_dump(exclude={"expected_version"})
    record = get_knowledge_store().update(
        organization_id=organization_id,
        article_id=article_id,
        actor_user_id=user_id,
        actor_role=role,
        expected_version=payload.expected_version,
        payload=KnowledgeCreateRequest.model_validate(values),
    )
    return KnowledgeArticleResponse.model_validate(record)


@router.get("/{article_id}/versions", response_model=KnowledgeVersionListResponse)
def list_knowledge_versions(request: Request, article_id: str) -> KnowledgeVersionListResponse:
    organization_id, _, _, role = _context(request)
    items = get_knowledge_store().versions(
        organization_id=organization_id,
        article_id=article_id,
        actor_role=role,
    )
    return KnowledgeVersionListResponse(
        items=[KnowledgeVersionResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/{article_id}/events", response_model=KnowledgeReviewEventListResponse)
def list_knowledge_events(request: Request, article_id: str) -> KnowledgeReviewEventListResponse:
    organization_id, _, _, role = _context(request)
    items = get_knowledge_store().events(
        organization_id=organization_id,
        article_id=article_id,
        actor_role=role,
    )
    return KnowledgeReviewEventListResponse(
        items=[KnowledgeReviewEventResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/{article_id}/actions", response_model=KnowledgeArticleResponse)
def knowledge_action(
    request: Request,
    article_id: str,
    payload: KnowledgeActionRequest,
) -> KnowledgeArticleResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    record = get_knowledge_store().action(
        organization_id=organization_id,
        article_id=article_id,
        actor_user_id=user_id,
        actor_name=display_name,
        actor_role=role,
        action=payload.action,
        expected_version=payload.expected_version,
        note=payload.note,
        version_number=payload.version_number,
    )
    return KnowledgeArticleResponse.model_validate(record)


def register_knowledge_routes(app: FastAPI) -> None:
    app.include_router(router)

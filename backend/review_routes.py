# -*- coding: utf-8 -*-
"""Project human-review endpoints with anonymous and organization scopes."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .auth_routes import require_auth, require_csrf
from .auth_store import get_account_store
from .project_store import ProjectNotFound, ProjectStoreUnavailable, ProjectVersionConflict, hash_workspace_key
from .review_schemas import (
    ProjectReviewActionRequest,
    ProjectReviewActionResponse,
    ProjectReviewDetailResponse,
    ProjectReviewEventListResponse,
    ProjectReviewEventResponse,
    ProjectReviewListResponse,
    ProjectReviewSummary,
    ReviewModule,
)
from .review_store import ReviewWorkflowError, get_review_store

router = APIRouter(prefix="/api/projects", tags=["project-reviews"])


class ReviewAPIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, current_version: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.current_version = current_version


def _workspace_key(request: Request) -> str:
    value = request.headers.get("x-workspace-key", "").strip()
    try:
        hash_workspace_key(value)
    except ValueError as exc:
        raise ReviewAPIError(400, "WORKSPACE_KEY_REQUIRED", "缺少有效的浏览器工作区密钥，请刷新页面后重试。") from exc
    return value


def _scope(request: Request, permission: str, write: bool = False):
    organization_id = request.headers.get("x-organization-id", "").strip()
    store = get_account_store()
    if organization_id:
        auth = require_auth(request)
        if write:
            require_csrf(request, auth)
        return store.organization_scope(auth.user_id, organization_id, permission)
    return store.anonymous_scope(_workspace_key(request))


def _error(exc: Exception) -> ReviewAPIError:
    if isinstance(exc, ReviewWorkflowError):
        return ReviewAPIError(exc.status_code, exc.code, exc.message)
    if isinstance(exc, ProjectNotFound):
        return ReviewAPIError(404, "PROJECT_NOT_FOUND", "项目不存在或无权访问。")
    if isinstance(exc, ProjectVersionConflict):
        return ReviewAPIError(409, "PROJECT_VERSION_CONFLICT", "项目已在其他页面更新，请重新载入后再操作。", exc.current_version)
    return ReviewAPIError(503, "REVIEW_STORAGE_UNAVAILABLE", "人工审核存储暂时不可用，请稍后重试。")


_ERRORS = (ReviewWorkflowError, ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable)


@router.get("/{project_id}/reviews", response_model=ProjectReviewListResponse)
def list_reviews(request: Request, project_id: str) -> ProjectReviewListResponse:
    try:
        data = get_review_store().list_reviews(_scope(request, "project:read"), project_id)
    except _ERRORS as exc:
        raise _error(exc) from exc
    return ProjectReviewListResponse(
        items=[ProjectReviewSummary.model_validate(item) for item in data["items"]],
        total=data["total"],
        project_lock_version=data["project_lock_version"],
    )


@router.get("/{project_id}/reviews/{module}", response_model=ProjectReviewDetailResponse)
def get_review(request: Request, project_id: str, module: ReviewModule) -> ProjectReviewDetailResponse:
    try:
        data = get_review_store().get_review(_scope(request, "project:read"), project_id, module)
    except _ERRORS as exc:
        raise _error(exc) from exc
    return ProjectReviewDetailResponse.model_validate(data)


@router.get("/{project_id}/reviews/{module}/events", response_model=ProjectReviewEventListResponse)
def list_review_events(request: Request, project_id: str, module: ReviewModule) -> ProjectReviewEventListResponse:
    try:
        items, total = get_review_store().list_events(_scope(request, "project:read"), project_id, module)
    except _ERRORS as exc:
        raise _error(exc) from exc
    return ProjectReviewEventListResponse(
        items=[ProjectReviewEventResponse.model_validate(item) for item in items], total=total
    )


@router.post("/{project_id}/reviews/{module}/actions", response_model=ProjectReviewActionResponse)
def review_action(
    request: Request,
    project_id: str,
    module: ReviewModule,
    payload: ProjectReviewActionRequest,
) -> ProjectReviewActionResponse:
    try:
        data = get_review_store().act(
            _scope(request, "project:update", write=True),
            project_id,
            module,
            expected_lock_version=payload.lock_version,
            action=payload.action,
            content=payload.content,
            note=payload.note,
        )
    except _ERRORS as exc:
        raise _error(exc) from exc
    return ProjectReviewActionResponse.model_validate(data)


def register_review_routes(app: FastAPI) -> None:
    app.include_router(router)

    @app.exception_handler(ReviewAPIError)
    async def review_error_handler(request: Request, exc: ReviewAPIError) -> JSONResponse:  # noqa: ARG001
        payload: dict[str, object] = {
            "detail": exc.message,
            "code": exc.code,
            "retryable": exc.status_code >= 500,
        }
        if exc.current_version is not None:
            payload["current_version"] = exc.current_version
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

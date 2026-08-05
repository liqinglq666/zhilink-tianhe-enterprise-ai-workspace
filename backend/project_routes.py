# -*- coding: utf-8 -*-
"""Project APIs with anonymous-workspace compatibility and organization RBAC."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from .auth_routes import register_auth_routes, require_auth, require_csrf
from .auth_store import get_account_store
from .knowledge_routes import register_knowledge_routes
from .policy_official_routes import register_official_policy_routes
from .project_schemas import (
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectRestoreRequest,
    ProjectSummary,
    ProjectUpdateRequest,
    ProjectVersionListResponse,
    ProjectVersionResponse,
    ProjectVersionSummary,
)
from .project_store import (
    ProjectHistoryNotFound,
    ProjectNotFound,
    ProjectStoreUnavailable,
    ProjectVersionConflict,
    hash_workspace_key,
)
from .review_routes import register_review_routes
from .review_store import prepare_created_snapshot, prepare_updated_snapshot
from .structured_routes import register_structured_routes
from .service_workflow_routes import register_service_workflow_routes

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "frontend" / "assets"
UI_BUNDLE_VERSION = "2026-08-05-live-redesign-v1"
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectAPIError(Exception):
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
        raise ProjectAPIError(400, "WORKSPACE_KEY_REQUIRED", "缺少有效的浏览器工作区密钥，请刷新页面后重试。") from exc
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


def _store_error(exc: Exception) -> ProjectAPIError:
    if isinstance(exc, ProjectNotFound):
        return ProjectAPIError(404, "PROJECT_NOT_FOUND", "项目不存在或无权访问。")
    if isinstance(exc, ProjectHistoryNotFound):
        return ProjectAPIError(404, "PROJECT_HISTORY_NOT_FOUND", "项目版本不存在。")
    if isinstance(exc, ProjectVersionConflict):
        return ProjectAPIError(409, "PROJECT_VERSION_CONFLICT", "项目已在其他页面更新，请重新载入后再操作。", exc.current_version)
    return ProjectAPIError(503, "PROJECT_STORAGE_UNAVAILABLE", "项目存储暂时不可用，请稍后重试。")


def _deduplicate_workspace_bundle_routes(app: FastAPI, preferred_endpoint: Callable[..., object]) -> None:
    """Keep one authoritative /assets/app.js route after the app finishes registering routes.

    The legacy base bundle in backend.main used the same path and could silently serve an
    incomplete script set depending on route ordering. Startup runs after module import, so
    every duplicate is visible and can be removed deterministically.
    """

    retained = []
    preferred_kept = False
    for route in app.router.routes:
        if getattr(route, "path", None) != "/assets/app.js":
            retained.append(route)
            continue
        if getattr(route, "endpoint", None) is preferred_endpoint and not preferred_kept:
            retained.append(route)
            preferred_kept = True
    if not preferred_kept:
        raise RuntimeError("The authoritative workspace bundle route is missing.")
    app.router.routes[:] = retained


_STORE_EXCEPTIONS = (ProjectNotFound, ProjectHistoryNotFound, ProjectVersionConflict, ProjectStoreUnavailable)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = False,
) -> ProjectListResponse:
    try:
        items, total = get_account_store().list_projects(
            _scope(request, "project:read"), limit=limit, offset=offset, include_archived=include_archived
        )
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectListResponse(items=[ProjectSummary.model_validate(item) for item in items], total=total)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(request: Request, payload: ProjectCreateRequest) -> ProjectResponse:
    try:
        record = get_account_store().create_project(
            _scope(request, "project:create", write=True),
            name=payload.name,
            description=payload.description,
            snapshot=prepare_created_snapshot(payload.snapshot.model_dump(mode="json")),
            version_label=payload.version_label,
        )
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.get("/{project_id}/versions", response_model=ProjectVersionListResponse)
def list_project_versions(
    request: Request,
    project_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProjectVersionListResponse:
    try:
        items, total = get_account_store().list_history(
            _scope(request, "history:read"), project_id, limit=limit, offset=offset
        )
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectVersionListResponse(items=[ProjectVersionSummary.model_validate(item) for item in items], total=total)


@router.get("/{project_id}/versions/{version_number}", response_model=ProjectVersionResponse)
def get_project_version(request: Request, project_id: str, version_number: int) -> ProjectVersionResponse:
    try:
        record = get_account_store().get_history(_scope(request, "history:read"), project_id, version_number)
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectVersionResponse.model_validate(record)


@router.post("/{project_id}/versions/{version_number}/restore", response_model=ProjectResponse)
def restore_project_version(
    request: Request,
    project_id: str,
    version_number: int,
    payload: ProjectRestoreRequest,
) -> ProjectResponse:
    try:
        record = get_account_store().restore_history(
            _scope(request, "history:restore", write=True),
            project_id,
            version_number,
            expected_lock_version=payload.lock_version,
            version_label=payload.version_label,
        )
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(request: Request, project_id: str) -> ProjectResponse:
    try:
        record = get_account_store().get_project(_scope(request, "project:read"), project_id)
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(request: Request, project_id: str, payload: ProjectUpdateRequest) -> ProjectResponse:
    try:
        store = get_account_store()
        scope = _scope(request, "project:update", write=True)
        prepared_snapshot = None
        if payload.snapshot is not None:
            current = store.get_project(scope, project_id)
            prepared_snapshot = prepare_updated_snapshot(
                current.get("snapshot") or {}, payload.snapshot.model_dump(mode="json")
            )
        record = store.update_project(
            scope,
            project_id,
            expected_lock_version=payload.lock_version,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            snapshot=prepared_snapshot,
            version_label=payload.version_label,
        )
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
def delete_project(request: Request, project_id: str) -> ProjectDeleteResponse:
    try:
        get_account_store().delete_project(_scope(request, "project:delete", write=True), project_id)
    except _STORE_EXCEPTIONS as exc:
        raise _store_error(exc) from exc
    return ProjectDeleteResponse(id=project_id)


def register_project_routes(app: FastAPI) -> None:
    register_auth_routes(app)
    register_review_routes(app)
    register_structured_routes(app)
    register_official_policy_routes(app)
    register_knowledge_routes(app)
    register_service_workflow_routes(app)
    app.include_router(router)

    @app.get("/preview", include_in_schema=False)
    def ui_preview() -> FileResponse:
        return FileResponse(
            ASSETS_DIR / "ui-preview.html",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/assets/app.js", include_in_schema=False)
    def workspace_app_bundle() -> Response:
        scripts = [
            "app.js",
            "generation-controls.js",
            "account-access.js",
            "project-storage.js",
            "review-workflow.js",
            "structured-results.js",
            "policy-sources.js",
            "knowledge-base.js",
            "service-workflow.js",
            "product-simplification.js",
            "ui-redesign-live.js",
            "ui-redesign-live-fixes.js",
        ]
        content = "\n\n".join((ASSETS_DIR / filename).read_text(encoding="utf-8") for filename in scripts)
        return Response(
            content=f"{content}\n",
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "X-Zhilink-UI-Bundle": UI_BUNDLE_VERSION,
            },
        )

    def prefer_complete_workspace_bundle() -> None:
        _deduplicate_workspace_bundle_routes(app, workspace_app_bundle)

    app.router.on_startup.append(prefer_complete_workspace_bundle)

    @app.exception_handler(ProjectAPIError)
    async def project_api_error_handler(request: Request, exc: ProjectAPIError) -> JSONResponse:  # noqa: ARG001
        payload: dict[str, object] = {
            "detail": exc.message,
            "code": exc.code,
            "retryable": exc.status_code >= 500,
        }
        if exc.current_version is not None:
            payload["current_version"] = exc.current_version
        return JSONResponse(status_code=exc.status_code, content=payload)

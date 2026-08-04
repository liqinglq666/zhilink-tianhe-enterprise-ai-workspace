# -*- coding: utf-8 -*-
"""Project persistence API, scoped by an anonymous browser workspace key."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from .project_schemas import (
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdateRequest,
)
from .project_store import (
    ProjectNotFound,
    ProjectStoreUnavailable,
    ProjectVersionConflict,
    get_project_store,
    hash_workspace_key,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        current_version: int | None = None,
    ):
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
        raise ProjectAPIError(
            400,
            "WORKSPACE_KEY_REQUIRED",
            "缺少有效的浏览器工作区密钥，请刷新页面后重试。",
        ) from exc
    return value


def _store_error(exc: Exception) -> ProjectAPIError:
    if isinstance(exc, ProjectNotFound):
        return ProjectAPIError(404, "PROJECT_NOT_FOUND", "项目不存在或无权访问。")
    if isinstance(exc, ProjectVersionConflict):
        return ProjectAPIError(
            409,
            "PROJECT_VERSION_CONFLICT",
            "项目已在其他页面更新，请重新载入后再保存。",
            current_version=exc.current_version,
        )
    return ProjectAPIError(
        503,
        "PROJECT_STORAGE_UNAVAILABLE",
        "项目存储暂时不可用，请稍后重试。",
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = False,
) -> ProjectListResponse:
    try:
        items, total = get_project_store().list(
            _workspace_key(request),
            limit=limit,
            offset=offset,
            include_archived=include_archived,
        )
    except (ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable) as exc:
        raise _store_error(exc) from exc
    return ProjectListResponse(
        items=[ProjectSummary.model_validate(item) for item in items], total=total
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(request: Request, payload: ProjectCreateRequest) -> ProjectResponse:
    try:
        record = get_project_store().create(
            _workspace_key(request),
            name=payload.name,
            description=payload.description,
            snapshot=payload.snapshot.model_dump(mode="json"),
        )
    except (ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable) as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(request: Request, project_id: str) -> ProjectResponse:
    try:
        record = get_project_store().get(_workspace_key(request), project_id)
    except (ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable) as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    request: Request,
    project_id: str,
    payload: ProjectUpdateRequest,
) -> ProjectResponse:
    try:
        record = get_project_store().update(
            _workspace_key(request),
            project_id,
            expected_lock_version=payload.lock_version,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            snapshot=(payload.snapshot.model_dump(mode="json") if payload.snapshot else None),
        )
    except (ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable) as exc:
        raise _store_error(exc) from exc
    return ProjectResponse.model_validate(record)


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
def delete_project(request: Request, project_id: str) -> ProjectDeleteResponse:
    try:
        get_project_store().delete(_workspace_key(request), project_id)
    except (ProjectNotFound, ProjectVersionConflict, ProjectStoreUnavailable) as exc:
        raise _store_error(exc) from exc
    return ProjectDeleteResponse(id=project_id)


def register_project_routes(app: FastAPI) -> None:
    app.include_router(router)

    @app.exception_handler(ProjectAPIError)
    async def project_api_error_handler(  # noqa: ARG001
        request: Request, exc: ProjectAPIError
    ) -> JSONResponse:
        payload: dict[str, object] = {
            "detail": exc.message,
            "code": exc.code,
            "retryable": exc.status_code >= 500,
        }
        if exc.current_version is not None:
            payload["current_version"] = exc.current_version
        return JSONResponse(status_code=exc.status_code, content=payload)

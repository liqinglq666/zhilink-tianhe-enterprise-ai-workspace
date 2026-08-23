# -*- coding: utf-8 -*-
"""Organization-scoped enterprise-service workflow APIs."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, Query, Request

from .auth_routes import require_auth, require_csrf
from .auth_store import AccountStoreError, get_account_store
from .service_workflow_schemas import (
    WorkflowCaseActionRequest,
    WorkflowCaseListResponse,
    WorkflowCaseResponse,
    WorkflowCaseSummary,
    WorkflowContextRefreshRequest,
    WorkflowCreateRequest,
    WorkflowEventListResponse,
    WorkflowEventResponse,
    WorkflowNodeActionRequest,
    WorkflowNodeUpdateRequest,
    WorkflowUpdateRequest,
)
from . import service_workflow_store as workflow_store
from .service_workflow_guards import ensure_active_organization_project

router = APIRouter(prefix="/api/service-cases", tags=["enterprise-service-workflows"])


def _context(request: Request, *, write: bool = False) -> tuple[str, str, str, str]:
    auth = require_auth(request)
    if write:
        require_csrf(request, auth)
    organization_id = request.headers.get("x-organization-id", "").strip()
    if not organization_id:
        raise AccountStoreError(400, "WORKFLOW_ORGANIZATION_REQUIRED", "请选择组织空间后再使用企业服务流程。")
    membership = get_account_store().membership(auth.user_id, organization_id)
    return organization_id, auth.user_id, auth.display_name, membership["role"]


@router.get("", response_model=WorkflowCaseListResponse)
def list_cases(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="", max_length=30),
) -> WorkflowCaseListResponse:
    organization_id, _, _, _ = _context(request)
    items, total = workflow_store.get_service_workflow_store().list(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        status=status.strip(),
    )
    return WorkflowCaseListResponse(
        items=[WorkflowCaseSummary.model_validate(item) for item in items],
        total=total,
    )


@router.post("", response_model=WorkflowCaseResponse, status_code=201)
def create_case(request: Request, payload: WorkflowCreateRequest) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    ensure_active_organization_project(organization_id, payload.project_id)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().create(
            organization_id=organization_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            payload=payload,
        )
    )


@router.get("/{case_id}", response_model=WorkflowCaseResponse)
def get_case(request: Request, case_id: str) -> WorkflowCaseResponse:
    organization_id, _, _, _ = _context(request)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().get(organization_id=organization_id, case_id=case_id)
    )


@router.put("/{case_id}", response_model=WorkflowCaseResponse)
def update_case(request: Request, case_id: str, payload: WorkflowUpdateRequest) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().update(
            organization_id=organization_id,
            case_id=case_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            lock_version=payload.lock_version,
            title=payload.title,
            objective=payload.objective,
            priority=payload.priority,
            owner_user_id=payload.owner_user_id,
            due_date=payload.due_date,
            clear_due_date=payload.clear_due_date,
        )
    )


@router.post("/{case_id}/context/refresh", response_model=WorkflowCaseResponse)
def refresh_case_context(
    request: Request,
    case_id: str,
    payload: WorkflowContextRefreshRequest,
) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().refresh_context(
            organization_id=organization_id,
            case_id=case_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            lock_version=payload.lock_version,
            citations=payload.knowledge_citations,
            note=payload.note,
        )
    )


@router.post("/{case_id}/actions", response_model=WorkflowCaseResponse)
def case_action(request: Request, case_id: str, payload: WorkflowCaseActionRequest) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().case_action(
            organization_id=organization_id,
            case_id=case_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            action=payload.action,
            lock_version=payload.lock_version,
            note=payload.note,
            acknowledge_open_items=payload.acknowledge_open_items,
        )
    )


@router.put("/{case_id}/nodes/{node_id}", response_model=WorkflowCaseResponse)
def update_node(
    request: Request,
    case_id: str,
    node_id: str,
    payload: WorkflowNodeUpdateRequest,
) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().update_node(
            organization_id=organization_id,
            case_id=case_id,
            node_id=node_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            lock_version=payload.lock_version,
            assignee_user_id=payload.assignee_user_id,
            due_date=payload.due_date,
            clear_due_date=payload.clear_due_date,
            description=payload.description,
        )
    )


@router.post("/{case_id}/nodes/{node_id}/actions", response_model=WorkflowCaseResponse)
def node_action(
    request: Request,
    case_id: str,
    node_id: str,
    payload: WorkflowNodeActionRequest,
) -> WorkflowCaseResponse:
    organization_id, user_id, display_name, role = _context(request, write=True)
    return WorkflowCaseResponse.model_validate(
        workflow_store.get_service_workflow_store().node_action(
            organization_id=organization_id,
            case_id=case_id,
            node_id=node_id,
            actor_user_id=user_id,
            actor_name=display_name,
            actor_role=role,
            action=payload.action,
            lock_version=payload.lock_version,
            note=payload.note,
            output_summary=payload.output_summary,
        )
    )


@router.get("/{case_id}/events", response_model=WorkflowEventListResponse)
def list_events(request: Request, case_id: str) -> WorkflowEventListResponse:
    organization_id, _, _, _ = _context(request)
    items = workflow_store.get_service_workflow_store().events(organization_id=organization_id, case_id=case_id)
    return WorkflowEventListResponse(
        items=[WorkflowEventResponse.model_validate(item) for item in items],
        total=len(items),
    )


def register_service_workflow_routes(app: FastAPI) -> None:
    app.include_router(router)

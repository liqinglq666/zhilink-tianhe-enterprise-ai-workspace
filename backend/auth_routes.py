# -*- coding: utf-8 -*-
"""Same-origin account, organization, membership, CSRF, and session routes."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .auth_schemas import (
    ClaimWorkspaceProjectsResponse,
    DeleteResponse,
    LoginRequest,
    MemberCreateRequest,
    MemberListResponse,
    MemberResponse,
    MemberUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    RegisterRequest,
)
from .auth_store import (
    AccountStoreError,
    AuthSession,
    get_account_store,
)

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "zhilink_session").strip() or "zhilink_session"
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "zhilink_csrf").strip() or "zhilink_csrf"
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
try:
    SESSION_TTL_HOURS = max(1, min(int(os.getenv("SESSION_TTL_HOURS", "168")), 720))
except ValueError:
    SESSION_TTL_HOURS = 168
SESSION_MAX_AGE = SESSION_TTL_HOURS * 3600

router = APIRouter(prefix="/api/auth", tags=["auth"])
organizations_router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def optional_auth(request: Request) -> AuthSession | None:
    return get_account_store().get_session(request.cookies.get(SESSION_COOKIE_NAME))


def require_auth(request: Request) -> AuthSession:
    auth = optional_auth(request)
    if auth is None:
        raise AccountStoreError(401, "AUTH_REQUIRED", "请先登录后再执行此操作。")
    return auth


def require_csrf(request: Request, auth: AuthSession) -> None:
    get_account_store().verify_csrf(
        auth,
        request.headers.get("x-csrf-token", ""),
        request.cookies.get(CSRF_COOKIE_NAME, ""),
    )


def _session_payload(auth: AuthSession, csrf_token: str) -> dict[str, Any]:
    organizations = get_account_store().list_organizations(auth.user_id)
    return {
        "authenticated": True,
        "user": {
            "id": auth.user_id,
            "email": auth.email,
            "display_name": auth.display_name,
        },
        "organizations": organizations,
        "csrf_token": csrf_token,
        "expires_at": auth.expires_at.isoformat(),
    }


def _set_auth_cookies(response: JSONResponse, token: str, csrf_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=SESSION_MAX_AGE,
        httponly=False,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: JSONResponse) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=AUTH_COOKIE_SECURE, samesite="lax")


@router.post("/register")
def register(request: Request, payload: RegisterRequest) -> JSONResponse:
    auth, token, csrf = get_account_store().register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        organization_name=payload.organization_name,
        user_agent=request.headers.get("user-agent", ""),
    )
    response = JSONResponse(status_code=201, content=jsonable_encoder(_session_payload(auth, csrf)))
    _set_auth_cookies(response, token, csrf)
    return response


@router.post("/login")
def login(request: Request, payload: LoginRequest) -> JSONResponse:
    auth, token, csrf = get_account_store().login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent", ""),
    )
    response = JSONResponse(content=jsonable_encoder(_session_payload(auth, csrf)))
    _set_auth_cookies(response, token, csrf)
    return response


@router.get("/session")
def session_status(request: Request) -> JSONResponse:
    auth = optional_auth(request)
    if auth is None:
        response = JSONResponse(
            content={
                "authenticated": False,
                "user": None,
                "organizations": [],
                "csrf_token": "",
                "expires_at": None,
            }
        )
        _clear_auth_cookies(response)
        return response

    csrf = request.cookies.get(CSRF_COOKIE_NAME, "").strip()
    if not csrf:
        csrf = get_account_store().rotate_csrf(auth.id)
        auth = require_auth(request)
    else:
        try:
            get_account_store().verify_csrf(auth, csrf, csrf)
        except AccountStoreError:
            csrf = get_account_store().rotate_csrf(auth.id)
            auth = require_auth(request)

    response = JSONResponse(content=jsonable_encoder(_session_payload(auth, csrf)))
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf,
        max_age=SESSION_MAX_AGE,
        httponly=False,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/logout", response_model=DeleteResponse)
def logout(request: Request) -> JSONResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    get_account_store().logout(auth.id)
    response = JSONResponse(content={"ok": True})
    _clear_auth_cookies(response)
    return response


@organizations_router.get("", response_model=list[OrganizationResponse])
def list_organizations(request: Request) -> list[OrganizationResponse]:
    auth = require_auth(request)
    return [
        OrganizationResponse.model_validate(item)
        for item in get_account_store().list_organizations(auth.user_id)
    ]


@organizations_router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    request: Request, payload: OrganizationCreateRequest
) -> OrganizationResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    return OrganizationResponse.model_validate(
        get_account_store().create_organization(auth.user_id, payload.name)
    )


@organizations_router.get("/{organization_id}/members", response_model=MemberListResponse)
def list_members(request: Request, organization_id: str) -> MemberListResponse:
    auth = require_auth(request)
    items = get_account_store().list_members(auth.user_id, organization_id)
    return MemberListResponse(
        items=[MemberResponse.model_validate(item) for item in items], total=len(items)
    )


@organizations_router.post(
    "/{organization_id}/members", response_model=MemberResponse, status_code=201
)
def add_member(
    request: Request, organization_id: str, payload: MemberCreateRequest
) -> MemberResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    return MemberResponse.model_validate(
        get_account_store().add_member(
            auth.user_id, organization_id, payload.email, payload.role
        )
    )


@organizations_router.put(
    "/{organization_id}/members/{user_id}", response_model=MemberResponse
)
def update_member(
    request: Request,
    organization_id: str,
    user_id: str,
    payload: MemberUpdateRequest,
) -> MemberResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    return MemberResponse.model_validate(
        get_account_store().update_member_role(
            auth.user_id, organization_id, user_id, payload.role
        )
    )


@organizations_router.delete(
    "/{organization_id}/members/{user_id}", response_model=DeleteResponse
)
def remove_member(request: Request, organization_id: str, user_id: str) -> DeleteResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    get_account_store().remove_member(auth.user_id, organization_id, user_id)
    return DeleteResponse()


@organizations_router.post(
    "/{organization_id}/claim-workspace-projects",
    response_model=ClaimWorkspaceProjectsResponse,
)
def claim_workspace_projects(
    request: Request, organization_id: str
) -> ClaimWorkspaceProjectsResponse:
    auth = require_auth(request)
    require_csrf(request, auth)
    workspace_key = request.headers.get("x-workspace-key", "").strip()
    if not workspace_key:
        raise AccountStoreError(
            400,
            "WORKSPACE_KEY_REQUIRED",
            "缺少当前浏览器的匿名工作区密钥。",
        )
    claimed = get_account_store().claim_workspace_projects(
        auth.user_id, organization_id, workspace_key
    )
    return ClaimWorkspaceProjectsResponse(claimed=claimed)


def register_auth_routes(app: FastAPI) -> None:
    app.include_router(router)
    app.include_router(organizations_router)

    @app.exception_handler(AccountStoreError)
    async def account_store_error_handler(  # noqa: ARG001
        request: Request, exc: AccountStoreError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "code": exc.code,
                "retryable": exc.retryable,
            },
        )

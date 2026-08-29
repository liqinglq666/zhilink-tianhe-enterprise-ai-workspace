from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.project_routes import register_project_routes

PASSWORD = "correct horse battery staple"


def _register(client: TestClient, email: str, name: str, organization_name: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": name,
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(csrf: str, organization_id: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "X-Organization-Id": organization_id}


def test_editor_cannot_assign_another_member_as_case_owner_on_create() -> None:
    app = FastAPI()
    register_project_routes(app)
    owner_client = TestClient(app)
    editor_client = TestClient(app)

    owner = _register(owner_client, "workflow-owner@example.com", "Owner", "Workflow Org")
    editor = _register(editor_client, "workflow-editor@example.com", "Editor", "Editor Personal Org")
    organization_id = owner["organizations"][0]["id"]
    owner_user_id = owner["user"]["id"]
    editor_user_id = editor["user"]["id"]

    added = owner_client.post(
        f"/api/organizations/{organization_id}/members",
        headers=_headers(owner["csrf_token"], organization_id),
        json={"email": editor["user"]["email"], "role": "editor"},
    )
    assert added.status_code == 201, added.text

    project = owner_client.post(
        "/api/projects",
        headers=_headers(owner["csrf_token"], organization_id),
        json={"name": "RBAC Project", "snapshot": {}},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    forbidden = editor_client.post(
        "/api/service-cases",
        headers=_headers(editor["csrf_token"], organization_id),
        json={
            "project_id": project_id,
            "title": "Editor assigned case",
            "objective": "Verify workflow owner assignment permissions.",
            "owner_user_id": owner_user_id,
        },
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["code"] == "WORKFLOW_FORBIDDEN"

    allowed = editor_client.post(
        "/api/service-cases",
        headers=_headers(editor["csrf_token"], organization_id),
        json={
            "project_id": project_id,
            "title": "Editor self-owned case",
            "objective": "Verify editors can still create their own workflow cases.",
            "owner_user_id": editor_user_id,
        },
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["owner_user_id"] == editor_user_id

    empty_owner = editor_client.post(
        "/api/service-cases",
        headers=_headers(editor["csrf_token"], organization_id),
        json={
            "project_id": project_id,
            "title": "Editor default-owned case",
            "objective": "Preserve the existing empty owner value as default self-assignment.",
            "owner_user_id": "",
        },
    )
    assert empty_owner.status_code == 201, empty_owner.text
    assert empty_owner.json()["owner_user_id"] == editor_user_id

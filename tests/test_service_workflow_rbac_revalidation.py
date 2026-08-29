from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from backend.auth_store import AccountStoreError
from backend.project_routes import register_project_routes
from backend.service_workflow_schemas import WorkflowCreateRequest
from backend.service_workflow_store import get_service_workflow_store

PASSWORD = "correct horse battery staple"


def _app() -> FastAPI:
    app = FastAPI()
    register_project_routes(app)
    return app


def _register(client: TestClient, email: str, name: str, organization_name: str):
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
    data = response.json()
    return data["csrf_token"], data["organizations"][0], data["user"]


def _headers(csrf: str, organization_id: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "X-Organization-Id": organization_id}


def _project_snapshot() -> dict:
    return {
        "identity": {},
        "profile": {},
        "forms": {},
        "results": {},
        "meta": {},
        "reviews": {},
        "current_section": "meeting",
    }


def _expect_forbidden(call) -> None:
    with pytest.raises(AccountStoreError) as exc_info:
        call()
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "WORKFLOW_FORBIDDEN"


def test_workflow_writes_ignore_stale_actor_role_snapshots() -> None:
    app = _app()
    owner_client = TestClient(app)
    actor_client = TestClient(app)

    owner_csrf, organization, owner_user = _register(
        owner_client,
        "owner-workflow@example.com",
        "Owner",
        "Workflow Org",
    )
    _, _, actor_user = _register(
        actor_client,
        "actor-workflow@example.com",
        "Actor",
        "Actor Personal Org",
    )
    organization_id = organization["id"]

    added = owner_client.post(
        f"/api/organizations/{organization_id}/members",
        headers={"X-CSRF-Token": owner_csrf},
        json={"email": actor_user["email"], "role": "admin"},
    )
    assert added.status_code == 201, added.text

    project_response = owner_client.post(
        "/api/projects",
        headers=_headers(owner_csrf, organization_id),
        json={"name": "Workflow RBAC Project", "snapshot": _project_snapshot()},
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()

    case_response = owner_client.post(
        "/api/service-cases",
        headers=_headers(owner_csrf, organization_id),
        json={
            "project_id": project["id"],
            "title": "Workflow RBAC Case",
            "objective": "Verify transaction-time role checks",
            "priority": "normal",
            "owner_user_id": owner_user["id"],
            "due_date": None,
            "knowledge_citations": [],
        },
    )
    assert case_response.status_code == 201, case_response.text
    case = case_response.json()
    node = case["nodes"][0]

    demoted = owner_client.put(
        f"/api/organizations/{organization_id}/members/{actor_user['id']}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"role": "viewer"},
    )
    assert demoted.status_code == 200, demoted.text

    store = get_service_workflow_store()
    stale_role = "admin"

    _expect_forbidden(
        lambda: store.create(
            organization_id=organization_id,
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            payload=WorkflowCreateRequest.model_validate(
                {
                    "project_id": project["id"],
                    "title": "Stale create",
                    "objective": "Must not be created",
                    "priority": "normal",
                    "owner_user_id": owner_user["id"],
                    "due_date": None,
                    "knowledge_citations": [],
                }
            ),
        )
    )
    _expect_forbidden(
        lambda: store.update(
            organization_id=organization_id,
            case_id=case["id"],
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            lock_version=case["lock_version"],
            title="Stale update",
            objective=None,
            priority=None,
            owner_user_id=None,
            due_date=None,
            clear_due_date=False,
        )
    )
    _expect_forbidden(
        lambda: store.refresh_context(
            organization_id=organization_id,
            case_id=case["id"],
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            lock_version=case["lock_version"],
            citations=[],
            note="stale refresh",
        )
    )
    _expect_forbidden(
        lambda: store.update_node(
            organization_id=organization_id,
            case_id=case["id"],
            node_id=node["id"],
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            lock_version=case["lock_version"],
            assignee_user_id=None,
            due_date=None,
            clear_due_date=False,
            description="Stale node update",
        )
    )
    _expect_forbidden(
        lambda: store.node_action(
            organization_id=organization_id,
            case_id=case["id"],
            node_id=node["id"],
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            action="start",
            lock_version=case["lock_version"],
            note="",
            output_summary="",
        )
    )
    _expect_forbidden(
        lambda: store.case_action(
            organization_id=organization_id,
            case_id=case["id"],
            actor_user_id=actor_user["id"],
            actor_name=actor_user["display_name"],
            actor_role=stale_role,
            action="cancel",
            lock_version=case["lock_version"],
            note="stale cancel",
            acknowledge_open_items=False,
        )
    )

    unchanged = store.get(organization_id=organization_id, case_id=case["id"])
    assert unchanged["title"] == "Workflow RBAC Case"
    assert unchanged["status"] == "draft"
    assert unchanged["lock_version"] == case["lock_version"]

    promoted = owner_client.put(
        f"/api/organizations/{organization_id}/members/{actor_user['id']}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"role": "admin"},
    )
    assert promoted.status_code == 200, promoted.text

    activated = store.case_action(
        organization_id=organization_id,
        case_id=case["id"],
        actor_user_id=actor_user["id"],
        actor_name=actor_user["display_name"],
        actor_role="editor",
        action="activate",
        lock_version=case["lock_version"],
        note="activate with stale request role",
        acknowledge_open_items=False,
    )
    assert activated["status"] == "active"

    events = store.events(organization_id=organization_id, case_id=case["id"])
    assert events[0]["action"] == "activate"
    assert events[0]["actor_role"] == "admin"


def test_every_workflow_write_revalidates_inside_store_transaction() -> None:
    source = open("backend/service_workflow_store.py", encoding="utf-8").read()
    write_methods = ("create", "update", "refresh_context", "update_node", "node_action", "case_action")

    for index, method in enumerate(write_methods):
        start = source.index(f"    def {method}(")
        later = [source.find(f"    def {candidate}(", start + 1) for candidate in write_methods[index + 1 :]]
        later = [position for position in later if position >= 0]
        end = min(later) if later else source.index("    def events(", start)
        section = source[start:end]
        assert "with self.sessions.begin() as session:" in section
        assert "self._current_actor_role(" in section

    assert ".with_for_update()" in source[source.index("    def _current_actor_role(") : source.index("    def kbrefs(")]

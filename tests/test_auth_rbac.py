from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.auth_store import UserRecord, get_account_store, reset_account_store_for_tests
from backend.project_routes import register_project_routes
from backend.project_store import reset_project_store_for_tests

KEY = "workspace-" + ("x" * 40)


def make_app(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'rbac.db'}"
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return app


def register(client, email, name, org):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "display_name": name,
            "organization_name": org,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return data["csrf_token"], data["organizations"][0]


def org_headers(csrf, org_id):
    return {
        "X-CSRF-Token": csrf,
        "X-Organization-Id": org_id,
        "X-Workspace-Key": KEY,
    }


def snapshot(text="会议材料"):
    return {
        "identity": {},
        "profile": {},
        "forms": {"meetingInput": text},
        "results": {},
        "meta": {},
        "current_section": "meeting",
    }


def test_register_session_password_hash_and_csrf(tmp_path):
    client = TestClient(make_app(tmp_path))
    csrf, org = register(client, "Owner@Example.com", "负责人", "测试组织")
    assert org["role"] == "owner"
    assert client.cookies.get("zhilink_session")
    assert client.cookies.get("zhilink_csrf") == csrf

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True

    with get_account_store().sessions() as db:
        user = db.scalar(select(UserRecord).where(UserRecord.email == "owner@example.com"))
        assert user
        assert user.password_hash != "correct horse battery staple"
        assert user.password_hash.startswith("scrypt$")

    blocked = client.post("/api/organizations", json={"name": "无 CSRF"})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "CSRF_TOKEN_INVALID"

    created = client.post(
        "/api/organizations",
        headers={"X-CSRF-Token": csrf},
        json={"name": "第二组织"},
    )
    assert created.status_code == 201

    other = TestClient(client.app)
    invalid = other.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "wrong password"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_rbac_project_permissions_and_last_owner(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    member = TestClient(app)
    owner_csrf, org = register(owner, "owner@example.com", "Owner", "组织 A")
    member_csrf, _ = register(member, "member@example.com", "Member", "成员个人空间")

    added = owner.post(
        f"/api/organizations/{org['id']}/members",
        headers={"X-CSRF-Token": owner_csrf},
        json={"email": "member@example.com", "role": "viewer"},
    )
    assert added.status_code == 201

    created = owner.post(
        "/api/projects",
        headers=org_headers(owner_csrf, org["id"]),
        json={"name": "组织项目", "snapshot": snapshot()},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    read = member.get(
        "/api/projects",
        headers={"X-Organization-Id": org["id"], "X-Workspace-Key": KEY},
    )
    assert read.status_code == 200
    assert read.json()["total"] == 1

    forbidden = member.post(
        "/api/projects",
        headers=org_headers(member_csrf, org["id"]),
        json={"name": "不允许", "snapshot": snapshot()},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "RBAC_FORBIDDEN"

    viewer_history = member.get(
        f"/api/projects/{project_id}/versions",
        headers={"X-Organization-Id": org["id"], "X-Workspace-Key": KEY},
    )
    assert viewer_history.status_code == 200
    assert viewer_history.json()["total"] == 1

    denied_restore = member.post(
        f"/api/projects/{project_id}/versions/1/restore",
        headers=org_headers(member_csrf, org["id"]),
        json={"lock_version": 1},
    )
    assert denied_restore.status_code == 403

    promoted = owner.put(
        f"/api/organizations/{org['id']}/members/{added.json()['user_id']}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"role": "editor"},
    )
    assert promoted.status_code == 200

    updated = member.put(
        f"/api/projects/{project_id}",
        headers=org_headers(member_csrf, org["id"]),
        json={"lock_version": 1, "snapshot": snapshot("已编辑")},
    )
    assert updated.status_code == 200

    denied_delete = member.delete(
        f"/api/projects/{project_id}",
        headers=org_headers(member_csrf, org["id"]),
    )
    assert denied_delete.status_code == 403

    restored = member.post(
        f"/api/projects/{project_id}/versions/1/restore",
        headers=org_headers(member_csrf, org["id"]),
        json={"lock_version": 2},
    )
    assert restored.status_code == 200
    assert restored.json()["lock_version"] == 3

    promoted_admin = owner.put(
        f"/api/organizations/{org['id']}/members/{added.json()['user_id']}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"role": "admin"},
    )
    assert promoted_admin.status_code == 200

    deleted = member.delete(
        f"/api/projects/{project_id}",
        headers=org_headers(member_csrf, org["id"]),
    )
    assert deleted.status_code == 200

    owner_id = owner.get("/api/auth/session").json()["user"]["id"]
    last_owner = owner.put(
        f"/api/organizations/{org['id']}/members/{owner_id}",
        headers={"X-CSRF-Token": owner_csrf},
        json={"role": "admin"},
    )
    assert last_owner.status_code == 409
    assert last_owner.json()["code"] == "LAST_OWNER_REQUIRED"


def test_claim_anonymous_projects_removes_anonymous_access(tmp_path):
    client = TestClient(make_app(tmp_path))
    csrf, org = register(client, "owner@example.com", "Owner", "组织")

    anonymous = client.post(
        "/api/projects",
        headers={"X-Workspace-Key": KEY},
        json={"name": "匿名项目", "snapshot": snapshot()},
    )
    assert anonymous.status_code == 201
    project_id = anonymous.json()["id"]
    assert client.get("/api/projects", headers={"X-Workspace-Key": KEY}).json()["total"] == 1

    claimed = client.post(
        f"/api/organizations/{org['id']}/claim-workspace-projects",
        headers={"X-CSRF-Token": csrf, "X-Workspace-Key": KEY},
    )
    assert claimed.status_code == 200
    assert claimed.json()["claimed"] == 1

    assert client.get(
        f"/api/projects/{project_id}", headers={"X-Workspace-Key": KEY}
    ).status_code == 404

    org_list = client.get(
        "/api/projects",
        headers={"X-Workspace-Key": KEY, "X-Organization-Id": org["id"]},
    )
    assert org_list.status_code == 200
    assert org_list.json()["total"] == 1


def test_cross_organization_isolation_and_logout(tmp_path):
    app = make_app(tmp_path)
    first = TestClient(app)
    second = TestClient(app)
    csrf1, org1 = register(first, "first@example.com", "First", "组织一")
    csrf2, _ = register(second, "second@example.com", "Second", "组织二")

    first.post(
        "/api/projects",
        headers=org_headers(csrf1, org1["id"]),
        json={"name": "项目一", "snapshot": snapshot()},
    )

    denied = second.get(
        "/api/projects",
        headers={"X-Workspace-Key": KEY, "X-Organization-Id": org1["id"]},
    )
    assert denied.status_code == 404
    assert denied.json()["code"] == "ORGANIZATION_NOT_FOUND"

    missing_csrf = second.post("/api/auth/logout")
    assert missing_csrf.status_code == 403
    logged_out = second.post("/api/auth/logout", headers={"X-CSRF-Token": csrf2})
    assert logged_out.status_code == 200
    assert second.get("/api/auth/session").json()["authenticated"] is False


def test_frontend_exposes_account_and_organization_controls():
    source = open("frontend/assets/account-access.js", encoding="utf-8").read()
    assert "ACCOUNT_ACCESS_READY" in source
    assert "X-Organization-Id" in source
    assert "X-CSRF-Token" in source
    assert "claim-workspace-projects" in source

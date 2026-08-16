from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth_store import reset_account_store_for_tests
from backend.project_routes import register_project_routes
from backend.project_store import reset_project_store_for_tests
from backend.review_store import reset_review_store_for_tests

KEY = "workspace-" + ("r" * 40)


def make_app(tmp_path):  # noqa: ARG001
    # The autouse fixture already provides a migrated, isolated database.
    reset_review_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return app


def snapshot(content="AI 初稿"):
    return {
        "identity": {},
        "profile": {},
        "forms": {"meetingInput": "会议原文"},
        "results": {"meeting": content},
        "meta": {},
        "reviews": {},
        "current_section": "meeting",
    }


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
        "X-Workspace-Key": KEY,
        "X-Organization-Id": org_id,
        "X-CSRF-Token": csrf,
    }


def test_anonymous_edit_confirm_and_event_history(tmp_path):
    client = TestClient(make_app(tmp_path))
    headers = {"X-Workspace-Key": KEY}
    created = client.post(
        "/api/projects", headers=headers, json={"name": "匿名审核", "snapshot": snapshot()}
    ).json()
    reviews = client.get(f"/api/projects/{created['id']}/reviews", headers=headers)
    assert reviews.status_code == 200
    assert reviews.json()["items"][0]["status"] == "ai_draft"

    edited = client.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 1, "action": "save_edit", "content": "人工修改稿", "note": "补充负责人"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["project"]["lock_version"] == 2
    assert edited.json()["project"]["snapshot"]["results"]["meeting"] == "人工修改稿"
    assert edited.json()["review"]["status"] == "edited"

    confirmed = client.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 2, "action": "confirm", "note": "本地确认"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["review"]["status"] == "confirmed"

    events = client.get(f"/api/projects/{created['id']}/reviews/meeting/events", headers=headers)
    assert events.status_code == 200
    assert events.json()["total"] == 2
    assert events.json()["items"][0]["actor_role"] == "anonymous"


def test_editor_submits_and_owner_approves(tmp_path):
    app = make_app(tmp_path)
    owner, editor = TestClient(app), TestClient(app)
    owner_csrf, org = register(owner, "owner@example.com", "负责人", "审核组织")
    editor_csrf, _ = register(editor, "editor@example.com", "编辑者", "编辑者个人空间")
    added = owner.post(
        f"/api/organizations/{org['id']}/members",
        headers={"X-CSRF-Token": owner_csrf},
        json={"email": "editor@example.com", "role": "editor"},
    )
    assert added.status_code == 201
    created = owner.post(
        "/api/projects", headers=org_headers(owner_csrf, org["id"]), json={"name": "组织审核", "snapshot": snapshot()}
    ).json()

    submitted = editor.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=org_headers(editor_csrf, org["id"]),
        json={"lock_version": 1, "action": "submit_review", "content": "编辑后提交稿", "note": "请负责人审核"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["review"]["status"] == "pending_review"

    denied = editor.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=org_headers(editor_csrf, org["id"]),
        json={"lock_version": 2, "action": "approve"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "REVIEW_ACTION_FORBIDDEN"

    approved = owner.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=org_headers(owner_csrf, org["id"]),
        json={"lock_version": 2, "action": "approve", "note": "已核对原文"},
    )
    assert approved.status_code == 200
    assert approved.json()["review"]["status"] == "approved"
    assert approved.json()["project"]["lock_version"] == 3


def test_generic_save_cannot_spoof_approval_and_regeneration_resets_review(tmp_path):
    client = TestClient(make_app(tmp_path))
    headers = {"X-Workspace-Key": KEY}
    created = client.post(
        "/api/projects", headers=headers, json={"name": "防伪审核", "snapshot": snapshot()}
    ).json()
    spoofed = snapshot()
    spoofed["reviews"] = {
        "meeting": {
            "status": "approved",
            "source_content": "伪造",
            "source_hash": "a" * 64,
            "content_hash": "b" * 64,
            "note": "伪造审批",
            "revision": 99,
            "submitted_by_name": "伪造",
            "submitted_at": "2026-08-04T00:00:00Z",
            "reviewed_by_name": "伪造",
            "reviewed_at": "2026-08-04T00:00:00Z",
            "updated_by_name": "伪造",
            "updated_at": "2026-08-04T00:00:00Z",
        }
    }
    saved = client.put(
        f"/api/projects/{created['id']}",
        headers=headers,
        json={"lock_version": 1, "snapshot": spoofed, "version_label": "尝试伪造"},
    )
    assert saved.status_code == 200
    assert saved.json()["snapshot"]["reviews"]["meeting"]["status"] == "ai_draft"

    regenerated = snapshot("重新生成的 AI 内容")
    regenerated["reviews"] = spoofed["reviews"]
    updated = client.put(
        f"/api/projects/{created['id']}", headers=headers, json={"lock_version": 2, "snapshot": regenerated}
    )
    assert updated.status_code == 200
    review = updated.json()["snapshot"]["reviews"]["meeting"]
    assert review["status"] == "ai_draft"
    assert review["source_content"] == ""
    assert "需重新审核" in review["updated_by_name"]


def test_request_changes_requires_note_and_revert_restores_source(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    owner_csrf, org = register(owner, "owner@example.com", "负责人", "组织")
    headers = org_headers(owner_csrf, org["id"])
    created = owner.post(
        "/api/projects", headers=headers, json={"name": "退回流程", "snapshot": snapshot()}
    ).json()
    owner.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 1, "action": "submit_review", "content": "人工修改内容"},
    )
    missing_note = owner.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 2, "action": "request_changes"},
    )
    assert missing_note.status_code == 422
    returned = owner.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 2, "action": "request_changes", "note": "请补充时间节点"},
    )
    assert returned.status_code == 200
    assert returned.json()["review"]["status"] == "changes_requested"
    reverted = owner.post(
        f"/api/projects/{created['id']}/reviews/meeting/actions",
        headers=headers,
        json={"lock_version": 3, "action": "revert_ai", "note": "恢复原稿"},
    )
    assert reverted.status_code == 200
    assert reverted.json()["project"]["snapshot"]["results"]["meeting"] == "AI 初稿"
    assert reverted.json()["review"]["status"] == "ai_draft"


def test_frontend_bundle_exposes_review_controls(tmp_path):
    client = TestClient(make_app(tmp_path))
    bundle = client.get("/assets/app.js")
    assert bundle.status_code == 200
    assert "REVIEW_WORKFLOW_READY" in bundle.text
    assert "data-review-action" in bundle.text
    assert "组织已批准" in bundle.text

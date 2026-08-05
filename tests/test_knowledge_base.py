from __future__ import annotations

import os
from datetime import date, timedelta

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth_store import reset_account_store_for_tests
from backend.knowledge_store import reset_knowledge_store_for_tests
from backend.project_routes import register_project_routes
from backend.project_store import reset_project_store_for_tests

PASSWORD = "correct horse battery staple"


def make_app(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'knowledge.db'}"
    reset_knowledge_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return app


def register(client: TestClient, email: str, name: str, org_name: str):
    response = client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": name, "organization_name": org_name})
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload["csrf_token"], payload["organizations"][0]


def headers(csrf: str, organization_id: str):
    return {"X-CSRF-Token": csrf, "X-Organization-Id": organization_id}


def entry(title="企业数字化服务指南", valid_until=None, source_type="service_guide", source_url=""):
    return {
        "title": title,
        "category": "企业服务指南",
        "summary": "面向天河区小微企业的数字化需求诊断和服务流转说明。",
        "content": "服务人员先确认企业主体、行业和需求，再形成诊断记录并安排人工复核。",
        "tags": ["数字化", "小微企业"],
        "applicability": {"regions": ["天河区"], "industries": ["商贸"], "entity_types": ["小微企业"], "scenarios": ["数字化诊断"], "roles": ["企业服务专员"]},
        "source": {"source_type": source_type, "title": "组织维护的企业服务手册", "issuer": "天河企业服务团队", "url": source_url, "published_at": "2026-07-01", "reference_number": "TH-SERVICE-001", "excerpt": "服务人员先确认企业主体、行业和需求。"},
        "valid_from": "2026-07-01",
        "valid_until": valid_until,
        "change_note": "初始版本",
    }


def add_member(owner: TestClient, owner_csrf: str, organization_id: str, email: str, role: str):
    response = owner.post(f"/api/organizations/{organization_id}/members", headers={"X-CSRF-Token": owner_csrf}, json={"email": email, "role": role})
    assert response.status_code == 201, response.text


def test_draft_is_hidden_until_approved_and_search_uses_versioned_citation(tmp_path):
    app = make_app(tmp_path)
    owner, viewer = TestClient(app), TestClient(app)
    owner_csrf, org = register(owner, "owner@example.com", "Owner", "天河服务组织")
    register(viewer, "viewer@example.com", "Viewer", "Viewer Space")
    add_member(owner, owner_csrf, org["id"], "viewer@example.com", "viewer")

    created = owner.post("/api/knowledge", headers=headers(owner_csrf, org["id"]), json=entry())
    assert created.status_code == 201, created.text
    article = created.json()
    assert article["review_status"] == "draft"
    assert article["published_version"] is None
    assert article["citation_code"].startswith("THKB-")

    viewer_headers = {"X-Organization-Id": org["id"]}
    hidden = viewer.get("/api/knowledge", headers=viewer_headers)
    assert hidden.status_code == 200
    assert hidden.json()["items"] == []

    for action in ("submit", "approve"):
        response = owner.post(f"/api/knowledge/{article['id']}/actions", headers=headers(owner_csrf, org["id"]), json={"action": action, "expected_version": 1, "note": "内容已复核" if action == "approve" else "", "version_number": None})
        assert response.status_code == 200, response.text
    assert response.json()["published_version"] == 1

    search = viewer.post("/api/knowledge/search", headers=viewer_headers, json={"query": "数字化诊断", "profile": {"industry": "商贸", "location": "天河区", "scale": "小微企业", "stage": "", "demands": ""}, "category": "", "limit": 8})
    assert search.status_code == 200, search.text
    result = search.json()
    assert result["status"] == "ok"
    assert result["items"][0]["citation_id"].endswith("@v1")
    assert result["items"][0]["source"]["source_type"] == "service_guide"
    assert "只有上述具体版本号可以引用" in result["markdown_context"]


def test_new_draft_does_not_replace_previous_published_version(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    csrf, org = register(owner, "owner2@example.com", "Owner", "组织")
    created = owner.post("/api/knowledge", headers=headers(csrf, org["id"]), json=entry()).json()
    for action in ("submit", "approve"):
        response = owner.post(f"/api/knowledge/{created['id']}/actions", headers=headers(csrf, org["id"]), json={"action": action, "expected_version": 1, "note": "", "version_number": None})
        assert response.status_code == 200, response.text

    changed = entry(title="企业数字化服务指南（修订稿）")
    changed["expected_version"] = 1
    updated = owner.put(f"/api/knowledge/{created['id']}", headers=headers(csrf, org["id"]), json=changed)
    assert updated.status_code == 200, updated.text
    payload = updated.json()
    assert payload["current_version"] == 2
    assert payload["published_version"] == 1
    assert payload["review_status"] == "draft"
    assert payload["published"]["version_number"] == 1

    search = owner.post("/api/knowledge/search", headers={"X-Organization-Id": org["id"]}, json={"query": "数字化", "profile": {}, "category": "", "limit": 8})
    assert search.status_code == 200
    assert search.json()["items"][0]["citation_id"].endswith("@v1")
    assert "修订稿" not in search.json()["items"][0]["title"]


def test_editor_can_submit_but_cannot_approve_and_viewer_cannot_edit(tmp_path):
    app = make_app(tmp_path)
    owner, editor, viewer = TestClient(app), TestClient(app), TestClient(app)
    owner_csrf, org = register(owner, "owner3@example.com", "Owner", "组织")
    editor_csrf, _ = register(editor, "editor@example.com", "Editor", "Editor Space")
    viewer_csrf, _ = register(viewer, "viewer2@example.com", "Viewer", "Viewer Space")
    add_member(owner, owner_csrf, org["id"], "editor@example.com", "editor")
    add_member(owner, owner_csrf, org["id"], "viewer2@example.com", "viewer")

    created = editor.post("/api/knowledge", headers=headers(editor_csrf, org["id"]), json=entry())
    assert created.status_code == 201
    article_id = created.json()["id"]
    submit = editor.post(f"/api/knowledge/{article_id}/actions", headers=headers(editor_csrf, org["id"]), json={"action": "submit", "expected_version": 1, "note": "", "version_number": None})
    assert submit.status_code == 200
    forbidden = editor.post(f"/api/knowledge/{article_id}/actions", headers=headers(editor_csrf, org["id"]), json={"action": "approve", "expected_version": 1, "note": "", "version_number": None})
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "KNOWLEDGE_FORBIDDEN"

    viewer_update = entry(title="伪造修改")
    viewer_update["expected_version"] = 1
    blocked = viewer.put(f"/api/knowledge/{article_id}", headers=headers(viewer_csrf, org["id"]), json=viewer_update)
    assert blocked.status_code == 403


def test_official_source_requires_allowlisted_government_https_url(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    csrf, org = register(owner, "owner4@example.com", "Owner", "组织")
    invalid = entry(source_type="official", source_url="https://example.com/policy")
    response = owner.post("/api/knowledge", headers=headers(csrf, org["id"]), json=invalid)
    assert response.status_code == 422

    valid = entry(source_type="official", source_url="https://www.thnet.gov.cn/zwgk/policy.html")
    valid["source"]["issuer"] = "广州市天河区人民政府"
    accepted = owner.post("/api/knowledge", headers=headers(csrf, org["id"]), json=valid)
    assert accepted.status_code == 201, accepted.text


def test_expired_published_version_is_excluded_from_search(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    csrf, org = register(owner, "owner5@example.com", "Owner", "组织")
    expired = entry(valid_until=(date.today() - timedelta(days=1)).isoformat())
    created = owner.post("/api/knowledge", headers=headers(csrf, org["id"]), json=expired).json()
    for action in ("submit", "approve"):
        response = owner.post(f"/api/knowledge/{created['id']}/actions", headers=headers(csrf, org["id"]), json={"action": action, "expected_version": 1, "note": "", "version_number": None})
        assert response.status_code == 200
    search = owner.post("/api/knowledge/search", headers={"X-Organization-Id": org["id"]}, json={"query": "数字化", "profile": {}, "category": "", "limit": 8})
    assert search.status_code == 200
    assert search.json()["status"] == "no_results"


def test_restore_creates_new_draft_and_keeps_history_and_events(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    csrf, org = register(owner, "owner6@example.com", "Owner", "组织")
    created = owner.post("/api/knowledge", headers=headers(csrf, org["id"]), json=entry()).json()
    changed = entry(title="第二版")
    changed["expected_version"] = 1
    second = owner.put(f"/api/knowledge/{created['id']}", headers=headers(csrf, org["id"]), json=changed)
    assert second.status_code == 200
    restored = owner.post(f"/api/knowledge/{created['id']}/actions", headers=headers(csrf, org["id"]), json={"action": "restore", "expected_version": 2, "note": "恢复初始内容", "version_number": 1})
    assert restored.status_code == 200, restored.text
    assert restored.json()["current_version"] == 3
    assert restored.json()["version"]["title"] == "企业数字化服务指南"

    versions = owner.get(f"/api/knowledge/{created['id']}/versions", headers={"X-Organization-Id": org["id"]})
    assert [item["version_number"] for item in versions.json()["items"]] == [3, 2, 1]
    events = owner.get(f"/api/knowledge/{created['id']}/events", headers={"X-Organization-Id": org["id"]})
    assert events.json()["items"][0]["action"] == "restore"


def test_organization_isolation_and_missing_org_header(tmp_path):
    app = make_app(tmp_path)
    first, second = TestClient(app), TestClient(app)
    first_csrf, first_org = register(first, "a@example.com", "A", "A Org")
    _, second_org = register(second, "b@example.com", "B", "B Org")
    created = first.post("/api/knowledge", headers=headers(first_csrf, first_org["id"]), json=entry())
    assert created.status_code == 201

    missing = first.get("/api/knowledge")
    assert missing.status_code == 400
    assert missing.json()["code"] == "KNOWLEDGE_ORGANIZATION_REQUIRED"
    isolated = second.get("/api/knowledge", headers={"X-Organization-Id": second_org["id"]})
    assert isolated.status_code == 200
    assert isolated.json()["items"] == []
    forbidden = second.get(f"/api/knowledge/{created.json()['id']}", headers={"X-Organization-Id": second_org["id"]})
    assert forbidden.status_code == 404

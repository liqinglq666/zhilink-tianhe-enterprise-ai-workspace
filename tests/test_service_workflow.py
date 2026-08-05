from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth_store import reset_account_store_for_tests
from backend.knowledge_store import reset_knowledge_store_for_tests
from backend.project_routes import register_project_routes
from backend.project_store import reset_project_store_for_tests
from backend.review_store import reset_review_store_for_tests
from backend.service_workflow_store import reset_service_workflow_store_for_tests

PASSWORD = "correct horse battery staple"


def make_app(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'workflow.db'}"
    reset_service_workflow_store_for_tests()
    reset_knowledge_store_for_tests()
    reset_review_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return app


def register(client: TestClient, email: str, name: str, org_name: str):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": name,
            "organization_name": org_name,
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload["csrf_token"], payload["organizations"][0]


def org_headers(csrf: str, organization_id: str):
    return {"X-CSRF-Token": csrf, "X-Organization-Id": organization_id}


def project_snapshot():
    return {
        "identity": {"role": "企业服务专员"},
        "profile": {
            "name": "示例企业",
            "industry": "商贸服务",
            "location": "天河区",
            "scale": "20 人团队",
            "stage": "成长期",
            "contact_role": "负责人",
            "demands": "数字化诊断和政策材料准备",
        },
        "forms": {},
        "results": {
            "meeting": "## 待确认信息\n- 企业联系人待确认。",
            "policy": (
                "## 官方政策来源与原文引用\n"
                "| 引用编号 | 政策文件 | 发布机关 | 文号 | 日期与状态 | 官方原文 |\n"
                "|---|---|---|---|---|---|\n"
                "| POL-001 | 天河区企业服务措施 | 天河区人民政府 | 天府规〔2026〕1号 | 状态 active | "
                "[打开官方原文](https://www.thnet.gov.cn/policy/1.html) |\n\n"
                "## 待确认信息\n- 申报窗口待确认。"
            ),
        },
        "meta": {},
        "reviews": {},
        "current_section": "policy",
    }


def create_project(client: TestClient, csrf: str, org_id: str):
    response = client.post(
        "/api/projects",
        headers=org_headers(csrf, org_id),
        json={"name": "企业服务项目", "snapshot": project_snapshot()},
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish_knowledge(client: TestClient, csrf: str, org_id: str):
    entry = {
        "title": "数字化服务指南",
        "category": "服务指南",
        "summary": "企业数字化需求诊断和服务流转说明。",
        "content": "服务人员先确认企业主体、行业和需求，再形成诊断记录。",
        "tags": ["数字化", "企业服务"],
        "applicability": {
            "regions": ["天河区"],
            "industries": ["商贸服务"],
            "entity_types": [],
            "scenarios": ["数字化诊断"],
            "roles": ["企业服务专员"],
        },
        "source": {
            "source_type": "service_guide",
            "title": "企业服务手册",
            "issuer": "天河企业服务团队",
            "url": "",
            "published_at": "2026-07-01",
            "reference_number": "TH-SERVICE-001",
            "excerpt": "服务人员先确认企业主体、行业和需求。",
        },
        "valid_from": "2026-07-01",
        "valid_until": None,
        "change_note": "初始发布",
    }
    created = client.post("/api/knowledge", headers=org_headers(csrf, org_id), json=entry)
    assert created.status_code == 201, created.text
    article = created.json()
    for action in ("submit", "approve"):
        response = client.post(
            f"/api/knowledge/{article['id']}/actions",
            headers=org_headers(csrf, org_id),
            json={
                "action": action,
                "expected_version": 1,
                "note": "内容已人工复核" if action == "approve" else "",
                "version_number": None,
            },
        )
        assert response.status_code == 200, response.text
    return f"{article['citation_code']}@v1"


def create_case(client: TestClient, csrf: str, org_id: str, project_id: str, citation: str, owner_user_id=None):
    response = client.post(
        "/api/service-cases",
        headers=org_headers(csrf, org_id),
        json={
            "project_id": project_id,
            "title": "数字化企业服务跟进",
            "objective": "完成需求诊断、依据核验、服务交付和结项审核。",
            "priority": "high",
            "owner_user_id": owner_user_id,
            "due_date": None,
            "knowledge_citations": [citation],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_case_creation_captures_project_policy_knowledge_and_pending_items(tmp_path):
    client = TestClient(make_app(tmp_path))
    csrf, org = register(client, "owner@example.com", "Owner", "天河服务组织")
    project = create_project(client, csrf, org["id"])
    citation = publish_knowledge(client, csrf, org["id"])
    case = create_case(client, csrf, org["id"], project["id"], citation)

    assert case["status"] == "draft"
    assert case["total_nodes"] == 6
    assert case["context"]["project_version"] == project["lock_version"]
    assert case["context"]["official_policy_references"][0]["citation_id"] == "POL-001"
    assert case["context"]["official_policy_references"][0]["official_url"].endswith("thnet.gov.cn/policy/1.html")
    assert case["context"]["knowledge_references"][0]["citation_id"] == citation
    assert {item["module"] for item in case["context"]["pending_items"]} == {"meeting", "policy"}


def test_editor_can_submit_assigned_node_but_only_owner_can_approve(tmp_path):
    app = make_app(tmp_path)
    owner = TestClient(app)
    editor = TestClient(app)
    owner_csrf, org = register(owner, "owner2@example.com", "Owner", "组织")
    editor_csrf, _ = register(editor, "editor@example.com", "Editor", "Editor Space")
    added = owner.post(
        f"/api/organizations/{org['id']}/members",
        headers={"X-CSRF-Token": owner_csrf},
        json={"email": "editor@example.com", "role": "editor"},
    )
    assert added.status_code == 201, added.text
    project = create_project(owner, owner_csrf, org["id"])
    citation = publish_knowledge(owner, owner_csrf, org["id"])
    editor_id = editor.get("/api/auth/session").json()["user"]["id"]
    case = create_case(owner, owner_csrf, org["id"], project["id"], citation, editor_id)
    node = case["nodes"][0]

    started = editor.post(
        f"/api/service-cases/{case['id']}/nodes/{node['id']}/actions",
        headers=org_headers(editor_csrf, org["id"]),
        json={"action": "start", "lock_version": case["lock_version"], "note": "", "output_summary": ""},
    )
    assert started.status_code == 200, started.text
    case = started.json()
    submitted = editor.post(
        f"/api/service-cases/{case['id']}/nodes/{node['id']}/actions",
        headers=org_headers(editor_csrf, org["id"]),
        json={
            "action": "submit",
            "lock_version": case["lock_version"],
            "note": "",
            "output_summary": "企业材料和联系人已核对。",
        },
    )
    assert submitted.status_code == 200, submitted.text
    case = submitted.json()

    forbidden = editor.post(
        f"/api/service-cases/{case['id']}/nodes/{node['id']}/actions",
        headers=org_headers(editor_csrf, org["id"]),
        json={"action": "approve", "lock_version": case["lock_version"], "note": "", "output_summary": ""},
    )
    assert forbidden.status_code == 403

    approved = owner.post(
        f"/api/service-cases/{case['id']}/nodes/{node['id']}/actions",
        headers=org_headers(owner_csrf, org["id"]),
        json={"action": "approve", "lock_version": case["lock_version"], "note": "通过", "output_summary": ""},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["nodes"][0]["status"] == "completed"


def test_unpublished_knowledge_reference_is_rejected(tmp_path):
    client = TestClient(make_app(tmp_path))
    csrf, org = register(client, "owner3@example.com", "Owner", "组织")
    project = create_project(client, csrf, org["id"])
    response = client.post(
        "/api/service-cases",
        headers=org_headers(csrf, org["id"]),
        json={
            "project_id": project["id"],
            "title": "测试流程",
            "objective": "验证引用",
            "priority": "normal",
            "owner_user_id": None,
            "due_date": None,
            "knowledge_citations": ["THKB-ABCDEF12@v1"],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] in {
        "WORKFLOW_KNOWLEDGE_CITATION_UNPUBLISHED",
        "WORKFLOW_KNOWLEDGE_CITATION_INVALID",
    }


def test_node_completion_gate_and_event_log(tmp_path):
    client = TestClient(make_app(tmp_path))
    csrf, org = register(client, "owner4@example.com", "Owner", "组织")
    project = create_project(client, csrf, org["id"])
    citation = publish_knowledge(client, csrf, org["id"])
    case = create_case(client, csrf, org["id"], project["id"], citation)

    blocked = client.post(
        f"/api/service-cases/{case['id']}/actions",
        headers=org_headers(csrf, org["id"]),
        json={
            "action": "submit_review",
            "lock_version": case["lock_version"],
            "note": "",
            "acknowledge_open_items": False,
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "WORKFLOW_NODES_INCOMPLETE"

    node = case["nodes"][0]
    started = client.post(
        f"/api/service-cases/{case['id']}/nodes/{node['id']}/actions",
        headers=org_headers(csrf, org["id"]),
        json={"action": "start", "lock_version": case["lock_version"], "note": "", "output_summary": ""},
    ).json()
    events = client.get(
        f"/api/service-cases/{case['id']}/events",
        headers={"X-Organization-Id": org["id"]},
    )
    assert events.status_code == 200
    assert events.json()["items"][0]["action"] == "start"
    assert len(events.json()["items"][0]["payload_sha256"]) == 64
    assert started["lock_version"] == case["lock_version"] + 1


def test_other_organization_cannot_read_case(tmp_path):
    app = make_app(tmp_path)
    first = TestClient(app)
    second = TestClient(app)
    first_csrf, first_org = register(first, "a@example.com", "A", "A Org")
    _, second_org = register(second, "b@example.com", "B", "B Org")
    project = create_project(first, first_csrf, first_org["id"])
    citation = publish_knowledge(first, first_csrf, first_org["id"])
    case = create_case(first, first_csrf, first_org["id"], project["id"], citation)

    response = second.get(
        f"/api/service-cases/{case['id']}",
        headers={"X-Organization-Id": second_org["id"]},
    )
    assert response.status_code == 404

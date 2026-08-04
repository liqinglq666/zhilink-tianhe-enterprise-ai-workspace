from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.project_routes import register_project_routes
from backend.project_store import reset_project_store_for_tests

KEY = "workspace-" + ("x" * 40)
OTHER_KEY = "workspace-" + ("y" * 40)


def make_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return TestClient(app)


def snapshot():
    return {
        "identity": {"org": "测试单位", "role": "企业用户"},
        "profile": {"name": "测试企业", "demands": "合同审阅"},
        "forms": {"meetingInput": "会议决定继续推进。"},
        "results": {"meeting": "## 一句话结论\n继续推进。"},
        "meta": {
            "meeting": {
                "mode": "AI模型模式",
                "error": "",
                "time": "2026-08-04T00:00:00Z",
            }
        },
        "current_section": "meeting",
    }


def test_project_crud(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    headers = {"X-Workspace-Key": KEY}

    created = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "项目一", "description": "测试", "snapshot": snapshot()},
    )
    assert created.status_code == 201
    project = created.json()
    assert project["lock_version"] == 1
    assert project["snapshot"]["profile"]["name"] == "测试企业"

    listed = client.get("/api/projects", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert "snapshot" not in listed.json()["items"][0]

    isolated_list = client.get(
        "/api/projects", headers={"X-Workspace-Key": OTHER_KEY}
    )
    assert isolated_list.status_code == 200
    assert isolated_list.json()["total"] == 0
    assert client.get(
        f"/api/projects/{project['id']}",
        headers={"X-Workspace-Key": OTHER_KEY},
    ).status_code == 404

    loaded = client.get(f"/api/projects/{project['id']}", headers=headers)
    assert loaded.status_code == 200

    updated = client.put(
        f"/api/projects/{project['id']}",
        headers=headers,
        json={
            "lock_version": 1,
            "name": "项目一（更新）",
            "snapshot": snapshot(),
        },
    )
    assert updated.status_code == 200
    assert updated.json()["lock_version"] == 2

    conflict = client.put(
        f"/api/projects/{project['id']}",
        headers=headers,
        json={"lock_version": 1, "name": "过期保存"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "PROJECT_VERSION_CONFLICT"
    assert conflict.json()["current_version"] == 2

    deleted = client.delete(f"/api/projects/{project['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(
        f"/api/projects/{project['id']}", headers=headers
    ).status_code == 404


def test_workspace_key_required_and_snapshot_rejects_credentials(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    missing = client.get("/api/projects")
    assert missing.status_code == 400
    assert missing.json()["code"] == "WORKSPACE_KEY_REQUIRED"

    blank_name = client.post(
        "/api/projects",
        headers={"X-Workspace-Key": KEY},
        json={"name": "   ", "snapshot": snapshot()},
    )
    assert blank_name.status_code == 422

    invalid = client.post(
        "/api/projects",
        headers={"X-Workspace-Key": KEY},
        json={
            "name": "不安全项目",
            "snapshot": {**snapshot(), "api_key": "secret"},
        },
    )
    assert invalid.status_code == 422

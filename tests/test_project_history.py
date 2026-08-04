from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.project_routes import register_project_routes
from backend.project_store import ProjectStore, reset_project_store_for_tests

KEY = "workspace-" + ("x" * 40)
OTHER = "workspace-" + ("y" * 40)


def snapshot(meeting: str = "第一次会议", contract: str = ""):
    return {
        "identity": {"org": "测试单位", "role": "企业用户"},
        "profile": {"name": "测试企业", "demands": "合同审阅"},
        "forms": {"meetingInput": meeting, "contractInput": contract},
        "results": {"meeting": f"纪要：{meeting}"} if meeting else {},
        "meta": {},
        "current_section": "meeting",
    }


def test_store_creates_lists_and_restores_history(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'history.db'}")
    created = store.create(
        KEY, name="项目一", description="", snapshot=snapshot(), version_label="初始建档"
    )
    assert created["lock_version"] == 1

    versions, total = store.list_history(KEY, created["id"])
    assert total == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["label"] == "初始建档"
    assert "meeting" in versions[0]["changed_modules"]

    updated = store.update(
        KEY,
        created["id"],
        expected_lock_version=1,
        snapshot=snapshot("第二次会议", "合同条款"),
        version_label="补充会议与合同",
    )
    assert updated["lock_version"] == 2

    versions, total = store.list_history(KEY, created["id"])
    assert total == 2
    assert versions[0]["version_number"] == 2
    assert versions[0]["changed_modules"] == ["meeting", "contract"]

    detail = store.get_history(KEY, created["id"], 1)
    assert detail["snapshot"]["forms"]["meetingInput"] == "第一次会议"

    restored = store.restore_history(
        KEY,
        created["id"],
        1,
        expected_lock_version=2,
        version_label="回退到初始会议",
    )
    assert restored["lock_version"] == 3
    assert restored["snapshot"]["forms"]["meetingInput"] == "第一次会议"

    versions, total = store.list_history(KEY, created["id"])
    assert total == 3
    assert versions[0]["change_kind"] == "restore"
    assert versions[0]["source_version_number"] == 1


def test_history_is_workspace_isolated_and_deleted_with_project(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'isolation.db'}")
    created = store.create(KEY, name="项目", description="", snapshot=snapshot())

    try:
        store.list_history(OTHER, created["id"])
    except Exception as exc:
        assert exc.__class__.__name__ == "ProjectNotFound"
    else:
        raise AssertionError("other workspace should not access history")

    store.delete(KEY, created["id"])
    try:
        store.list_history(KEY, created["id"])
    except Exception as exc:
        assert exc.__class__.__name__ == "ProjectNotFound"
    else:
        raise AssertionError("deleted history should not remain accessible")


def test_noop_save_does_not_create_duplicate_version(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'noop.db'}")
    created = store.create(KEY, name="项目", description="", snapshot=snapshot())
    saved = store.update(
        KEY,
        created["id"],
        expected_lock_version=1,
        snapshot=snapshot(),
    )
    assert saved["lock_version"] == 1
    assert store.list_history(KEY, created["id"])[1] == 1


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'routes.db'}")
    reset_project_store_for_tests()
    app = FastAPI()
    register_project_routes(app)
    return TestClient(app)


def test_version_routes(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    headers = {"X-Workspace-Key": KEY}
    created = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "项目", "snapshot": snapshot(), "version_label": "创建"},
    ).json()
    updated = client.put(
        f"/api/projects/{created['id']}",
        headers=headers,
        json={
            "lock_version": 1,
            "snapshot": snapshot("更新后的会议"),
            "version_label": "会议更新",
        },
    ).json()
    assert updated["lock_version"] == 2

    listing = client.get(f"/api/projects/{created['id']}/versions", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert "snapshot" not in listing.json()["items"][0]

    detail = client.get(
        f"/api/projects/{created['id']}/versions/1", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["snapshot"]["forms"]["meetingInput"] == "第一次会议"

    restored = client.post(
        f"/api/projects/{created['id']}/versions/1/restore",
        headers=headers,
        json={"lock_version": 2, "version_label": "恢复初始版本"},
    )
    assert restored.status_code == 200
    assert restored.json()["lock_version"] == 3
    assert restored.json()["snapshot"]["forms"]["meetingInput"] == "第一次会议"

    stale = client.post(
        f"/api/projects/{created['id']}/versions/1/restore",
        headers=headers,
        json={"lock_version": 2},
    )
    assert stale.status_code == 409
    assert stale.json()["current_version"] == 3

    missing = client.get(
        f"/api/projects/{created['id']}/versions/99", headers=headers
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "PROJECT_HISTORY_NOT_FOUND"


def test_existing_projects_receive_single_baseline_history(tmp_path):
    url = f"sqlite:///{tmp_path / 'backfill.db'}"
    store = ProjectStore(url)
    from backend.project_store import ProjectRecord, hash_workspace_key
    from uuid import uuid4

    record = ProjectRecord(
        id=str(uuid4()),
        workspace_hash=hash_workspace_key(KEY),
        name="旧项目",
        description="",
        snapshot=snapshot("迁移前材料"),
        lock_version=4,
    )
    with store.sessions.begin() as session:
        session.add(record)
    store.engine.dispose()

    migrated = ProjectStore(url)
    versions, total = migrated.list_history(KEY, record.id)
    assert total == 1
    assert versions[0]["version_number"] == 4
    assert versions[0]["change_kind"] == "baseline"


def test_history_routes_are_workspace_isolated(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    created = client.post(
        "/api/projects",
        headers={"X-Workspace-Key": KEY},
        json={"name": "隔离项目", "snapshot": snapshot()},
    ).json()

    other_headers = {"X-Workspace-Key": OTHER}
    listing = client.get(
        f"/api/projects/{created['id']}/versions", headers=other_headers
    )
    detail = client.get(
        f"/api/projects/{created['id']}/versions/1", headers=other_headers
    )
    restore = client.post(
        f"/api/projects/{created['id']}/versions/1/restore",
        headers=other_headers,
        json={"lock_version": 1},
    )
    assert listing.status_code == 404
    assert detail.status_code == 404
    assert restore.status_code == 404


def test_frontend_exposes_version_history_controls():
    source = open("frontend/assets/project-storage.js", encoding="utf-8").read()
    assert "PROJECT_HISTORY_READY" in source
    assert "data-view-project-version" in source
    assert "data-restore-project-version" in source
    assert "版本说明（可选）" in source

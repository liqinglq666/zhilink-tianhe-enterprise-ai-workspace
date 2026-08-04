from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import RATE_LIMITER, app
from backend.project_store import reset_project_store_for_tests

WORKSPACE_KEY = "integration-" + ("z" * 40)


def test_project_api_is_registered_and_secured(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'main-app.db'}")
    reset_project_store_for_tests()
    RATE_LIMITER.reset()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/projects",
            headers={"X-Workspace-Key": WORKSPACE_KEY},
            json={
                "name": "主应用集成项目",
                "snapshot": {
                    "identity": {},
                    "profile": {},
                    "forms": {},
                    "results": {},
                    "meta": {},
                    "current_section": "home",
                },
            },
        )

        assert response.status_code == 201
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-ratelimit-limit"]

        project_id = response.json()["id"]
        deleted = client.delete(
            f"/api/projects/{project_id}",
            headers={"X-Workspace-Key": WORKSPACE_KEY},
        )
        assert deleted.status_code == 200
        assert deleted.headers["x-ratelimit-limit"]
    finally:
        RATE_LIMITER.reset()
        reset_project_store_for_tests()

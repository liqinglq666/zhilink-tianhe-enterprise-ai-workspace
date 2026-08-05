from __future__ import annotations

from fastapi.testclient import TestClient

from backend.auth_store import reset_account_store_for_tests
from backend.main import RATE_LIMITER, app
from backend.project_store import reset_project_store_for_tests
from backend.review_store import reset_review_store_for_tests

WORKSPACE_KEY = "integration-" + ("z" * 40)


def test_project_api_is_registered_and_secured(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'main-app.db'}")
    reset_review_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    RATE_LIMITER.reset()
    client = TestClient(app)

    try:
        bundle = client.get("/assets/app.js")
        assert bundle.status_code == 200
        assert "PROJECT_STORAGE_READY" in bundle.text
        assert "ACCOUNT_ACCESS_READY" in bundle.text
        assert "REVIEW_WORKFLOW_READY" in bundle.text
        assert "ZHILINK_STRUCTURED_READY" in bundle.text

        structured = client.post(
            "/api/structured/convert",
            json={
                "module": "meeting",
                "content": "## 一句话结论\n需确认负责人。[MT-01]\n\n## 关键决策\n已明确试点。[MT-01]\n\n## 待办事项表\n- 负责人待确认。[MT-C01]\n\n## 待确认信息\n- 负责人待确认。[MT-C01]",
            },
        )
        assert structured.status_code == 200
        assert structured.json()["schema_version"] == "1.0"
        assert structured.json()["source_sha256"]
        assert structured.headers["cache-control"] == "no-store"
        assert structured.headers["x-ratelimit-limit"]

        session = client.get("/api/auth/session")
        assert session.status_code == 200
        assert session.json()["authenticated"] is False
        assert session.headers["cache-control"] == "no-store"

        response = client.post(
            "/api/projects",
            headers={"X-Workspace-Key": WORKSPACE_KEY},
            json={
                "name": "主应用集成项目",
                "snapshot": {
                    "identity": {},
                    "profile": {},
                    "forms": {},
                    "results": {"meeting": "需要人工确认的会议纪要"},
                    "meta": {},
                    "current_section": "meeting",
                },
            },
        )

        assert response.status_code == 201
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-ratelimit-limit"]
        assert response.json()["snapshot"]["reviews"]["meeting"]["status"] == "ai_draft"

        project_id = response.json()["id"]
        reviews = client.get(
            f"/api/projects/{project_id}/reviews",
            headers={"X-Workspace-Key": WORKSPACE_KEY},
        )
        assert reviews.status_code == 200
        assert reviews.json()["items"][0]["module"] == "meeting"

        deleted = client.delete(
            f"/api/projects/{project_id}",
            headers={"X-Workspace-Key": WORKSPACE_KEY},
        )
        assert deleted.status_code == 200
        assert deleted.headers["x-ratelimit-limit"]
    finally:
        RATE_LIMITER.reset()
        reset_review_store_for_tests()
        reset_account_store_for_tests()
        reset_project_store_for_tests()

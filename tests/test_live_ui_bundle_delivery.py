from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION


def test_native_v4_bundle_is_the_only_app_js_route_after_startup() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert "ZHILINK_UI_V4_SHELL_READY" in response.text
    assert "ZHILINK_UI_V4_FOUNDATION_READY" in response.text
    assert "ZHILINK_UI_V4_FINAL_QA_READY" not in response.text  # loaded lazily by the V4 results layer
    assert "openAccountManager" in response.text
    assert "openKnowledgeBase" in response.text
    assert "openProjectManager" in response.text
    assert "ZHILINK_SIMPLE_UI_READY" in response.text
    assert "ZHILINK_UI_REDESIGN_LIVE_READY" not in response.text
    assert "ZHILINK_UI_V3_READY" not in response.text

    app_js_routes = [route for route in app.router.routes if getattr(route, "path", None) == "/assets/app.js"]
    assert len(app_js_routes) == 1
    assert app_js_routes[0].endpoint.__name__ == "workspace_app_bundle"

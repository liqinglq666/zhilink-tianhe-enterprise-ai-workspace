from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"


def test_api_drawer_is_loaded_from_native_v4_shell_before_meeting_view() -> None:
    routes = ROUTES.read_text(encoding="utf-8")

    assert '"ui-v4-shell.js"' in routes
    assert '"api-drawer-v4.js"' in routes
    assert routes.index('"ui-v4-shell.js"') < routes.index('"api-drawer-v4.js"')
    assert routes.index('"api-drawer-v4.js"') < routes.index('"meeting-user-view.js"')
    assert '"ui-v3-clean.js"' not in routes
    assert '"ui-redesign-live.js"' not in routes

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")

    assert bundle.status_code == 200
    assert "ZHILINK_API_DRAWER_V4_READY" in bundle.text


def test_api_drawer_uses_v4_right_side_layout_without_legacy_scope() -> None:
    script = (ASSETS / "api-drawer-v4.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "api-drawer-v4.css").read_text(encoding="utf-8")

    assert 'document.body.appendChild(panel)' in script
    assert 'panel.classList.add("api-drawer-v4")' in script
    assert 'title.textContent = "模型配置"' in script
    assert 'close.id = "uiV4ApiClose"' in script
    assert 'backdrop.id = "uiV4ApiBackdrop"' in script
    assert 'document.body.classList.remove("ui-v4-api-open")' in script

    assert "body.ui-v4-shell .api-panel.api-drawer-v4" in stylesheet
    assert "body.ui-v4-shell.ui-v4-api-open .api-panel.api-drawer-v4" in stylesheet
    assert "inset: 0 0 0 auto;" in stylesheet
    assert "width: min(560px,100vw);" in stylesheet
    assert "display: none !important;" in stylesheet
    assert "display: flex !important;" in stylesheet
    assert "ui-v3-clean-shell" not in stylesheet
    assert "live-api-" not in stylesheet


def test_api_drawer_preserves_security_copy_and_existing_control_ids() -> None:
    script = (ASSETS / "api-drawer-v4.js").read_text(encoding="utf-8")

    for control_id in (
        "providerSelect",
        "apiKey",
        "baseUrl",
        "modelName",
        "temperature",
        "testConnection",
        "clearKey",
        "connectionResult",
    ):
        assert f'document.getElementById("{control_id}")' in script

    assert "API Key 仅保存在当前浏览器会话" in script
    assert "不会写入业务报告" in script
    assert "公共模型" in script

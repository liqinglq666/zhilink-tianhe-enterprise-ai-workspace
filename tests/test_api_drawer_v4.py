from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"


def test_api_drawer_is_loaded_from_native_v4_shell_before_model_controller() -> None:
    routes = ROUTES.read_text(encoding="utf-8")
    assert routes.index('"ui-v4-shell.js"') < routes.index('"api-drawer-v4.js"')
    assert routes.index('"api-drawer-v4.js"') < routes.index('"model-config-save-v4.js"')
    assert routes.index('"model-config-save-v4.js"') < routes.index('"meeting-user-view.js"')
    assert '"ui-v3-clean.js"' not in routes
    assert '"ui-redesign-live.js"' not in routes

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
    assert bundle.status_code == 200
    assert "ZHILINK_API_DRAWER_V4_READY" in bundle.text
    assert "ZHILINK_MODEL_CONFIG_SAVE_V4_READY" in bundle.text


def test_api_drawer_is_native_markup_and_controller_no_longer_rebuilds_dom() -> None:
    script = (ASSETS / "api-drawer-v4.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "api-drawer-v4.css").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert 'id="apiPanel" class="api-panel api-drawer-v4"' in html
    assert 'id="uiV4ApiClose"' in html
    assert 'id="uiV4ApiBackdrop"' in html
    assert 'id="saveApiConfig"' in html
    assert "document.body.appendChild(panel)" not in script
    assert "document.createElement(\"section\")" not in script
    assert 'document.body.classList.remove("ui-v4-api-open")' in script
    assert "LEGACY_COLLAPSE_STORAGE" in script
    assert "localStorage.removeItem(LEGACY_COLLAPSE_STORAGE)" in script

    assert "body.ui-v4-shell .api-panel.api-drawer-v4" in stylesheet
    assert "body.ui-v4-shell.ui-v4-api-open .api-panel.api-drawer-v4" in stylesheet
    assert "inset: 0 0 0 auto;" in stylesheet
    assert "width: min(560px,100vw);" in stylesheet
    assert "ui-v3-clean-shell" not in stylesheet
    assert "live-api-" not in stylesheet


def test_api_drawer_preserves_security_copy_and_control_ids_in_native_html() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for control_id in (
        "providerSelect", "apiKey", "baseUrl", "modelName", "temperature",
        "testConnection", "clearKey", "connectionResult", "saveApiConfig",
    ):
        assert f'id="{control_id}"' in html

    assert "API Key 仅保存在当前浏览器会话" in html
    assert "不会写入业务报告" in html
    assert "公共模型" in html

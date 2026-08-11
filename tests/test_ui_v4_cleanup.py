from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_native_index_loads_v4_styles_at_first_paint_without_runtime_preload() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    foundation = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")

    styles = (
        "ui-v4-shell.css",
        "ui-v4-foundation.css",
        "ui-v4-dashboard.css",
        "ui-v4-workspace.css",
        "ui-v4-navigation.css",
        "api-drawer-v4.css",
        "model-config-save-v4.css",
        "ui-v4-overlays.css",
        "ui-v4-states.css",
        "ui-v4-forms.css",
        "ui-v4-results.css",
        "ui-v4-final-qa.css",
    )
    positions = [html.index(name) for name in styles]
    assert positions == sorted(positions)
    for name in styles:
        assert name in html

    assert 'link.rel = "preload"' not in foundation
    assert "EARLY_STYLE_ASSETS" not in foundation
    assert "document.createElement(\"link\")" not in foundation
    assert "ZHILINK_UI_V4_FOUNDATION_READY" in foundation


def test_final_bundle_exposes_result_event_version_and_overlay_after_meeting_view() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-11-ui-v4-result-events-v5"
    assert response.text.rfind('key: "meeting-sources"') > response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY")
    assert "ZHILINK_RESULT_EVENTS_READY" in response.text
    assert "ZHILINK_UI_V4_RUNTIME_READY" in response.text
    assert "ZHILINK_UI_V4_SHELL_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" not in response.text
    assert "EARLY_STYLE_ASSETS" not in response.text


def test_foundation_and_overlay_layers_do_not_own_business_state() -> None:
    foundation = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in ("fetch(", "state.results", "setResult", "apiStream", "sessionStorage", "localStorage"):
        assert forbidden not in foundation
        assert forbidden not in overlays


def test_provenance_guard_is_self_contained_after_wrapper_removal() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert 'STYLE_URL = "/assets/data-provenance-guard.css?v=20260806.1"' in script
    assert 'link.dataset.zhilinkDataProvenance = "true"' in script
    assert "function ensureStyles()" in script
    assert "BASE_RESULT_SCHEMA_VERSION" in script
    assert "ZHILINK_DATA_PROVENANCE_READY" in script
    assert "CORE_SCRIPT" not in script
    assert "loadCoreGuard" not in script

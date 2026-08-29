from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
RECOVERY_MARKER = "/* Recover known workspace JSON keys before feature modules start. */"


def test_native_index_loads_v4_styles_at_first_paint_without_runtime_preload() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    styles = (
        "ui-v4-shell.css",
        "ui-v4-foundation.css",
        "ui-v4-dashboard.css",
        "ui-v4-workspace.css",
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
    assert "ui-v4-navigation.css" not in html

    assert "ui-v4-foundation.js" not in UI_SCRIPTS
    assert not (ASSETS / "ui-v4-foundation.js").exists()


def test_final_bundle_recovers_storage_before_core_and_exposes_v4_runtime() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")
        old_result_bridge = client.get("/assets/result-events.js")
        old_hook_bridge = client.get("/assets/workspace-hooks.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert response.text.index(RECOVERY_MARKER) < response.text.index("function loadResultsFromSession")
    assert response.text.rfind('key: "meeting-sources"') > response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY")
    assert "ZHILINK_STORAGE_RECOVERY" not in response.text
    assert "ZHILINK_WORKSPACE_CONTRACTS_READY" in response.text
    assert "ZHILINK_EXAMPLE_LOADER_READY" in response.text
    assert "ZHILINK_WORKSPACE_HOOKS_READY" in response.text
    assert "ZHILINK_RESULT_EVENTS_READY" in response.text
    assert "ZHILINK_UI_V4_RUNTIME_READY" in response.text
    assert "ZHILINK_UI_V4_SHELL_READY" in response.text
    assert "ZHILINK_UI_V4_FINAL_QA_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" not in response.text
    assert "EARLY_STYLE_ASSETS" not in response.text
    assert old_result_bridge.status_code == 404
    assert old_hook_bridge.status_code == 404


def test_final_presentation_and_overlay_layers_do_not_own_business_state() -> None:
    final_qa = (ASSETS / "ui-v4-final-qa.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in ("fetch(", "state.results", "setResult", "apiStream", "sessionStorage", "localStorage"):
        assert forbidden not in final_qa
        assert forbidden not in overlays


def test_provenance_guard_is_self_contained_after_wrapper_removal() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert "STYLE_URL" not in script
    assert "zhilinkDataProvenance" not in script
    assert "ensureStyles" not in script
    assert 'document.createElement("link")' not in script
    assert "BASE_RESULT_SCHEMA_VERSION" in script
    assert "ZHILINK_DATA_PROVENANCE_READY" in script
    assert "CORE_SCRIPT" not in script
    assert "loadCoreGuard" not in script


def test_dashboard_pending_items_ignore_markdown_structure_noise() -> None:
    dashboard = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")

    assert "function pendingText(raw)" in dashboard
    assert 'if (/^\\s*\\|.*\\|\\s*$/.test(source)) return "";' in dashboard
    assert '.replace(/[*_`~]/g, "")' in dashboard
    assert "待确认(?:信息|事项)?" in dashboard
    assert "待核实(?:信息|事项)?" in dashboard
    assert "const text = pendingText(raw);" in dashboard

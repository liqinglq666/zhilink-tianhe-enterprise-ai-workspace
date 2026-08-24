from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_global_simple_advanced_mode_is_removed() -> None:
    assert not (ASSETS / "product-simplification.js").exists()
    assert not (ASSETS / "product-simplification.css").exists()
    routes = (ROOT / "backend" / "project_routes.py").read_text(encoding="utf-8")
    assert "product-simplification" not in routes
    assert "zhilian_ui_mode_v1" not in (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")


def test_runtime_is_the_shared_dom_refresh_scheduler() -> None:
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")
    assert "ZHILINK_UI_V4_RUNTIME_READY" in runtime
    assert "new MutationObserver" in runtime
    assert "requestAnimationFrame(runSubscribers)" in runtime

    presentation_layers = (
        "ui-v4-dashboard.js",
        "ui-v4-overlays.js",
        "ui-v4-states.js",
        "ui-v4-results.js",
        "ui-v4-final-qa.js",
    )
    for filename in presentation_layers:
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "new MutationObserver" not in source, filename
        assert "ZHILINK_UI_V4_RUNTIME" in source, filename


def test_forms_results_final_qa_and_model_save_are_direct_bundle_entries() -> None:
    routes = (ROOT / "backend" / "project_routes.py").read_text(encoding="utf-8")
    expected = (
        '"ui-v4-runtime.js"',
        '"ui-v4-shell.js"',
        '"api-drawer-v4.js"',
        '"model-config-save-v4.js"',
        '"ui-v4-states.js"',
        '"ui-v4-forms.js"',
        '"ui-v4-results.js"',
        '"ui-v4-final-qa.js"',
    )
    positions = [routes.index(item) for item in expected]
    assert positions == sorted(positions)

    states = (ASSETS / "ui-v4-states.js").read_text(encoding="utf-8")
    results = (ASSETS / "ui-v4-results.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")
    assert "ensureForms" not in states
    assert "ensureResults" not in states
    assert "ensureFinalQa" not in results
    assert "data-model-config-save-v4" not in overlays


def test_index_serves_native_v4_structure_at_first_paint() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'body class="ui-v4-shell ui-v4-foundation' in html
    assert 'id="uiV4TopNav"' in html
    assert 'id="uiV4ProjectContext"' in html
    assert 'id="uiV4AccountMenu"' in html
    assert 'id="uiV4SidebarRecent"' in html
    assert 'id="uiV4PendingPanel"' in html
    assert 'id="uiV4UsagePanel"' in html
    assert 'id="apiPanel" class="api-panel api-drawer-v4"' in html
    assert 'id="saveApiConfig"' in html
    assert "readiness-card" not in html
    assert "hero-visual" not in html
    assert 'data-tool-key="report"' not in html
    assert "tool-status-card" not in html

    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert 'id="uiV4TopNav"' in response.text

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_foundation_preloads_exact_native_v4_styles_without_reordering_cascade() -> None:
    script = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")

    assert 'link.rel = "preload"' in script
    assert 'link.as = "style"' in script
    assert '["ui-v4-shell.css", "20260810.3"]' in script
    assert '["ui-v4-foundation.css", "20260810.3"]' in script
    assert '["ui-v4-dashboard.css", "20260810.3"]' in script
    assert '["ui-v4-workspace.css", "20260810.3"]' in script
    assert '["ui-v4-navigation.css", "20260810.3"]' in script
    assert '["ui-v4-overlays.css", "20260810.3"]' in script
    assert '["ui-v4-final-qa.css", "20260810.3"]' in script
    assert '["model-config-save-v4.css", "20260810.3"]' in script
    assert 'link.rel = "stylesheet"' in script
    assert 'link.dataset.uiV4Preload = filename' in script


def test_final_bundle_exposes_native_version_and_overlay_after_meeting_view() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-10-ui-v4-native-v3"
    assert response.text.rfind('key: "meeting-sources"') > response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY")
    assert "EARLY_STYLE_ASSETS" in response.text
    assert "ZHILINK_UI_V4_SHELL_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" in response.text


def test_foundation_and_overlay_layers_do_not_own_business_state() -> None:
    foundation = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in ("fetch(", "state.results", "setResult", "apiStream", "sessionStorage", "localStorage"):
        assert forbidden not in foundation
        assert forbidden not in overlays


def test_provenance_guard_is_self_contained_after_legacy_fixes_removal() -> None:
    script = (ASSETS / "data-provenance-guard-v2.js").read_text(encoding="utf-8")

    assert 'const CORE_STYLE = "/assets/data-provenance-guard.css?v=20260806.1"' in script
    assert 'style.dataset.zhilinkDataProvenance = "true"' in script
    assert "function ensureStyles()" in script
    assert "loadCoreGuard();" in script
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" in script

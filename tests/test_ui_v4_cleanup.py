from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_foundation_preloads_exact_runtime_styles_without_reordering_cascade() -> None:
    script = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")

    assert 'link.rel = "preload"' in script
    assert 'link.as = "style"' in script
    assert '["ui-v4-foundation.css", "20260810.2"]' in script
    assert '["ui-v4-dashboard.css", "20260810.1"]' in script
    assert '["ui-v4-overlays.css", "20260810.2"]' in script
    assert '["ui-v4-results.css", "20260810.1"]' in script
    assert '["ui-v4-final-qa.css", "20260810.1"]' in script
    assert '["model-config-save-v4.css", "20260810.1"]' in script

    # The optimization must warm the cache only. Runtime loaders still own stylesheet order.
    assert 'link.rel = "stylesheet"' in script
    assert 'link.dataset.uiV4Preload = filename' in script
    assert 'document.querySelectorAll(".live-ai-orbit").forEach(node => node.remove())' in script


def test_final_bundle_exposes_cleanup_version_and_overlay_after_meeting_view() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-10-ui-v4-final-v2"
    assert response.text.rfind('key: "meeting-sources"') > response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY")
    assert "EARLY_STYLE_ASSETS" in response.text


def test_cleanup_remains_visual_and_accessibility_only() -> None:
    foundation = (ASSETS / "ui-v4-foundation.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in ("fetch(", "state.results", "setResult", "apiStream", "sessionStorage", "localStorage"):
        assert forbidden not in foundation
        assert forbidden not in overlays

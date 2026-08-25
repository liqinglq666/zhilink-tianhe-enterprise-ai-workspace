from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
INDEX = ROOT / "frontend" / "index.html"
RECOVERY_MARKER = "/* Recover known workspace JSON keys before feature modules start. */"

FEATURE_STYLES = (
    "generation-controls.css",
    "account-access.css",
    "project-storage.css",
    "project-history.css",
    "review-workflow.css",
    "structured-results.css",
    "policy-sources.css",
    "knowledge-base.css",
    "service-workflow.css",
    "data-provenance-guard.css?v=20260806.1",
    "meeting-user-view.css",
)


def test_feature_styles_are_native_dependencies_before_v4_presentation() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert UI_SCRIPTS[0] == "storage-recovery.js"
    base_position = html.index('href="/assets/style.css"')
    v4_position = html.index('href="/assets/ui-v4-shell.css?v=20260811.1"')
    positions = []
    for stylesheet in FEATURE_STYLES:
        marker = f'href="/assets/{stylesheet}"'
        assert html.count(marker) == 1, stylesheet
        positions.append(html.index(marker))

    assert base_position < positions[0]
    assert positions == sorted(positions)
    assert positions[-1] < v4_position


def test_storage_recovery_is_storage_only() -> None:
    source = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")

    assert RECOVERY_MARKER in source
    assert "ZHILINK_STORAGE_RECOVERY" not in source
    assert "FEATURE_STYLES_URL" not in source
    assert "ensureFeatureStyles" not in source
    assert "feature-styles.css" not in source
    assert "ZHILINK_FEATURE_STYLES_READY" not in source
    assert 'document.createElement("link")' not in source
    assert "document.head.appendChild" not in source


def test_feature_styles_have_no_module_level_loaders() -> None:
    consumers = {
        "generation-controls.js": ("link[data-generation-controls]", "generation-controls.css"),
        "account-access.js": ("link[data-account-access]", "account-access.css"),
        "project-storage.js": ("link[data-project-storage]", "project-storage.css"),
        "review-workflow.js": ("link[data-review-workflow]", "review-workflow.css"),
        "structured-results.js": ("link[data-structured-results]", "structured-results.css"),
        "policy-sources.js": ("link[data-policy-sources]", "policy-sources.css"),
        "knowledge-base.js": ("link[data-knowledge-base]", "knowledge-base.css"),
        "service-workflow.js": ("link[data-service-workflow]", "service-workflow.css"),
        "data-provenance-guard.js": ("link[data-zhilink-data-provenance]", "data-provenance-guard.css"),
        "meeting-user-view.js": ("link[data-meeting-user-view]", "meeting-user-view.css"),
    }

    for filename, (selector, stylesheet) in consumers.items():
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert selector not in source
        assert stylesheet not in source
        assert 'document.createElement("link")' not in source

    project_source = (ASSETS / "project-storage.js").read_text(encoding="utf-8")
    assert "link[data-project-history]" not in project_source
    assert "project-history.css" not in project_source


def test_feature_manifest_and_legacy_collapse_dom_are_removed() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert not (ASSETS / "feature-styles.css").exists()
    assert "feature-styles.css" not in html
    assert 'id="toggleApiPanel"' not in html
    assert "collapse-btn" not in html
    for stylesheet in FEATURE_STYLES:
        assert (ASSETS / stylesheet.split("?", 1)[0]).is_file()


def test_bundle_still_starts_with_storage_recovery() -> None:
    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")

    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert bundle.text.index(RECOVERY_MARKER) < bundle.text.index("ZHILINK_GENERATION_CONTROLS_READY")

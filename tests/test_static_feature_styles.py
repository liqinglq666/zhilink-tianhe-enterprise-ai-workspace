from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
INDEX = ROOT / "frontend" / "index.html"

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


def test_feature_styles_are_native_html_dependencies_before_v4_presentation() -> None:
    html = INDEX.read_text(encoding="utf-8")

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


def test_storage_recovery_no_longer_loads_or_owns_stylesheets() -> None:
    script = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")

    assert "FEATURE_STYLES_URL" not in script
    assert "ensureFeatureStyles" not in script
    assert "feature-styles.css" not in script
    assert "ZHILINK_FEATURE_STYLES_READY" not in script
    assert 'document.createElement("link")' not in script
    assert "document.head.appendChild" not in script
    assert "ZHILINK_STORAGE_RECOVERY" in script


def test_feature_style_manifest_and_legacy_api_collapse_button_are_removed() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert not (ASSETS / "feature-styles.css").exists()
    assert "feature-styles.css" not in html
    assert 'id="toggleApiPanel"' not in html
    assert "collapse-btn" not in html


def test_every_native_feature_stylesheet_exists_as_a_real_asset() -> None:
    for stylesheet in FEATURE_STYLES:
        filename = stylesheet.split("?", 1)[0]
        assert (ASSETS / filename).is_file(), filename

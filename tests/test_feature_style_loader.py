from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"

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
    "data-provenance-guard.css",
)


def test_feature_styles_have_one_early_bootstrap_owner() -> None:
    source = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")

    assert UI_SCRIPTS[0] == "storage-recovery.js"
    assert 'const FEATURE_STYLES_URL = "/assets/feature-styles.css?v=20260824.1"' in source
    assert 'document.querySelector("link[data-zhilink-feature-styles]")' in source
    assert source.count('document.createElement("link")') == 1
    assert 'stylesheet.dataset.zhilinkFeatureStyles = "true"' in source
    assert "ZHILINK_FEATURE_STYLES_READY" in source


def test_feature_style_manifest_preserves_existing_cascade_order() -> None:
    manifest = (ASSETS / "feature-styles.css").read_text(encoding="utf-8")
    positions = []

    for filename in FEATURE_STYLES:
        assert filename in manifest
        positions.append(manifest.index(filename))

    assert positions == sorted(positions)
    assert manifest.count("@import") == len(FEATURE_STYLES)


def test_generation_styles_have_no_module_level_loader() -> None:
    bootstrap = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")
    generation = (ASSETS / "generation-controls.js").read_text(encoding="utf-8")

    assert "generationControls" not in bootstrap
    assert "link[data-generation-controls]" not in generation
    assert 'document.createElement("link")' not in generation
    assert 'generation-controls.css' not in generation


def test_bootstrap_marks_remaining_legacy_loaders_as_already_satisfied() -> None:
    source = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")
    markers = (
        "accountAccess",
        "projectStorage",
        "projectHistory",
        "reviewWorkflow",
        "structuredResults",
        "policySources",
        "knowledgeBase",
        "serviceWorkflow",
        "zhilinkDataProvenance",
    )
    for marker in markers:
        assert f"stylesheet.dataset.{marker}" in source

    legacy_guards = {
        "account-access.js": "link[data-account-access]",
        "project-storage.js": "link[data-project-storage]",
        "review-workflow.js": "link[data-review-workflow]",
        "structured-results.js": "link[data-structured-results]",
        "policy-sources.js": "link[data-policy-sources]",
        "knowledge-base.js": "link[data-knowledge-base]",
        "service-workflow.js": "link[data-service-workflow]",
        "data-provenance-guard.js": "link[data-zhilink-data-provenance]",
    }
    for filename, selector in legacy_guards.items():
        assert selector in (ASSETS / filename).read_text(encoding="utf-8"), filename

    project_source = (ASSETS / "project-storage.js").read_text(encoding="utf-8")
    assert "link[data-project-history]" in project_source


def test_feature_manifest_and_bundle_are_served() -> None:
    with TestClient(app) as client:
        stylesheet = client.get("/assets/feature-styles.css?v=20260824.1")
        bundle = client.get("/assets/app.js")

    assert stylesheet.status_code == 200
    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert bundle.text.index("ZHILINK_FEATURE_STYLES_READY") < bundle.text.index("ZHILINK_GENERATION_CONTROLS_READY")

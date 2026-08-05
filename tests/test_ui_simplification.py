from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_simple_ui_defaults_and_progressive_disclosure_are_present():
    script = (ROOT / "frontend/assets/product-simplification.js").read_text(encoding="utf-8")
    assert 'const SIMPLE = "simple"' in script
    assert "zhilian_ui_mode_v1" in script
    assert "openServiceWorkflowFromProject" in script
    assert "toggleAdvancedUiMode" in script
    assert "toggleStructuredAdvanced" in script
    assert "toggleKnowledgeAdvanced" in script
    assert "toggleReviewAdvanced" in script
    assert "ZHILINK_SIMPLE_UI_READY = true" in script


def test_simple_ui_css_hides_only_advanced_surfaces():
    css = (ROOT / "frontend/assets/product-simplification.css").read_text(encoding="utf-8")
    assert "body.ui-simple-mode #openServiceWorkflow" in css
    assert ".structured-raw" in css
    assert ".knowledge-history" in css
    assert ".review-events-section" in css
    assert ".ui-workflow-audit-card" in css
    assert "@media (max-width: 760px)" in css


def test_simplification_runs_after_feature_scripts_in_workspace_bundle():
    routes = (ROOT / "backend/project_routes.py").read_text(encoding="utf-8")
    service_index = routes.index('"service-workflow.js"')
    simple_index = routes.index('"product-simplification.js"')
    assert service_index < simple_index

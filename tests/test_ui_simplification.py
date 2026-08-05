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

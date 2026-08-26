from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_brand_logo_is_a_static_vector_asset() -> None:
    logo = (ASSETS / "brand-logo.svg").read_text(encoding="utf-8")
    assert "智链天河" in logo
    assert "Enterprise AI Workspace" in logo
    assert "ribbonBlue" in logo
    assert "ribbonCyan" in logo


def test_v4_stylesheet_loads_brand_lockup_without_runtime_injection() -> None:
    model_css = (ASSETS / "model-config-save-v4.css").read_text(encoding="utf-8")
    brand_css = (ASSETS / "brand-lockup.css").read_text(encoding="utf-8")

    assert model_css.startswith('@import url("/assets/brand-lockup.css?v=20260826.1");')
    assert 'url("/assets/brand-logo.svg")' in brand_css
    assert ".ui-v4-shell .brand::before" in brand_css

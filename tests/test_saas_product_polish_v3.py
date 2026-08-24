from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_saas_polish_v3_is_loaded_as_the_final_presentation_layer() -> None:
    routes = (ROOT / "backend" / "project_routes.py").read_text(encoding="utf-8")
    assert UI_BUNDLE_VERSION == "2026-08-24-ui-v4-saas-polish-v3"
    assert routes.index('"enterprise-user-view.js"') < routes.index('"ui-v4-final-qa.js"')
    assert routes.index('"ui-v4-final-qa.js"') < routes.index('"saas-product-polish-v3.js"')

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        stylesheet = client.get("/assets/saas-product-polish-v3.css?v=20260824.1")

    assert bundle.status_code == 200
    assert stylesheet.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert "ZHILINK_SAAS_PRODUCT_POLISH_V3_READY" in bundle.text
    assert 'STYLE_URL = "/assets/saas-product-polish-v3.css?v=20260824.1"' in bundle.text


def test_saas_polish_controller_only_owns_presentation() -> None:
    script = (ASSETS / "saas-product-polish-v3.js").read_text(encoding="utf-8")

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "sessionStorage",
        "localStorage",
        "state.results",
        "setResult",
        "saveConfig",
        "projectRequest",
        "new MutationObserver",
    ):
        assert forbidden not in script

    assert 'runtime?.subscribe?.(apply, { immediate: false })' in script
    assert 'document.body.classList.add("ui-v4-saas-polish")' in script
    assert 'button.setAttribute("aria-current", "page")' in script
    assert 'card.dataset.productTier = card.classList.contains("ui-v4-secondary-task") ? "utility" : "primary"' in script


def test_saas_polish_css_enforces_hierarchy_density_and_mobile_behavior() -> None:
    stylesheet = (ASSETS / "saas-product-polish-v3.css").read_text(encoding="utf-8")

    assert '#home .module-card[data-product-tier="primary"]' in stylesheet
    assert '#home .module-card[data-product-tier="utility"]' in stylesheet
    assert "grid-template-columns: repeat(12, minmax(0, 1fr));" in stylesheet
    assert "grid-column: span 3;" in stylesheet
    assert "grid-column: span 6;" in stylesheet
    assert "@media (max-width: 760px)" in stylesheet
    assert "grid-template-columns: 1fr;" in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert "@media (max-height: 760px) and (min-width: 1021px)" in stylesheet
    assert "@media (hover: none)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet


def test_customer_copy_uses_business_language_instead_of_model_jargon() -> None:
    script = (ASSETS / "saas-product-polish-v3.js").read_text(encoding="utf-8")

    assert '"AI 服务设置"' in script
    assert "当前没有待你确认的事项。新结果需要复核时会显示在这里。" in script
    assert "还没有最近结果。完成一次业务任务后，这里会显示你的最新材料。" in script
    assert 'setText(safetyTitle, "使用与复核")' in script

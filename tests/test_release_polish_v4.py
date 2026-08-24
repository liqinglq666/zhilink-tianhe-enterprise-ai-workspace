from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_release_polish_v4_is_delivered_by_the_existing_presentation_controller() -> None:
    script = (ASSETS / "saas-product-polish-v3.js").read_text(encoding="utf-8")

    with TestClient(app) as client:
        stylesheet = client.get("/assets/release-polish-v4.css?v=20260824.1")
        bundle = client.get("/assets/app.js")

    assert stylesheet.status_code == 200
    assert bundle.status_code == 200
    assert 'RELEASE_STYLE_URL = "/assets/release-polish-v4.css?v=20260824.1"' in script
    assert 'document.body.classList.add("ui-v4-saas-polish", "ui-v4-release-polish")' in script
    assert 'document.documentElement.dataset.zhilinkReleasePolish = "v4"' in script
    assert "ZHILINK_RELEASE_POLISH_V4_READY" in bundle.text


def test_release_polish_v4_remains_presentation_and_accessibility_only() -> None:
    script = (ASSETS / "saas-product-polish-v3.js").read_text(encoding="utf-8")

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "localStorage",
        "sessionStorage",
        "projectRequest",
        "setResult",
        "saveConfig",
        "new MutationObserver",
    ):
        assert forbidden not in script

    assert "window.visualViewport" in script
    assert 'toggle.setAttribute("aria-haspopup", "menu")' in script
    assert 'menu.setAttribute("role", "menu")' in script
    assert 'button.setAttribute("role", "menuitem")' in script
    assert 'event.key === "ArrowDown"' in script
    assert 'event.key === "ArrowUp"' in script
    assert 'event.key === "Home"' in script
    assert 'event.key === "End"' in script
    assert 'sidebar.setAttribute("aria-hidden"' in script
    assert 'document.addEventListener("keydown", handleReleaseKeydown, true)' in script
    assert 'window.addEventListener("resize", scheduleViewportSync' in script


def test_release_polish_v4_handles_real_world_viewports_and_long_content() -> None:
    stylesheet = (ASSETS / "release-polish-v4.css").read_text(encoding="utf-8")

    assert "overflow-wrap: anywhere;" in stylesheet
    assert "@supports (height: 100dvh)" in stylesheet
    assert "height: 100dvh;" in stylesheet
    assert "var(--ui4-visual-height, 100vh)" in stylesheet
    assert "env(safe-area-inset-top)" in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert "@media (min-width: 1021px) and (max-width: 1440px) and (max-height: 820px)" in stylesheet
    assert "body.ui-v4-release-polish.ui-v4-sidebar-open" in stylesheet
    assert "@media (max-width: 390px)" in stylesheet
    assert "@media (min-width: 1800px)" in stylesheet
    assert "@media (hover: none)" in stylesheet
    assert "@media (forced-colors: active)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet

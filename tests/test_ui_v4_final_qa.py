from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_v4_results_and_final_qa_are_direct_ordered_bundle_layers() -> None:
    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        results = client.get("/assets/ui-v4-results.js?v=20260811.1")
        final_qa = client.get("/assets/ui-v4-final-qa.js?v=20260811.1")
        stylesheet = client.get("/assets/ui-v4-final-qa.css?v=20260811.1")

    assert bundle.status_code == 200
    assert results.status_code == 200
    assert final_qa.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_RESULTS_READY" in results.text
    assert "ZHILINK_UI_V4_FINAL_QA_READY" in final_qa.text
    assert bundle.text.index("ZHILINK_UI_V4_RESULTS_READY") < bundle.text.index("ZHILINK_UI_V4_FINAL_QA_READY")
    assert "ensureFinalQa" not in results.text
    assert "document.createElement(\"script\")" not in results.text
    assert "ZHILINK_UI_V4_RUNTIME" in final_qa.text


def test_v4_final_qa_adds_keyboard_navigation_and_landmark_support() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-final-qa.js?v=20260811.1")

    text = script.text
    assert 'link.id = "uiV4SkipLink"' in text
    assert 'link.textContent = "跳到主内容"' in text
    assert 'main.id = "mainContent"' in text
    assert 'main.setAttribute("aria-label", "主要工作区")' in text
    assert 'button.setAttribute("aria-current", "page")' in text
    assert 'document.getElementById("uiV4MobileMenu")' in text
    assert 'mobile.setAttribute("aria-controls", sidebar.id)' in text
    assert 'title.setAttribute("tabindex", "-1")' in text
    assert 'title.focus({ preventScroll: true })' in text
    assert 'event.detail === 0' in text
    assert "#identityChip[role='button']" in text
    assert 'document.getElementById("uiV4AccountToggle")' in text


def test_v4_final_qa_makes_horizontal_result_content_keyboard_reachable() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-final-qa.js?v=20260811.1")

    text = script.text
    assert 'const SCROLLABLE_SELECTOR = ".result-section-content, .structured-table-wrap"' in text
    assert 'region.scrollWidth > region.clientWidth + 2' in text
    assert 'region.dataset.uiV4KeyboardScroll = "true"' in text
    assert 'region.setAttribute("tabindex", "0")' in text
    assert 'region.setAttribute("role", "region")' in text
    assert '可横向滚动的内容区域' in text


def test_v4_final_qa_covers_required_responsive_widths_and_touch_targets() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-final-qa.js?v=20260811.1")
        stylesheet = client.get("/assets/ui-v4-final-qa.css?v=20260811.1")

    script_text = script.text
    css = stylesheet.text
    for marker in ("360", "390", "768", "1024", "1280"):
        assert marker in script_text

    assert "min-height: 44px" in css
    assert "min-width: 44px !important" in css
    assert "@media (max-width: 1280px)" in css
    assert "@media (max-width: 1024px)" in css
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 720px)" in css
    assert "@media (max-width: 390px)" in css
    assert "@media (max-width: 360px)" in css
    assert "@media (min-width: 1025px) and (max-height: 680px)" in css
    assert "env(safe-area-inset-top)" in css
    assert "env(safe-area-inset-right)" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "env(safe-area-inset-left)" in css
    assert "overflow-x: clip" in css
    assert ".ui-v4-mobile-menu" in css
    assert ".ui-v4-account-toggle" in css


def test_v4_final_qa_supports_reduced_motion_and_high_contrast_focus() -> None:
    with TestClient(app) as client:
        stylesheet = client.get("/assets/ui-v4-final-qa.css?v=20260811.1")

    css = stylesheet.text
    assert ".ui-v4-skip-link" in css
    assert ":focus-visible" in css
    assert "outline: 3px solid #2563eb" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (forced-colors: active)" in css
    assert "Highlight" in css


def test_v4_final_qa_does_not_own_business_or_persistence_state() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-final-qa.js?v=20260811.1")

    for forbidden in (
        "fetch(", "localStorage", "sessionStorage", "state.results", "setResult(", "saveConfig(", "apiStream(",
        "setAttribute(\"type\", \"button\")", "liveMobileMenu", "liveAccountToggle", "MutationObserver",
    ):
        assert forbidden not in script.text

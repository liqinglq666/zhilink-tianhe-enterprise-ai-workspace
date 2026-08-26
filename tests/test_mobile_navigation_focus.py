from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_mobile_navigation_focus_waits_for_runtime_page_state():
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    app = (ASSETS / "app.js").read_text(encoding="utf-8")

    assert 'let pendingMobileNavigationSection = "";' in shell
    assert "function requestMobileNavigationFocus(section)" in shell
    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("mobile-navigation-focus")' in shell
    assert "function resolveMobileNavigationFocus()" in shell
    assert 'document.querySelector(".page.active-page")?.id !== section' in shell
    assert "resolveMobileNavigationFocus();" in shell

    # Business navigation stays owned by app.js; Shell only owns mobile chrome/focus.
    assert 'btn.addEventListener("click", () => go(btn.dataset.section))' in app
    assert "function go(section)" in app
    assert "go(navButton.dataset.section)" not in shell


def test_mobile_navigation_focus_has_no_key_lifecycle_timeout_race():
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")

    assert "pendingMobileNavFocus" not in shell
    assert 'document.addEventListener("keyup"' not in shell
    assert "window.setTimeout" not in shell
    assert 'requestMobileNavigationFocus(navButton.dataset.section)' in shell

    # Final focus is confirmed on the following frame so Chromium cannot return
    # focus to the just-deactivated sidebar button after keyboard activation.
    first_frame = shell.index("window.requestAnimationFrame(() => {", shell.index("function resolveMobileNavigationFocus()"))
    second_frame = shell.index("window.requestAnimationFrame(() => {", first_frame + 1)
    assert second_frame > first_frame
    assert 'document.activeElement !== title' in shell

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "frontend/assets/ui-v4-shell.js").read_text(encoding="utf-8")


def test_mobile_sidebar_moves_focus_before_becoming_inert():
    focus = 'if (!shouldOpen && focusAfterClose) focusAfterClose.focus?.({ preventScroll: true });'
    inert_sync = 'syncSidebarAccessibility();'
    set_sidebar = SHELL.split("function setSidebarOpen", 1)[1].split("function syncSidebarViewport", 1)[0]
    assert focus in set_sidebar
    assert set_sidebar.index(focus) < set_sidebar.index(inert_sync)


def test_sidebar_accessibility_never_inerts_current_focus():
    assert 'if (!open && sidebar.contains(document.activeElement))' in SHELL
    assert '(byId("uiV4MobileMenu") || byId("mainContent"))?.focus?.({ preventScroll: true });' in SHELL

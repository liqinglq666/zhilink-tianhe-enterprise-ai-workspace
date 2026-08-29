from __future__ import annotations

from pathlib import Path


def test_mobile_navigation_uses_deterministic_keyboard_focus_path() -> None:
    root = Path(__file__).resolve().parents[1]
    shell = (root / "frontend/assets/ui-v4-shell.js").read_text(encoding="utf-8")
    index = (root / "frontend/index.html").read_text(encoding="utf-8")

    assert 'id="pageTitle" tabindex="-1"' in index
    assert 'let pendingMobileNavKey = "";' in shell
    assert "focusAfterNavigation" not in shell
    assert 'const title = byId("pageTitle");\n        setSidebarOpen(false, title);' in shell
    assert 'setSidebarOpen(false);\n        if (!pendingMobileNavKey) title?.focus?.({ preventScroll: true });' not in shell
    assert 'navButton && isMobileSidebar() && ["Enter", " "].includes(event.key)' in shell
    assert "pendingMobileNavKey = event.key;\n        navButton.click();" in shell
    assert 'document.addEventListener("keyup"' in shell
    assert 'if (!pendingMobileNavKey || event.key !== pendingMobileNavKey) return;' in shell
    assert 'pendingMobileNavKey = "";\n      byId("pageTitle")?.focus?.({ preventScroll: true });' in shell
    assert "pendingMobileNavFocus" not in shell

from __future__ import annotations

from pathlib import Path


def test_mobile_navigation_uses_single_deferred_focus_path() -> None:
    root = Path(__file__).resolve().parents[1]
    shell = (root / "frontend/assets/ui-v4-shell.js").read_text(encoding="utf-8")
    index = (root / "frontend/index.html").read_text(encoding="utf-8")

    assert 'id="pageTitle" tabindex="-1"' in index
    assert "focusAfterNavigation" in shell
    assert "setSidebarOpen(false);\n        focusAfterNavigation(title);" in shell
    assert "pendingMobileNavFocus" not in shell
    assert 'document.addEventListener("keyup"' not in shell

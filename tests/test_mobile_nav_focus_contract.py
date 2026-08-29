from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "frontend" / "assets" / "ui-v4-shell.js"


def test_mobile_navigation_moves_focus_before_sidebar_becomes_inert() -> None:
    source = SHELL.read_text(encoding="utf-8")

    assert 'const title = byId("pageTitle");\n        setSidebarOpen(false, title);' in source
    assert 'setSidebarOpen(false);\n        if (!pendingMobileNavKey) title?.focus?.({ preventScroll: true });' not in source

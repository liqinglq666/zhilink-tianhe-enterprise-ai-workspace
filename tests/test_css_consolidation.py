from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_navigation_only_owns_project_resource_and_desktop_context_refinements() -> None:
    navigation = read("ui-v4-navigation.css")
    shell = read("ui-v4-shell.css")

    assert ".ui-v4-navigation .ui-v4-nav-group-label" not in navigation
    assert ".ui-v4-navigation .ui-v4-top-nav { gap: 7px; }" not in navigation
    assert ".ui-v4-navigation .ui-v4-account-context" not in navigation

    assert ".ui-v4-shell .nav-group-label" in shell
    assert ".ui-v4-shell .ui-v4-top-nav { display: flex; align-items: center; gap: 7px; }" in shell


def test_navigation_does_not_override_mobile_sidebar_width() -> None:
    navigation = read("ui-v4-navigation.css")
    shell = read("ui-v4-shell.css")

    assert "@media (min-width: 1021px)" in navigation
    assert ".ui-v4-navigation .sidebar { width: var(--ui4-sidebar-width); }" in navigation
    assert "@media (min-width: 1021px) and (max-width: 1240px)" in navigation
    assert "@media (max-width: 1020px) {\n  .ui-v4-navigation .shell { display: block; }" not in navigation

    assert "width: min(300px, 86vw);" in shell


def test_workspace_sticky_offset_is_desktop_only() -> None:
    navigation = read("ui-v4-navigation.css")
    workspace = read("ui-v4-workspace.css")

    assert "@media (min-width: 1181px)" in navigation
    assert "top: 88px;" in navigation
    assert "max-height: calc(100vh - 102px);" in navigation

    assert "@media (max-width: 1180px)" in workspace
    assert "position: relative; top: auto; max-height: none;" in workspace
    assert "@media (max-width: 1020px)" in navigation
    assert "top: auto;" not in navigation


def test_deleted_native_v4_dom_does_not_keep_compatibility_css() -> None:
    foundation = read("ui-v4-foundation.css")
    dashboard = read("ui-v4-dashboard.css")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "readiness-card" not in html
    assert "hero-visual" not in html
    assert ".ui-v4-foundation #home .readiness-card" not in foundation
    assert ".ui-v4-work-hero .hero-visual" not in dashboard
    assert ".ui-v4-dashboard-hidden" not in dashboard


def test_foundation_leaves_topbar_navigation_typography_to_navigation_layer() -> None:
    foundation = read("ui-v4-foundation.css")
    navigation = read("ui-v4-navigation.css")

    assert ".ui-v4-foundation .topbar .track" not in foundation
    assert ".ui-v4-foundation .topbar h2 {\n  font-size: clamp" not in foundation
    assert ".ui-v4-navigation .topbar .track" in navigation
    assert ".ui-v4-navigation .topbar h2" in navigation

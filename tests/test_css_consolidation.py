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


def test_base_stylesheet_only_owns_shared_business_primitives() -> None:
    base = read("style.css")

    forbidden = (
        "\n.shell {",
        "\n.sidebar {",
        "\n.brand {",
        "\n.nav {",
        "tool-status-card",
        "tool-status-item",
        ".api-panel",
        ".topbar {",
        ".top-actions",
        ".overview-panel",
        ".hero-card",
        ".hero-visual",
        ".module-grid",
        ".module-card",
        ".governance-card",
        ".recent-card",
        ".identity-chip",
        ".top-status",
        "hero-enterprise-ai.png",
    )
    for selector in forbidden:
        assert selector not in base, selector

    required = (
        ".form-grid {",
        ".quick-fill-bar {",
        ".button-row {",
        ".content-card,\n.result-panel,\n.report-card {",
        ".result-panel {",
        ".report-grid {",
        ".modal-backdrop {",
        ".toast {",
    )
    for selector in required:
        assert selector in base, selector

    assert len(base.splitlines()) < 500


def test_dashboard_owns_all_home_layout_primitives_after_base_cleanup() -> None:
    dashboard = read("ui-v4-dashboard.css")

    for marker in (
        ".ui-v4-dashboard #home .overview-panel {\n  display: grid;",
        ".ui-v4-dashboard #home .ui-v4-work-hero {\n  position: relative;",
        "padding: 0;",
        ".ui-v4-dashboard #home .module-grid {\n  display: grid;",
        ".ui-v4-dashboard #home .module-card {",
        "display: flex;\n  flex-direction: column;",
        ".ui-v4-dashboard #home .module-footer {",
        ".ui-v4-dashboard #home .recent-list { display: grid; gap: 10px; }",
        ".ui-v4-dashboard #home .ui-v4-safety-strip {\n  display: grid;",
        "grid-template-columns: 310px minmax(0, 1fr);",
        ".ui-v4-dashboard #home .ui-v4-recent-panel,\n.ui-v4-dashboard #home .ui-v4-usage-panel {",
        "margin: 0;",
    ):
        assert marker in dashboard, marker


def test_shell_and_dashboard_assets_no_longer_depend_on_legacy_hero_image() -> None:
    base = read("style.css")
    dashboard = read("ui-v4-dashboard.css")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "hero-enterprise-ai.png" not in base
    assert "hero-enterprise-ai.png" not in dashboard
    assert "hero-enterprise-ai.png" not in html
    assert not (ASSETS / "hero-enterprise-ai.png").exists()

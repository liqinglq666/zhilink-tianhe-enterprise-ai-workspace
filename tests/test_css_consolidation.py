from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_shell_is_the_only_navigation_and_project_context_stylesheet_owner() -> None:
    shell = read("ui-v4-shell.css")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    shell_js = read("ui-v4-shell.js")

    assert not (ASSETS / "ui-v4-navigation.css").exists()
    assert "ui-v4-navigation.css" not in html
    assert "data-ui-v4-navigation" not in html
    assert "ui-v4-navigation" not in html
    assert "ui-v4-navigation.css" not in shell_js

    for marker in (
        ".ui-v4-shell .nav > .nav-group-label:first-child",
        ".ui-v4-shell .ui-v4-nav-label",
        ".ui-v4-shell .ui-v4-resource-button",
        ".ui-v4-shell .ui-v4-project-context",
        ".ui-v4-shell .ui-v4-project-meta",
        ".ui-v4-shell .topbar .track",
        ".ui-v4-shell .topbar h2",
    ):
        assert marker in shell, marker


def test_shell_keeps_desktop_sidebar_refinement_out_of_mobile_drawer() -> None:
    shell = read("ui-v4-shell.css")

    assert "@media (min-width: 1021px) and (max-width: 1240px)" in shell
    assert ".ui-v4-shell .shell { grid-template-columns: 236px minmax(0, 1fr); }" in shell
    assert ".ui-v4-shell .sidebar { width: 236px; }" in shell
    assert "@media (max-width: 1020px)" in shell
    assert "width: min(300px, 86vw);" in shell


def test_workspace_sticky_offset_is_desktop_only_and_owned_by_shell() -> None:
    shell = read("ui-v4-shell.css")
    workspace = read("ui-v4-workspace.css")

    assert "@media (min-width: 1181px)" in shell
    assert ".ui-v4-shell.ui-v4-workspace .ui-v4-workspace-page > .ui-v4-input-pane" in shell
    assert "top: 88px;" in shell
    assert "max-height: calc(100vh - 102px);" in shell

    assert "@media (max-width: 1180px)" in workspace
    assert "position: relative; top: auto; max-height: none;" in workspace


def test_deleted_native_v4_dom_does_not_keep_compatibility_css() -> None:
    foundation = read("ui-v4-foundation.css")
    dashboard = read("ui-v4-dashboard.css")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "readiness-card" not in html
    assert "hero-visual" not in html
    assert ".ui-v4-foundation #home .readiness-card" not in foundation
    assert ".ui-v4-work-hero .hero-visual" not in dashboard
    assert ".ui-v4-dashboard-hidden" not in dashboard


def test_foundation_leaves_topbar_navigation_typography_to_shell() -> None:
    foundation = read("ui-v4-foundation.css")
    shell = read("ui-v4-shell.css")

    assert ".ui-v4-foundation .topbar .track" not in foundation
    assert ".ui-v4-foundation .topbar h2 {\n  font-size: clamp" not in foundation
    assert ".ui-v4-shell .topbar .track" in shell
    assert ".ui-v4-shell .topbar h2" in shell


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

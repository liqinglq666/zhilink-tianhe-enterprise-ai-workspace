from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_shell_only_owns_workspace_chrome_not_business_content() -> None:
    shell = read("ui-v4-shell.css")

    for forbidden in (
        ".ui-v4-shell .ui-v4-business-page.active-page",
        ".ui-v4-shell .ui-v4-module-meta",
        ".ui-v4-shell .section-head > span svg",
        ".ui-v4-shell .ui-v4-module-icon svg",
        ".ui-v4-shell .module-footer button svg",
        ".ui-v4-shell .sticky-actions .primary svg",
    ):
        assert forbidden not in shell, forbidden


def test_workspace_owns_business_meta_and_primary_action_icons() -> None:
    workspace = read("ui-v4-workspace.css")

    for required in (
        ".ui-v4-workspace .ui-v4-business-page.active-page { min-width: 0; }",
        ".ui-v4-workspace .ui-v4-input-pane .ui-v4-module-meta {",
        "display: flex;",
        "flex-wrap: wrap;",
        ".ui-v4-workspace .ui-v4-input-pane .ui-v4-module-meta span {",
        "display: inline-flex;",
        ".ui-v4-workspace .ui-v4-input-pane .section-head > span svg { width: 21px; height: 21px; }",
        ".ui-v4-workspace .ui-v4-input-pane .sticky-actions .primary svg { width: 15px; height: 15px; margin-left: 5px; }",
    ):
        assert required in workspace, required


def test_dashboard_owns_home_card_icons_and_action_arrows() -> None:
    dashboard = read("ui-v4-dashboard.css")

    assert ".ui-v4-dashboard #home .ui-v4-module-icon svg { width: 20px; height: 20px; }" in dashboard
    assert ".ui-v4-dashboard #home .module-footer button svg { width: 15px; height: 15px; margin-left: 5px; }" in dashboard


def test_shell_javascript_keeps_decoration_behavior_while_css_is_delegated() -> None:
    shell_js = read("ui-v4-shell.js")

    assert 'meta.className = "ui-v4-module-meta"' in shell_js
    assert 'holder.classList.add("ui-v4-module-icon")' in shell_js
    assert 'button.insertAdjacentHTML("beforeend", ICONS.arrow)' in shell_js

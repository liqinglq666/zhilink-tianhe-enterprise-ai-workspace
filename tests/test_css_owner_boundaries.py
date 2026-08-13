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


def test_javascript_owners_match_css_owners() -> None:
    shell = read("ui-v4-shell.js")
    workspace = read("ui-v4-workspace.js")
    dashboard = read("ui-v4-dashboard.js")
    runtime = read("ui-v4-runtime.js")

    for forbidden in (
        "function decorateBusinessPages",
        "function decorateHomeCards",
        "function ensureHomePanels",
        "function renderPending",
        "function renderUsage",
        'meta.className = "ui-v4-module-meta"',
        'classList.add("ui-v4-module-icon")',
        "contracts.resultKeys",
        "contracts.resultTitles",
    ):
        assert forbidden not in shell, forbidden

    for required in (
        'meta.className = "ui-v4-module-meta"',
        'button.insertAdjacentHTML("beforeend", ICONS.arrow)',
        'result.setAttribute("aria-label", shared.resultLabel)',
        "ICONS[shared.icon]",
    ):
        assert required in workspace, required

    assert "function ensureHomePanels" not in dashboard
    assert "document.createElement" not in dashboard
    for required in (
        "function decorateHomeCards",
        "function renderPending",
        "function renderUsage",
        'holder.classList.add("ui-v4-module-icon")',
        'button.insertAdjacentHTML("beforeend", ICONS.arrow)',
        "ZHILINK_UI_V4_SHELL?.projectCount?.()",
        "const MODULE_ORDER = contracts.moduleOrder",
    ):
        assert required in dashboard, required

    assert "const modules = Object.freeze({" in runtime
    assert "const icons = Object.freeze({" in runtime
    assert "window.ZHILINK_UI_V4_ICONS = icons" in runtime
    assert "window.ZHILINK_UI_V4_ICONS_READY = true" in runtime
    for source in (shell, workspace, dashboard):
        assert '<svg viewBox="0 0 24 24"' not in source
        assert "window.ZHILINK_UI_V4_ICONS" in source

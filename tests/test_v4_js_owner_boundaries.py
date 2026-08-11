from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_runtime_is_the_only_shared_svg_catalog() -> None:
    runtime = read("ui-v4-runtime.js")
    shell = read("ui-v4-shell.js")
    workspace = read("ui-v4-workspace.js")
    dashboard = read("ui-v4-dashboard.js")

    assert "const icons = Object.freeze({" in runtime
    assert "window.ZHILINK_UI_V4_ICONS = icons" in runtime
    assert "window.ZHILINK_UI_V4_ICONS_READY = true" in runtime
    for source in (shell, workspace, dashboard):
        assert "window.ZHILINK_UI_V4_ICONS" in source
        assert '<svg viewBox="0 0 24 24"' not in source


def test_shell_does_not_own_business_or_dashboard_presentation() -> None:
    shell = read("ui-v4-shell.js")
    for forbidden in (
        "decorateBusinessPages",
        "decorateHomeCards",
        "ensureHomePanels",
        "renderPending",
        "renderUsage",
        "uiV4PendingPanel",
        "uiV4UsagePanel",
        "contracts.resultKeys",
        "contracts.resultTitles",
        'meta.className = "ui-v4-module-meta"',
    ):
        assert forbidden not in shell, forbidden


def test_workspace_and_dashboard_own_their_decoration() -> None:
    workspace = read("ui-v4-workspace.js")
    dashboard = read("ui-v4-dashboard.js")

    for required in (
        'meta.className = "ui-v4-module-meta"',
        'result.setAttribute("aria-label", config.resultLabel)',
        'button.insertAdjacentHTML("beforeend", ICONS.arrow)',
    ):
        assert required in workspace, required

    for required in (
        "function decorateHomeCards",
        "function ensureHomePanels",
        "function renderPending",
        "function renderUsage",
        "ZHILINK_UI_V4_SHELL?.projectCount?.()",
    ):
        assert required in dashboard, required

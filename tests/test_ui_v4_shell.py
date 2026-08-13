from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_is_consolidated_v4_and_preserves_business_layers() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION == "2026-08-11-ui-v4-fetch-hooks-v11"

    required = [
        "ZHILINK_WORKSPACE_CONTRACTS_READY",
        "ZHILINK_UI_V4_ICONS_READY",
        "ZHILINK_WORKSPACE_HOOKS_READY",
        "ZHILINK_RESULT_EVENTS_READY",
        "ZHILINK_UI_V4_RUNTIME_READY",
        "ZHILINK_EXAMPLE_LOADER_READY",
        "ZHILINK_DATA_PROVENANCE_READY",
        "ZHILINK_UI_V4_SHELL_READY",
        "ZHILINK_API_DRAWER_V4_READY",
        "ZHILINK_MODEL_CONFIG_SAVE_V4_READY",
        "ZHILINK_MEETING_USER_VIEW_READY",
        "ZHILINK_UI_V4_FOUNDATION_READY",
        "ZHILINK_UI_V4_DASHBOARD_READY",
        "ZHILINK_UI_V4_WORKSPACE_READY",
        "ZHILINK_UI_V4_OVERLAYS_READY",
        "ZHILINK_UI_V4_STATES_READY",
        "ZHILINK_UI_V4_FORMS_READY",
        "ZHILINK_UI_V4_RESULTS_READY",
        "ZHILINK_UI_V4_FINAL_QA_READY",
    ]
    for marker in required:
        assert marker in response.text

    positions = [response.text.rfind(marker) for marker in required]
    assert positions == sorted(positions)

    for removed_marker in (
        "ZHILINK_UI_REDESIGN_LIVE_READY",
        "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY",
        "ZHILINK_UI_V3_READY",
        "ZHILINK_UI_V2_READY",
        "ZHILINK_UI_V4_NAVIGATION_READY",
        "ZHILINK_SIMPLE_UI_READY",
        "ZHILINK_DATA_PROVENANCE_V2_READY",
    ):
        assert removed_marker not in response.text


def test_replaced_ui_layers_and_fake_preview_assets_are_deleted() -> None:
    removed = (
        "ui-redesign-live.js",
        "ui-redesign-live.css",
        "ui-redesign-live-fixes.js",
        "ui-v3-clean.js",
        "ui-v3-clean.css",
        "ui-v2-dashboard.js",
        "ui-v2-dashboard.css",
        "ui-v4-navigation-compat.css",
        "ui-v4-navigation.js",
        "ui-v4-navigation.css",
        "product-simplification.js",
        "product-simplification.css",
        "data-provenance-guard-v2.js",
        "result-events.js",
        "workspace-hooks.js",
        "ui-preview.html",
        "ui-preview.css",
        "ui-preview.js",
    )
    for filename in removed:
        assert not (ASSETS / filename).exists(), filename

    with TestClient(app) as client:
        preview = client.get("/preview")
    assert preview.status_code == 404


def test_native_index_owns_workspace_chrome_before_javascript_runs() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for required in (
        'id="uiV4WorkspaceGroup"',
        'id="uiV4MobileMenu"',
        'id="uiV4TopNav"',
        'id="uiV4ProjectContext"',
        'id="uiV4AccountToggle"',
        'id="uiV4SidebarRecent"',
        'id="uiV4ResourceNavigation"',
        'id="uiV4MobileBackdrop"',
        'id="uiV4PendingPanel"',
        'id="uiV4HomeGrid"',
        'id="uiV4UsagePanel"',
        'id="apiPanel" class="api-panel api-drawer-v4"',
    ):
        assert required in html
    assert "tool-status-card" not in html
    assert "readiness-card" not in html
    assert "hero-visual" not in html
    assert 'data-tool-key="report"' not in html
    assert "ui-v4-navigation.css" not in html
    assert "ui-v4-navigation" not in html


def test_v4_shell_owns_only_navigation_project_and_account_context() -> None:
    script = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-shell.css").read_text(encoding="utf-8")

    assert "ZHILINK_UI_V4_SHELL_READY" in script
    assert "window.ZHILINK_WORKSPACE_CONTRACTS" in script
    assert "window.ZHILINK_UI_V4_ICONS" in script
    assert "contracts.storage.currentProject" in script
    assert "contracts.storage.workspaceKey" in script
    assert "const MODULES = contracts.modules" in script
    assert "const MODULES = {" not in script
    assert "contracts.resultKeys" not in script
    assert "contracts.resultTitles" not in script
    assert 'document.body.classList.add("ui-v4-shell")' in script
    assert "function syncSidebarPresentation" in script
    assert "uiV4ProjectContext" in script
    assert "uiV4KnowledgeNav" in script
    assert "uiV4ResourceNavigation" not in script
    assert 'triggerExisting("openProjectManager")' in script
    assert 'triggerExisting("openServiceWorkflow")' in script
    assert "projectCount: () => Number(latestProjects.total || 0)" in script
    assert "projects-refreshed" in script
    for forbidden in (
        "ensureTopNavigation",
        "ensureSidebarSupport",
        "document.createElement",
        "decorateBusinessPages",
        "decorateHomeCards",
        "ensureHomePanels",
        "renderPending",
        "renderUsage",
        "uiV4PendingPanel",
        "uiV4UsagePanel",
        "ui-v4-navigation.css",
    ):
        assert forbidden not in script
    assert ".ui-v4-shell .shell" in stylesheet
    assert ".ui-v4-shell .ui-v4-project-context" in stylesheet
    assert ".ui-v4-shell .ui-v4-resource-navigation" in stylesheet
    assert ".ui-v4-shell .topbar .track" in stylesheet
    assert "@media (min-width: 1181px)" in stylesheet
    assert "top: 88px;" in stylesheet


def test_v4_presentation_layers_do_not_reintroduce_legacy_names() -> None:
    files = (
        "ui-v4-runtime.js",
        "ui-v4-shell.js",
        "ui-v4-foundation.js",
        "ui-v4-dashboard.js",
        "ui-v4-workspace.js",
        "ui-v4-overlays.js",
        "ui-v4-states.js",
        "ui-v4-forms.js",
        "ui-v4-results.js",
        "ui-v4-final-qa.js",
    )
    for filename in files:
        content = (ASSETS / filename).read_text(encoding="utf-8")
        for forbidden in ("ui-redesign-live", "ui-v3-clean", "liveTopNav", "liveAccountToggle", "product-simplification"):
            assert forbidden not in content, f"{forbidden} leaked into {filename}"


def test_dashboard_keeps_task_first_information_architecture() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    script = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    assert "今天要处理什么？" in html
    assert "新建任务" in html
    assert "需要你处理" in html
    assert "最近材料" in html
    assert "工作状态" in html
    assert "企业档案与实施计划作为辅助能力" in html
    assert 'class="ui-v4-home-panel ui-v4-attention-panel"' in html
    assert 'class="module-card ui-v4-secondary-task" data-goto="profile"' in html
    assert 'class="module-card ui-v4-secondary-task" data-goto="landing"' in html
    assert 'id="uiV4HomeGrid" class="ui-v4-home-grid ui-v4-secondary-grid"' in html
    assert 'class="recent-card ui-v4-recent-panel"' in html
    assert 'id="uiV4UsagePanel" class="ui-v4-home-panel ui-v4-usage-panel"' in html
    assert 'class="governance-card ui-v4-safety-strip" aria-label="使用边界"' in html
    assert 'data-tool-key="meeting"' in html
    assert 'data-tool-key="contract"' in html
    assert 'data-tool-key="policy"' in html
    assert 'data-tool-key="match"' in html
    assert 'data-tool-key="report"' not in html
    assert "function decorateHomeCards" in script
    assert "function decorateHero" in script
    assert "function renderPending" in script
    assert "function renderUsage" in script
    assert "const MODULES = contracts.modules" in script
    assert "const MODULE_ORDER = contracts.moduleOrder" in script
    assert 'const MODULE_ORDER = ["meeting"' not in script
    assert 'key === "landing" ? "plan" : key' not in script
    assert "ZHILINK_UI_V4_SHELL?.projectCount?.()" in script
    for forbidden in (
        "function ensureHomePanels",
        "function arrangeAttentionPanel",
        "function decorateTaskSection",
        "function decorateLowerPanels",
        "function simplifyGovernance",
        'hero.classList.add("ui-v4-work-hero")',
        "document.createElement",
    ):
        assert forbidden not in script


def test_workspace_keeps_split_workbench_semantics_and_business_decoration() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    script = (ASSETS / "ui-v4-workspace.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-workspace.css").read_text(encoding="utf-8")

    assert "ui-v4-workspace" in html
    for module_id in ("profile", "meeting", "contract", "policy", "match", "landing", "report"):
        assert f'id="{module_id}" class="page ui-v4-business-page"' in html

    assert 'page.classList.add("ui-v4-workspace-page")' in script
    assert 'page.classList.add("ui-v4-workspace-page", "ui-v4-business-page")' not in script
    assert 'document.body.classList.add("ui-v4-workspace")' not in script
    assert "uiV4PaneLabel" not in script
    assert "uiV4ResultState" not in script
    assert 'emptyTitle: "会议纪要将在这里生成"' in script
    assert "const SHARED_MODULES = contracts.modules" in script
    assert "const WORKSPACE_MODULES = {" in script
    assert "resultLabel:" not in script
    assert 'meta.className = "ui-v4-module-meta"' in script
    assert 'result.setAttribute("aria-label", shared.resultLabel)' in script
    assert "ICONS[shared.icon]" in script
    assert 'button.insertAdjacentHTML("beforeend", ICONS.arrow)' in script
    assert "grid-template-columns: minmax(360px, .78fr) minmax(520px, 1.22fr)" in stylesheet
    assert "@media (max-width: 1180px)" in stylesheet


def test_runtime_is_the_single_shared_v4_icon_catalog() -> None:
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")
    assert "const icons = Object.freeze({" in runtime
    assert "window.ZHILINK_UI_V4_ICONS = icons" in runtime
    assert "window.ZHILINK_UI_V4_ICONS_READY = true" in runtime
    for filename in ("ui-v4-shell.js", "ui-v4-workspace.js", "ui-v4-dashboard.js"):
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "window.ZHILINK_UI_V4_ICONS" in source
        assert '<svg viewBox="0 0 24 24"' not in source

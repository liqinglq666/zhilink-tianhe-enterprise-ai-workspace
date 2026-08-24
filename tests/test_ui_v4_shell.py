from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_is_one_consolidated_v4_runtime() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION

    core_runtime = (
        "ZHILINK_WORKSPACE_CONTRACTS_READY",
        "ZHILINK_WORKSPACE_HOOKS_READY",
        "ZHILINK_RESULT_EVENTS_READY",
        "ZHILINK_UI_V4_RUNTIME_READY",
    )
    consumers = (
        "ZHILINK_EXAMPLE_LOADER_READY",
        "ZHILINK_DATA_PROVENANCE_READY",
        "ZHILINK_UI_V4_SHELL_READY",
        "ZHILINK_API_DRAWER_V4_READY",
        "ZHILINK_MODEL_CONFIG_SAVE_V4_READY",
        "ZHILINK_MEETING_USER_VIEW_READY",
        "ZHILINK_UI_V4_DASHBOARD_READY",
        "ZHILINK_UI_V4_OVERLAYS_READY",
        "ZHILINK_UI_V4_STATES_READY",
        "ZHILINK_UI_V4_FORMS_READY",
        "ZHILINK_UI_V4_RESULTS_READY",
        "ZHILINK_UI_V4_FINAL_QA_READY",
    )
    storage_position = response.text.index("ZHILINK_STORAGE_RECOVERY")
    core_positions = [response.text.index(marker) for marker in core_runtime]
    consumer_positions = [response.text.index(marker) for marker in consumers]
    assert storage_position < min(core_positions)
    assert max(core_positions) < min(consumer_positions)
    assert consumer_positions == sorted(consumer_positions)

    for legacy in (
        "ZHILINK_UI_REDESIGN_LIVE_READY",
        "ZHILINK_UI_V3_READY",
        "ZHILINK_UI_V2_READY",
        "ZHILINK_SIMPLE_UI_READY",
        "ZHILINK_DATA_PROVENANCE_V2_READY",
        "ZHILINK_UI_V4_FOUNDATION_READY",
        "ZHILINK_UI_V4_WORKSPACE_READY",
    ):
        assert legacy not in response.text


def test_replaced_ui_layers_and_fake_preview_are_deleted() -> None:
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
        "ui-v4-foundation.js",
        "ui-v4-workspace.js",
        "saas-product-polish-v3.js",
        "saas-product-polish-v3.css",
        "release-polish-v4.css",
        "enterprise-user-view-guards.js",
    )
    assert all(not (ASSETS / filename).exists() for filename in removed)
    assert "ui-v4-workspace.js" not in UI_SCRIPTS
    with TestClient(app) as client:
        assert client.get("/preview").status_code == 404


def test_native_index_owns_core_workspace_chrome_before_javascript() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for required in (
        'id="uiV4MobileMenu"',
        'id="uiV4TopNav"',
        'id="uiV4ProjectContext"',
        'id="uiV4AccountToggle"',
        'id="uiV4SidebarRecent"',
        'id="uiV4ResourceNavigation"',
        'id="uiV4MobileBackdrop"',
        'id="uiV4PendingPanel"',
        'id="uiV4UsagePanel"',
        'id="apiPanel" class="api-panel api-drawer-v4"',
    ):
        assert required in html
    assert "ui-v4-navigation" not in html
    assert "hero-visual" not in html


def test_v4_shell_uses_shared_runtime_contracts_without_recreating_business_state() -> None:
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    dashboard = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    final_qa = (ASSETS / "ui-v4-final-qa.js").read_text(encoding="utf-8")

    assert "window.ZHILINK_WORKSPACE_CONTRACTS" in shell
    assert "window.ZHILINK_UI_V4_ICONS" in shell
    assert "contracts.storage.currentProject" in shell
    assert "contracts.storage.workspaceKey" in shell
    assert "const MODULES = contracts.modules" in shell
    assert "document.createElement" not in shell

    assert "const MODULES = contracts.modules" in dashboard
    assert "const MODULE_ORDER = contracts.moduleOrder" in dashboard
    assert "function renderPending" in dashboard
    assert "function renderUsage" in dashboard

    assert "const SHARED_MODULES = contracts.modules" in final_qa
    assert "function decorateBusinessWorkspace()" in final_qa
    assert 'document.querySelectorAll(".ui-v4-business-page[id]").forEach(page =>' in final_qa
    assert 'document.documentElement.dataset.zhilinkWorkspace = "v4"' in final_qa


def test_workspace_keeps_task_first_split_workbench_and_accessibility_contracts() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ASSETS / "ui-v4-workspace.css").read_text(encoding="utf-8")
    final_qa = (ASSETS / "ui-v4-final-qa.css").read_text(encoding="utf-8")

    for text in ("今天要处理什么？", "新建任务", "需要你处理", "最近材料", "工作状态"):
        assert text in html
    for module in ("profile", "meeting", "contract", "policy", "match", "landing", "report"):
        assert f'id="{module}" class="page ui-v4-business-page"' in html
    assert "grid-template-columns: minmax(360px, .78fr) minmax(520px, 1.22fr)" in css
    assert "@media (max-width: 1180px)" in css
    assert "@media (max-width: 390px)" in final_qa
    assert "@media (max-width: 360px)" in final_qa
    assert "@media (prefers-reduced-motion: reduce)" in final_qa

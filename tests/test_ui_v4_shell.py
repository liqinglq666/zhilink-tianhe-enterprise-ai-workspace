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
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION == "2026-08-11-ui-v4-hooks-v6"

    required = [
        "ZHILINK_RESULT_EVENTS_READY",
        "ZHILINK_DATA_PROVENANCE_READY",
        "ZHILINK_UI_V4_RUNTIME_READY",
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

    ordered = [
        "ZHILINK_RESULT_EVENTS_READY",
        "ZHILINK_DATA_PROVENANCE_READY",
        "ZHILINK_UI_V4_RUNTIME_READY",
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
    positions = [response.text.rfind(marker) for marker in ordered]
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
        "product-simplification.js",
        "product-simplification.css",
        "data-provenance-guard-v2.js",
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
        'id="uiV4TopNav"',
        'id="uiV4ProjectContext"',
        'id="uiV4AccountToggle"',
        'id="uiV4SidebarRecent"',
        'id="uiV4ResourceNavigation"',
        'id="uiV4PendingPanel"',
        'id="uiV4UsagePanel"',
        'id="apiPanel" class="api-panel api-drawer-v4"',
    ):
        assert required in html
    assert "tool-status-card" not in html
    assert "readiness-card" not in html
    assert "hero-visual" not in html
    assert 'data-tool-key="report"' not in html


def test_v4_shell_owns_navigation_project_context_and_dashboard_support() -> None:
    script = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-shell.css").read_text(encoding="utf-8")
    navigation_css = (ASSETS / "ui-v4-navigation.css").read_text(encoding="utf-8")

    assert "ZHILINK_UI_V4_SHELL_READY" in script
    assert 'document.body.classList.add("ui-v4-shell")' in script
    assert "uiV4TopNav" in script
    assert "uiV4ProjectContext" in script
    assert "uiV4ResourceNavigation" in script
    assert "uiV4PendingPanel" in script
    assert "uiV4UsagePanel" in script
    assert 'triggerExisting("openProjectManager")' in script
    assert 'triggerExisting("openServiceWorkflow")' in script
    assert ".ui-v4-shell .shell" in stylesheet
    assert ".ui-v4-project-context" in navigation_css
    assert ".ui-v4-resource-navigation" in navigation_css


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
    assert 'data-tool-key="meeting"' in html
    assert 'data-tool-key="contract"' in html
    assert 'data-tool-key="policy"' in html
    assert 'data-tool-key="match"' in html
    assert 'data-tool-key="report"' not in html
    assert "企业档案与实施计划作为辅助能力" in script


def test_workspace_keeps_split_workbench_semantics() -> None:
    script = (ASSETS / "ui-v4-workspace.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-workspace.css").read_text(encoding="utf-8")
    assert 'page.classList.add("ui-v4-workspace-page", "ui-v4-business-page")' in script
    assert 'result.dataset.uiV4ResultState = result.classList.contains("empty") ? "empty" : "ready"' in script
    assert 'emptyTitle: "会议纪要将在这里生成"' in script
    assert "grid-template-columns: minmax(360px, .78fr) minmax(520px, 1.22fr)" in stylesheet
    assert "@media (max-width: 1180px)" in stylesheet

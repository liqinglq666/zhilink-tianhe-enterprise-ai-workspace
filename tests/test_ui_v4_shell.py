from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_is_native_v4_and_preserves_business_layers() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-10-ui-v4-native-v3"

    required = [
        "ZHILINK_DATA_PROVENANCE_V2_READY",
        "ZHILINK_UI_V4_SHELL_READY",
        "ZHILINK_API_DRAWER_V4_READY",
        "ZHILINK_MEETING_USER_VIEW_READY",
        "ZHILINK_UI_V4_FOUNDATION_READY",
        "ZHILINK_UI_V4_DASHBOARD_READY",
        "ZHILINK_UI_V4_WORKSPACE_READY",
        "ZHILINK_UI_V4_NAVIGATION_READY",
        "ZHILINK_UI_V4_OVERLAYS_READY",
        "ZHILINK_UI_V4_STATES_READY",
    ]
    for marker in required:
        assert marker in response.text

    ordered = [
        "ZHILINK_UI_V4_SHELL_READY",
        "ZHILINK_API_DRAWER_V4_READY",
        "ZHILINK_MEETING_USER_VIEW_READY",
        "ZHILINK_UI_V4_FOUNDATION_READY",
        "ZHILINK_UI_V4_DASHBOARD_READY",
        "ZHILINK_UI_V4_WORKSPACE_READY",
        "ZHILINK_UI_V4_NAVIGATION_READY",
        "ZHILINK_UI_V4_OVERLAYS_READY",
        "ZHILINK_UI_V4_STATES_READY",
    ]
    positions = [response.text.rfind(marker) for marker in ordered]
    assert positions == sorted(positions)

    for removed_marker in (
        "ZHILINK_UI_REDESIGN_LIVE_READY",
        "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY",
        "ZHILINK_UI_V3_READY",
        "ZHILINK_UI_V2_READY",
    ):
        assert removed_marker not in response.text


def test_replaced_legacy_and_fake_preview_assets_are_deleted() -> None:
    removed = (
        "ui-redesign-live.js",
        "ui-redesign-live.css",
        "ui-redesign-live-fixes.js",
        "ui-v3-clean.js",
        "ui-v3-clean.css",
        "ui-v2-dashboard.js",
        "ui-v2-dashboard.css",
        "ui-v4-navigation-compat.css",
        "ui-preview.html",
        "ui-preview.css",
        "ui-preview.js",
    )
    for filename in removed:
        assert not (ASSETS / filename).exists(), filename

    with TestClient(app) as client:
        preview = client.get("/preview")
    assert preview.status_code == 404


def test_v4_shell_owns_workspace_chrome_without_legacy_names() -> None:
    script = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-shell.css").read_text(encoding="utf-8")

    assert "ZHILINK_UI_V4_SHELL_READY" in script
    assert 'document.body.classList.add("ui-v4-shell")' in script
    assert 'id="uiV4TopNav"' in script
    assert 'id="uiV4AccountToggle"' in script
    assert 'id="uiV4SidebarRecent"' in script
    assert 'id="uiV4PendingPanel"' in script
    assert 'id="uiV4UsagePanel"' in script
    assert 'page.classList.add("ui-v4-business-page")' in script
    assert ".ui-v4-shell .shell" in stylesheet
    assert ".ui-v4-sidebar-project" in stylesheet
    assert ".ui-v4-account-menu" in stylesheet
    assert "@media (max-width: 1020px)" in stylesheet

    for forbidden in ("ui-redesign-live", "ui-v3-clean", "liveTopNav", "liveAccount", "livePending", "liveUsage"):
        assert forbidden not in script
        assert forbidden not in stylesheet


def test_foundation_dashboard_workspace_and_navigation_use_v4_primitives_only() -> None:
    files = (
        "ui-v4-foundation.js",
        "ui-v4-foundation.css",
        "ui-v4-dashboard.js",
        "ui-v4-dashboard.css",
        "ui-v4-workspace.js",
        "ui-v4-workspace.css",
        "ui-v4-navigation.js",
        "ui-v4-navigation.css",
        "ui-v4-final-qa.js",
        "ui-v4-final-qa.css",
    )
    for filename in files:
        content = (ASSETS / filename).read_text(encoding="utf-8")
        for forbidden in ("ui-redesign-live", "ui-v3-clean", "liveTopNav", "liveAccountToggle", "liveSidebarProject"):
            assert forbidden not in content, f"{forbidden} leaked into {filename}"


def test_v4_dashboard_keeps_task_first_information_architecture() -> None:
    script = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-dashboard.css").read_text(encoding="utf-8")

    assert 'setText(title, "今天要处理什么？")' in script
    assert 'setText(pending.querySelector(".ui-v4-panel-head h3"), "需要你处理")' in script
    assert 'setText(toolbar.querySelector("h3"), "新建任务")' in script
    assert 'setText(recent.querySelector(".section-toolbar h3"), "最近材料")' in script
    assert 'setText(usage.querySelector(".ui-v4-panel-head h3"), "工作状态")' in script
    assert ".ui-v4-attention-panel" in stylesheet
    assert ".ui-v4-secondary-grid" in stylesheet
    for forbidden in ("98%", "节省时间", "提升 35%", "审核准确率", "效率提升"):
        assert forbidden not in script
        assert forbidden not in stylesheet


def test_v4_workspace_keeps_split_workbench_without_v3_grid_dependency() -> None:
    script = (ASSETS / "ui-v4-workspace.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-workspace.css").read_text(encoding="utf-8")

    assert 'page.classList.add("ui-v4-workspace-page", "ui-v4-business-page")' in script
    assert 'result.dataset.uiV4ResultState = result.classList.contains("empty") ? "empty" : "ready"' in script
    assert 'emptyTitle: "会议纪要将在这里生成"' in script
    assert "display: grid" in stylesheet
    assert "grid-template-columns: minmax(360px, .78fr) minmax(520px, 1.22fr)" in stylesheet
    assert '[data-ui-v4-module="meeting"]' in stylesheet
    assert "@media (max-width: 1180px)" in stylesheet


def test_navigation_uses_v4_shell_resources_and_project_context() -> None:
    script = (ASSETS / "ui-v4-navigation.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v4-navigation.css").read_text(encoding="utf-8")

    assert 'home: "工作首页"' in script
    assert 'report: "报告归档"' in script
    assert 'resource.id = "uiV4ResourceNavigation"' in script
    assert 'project.id = "uiV4ProjectContext"' in script
    assert 'document.getElementById("uiV4TopNav")' in script
    assert 'document.getElementById("uiV4MobileMenu")' in script
    assert "--ui4-sidebar-width: 252px" in stylesheet
    assert ".ui-v4-resource-navigation" in stylesheet
    assert ".ui-v4-project-context" in stylesheet
    assert "@media (max-width: 720px)" in stylesheet

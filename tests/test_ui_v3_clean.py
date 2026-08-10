from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_loads_meeting_user_view_after_ui_v3() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-10-ui-v4-final-v2"
    assert "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY" in response.text
    assert "ZHILINK_UI_V3_READY" in response.text
    assert "ZHILINK_MEETING_USER_VIEW_READY" in response.text
    assert "ZHILINK_UI_V4_FOUNDATION_READY" in response.text
    assert "ZHILINK_UI_V4_DASHBOARD_READY" in response.text
    assert "ZHILINK_UI_V4_WORKSPACE_READY" in response.text
    assert "ZHILINK_UI_V4_NAVIGATION_READY" in response.text
    assert "ZHILINK_UI_V4_OVERLAYS_READY" in response.text
    assert "ZHILINK_UI_V4_STATES_READY" in response.text
    assert response.text.rfind("ZHILINK_UI_V3_READY") > response.text.rfind(
        "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY"
    )
    assert response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY") > response.text.rfind("ZHILINK_UI_V3_READY")
    assert response.text.rfind("ZHILINK_UI_V4_FOUNDATION_READY") > response.text.rfind(
        "ZHILINK_MEETING_USER_VIEW_READY"
    )
    assert response.text.rfind("ZHILINK_UI_V4_DASHBOARD_READY") > response.text.rfind(
        "ZHILINK_UI_V4_FOUNDATION_READY"
    )
    assert response.text.rfind("ZHILINK_UI_V4_WORKSPACE_READY") > response.text.rfind(
        "ZHILINK_UI_V4_DASHBOARD_READY"
    )
    assert response.text.rfind("ZHILINK_UI_V4_NAVIGATION_READY") > response.text.rfind(
        "ZHILINK_UI_V4_WORKSPACE_READY"
    )
    assert response.text.rfind("ZHILINK_UI_V4_OVERLAYS_READY") > response.text.rfind(
        "ZHILINK_UI_V4_NAVIGATION_READY"
    )
    assert response.text.rfind("ZHILINK_UI_V4_STATES_READY") > response.text.rfind(
        "ZHILINK_UI_V4_OVERLAYS_READY"
    )


def test_ui_v3_assets_are_served() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v3-clean.js?v=20260806.2")
        stylesheet = client.get("/assets/ui-v3-clean.css?v=20260806.2")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ui-v3-clean-shell" in script.text
    assert ".page.ui-v3-business-page.active-page" in stylesheet.text


def test_ui_v4_foundation_assets_are_served_and_business_readable() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-foundation.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-foundation.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert 'document.body.classList.add("ui-v4-foundation")' in script.text
    assert "--ui4-radius" in stylesheet.text
    assert "font-size: 14px" in stylesheet.text
    assert "min-height: 44px" in stylesheet.text
    assert "ZHILINK_UI_V4_FOUNDATION_READY" in script.text

    # Foundation must not hide core controls or rewrite business behavior.
    for forbidden in ("display: none !important", "state.results", "fetch(", "sessionStorage", "localStorage"):
        assert forbidden not in stylesheet.text


def test_ui_v4_dashboard_prioritizes_real_work_over_marketing_chrome() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-dashboard.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-dashboard.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_DASHBOARD_READY" in script.text
    assert 'const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1"' in script.text
    assert 'setText(title, project.name || "当前项目")' in script.text
    assert 'setText(pending.querySelector(".live-panel-head h3"), "需要你处理")' in script.text
    assert 'setText(toolbar.querySelector("h3"), "新建任务")' in script.text
    assert 'setText(recent.querySelector(".section-toolbar h3"), "最近材料")' in script.text
    assert 'setText(usage.querySelector(".live-panel-head h3"), "工作状态")' in script.text
    assert "uiV4WorkSignature" in script.text
    assert ".hero-visual" in stylesheet.text
    assert "display: none !important" in stylesheet.text
    assert ".ui-v4-attention-panel" in stylesheet.text
    assert ".ui-v4-secondary-grid" in stylesheet.text

    # Dashboard copy must not invent success rates, time savings or fake business performance.
    for forbidden in ("98%", "节省时间", "提升 35%", "审核准确率", "效率提升"):
        assert forbidden not in script.text
        assert forbidden not in stylesheet.text


def test_ui_v4_workspace_assets_create_a_focused_split_workbench() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-workspace.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-workspace.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_WORKSPACE_READY" in script.text
    assert 'page.classList.add("ui-v4-workspace-page")' in script.text
    assert 'input.classList.add("ui-v4-input-pane")' in script.text
    assert 'result.classList.add("ui-v4-result-pane")' in script.text
    assert 'result.dataset.uiV4ResultState = result.classList.contains("empty") ? "empty" : "ready"' in script.text
    assert 'emptyTitle: "会议纪要将在这里生成"' in script.text
    assert 'emptyCopy: "粘贴会议记录或录音转写文本，然后点击“生成会议纪要”。"' in script.text

    assert "grid-template-columns: minmax(360px, .78fr) minmax(520px, 1.22fr)" in stylesheet.text
    assert ".ui-v4-result-pane:not(.empty)::before" in stylesheet.text
    assert ".ui-v4-result-pane .result-header" in stylesheet.text
    assert "content: attr(data-ui-v4-empty-title)" in stylesheet.text
    assert "min-height: 360px" in stylesheet.text
    assert "@media (max-width: 1180px)" in stylesheet.text

    # This layer may decorate DOM and observe result state, but must not alter model calls or persisted business data.
    for forbidden in ("fetch(", "setResult", "state.results", "sessionStorage", "localStorage", "saveConfig"):
        assert forbidden not in script.text


def test_ui_v4_navigation_consolidates_header_actions_and_sidebar_resources() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-navigation.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-navigation.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_NAVIGATION_READY" in script.text
    assert 'const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1"' in script.text
    assert 'home: "工作首页"' in script.text
    assert 'report: "报告归档"' in script.text
    assert 'group.textContent = "工作台"' in script.text
    assert 'resource.className = "ui-v4-resource-navigation"' in script.text
    assert 'project.id = "uiV4ProjectContext"' in script.text
    assert '["liveProjectNav", "liveKnowledgeNav", "liveReportNav"]' in script.text
    assert 'classList.add("ui-v4-top-redundant")' in script.text
    assert 'setText(meta, dirty ? "未保存"' in script.text
    assert 'setText(kicker, group)' in script.text

    assert ".ui-v4-top-redundant" in stylesheet.text
    assert "display: none !important" in stylesheet.text
    assert ".ui-v4-project-context" in stylesheet.text
    assert ".ui-v4-resource-navigation" in stylesheet.text
    assert ".ui-v4-account-menu" in stylesheet.text
    assert "--ui4-sidebar-width: 252px" in stylesheet.text
    assert "@media (max-width: 720px)" in stylesheet.text
    assert "display: grid !important" in stylesheet.text

    # Navigation can read the current project and trigger existing controls, but cannot own business/model state.
    for forbidden in ("fetch(", "setResult", "state.results", "saveConfig", "sessionStorage"):
        assert forbidden not in script.text


def test_ui_v3_preserves_all_primary_module_ids_and_adds_scalable_icons() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")

    for module in ("profile", "meeting", "contract", "policy", "match", "landing", "report"):
        assert f"{module}: {{" in script
        assert "document.getElementById(id)" in script

    assert "<svg viewBox=" in script
    assert "人工复核后使用" in script
    assert "结果可归档" in script
    assert "innerHTML = config.icon" in script


def test_ui_v3_disables_the_legacy_fixed_shell_before_enabling_grid_layout() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")

    remove_marker = 'document.body.classList.remove("ui-redesign-live")'
    add_marker = 'document.body.classList.add("ui-v3-clean-shell")'
    assert remove_marker in script
    assert add_marker in script
    assert script.index(remove_marker) < script.index(add_marker)


def test_ui_v3_replaces_legacy_visual_patterns_without_business_rewrites() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v3-clean.css").read_text(encoding="utf-8")

    assert 'document.body.classList.add("ui-v3-clean-shell")' in script
    assert ".tool-status-card { display: none !important; }" in stylesheet
    assert ".top-actions > :not(#liveTopNav)" in stylesheet
    assert ".ui-v3-business-page > .result-panel" in stylesheet
    assert ".quick-fill-btn" in stylesheet
    assert ".sticky-actions" in stylesheet

    # V3 must not introduce fabricated performance or business metrics.
    for forbidden in ("98%", "节省时间", "提升 35%", "审核准确率"):
        assert forbidden not in script
        assert forbidden not in stylesheet

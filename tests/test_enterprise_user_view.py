from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"
INDEX = ROOT / "frontend" / "index.html"


def test_enterprise_customer_view_translates_only_remaining_global_ui() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")

    for expected in (
        "AI 服务设置",
        "高级连接设置",
        "平台 AI 服务已就绪",
        "仅导出业务内容",
        "智能辅助整理",
        "清除这些内容",
    ):
        assert expected in source


def test_account_and_project_customer_copy_is_owned_by_source_modules() -> None:
    enterprise = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")
    account = (ASSETS / "account-access.js").read_text(encoding="utf-8")
    project = (ASSETS / "project-storage.js").read_text(encoding="utf-8")

    for expected in (
        "账户与组织",
        "账户、组织与成员",
        "本机工作区",
        "将本机项目移入当前组织",
        "当前暂不支持密码找回和邮件邀请，请妥善保管登录信息。",
    ):
        assert expected in account

    for expected in (
        "项目管理",
        "项目与历史版本",
        "保存项目后会记录当前工作内容和历史版本",
        "项目保存在当前工作空间。",
        "当前未打开项目",
        "业务结果",
        "恢复操作只恢复业务材料",
    ):
        assert expected in project

    for obsolete in (
        "decorateAccount",
        "decorateProjectManager",
        "账户、组织与成员",
        "本机工作区",
        "项目与历史版本",
    ):
        assert obsolete not in enterprise

    for technical_copy in (
        "组织空间与角色权限",
        "匿名浏览器工作区",
        "当前仍在匿名浏览器工作区",
        "本浏览器匿名项目",
    ):
        assert technical_copy not in account

    for technical_copy in (
        "项目存储请求超时",
        "当前未打开持久化项目",
        "项目按当前浏览器工作区隔离",
        "浏览器工作区密钥只保存在本机",
        'rows.push(["AI 结果"',
        "恢复操作只恢复业务快照",
    ):
        assert technical_copy not in project


def test_enterprise_view_keeps_advanced_model_controls_but_collapses_them_for_normal_users() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")
    css = (ASSETS / "enterprise-user-view.css").read_text(encoding="utf-8")

    assert 'details.id = "enterpriseAdvancedAiSettings"' in source
    assert 'summary.textContent = "高级连接设置"' in source
    assert 'details.open = mode === "custom" || mode === "unconfigured"' in source
    assert ".enterprise-ai-advanced" in css
    assert "普通用户无需修改" in source


def test_enterprise_view_does_not_patch_service_workflow_or_duplicate_runtime_scheduler() -> None:
    enterprise = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")
    service = (ASSETS / "service-workflow.js").read_text(encoding="utf-8")
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")

    for obsolete in (
        "fixServiceDialogTitleId",
        "decorateServiceWorkflow",
        "interceptServiceContextPrompt",
        "TECH_CODE_RE",
        "STATUS_LABELS",
        "ACTION_LABELS",
        "ROLE_LABELS",
    ):
        assert obsolete not in enterprise

    assert 'aria-labelledby="swDialogTitle"' in service
    assert '<h2 id="swDialogTitle">事项进度与责任协作</h2>' in service
    assert "new MutationObserver" not in enterprise
    assert "new MutationObserver" in runtime
    assert "ZHILINK_UI_V4_RUNTIME?.subscribe" in enterprise


def test_enterprise_view_owns_user_toast_rewrites_without_extra_guard_file() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")

    assert not (ASSETS / "enterprise-user-view-guards.js").exists()
    assert "enterprise-user-view-guards.js" not in UI_SCRIPTS
    assert "AI 服务设置已保存" in source
    assert "平台 AI 服务" in source
    assert "示例内容仅供体验" in source
    assert "window.toast = wrapped" in source


def test_enterprise_styles_load_statically_instead_of_runtime_injection() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")

    assert 'href="/assets/enterprise-user-view.css?v=20260824.1"' in html
    assert 'data-enterprise-user-view="true"' in html
    assert "STYLE_URL" not in source
    assert "ensureStyles" not in source
    assert 'document.createElement("link")' not in source
    assert '.rel = "stylesheet"' not in source


def test_enterprise_customer_layer_is_delivered_after_results_and_before_final_qa() -> None:
    routes = ROUTES.read_text(encoding="utf-8")

    assert routes.index('"ui-v4-results.js"') < routes.index('"enterprise-user-view.js"')
    assert routes.index('"enterprise-user-view.js"') < routes.index('"ui-v4-final-qa.js"')
    assert '"enterprise-user-view-guards.js"' not in routes

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")

    assert bundle.status_code == 200
    assert "ZHILINK_ENTERPRISE_USER_VIEW_GUARDS_READY" not in bundle.text
    assert "ZHILINK_ENTERPRISE_USER_VIEW_READY" in bundle.text
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION

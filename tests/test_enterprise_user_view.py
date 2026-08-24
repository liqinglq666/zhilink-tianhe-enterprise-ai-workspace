from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"
INDEX = ROOT / "frontend" / "index.html"


def test_enterprise_customer_view_translates_technical_ui_into_business_copy() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")

    for expected in (
        "AI 服务设置",
        "高级连接设置",
        "平台 AI 服务已就绪",
        "账户、组织与成员",
        "本机工作区",
        "项目与历史版本",
        "事项进度与责任协作",
        "仅导出业务内容",
        "智能辅助整理",
        "清除这些内容",
    ):
        assert expected in source

    assert 'label.hidden = true' in source
    assert 'if (/SHA-256|上下文\\s*SHA/i.test(item.textContent)) item.remove();' in source
    assert "TECH_CODE_RE.test(code.textContent.trim())" in source
    assert 'item.remove();' in source
    assert "interceptServiceContextPrompt" in source


def test_enterprise_view_keeps_advanced_model_controls_but_collapses_them_for_normal_users() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")
    css = (ASSETS / "enterprise-user-view.css").read_text(encoding="utf-8")

    assert 'details.id = "enterpriseAdvancedAiSettings"' in source
    assert 'summary.textContent = "高级连接设置"' in source
    assert 'details.open = mode === "custom" || mode === "unconfigured"' in source
    assert ".enterprise-ai-advanced" in css
    assert "普通用户无需修改" in source


def test_enterprise_view_owns_dom_guard_and_user_toast_rewrites() -> None:
    source = (ASSETS / "enterprise-user-view.js").read_text(encoding="utf-8")

    assert not (ASSETS / "enterprise-user-view-guards.js").exists()
    assert "enterprise-user-view-guards.js" not in UI_SCRIPTS
    assert 'title.id = "swDialogTitle"' in source
    assert 'dialog.setAttribute("aria-labelledby", "swDialogTitle")' in source
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

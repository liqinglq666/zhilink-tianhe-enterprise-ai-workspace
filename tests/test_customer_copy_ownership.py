from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION, UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
INDEX = ROOT / "frontend" / "index.html"


def test_global_customer_copy_is_native_html() -> None:
    html = INDEX.read_text(encoding="utf-8")

    for expected in (
        "AI 服务设置",
        "用于调整报告抬头、首页状态和生成内容中的业务视角。",
        "如：企业网页工作台，按组织权限使用，敏感业务原文按需脱敏",
        "如：生成结果由业务负责人或专业人员复核确认",
        "Word / Markdown / 文本",
        "导出范围",
        "仅导出业务内容",
        "导出文件仅包含业务材料，不包含 AI 服务设置。",
        "默认使用平台提供的 AI 服务；如企业有专属模型，可由管理员在设置中接入。",
    ):
        assert expected in html

    for implementation_copy in (
        "FastAPI网页应用",
        "不涉及注册登录",
        "MD / TXT / DOCX",
        "不含 API Key",
        "模型调用",
    ):
        assert implementation_copy not in html


def test_account_project_provenance_and_model_copy_are_source_owned() -> None:
    account = (ASSETS / "account-access.js").read_text(encoding="utf-8")
    project = (ASSETS / "project-storage.js").read_text(encoding="utf-8")
    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    model = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")
    model_css = (ASSETS / "model-config-save-v4.css").read_text(encoding="utf-8")

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

    for expected in (
        "有 ${keys.length} 项历史会话内容未加入当前项目",
        "历史会话内容不会加入项目、待处理事项或报告",
        "清除这些内容",
        'const text = "历史会话内容"',
        "当前包含历史会话内容。请先清除这些内容，再保存项目。",
    ):
        assert expected in provenance

    for removed_example_isolation_copy in (
        "示例内容仅供体验，不会加入当前项目、待处理事项或报告。",
        "有 ${keys.length} 项示例或历史会话内容未加入当前项目",
        "当前包含示例或历史会话内容。请先清除这些内容，再保存项目。",
    ):
        assert removed_example_isolation_copy not in provenance

    for expected in (
        "AI 服务设置",
        "高级连接设置",
        "平台 AI 服务已就绪",
        "正在使用企业自有 AI 服务",
        "普通用户无需修改",
        "AI 服务设置已保存",
    ):
        assert expected in model
    assert 'details.id = "modelConfigAdvancedSettings"' in model
    assert ".model-config-advanced" in model_css


def test_service_workflow_owns_its_customer_presentation_rules() -> None:
    stylesheet = (ASSETS / "service-workflow.css").read_text(encoding="utf-8")

    for required in (
        '#serviceWorkflowModal label[aria-hidden="true"]',
        "#serviceWorkflowModal .sw-metrics{grid-template-columns:repeat(4,minmax(0,1fr))}",
        "#serviceWorkflowModal .sw-context p b:empty",
        "#serviceWorkflowModal .sw-event{padding-bottom:10px}",
        "@media(max-width:720px){#serviceWorkflowModal .sw-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}",
    ):
        assert required in stylesheet


def test_removed_enterprise_presentation_layer_does_not_return() -> None:
    assert not (ASSETS / "enterprise-user-view.js").exists()
    assert not (ASSETS / "enterprise-user-view.css").exists()
    assert "enterprise-user-view.js" not in UI_SCRIPTS

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")

    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert "ZHILINK_ENTERPRISE_USER_VIEW_READY" not in bundle.text
    assert "ZHILINK_ENTERPRISE_USER_VIEW_GUARDS_READY" not in bundle.text
    assert "ZHILINK_UI_V4_FINAL_QA_READY" in bundle.text


def test_customer_sources_do_not_reintroduce_runtime_rewrite_helpers() -> None:
    sources = "\n".join(
        (ASSETS / name).read_text(encoding="utf-8")
        for name in ("account-access.js", "project-storage.js", "data-provenance-guard.js", "model-config-save-v4.js")
    )
    for obsolete in (
        "decorateModelSettings",
        "decorateProvenance",
        "decorateProjectManager",
        "decorateAccount",
        "TOAST_REWRITES",
        "rewriteToastMessage",
        "window.toast = wrapped",
        "enterpriseAdvancedAiSettings",
    ):
        assert obsolete not in sources

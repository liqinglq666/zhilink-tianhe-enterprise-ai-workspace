from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_normal_customer_flow_hides_demo_only_examples() -> None:
    forms_css = (ASSETS / "ui-v4-forms.css").read_text(encoding="utf-8")

    assert "body.ui-v4-forms .ui-v4-example-bar {\n  display: none;\n}" in forms_css


def test_customer_copy_does_not_expose_runtime_transport_details() -> None:
    app = (ASSETS / "app.js").read_text(encoding="utf-8")

    for expected in (
        "暂无生成材料。进入业务模块完成一次任务后，这里会自动显示最近材料。",
        "确认清空当前输入和生成结果吗？当前会话中的 AI 服务临时设置也会一并清除。",
        "正在生成内容，请稍候...",
        "处理异常：",
    ):
        assert expected in app

    for implementation_copy in (
        "配置 API 后进入业务模块生成内容",
        "流式生成中...",
        "流式整合中...",
        "API Key 也会从当前会话清除",
        "正在接收模型输出...",
        "调用异常：",
    ):
        assert implementation_copy not in app

    assert '<span class="meta-pill">${escapeHtml(result.mode || "AI模型模式")}</span>' not in app

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_generation_panel_does_not_expose_transport_details() -> None:
    source = (ASSETS / "generation-controls.js").read_text(encoding="utf-8")

    assert "流式生成中" not in source
    assert "连接超时 30 秒" not in source
    assert "生成超时由服务端协调" not in source
    assert "正在连接模型接口" not in source
    assert '<span class="meta-pill">AI模型流式模式</span>' not in source
    assert "正在处理" in source
    assert "正在核对内容" in source


def test_result_view_filters_internal_model_metadata() -> None:
    source = (ASSETS / "ui-v4-results.js").read_text(encoding="utf-8")

    assert "INTERNAL_META_RE" in source
    assert "AI\\s*模型" in source
    assert "本地规则预检" in source
    assert "item.remove()" in source
    assert 'meta.setAttribute("aria-label", "文档信息")' in source


def test_meeting_view_uses_business_language_not_implementation_language() -> None:
    source = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")

    assert "核对原文" in source
    assert "归档前请复核" in source
    assert "需人工确认" in source
    assert "不向业务用户暴露内部编号" not in source
    assert "AI 生成 · 待人工确认" not in source

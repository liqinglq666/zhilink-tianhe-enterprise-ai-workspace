from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_SOURCE = ROOT / "frontend" / "assets" / "meeting-user-view.js"
ROUTES_SOURCE = ROOT / "backend" / "project_routes.py"


def test_meeting_view_keeps_internal_ids_out_of_default_ui_and_exports():
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "INTERNAL_REF_RE" in source
    assert "removeEvidenceColumns" in source
    assert "输入证据与待确认索引" in source
    assert "自动一致性校验" in source
    assert "AI 建议补充动作" in source
    assert "AI 生成 · 待人工确认" in source
    assert "示例数据 · 不会保存为正式材料" in source
    assert "查看生成依据" in source
    assert "sanitizeMeetingMarkdown(result.content)" in source
    assert "downloadReportFile" in source
    assert "copyText(sanitizeMeetingMarkdown(rawMeeting()))" in source


def test_meeting_view_preserves_a_source_drawer_without_exposing_internal_ids():
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "meetingSourceDialog" in source
    assert "会议原文来源" in source
    assert "内部编号不会展示给业务用户" in source
    assert "evidenceSources(raw)" in source
    assert "pendingQuestions(raw)" in source


def test_production_bundle_loads_meeting_user_view_after_structured_results():
    source = ROUTES_SOURCE.read_text(encoding="utf-8")

    assert '"meeting-user-view.js"' in source
    assert source.index('"structured-results.js"') < source.index('"meeting-user-view.js"')

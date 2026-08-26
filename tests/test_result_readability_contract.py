from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_CSS = (ROOT / "frontend/assets/ui-v4-workspace.css").read_text(encoding="utf-8")
MEETING_CSS = (ROOT / "frontend/assets/meeting-user-view.css").read_text(encoding="utf-8")
APP_JS = (ROOT / "frontend/assets/app.js").read_text(encoding="utf-8")


def test_section_kind_badges_are_not_forced_into_sequence_width():
    assert ".result-section-title > span:first-child" in WORKSPACE_CSS
    assert ".result-section-title > span {" not in WORKSPACE_CSS
    assert "#meetingResult .ui-v4-section-kind-badge" in MEETING_CSS
    assert "white-space: nowrap;" in MEETING_CSS
    assert "writing-mode: horizontal-tb;" in MEETING_CSS


def test_meeting_evidence_table_keeps_reference_columns_readable():
    assert "#meetingResult .ui-v4-document-table" in MEETING_CSS
    assert "table-layout: fixed;" in MEETING_CSS
    assert "td:nth-child(2)" in MEETING_CSS
    assert "td:nth-child(3)" in MEETING_CSS
    assert "word-break: keep-all;" in MEETING_CSS


def test_streaming_does_not_render_partial_markdown_as_final_document():
    section = APP_JS.split("function updateStreamingResult", 1)[1].split("function finishStreamingResult", 1)[0]
    assert "renderStructuredMarkdown(content)" not in section
    assert "正在生成并整理内容，完成后将自动显示正式结果。" in section

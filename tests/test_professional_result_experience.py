from pathlib import Path


GENERATION = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")
GENERATION_CSS = Path("frontend/assets/generation-controls.css").read_text(encoding="utf-8")
RESULTS = Path("frontend/assets/ui-v4-results.js").read_text(encoding="utf-8")
RESULTS_CSS = Path("frontend/assets/ui-v4-results.css").read_text(encoding="utf-8")


def test_generation_view_uses_business_workflow_instead_of_raw_transport_copy() -> None:
    assert 'class="generation-steps"' in GENERATION
    assert "理解材料" in GENERATION
    assert "形成结果" in GENERATION
    assert "核对排版" in GENERATION
    assert "正在形成业务结果" in GENERATION
    assert "业务草稿" in GENERATION
    assert "实时更新" in GENERATION
    assert ".generation-step.is-active" in GENERATION_CSS
    assert ".generation-step.is-done" in GENERATION_CSS


def test_stream_preview_removes_internal_ids_and_markdown_table_chrome() -> None:
    assert "PREVIEW_INTERNAL_REF_RE" in GENERATION
    assert "PREVIEW_HIDDEN_SECTIONS" in GENERATION
    assert "PREVIEW_TECHNICAL_HEADERS" in GENERATION
    assert "function buildBusinessPreview(content)" in GENERATION
    assert 'trimmed.startsWith("|") && trimmed.endsWith("|")' in GENERATION
    assert 'output.push(`• ${primary}' in GENERATION
    preview_start = GENERATION.index("function updateLiveStreamPreview(key, content)")
    preview_end = GENERATION.index("function showStoppedResult", preview_start)
    preview = GENERATION[preview_start:preview_end]
    assert "buildBusinessPreview(content)" in preview
    assert "target.textContent = text;" in preview
    assert "innerHTML" not in preview


def test_result_presenter_converts_tables_into_business_components() -> None:
    assert "const RECORD_KINDS = new Set" in RESULTS
    assert "function replaceSummaryTable(table, model)" in RESULTS
    assert 'grid.className = "ui-v4-fact-grid"' in RESULTS
    assert "function replaceRecordTable(table, model, kind)" in RESULTS
    assert "ui-v4-business-record" in RESULTS
    assert "ui-v4-record-status" in RESULTS
    assert "upgradeBusinessTables(section, titleText, kind);" in RESULTS
    assert "function scheduleResultSync()" in RESULTS
    assert "queueMicrotask(() => queueMicrotask" in RESULTS


def test_result_css_prevents_stretched_spreadsheet_rows() -> None:
    assert ".ui-v4-fact-grid" in RESULTS_CSS
    assert ".ui-v4-record-list" in RESULTS_CSS
    assert ".ui-v4-business-record" in RESULTS_CSS
    assert 'height: auto !important;' in RESULTS_CSS
    assert 'min-height: 0 !important;' in RESULTS_CSS
    assert ".ui-v4-table-scroll" in RESULTS_CSS
    assert "table-layout: auto" in RESULTS_CSS

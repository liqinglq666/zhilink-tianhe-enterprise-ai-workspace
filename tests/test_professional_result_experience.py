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


def test_result_status_tones_do_not_treat_negative_words_as_success() -> None:
    assert 'if (/(高风险|严重|逾期|异常|失败|拒绝|未通过|不通过|未达标)/.test(text)) return "danger";' in RESULTS
    assert 'if (/(待确认|待补充|未确认|未知|待定|部分明确|未完成|不明确|需补充|处理中)/.test(text)) return "pending";' in RESULTS
    assert 'if (/(已确认|已完成|已通过|正常|低风险)/.test(text)) return "success";' in RESULTS
    assert '已完成|完成|明确|通过|正常' not in RESULTS


def test_copy_text_falls_back_when_async_clipboard_is_rejected() -> None:
    start = RESULTS.index("async function copyText(text)")
    end = RESULTS.index("function downloadTextFile", start)
    implementation = RESULTS[start:end]
    assert 'const value = String(text || "");' in implementation
    assert "try {" in implementation
    assert "await navigator.clipboard.writeText(value);" in implementation
    assert "catch (_) {}" in implementation
    assert 'document.execCommand("copy")' in implementation
    assert "if (!copied) throw new Error" in implementation
    assert "finally {" in implementation
    assert "textarea.remove();" in implementation

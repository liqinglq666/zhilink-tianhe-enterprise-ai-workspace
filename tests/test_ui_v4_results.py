from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_v4_states_loads_result_reading_layer_after_forms() -> None:
    with TestClient(app) as client:
        states = client.get("/assets/ui-v4-states.js?v=20260810.1")

    assert states.status_code == 200
    text = states.text
    assert 'function ensureForms()' in text
    assert 'function ensureResults()' in text
    assert '/assets/ui-v4-results.js?v=${VERSION}' in text
    assert 'script.dataset.uiV4Results = "true"' in text
    assert 'ensureForms();' in text
    assert 'ensureResults();' in text
    assert text.index('ensureForms();') < text.index('ensureResults();')


def test_v4_result_assets_present_business_document_hierarchy() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-results.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-results.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_RESULTS_READY" in script.text
    assert 'panel.classList.add("ui-v4-document-result")' in script.text
    assert 'body.classList.add("ui-v4-document-body")' in script.text
    assert 'section.classList.add("ui-v4-document-section")' in script.text
    assert 'rail.className = "ui-v4-document-status-rail"' in script.text
    assert 'bar.classList.add("ui-v4-document-status-item")' in script.text
    assert 'copy.textContent = "复制正文"' in script.text
    assert 'label.textContent = "导出"' in script.text

    assert ".ui-v4-document-status-rail" in stylesheet.text
    assert ".ui-v4-document-section" in stylesheet.text
    assert ".ui-v4-section-kind-badge" in stylesheet.text
    assert ".ui-v4-document-table" in stylesheet.text
    assert "max-width: 78ch" in stylesheet.text
    assert "@media print" in stylesheet.text
    assert "@media (max-width: 720px)" in stylesheet.text
    assert "prefers-reduced-motion" in stylesheet.text


def test_v4_results_classify_business_sections_without_rewriting_generated_content() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-results.js?v=20260810.1")

    text = script.text
    assert '["pending", /(待确认|待补充|需确认|未确认|信息缺口|未知事项|待核实)/]' in text
    assert '["risk", /(风险|问题|注意事项|合规|警示|隐患|异常)/]' in text
    assert '["decision", /(关键决策|会议决策|决定事项|已确认事项|核心结论|结论)/]' in text
    assert '["action", /(待办|行动|下一步|执行|任务|实施|跟进|建议动作|工作安排)/]' in text
    assert 'section.dataset.uiV4SectionKind = kind' in text
    assert 'section.setAttribute("aria-labelledby", title.id)' in text
    assert 'table.setAttribute("aria-label", `${sectionTitle || "结果"}表格`)' in text
    assert 'cell.setAttribute("scope", "col")' in text

    # The reading layer may decorate rendered DOM, but generated business content and persistence
    # remain owned by the existing result/review/export layers.
    for forbidden in (
        "fetch(",
        "localStorage",
        "sessionStorage",
        "state.results",
        "setResult(",
        "showResult =",
        "apiStream(",
        "saveConfig(",
        "downloadModuleFile(",
    ):
        assert forbidden not in text


def test_v4_results_reduce_plugin_chrome_and_keep_mobile_readability() -> None:
    with TestClient(app) as client:
        stylesheet = client.get("/assets/ui-v4-results.css?v=20260810.1")

    text = stylesheet.text
    assert "grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))" in text
    assert "border-bottom: 1px solid #edf1f5" in text
    assert '[data-ui-v4-section-kind="risk"]' in text
    assert '[data-ui-v4-section-kind="pending"]' in text
    assert '[data-ui-v4-section-kind="decision"]' in text
    assert '[data-ui-v4-section-kind="action"]' in text
    assert "min-width: 620px" in text
    assert "overflow-x: auto" in text
    assert "flex-wrap: nowrap" in text
    assert "scrollbar-width: none" in text

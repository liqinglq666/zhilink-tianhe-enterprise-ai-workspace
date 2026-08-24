from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
VIEW_SOURCE = ASSETS / "meeting-user-view.js"
VIEW_STYLE = ASSETS / "meeting-user-view.css"
INDEX = ROOT / "frontend" / "index.html"
ROUTES_SOURCE = ROOT / "backend" / "project_routes.py"


def test_meeting_view_keeps_internal_ids_out_of_default_ui_and_exports():
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "INTERNAL_REF_RE" in source
    assert "removeEvidenceColumns" in source
    assert "输入证据与待确认索引" in source
    assert "自动一致性校验" in source
    assert "AI 建议补充动作" in source
    assert "需人工确认" in source
    assert "核对原文" in source
    assert "AI 生成 · 待人工确认" not in source
    assert "sanitizeMeetingMarkdown(result?.content)" in source
    assert 'hooks.register("results:collect", sanitizeCollectedResults)' in source
    assert "downloadReportFile =" not in source
    assert "collectResultsForReport =" not in source
    assert "copyText(sanitizeMeetingMarkdown(rawMeeting()))" in source


def test_meeting_view_preserves_a_source_drawer_without_exposing_internal_ids():
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "meetingSourceDialog" in source
    assert "会议原文" in source
    assert "用于核对纪要内容与原始会议记录" in source
    assert "不向业务用户暴露内部编号" not in source
    assert "sourceItems(rawMeeting())" in source
    assert "pendingItems(rawMeeting())" in source


def test_meeting_view_styles_are_owned_by_native_html_not_runtime_injection():
    source = VIEW_SOURCE.read_text(encoding="utf-8")
    stylesheet = VIEW_STYLE.read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")

    marker = 'href="/assets/meeting-user-view.css"'
    assert html.count(marker) == 1
    assert html.index(marker) < html.index('href="/assets/ui-v4-shell.css?v=20260811.1"')
    assert "feature-styles.css" not in html
    assert ".meeting-source-modal" in stylesheet
    assert ".meeting-source-dialog" in stylesheet
    assert ".meeting-source-pending" in stylesheet
    assert "meeting-user-view.css" not in source
    assert 'document.createElement("link")' not in source
    assert 'document.createElement("style")' not in source
    assert "style.dataset.meetingUserView" not in source
    assert "style.textContent" not in source


def test_meeting_view_does_not_rewrite_provenance_labels_owned_elsewhere():
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "示例生成" not in source
    assert "示例数据" not in source
    assert "旧会话材料" not in source
    assert "历史材料 · 请复核后使用" not in source
    assert ".data-origin-pill" not in source


def test_production_bundle_loads_meeting_user_view_after_structured_results():
    source = ROUTES_SOURCE.read_text(encoding="utf-8")

    assert '"meeting-user-view.js"' in source
    assert source.index('"structured-results.js"') < source.index('"meeting-user-view.js"')

from __future__ import annotations

from backend.project_schemas import ProjectSnapshot


def test_report_freshness_guard_is_loaded_last() -> None:
    routes = open("backend/project_routes.py", encoding="utf-8").read()
    freshness = routes.index('"report-freshness.js"')
    final_qa = routes.index('"ui-v4-final-qa.js"')

    assert freshness > final_qa


def test_source_changes_invalidate_old_derived_report() -> None:
    source = open("frontend/assets/report-freshness.js", encoding="utf-8").read()

    assert 'key === "report" || !state.results.report' in source
    assert "previousContent === incomingContent" in source
    assert "delete state.results.report" in source
    assert "mode: REPORT_REFRESH_MODE" in source
    assert "源材料已发生变化" in source
    assert "重新整合运营报告" in source
    assert 'panel.className = "result-panel report-needs-refresh"' in source


def test_stale_report_is_excluded_from_export_collection() -> None:
    source = open("frontend/assets/report-freshness.js", encoding="utf-8").read()

    assert "if (reportNeedsRefresh())" in source
    assert "originalCollectResultsForReport(false)" in source


def test_completed_report_restores_fresh_action_label_after_loading() -> None:
    source = open("frontend/assets/report-freshness.js", encoding="utf-8").read()

    assert 'if (key === "report") setTimeout(() => updateProgress(), 0);' in source
    assert 'stale ? "重新整合运营报告" : "AI 整合运营报告"' in source


def test_refresh_marker_can_be_saved_in_existing_project_meta_schema() -> None:
    snapshot = ProjectSnapshot.model_validate(
        {
            "results": {"meeting": "最新会议纪要"},
            "meta": {
                "report": {
                    "mode": "需更新",
                    "error": "",
                    "time": "2026-08-29T03:00:00Z",
                }
            },
        }
    )

    assert "report" not in snapshot.results
    assert snapshot.meta["report"].mode == "需更新"

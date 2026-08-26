from pathlib import Path


ASSETS = Path("frontend/assets")


def test_meeting_rerender_returns_presentation_to_results_owner() -> None:
    source = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")

    assert "replaceResultBody(panel, sanitizeMeetingMarkdown(raw));" in source
    assert "window.ZHILINK_RESULTS?.refreshPresentation?.();" in source
    assert source.index("replaceResultBody(panel, sanitizeMeetingMarkdown(raw));") < source.index(
        "window.ZHILINK_RESULTS?.refreshPresentation?.();"
    )


def test_meeting_fallback_tables_never_force_long_business_text_to_nowrap() -> None:
    stylesheet = (ASSETS / "meeting-user-view.css").read_text(encoding="utf-8")

    assert "#meetingResult .ui-v4-document-table {" in stylesheet
    assert "table-layout: auto;" in stylesheet
    assert "white-space: normal;" in stylesheet
    assert "overflow-wrap: anywhere;" in stylesheet
    assert "word-break: break-word;" in stylesheet

    # The old 4-column meeting table contract caused risk/explanation/action text to overlap.
    assert "td:nth-child(2)" not in stylesheet
    assert "td:nth-child(3)" not in stylesheet
    assert "table-layout: fixed;" not in stylesheet

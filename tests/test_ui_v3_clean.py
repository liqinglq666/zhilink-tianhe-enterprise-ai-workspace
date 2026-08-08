from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_loads_meeting_user_view_after_ui_v3() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-08-meeting-user-view-v1"
    assert "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY" in response.text
    assert "ZHILINK_UI_V3_READY" in response.text
    assert "ZHILINK_MEETING_USER_VIEW_READY" in response.text
    assert response.text.rfind("ZHILINK_UI_V3_READY") > response.text.rfind(
        "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY"
    )
    assert response.text.rfind("ZHILINK_MEETING_USER_VIEW_READY") > response.text.rfind("ZHILINK_UI_V3_READY")


def test_ui_v3_assets_are_served() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v3-clean.js?v=20260806.2")
        stylesheet = client.get("/assets/ui-v3-clean.css?v=20260806.2")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ui-v3-clean-shell" in script.text
    assert ".page.ui-v3-business-page.active-page" in stylesheet.text


def test_ui_v3_preserves_all_primary_module_ids_and_adds_scalable_icons() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")

    for module in ("profile", "meeting", "contract", "policy", "match", "landing", "report"):
        assert f"{module}: {{" in script
        assert "document.getElementById(id)" in script

    assert "<svg viewBox=" in script
    assert "人工复核后使用" in script
    assert "结果可归档" in script
    assert "innerHTML = config.icon" in script


def test_ui_v3_disables_the_legacy_fixed_shell_before_enabling_grid_layout() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")

    remove_marker = 'document.body.classList.remove("ui-redesign-live")'
    add_marker = 'document.body.classList.add("ui-v3-clean-shell")'
    assert remove_marker in script
    assert add_marker in script
    assert script.index(remove_marker) < script.index(add_marker)


def test_ui_v3_replaces_legacy_visual_patterns_without_business_rewrites() -> None:
    script = (ASSETS / "ui-v3-clean.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-v3-clean.css").read_text(encoding="utf-8")

    assert 'document.body.classList.add("ui-v3-clean-shell")' in script
    assert ".tool-status-card { display: none !important; }" in stylesheet
    assert ".top-actions > :not(#liveTopNav)" in stylesheet
    assert ".ui-v3-business-page > .result-panel" in stylesheet
    assert ".quick-fill-btn" in stylesheet
    assert ".sticky-actions" in stylesheet

    # V3 must not introduce fabricated performance or business metrics.
    for forbidden in ("98%", "节省时间", "提升 35%", "审核准确率"):
        assert forbidden not in script
        assert forbidden not in stylesheet

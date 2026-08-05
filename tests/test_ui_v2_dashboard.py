from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_live_bundle_loads_ui_v2_dashboard() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "ui-v2-dashboard.js?v=20260805.1" in response.text
    assert "loadUiV2Dashboard" in response.text
    assert "ZHILINK_UI_REDESIGN_LIVE_FIXES_READY" in response.text


def test_ui_v2_assets_are_served_as_frontend_assets() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v2-dashboard.js?v=20260805.1")
        stylesheet = client.get("/assets/ui-v2-dashboard.css")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V2_READY" in script.text
    assert "ui-v2-recommendations" in stylesheet.text


def test_ui_v2_uses_real_workspace_state_and_scalable_icons() -> None:
    script = (ASSETS / "ui-v2-dashboard.js").read_text(encoding="utf-8")

    for marker in (
        'text("homeApiStatus")',
        'text("homeGeneratedCount")',
        'text("homeIdentityStatus")',
        "profileComplete()",
        "pendingCount()",
        "generatedCount()",
    ):
        assert marker in script

    assert "根据当前工作台状态给出下一步建议，不使用虚构业务数据" in script
    assert "98%" not in script
    assert "节省时间" not in script
    assert "<svg viewBox=" in script


def test_ui_v2_covers_all_primary_workspace_modules() -> None:
    script = (ASSETS / "ui-v2-dashboard.js").read_text(encoding="utf-8")

    for module in ("meeting", "contract", "policy", "match", "profile", "landing", "report"):
        assert f"{module}: {{" in script

    for label in ("会议纪要", "合同审阅", "政策助手", "供需协作", "企业档案", "实施计划", "报告归档"):
        assert label in script

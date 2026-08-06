from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_loads_versioned_data_provenance_guard() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "data-provenance-guard-v2.js?v=20260806.2" in response.text
    assert "loadDataProvenanceGuard" in response.text


def test_data_provenance_assets_are_served() -> None:
    with TestClient(app) as client:
        wrapper = client.get("/assets/data-provenance-guard-v2.js?v=20260806.2")
        core = client.get("/assets/data-provenance-guard.js?v=20260806.1")
        stylesheet = client.get("/assets/data-provenance-guard.css?v=20260806.1")

    assert wrapper.status_code == 200
    assert core.status_code == 200
    assert stylesheet.status_code == 200
    assert 'RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2"' in wrapper.text
    assert 'QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1"' in wrapper.text
    assert "data-provenance-guard.js?v=20260806.1" in wrapper.text
    assert "ZHILINK_DATA_PROVENANCE_READY" in core.text
    assert "data-isolation-notice" in stylesheet.text


def test_example_and_legacy_results_are_not_formal_workspace_data() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert 'FORMAL_ORIGINS = new Set(["user", "project", "imported"])' in script
    assert 'return "example"' in script
    assert 'return localStorage.getItem(CURRENT_PROJECT_STORAGE) ? "project" : "legacy"' in script
    assert "isFormalResult" in script
    assert "collectFormalBaseResults" in script
    assert "collectFormalResultsForReport" in script
    assert "示例生成 · 不计入正式工作台" in script
    assert "旧会话材料 · 已隔离" in script


def test_formal_pending_panel_replaces_ambiguous_legacy_panel() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "data-provenance-guard.css").read_text(encoding="utf-8")

    assert "AI 待人工核对" in script
    assert "只显示真实业务材料" in script
    assert "data-formal-goto" in script
    assert "clearIsolatedResults" in script
    assert "#livePendingPanel" in stylesheet
    assert "display: none !important" in stylesheet


def test_example_material_cannot_be_saved_as_formal_project() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert 'event.target.closest("#createProjectButton, #saveProjectButton")' in script
    assert "请先清除隔离材料，再保存正式项目" in script
    assert "stopImmediatePropagation" in script

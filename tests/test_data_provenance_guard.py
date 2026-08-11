from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_loads_provenance_wrapper_directly_before_v4_runtime_and_shell() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" in response.text
    assert "ZHILINK_UI_V4_RUNTIME_READY" in response.text
    assert "ZHILINK_UI_V4_SHELL_READY" in response.text
    assert response.text.index("ZHILINK_DATA_PROVENANCE_V2_READY") < response.text.index("ZHILINK_UI_V4_RUNTIME_READY")
    assert response.text.index("ZHILINK_UI_V4_RUNTIME_READY") < response.text.index("ZHILINK_UI_V4_SHELL_READY")
    assert "loadDataProvenanceGuard" not in response.text


def test_data_provenance_assets_are_served_and_self_contained() -> None:
    with TestClient(app) as client:
        wrapper = client.get("/assets/data-provenance-guard-v2.js?v=20260807.1")
        core = client.get("/assets/data-provenance-guard.js?v=20260806.1")
        stylesheet = client.get("/assets/data-provenance-guard.css?v=20260806.1")

    assert wrapper.status_code == 200
    assert core.status_code == 200
    assert stylesheet.status_code == 200
    assert 'BASE_RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2"' in wrapper.text
    assert 'contract: "20260807-contract-grounded-v3"' in wrapper.text
    assert 'policy: "20260807-policy-grounded-v3"' in wrapper.text
    assert 'QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1"' in wrapper.text
    assert 'const CORE_STYLE = "/assets/data-provenance-guard.css?v=20260806.1"' in wrapper.text
    assert "function ensureStyles()" in wrapper.text
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


def test_provenance_refreshes_v4_shell_without_owning_dashboard_panels() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "data-provenance-guard.css").read_text(encoding="utf-8")

    assert "window.ZHILINK_UI_V4_SHELL?.refresh?.()" in script
    assert "window.ZHILINK_DATA_PROVENANCE =" in script
    assert "formalCount," in script
    assert "isFormalResult," in script
    assert "uiV4HomeGrid" in script

    for forbidden in (
        "formalPendingPanel", "formalUsagePanel", "liveHomeGrid", "livePendingPanel", "liveUsagePanel",
        "live-panel", "live-pending", "zhilink:ui-v3-ready",
    ):
        assert forbidden not in script
        assert forbidden not in stylesheet


def test_example_material_cannot_be_saved_as_formal_project() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    assert 'event.target.closest("#createProjectButton, #saveProjectButton")' in script
    assert "请先清除隔离材料，再保存正式项目" in script
    assert "stopImmediatePropagation" in script


def test_v4_shell_metrics_and_pending_items_use_formal_results_only() -> None:
    script = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")

    assert 'FORMAL_ORIGINS = new Set(["user", "project", "imported"])' in script
    assert "function isFormalResult(key)" in script
    assert "window.ZHILINK_DATA_PROVENANCE?.isFormalResult" in script
    assert "if (!isFormalResult(key)) return;" in script
    assert 'window.ZHILINK_DATA_PROVENANCE?.formalCount' in script
    assert 'window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false })' in script
    assert '"zhilink:data-provenance-ready"' in runtime
    assert "示例和旧会话材料不会进入正式统计" in script

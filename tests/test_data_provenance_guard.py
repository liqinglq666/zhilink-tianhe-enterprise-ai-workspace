from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_production_bundle_loads_unified_provenance_after_core_runtime() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "ZHILINK_WORKSPACE_CONTRACTS_READY" in response.text
    assert "ZHILINK_WORKSPACE_HOOKS_READY" in response.text
    assert "ZHILINK_RESULT_EVENTS_READY" in response.text
    assert "ZHILINK_DATA_PROVENANCE_READY" in response.text
    assert "ZHILINK_UI_V4_RUNTIME_READY" in response.text
    assert response.text.index("ZHILINK_WORKSPACE_CONTRACTS_READY") < response.text.index("ZHILINK_DATA_PROVENANCE_READY")
    assert response.text.index("ZHILINK_WORKSPACE_HOOKS_READY") < response.text.index("ZHILINK_DATA_PROVENANCE_READY")
    assert response.text.index("ZHILINK_RESULT_EVENTS_READY") < response.text.index("ZHILINK_DATA_PROVENANCE_READY")
    assert response.text.index("ZHILINK_UI_V4_RUNTIME_READY") < response.text.index("ZHILINK_DATA_PROVENANCE_READY")
    assert "ZHILINK_DATA_PROVENANCE_V2_READY" not in response.text


def test_data_provenance_is_one_self_contained_asset() -> None:
    with TestClient(app) as client:
        removed_wrapper = client.get("/assets/data-provenance-guard-v2.js?v=20260807.1")
        core = client.get("/assets/data-provenance-guard.js?v=20260806.1")
        stylesheet = client.get("/assets/data-provenance-guard.css?v=20260806.1")

    assert removed_wrapper.status_code == 404
    assert core.status_code == 200
    assert stylesheet.status_code == 200
    assert 'BASE_RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2"' in core.text
    assert 'contract: "20260807-contract-grounded-v3"' in core.text
    assert 'policy: "20260807-policy-grounded-v3"' in core.text
    assert "QUARANTINE_STORAGE = contracts.storage.legacyQuarantine" in core.text
    assert "STYLE_URL" not in core.text
    assert "ensureStyles" not in core.text
    assert 'link[data-zhilink-data-provenance]' not in core.text
    assert 'document.createElement("link")' not in core.text
    assert "ZHILINK_DATA_PROVENANCE_READY" in core.text
    assert "CORE_SCRIPT" not in core.text
    assert "document.createElement(\"script\")" not in core.text
    assert "data-isolation-notice" in stylesheet.text


def test_example_and_legacy_results_are_not_formal_workspace_data() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert "FORMAL_ORIGINS = new Set(contracts.formalOrigins)" in script
    assert 'return "example"' in script
    assert 'return localStorage.getItem(CURRENT_PROJECT_STORAGE) ? "project" : "legacy"' in script
    assert "isFormalResult" in script
    assert "collectFormalResults" in script
    assert 'hooks.register("results:collect", collectFormalResults)' in script
    assert "collectBaseResults =" not in script
    assert "collectResultsForReport =" not in script
    assert 'origin === "example" ? "示例内容" : "历史会话内容"' in script
    assert "示例生成 · 不计入正式工作台" not in script
    assert "旧会话材料 · 已隔离" not in script


def test_provenance_uses_result_events_without_function_or_dom_observers() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert "window.addEventListener(EVENTS.resultUpdated" in script
    assert "window.addEventListener(EVENTS.progressUpdated, renderFormalProgress)" in script
    assert "stampCommittedResult" in script
    assert "EVENTS.resultSchemaStamped" in script
    assert "MutationObserver" not in script
    assert "setInterval(" not in script
    assert "window.setResult =" not in script
    assert "window.updateProgress =" not in script
    assert "window.applyExample =" not in script


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
    assert 'event.target.closest?.("#createProjectButton, #saveProjectButton")' in script
    assert "当前包含示例或历史会话内容。请先清除这些内容，再保存项目。" in script
    assert "请先清除隔离材料，再保存正式项目" not in script
    assert "stopImmediatePropagation" in script


def test_provenance_customer_copy_is_native_and_business_facing() -> None:
    script = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    for expected in (
        "示例内容仅供体验，不会加入当前项目、待处理事项或报告。",
        "暂无已加入项目的正式材料。示例和历史会话内容不会显示在这里。",
        "有 ${keys.length} 项示例或历史会话内容未加入当前项目",
        "示例和历史会话内容不会加入项目、待处理事项或报告",
        "清除这些内容",
        "已清除 ${keys.length} 项示例或历史会话内容。",
    ):
        assert expected in script


def test_v4_dashboard_metrics_and_pending_items_use_formal_results_only() -> None:
    script = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")

    assert "FORMAL_ORIGINS = new Set(contracts.formalOrigins)" in script
    assert "function isFormalResult(key)" in script
    assert "window.ZHILINK_DATA_PROVENANCE?.isFormalResult" in script
    assert "if (!isFormalResult(key)) return;" in script
    assert 'window.ZHILINK_DATA_PROVENANCE?.formalCount' in script
    assert 'window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false })' in script
    assert 'dataProvenanceReady: "zhilink:data-provenance-ready"' in runtime
    assert "当前未打开项目。新建或打开项目后可持续保存工作进度。" in script

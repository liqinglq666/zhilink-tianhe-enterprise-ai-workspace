from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"
RUNTIME = ASSETS / "ui-v4-runtime.js"


def test_storage_recovery_removes_invalid_json_without_exporting_diagnostics() -> None:
    source = (ASSETS / "storage-recovery.js").read_text(encoding="utf-8")

    for key in (
        "zhilian_identity",
        "zhilian_current_project_v1",
        "zhilian_profile",
        "zhilian_form_inputs",
        "zhilian_results",
        "zhilian_meta",
    ):
        assert key in source
    assert "JSON.parse(raw)" in source
    assert "storage.removeItem(key);" in source
    assert "ZHILINK_STORAGE_RECOVERY" not in source
    assert "console." not in source
    assert "recovered" not in source


def test_core_runtime_owns_contracts_result_events_hooks_and_ui_scheduler() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    for marker in (
        "ZHILINK_WORKSPACE_CONTRACTS_READY",
        "ZHILINK_WORKSPACE_HOOKS_READY",
        "ZHILINK_RESULT_EVENTS_READY",
        "ZHILINK_UI_V4_RUNTIME_READY",
    ):
        assert marker in runtime

    assert "window.ZHILINK_WORKSPACE_CONTRACTS = contracts" in runtime
    assert 'workspaceKey: "zhilian_workspace_key_v1"' in runtime
    assert 'currentProject: "zhilian_current_project_v1"' in runtime
    assert 'results: "zhilian_results"' in runtime
    assert 'meta: "zhilian_meta"' in runtime
    assert 'projectChanged: "zhilink:project-changed"' in runtime
    assert 'resultUpdated: "zhilink:result-updated"' in runtime
    assert 'progressUpdated: "zhilink:progress-updated"' in runtime
    assert 'structuredUpdated: "zhilink:structured-updated"' in runtime
    assert 'reviewUpdated: "zhilink:review-updated"' in runtime
    assert "apiStream = async function hookedApiStream" in runtime
    assert "collectResultsForReport = function hookedCollectResultsForReport" in runtime
    assert "collectSingleModuleResult = function hookedCollectSingleModuleResult" in runtime
    assert "window.fetch = async function hookedWorkspaceFetch" in runtime
    assert "window.showResult = function eventAwareShowResult" in runtime
    assert "window.setResult = function eventAwareSetResult" in runtime
    assert "window.updateProgress = function eventAwareUpdateProgress" in runtime
    assert "const RESULT_EVENT = events.resultUpdated" in runtime
    assert "const PROGRESS_EVENT = events.progressUpdated" in runtime
    assert 'source: commitDepth > 0 ? "commit" : "render"' in runtime
    assert "setGenerationTransport" in runtime
    assert 'runHookAsync("generation:request"' in runtime
    assert 'runHookSync("results:collect"' in runtime
    assert 'runHookAsync("fetch:request"' in runtime
    assert "isProjectWrite" in runtime
    assert "response.ok && isProjectWrite(finalInput, finalInit)" in runtime
    assert "emitWindowEvent(events.projectChanged" in runtime
    assert 'throw new Error("Generation transport is already registered.")' in runtime
    assert 'throw new TypeError(`Hook ${kind} must be synchronous.`)' in runtime
    assert "MutationObserver" in runtime
    assert "requestAnimationFrame" in runtime


def test_runtime_mutation_filter_is_owned_by_observer_options() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert 'observer = new MutationObserver(() => schedule("dom"));' in runtime
    assert 'attributeFilter: ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"]' in runtime
    assert "mutations.some" not in runtime
    assert "mutation.type" not in runtime
    assert "mutation.attributeName" not in runtime


def test_business_extensions_register_hooks_and_events_without_wrapping_globals() -> None:
    consumers = {
        "generation-controls.js": ("hooks.setGenerationTransport(runGeneration)",),
        "policy-sources.js": ('hooks.register("generation:request"', "contracts.events.resultUpdated"),
        "data-provenance-guard.js": ('hooks.register("results:collect", collectFormalResults)', "EVENTS.resultUpdated"),
        "meeting-user-view.js": ('hooks.register("results:collect", sanitizeCollectedResults)', "contracts.events.resultUpdated"),
        "review-workflow.js": ("contracts.events.resultUpdated",),
        "structured-results.js": ("contracts.events.resultUpdated",),
    }
    forbidden = (
        "apiStream =",
        "collectResultsForReport =",
        "collectSingleModuleResult =",
        "downloadReportFile =",
        "window.fetch =",
        "showResult = function",
        "setResult = function",
    )

    for filename, required in consumers.items():
        source = (ASSETS / filename).read_text(encoding="utf-8")
        for marker in required:
            assert marker in source, f"{marker} missing from {filename}"
        for marker in forbidden:
            assert marker not in source, f"{marker} leaked into {filename}"

    project_storage = (ASSETS / "project-storage.js").read_text(encoding="utf-8")
    assert 'const PERSISTED_META_FIELDS = ["origin", "example_key", "result_schema_version"]' in project_storage
    assert 'hooks.register("fetch:request"' not in project_storage
    assert not (ASSETS / "project-result-meta.js").exists()


def test_bundle_loads_runtime_contracts_before_examples_and_consumers() -> None:
    routes = ROUTES.read_text(encoding="utf-8")
    assert '"result-events.js"' not in routes
    assert '"workspace-hooks.js"' not in routes
    assert '"project-result-meta.js"' not in routes
    assert '"example-loader.js"' in routes
    assert '"ui-v4-runtime.js"' in routes

    app_position = routes.index('"app.js"')
    runtime_position = routes.index('"ui-v4-runtime.js"')
    examples_position = routes.index('"example-loader.js"')
    assert app_position < runtime_position < examples_position
    for filename in (
        "generation-controls.js",
        "project-storage.js",
        "review-workflow.js",
        "structured-results.js",
        "policy-sources.js",
        "data-provenance-guard.js",
        "meeting-user-view.js",
    ):
        assert runtime_position < routes.index(f'"{filename}"')

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        old_result_bridge = client.get("/assets/result-events.js")
        old_hook_bridge = client.get("/assets/workspace-hooks.js")

    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert bundle.text.index("ZHILINK_WORKSPACE_CONTRACTS_READY") < bundle.text.index("ZHILINK_EXAMPLE_LOADER_READY")
    assert bundle.text.index("ZHILINK_WORKSPACE_HOOKS_READY") < bundle.text.index("ZHILINK_GENERATION_CONTROLS_READY")
    assert bundle.text.index("ZHILINK_RESULT_EVENTS_READY") < bundle.text.index("ZHILINK_DATA_PROVENANCE_READY")
    assert old_result_bridge.status_code == 404
    assert old_hook_bridge.status_code == 404


def test_removed_bridge_assets_are_physically_deleted() -> None:
    assert not (ASSETS / "result-events.js").exists()
    assert not (ASSETS / "workspace-hooks.js").exists()
    assert not (ASSETS / "project-result-meta.js").exists()

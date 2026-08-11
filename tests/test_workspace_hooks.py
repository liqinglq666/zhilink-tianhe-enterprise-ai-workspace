from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"


def test_workspace_hooks_are_the_only_global_generation_export_and_fetch_bridge() -> None:
    bridge = (ASSETS / "workspace-hooks.js").read_text(encoding="utf-8")

    assert "ZHILINK_WORKSPACE_HOOKS_READY" in bridge
    assert "apiStream = async function hookedApiStream" in bridge
    assert "collectResultsForReport = function hookedCollectResultsForReport" in bridge
    assert "collectSingleModuleResult = function hookedCollectSingleModuleResult" in bridge
    assert "window.fetch = async function hookedWorkspaceFetch" in bridge
    assert "setGenerationTransport" in bridge
    assert 'runAsync("generation:request"' in bridge
    assert 'runSync("results:collect"' in bridge
    assert 'runAsync("fetch:request"' in bridge

    consumers = (
        "generation-controls.js",
        "policy-sources.js",
        "project-result-meta.js",
        "data-provenance-guard.js",
        "meeting-user-view.js",
    )
    for filename in consumers:
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "apiStream =" not in source, filename
        assert "collectResultsForReport =" not in source, filename
        assert "collectSingleModuleResult =" not in source, filename
        assert "downloadReportFile =" not in source, filename
        assert "window.fetch =" not in source, filename


def test_extensions_register_hooks_instead_of_wrapping_globals() -> None:
    generation = (ASSETS / "generation-controls.js").read_text(encoding="utf-8")
    policy = (ASSETS / "policy-sources.js").read_text(encoding="utf-8")
    project_meta = (ASSETS / "project-result-meta.js").read_text(encoding="utf-8")
    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    meeting = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")

    assert "hooks.setGenerationTransport(runGeneration)" in generation
    assert 'hooks.register("generation:request"' in policy
    assert 'hooks.register("fetch:request"' in project_meta
    assert 'hooks.register("results:collect", collectFormalResults)' in provenance
    assert 'hooks.register("results:collect", sanitizeCollectedResults)' in meeting
    assert "originalApiStream" not in policy
    assert "originalFetch" not in project_meta
    assert "installFormalCollectors" not in provenance
    assert "installExportGuards" not in meeting


def test_bundle_loads_hook_bridge_before_all_hook_consumers() -> None:
    routes = ROUTES.read_text(encoding="utf-8")
    assert '"workspace-hooks.js"' in routes
    bridge = routes.index('"workspace-hooks.js"')
    assert routes.index('"app.js"') < bridge
    for filename in (
        "generation-controls.js",
        "project-result-meta.js",
        "policy-sources.js",
        "data-provenance-guard.js",
        "meeting-user-view.js",
    ):
        assert bridge < routes.index(f'"{filename}"')

    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == "2026-08-11-ui-v4-hooks-v6"
    assert response.text.index("ZHILINK_WORKSPACE_HOOKS_READY") < response.text.index("ZHILINK_GENERATION_CONTROLS_READY")


def test_hook_bridge_rejects_multiple_generation_transports_and_async_sync_hooks() -> None:
    bridge = (ASSETS / "workspace-hooks.js").read_text(encoding="utf-8")

    assert 'throw new Error("Generation transport is already registered.")' in bridge
    assert 'throw new TypeError(`Hook ${kind} must be synchronous.`)' in bridge
    assert "handlers.get(kind) || []" in bridge

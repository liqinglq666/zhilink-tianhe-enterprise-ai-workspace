from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"


def test_result_lifecycle_has_one_central_event_bridge() -> None:
    bridge = (ASSETS / "result-events.js").read_text(encoding="utf-8")

    assert "ZHILINK_RESULT_EVENTS_READY" in bridge
    assert 'const RESULT_EVENT = "zhilink:result-updated"' in bridge
    assert 'const PROGRESS_EVENT = "zhilink:progress-updated"' in bridge
    assert "window.showResult = function eventAwareShowResult" in bridge
    assert "window.setResult = function eventAwareSetResult" in bridge
    assert "window.updateProgress = function eventAwareUpdateProgress" in bridge
    assert 'source: commitDepth > 0 ? "commit" : "render"' in bridge


def test_result_consumers_subscribe_instead_of_replacing_core_result_functions() -> None:
    consumers = (
        "review-workflow.js",
        "structured-results.js",
        "policy-sources.js",
        "data-provenance-guard.js",
        "meeting-user-view.js",
    )
    for filename in consumers:
        text = (ASSETS / filename).read_text(encoding="utf-8")
        assert "zhilink:result-updated" in text
        assert "showResult = function" not in text
        assert "setResult = function" not in text

    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    meeting = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")
    assert "window.updateProgress =" not in provenance
    assert "MutationObserver" not in provenance
    assert "setInterval(" not in provenance
    assert "MutationObserver" not in meeting
    assert "zhilink:structured-updated" in meeting
    assert "zhilink:review-updated" in meeting


def test_policy_schema_is_owned_by_unified_provenance_guard() -> None:
    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")
    policy = (ASSETS / "policy-sources.js").read_text(encoding="utf-8")

    assert 'policy: "20260807-policy-grounded-v3"' in provenance
    assert "quarantineLegacyResults" in provenance
    assert "result_schema_version" in provenance
    assert "installPolicyResultVersionGuard" not in policy
    assert "migrateStalePolicyResult" not in policy
    assert "POLICY_RESULT_SCHEMA_VERSION" not in policy
    assert 'hooks.register("generation:request"' in policy
    assert 'url: "/api/policy/official/stream"' in policy
    assert "apiStream =" not in policy


def test_production_bundle_orders_bridges_before_event_consumers() -> None:
    routes = ROUTES.read_text(encoding="utf-8")
    assert '"workspace-hooks.js"' in routes
    assert '"result-events.js"' in routes
    assert '"data-provenance-guard.js"' in routes
    assert '"data-provenance-guard-v2.js"' not in routes

    hooks = routes.index('"workspace-hooks.js"')
    bridge = routes.index('"result-events.js"')
    assert hooks < bridge
    for filename in (
        "review-workflow.js",
        "structured-results.js",
        "policy-sources.js",
        "data-provenance-guard.js",
        "meeting-user-view.js",
    ):
        assert bridge < routes.index(f'"{filename}"')

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        removed = client.get("/assets/data-provenance-guard-v2.js")

    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == "2026-08-11-ui-v4-hooks-v6"
    assert "ZHILINK_WORKSPACE_HOOKS_READY" in bundle.text
    assert "ZHILINK_RESULT_EVENTS_READY" in bundle.text
    assert removed.status_code == 404

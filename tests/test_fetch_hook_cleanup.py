from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.project_routes import UI_BUNDLE_VERSION

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_runtime_is_the_only_production_fetch_owner() -> None:
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")
    assert "window.fetch = async function hookedWorkspaceFetch" in runtime

    offenders = []
    for path in ASSETS.glob("*.js"):
        if path.name == "ui-v4-runtime.js":
            continue
        source = path.read_text(encoding="utf-8")
        if "window.fetch =" in source:
            offenders.append(path.name)
    assert offenders == []


def test_account_security_is_a_runtime_fetch_hook() -> None:
    source = (ASSETS / "account-access.js").read_text(encoding="utf-8")

    assert "const contracts = window.ZHILINK_WORKSPACE_CONTRACTS" in source
    assert "const hooks = window.ZHILINK_WORKSPACE_HOOKS" in source
    assert 'hooks.register("fetch:request", async request =>' in source
    assert 'headers.set("X-Organization-Id", activeOrganizationId)' in source
    assert 'headers.set("X-CSRF-Token", account.csrf_token)' in source
    assert 'credentials: "same-origin"' in source
    assert "CURRENT_PROJECT_STORAGE = contracts.storage.currentProject" in source
    assert "WORKSPACE_KEY_STORAGE = contracts.storage.workspaceKey" in source
    assert "ACCOUNT_READY_EVENT = contracts.events.accountReady" in source
    assert "nativeFetch" not in source
    assert "securedWorkspaceFetch" not in source
    assert "window.fetch =" not in source
    assert '"zhilian_current_project_v1"' not in source
    assert '"zhilian_workspace_key_v1"' not in source
    assert '"zhilink:account-ready"' not in source


def test_recent_project_open_uses_runtime_dom_schedule_without_retry_timer() -> None:
    source = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")

    assert 'let pendingProjectId = ""' in source
    assert "function resolvePendingProjectOpen()" in source
    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("project-open")' in source
    assert "resolvePendingProjectOpen();" in source
    assert "setInterval" not in source
    assert "clearInterval" not in source
    assert "attempts > 12" not in source
    assert "}, 180);" not in source


def test_production_bundle_has_one_fetch_owner() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["x-zhilink-ui-bundle"] == UI_BUNDLE_VERSION
    assert response.text.count("window.fetch =") == 1
    assert 'hooks.register("fetch:request", async request =>' in response.text

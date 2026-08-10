from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_navigation_loader_includes_mobile_compatibility_stylesheet() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-navigation.js?v=20260810.1")
        compat = client.get("/assets/ui-v4-navigation-compat.css?v=20260810.1")

    assert script.status_code == 200
    assert compat.status_code == 200
    assert "ui-v4-navigation-compat.css" in script.text
    assert "data-ui-v4-navigation-compat" in script.text
    assert "#liveTopNav > #uiV4ProjectContext" in compat.text
    assert "display: grid !important" in compat.text


def test_navigation_layer_only_reuses_existing_project_and_account_controls() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-navigation.js?v=20260810.1")

    assert 'triggerExisting("openProjectManager")' in script.text
    assert 'triggerExisting("openAccountManager")' in script.text
    assert 'document.getElementById("openKnowledgeBase")' in script.text
    for forbidden in ("fetch(", "setResult", "state.results", "saveConfig", "sessionStorage"):
        assert forbidden not in script.text

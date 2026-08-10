from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_navigation_is_self_contained_without_compatibility_stylesheet() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-navigation.js?v=20260810.3")
        stylesheet = client.get("/assets/ui-v4-navigation.css?v=20260810.3")
        compat = client.get("/assets/ui-v4-navigation-compat.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert compat.status_code == 404
    assert "ui-v4-navigation-compat.css" not in script.text
    assert 'document.getElementById("uiV4TopNav")' in script.text
    assert 'document.getElementById("uiV4MobileMenu")' in script.text
    assert ".ui-v4-project-context" in stylesheet.text
    assert ".ui-v4-resource-navigation" in stylesheet.text
    assert "liveTopNav" not in stylesheet.text


def test_navigation_layer_only_reuses_existing_project_and_account_controls() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-navigation.js?v=20260810.3")

    assert 'triggerExisting("openProjectManager")' in script.text
    assert 'triggerExisting("openAccountManager")' in script.text
    assert 'document.getElementById("openKnowledgeBase")' in script.text
    for forbidden in ("fetch(", "setResult", "state.results", "saveConfig", "sessionStorage"):
        assert forbidden not in script.text

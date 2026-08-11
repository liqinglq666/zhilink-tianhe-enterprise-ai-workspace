from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_navigation_script_is_removed_and_shell_owns_navigation() -> None:
    with TestClient(app) as client:
        removed = client.get("/assets/ui-v4-navigation.js?v=20260811.1")
        stylesheet = client.get("/assets/ui-v4-navigation.css?v=20260811.1")
        shell = client.get("/assets/ui-v4-shell.js?v=20260811.1")

    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert removed.status_code == 404
    assert stylesheet.status_code == 200
    assert shell.status_code == 200
    assert 'id="uiV4ProjectContext"' in html
    assert 'id="uiV4AccountToggle"' in html
    assert 'id="uiV4ResourceNavigation"' in html
    assert 'id="uiV4KnowledgeNav"' in html
    assert "uiV4ProjectContext" in shell.text
    assert "uiV4ResourceNavigation" in shell.text
    assert ".ui-v4-project-context" in stylesheet.text
    assert ".ui-v4-resource-navigation" in stylesheet.text


def test_shell_navigation_preserves_existing_business_entry_points() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-shell.js?v=20260811.1")

    assert 'triggerExisting("openProjectManager")' in script.text
    assert 'triggerExisting("openAccountManager")' in script.text
    assert 'triggerExisting("openServiceWorkflow")' in script.text
    assert 'byId("openKnowledgeBase")' in script.text
    assert "setResult(" not in script.text
    assert "saveConfig(" not in script.text
    assert "MutationObserver" not in script.text
    assert "ZHILINK_UI_V4_RUNTIME" in script.text

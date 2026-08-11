from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_navigation_assets_are_removed_and_shell_owns_navigation() -> None:
    with TestClient(app) as client:
        removed_script = client.get("/assets/ui-v4-navigation.js?v=20260811.1")
        removed_stylesheet = client.get("/assets/ui-v4-navigation.css?v=20260811.1")
        shell_script = client.get("/assets/ui-v4-shell.js?v=20260811.1")
        shell_stylesheet = client.get("/assets/ui-v4-shell.css?v=20260811.1")

    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert removed_script.status_code == 404
    assert removed_stylesheet.status_code == 404
    assert shell_script.status_code == 200
    assert shell_stylesheet.status_code == 200
    assert 'id="uiV4ProjectContext"' in html
    assert 'id="uiV4AccountToggle"' in html
    assert 'id="uiV4ResourceNavigation"' in html
    assert 'id="uiV4KnowledgeNav"' in html
    assert "ui-v4-navigation.css" not in html
    assert "ui-v4-navigation" not in html
    assert "uiV4ProjectContext" in shell_script.text
    assert "uiV4ResourceNavigation" in shell_script.text
    assert "ui-v4-navigation.css" not in shell_script.text
    assert ".ui-v4-shell .ui-v4-project-context" in shell_stylesheet.text
    assert ".ui-v4-shell .ui-v4-resource-navigation" in shell_stylesheet.text


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

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_live_redesign_is_loaded_after_business_extensions() -> None:
    routes = (ROOT / "backend" / "project_routes.py").read_text(encoding="utf-8")
    assert '"ui-redesign-live.js"' in routes
    assert routes.index('"product-simplification.js"') < routes.index('"ui-redesign-live.js"')


def test_live_redesign_preserves_real_workspace_actions() -> None:
    script = (ASSETS / "ui-redesign-live.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "ui-redesign-live.css").read_text(encoding="utf-8")

    assert "ZHILINK_UI_REDESIGN_LIVE_READY" in script
    assert 'triggerExisting("openProjectManager")' in script
    assert 'triggerExisting("openAccountManager")' in script
    assert 'triggerExisting("openIdentity")' in script
    assert 'openApiModal()' in script
    assert 'go("report")' in script
    assert 'fetch("/api/projects?limit=4&offset=0"' in script
    assert "collectPendingItems" in script
    assert "state.results" in script
    assert "ui-redesign-live" in stylesheet
    assert "data-demo-project" not in script
    assert "98%" not in script
    assert "平均节省" not in script


def test_live_redesign_keeps_advanced_features_outside_primary_navigation() -> None:
    script = (ASSETS / "ui-redesign-live.js").read_text(encoding="utf-8")
    assert "账号、组织与权限" in script
    assert "模型与 API 配置" in script
    assert "清空当前会话" in script
    assert "live-account-menu" in script

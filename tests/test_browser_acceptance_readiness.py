from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "frontend" / "assets" / "app.js").read_text(encoding="utf-8")
BROWSER_ACCEPTANCE = (ROOT / "scripts" / "browser_acceptance.mjs").read_text(encoding="utf-8")


def test_browser_acceptance_waits_for_core_app_initialization() -> None:
    assert "await initDefaults();\n  bindEvents();" in APP_JS
    assert "isInitialized: () => initialized" in (ROOT / "frontend" / "assets" / "model-config-save-v4.js").read_text(encoding="utf-8")
    assert "modelInitialized: Boolean(window.ZHILINK_MODEL_CONFIG?.isInitialized?.())" in BROWSER_ACCEPTANCE

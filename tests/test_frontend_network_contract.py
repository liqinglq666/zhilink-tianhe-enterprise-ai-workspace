from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "frontend" / "assets" / "app.js"


def test_legacy_api_post_helper_stays_removed() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "async function apiPost(" not in source
    assert "REQUEST_TIMEOUT_MS" not in source
    assert "throw new Error(detail)" not in source
    assert "hooks.runGeneration({ url, payload, key })" in source

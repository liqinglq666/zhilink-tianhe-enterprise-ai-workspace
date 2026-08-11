from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
RUNTIME = ASSETS / "ui-v4-runtime.js"


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_runtime_is_the_single_v4_stylesheet_loader_owner() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "function ensureStylesheet(key, href)" in runtime
    assert 'document.createElement("link")' in runtime
    assert "window.ZHILINK_UI_V4_HELPERS = Object.freeze" in runtime
    assert "window.ZHILINK_UI_V4_HELPERS_READY = true" in runtime


def test_v4_presentation_layers_use_the_shared_stylesheet_helper() -> None:
    consumers = {
        "ui-v4-shell.js": "shell",
        "ui-v4-dashboard.js": "dashboard",
        "ui-v4-workspace.js": "workspace",
        "ui-v4-overlays.js": "overlays",
        "ui-v4-forms.js": "forms",
        "ui-v4-results.js": "results",
        "ui-v4-states.js": "states",
        "ui-v4-final-qa.js": "final-qa",
    }

    for filename, key in consumers.items():
        source = read(filename)
        assert "window.ZHILINK_UI_V4_HELPERS" in source, filename
        assert f'ensureStylesheet("{key}",' in source, filename
        assert "function ensureStyles()" not in source, filename
        assert 'document.createElement("link")' not in source, filename
        assert ".rel = \"stylesheet\"" not in source, filename

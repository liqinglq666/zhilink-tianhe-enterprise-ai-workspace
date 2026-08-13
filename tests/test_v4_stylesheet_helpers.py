from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
RUNTIME = ASSETS / "ui-v4-runtime.js"
INDEX = ROOT / "frontend" / "index.html"


STATIC_STYLES = {
    "ui-v4-shell.js": ("ui-v4-shell.css", "data-ui-v4-shell"),
    "ui-v4-dashboard.js": ("ui-v4-dashboard.css", "data-ui-v4-dashboard"),
    "ui-v4-workspace.js": ("ui-v4-workspace.css", "data-ui-v4-workspace"),
    "ui-v4-overlays.js": ("ui-v4-overlays.css", "data-ui-v4-overlays"),
    "ui-v4-forms.js": ("ui-v4-forms.css", "data-ui-v4-forms"),
    "ui-v4-results.js": ("ui-v4-results.css", "data-ui-v4-results"),
    "ui-v4-states.js": ("ui-v4-states.css", "data-ui-v4-states"),
    "ui-v4-final-qa.js": ("ui-v4-final-qa.css", "data-ui-v4-final-qa"),
}


def read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_index_is_the_single_v4_stylesheet_owner() -> None:
    html = INDEX.read_text(encoding="utf-8")
    head = html.split("</head>", 1)[0]

    for stylesheet, marker in STATIC_STYLES.values():
        assert f'href="/assets/{stylesheet}' in head
        assert marker in head


def test_runtime_no_longer_owns_a_stylesheet_loader() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "function ensureStylesheet" not in runtime
    assert "ensureStylesheet" not in runtime
    assert 'document.createElement("link")' not in runtime
    assert "window.ZHILINK_UI_V4_HELPERS_READY = true" in runtime


def test_v4_presentation_layers_do_not_load_stylesheets_from_javascript() -> None:
    for filename, (stylesheet, _) in STATIC_STYLES.items():
        source = read(filename)
        assert "ensureStylesheet" not in source, filename
        assert "function ensureStyles()" not in source, filename
        assert 'document.createElement("link")' not in source, filename
        assert '.rel = "stylesheet"' not in source, filename
        assert f"/assets/{stylesheet}" not in source, filename
        assert "const VERSION =" not in source, filename

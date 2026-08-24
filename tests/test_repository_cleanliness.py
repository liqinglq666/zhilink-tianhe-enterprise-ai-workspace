from __future__ import annotations

import subprocess
from pathlib import Path

from backend.project_routes import UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
INDEX = ROOT / "frontend" / "index.html"


def test_frontend_javascript_has_no_orphan_or_duplicate_assets() -> None:
    bundled = list(UI_SCRIPTS)
    files = sorted(path.name for path in ASSETS.glob("*.js"))

    assert len(bundled) == len(set(bundled))
    assert files == sorted(bundled)


def test_frontend_css_and_json_assets_are_referenced() -> None:
    html = INDEX.read_text(encoding="utf-8")
    scripts = "\n".join(path.read_text(encoding="utf-8") for path in ASSETS.glob("*.js"))
    styles = "\n".join(path.read_text(encoding="utf-8") for path in ASSETS.glob("*.css"))
    references = "\n".join((html, scripts, styles))

    for pattern in ("*.css", "*.json"):
        for path in ASSETS.glob(pattern):
            assert path.name in references, f"orphan asset: {path.relative_to(ROOT)}"


def test_removed_patch_layers_do_not_return() -> None:
    obsolete = (
        "saas-product-polish-v3.js",
        "saas-product-polish-v3.css",
        "release-polish-v4.css",
        "ui-v4-foundation.js",
        "ui-v4-workspace.js",
        "project-result-meta.js",
        "enterprise-user-view-guards.js",
        "enterprise-user-view.js",
        "enterprise-user-view.css",
    )
    for name in obsolete:
        assert not (ASSETS / name).exists(), name
        assert name not in UI_SCRIPTS


def test_removed_python_compatibility_code_does_not_return() -> None:
    package = ROOT / "src" / "zhilian_tianhe_agent"
    agents = (package / "agents.py").read_text(encoding="utf-8")
    utilities = (package / "utils.py").read_text(encoding="utf-8")
    package_init = (package / "__init__.py").read_text(encoding="utf-8")
    dependencies = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert not (package / "rule_engine.py").exists()
    assert "Compatibility stream that exposes only the verified result" not in agents
    for obsolete_helper in ("safe_join", "normalize_text", "has_meaningful_text", "compact_dict"):
        assert obsolete_helper not in utilities
    assert "__version__" not in package_init
    assert "python-dotenv" not in dependencies


def test_repository_does_not_track_generated_or_editor_junk() -> None:
    forbidden_dirs = {
        "__pycache__",
        ".pytest_cache",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
        "runtime",
    }
    forbidden_suffixes = {".pyc", ".pyo", ".log", ".db", ".sqlite", ".sqlite3", ".zip"}

    tracked = subprocess.check_output(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).splitlines()

    for item in tracked:
        relative = Path(item)
        assert not forbidden_dirs.intersection(relative.parts), f"generated directory tracked: {relative}"
        assert relative.suffix.lower() not in forbidden_suffixes, f"generated file tracked: {relative}"

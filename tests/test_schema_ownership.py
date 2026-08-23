from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def test_backend_runtime_never_creates_schema() -> None:
    offenders: list[str] = []
    for path in sorted(BACKEND.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if ".create_all(" in source:
            offenders.append(path.name)
    assert offenders == [], f"Runtime schema creation must stay in Alembic only: {offenders}"


def test_service_workflow_policy_parser_has_single_owner() -> None:
    store = (BACKEND / "service_workflow_store.py").read_text(encoding="utf-8")
    routes = (BACKEND / "service_workflow_routes.py").read_text(encoding="utf-8")
    guards = (BACKEND / "service_workflow_guards.py").read_text(encoding="utf-8")

    assert "safe_official_references" in store
    assert "def safe_official_references" in guards
    assert "workflow_store.official" not in routes


def test_runtime_version_matches_project_metadata() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    main = (BACKEND / "main.py").read_text(encoding="utf-8")
    package_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    runtime_match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', main, re.MULTILINE)

    assert package_match is not None
    assert runtime_match is not None
    assert runtime_match.group(1) == package_match.group(1)

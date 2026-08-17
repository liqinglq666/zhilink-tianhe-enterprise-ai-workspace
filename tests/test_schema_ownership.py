from __future__ import annotations

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

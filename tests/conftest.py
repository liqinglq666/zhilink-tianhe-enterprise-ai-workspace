from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from backend.auth_store import reset_account_store_for_tests
from backend.knowledge_store import reset_knowledge_store_for_tests
from backend.project_store import reset_project_store_for_tests
from backend.review_store import reset_review_store_for_tests
from backend.service_workflow_store import reset_service_workflow_store_for_tests

ROOT = Path(__file__).resolve().parents[1]


def _reset_stores() -> None:
    # Reset dependants before disposing the shared project engine.
    reset_knowledge_store_for_tests()
    reset_service_workflow_store_for_tests()
    reset_review_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()


def _migrate(database_url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def isolate_database_state(tmp_path, monkeypatch):
    """Give every test an independent, fully migrated database."""
    database_url = f"sqlite:///{tmp_path / 'isolated-suite.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    _reset_stores()
    _migrate(database_url)
    try:
        yield
    finally:
        _reset_stores()

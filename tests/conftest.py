from __future__ import annotations

import pytest

from backend.auth_store import reset_account_store_for_tests
from backend.knowledge_store import reset_knowledge_store_for_tests
from backend.project_store import reset_project_store_for_tests
from backend.review_store import reset_review_store_for_tests
from backend.service_workflow_store import reset_service_workflow_store_for_tests


def _reset_stores() -> None:
    # Reset dependants before disposing the shared project engine.
    reset_knowledge_store_for_tests()
    reset_service_workflow_store_for_tests()
    reset_review_store_for_tests()
    reset_account_store_for_tests()
    reset_project_store_for_tests()


@pytest.fixture(autouse=True)
def isolate_database_state(tmp_path, monkeypatch):
    """Give every test an independent database and singleton graph.

    The complete suite exercises several FastAPI app factories that reuse the
    same module-level store accessors. Without a suite-wide boundary, a test
    that forgets one reset can leak users and organizations into later tests.
    """

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'isolated-suite.db'}")
    _reset_stores()
    try:
        yield
    finally:
        _reset_stores()

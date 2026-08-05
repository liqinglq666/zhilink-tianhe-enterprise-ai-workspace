from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.model_registry import get_model_metadata

ROOT = Path(__file__).resolve().parents[1]
REVISION = "20260805_0001"
EXPECTED_TABLES = {
    "projects",
    "project_versions",
    "users",
    "organizations",
    "organization_memberships",
    "auth_sessions",
    "organization_projects",
    "project_review_events",
    "knowledge_articles",
    "knowledge_versions",
    "knowledge_review_events",
    "service_cases",
    "service_case_nodes",
    "service_case_contexts",
    "service_case_events",
    "alembic_version",
}


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _assert_head(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES <= tables
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert revision == REVISION
    finally:
        engine.dispose()


def test_baseline_upgrades_a_clean_database_and_is_idempotent(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'clean.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _config(database_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    _assert_head(database_url)


def test_baseline_adopts_a_legacy_create_all_database(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = create_engine(database_url)
    try:
        get_model_metadata().create_all(engine, checkfirst=True)
        assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()

    command.upgrade(_config(database_url), "head")

    _assert_head(database_url)

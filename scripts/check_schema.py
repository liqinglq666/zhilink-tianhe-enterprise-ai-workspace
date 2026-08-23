#!/usr/bin/env python3
"""Validate that the configured database is ready for the current Alembic head."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.project_store import normalize_database_url  # noqa: E402
from backend.schema_contract import REQUIRED_TABLES  # noqa: E402


def expected_revision() -> str:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    head = ScriptDirectory.from_config(config).get_current_head()
    if not head:
        raise RuntimeError("Alembic migration head is not defined.")
    return head


def main() -> int:
    database_url = normalize_database_url(os.getenv("DATABASE_URL"))
    expected = expected_revision()
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        tables = set(inspect(engine).get_table_names())
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise RuntimeError(f"Database schema is missing tables: {', '.join(missing)}")

        with engine.connect() as connection:
            current_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if current_revision != expected:
                raise RuntimeError(f"Database revision is {current_revision}; expected {expected}.")
            if connection.dialect.name == "sqlite":
                foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
                if foreign_keys != 1:
                    raise RuntimeError("SQLite foreign key enforcement is disabled.")
    finally:
        engine.dispose()

    print(f"Database schema ready ({expected}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

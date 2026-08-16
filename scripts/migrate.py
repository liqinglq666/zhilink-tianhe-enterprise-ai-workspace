#!/usr/bin/env python3
"""Upgrade the configured database to the latest Alembic revision."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.project_store import normalize_database_url  # noqa: E402

# Session-level PostgreSQL advisory lock. A crashed process releases it automatically.
MIGRATION_LOCK_KEY = 0x5A48494C494E4B


def build_config() -> tuple[Config, str]:
    database_url = normalize_database_url(os.getenv("DATABASE_URL"))
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    # ConfigParser treats percent signs as interpolation markers.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config, database_url


@contextmanager
def migration_lock(database_url: str) -> Iterator[None]:
    """Serialize PostgreSQL migrations across concurrently starting containers."""
    if not database_url.startswith("postgresql+"):
        yield
        return

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:lock_key)"),
                {"lock_key": MIGRATION_LOCK_KEY},
            )
            try:
                yield
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": MIGRATION_LOCK_KEY},
                )
    finally:
        engine.dispose()


def main() -> int:
    config, database_url = build_config()
    with migration_lock(database_url):
        command.upgrade(config, "head")
    scheme = database_url.split(":", 1)[0]
    print(f"Database migration complete ({scheme}, head).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

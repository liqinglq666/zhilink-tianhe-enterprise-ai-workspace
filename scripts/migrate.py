#!/usr/bin/env python3
"""Upgrade the configured database to the latest Alembic revision."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.project_store import normalize_database_url  # noqa: E402


def build_config() -> tuple[Config, str]:
    database_url = normalize_database_url(os.getenv("DATABASE_URL"))
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    # ConfigParser treats percent signs as interpolation markers. Escaping here
    # keeps PostgreSQL passwords containing '%' valid.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config, database_url


def main() -> int:
    config, database_url = build_config()
    command.upgrade(config, "head")
    scheme = database_url.split(":", 1)[0]
    print(f"Database migration complete ({scheme}, head).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

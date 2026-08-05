"""FastAPI backend for 智链天河 Agent.

The package registers SQLite connection safeguards before any SQLAlchemy engine is
created. Keeping this at package-import time ensures the same behaviour in the
web app, migration commands, tests, and one-off maintenance scripts.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    """Enable SQLite referential integrity for every application connection.

    SQLite does not enforce declared foreign keys unless the pragma is enabled
    per connection. Without it, project deletion can leave service workflow,
    review, and organization rows orphaned even though the models declare
    ``ON DELETE`` actions.
    """

    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()

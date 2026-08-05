"""Establish the versioned application schema baseline.

Revision ID: 20260805_0001
Revises: None
Create Date: 2026-08-05

This first migration intentionally uses the shared SQLAlchemy metadata with
``checkfirst=True``. It supports both a brand-new database and an existing Demo
database that was originally created through ``Base.metadata.create_all``.
After this revision, all schema changes must be expressed as explicit Alembic
revisions rather than relying on create_all to mutate existing installations.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from backend.model_registry import get_model_metadata

revision: str = "20260805_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    get_model_metadata().create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise RuntimeError(
        "The production baseline is intentionally non-destructive. "
        "Restore a database backup instead of downgrading below the baseline."
    )

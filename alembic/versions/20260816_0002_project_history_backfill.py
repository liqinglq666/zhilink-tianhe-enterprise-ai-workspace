"""Move legacy project-history backfill out of application runtime.

Revision ID: 20260816_0002
Revises: 20260805_0001
Create Date: 2026-08-16
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
from sqlalchemy import func, select

from backend.project_store import (
    ProjectHistoryRecord,
    ProjectRecord,
    _default_label,
    _initial_modules,
)

revision: str = "20260816_0002"
down_revision: Union[str, None] = "20260805_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create one immutable baseline version for legacy projects that have no history."""
    bind = op.get_bind()
    projects = bind.execute(select(ProjectRecord.__table__)).mappings().all()
    for project in projects:
        existing = bind.execute(
            select(func.count(ProjectHistoryRecord.id)).where(
                ProjectHistoryRecord.project_id == project["id"]
            )
        ).scalar_one()
        if existing:
            continue
        bind.execute(
            ProjectHistoryRecord.__table__.insert().values(
                id=str(uuid4()),
                project_id=project["id"],
                workspace_hash=project["workspace_hash"],
                version_number=project["lock_version"],
                change_kind="baseline",
                label=_default_label("baseline"),
                changed_modules=_initial_modules(project["snapshot"] or {}),
                source_version_number=None,
                project_name=project["name"],
                project_description=project["description"],
                project_status=project["status"],
                snapshot=dict(project["snapshot"] or {}),
            )
        )


def downgrade() -> None:
    # Baseline history is intentionally preserved; deleting it would destroy audit records.
    pass

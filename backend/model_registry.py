"""Load every SQLAlchemy model into the shared application metadata."""

from __future__ import annotations

from sqlalchemy import MetaData

from .project_store import Base


def get_model_metadata() -> MetaData:
    """Return metadata containing all persistent application tables.

    Imports are intentionally local. They register each declarative model on
    ``Base.metadata`` without creating stores, opening sessions, or touching the
    database. Alembic and integrity tests use this as the single schema source.
    """

    from . import auth_store as _auth_store  # noqa: F401
    from . import knowledge_store as _knowledge_store  # noqa: F401
    from . import review_store as _review_store  # noqa: F401
    from . import service_workflow_store as _service_workflow_store  # noqa: F401

    return Base.metadata

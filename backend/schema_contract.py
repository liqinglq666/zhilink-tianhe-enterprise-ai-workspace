"""Stable database schema identifiers used by migrations and readiness checks."""

from __future__ import annotations

BASELINE_REVISION = "20260805_0001"
REQUIRED_TABLES = frozenset(
    {
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
)

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, insert, select, text

from backend.auth_store import AccountStore, ProjectScope
from backend.model_registry import get_model_metadata
from backend.project_store import ProjectStore

USER_ID = "00000000-0000-0000-0000-000000000001"
ORG_ID = "00000000-0000-0000-0000-000000000002"
PROJECT_ID = "00000000-0000-0000-0000-000000000003"
CASE_ID = "00000000-0000-0000-0000-000000000004"
NODE_ID = "00000000-0000-0000-0000-000000000005"


def _seed_project_graph(store: ProjectStore) -> None:
    tables = get_model_metadata().tables
    now = datetime.now(timezone.utc)
    workspace_hash = "w" * 64

    with store.engine.begin() as connection:
        connection.execute(
            insert(tables["users"]).values(
                id=USER_ID,
                email="owner@example.com",
                display_name="Owner",
                password_hash="test-only",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            insert(tables["organizations"]).values(
                id=ORG_ID,
                name="Integrity Test Organization",
                slug="integrity-test-org",
                created_by_user_id=USER_ID,
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            insert(tables["organization_memberships"]).values(
                id="00000000-0000-0000-0000-000000000006",
                organization_id=ORG_ID,
                user_id=USER_ID,
                role="owner",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            insert(tables["projects"]).values(
                id=PROJECT_ID,
                workspace_hash=workspace_hash,
                name="Cascade Project",
                description="",
                status="active",
                snapshot={"results": {"meeting": "test"}},
                lock_version=1,
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            insert(tables["organization_projects"]).values(
                project_id=PROJECT_ID,
                organization_id=ORG_ID,
                created_by_user_id=USER_ID,
                created_at=now,
            )
        )
        connection.execute(
            insert(tables["project_versions"]).values(
                id="00000000-0000-0000-0000-000000000007",
                project_id=PROJECT_ID,
                workspace_hash=workspace_hash,
                version_number=1,
                change_kind="create",
                label="create",
                changed_modules=["project"],
                source_version_number=None,
                project_name="Cascade Project",
                project_description="",
                project_status="active",
                snapshot={"results": {"meeting": "test"}},
                created_at=now,
            )
        )
        connection.execute(
            insert(tables["project_review_events"]).values(
                id="00000000-0000-0000-0000-000000000008",
                project_id=PROJECT_ID,
                module="meeting",
                action="save_edit",
                from_status="ai_draft",
                to_status="edited",
                actor_user_id=USER_ID,
                actor_name="Owner",
                actor_role="owner",
                note="",
                content_hash="a" * 64,
                created_at=now,
            )
        )
        connection.execute(
            insert(tables["service_cases"]).values(
                id=CASE_ID,
                organization_id=ORG_ID,
                project_id=PROJECT_ID,
                case_number="THSC-00000001",
                title="Project service case",
                objective="Verify cascading deletion",
                priority="normal",
                status="draft",
                owner_user_id=USER_ID,
                due_date=None,
                lock_version=1,
                current_context_version=1,
                closure_summary="",
                created_by_user_id=USER_ID,
                created_at=now,
                updated_at=now,
                completed_at=None,
            )
        )
        connection.execute(
            insert(tables["service_case_nodes"]).values(
                id=NODE_ID,
                case_id=CASE_ID,
                sequence=1,
                node_type="intake",
                title="Intake",
                description="",
                status="pending",
                assignee_user_id=USER_ID,
                due_date=None,
                output_summary="",
                decision_note="",
                started_at=None,
                submitted_at=None,
                completed_at=None,
                updated_at=now,
            )
        )
        connection.execute(
            insert(tables["service_case_contexts"]).values(
                id="00000000-0000-0000-0000-000000000009",
                case_id=CASE_ID,
                context_version=1,
                project_id=PROJECT_ID,
                project_name="Cascade Project",
                project_version=1,
                project_updated_at=now,
                snapshot={},
                context_sha256="b" * 64,
                created_by_user_id=USER_ID,
                created_at=now,
            )
        )
        connection.execute(
            insert(tables["service_case_events"]).values(
                id="00000000-0000-0000-0000-000000000010",
                case_id=CASE_ID,
                node_id=NODE_ID,
                action="create",
                before_status="none",
                after_status="draft",
                actor_user_id=USER_ID,
                actor_name="Owner",
                actor_role="owner",
                note="",
                payload_sha256="c" * 64,
                created_at=now,
            )
        )


def test_sqlite_connections_enable_foreign_keys(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'foreign-keys.db'}")
    get_model_metadata().create_all(store.engine, checkfirst=True)

    with store.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000


def test_project_delete_cascades_all_project_owned_records(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'cascade.db'}")
    get_model_metadata().create_all(store.engine, checkfirst=True)
    _seed_project_graph(store)

    account = AccountStore(store)
    scope = ProjectScope(
        kind="organization",
        storage_hash="unused-for-organization-scope",
        organization_id=ORG_ID,
        user_id=USER_ID,
        role="owner",
    )
    account.delete_project(scope, PROJECT_ID)

    project_owned_tables = (
        "projects",
        "organization_projects",
        "project_versions",
        "project_review_events",
        "service_cases",
        "service_case_nodes",
        "service_case_contexts",
        "service_case_events",
    )
    tables = get_model_metadata().tables
    with store.engine.connect() as connection:
        for table_name in project_owned_tables:
            count = connection.execute(select(func.count()).select_from(tables[table_name])).scalar_one()
            assert count == 0, f"{table_name} left orphaned rows"

        assert connection.execute(select(func.count()).select_from(tables["users"])).scalar_one() == 1
        assert connection.execute(select(func.count()).select_from(tables["organizations"])).scalar_one() == 1

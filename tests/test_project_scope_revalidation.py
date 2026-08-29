from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from backend.auth_store import AccountStoreError, get_account_store, reset_account_store_for_tests
from backend.project_store import reset_project_store_for_tests

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse battery staple"


def _migrate(database_url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def _store(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'scope-revalidation.db'}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
    os.environ["PASSWORD_MIN_LENGTH"] = "10"
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    _migrate(database_url)
    return get_account_store()


def _snapshot(text: str = "会议材料") -> dict:
    return {
        "identity": {},
        "profile": {},
        "forms": {"meetingInput": text},
        "results": {},
        "meta": {},
        "current_section": "meeting",
    }


def test_stale_project_scopes_are_revalidated_after_role_change_and_removal(tmp_path) -> None:
    store = _store(tmp_path)
    owner_auth, _, _ = store.register(
        email="owner@example.com",
        password=PASSWORD,
        display_name="Owner",
        organization_name="Scope Org",
    )
    member_auth, _, _ = store.register(
        email="member@example.com",
        password=PASSWORD,
        display_name="Member",
        organization_name="Member Personal Org",
    )
    organization_id = store.list_organizations(owner_auth.user_id)[0]["id"]
    store.add_member(owner_auth.user_id, organization_id, "member@example.com", "admin")

    stale_create = store.organization_scope(member_auth.user_id, organization_id, "project:create")
    stale_update = store.organization_scope(member_auth.user_id, organization_id, "project:update")
    stale_delete = store.organization_scope(member_auth.user_id, organization_id, "project:delete")
    owner_scope = store.organization_scope(owner_auth.user_id, organization_id, "project:create")
    project = store.create_project(
        owner_scope,
        name="Protected Project",
        description="",
        snapshot=_snapshot(),
        version_label="",
    )

    store.update_member_role(owner_auth.user_id, organization_id, member_auth.user_id, "viewer")

    for permission, operation in (
        (
            "project:create",
            lambda: store.create_project(
                stale_create,
                name="Stale Create",
                description="",
                snapshot=_snapshot("stale create"),
                version_label="",
            ),
        ),
        (
            "project:update",
            lambda: store.update_project(
                stale_update,
                project["id"],
                expected_lock_version=project["lock_version"],
                name="Stale Update",
                description=None,
                status=None,
                snapshot=None,
                version_label="",
            ),
        ),
        ("project:delete", lambda: store.delete_project(stale_delete, project["id"])),
    ):
        with pytest.raises(AccountStoreError) as exc_info:
            operation()
        assert exc_info.value.status_code == 403, permission
        assert exc_info.value.code == "RBAC_FORBIDDEN", permission

    stale_read = store.organization_scope(member_auth.user_id, organization_id, "project:read")
    store.remove_member(owner_auth.user_id, organization_id, member_auth.user_id)

    with pytest.raises(AccountStoreError) as exc_info:
        store.get_project(stale_read, project["id"])
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"

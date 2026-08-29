from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from backend.auth_store import (
    AccountStoreError,
    OrganizationMembershipRecord,
    get_account_store,
    reset_account_store_for_tests,
)
from backend.project_store import reset_project_store_for_tests

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse battery staple"


def _migrate(database_url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def _store(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'member-rbac-revalidation.db'}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["AUTH_ALLOW_REGISTRATION"] = "true"
    os.environ["PASSWORD_MIN_LENGTH"] = "10"
    reset_account_store_for_tests()
    reset_project_store_for_tests()
    _migrate(database_url)
    return get_account_store()


def _register(store, email: str, name: str):
    auth, _, _ = store.register(
        email=email,
        password=PASSWORD,
        display_name=name,
        organization_name=f"{name} Personal Org",
    )
    return auth


def test_member_writes_revalidate_actor_after_transaction_starts(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path)
    owner = _register(store, "owner@example.com", "Owner")
    actor = _register(store, "admin@example.com", "Admin")
    target = _register(store, "target@example.com", "Target")
    candidate = _register(store, "candidate@example.com", "Candidate")

    organization_id = store.list_organizations(owner.user_id)[0]["id"]
    store.add_member(owner.user_id, organization_id, actor.email, "admin")
    store.add_member(owner.user_id, organization_id, target.email, "viewer")

    original_lock = store._lock_organization

    def demote_actor_after_request_precheck(session, locked_organization_id: str) -> None:
        membership = session.scalar(
            select(OrganizationMembershipRecord).where(
                OrganizationMembershipRecord.organization_id == locked_organization_id,
                OrganizationMembershipRecord.user_id == actor.user_id,
                OrganizationMembershipRecord.status == "active",
            )
        )
        assert membership is not None
        membership.role = "viewer"
        session.flush()
        original_lock(session, locked_organization_id)

    monkeypatch.setattr(store, "_lock_organization", demote_actor_after_request_precheck)

    operations = (
        lambda: store.add_member(actor.user_id, organization_id, candidate.email, "viewer"),
        lambda: store.update_member_role(actor.user_id, organization_id, target.user_id, "editor"),
        lambda: store.remove_member(actor.user_id, organization_id, target.user_id),
    )

    for operation in operations:
        with pytest.raises(AccountStoreError) as exc_info:
            operation()
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "RBAC_FORBIDDEN"

    with store.sessions() as session:
        candidate_membership = session.scalar(
            select(OrganizationMembershipRecord).where(
                OrganizationMembershipRecord.organization_id == organization_id,
                OrganizationMembershipRecord.user_id == candidate.user_id,
            )
        )
        target_membership = session.scalar(
            select(OrganizationMembershipRecord).where(
                OrganizationMembershipRecord.organization_id == organization_id,
                OrganizationMembershipRecord.user_id == target.user_id,
            )
        )
        actor_membership = session.scalar(
            select(OrganizationMembershipRecord).where(
                OrganizationMembershipRecord.organization_id == organization_id,
                OrganizationMembershipRecord.user_id == actor.user_id,
            )
        )

    assert candidate_membership is None
    assert target_membership is not None
    assert target_membership.status == "active"
    assert target_membership.role == "viewer"
    assert actor_membership is not None
    assert actor_membership.role == "admin"

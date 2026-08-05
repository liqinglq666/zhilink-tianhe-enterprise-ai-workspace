from __future__ import annotations

import sqlite3

import pytest

from backend.project_store import (
    ProjectNotFound,
    ProjectStore,
    ProjectVersionConflict,
    hash_workspace_key,
    normalize_database_url,
)

KEY_A = "a" * 40
KEY_B = "b" * 40


def test_normalize_database_url_supports_sqlite_and_postgres():
    assert normalize_database_url(None).startswith("sqlite:///")
    assert normalize_database_url("postgres://u:p@db/app").startswith(
        "postgresql+psycopg://"
    )
    assert normalize_database_url("postgresql://u:p@db/app").startswith(
        "postgresql+psycopg://"
    )
    with pytest.raises(ValueError):
        normalize_database_url("mysql://db/app")


def test_workspace_key_is_hashed_and_never_stored_raw(tmp_path):
    database = tmp_path / "projects.db"
    store = ProjectStore(f"sqlite:///{database}")
    store.create(KEY_A, name="测试项目", description="", snapshot={})

    with sqlite3.connect(database) as connection:
        row = connection.execute("select workspace_hash from projects").fetchone()

    assert row[0] == hash_workspace_key(KEY_A)
    assert row[0] != KEY_A


def test_projects_are_isolated_by_workspace(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'projects.db'}")
    created = store.create(KEY_A, name="项目A", description="", snapshot={})

    items_a, total_a = store.list(KEY_A)
    items_b, total_b = store.list(KEY_B)

    assert total_a == 1 and items_a[0]["id"] == created["id"]
    assert total_b == 0 and items_b == []
    with pytest.raises(ProjectNotFound):
        store.get(KEY_B, created["id"])


def test_update_uses_optimistic_lock_and_archive_filter(tmp_path):
    store = ProjectStore(f"sqlite:///{tmp_path / 'projects.db'}")
    created = store.create(KEY_A, name="项目A", description="", snapshot={})

    updated = store.update(
        KEY_A,
        created["id"],
        expected_lock_version=1,
        status="archived",
        snapshot={"current_section": "meeting"},
    )

    assert updated["lock_version"] == 2
    assert updated["status"] == "archived"
    assert store.list(KEY_A)[1] == 0
    assert store.list(KEY_A, include_archived=True)[1] == 1
    with pytest.raises(ProjectVersionConflict) as conflict:
        store.update(
            KEY_A,
            created["id"],
            expected_lock_version=1,
            name="过期页面写入",
        )
    assert conflict.value.current_version == 2

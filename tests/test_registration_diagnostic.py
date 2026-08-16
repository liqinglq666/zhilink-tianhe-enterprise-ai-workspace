from __future__ import annotations

import pytest

from backend.auth_store import AccountStoreError, get_account_store


def test_registration_diagnostic_exposes_underlying_integrity_error():
    try:
        auth, token, csrf = get_account_store().register(
            email="diagnostic@example.com",
            password="correct horse battery staple",
            display_name="Diagnostic",
            organization_name="Diagnostic Org",
            user_agent="pytest",
        )
    except AccountStoreError as exc:
        cause = repr(exc.__cause__) if exc.__cause__ is not None else "<no underlying cause>"
        pytest.fail(f"registration failed: code={exc.code}; cause={cause}")
    assert auth.email == "diagnostic@example.com"
    assert token
    assert csrf

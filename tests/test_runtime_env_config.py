from __future__ import annotations

from pathlib import Path

from backend.main import _bounded_env_int, _env_int, _positive_env_int

ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = ROOT / "backend" / "main.py"


def test_env_int_falls_back_for_invalid_or_empty_values(monkeypatch) -> None:
    monkeypatch.setenv("ZHILINK_TEST_INT", "not-a-number")
    assert _env_int("ZHILINK_TEST_INT", 17) == 17

    monkeypatch.setenv("ZHILINK_TEST_INT", "   ")
    assert _env_int("ZHILINK_TEST_INT", 17) == 17


def test_env_int_preserves_valid_integer_values(monkeypatch) -> None:
    monkeypatch.setenv("ZHILINK_TEST_INT", " 42 ")
    assert _env_int("ZHILINK_TEST_INT", 17) == 42


def test_positive_env_int_rejects_zero_and_negative_values(monkeypatch) -> None:
    monkeypatch.setenv("ZHILINK_TEST_INT", "0")
    assert _positive_env_int("ZHILINK_TEST_INT", 17) == 17

    monkeypatch.setenv("ZHILINK_TEST_INT", "-5")
    assert _positive_env_int("ZHILINK_TEST_INT", 17) == 17

    monkeypatch.setenv("ZHILINK_TEST_INT", "23")
    assert _positive_env_int("ZHILINK_TEST_INT", 17) == 23


def test_bounded_env_int_still_applies_bounds(monkeypatch) -> None:
    monkeypatch.setenv("ZHILINK_TEST_INT", "999")
    assert _bounded_env_int("ZHILINK_TEST_INT", 20, 5, 120) == 120

    monkeypatch.setenv("ZHILINK_TEST_INT", "invalid")
    assert _bounded_env_int("ZHILINK_TEST_INT", 20, 5, 120) == 20


def test_runtime_numeric_settings_use_safe_parser() -> None:
    source = MAIN_PY.read_text(encoding="utf-8")
    unsafe_settings = (
        "MAX_BODY_BYTES",
        "RATE_LIMIT_REQUESTS",
        "RATE_LIMIT_WINDOW_SECONDS",
        "MAX_CONCURRENT_GENERATIONS_PER_CLIENT",
        "MODEL_TEST_TIMEOUT_SECONDS",
        "HSTS_MAX_AGE",
    )

    for name in unsafe_settings:
        assert f'{name} = int(os.getenv(' not in source

    assert 'MAX_BODY_BYTES = _positive_env_int("MAX_BODY_BYTES", 1500000)' in source
    assert 'RATE_LIMIT_WINDOW_SECONDS = _positive_env_int("RATE_LIMIT_WINDOW_SECONDS", 60)' in source
    assert 'RATE_LIMIT_REQUESTS = _env_int("RATE_LIMIT_REQUESTS", 30)' in source
    assert 'MAX_CONCURRENT_GENERATIONS_PER_CLIENT = _env_int("MAX_CONCURRENT_GENERATIONS_PER_CLIENT", 1)' in source
    assert 'MODEL_TEST_TIMEOUT_SECONDS = _bounded_env_int("MODEL_TEST_TIMEOUT_SECONDS", 20, 5, 120)' in source
